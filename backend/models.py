"""
backend/models.py
Représentation des entités et fonctions CRUD pour la base SQLite.

Dépendances:
    from database import database as dbwrapper

Fonctions exposées (essentielles pour les vues/controllers) :
- list_tools(filters: dict | None = None) -> list[dict]
- get_tool(tool_id: int) -> dict | None
- create_tool(data: dict) -> dict   # attend le payload provenant d'AddEquipmentWindow
- update_tool(tool_id: int, data: dict) -> dict
- delete_tool(tool_id: int) -> bool
- get_history(tool_id: int | None = None, limit: int = 100) -> list[dict]
- list_categories() -> list[dict]
- list_locations() -> list[dict]
- add_history_entry(tool_id: int, action: str, old_value: str | None, new_value: str | None, changed_by: str | None)
"""

from typing import Any, Dict, List, Optional, Sequence, Tuple
import logging
import sqlite3

from database import database as dbwrapper
from backend import notification_service

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


# ---------- Utilities / Mapping -------------------------------------------------
def _sanitize_status(raw: Optional[str]) -> Optional[str]:
    """Normalise le statut pour qu'il corresponde aux valeurs CHECK du schéma."""
    if not raw:
        return None
    s = str(raw).upper().strip()
    # Retirer puces et caractères spéciaux fréquemment utilisés dans l'UI ("•", "-", etc.)
    s = s.replace("•", "").replace("·", "").strip()
    # Garder uniquement mots connus
    allowed = {"ACTIVE", "MAINTENANCE", "LENT OUT", "AVAILABLE"}
    # Parfois le statut arrive avec texte supplémentaire; garder le mot qui correspond
    for tok in s.split():
        if tok in allowed:
            return tok
    # Si la chaîne complète est une des valeurs, la retourner
    if s in allowed:
        return s
    # Fallback: None (DB a DEFAULT 'AVAILABLE' si null)
    return None


