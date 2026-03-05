"""
controllers/consumable_controller.py

Contrôleur pour la vue Supplies/Consommables.
Fournit des helpers pour obtenir, filtrer, créer, modifier et supprimer des consommables.

Fonctions principales exposées :
- get_all_supplies(search_query=None) -> List[Dict]
- upsert_supply(data: Dict) -> None
- delete_supply(supply_id: str) -> None
- update_supply_quantity(supply_id: str, new_quantity: int, new_status: str) -> None
"""
from typing import Any, Dict, List, Optional
import logging

from database import database as dbwrapper

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


def _search_in_supply(supply: Dict[str, Any], query: str) -> bool:
    """
    Recherche une chaîne dans tous les champs pertinents d'un consommable.
    Supporte la recherche par: nom, catégorie, section, statut, ID
    
    Args:
        supply: Dictionnaire du consommable
        query: Texte de recherche (insensible à la casse)
    
    Returns:
        True si la recherche correspond à au moins un champ
    """
    if not query:
        return True
    
    query_original = query.strip()
    query_lower = query_original.lower()
    
    # ===================================================================
    # NETTOYAGE INTELLIGENT DES PRÉFIXES (comme dans inventory_controller)
    # ===================================================================
    query_clean = query_lower
    
    # Gérer le préfixe "#ID" si présent (prioritaire)
    if query_lower.startswith('#id') and len(query_lower) > 3:
        potential_id = query_lower[3:].strip()
        if potential_id:
            query_clean = potential_id
            logger.debug(f"Préfixe #ID détecté, recherche avec: '{query_clean}'")
    
    # Gérer le préfixe "ID" si présent (sans #)
    elif query_lower.startswith('id') and len(query_lower) > 2:
        potential_id = query_lower[2:].strip()
        if potential_id:
            query_clean = potential_id
            logger.debug(f"Préfixe ID détecté, recherche avec: '{query_clean}'")
    
    # Liste des champs textuels à rechercher
    text_search_fields = [
        'name',         # Nom du consommable
        'category',     # Catégorie (PRINTING, CABLES, etc.)
        'section',      # Section (SECTION A, B, C)
        'status',       # Statut (STOCKED, CRITICAL, OUT)
        'id',           # ID du consommable
    ]
    
    # Rechercher dans chaque champ textuel
    for field in text_search_fields:
        value = supply.get(field)
        if value is not None:
            str_value = str(value).lower()
            
            # Recherche normale avec la requête originale
            if query_lower in str_value:
                return True
            
            # Recherche avec la requête nettoyée (pour les IDs sans préfixe)
            if query_clean != query_lower and query_clean in str_value:
                return True
            
            # Pour le champ ID spécifiquement : essayer aussi avec le préfixe "ID"
            if field == 'id':
                id_with_prefix = f"id{str_value}"
                if query_lower in id_with_prefix:
                    return True
    
    # ===================================================================
    # RECHERCHE DANS LES CHAMPS NUMÉRIQUES
    # ===================================================================
    
    # Recherche dans in_storage (quantité en stock)
    in_storage = supply.get('in_storage')
    if in_storage is not None:
        storage_str = str(in_storage).lower()
        if query_lower in storage_str or query_clean in storage_str:
            return True
        
        # Recherche par mots-clés de stock
        try:
            storage_val = int(in_storage)
            limit_val = int(supply.get('limit_alert', 0))
            
            # Si on cherche "low stock" ou "stock faible"
            if any(kw in query_lower for kw in ['low', 'faible', 'critical', 'critique']):
                if storage_val < limit_val:
                    return True
            
            # Si on cherche "out of stock" ou "rupture"
            if any(kw in query_lower for kw in ['out', 'rupture', 'depleted', 'épuisé']):
                if storage_val == 0:
                    return True
            
            # Si on cherche "stocked" ou "bien approvisionné"
            if any(kw in query_lower for kw in ['stocked', 'stock', 'full', 'plein']):
                if storage_val >= limit_val:
                    return True
        except (ValueError, TypeError):
            pass
    
    # Recherche dans limit_alert
    limit_alert = supply.get('limit_alert')
    if limit_alert is not None:
        limit_str = str(limit_alert).lower()
        if query_lower in limit_str or query_clean in limit_str:
            return True
    
    return False


