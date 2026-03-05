"""
database/init_db.py

Initialise la base SQLite en lisant le fichier schema.sql présent dans le même dossier.

Usage:
    python -m database.init_db            # interactif si la DB existe
    python -m database.init_db --force    # supprime et recrée sans demander
    python -m database.init_db --db path/to/dbfile.db
"""
from pathlib import Path
import argparse
import sqlite3
import sys
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(message)s")


def create_database_from_schema(db_path: Path, schema_path: Path, force: bool = False) -> bool:
    """
    Crée la base SQLite en exécutant le SQL contenu dans schema_path.
    Si db_path existe et force==False, demande confirmation.
    """
    try:
        if not schema_path.exists():
            logger.error("Fichier schema introuvable : %s", schema_path)
            return False

        if db_path.exists():
            if not force:
                resp = input(f"Database already exists at {db_path}. Recreate? (y/N): ").strip().lower()
                if resp != "y":
                    logger.info("Aborted by user.")
                    return False
            try:
                db_path.unlink()
                logger.info("Removed existing database: %s", db_path)
            except Exception as e:
                logger.warning("Could not remove existing DB: %s", e)

        # Ensure parent dir exists
        db_path.parent.mkdir(parents=True, exist_ok=True)

        schema_sql = schema_path.read_text(encoding="utf-8")

        conn = sqlite3.connect(str(db_path))
        try:
            conn.executescript(schema_sql)
            conn.commit()
        finally:
            conn.close()

        logger.info("✅ Database created at: %s", db_path)
        return True
    except Exception as e:
        logger.exception("Failed to create database: %s", e)
        return False


def integrity_check(db_path: Path) -> bool:
    try:
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        cur.execute("PRAGMA integrity_check;")
        row = cur.fetchone()
        conn.close()
        if row and row[0] == "ok":
            logger.info("✅ PRAGMA integrity_check: OK")
            return True
        logger.warning("❌ PRAGMA integrity_check: %s", row)
        return False
    except Exception:
        logger.exception("Integrity check failed")
        return False


def print_stats(db_path: Path) -> None:
    try:
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
        tables = [r[0] for r in cur.fetchall()]
        logger.info("Tables created: %d", len(tables))
        for t in tables:
            logger.info("  - %s", t)
            try:
                cur.execute(f"SELECT COUNT(*) FROM {t};")
                cnt = cur.fetchone()[0]
                logger.info("      rows: %d", cnt)
            except Exception:
                pass
        conn.close()
    except Exception:
        logger.exception("Could not get DB stats")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Initialise la DB SQLite depuis schema.sql")
    parser.add_argument("--db", "-d", type=str, default=str(Path(__file__).parent / "database.db"), help="Chemin du fichier sqlite (par défaut database/database.db)")
    parser.add_argument("--schema", "-s", type=str, default=str(Path(__file__).parent / "schema.sql"), help="Chemin du fichier schema.sql")
    parser.add_argument("--force", "-f", action="store_true", help="Supprimer et recréer la DB sans demander")
    parser.add_argument("--yes", "-y", action="store_true", help="Répond automatiquement 'y' aux confirmations (équivalent de --force)")
    args = parser.parse_args(argv)

    db_path = Path(args.db)
    schema_path = Path(args.schema)
    force = args.force or args.yes

    logger.info("=" * 60)
    logger.info("INITIALISATION DE LA BASE DE DONNÉES (schema.sql séparé)")
    logger.info("Target DB : %s", db_path)
    logger.info("Schema SQL : %s", schema_path)
    logger.info("=" * 60)

    ok = create_database_from_schema(db_path=db_path, schema_path=schema_path, force=force)
    if not ok:
        logger.error("❌ Initialization failed or aborted.")
        sys.exit(1)

    integrity_check(db_path)
    print_stats(db_path)

    logger.info("✅ Initialisation terminée.")


if __name__ == "__main__":
    main()