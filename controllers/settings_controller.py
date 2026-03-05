"""
controllers/settings_controller.py

Controller for managing user settings and profile data.
NOW LOADS FROM DATABASE (users table) instead of JSON file.

The JSON file is kept as a fallback only.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# Path to settings file (fallback only)
SETTINGS_FILE = Path(__file__).parent.parent.joinpath("database", "user_settings.json")

# ============================================================
# GLOBAL: ID de l'utilisateur connecté
# ============================================================
_CURRENT_USER_ID = None


def set_current_user(user_id: int) -> None:
    """
    Définit l'ID de l'utilisateur actuellement connecté.
    À appeler depuis main.py après le login réussi.
    
    Args:
        user_id: ID de l'utilisateur dans la table users
    """
    global _CURRENT_USER_ID
    _CURRENT_USER_ID = user_id
    logger.info(f"Current user set to ID: {user_id}")


def get_current_user_id() -> Optional[int]:
    """Retourne l'ID de l'utilisateur connecté, ou None si pas connecté."""
    return _CURRENT_USER_ID


# ============================================================
# CHARGEMENT DEPUIS LA BASE DE DONNÉES
# ============================================================

def get_user_profile() -> Dict[str, Any]:
    """
    Get current user profile data FROM DATABASE.
    Falls back to JSON file if no user is logged in or DB fails.
    """
    # Si un utilisateur est connecté, charger depuis la DB
    if _CURRENT_USER_ID is not None:
        try:
            from database.database import fetchone
            
            user = fetchone(
                """
                SELECT u.id, u.first_name, u.last_name, u.email, u.phone_number,
                       u.date_of_birth, u.address, u.gender, u.profile_photo,
                       u.role_id, u.password,
                       r.name as role_name
                FROM users u
                JOIN roles r ON u.role_id = r.id
                WHERE u.id = ? AND u.is_active = 1;
                """,
                (_CURRENT_USER_ID,)
            )
            
            if user:
                # Mapper les colonnes SQL vers le format attendu par l'UI
                profile = {
                    "first_name": user.get("first_name", ""),
                    "last_name": user.get("last_name", ""),
                    "title": user.get("role_name", "USER"),  # role_name devient title
                    "email": user.get("email", ""),
                    "phone": user.get("phone_number", ""),
                    "date_of_birth": user.get("date_of_birth", ""),
                    "address": user.get("address", ""),

                    "gender": user.get("gender") or "male",
                    "password": user.get("password", ""),
                    "profile_photo": user.get("profile_photo"),
                    "role": user.get("role_name", "USER"),
                    "user_id": user.get("id"),
                }
                
                logger.info(f"Loaded profile from DB for user {profile['first_name']} {profile['last_name']}")
                return profile
            else:
                logger.warning(f"User ID {_CURRENT_USER_ID} not found in database")
        
        except Exception as e:
            logger.exception(f"Failed to load user profile from DB: {e}")
    
    # Fallback: charger depuis le JSON (ancien comportement)
    logger.info("Loading profile from JSON fallback")
    return _load_profile_from_json()


def _load_profile_from_json() -> Dict[str, Any]:
    """Charge le profil depuis le fichier JSON (fallback)."""
    try:
        _ensure_settings_file()
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            profile = data.get("user_profile", {})
            
            # Merge avec defaults
            default = get_default_user_profile()
            for key in default:
                if key not in profile:
                    profile[key] = default[key]
            
            return profile
    except Exception as e:
        logger.exception(f"Failed to load from JSON: {e}")
        return get_default_user_profile()


def save_user_profile(profile_data: Dict[str, Any]) -> bool:
    """
    Save user profile data TO DATABASE.
    Falls back to JSON if no user is logged in.
    
    Args:
        profile_data: Dictionary containing user profile fields
        
    Returns:
        True if save was successful, False otherwise
    """
    # Séparer les champs DB et JSON
    db_fields = {}
    json_fields = {}
    
    # Mapping: clé UI → colonne DB (seulement les colonnes qui existent)
    field_mapping = {
        "first_name": "first_name",
        "last_name": "last_name",
        "email": "email",
        "phone": "phone_number",
        "date_of_birth": "date_of_birth",
        "address": "address",
        "password": "password",
        "gender": "gender",
        "profile_photo": "profile_photo",
    }
    
    # Champs qui vont dans JSON uniquement (OBSOLETE but keeping for compatibility if needed)
    json_only_fields = []
    
    for key, value in profile_data.items():
        if key in field_mapping:
            db_fields[field_mapping[key]] = value
        elif key in json_only_fields:
            json_fields[key] = value
    
    db_success = True
    json_success = True
    
    # Si un utilisateur est connecté, sauvegarder dans la DB
    if _CURRENT_USER_ID is not None and db_fields:
        try:
            from database.database import execute
            
            # Construire la requête UPDATE
            set_clause = ", ".join([f"{col} = ?" for col in db_fields.keys()])
            values = list(db_fields.values())
            values.append(_CURRENT_USER_ID)  # WHERE id = ?
            
            sql = f"UPDATE users SET {set_clause} WHERE id = ?;"
            
            execute(sql, tuple(values))
            logger.info(f"User profile saved to DB for user ID {_CURRENT_USER_ID}")
            db_success = True
            
        except Exception as e:
            logger.exception(f"Failed to save user profile to DB: {e}")
            db_success = False
    
    # Sauvegarder les champs JSON
    if json_fields:
        json_success = _save_profile_to_json(json_fields)
    
    return db_success and json_success


def _save_profile_to_json(profile_data: Dict[str, Any]) -> bool:
    """Sauvegarde le profil dans le fichier JSON (fallback)."""
    try:
        settings = _load_settings()
        current_profile = settings.get("user_profile", {})
        current_profile.update(profile_data)
        settings["user_profile"] = current_profile
        return _save_settings(settings)
    except Exception as e:
        logger.exception(f"Failed to save to JSON: {e}")
        return False


def update_password(current_password: str, new_password: str) -> tuple[bool, str]:
    """
    Update user password with validation.
    NOW UPDATES IN DATABASE with current password verification.
    
    Args:
        current_password: Current password for verification
        new_password: New password to set
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        profile = get_user_profile()
        stored_password = profile.get("password", "")
        
        # ✅ Verify current password
        if current_password != stored_password:
            logger.warning("Password update failed: incorrect current password")
            return False, "Le mot de passe actuel est incorrect"
        
        # ✅ Validate new password
        if len(new_password) < 6:
            return False, "Le nouveau mot de passe doit contenir au moins 6 caractères"
        
        if new_password == current_password:
            return False, "Le nouveau mot de passe doit être différent de l'actuel"
        
        # ✅ Save new password
        success = save_user_profile({"password": new_password})
        
        if success:
            logger.info("Password updated successfully")
            return True, "Mot de passe mis à jour avec succès"
        else:
            return False, "Échec de la sauvegarde du nouveau mot de passe"
            
    except Exception as e:
        logger.exception(f"Failed to update password: {e}")
        return False, f"Erreur: {str(e)}"