def get_all_supplies(search_query: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Récupère tous les consommables avec filtre de recherche optionnel.
    
    Args:
        search_query: Texte de recherche (nom, catégorie, section, ID, statut)
    
    Returns:
        Liste de dictionnaires de consommables
    """
    try:
        from controllers import settings_controller
        if settings_controller.get_user_role() == "IT_TECHNICIAN":
            return []
            
        # Récupérer TOUS les consommables de la base
        sql = "SELECT * FROM supplies ORDER BY name ASC"
        all_supplies = dbwrapper.fetchall(sql, [])
        
        # Appliquer le filtre de recherche si présent
        if search_query and search_query.strip():
            filtered_supplies = [
                supply for supply in all_supplies 
                if _search_in_supply(supply, search_query)
            ]
            logger.info(f"Filtered supplies with query '{search_query}': {len(filtered_supplies)}/{len(all_supplies)} results")
            return filtered_supplies
        
        logger.info(f"Retrieved all supplies: {len(all_supplies)} items")
        return all_supplies
        
    except Exception:
        logger.exception("Failed to get supplies")
        return []


def upsert_supply(data: Dict[str, Any]) -> None:
    """
    Insère ou met à jour un consommable.
    """
    from controllers import settings_controller
    if settings_controller.get_user_role() == "IT_TECHNICIAN":
        raise PermissionError("IT_TECHNICIAN is not allowed to modify supplies")

    try:
        # Validation basique
        if not data.get('id') or not data.get('name'):
            raise ValueError("ID and name are required")
        
        # Vérifier si l'item existe déjà
        exists = dbwrapper.fetchone("SELECT 1 FROM supplies WHERE id = ?", (data['id'],))
        
        if exists:
            # UPDATE
            sql = """
                UPDATE supplies SET 
                    name=?, category=?, section=?, in_storage=?, limit_alert=?, status=?
                WHERE id=?
            """
            params = (
                data['name'], 
                data['category'], 
                data['section'], 
                data['in_storage'], 
                data['limit_alert'], 
                data['status'], 
                data['id']
            )
            dbwrapper.execute(sql, params)
            logger.info(f"Updated supply: {data['name']} (ID: {data['id']})")
        else:
            # INSERT
            sql = """
                INSERT INTO supplies (id, name, category, section, in_storage, limit_alert, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            params = (
                data['id'], 
                data['name'], 
                data['category'], 
                data['section'], 
                data['in_storage'], 
                data['limit_alert'], 
                data['status']
            )
            dbwrapper.execute(sql, params)
            logger.info(f"Created supply: {data['name']} (ID: {data['id']})")
        
    except ValueError as e:
        logger.warning(f"Validation error upserting supply: {e}")
        raise
    except Exception:
        logger.exception("Failed to upsert supply")
        raise


def delete_supply(supply_id: str) -> bool:
    """
    Supprime un consommable par son ID.
    """
    from controllers import settings_controller
    if settings_controller.get_user_role() == "IT_TECHNICIAN":
        raise PermissionError("IT_TECHNICIAN is not allowed to delete supplies")

    try:
        dbwrapper.execute("DELETE FROM supplies WHERE id = ?", (supply_id,))
        logger.info(f"Deleted supply ID {supply_id}")
        return True
        
    except Exception:
        logger.exception(f"Failed to delete supply {supply_id}")
        return False


def update_supply_quantity(supply_id: str, new_quantity: int, new_status: str) -> bool:
    """
    Met à jour uniquement la quantité et le statut d'un consommable.
    """
    from controllers import settings_controller
    if settings_controller.get_user_role() == "IT_TECHNICIAN":
        raise PermissionError("IT_TECHNICIAN is not allowed to update supply quantity")

    try:
        dbwrapper.execute(
            "UPDATE supplies SET in_storage = ?, status = ? WHERE id = ?", 
            (new_quantity, new_status, supply_id)
        )
        logger.info(f"Updated supply quantity: ID {supply_id} -> {new_quantity} ({new_status})")
        
        return True
        
    except Exception:
        logger.exception(f"Failed to update supply quantity {supply_id}")
        return False


def get_supply(supply_id: str) -> Optional[Dict[str, Any]]:
    """
    Récupère un consommable par son ID.
    """
    try:
        from controllers import settings_controller
        if settings_controller.get_user_role() == "IT_TECHNICIAN":
            return None
            
        supply = dbwrapper.fetchone("SELECT * FROM supplies WHERE id = ?", (supply_id,))
        return supply
        
    except Exception:
        logger.exception(f"Failed to get supply {supply_id}")
        return None


def get_critical_supplies(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Récupère les consommables en stock critique (in_storage < limit_alert).
    """
    try:
        from controllers import settings_controller
        if settings_controller.get_user_role() == "IT_TECHNICIAN":
            return []
            
        sql = """
            SELECT * FROM supplies 
            WHERE in_storage < limit_alert 
            ORDER BY in_storage ASC 
            LIMIT ?
        """
        return dbwrapper.fetchall(sql, (limit,))
        
    except Exception:
        logger.exception("Failed to get critical supplies")
        return []


def get_supplies_by_category(category: str) -> List[Dict[str, Any]]:
    """
    Récupère les consommables d'une catégorie spécifique.
    """
    try:
        from controllers import settings_controller
        if settings_controller.get_user_role() == "IT_TECHNICIAN":
            return []
            
        sql = "SELECT * FROM supplies WHERE category = ? ORDER BY name ASC"
        return dbwrapper.fetchall(sql, (category,))
        
    except Exception:
        logger.exception(f"Failed to get supplies by category {category}")
        return []


def get_supplies_by_section(section: str) -> List[Dict[str, Any]]:
    """
    Récupère les consommables d'une section spécifique.
    """
    try:
        from controllers import settings_controller
        if settings_controller.get_user_role() == "IT_TECHNICIAN":
            return []
            
        sql = "SELECT * FROM supplies WHERE section = ? ORDER BY name ASC"
        return dbwrapper.fetchall(sql, (section,))
        
    except Exception:
        logger.exception(f"Failed to get supplies by section {section}")
        return []


def get_supplies_stats() -> Dict[str, Any]:
    """
    Récupère des statistiques sur les consommables.
    """
    try:
        from controllers import settings_controller
        if settings_controller.get_user_role() == "IT_TECHNICIAN":
            return {"total": 0, "stocked": 0, "critical": 0, "out_of_stock": 0}
            
        # Total
        total = dbwrapper.fetchone("SELECT COUNT(*) as count FROM supplies", [])
        
        # Par statut
        stocked = dbwrapper.fetchone(
            "SELECT COUNT(*) as count FROM supplies WHERE status = 'STOCKED'", []
        )
        critical = dbwrapper.fetchone(
            "SELECT COUNT(*) as count FROM supplies WHERE status = 'CRITICAL'", []
        )
        out = dbwrapper.fetchone(
            "SELECT COUNT(*) as count FROM supplies WHERE status = 'OUT'", []
        )
        
        return {
            "total": total['count'] if total else 0,
            "stocked": stocked['count'] if stocked else 0,
            "critical": critical['count'] if critical else 0,
            "out_of_stock": out['count'] if out else 0
        }
        
    except Exception:
        logger.exception("Failed to get supplies stats")
        return {
            "total": 0, "stocked": 0, "critical": 0, "out_of_stock": 0
        }