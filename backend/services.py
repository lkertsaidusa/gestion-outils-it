
from typing import Any, Dict, List, Optional, Sequence, Tuple
import logging
from datetime import datetime, timedelta, date

from backend import models
from database import database as dbwrapper

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


# Mapping couleurs pour le donut/status breakdown (utilisé par DashboardView)
_STATUS_COLORS = {
    "ACTIVE": "#10B981",
    "AVAILABLE": "#3B82F6",
    "MAINTENANCE": "#F59E0B",
    "LENT OUT": "#EF4444",
    # fallback color
    "UNKNOWN": "#9CA3AF",
}


# Petite map category -> icon_name pour l'UI (cohérent avec InventoryView._get_icon_from_category)
_CATEGORY_ICONS = {
    "PC": "monitor",
    "PRINTER": "printer",
    "PHONE": "smartphone",
    "STORAGE": "server",
    "MONITOR": "monitor",
    "KEYBOARD": "keyboard",
    "SERVER": "server",
    "SMARTPHONE": "smartphone",
    "TABLET": "monitor",
    "ACCESSOIRE": "archive",
}


def normalize_filters(filters: Optional[Dict[str, Sequence[str]]]) -> Dict[str, Sequence[str]]:
    """
    Normalise les filtres reçus depuis l'UI vers la forme attendue par models.list_tools.
    - statut -> valeurs normalisées (ACTIVE, AVAILABLE, MAINTENANCE, LENT OUT)
    - category -> pass-through (strip/upper)
    - location/location -> pass-through (strip)
    - q -> full-text query
    """
    if not filters:
        return {}

    out: Dict[str, Sequence[str]] = {}

    # Status
    if "status" in filters:
        raw_statuses = filters.get("status") or []
        normalized = []
        for s in raw_statuses:
            ns = models._sanitize_status(s) if hasattr(models, "_sanitize_status") else (str(s).upper().strip())
            if ns:
                normalized.append(ns)
        if normalized:
            out["status"] = normalized

    # Category (map to DB 'type')
    if "category" in filters:
        cats = [str(c).strip().upper() for c in filters.get("category") or [] if c]
        if cats:
            out["category"] = cats

    # Location
    if "location" in filters:
        locs = [str(l).strip() for l in filters.get("location") or [] if l]
        if locs:
            out["location"] = locs

    # Free text q
    if "q" in filters and filters.get("q"):
        out["q"] = filters.get("q")

    return out


def get_overview_stats() -> Dict[str, int]:
    """
    Retourne des statistiques agrégées pour le dashboard.
    - total_assets
    - active_units
    - warranty_alerts (expirations dans les next 30 days)
    - lent_out_assets
    """
    stats = {
        "total_assets": 0,
        "active_units": 0,
        "warranty_alerts": 0,
        "lent_out_assets": 0,
    }

    try:
        row = dbwrapper.fetchone("SELECT COUNT(*) as cnt FROM tools;")
        if row:
            stats["total_assets"] = int(row.get("cnt", 0))

        row = dbwrapper.fetchone("SELECT COUNT(*) as cnt FROM tools WHERE status = 'ACTIVE';")
        if row:
            stats["active_units"] = int(row.get("cnt", 0))

        row = dbwrapper.fetchone("SELECT COUNT(*) as cnt FROM tools WHERE status = 'LENT OUT';")
        if row:
            stats["lent_out_assets"] = int(row.get("cnt", 0))

        # warranty alerts: expirations within next 30 days (including past due)
        # Using SQLite date function via SQL
        try:
            row = dbwrapper.fetchone(
                "SELECT COUNT(*) as cnt FROM tools WHERE warranty_expiration IS NOT NULL AND DATE(warranty_expiration) <= DATE('now', '+30 day');"
            )
            if row:
                stats["warranty_alerts"] = int(row.get("cnt", 0))
        except Exception:
            # Fallback: load in python and compute (slower)
            tools = models.list_tools(limit=None)
            now = datetime.utcnow().date()
            warn_count = 0
            for t in tools:
                we = t.get("warranty_expiration")
                if not we:
                    continue
                try:
                    d = datetime.strptime(we, "%Y-%m-%d").date()
                    if d <= (now + timedelta(days=30)):
                        warn_count += 1
                except Exception:
                    continue
            stats["warranty_alerts"] = warn_count

    except Exception:
        logger.exception("Failed to compute overview stats")

    return stats


def get_equipment_distribution(limit: int = 12) -> Dict[str, int]:
    """
    Renvoie un dict {category/type: count} trié par count décroissant (limité).
    Utilisé par BarChart.
    """
    try:
        rows = dbwrapper.fetchall(
            "SELECT type as category, COUNT(*) as cnt FROM tools GROUP BY type ORDER BY cnt DESC LIMIT ?;",
            (int(limit),),
        )
        out: Dict[str, int] = {}
        for r in rows:
            key = r.get("category") or "UNCATEGORIZED"
            out[key] = int(r.get("cnt", 0))
        return out
    except Exception:
        logger.exception("get_equipment_distribution failed")
        return {}