# ============================================================
# FONCTIONS UTILITAIRES POUR LE HEADER
# ============================================================

def get_user_display_name() -> str:
    """Get formatted display name for header."""
    try:
        profile = get_user_profile()
        first = profile.get("first_name", "").upper()
        last = profile.get("last_name", "").upper()
        return f"{first} {last}".strip() or "USER"
    except Exception:
        return "USER"


def get_user_role() -> str:
    """Get user role for display."""
    try:
        profile = get_user_profile()
        return profile.get("role", profile.get("title", "USER"))
    except Exception:
        return "USER"


def get_all_employees() -> list[dict]:
    """Retrieve all active users and their roles for the CEO."""
    try:
        from database.database import fetchall
        users = fetchall(
            """
            SELECT u.id, u.first_name, u.last_name, u.email, u.phone_number,
                   u.date_of_birth, u.address, u.gender, u.profile_photo,
                   r.name as role_name
            FROM users u
            JOIN roles r ON u.role_id = r.id
            WHERE u.is_active = 1
            ORDER BY r.name, u.last_name;
            """
        )
        return users
    except Exception as e:
        logger.exception(f"Failed to fetch employees: {e}")
        return []


def delete_employee(user_id: int) -> bool:
    """
    Delete a user (employee) from the database by ID.
    Sets is_active to 0 instead of actual deletion for soft delete.
    
    Args:
        user_id: The ID of the user to delete.
        
    Returns:
        True if the user was successfully marked as inactive, False otherwise.
    """
    try:
        from database.database import execute
        # Perform a soft delete by setting is_active to 0
        execute(
            """
            UPDATE users
            SET is_active = 0
            WHERE id = ?;
            """,
            (user_id,)
        )
        logger.info(f"User with ID {user_id} soft-deleted from DB.")
        return True
    except Exception as e:
        logger.exception(f"Failed to soft-delete user with ID {user_id}: {e}")
        return False


