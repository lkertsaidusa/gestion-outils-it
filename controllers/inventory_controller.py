"""
controllers/inventory_controller.py

Contrôleur pour la vue Inventory.
Fournit des helpers pour obtenir, filtrer, créer, modifier et supprimer des équipements.

Fonctions principales exposées :
- list_tools(filters: Optional[Dict] = None) -> List[Dict]
- apply_filters(filters: Dict) -> List[Dict]
- get_tool(tool_id: int) -> Optional[Dict]
- create_tool(data: Dict) -> Dict
- update_tool(tool_id: int, data: Dict) -> Dict
- delete_tool(tool_id: int) -> bool
"""
from typing import Any, Dict, List, Optional
import logging
from datetime import datetime, date

from backend import services, models

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


def _normalize_date(date_value: Any) -> str:
    """
    Normalise différents formats de date en string pour la recherche.
    
    Args:
        date_value: Date sous forme de string, datetime, date ou autre
    
    Returns:
        String normalisé de la date
    """
    if isinstance(date_value, (datetime, date)):
        return date_value.strftime("%Y-%m-%d")
    elif isinstance(date_value, str):
        return date_value
    return str(date_value)


def _search_in_tool(tool: Dict[str, Any], query: str) -> bool:
    """
    Recherche une chaîne dans tous les champs pertinents d'un outil.
    Supporte la recherche par: nom, id, marque, modèle, catégorie, status, date d'expiration
    
    Args:
        tool: Dictionnaire de l'outil (brut ou formaté)
        query: Texte de recherche (insensible à la casse)
    
    Returns:
        True si la recherche correspond à au moins un champ
    """
    if not query:
        return True
    
    query_original = query.strip()
    query_lower = query_original.lower()
    
    # ===================================================================
    # NETTOYAGE INTELLIGENT DES PRÉFIXES
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
    
    # Gérer le préfixe "SN" (Serial Number) si présent
    elif query_lower.startswith('sn') and len(query_lower) > 2:
        potential_sn = query_lower[2:].strip()
        if potential_sn:
            query_clean = potential_sn
            logger.debug(f"Préfixe SN détecté, recherche avec: '{query_clean}'")
    
    # Liste des champs textuels à rechercher
    text_search_fields = [
        'name',              # Nom de l'article
        'asset_model',       # Modèle
        'id',                # ID
        'brand',             # Marque
        'category',          # Catégorie
        'type',              # Catégorie (DB column)
        'status',            # Statut (ACTIVE, AVAILABLE, etc.)
        'location',          # Localisation
        'localisation',      # Localisation (DB column)
        'assigned_area',     # Zone assignée
        'serial',            # Numéro de série
        'serial_number',     # Numéro de série (autre nom)
        'assigned_to',       # Assigné à
        'notes',             # Notes
    ]
    
    # Rechercher dans chaque champ textuel
    for field in text_search_fields:
        value = tool.get(field)
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
    # RECHERCHE DANS LES DATES (warranty_expiration, purchase_date, etc.)
    # ===================================================================
    
    # 1. Date d'expiration de garantie (warranty_date, warranty_expiration)
    date_fields = [
        'warranty_date',
        'warranty_expiration',
        'purchase_date',
        'last_maintenance_date'
    ]
    
    for date_field in date_fields:
        date_value = tool.get(date_field)
        if date_value:
            # Normaliser la date
            date_str = _normalize_date(date_value)
            
            # Recherche directe dans la date formatée
            if query_lower in date_str.lower():
                return True
            
            # Recherche par année
            if len(query_original) == 4 and query_original.isdigit():
                if query_original in date_str:
                    return True
            
            # Recherche par mois/année (MM/YYYY ou MM-YYYY)
            if '/' in query_original or '-' in query_original:
                if query_original in date_str:
                    return True
    
    # 2. Recherche spécifique dans warranty_expiration si c'est un objet
    warranty_info = tool.get('warranty_expiration')
    if isinstance(warranty_info, dict):
        # Chercher dans display_date
        display_date = warranty_info.get('display_date')
        if display_date and query_lower in str(display_date).lower():
            return True
        
        # Chercher dans les flags (expiring, expired)
        if warranty_info.get('is_expiring') and any(
            keyword in query_lower for keyword in ['expiring', 'expire', 'soon']
        ):
            return True
        
        if warranty_info.get('is_expired') and any(
            keyword in query_lower for keyword in ['expired', 'expire']
        ):
            return True
    
    # ===================================================================
    # RECHERCHE DANS D'AUTRES CHAMPS SPÉCIAUX
    # ===================================================================
    
    # Recherche dans battery_health si présent
    battery_health = tool.get('battery_health')
    if battery_health is not None:
        battery_str = str(battery_health).lower()
        if query_lower in battery_str or query_clean in battery_str:
            return True
        
        # Recherche par mots-clés de santé batterie
        if 'battery' in query_lower or 'batterie' in query_lower:
            try:
                battery_val = int(battery_health)
                # Si on cherche "low battery" ou "batterie faible"
                if any(kw in query_lower for kw in ['low', 'faible', 'weak']):
                    if battery_val < 30:
                        return True
                # Si on cherche "good battery" ou "bonne batterie"
                if any(kw in query_lower for kw in ['good', 'bonne', 'high', 'forte']):
                    if battery_val >= 70:
                        return True
            except (ValueError, TypeError):
                pass
    
    return False