def get_status_breakdown() -> List[Tuple[str, int, str]]:
    """
    Renvoie une liste de tuples (label, count, color) pour le donut chart.
    Ordre: ACTIVE, AVAILABLE, MAINTENANCE, LENT OUT
    """
    order = ["ACTIVE", "AVAILABLE", "MAINTENANCE", "LENT OUT"]
    results: List[Tuple[str, int, str]] = []
    try:
        rows = dbwrapper.fetchall("SELECT status, COUNT(*) as cnt FROM tools GROUP BY status;")
        counts = {r.get("status") or "UNKNOWN": int(r.get("cnt", 0)) for r in rows}
        for st in order:
            results.append((st, counts.get(st, 0), _STATUS_COLORS.get(st, _STATUS_COLORS["UNKNOWN"])))
        # include any unknown statuses if present
        for k, v in counts.items():
            if k not in order:
                results.append((k, v, _STATUS_COLORS.get(k, _STATUS_COLORS["UNKNOWN"])))
    except Exception:
        logger.exception("get_status_breakdown failed")
    return results


def get_tools_grouped_by_location(limit: Optional[int] = None) -> Dict[str, List[Dict[str, Any]]]:
    """
    Retourne un mapping localisation -> liste d'outils (dicts).
    Utile pour FacilityMapView.
    """
    try:
        tools = models.list_tools(filters=None, limit=limit)
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for t in tools:
            loc = t.get("localisation") or "UNASSIGNED"
            grouped.setdefault(loc, []).append(t)
        return grouped
    except Exception:
        logger.exception("get_tools_grouped_by_location failed")
        return {}


def get_tools_nearing_warranty(days: int = 30, limit: Optional[int] = 100) -> List[Dict[str, Any]]:
    """
    Récupère les outils dont la warranty_expiration est dans les `days` prochains (incl).
    """
    try:
        sql = """
        SELECT * FROM tools
        WHERE warranty_expiration IS NOT NULL
          AND DATE(warranty_expiration) <= DATE('now', ?)
        ORDER BY DATE(warranty_expiration) ASC
        """
        param = f"+{int(days)} day"
        rows = dbwrapper.fetchall(sql, (param,))
        if limit:
            return rows[:limit]
        return rows
    except Exception:
        logger.exception("get_tools_nearing_warranty failed")
        return []


# ==================== NOUVELLES FONCTIONS POUR WARRANTY EXPIRATION ====================

def is_warranty_expiring_soon(warranty_date_str: str, threshold_days: int = 60) -> bool:
    """
    Vérifie si une date de garantie expire dans les prochains `threshold_days` jours.
    
    Args:
        warranty_date_str: Date au format "YYYY-MM-DD" ou None
        threshold_days: Nombre de jours avant expiration pour déclencher l'alerte (défaut: 60 = ~2 mois)
    
    Returns:
        True si la garantie expire dans moins de `threshold_days` jours, False sinon
    """
    if not warranty_date_str:
        return False
    
    try:
        warranty_date = datetime.strptime(warranty_date_str, "%Y-%m-%d").date()
        today = datetime.now().date()
        days_remaining = (warranty_date - today).days
        
        # Retourne True si expire bientôt (dans les threshold_days prochains jours)
        # Inclut aussi les garanties déjà expirées (days_remaining < 0)
        return days_remaining <= threshold_days
        
    except (ValueError, TypeError):
        return False