def get_user_avatar_path() -> Optional[str]:
    """Get path to user's profile photo."""
    try:
        profile = get_user_profile()
        photo_path = profile.get("profile_photo")
        
        if photo_path and os.path.exists(photo_path):
            return photo_path
        
        return None
    except Exception:
        return None


# ============================================================
# FONCTIONS DE FALLBACK (JSON)
# ============================================================

def _ensure_settings_file() -> None:
    """Ensure the settings file and directory exist."""
    try:
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        if not SETTINGS_FILE.exists():
            default_data = {
                "user_profile": get_default_user_profile(),
                "app_settings": {}
            }
            _save_settings(default_data)
    except Exception as e:
        logger.exception(f"Failed to ensure settings file: {e}")


def _load_settings() -> Dict[str, Any]:
    """Load settings from JSON file."""
    try:
        _ensure_settings_file()
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if "user_profile" not in data:
                data["user_profile"] = get_default_user_profile()
            if "app_settings" not in data:
                data["app_settings"] = {}
            return data
    except Exception as e:
        logger.exception(f"Failed to load settings: {e}")
        return {
            "user_profile": get_default_user_profile(),
            "app_settings": {}
        }


def _save_settings(data: Dict[str, Any]) -> bool:
    """Save settings to JSON file."""
    try:
        _ensure_settings_file()
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.exception(f"Failed to save settings: {e}")
        return False


def get_default_user_profile() -> Dict[str, Any]:
    """Return default user profile data."""
    return {
        "first_name": "User",
        "last_name": "Unknown",
        "title": "USER",
        "email": "user@example.com",
        "phone": "",
        "date_of_birth": "",
        "address": "",
        "gender": "male",
        "password": "",
        "profile_photo": None,
    }


def reset_user_profile() -> bool:
    """Reset user profile to default values (JSON only, not DB)."""
    try:
        settings = _load_settings()
        settings["user_profile"] = get_default_user_profile()
        return _save_settings(settings)
    except Exception as e:
        logger.exception(f"Failed to reset user profile: {e}")
        return False


# ── App Settings (for future use) ────────────────────────────────

def get_app_setting(key: str, default: Any = None) -> Any:
    """Get an application setting value."""
    try:
        settings = _load_settings()
        return settings.get("app_settings", {}).get(key, default)
    except Exception:
        return default


def set_app_setting(key: str, value: Any) -> bool:
    """Set an application setting value."""
    try:
        settings = _load_settings()
        if "app_settings" not in settings:
            settings["app_settings"] = {}
        settings["app_settings"][key] = value
        return _save_settings(settings)
    except Exception as e:
        logger.exception(f"Failed to set app setting: {e}")
        return False