def _map_input_to_db_fields(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mappe les clés envoyées par l'UI vers les colonnes de la table `tools`.
    UI keys examples: asset_model, brand, serial_number, warranty_date, category, assigned_area, status
    DB columns: name, brand, serial_number, warranty_expiration, type, localisation, status, assigned_to, ...
    """
    out: Dict[str, Any] = {}

    # Nom du produit
    if "asset_model" in data:
        out["name"] = data.get("asset_model") or ""
    elif "name" in data:
        out["name"] = data.get("name") or ""

    # Marque
    if "brand" in data:
        out["brand"] = data.get("brand") or ""
    # product_id optional
    if "product_id" in data:
        out["product_id"] = data.get("product_id") or None

    # serial_number (UI envoie serial_number)
    if "serial_number" in data:
        out["serial_number"] = (data.get("serial_number") or "").strip()

    # category -> type (DB column)
    if "category" in data:
        out["type"] = (data.get("category") or "").strip().upper()

    # assigned_area -> localisation - NORMALISER EN MAJUSCULES
    if "assigned_area" in data:
        out["localisation"] = (data.get("assigned_area") or "").strip().upper()
    elif "localisation" in data:
        out["localisation"] = (data.get("localisation") or "").strip().upper()
    elif "location" in data:
        out["localisation"] = (data.get("location") or "").strip().upper()

    # assigned_to (person) - if present
    if "assigned_to" in data:
        out["assigned_to"] = (data.get("assigned_to") or "").strip()

    # warranty_date -> warranty_expiration (expecting YYYY-MM-DD or empty)
    if "warranty_date" in data:
        wd = data.get("warranty_date") or ""
        out["warranty_expiration"] = wd if wd != "" else None
    elif "warranty_expiration" in data:
        out["warranty_expiration"] = data.get("warranty_expiration")

    # status cleanup
    if "status" in data:
        out["status"] = _sanitize_status(data.get("status"))
    elif "state" in data:
        out["status"] = _sanitize_status(data.get("state"))

    # battery_health, purchase_date, notes
    if "battery_health" in data:
        try:
            out["battery_health"] = int(data.get("battery_health"))
        except Exception:
            out["battery_health"] = None

    if "purchase_date" in data:
        out["purchase_date"] = data.get("purchase_date")

    if "notes" in data:
        out["notes"] = data.get("notes")

    return out


# ---------- CRUD operations ----------------------------------------------------
def list_tools(filters: Optional[Dict[str, Sequence[str]]] = None, limit: Optional[int] = 200) -> List[Dict[str, Any]]:
    """
    Lister les outils avec filtres simples.
    filters example (from FilterWindow): {"status": ["Active","Available"], "category": [...], "location": [...]}
    """
    base_sql = "SELECT * FROM tools"
    clauses: List[str] = []
    params: List[Any] = []

    if filters:
        # status filter: map values to DB-normalized statuses
        if "status" in filters and filters["status"]:
            statuses = [_sanitize_status(s) for s in filters["status"]]
            statuses = [s for s in statuses if s]
            if statuses:
                placeholders = ",".join("?" for _ in statuses)
                clauses.append(f"status IN ({placeholders})")
                params.extend(statuses)

        # category -> type
        if "category" in filters and filters["category"]:
            cats = [str(c).strip() for c in filters["category"] if c]
            if cats:
                placeholders = ",".join("?" for _ in cats)
                clauses.append(f"type IN ({placeholders})")
                params.extend(cats)

        # location -> localisation
        if "location" in filters and filters["location"]:
            locs = [str(l).strip() for l in filters["location"] if l]
            if locs:
                placeholders = ",".join("?" for _ in locs)
                clauses.append(f"localisation IN ({placeholders})")
                params.extend(locs)

        # text search (optional)
        if "q" in filters and filters["q"]:
            q = f"%{filters['q']}%"
            clauses.append("(name LIKE ? OR brand LIKE ? OR serial_number LIKE ? OR product_id LIKE ?)")
            params.extend([q, q, q, q])

    if clauses:
        base_sql += " WHERE " + " AND ".join(clauses)

    base_sql += " ORDER BY created_at DESC"
    if limit:
        base_sql += f" LIMIT {int(limit)}"

    try:
        # Strict enforcement for IT_TECHNICIAN
        from controllers import settings_controller
        user_role = str(settings_controller.get_user_role()).upper()
        is_technician = user_role in ["IT_TECHNICIAN", "IT_TECHNICIEN"]
        
        if is_technician:
            # Start with MAINTENANCE status
            it_clauses = ["status = 'MAINTENANCE'"]
            it_params = []
            
            # Re-add text search if present
            if filters and "q" in filters and filters["q"]:
                q = f"%{filters['q']}%"
                it_clauses.append("(name LIKE ? OR brand LIKE ? OR serial_number LIKE ? OR product_id LIKE ?)")
                it_params.extend([q, q, q, q])
            
            base_sql = "SELECT * FROM tools WHERE " + " AND ".join(it_clauses)
            base_sql += " ORDER BY created_at DESC"
            if limit:
                base_sql += f" LIMIT {int(limit)}"
            params = it_params

        rows = dbwrapper.fetchall(base_sql, tuple(params))
        return rows
    except Exception:
        logger.exception("list_tools failed")
        return []


def get_tool(tool_id: int) -> Optional[Dict[str, Any]]:
    try:
        tool = dbwrapper.fetchone("SELECT * FROM tools WHERE id = ?;", (tool_id,))
        
        # Strict enforcement for IT_TECHNICIAN
        from controllers import settings_controller
        user_role = str(settings_controller.get_user_role()).upper()
        is_technician = user_role in ["IT_TECHNICIAN", "IT_TECHNICIEN"]
        if is_technician and tool and tool.get("status") != "MAINTENANCE":
            logger.warning(f"IT_TECHNICIAN attempted to access tool {tool_id} with status {tool.get('status')}")
            return None
            
        return tool
    except Exception:
        logger.exception(f"get_tool failed for id={tool_id}")
        return None


def create_tool(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Crée un enregistrement dans tools.
    Attends le dictionnaire provenant du formulaire AddEquipmentWindow.
    """
    # Strict enforcement for IT_TECHNICIAN
    from controllers import settings_controller
    user_role = str(settings_controller.get_user_role()).upper()
    is_technician = user_role in ["IT_TECHNICIAN", "IT_TECHNICIEN"]
    if is_technician:
        raise PermissionError("IT_TECHNICIAN is not allowed to create tools")

    mapped = _map_input_to_db_fields(data)

    # Champs requis check minimal
    if not mapped.get("name"):
        raise ValueError("Missing product name (asset_model).")
    if not mapped.get("brand"):
        raise ValueError("Missing brand.")
    if not mapped.get("serial_number"):
        raise ValueError("Missing serial_number.")

    sql = """
    INSERT INTO tools
      (name, brand, product_id, serial_number, type, localisation, status, warranty_expiration, battery_health, assigned_to, purchase_date, notes)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """
    params = (
        mapped.get("name"),
        mapped.get("brand"),
        mapped.get("product_id"),
        mapped.get("serial_number"),
        mapped.get("type") or "UNCATEGORIZED",
        mapped.get("localisation"),
        mapped.get("status") or "AVAILABLE",
        mapped.get("warranty_expiration"),
        mapped.get("battery_health"),
        mapped.get("assigned_to"),
        mapped.get("purchase_date"),
        mapped.get("notes"),
    )

    try:
        new_id = dbwrapper.execute(sql, params)
        # Fetch and return the created record
        created = get_tool(new_id)
        
        # Send email notification
        if created:
            user_name = settings_controller.get_user_display_name()
            details = (
                f"Created by: {user_name}\n"
                f"Item Name: {created.get('name', 'Unknown')}\n"
                f"Item ID/SN: {created.get('serial_number', str(new_id))}\n"
                f"Brand: {created.get('brand', 'N/A')}\n"
                f"Type: {created.get('type', 'N/A')}\n"
                f"Initial Status: {created.get('status', 'AVAILABLE')}"
            )
            notification_service.send_inventory_notification(
                action="ADD",
                item_name=created.get("name", "Unknown"),
                item_id=created.get("serial_number", str(new_id)),
                details=details
            )

        # Optionally log history
        try:
            add_history_entry(new_id, "CREATE", None, str(created))
        except Exception:
            logger.debug("Could not insert history entry for create (non-fatal).")
        return created or {}
    except sqlite3.IntegrityError as e:
        # Duplicate serial number etc.
        logger.exception("Integrity error creating tool: %s", e)
        raise ValueError(f"Database integrity error: {e}")
    except Exception:
        logger.exception("create_tool failed")
        raise


def update_tool(tool_id: int, data: Dict[str, Any], silent: bool = False) -> Dict[str, Any]:
    """
    Met à jour un outil. Ne met à jour que les champs présents dans `data`.
    Retourne l'enregistrement mis à jour.
    """
    from controllers import settings_controller
    user_role = str(settings_controller.get_user_role()).upper()
    is_technician = user_role in ["IT_TECHNICIAN", "IT_TECHNICIEN"]
    
    old = get_tool(tool_id)
    mapped = _map_input_to_db_fields(data)
    
    if is_technician:
        # They can only update 'status'
        if any(k != "status" for k in mapped.keys()):
            raise PermissionError("IT_TECHNICIAN can only update the 'status' field")
            
        # They can only update if OLD status is MAINTENANCE
        if old and old.get("status") != "MAINTENANCE":
            raise PermissionError("IT_TECHNICIAN can only update tools with status 'MAINTENANCE'")
            
        # They can only update status to: ACTIVE, AVAILABLE, LENT OUT
        new_status = mapped.get("status")
        if new_status not in {"ACTIVE", "AVAILABLE", "LENT OUT"}:
            raise PermissionError("IT_TECHNICIAN can only update status to ACTIVE, AVAILABLE, or LENT OUT")
            
    if not mapped:
        return old or {}

    # Construire SET clause dynamiquement
    set_parts: List[str] = []
    params: List[Any] = []
    for k, v in mapped.items():
        # sécuriser les colonnes autorisées
        if k not in {"name", "brand", "product_id", "serial_number", "type", "localisation", "status", "warranty_expiration", "battery_health", "assigned_to", "purchase_date", "notes"}:
            continue
        set_parts.append(f"{k} = ?")
        params.append(v)

    if not set_parts:
        return old or {}

    params.append(tool_id)
    sql = f"UPDATE tools SET {', '.join(set_parts)} WHERE id = ?;"

    try:
        dbwrapper.execute(sql, tuple(params))
        # Bypass role-based get_tool to ensure we can send notification even if item is now hidden
        updated = dbwrapper.fetchone("SELECT * FROM tools WHERE id = ?;", (tool_id,))
        
        # Send email notification (if not silent)
        if not silent and updated and old:
            changed_fields = []
            for key, new_val in updated.items():
                if key in old and old[key] != new_val and key not in ['updated_at', 'created_at']:
                    changed_fields.append(f"{key}: {old[key]} -> {new_val}")
            
            if changed_fields:
                user_name = settings_controller.get_user_display_name()
                
                # Format a more detailed description for the CEO
                details = (
                    f"Modified by: {user_name}\n"
                    f"Item Name: {updated.get('name', 'Unknown')}\n"
                    f"Item ID/SN: {updated.get('serial_number', str(tool_id))}\n"
                    f"Brand/Type: {updated.get('brand', 'N/A')} / {updated.get('type', 'N/A')}\n"
                    f"\n--- CHANGES ---\n" + 
                    "\n".join(changed_fields)
                )
                
                notification_service.send_inventory_notification(
                    action="UPDATE",
                    item_name=updated.get("name", "Unknown"),
                    item_id=updated.get("serial_number", str(tool_id)),
                    details=details
                )

        # Log changes to history
        # but we keep a generic history entry)
        try:
            add_history_entry(tool_id, "UPDATE", str(old), str(updated))
        except Exception:
            logger.debug("Could not insert history entry for update (non-fatal).")
        return updated or {}
    except Exception:
        logger.exception("update_tool failed for id=%s", tool_id)
        raise


def delete_tool(tool_id: int, silent: bool = False) -> bool:
    from controllers import settings_controller
    user_role = str(settings_controller.get_user_role()).upper()
    is_technician = user_role in ["IT_TECHNICIAN", "IT_TECHNICIEN"]
    if is_technician:
        raise PermissionError("IT_TECHNICIAN is not allowed to delete tools")

    try:
        # Optionally fetch record for logging
        old = get_tool(tool_id)
        
        # Send email notification (if not silent)
        if not silent and old:
            user_name = settings_controller.get_user_display_name()
            details = (
                f"Deleted by: {user_name}\n"
                f"Item Name: {old.get('name', 'Unknown')}\n"
                f"Item ID/SN: {old.get('serial_number', str(tool_id))}\n"
                f"Brand: {old.get('brand', 'N/A')}\n"
                f"Type: {old.get('type', 'N/A')}\n"
                f"Status before deletion: {old.get('status', 'N/A')}"
            )
            notification_service.send_inventory_notification(
                action="DELETE",
                item_name=old.get("name", "Unknown"),
                item_id=old.get("serial_number", str(tool_id)),
                details=details
            )

        dbwrapper.execute("DELETE FROM tools WHERE id = ?;", (tool_id,))
        try:
            add_history_entry(tool_id, "DELETE", str(old), None)
        except Exception:
            logger.debug("Could not insert history entry for delete (non-fatal).")
        return True
    except Exception:
        logger.exception("delete_tool failed for id=%s", tool_id)
        return False


# ---------- History / Meta ----------------------------------------------------
def get_history(tool_id: Optional[int] = None, limit: int = 200) -> List[Dict[str, Any]]:
    sql = "SELECT * FROM history"
    params: List[Any] = []
    if tool_id:
        sql += " WHERE tool_id = ?"
        params.append(tool_id)
    sql += " ORDER BY changed_at DESC"
    if limit:
        sql += f" LIMIT {int(limit)}"
    try:
        return dbwrapper.fetchall(sql, tuple(params))
    except Exception:
        logger.exception("get_history failed")
        return []


def add_history_entry(tool_id: int, action: str, old_value: Optional[str], new_value: Optional[str], changed_by: Optional[str] = None) -> int:
    """
    Ajoute une entrée manuelle dans la table history.
    Note: certains changements (status, assigned_to) sont automatiquement loggés par triggers;
    utiliser cette fonction pour actions personnalisées.
    """
    sql = """
    INSERT INTO history (tool_id, action, old_value, new_value, changed_by)
    VALUES (?, ?, ?, ?, ?);
    """
    params = (tool_id, action, old_value, new_value, changed_by)
    return dbwrapper.execute(sql, params)


# ---------- Categories / Locations helpers -----------------------------------
def list_categories() -> List[Dict[str, Any]]:
    try:
        return dbwrapper.fetchall("SELECT * FROM categories ORDER BY name;")
    except Exception:
        logger.exception("list_categories failed")
        return []


def list_locations() -> List[Dict[str, Any]]:
    try:
        return dbwrapper.fetchall("SELECT * FROM locations ORDER BY name;")
    except Exception:
        logger.exception("list_locations failed")
        return []


# ---------- Rooms / Capacity functions -----------------------------------
def list_rooms() -> List[Dict[str, Any]]:
    """
    Liste toutes les rooms avec leur capacité.
    """
    try:
        return dbwrapper.fetchall("SELECT * FROM rooms ORDER BY name;")
    except Exception:
        logger.exception("list_rooms failed")
        return []


def get_room(room_name: str) -> Optional[Dict[str, Any]]:
    """
    Récupère une room par son nom.
    """
    try:
        return dbwrapper.fetchone("SELECT * FROM rooms WHERE name = ?;", (room_name,))
    except Exception:
        logger.exception("get_room failed for %s", room_name)
        return None


def create_room(name: str, icon: str = "building", max_capacity: int = 10, room_type: str = "office") -> Dict[str, Any]:
    """
    Crée une nouvelle room.
    """
    try:
        sql = """
        INSERT INTO rooms (name, icon, max_capacity, room_type)
        VALUES (?, ?, ?, ?);
        """
        dbwrapper.execute(sql, (name, icon, max_capacity, room_type))
        return get_room(name) or {}
    except Exception:
        logger.exception("create_room failed for %s", name)
        return {}


def update_room_capacity(room_name: str, new_capacity: int) -> bool:
    """
    Met à jour la capacité maximale d'une room.
    """
    try:
        sql = "UPDATE rooms SET max_capacity = ? WHERE name = ?;"
        dbwrapper.execute(sql, (new_capacity, room_name))
        logger.info(f"Capacité mise à jour pour {room_name}: {new_capacity}")
        return True
    except Exception:
        logger.exception("update_room_capacity failed for %s", room_name)
        return False


def update_room(room_name: str, data: Dict[str, Any]) -> bool:
    """
    Met à jour les informations d'une room.
    """
    try:
        allowed_fields = {"icon", "max_capacity", "room_type"}
        set_parts = []
        params = []
        
        for k, v in data.items():
            if k in allowed_fields:
                set_parts.append(f"{k} = ?")
                params.append(v)
        
        if not set_parts:
            return False
        
        params.append(room_name)
        sql = f"UPDATE rooms SET {', '.join(set_parts)} WHERE name = ?;"
        dbwrapper.execute(sql, tuple(params))
        return True
    except Exception:
        logger.exception("update_room failed for %s", room_name)
        return False


def delete_room(room_name: str) -> bool:
    """
    Supprime une room.
    """
    try:
        dbwrapper.execute("DELETE FROM rooms WHERE name = ?;", (room_name,))
        return True
    except Exception:
        logger.exception("delete_room failed for %s", room_name)
        return False


def migrate_office_room_names() -> bool:
    """
    Migration "soft" des noms de bureaux.

    Mapping demandé:
    - BOSS BUREAU -> CEO BUREAU
    - CEO BUREAU  -> ADMINISTRATION

    Applique aussi la mise à jour dans la table `tools` (colonne `localisation`)
    et (si présente) la table `locations`.
    Idempotent: si aucune ancienne valeur n'existe, ne fait rien.
    """
    old_boss = "BOSS BUREAU"
    old_ceo = "CEO BUREAU"
    new_ceo = "CEO BUREAU"
    new_admin = "ADMINISTRATION"
    tmp = "__TMP_BOSS_BUREAU__"

    try:
        # Détecter si la migration est nécessaire
        needs = False
        try:
            r1 = dbwrapper.fetchone("SELECT 1 FROM rooms WHERE name IN (?, ?) LIMIT 1;", (old_boss, old_ceo))
            t1 = dbwrapper.fetchone("SELECT 1 FROM tools WHERE localisation IN (?, ?) LIMIT 1;", (old_boss, old_ceo))
            needs = bool(r1 or t1)
        except Exception:
            # Si la requête de détection échoue, on tente quand même la migration
            needs = True

        if not needs:
            return True

        # --- rooms ---
        dbwrapper.execute("UPDATE rooms SET name = ? WHERE name = ?;", (tmp, old_boss))
        dbwrapper.execute("UPDATE rooms SET name = ? WHERE name = ?;", (new_admin, old_ceo))
        dbwrapper.execute("UPDATE rooms SET name = ? WHERE name = ?;", (new_ceo, tmp))

        # --- tools.localisation ---
        dbwrapper.execute("UPDATE tools SET localisation = ? WHERE localisation = ?;", (tmp, old_boss))
        dbwrapper.execute("UPDATE tools SET localisation = ? WHERE localisation = ?;", (new_admin, old_ceo))
        dbwrapper.execute("UPDATE tools SET localisation = ? WHERE localisation = ?;", (new_ceo, tmp))

        # --- locations table (optional) ---
        try:
            dbwrapper.execute("UPDATE locations SET name = ? WHERE name = ?;", (tmp, old_boss))
            dbwrapper.execute("UPDATE locations SET name = ? WHERE name = ?;", (new_admin, old_ceo))
            dbwrapper.execute("UPDATE locations SET name = ? WHERE name = ?;", (new_ceo, tmp))
        except Exception:
            # Table peut ne pas exister selon la version DB
            pass

        return True
    except Exception:
        logger.exception("migrate_office_room_names failed")
        return False