def _check_warranty_status(tool: Dict[str, Any], warranty_filter: str) -> bool:
    """
    Vérifie si un outil correspond au filtre de garantie.
    
    Args:
        tool: Dictionnaire de l'outil (données brutes de la DB)
        warranty_filter: "Valid", "Expiring Soon" ou "Expired"
    
    Returns:
        True si l'outil correspond au filtre
    """
    from datetime import datetime, date
    
    # Récupérer la date de garantie (peut être dans warranty_expiration ou warranty_date)
    warranty_date_input = tool.get('warranty_expiration') or tool.get('warranty_date')
    
    # Si pas de date, considérer comme N/A (ni valide, ni expirant, ni expiré)
    if not warranty_date_input or warranty_date_input == "":
        is_expired = False
        is_expiring = False
    else:
        try:
            # Parser la date
            if isinstance(warranty_date_input, date):
                warranty_date = warranty_date_input
            elif isinstance(warranty_date_input, str):
                # Essayer format YYYY-MM-DD (format SQLite standard)
                warranty_date = datetime.strptime(warranty_date_input.strip(), "%Y-%m-%d").date()
            else:
                is_expired = False
                is_expiring = False
                warranty_date = None
            
            if warranty_date:
                today = date.today()
                days_remaining = (warranty_date - today).days
                
                is_expired = days_remaining < 0
                is_expiring = 0 <= days_remaining <= 60  # 60 jours = ~2 mois
            else:
                is_expired = False
                is_expiring = False
        except Exception:
            is_expired = False
            is_expiring = False
    
    # Appliquer le filtre
    if warranty_filter == "Valid":
        # Valide = ni expirant, ni expiré ET a une date de garantie
        has_warranty = warranty_date_input is not None and warranty_date_input != ""
        return has_warranty and not is_expiring and not is_expired
    elif warranty_filter == "Expiring Soon":
        return is_expiring
    elif warranty_filter == "Expired":
        return is_expired
    
    return True


