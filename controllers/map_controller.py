"""
controllers/map_controller.py

Contrôleur pour la Facility Map.
Récupère les données de la base et les organise par zone.
"""
from typing import Dict, List, Optional
import logging

from backend import services
from backend import models
from controllers import consumable_controller

logger = logging.getLogger(__name__)


# Données par défaut pour les rooms (utilisées si la base est vide)
DEFAULT_ZONES = [
    {"Name": "CEO BUREAU", "icon": "crown", "max_capacity": 2, "type": "office"},
    {"Name": "ADMINISTRATION", "icon": "command", "max_capacity": 2, "type": "office"},
    {"Name": "SECTION A", "icon": "package", "max_capacity": 70, "type": "section"},
    {"Name": "OFFICE 101", "icon": "building", "max_capacity": 5, "type": "office"},
    {"Name": "RECEPTION", "icon": "bell", "max_capacity": 3, "type": "office"},
    {"Name": "MAIN STORAGE", "icon": "package", "max_capacity": 4, "type": "storage"},
    {"Name": "SECTION B", "icon": "package", "max_capacity": 50, "type": "section"},
    {"Name": "SECTION C", "icon": "package", "max_capacity": 30, "type": "section"},
    {"Name": "SECRET ROOM", "icon": "lock", "max_capacity": 1, "type": "restricted"},
    {"Name": "UNDERGROUND", "icon": "zap", "max_capacity": 10, "type": "underground"},
]


def _ensure_rooms_exist():
    """S'assure que les rooms par défaut existent dans la base."""
    try:
        # Migration douce des noms de bureaux (pour compatibilité)
        try:
            models.migrate_office_room_names()
        except Exception:
            logger.exception("Room name migration failed")

        rooms = models.list_rooms()
        if not rooms:
            logger.info("Aucune room trouvée, création des rooms par défaut...")
            for zone in DEFAULT_ZONES:
                models.create_room(
                    name=zone["Name"],
                    icon=zone["icon"],
                    max_capacity=zone["max_capacity"],
                    room_type=zone["type"]
                )
            logger.info("Rooms par défaut créées avec succès")
    except Exception:
        logger.exception("Erreur lors de la vérification/création des rooms")


def get_facility_data() -> List[Dict]:
    """
    Récupère les données pour toutes les zones de la carte.
    
    Returns:
        Liste de dictionnaires avec les informations de chaque zone
    """
    try:
        # S'assurer que les rooms existent
        _ensure_rooms_exist()
        
        # Récupérer toutes les rooms depuis la base
        rooms = models.list_rooms()
        
        # Récupérer tous les équipements groupés par localisation
        grouped = services.get_tools_grouped_by_location(limit=None)
        
        # Role check
        from controllers import settings_controller
        user_role = settings_controller.get_user_role()
        
        facility_data = []
        
        for room in rooms:
            name = room["name"]
            equipment_raw = grouped.get(name, [])
            
            if user_role == "IT_TECHNICIAN":
                # Filter equipment to only show MAINTENANCE
                equipment_raw = [t for t in equipment_raw if t.get("status") == "MAINTENANCE"]
                consumables = [] # Hide consumables
            else:
                # Récupérer les consommables pour cette section
                consumables = consumable_controller.get_supplies_by_section(name)
            
            equipment_ui = [services.format_tool_for_ui(t) for t in equipment_raw]
            
            # Calculer le total (équipements + consommables)
            total_items = len(equipment_ui) + len(consumables)
            max_capacity = room["max_capacity"]
            
            facility_data.append({
                "name": name,
                "equipment": equipment_ui,
                "consumables": consumables,
                "max_capacity": max_capacity,
                "zone_type": room.get("room_type", "office"),
                "icon": room.get("icon", "building"),
                "total_items": total_items,
                "occupancy_status": _get_occupancy_status(total_items, max_capacity)
            })
        
        return facility_data
        
    except Exception:
        logger.exception("Failed to get facility data")
        return []


def get_room_details(room_name: str) -> Dict:
    """
    Récupère les détails d'une zone spécifique.
    
    Args:
        room_name: Nom de la zone
        
    Returns:
        Dictionnaire avec les informations de la zone
    """
    try:
        # Récupérer la room depuis la base
        room = models.get_room(room_name)
        
        if not room:
            # Si pas trouvée, essayer de la créer
            _ensure_rooms_exist()
            room = models.get_room(room_name)
            
            if not room:
                return {
                    "name": room_name,
                    "equipment": [],
                    "max_capacity": 10,
                    "zone_type": "office",
                    "icon": "building",
                    "total_items": 0,
                    "occupancy_status": "NONE"
                }
        
        # Récupérer les équipements
        grouped = services.get_tools_grouped_by_location(limit=None)
        equipment_raw = grouped.get(room_name, [])
        
        # Role check
        from controllers import settings_controller
        user_role = settings_controller.get_user_role()
        
        if user_role == "IT_TECHNICIAN":
            # Filter equipment to only show MAINTENANCE
            equipment_raw = [t for t in equipment_raw if t.get("status") == "MAINTENANCE"]
            consumables = [] # Hide consumables
        else:
            # Récupérer les consommables pour cette section
            consumables = consumable_controller.get_supplies_by_section(room_name)
            
        equipment_ui = [services.format_tool_for_ui(t) for t in equipment_raw]
        
        # Calculer le total (équipements + consommables)
        total_items = len(equipment_ui) + len(consumables)
        max_capacity = room["max_capacity"]
        
        return {
            "name": room_name,
            "equipment": equipment_ui,
            "consumables": consumables,
            "max_capacity": max_capacity,
            "zone_type": room.get("room_type", "office"),
            "icon": room.get("icon", "building"),
            "total_items": total_items,
            "occupancy_status": _get_occupancy_status(total_items, max_capacity)
        }
        
    except Exception:
        logger.exception(f"Failed to get room details for {room_name}")
        return {
            "name": room_name,
            "equipment": [],
            "max_capacity": 10,
            "zone_type": "office",
            "icon": "building",
            "total_items": 0,
            "occupancy_status": "NONE"
        }


def update_room_capacity(room_name: str, new_capacity: int) -> bool:
    """
    Met à jour la capacité maximale d'une zone.
    
    Args:
        room_name: Nom de la zone
        new_capacity: Nouvelle capacité maximale
        
    Returns:
        True si la mise à jour a réussi, False sinon
    """
    try:
        _ensure_rooms_exist()
        success = models.update_room_capacity(room_name, new_capacity)
        if success:
            logger.info(f"Capacité mise à jour pour {room_name}: {new_capacity}")
        else:
            logger.warning(f"Échec de la mise à jour pour {room_name}")
        return success
    except Exception:
        logger.exception(f"Erreur lors de la mise à jour de la capacité pour {room_name}")
        return False


def _get_occupancy_status(total_items: int, max_capacity: Optional[int]) -> str:
    """
    Calcule le statut d'occupation d'une zone.
    
    Args:
        total_items: Nombre d'équipements dans la zone
        max_capacity: Capacité maximale de la zone
        
    Returns:
        Statut: "NONE", "NORMAL", "MEDIUM", "HIGH", "CRITICAL"
    """
    if total_items == 0:
        return "NONE"
    
    if max_capacity is None or max_capacity == 0:
        return "NORMAL"
    
    usage_percent = (total_items / max_capacity) * 100
    
    if usage_percent >= 90:
        return "HIGH"
    elif usage_percent >= 70:
        return "MEDIUM"
    else:
        return "NORMAL"