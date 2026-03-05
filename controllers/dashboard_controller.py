"""
controllers/dashboard_controller.py
Façade entre les vues (UI) et la logique métier (backend.services / backend.models).

Fournit des fonctions simples et sûres pour récupérer les données
formatées pour les composants de la dashboard (stat cards, bar chart, donut chart, etc.).
"""

from typing import Any, Dict, List, Tuple
import logging

from backend import services, models
from database import database as dbwrapper

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


def get_overview_stats() -> Dict[str, int]:
    """
    Retourne les statistiques principales utilisées par la dashboard.
    Format:
      {
        "total_assets": int,
        "active_units": int,
        "warranty_alerts": int,
        "lent_out_assets": int
      }
    """
    try:
        from controllers import settings_controller
        if settings_controller.get_user_role() == "IT_TECHNICIAN":
            return {"total_assets": 0, "active_units": 0, "warranty_alerts": 0, "lent_out_assets": 0}
            
        stats = services.get_overview_stats()
        return stats
    except Exception:
        logger.exception("Failed to get overview stats")
        return {
            "total_assets": 0,
            "active_units": 0,
            "warranty_alerts": 0,
            "lent_out_assets": 0,
        }


def get_bar_chart_data(limit: int = 12) -> Dict[str, int]:
    """
    Retourne un dictionnaire {category: count} trié par count décroissant,
    utilisable directement avec BarChart (qui accepte un dict).
    """
    try:
        from controllers import settings_controller
        if settings_controller.get_user_role() == "IT_TECHNICIAN":
            return {}
            
        return services.get_equipment_distribution(limit=limit)
    except Exception:
        logger.exception("Failed to get bar chart data")
        return {}


def get_donut_chart_data() -> List[Tuple[str, int, str]]:
    """
    Retourne la liste de tuples (label, value, color) pour le DonutChart.
    Exemple: [("ACTIVE", 10, "#10B981"), ...]
    """
    try:
        from controllers import settings_controller
        if settings_controller.get_user_role() == "IT_TECHNICIAN":
            return []
            
        return services.get_status_breakdown()
    except Exception:
        logger.exception("Failed to donut chart data")
        return []


def get_battery_hub_items(threshold: int = 80, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Retourne une liste d'outils ayant battery_health < threshold.
    Chaque item est un dict raw DB row ; les vues peuvent appeler services.format_tool_for_ui.
    """
    try:
        from controllers import settings_controller
        if settings_controller.get_user_role() == "IT_TECHNICIAN":
            return []
            
        rows = dbwrapper.fetchall(
            "SELECT * FROM tools WHERE battery_health IS NOT NULL AND battery_health < ? ORDER BY battery_health ASC LIMIT ?;",
            (int(threshold), int(limit)),
        )
        return rows
    except Exception:
        logger.exception("Failed to query battery hub items")
        return []


def get_repair_hub_items(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Retourne les outils en maintenance (status = 'MAINTENANCE').
    """
    try:
        from controllers import settings_controller
        if settings_controller.get_user_role() == "IT_TECHNICIAN":
            return []
            
        rows = dbwrapper.fetchall(
            "SELECT * FROM tools WHERE status = 'MAINTENANCE' ORDER BY updated_at DESC LIMIT ?;",
            (int(limit),),
        )
        return rows
    except Exception:
        logger.exception("Failed to query repair hub items")
        return []


def get_critical_supplies(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Retourne les consommables en stock critique (in_storage < limit_alert).
    """
    try:
        from controllers import settings_controller
        if settings_controller.get_user_role() == "IT_TECHNICIAN":
            return []
            
        rows = dbwrapper.fetchall(
            "SELECT * FROM supplies WHERE in_storage < limit_alert ORDER BY in_storage ASC LIMIT ?;",
            (int(limit),),
        )
        return rows
    except Exception:
        logger.exception("Failed to query critical supplies")
        return []


def get_intelligence_feed(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Retourne les zones avec occupation HIGH (saturées) pour les alertes actives.
    Ne montre que les chambres/zones qui ont atteint le seuil HIGH (>= 90% de capacité).
    """
    try:
        from controllers import settings_controller
        if settings_controller.get_user_role() == "IT_TECHNICIAN":
            return []
            
        # Importer le map_controller pour récupérer les données d'occupation
        from controllers import map_controller
        
        # Récupérer toutes les zones avec leurs données d'occupation
        facility_data = map_controller.get_facility_data()
        
        # Filtrer les zones en HIGH ou CRITICAL occupancy (>= 90%)
        saturated_zones = [
            zone for zone in facility_data 
            if zone.get("occupancy_status") in ["HIGH", "CRITICAL"]
        ]
        
        # Trier par nombre d'items (du plus haut au plus bas)
        saturated_zones.sort(key=lambda x: x.get("total_items", 0), reverse=True)
        
        # Limiter le nombre de résultats
        saturated_zones = saturated_zones[:limit]
        
        # Formater pour l'affichage dans le dashboard
        feed = []
        for zone in saturated_zones:
            feed.append({
                "location": zone.get("name", "UNKNOWN"),
                "count": zone.get("total_items", 0),
                "max_capacity": zone.get("max_capacity", 0),
                "occupancy_status": zone.get("occupancy_status", "UNKNOWN")
            })
        
        logger.info(f"Intelligence feed: {len(feed)} saturated zones found")
        return feed
        
    except Exception:
        logger.exception("Failed to build intelligence feed")
        return []


def get_dashboard_payload() -> Dict[str, Any]:
    """
    Combine les différentes sources de données en une seule payload prête pour la DashboardView.
    Format:
      {
        "stats": {...},
        "bar_data": {...},
        "donut_data": [...],
        "battery_hub": [...],
        "repair_hub": [...],
        "intelligence_feed": [...]
      }
    """
    try:
        from controllers import settings_controller
        if settings_controller.get_user_role() == "IT_TECHNICIAN":
            return {
                "stats": {}, "bar_data": {}, "donut_data": [],
                "battery_hub": [], "repair_hub": [], "intelligence_feed": []
            }
            
        payload = {
            "stats": get_overview_stats(),
            "bar_data": get_bar_chart_data(),
            "donut_data": get_donut_chart_data(),
            "battery_hub": [services.format_tool_for_ui(t) for t in get_battery_hub_items()],
            "repair_hub": [services.format_tool_for_ui(t) for t in get_repair_hub_items()],
            "intelligence_feed": get_intelligence_feed(),
        }
        return payload
    except Exception:
        logger.exception("Failed to assemble dashboard payload")
        return {
            "stats": {},
            "bar_data": {},
            "donut_data": [],
            "battery_hub": [],
            "repair_hub": [],
            "intelligence_feed": [],
        }