def list_tools(filters: Optional[Dict[str, Any]] = None, limit: Optional[int] = 200) -> List[Dict[str, Any]]:
    """
    Lister tous les outils avec filtres optionnels, formatés pour l'UI.
    
    Args:
        filters: Dictionnaire de filtres (status, category, location, q, search_id, warranty)
        limit: Nombre maximum d'éléments à retourner
    
    Returns:
        Liste de dictionnaires formatés pour l'affichage UI
    """
    try:
        # Extraire les filtres spéciaux
        search_query = None
        search_id = None
        warranty_filter = None
        
        if filters:
            # Recherche textuelle générale (barre de recherche principale)
            if 'q' in filters:
                search_query = filters.get('q')
            
            # Recherche par ID (depuis FilterWindow)
            if 'search_id' in filters and filters.get('search_id'):
                search_id = filters.get('search_id')
                # Nettoyer le préfixe "#ID" si présent
                if search_id and search_id.upper().startswith('#ID'):
                    search_id = search_id[4:].strip()
                elif search_id and search_id.upper().startswith('ID'):
                    search_id = search_id[2:].strip()
            
            # Filtre de garantie
            if 'warranty' in filters and filters.get('warranty'):
                warranty_list = filters.get('warranty')
                if warranty_list and len(warranty_list) > 0:
                    warranty_filter = warranty_list[0]  # Prendre le premier sélectionné
            
            # Créer une copie des filtres sans les filtres spéciaux pour le service
            filters_without_special = {k: v for k, v in filters.items() 
                                      if k not in ['q', 'search_id', 'warranty']}
        else:
            filters_without_special = None
        
        # Récupérer les données brutes depuis services
        raw_tools = models.list_tools(filters=filters_without_special, limit=limit)
        
        # Appliquer le filtre de garantie si présent
        if warranty_filter:
            logger.info(f"Applying warranty filter: '{warranty_filter}' on {len(raw_tools)} tools")
            filtered_tools = []
            for tool in raw_tools:
                matches = _check_warranty_status(tool, warranty_filter)
                if matches:
                    filtered_tools.append(tool)
                    logger.debug(f"Tool {tool.get('id')} matches warranty filter")
            raw_tools = filtered_tools
            logger.info(f"Warranty filter '{warranty_filter}': {len(raw_tools)} results remaining")
        
        # Appliquer le filtre de recherche par ID si présent (prioritaire)
        if search_id:
            raw_tools = [
                tool for tool in raw_tools 
                if search_id.lower() in (tool.get('serial_number') or '').lower()
            ]
            logger.info(f"Filtered by ID '{search_id}': {len(raw_tools)} results")
        
        # Appliquer le filtre de recherche textuelle si présent (et pas de search_id)
        elif search_query:
            raw_tools = [tool for tool in raw_tools if _search_in_tool(tool, search_query)]
        
        # Formater chaque outil pour l'UI
        formatted_tools = [services.format_tool_for_ui(tool) for tool in raw_tools]
        
        logger.info(f"Listed {len(formatted_tools)} tools (filters: {filters}, search_query: '{search_query}', search_id: '{search_id}')")
        return formatted_tools
        
    except Exception:
        logger.exception("Failed to list tools")
        return []