def format_warranty_date_for_ui(warranty_date_input) -> Dict[str, Any]:
    """
    Formate une date de garantie pour l'affichage UI avec détection d'expiration.
    
    Args:
        warranty_date_input: Peut être:
            - Un objet datetime.date (retourné par SQLite)
            - Une string au format "YYYY-MM-DD"
            - None
    
    Returns:
        dict avec:
        - "display_date": Date formatée pour affichage (ex: "25/04/2027")
        - "is_expiring": True si expire dans les 60 prochains jours
        - "is_expired": True si déjà expirée
        - "days_remaining": Nombre de jours restants
    """
    # CAS 1: None ou vide
    if warranty_date_input is None or warranty_date_input == "":
        return {
            "display_date": "N/A",
            "is_expiring": False,
            "is_expired": False,
            "days_remaining": None
        }
    
    # CAS 2: Déjà un objet date (retourné par SQLite)
    if isinstance(warranty_date_input, date):
        warranty_date = warranty_date_input
    
    # CAS 3: C'est une string
    elif isinstance(warranty_date_input, str):
        warranty_date_str = warranty_date_input.strip()
        
        if not warranty_date_str or warranty_date_str.upper() in ["NONE", "NULL"]:
            return {
                "display_date": "N/A",
                "is_expiring": False,
                "is_expired": False,
                "days_remaining": None
            }
        
        try:
            # Essayer format YYYY-MM-DD (format SQLite standard)
            warranty_date = datetime.strptime(warranty_date_str, "%Y-%m-%d").date()
        except ValueError:
            try:
                # Essayer format DD/MM/YYYY
                warranty_date = datetime.strptime(warranty_date_str, "%d/%m/%Y").date()
            except ValueError:
                return {
                    "display_date": "INVALID DATE",
                    "is_expiring": False,
                    "is_expired": False,
                    "days_remaining": None
                }
    
    # CAS 4: Type non supporté
    else:
        return {
            "display_date": f"INVALID TYPE: {type(warranty_date_input).__name__}",
            "is_expiring": False,
            "is_expired": False,
            "days_remaining": None
        }
    
    # Calcul du statut
    try:
        today = datetime.now().date()
        days_remaining = (warranty_date - today).days
        
        # Formatter la date en DD/MM/YYYY
        display_date = warranty_date.strftime("%d/%m/%Y")
        
        is_expired = days_remaining < 0
        is_expiring = 0 <= days_remaining <= 60  # 60 jours = ~2 mois
        
        return {
            "display_date": display_date,
            "is_expiring": is_expiring,
            "is_expired": is_expired,
            "days_remaining": days_remaining
        }
    
    except Exception as e:
        return {
            "display_date": f"ERROR: {str(e)[:30]}",
            "is_expiring": False,
            "is_expired": False,
            "days_remaining": None
        }

# ======================================================================================


def format_tool_for_ui(tool: Dict[str, Any]) -> Dict[str, Any]:
    """
    Prépare et normalise un enregistrement 'tool' pour l'affichage côté UI.
    Retour attendu par InventoryView (approximatif) :
    {
        "icon": "monitor",
        "name": "SURFACE LAPTOP",
        "serial": "SN-001239-X",
        "id": "#ID213F0G",
        "brand": "MICROSOFT",
        "category": "PC",
        "location": "OFFICE 201",
        "status": "•  ACTIVE",
        "warranty_expiration": {...}  [NOUVEAU]
    }
    """
    if not tool:
        return {}

    name = (tool.get("name") or "").upper()
    brand = (tool.get("brand") or "").upper()
    serial = (tool.get("serial_number") or "").upper()
    product_id = tool.get("product_id") or tool.get("id")  # fallback
    display_id = f"#ID{(serial or '')[:6].upper()}" if serial else (f"#{tool.get('id')}" if tool.get("id") else "")

    category = (tool.get("type") or "UNCATEGORIZED").upper()
    location = (tool.get("localisation") or "").upper()

    status_raw = (tool.get("status") or "").upper()
    status_norm = status_raw.strip()
    if status_norm and not status_norm.startswith("•"):
        display_status = f"•  {status_norm}"
    else:
        display_status = status_norm or "•  AVAILABLE"

    icon = _CATEGORY_ICONS.get(category.upper(), "monitor")

    # ==================== NOUVELLE PARTIE: WARRANTY EXPIRATION ====================
    warranty_date_str = tool.get("warranty_expiration")
    warranty_info = format_warranty_date_for_ui(warranty_date_str)
    # ==============================================================================

    return {
        "icon": icon,
        "name": name,
        "serial": serial,
        "id": display_id,
        "brand": brand,
        "category": category,
        "location": location,
        "status": display_status,
        "warranty_expiration": warranty_info,  # ← NOUVELLE CLÉ AJOUTÉE
        "raw": tool,  # keep original record for reference if needed
    }


# Convenience functions delegating to models for direct CRUD usage
def create_tool(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validation légère puis délégation à models.create_tool"""
    # Basic validation can be extended here
    if not data.get("asset_model") and not data.get("name"):
        raise ValueError("asset_model (name) is required")
    if not data.get("brand"):
        raise ValueError("brand is required")
    if not data.get("serial_number"):
        raise ValueError("serial_number is required")
    # Normalize status if present
    if "status" in data and data["status"]:
        if hasattr(models, "_sanitize_status"):
            data["status"] = models._sanitize_status(data["status"])
    return models.create_tool(data)


def list_tools(filters: Optional[Dict[str, Sequence[str]]] = None, limit: Optional[int] = 200) -> List[Dict[str, Any]]:
    """
    Applique la normalisation des filtres puis appelle models.list_tools.
    Retourne la liste d'enregistrements bruts (dicts DB). Les vues peuvent utiliser format_tool_for_ui.
    """
    normalized = normalize_filters(filters or {})
    return models.list_tools(filters=normalized, limit=limit)