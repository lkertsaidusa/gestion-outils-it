"""
database/database.py
Wrapper léger pour SQLite : connexion par opération, helpers pour exécuter requêtes.
Usage:
    from database.database import execute, fetchall, fetchone, executemany, get_connection
"""
from pathlib import Path
import sqlite3
import logging
from typing import Any, Dict, List, Optional, Sequence, Union, Iterator
import contextlib

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# Par défaut, la base est située dans le même dossier que ce fichier
DEFAULT_DB_PATH: Path = Path(__file__).parent / "database.db"


def get_connection(db_path: Union[str, Path, None] = None, timeout: float = 30.0) -> sqlite3.Connection:
    """
    Ouvre une connexion sqlite3 configurée correctement.
    - row_factory -> sqlite3.Row (retour sous forme de mapping)
    - active foreign_keys pragma
    - isolation_level None (autocommit disabled by default), we'll manage transactions manually
    """
    db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
    conn = sqlite3.connect(
        str(db_path),
        timeout=timeout,
        detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
    )
    conn.row_factory = sqlite3.Row
    # Activer foreign keys
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
    except Exception:
        # Ne pas interrompre si échec (rare)
        logger.exception("Failed to set PRAGMA foreign_keys")
    return conn


def _row_to_dict(row: Optional[sqlite3.Row]) -> Optional[Dict[str, Any]]:
    """Convertit une ligne sqlite3.Row en dictionnaire."""
    if row is None:
        return None
    return {k: row[k] for k in row.keys()}


def _rows_to_list(rows: Sequence[sqlite3.Row]) -> List[Dict[str, Any]]:
    """Convertit une liste de sqlite3.Row en liste de dictionnaires."""
    return [{k: r[k] for k in r.keys()} for r in rows]


def execute(
    sql: str,
    params: Union[Sequence[Any], Dict[str, Any]] = (),
    db_path: Union[str, Path, None] = None,
    commit: bool = True,
) -> int:
    """
    Execute une instruction SQL d'écriture (INSERT/UPDATE/DELETE).
    Returns: lastrowid (int) if available, else number of rows affected (cursor.rowcount).
    """
    conn = get_connection(db_path)
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        if commit:
            conn.commit()
        lastrowid = cur.lastrowid if cur.lastrowid is not None else cur.rowcount
        return lastrowid if lastrowid is not None else 0
    except Exception:
        conn.rollback()
        logger.exception("Error executing SQL: %s -- params=%s", sql, params)
        raise
    finally:
        conn.close()


def executemany(
    sql: str,
    seq_of_params: Sequence[Sequence[Any]],
    db_path: Union[str, Path, None] = None,
    commit: bool = True,
) -> int:
    """
    Execute plusieurs opérations (ex: many inserts).
    Returns: total rows affected (approx).
    """
    conn = get_connection(db_path)
    try:
        cur = conn.cursor()
        cur.executemany(sql, seq_of_params)
        if commit:
            conn.commit()
        return cur.rowcount
    except Exception:
        conn.rollback()
        logger.exception("Error executing many SQL: %s", sql)
        raise
    finally:
        conn.close()


def fetchone(
    sql: str,
    params: Union[Sequence[Any], Dict[str, Any]] = (),
    db_path: Union[str, Path, None] = None,
) -> Optional[Dict[str, Any]]:
    """
    Execute une requête SELECT et retourne la première ligne (ou None).
    """
    conn = get_connection(db_path)
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        row = cur.fetchone()
        return _row_to_dict(row)
    except Exception:
        logger.exception("Error fetchone SQL: %s -- params=%s", sql, params)
        raise
    finally:
        conn.close()


def fetchall(
    sql: str,
    params: Union[Sequence[Any], Dict[str, Any]] = (),
    db_path: Union[str, Path, None] = None,
) -> List[Dict[str, Any]]:
    """
    Execute une requête SELECT et retourne toutes les lignes sous forme de liste de dicts.
    """
    conn = get_connection(db_path)
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        rows = cur.fetchall()
        return _rows_to_list(rows)
    except Exception:
        logger.exception("Error fetchall SQL: %s -- params=%s", sql, params)
        raise
    finally:
        conn.close()


@contextlib.contextmanager
def transaction(db_path: Union[str, Path, None] = None) -> Iterator[sqlite3.Connection]:
    """
    Context manager pour exécuter plusieurs commandes dans une transaction.
    Usage:
        with transaction() as conn:
            cur = conn.cursor()
            cur.execute(...)
            cur.execute(...)
    """
    conn = get_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        logger.exception("Transaction rolled back")
        raise
    finally:
        conn.close()


def table_exists(table_name: str, db_path: Union[str, Path, None] = None) -> bool:
    """Vérifie si une table existe dans la base de données."""
    r = fetchone("SELECT name FROM sqlite_master WHERE type='table' AND name = ?;", (table_name,), db_path)
    return bool(r)


def list_tables(db_path: Union[str, Path, None] = None) -> List[str]:
    """Liste toutes les tables de la base de données."""
    rows = fetchall("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;", (), db_path)
    return [r["name"] for r in rows]


# Code de test (optionnel, s'exécute seulement si le fichier est lancé directement)
if __name__ == "__main__":
    print("=== Test du module database ===")
    print(f"Chemin de la base de données par défaut: {DEFAULT_DB_PATH}")
    
    # Test de connexion
    try:
        conn = get_connection()
        print("✓ Connexion à la base de données réussie")
        conn.close()
    except Exception as e:
        print(f"✗ Erreur de connexion: {e}")
    
    # Lister les tables existantes
    try:
        tables = list_tables()
        print(f"✓ Tables existantes: {tables if tables else 'Aucune table'}")
    except Exception as e:
        print(f"✗ Erreur lors du listage des tables: {e}")
    
    print("\nModule database prêt à l'emploi!")