def apply_filters(filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Applique des filtres et retourne les outils correspondants.
    
    Args:
        filters: Dictionnaire de filtres {
            "status": ["ACTIVE", "AVAILABLE"],
            "category": ["PC", "PRINTER"],
            "location": ["OFFICE 101"],
            "q": "search text",
            "search_id": "#ID13DZA3",  # Nouveau: recherche par ID
            "warranty": ["Valid", "Expiring Soon", "Expired"]  # Filtre warranty
        }
    
    Returns:
        Liste de dictionnaires formatés pour l'affichage UI
    """
    try:
        # Normaliser les filtres
        normalized_filters = services.normalize_filters(filters)
        
        # Ajouter les filtres de recherche (q, search_id, warranty) qui ne sont pas normalisés par services
        if 'q' in filters:
            normalized_filters['q'] = filters['q']
        
        if 'search_id' in filters:
            normalized_filters['search_id'] = filters['search_id']
        
        # IMPORTANT: Ajouter le filtre warranty s'il existe
        if 'warranty' in filters and filters['warranty']:
            normalized_filters['warranty'] = filters['warranty']
            logger.info(f"Warranty filter added: {filters['warranty']}")
        
        # Récupérer les données filtrées
        return list_tools(filters=normalized_filters)
        
    except Exception:
        logger.exception("Failed to apply filters")
        return []


def get_tool(tool_id: int) -> Optional[Dict[str, Any]]:
    """
    Récupère un outil par son ID.
    
    Args:
        tool_id: ID de l'outil
    
    Returns:
        Dictionnaire de l'outil ou None si non trouvé
    """
    try:
        tool = models.get_tool(tool_id)
        if tool:
            return services.format_tool_for_ui(tool)
        return None
        
    except Exception:
        logger.exception(f"Failed to get tool {tool_id}")
        return None


def create_tool(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Crée un nouvel outil dans la base de données.
    
    Args:
        data: Dictionnaire contenant les données de l'outil {
            "asset_model": str,  # Nom du produit
            "brand": str,
            "serial_number": str,
            "category": str,
            "assigned_area": str,
            "status": str,
            "warranty_date": str (YYYY-MM-DD),
            "battery_health": int,
            "assigned_to": str,
            "purchase_date": str (YYYY-MM-DD),
            "notes": str
        }
    
    Returns:
        Dictionnaire de l'outil créé, formaté pour l'UI
    
    Raises:
        ValueError: Si les données sont invalides ou incomplètes
    """
    try:
        # Valider et créer via services
        created = models.create_tool(data)
        
        logger.info(f"Created tool: {created.get('name')} (ID: {created.get('id')})")
        
        # Retourner formaté pour l'UI
        return services.format_tool_for_ui(created)
        
    except ValueError as e:
        # Erreur de validation (ex: champs requis manquants, serial dupliqué)
        logger.warning(f"Validation error creating tool: {e}")
        raise
    except Exception:
        logger.exception("Failed to create tool")
        raise


def update_tool(tool_id: int, data: Dict[str, Any], silent: bool = False) -> Dict[str, Any]:
    """
    Met à jour un outil existant.
    
    Args:
        tool_id: ID de l'outil à modifier
        data: Dictionnaire contenant les champs à mettre à jour
        silent: Si True, n'envoie pas de notification email individuelle
    
    Returns:
        Dictionnaire de l'outil mis à jour, formaté pour l'UI
    
    Raises:
        ValueError: Si les données sont invalides
    """
    try:
        # Sauvegarder l'ancien état pour la notification
        old_tool = models.get_tool(tool_id)
        
        # Mettre à jour via models
        updated = models.update_tool(tool_id, data, silent=silent)
        
        logger.info(f"Updated tool ID {tool_id}")
        # Retourner formaté pour l'UI
        return services.format_tool_for_ui(updated)
        
    except Exception:
        logger.exception(f"Failed to update tool {tool_id}")
        raise


def delete_tool(tool_id: int, silent: bool = False) -> bool:
    """
    Supprime un outil de la base de données.
    
    Args:
        tool_id: ID de l'outil à supprimer
        silent: Si True, n'envoie pas de notification email individuelle
    
    Returns:
        True si supprimé avec succès, False sinon
    """
    try:
        # Sauvegarder les données pour la notification avant suppression
        tool_to_delete = models.get_tool(tool_id)
        
        success = models.delete_tool(tool_id, silent=silent)
        
        if success:
            logger.info(f"Deleted tool ID {tool_id}")
        else:
            logger.warning(f"Failed to delete tool ID {tool_id}")
        
        return success
        
    except Exception:
        logger.exception(f"Failed to delete tool {tool_id}")
        return False


def get_categories() -> List[Dict[str, Any]]:
    """
    Récupère la liste des catégories disponibles.
    
    Returns:
        Liste de dictionnaires {id, name, description}
    """
    try:
        return models.list_categories()
    except Exception:
        logger.exception("Failed to list categories")
        return []


def get_locations() -> List[Dict[str, Any]]:
    """
    Récupère la liste des localisations disponibles.
    
    Returns:
        Liste de dictionnaires {id, name, building, floor, description}
    """
    try:
        return models.list_locations()
    except Exception:
        logger.exception("Failed to list locations")
        return []


def get_history(tool_id: Optional[int] = None, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Récupère l'historique des modifications.
    
    Args:
        tool_id: Si fourni, filtre par ID d'outil
        limit: Nombre maximum d'entrées à retourner
    
    Returns:
        Liste de dictionnaires d'historique
    """
    try:
        return models.get_history(tool_id=tool_id, limit=limit)
    except Exception:
        logger.exception("Failed to get history")
        return []