import sys
import os

# Filtre stderr pour supprimer les messages Tcl/Tk parasites
class SilentStderr:
    def __init__(self, original):
        self.original = original
        self.buffer = ""
        self.blocked_patterns = [
            'invalid command name',
            'while executing',
            '("after" script)',
            'UserWarning',
            'CTkImage',
            'CTkLabel',
            'CTkButton',
            'PhotoImage',
            'HighDPI',
            'check_dpi_scaling',
            'update'
        ]
    def write(self, msg):
        # Accumuler dans le buffer
        self.buffer += msg
        # Traiter ligne par ligne
        while '\n' in self.buffer:
            line, self.buffer = self.buffer.split('\n', 1)
            line += '\n'
            if not any(pattern in line for pattern in self.blocked_patterns):
                self.original.write(line)
    def flush(self):
        # Traiter le reste du buffer
        if self.buffer:
            if not any(pattern in self.buffer for pattern in self.blocked_patterns):
                self.original.write(self.buffer)
            self.buffer = ""
        self.original.flush()

sys.stderr = SilentStderr(sys.stderr)

import customtkinter as ctk
import logging
import warnings

# Désactiver tous les warnings
warnings.filterwarnings('ignore')

# Configuration du logging - n'afficher que les erreurs et warnings
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

# Désactiver les logs des bibliothèques
for logger_name in ['PIL', 'PIL.Image', 'customtkinter', 'py.warnings', 'app', 'controllers', 'backend']:
    logging.getLogger(logger_name).setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Ajouter le chemin d'accès au dossier app pour les imports relatifs
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))

from app.views.login_view import LoginApp
from app.components.header import Header
from app.components.sidebar import Sidebar
from app.views.dashboard_view import DashboardView
from app.views.settings_view import SettingsView
from app.views.inventory_view import InventoryView
from app.views.map import FacilityMapView
from app.views.consomable_view import SuppliesView
from app.views.help_view import HelpView
from app.components.notification import NotificationsApp
from app.components.toast_confirm import show_confirm_toast

# Import du contrôleur settings
from controllers import settings_controller


class TechManageApp(ctk.CTk):
    SIDEBAR_WIDTH = 260
    COLLAPSED_SIDEBAR_WIDTH = 90

    def __init__(self, logged_in_user=None):
        """
        logged_in_user: dictionnaire contenant les données de l'utilisateur connecté
                        (retourné par la requête SQL dans LoginApp).
        """
        super().__init__()

        # Stocker l'utilisateur connecté
        self.logged_in_user = logged_in_user
        
        # Définir l'utilisateur actuel dans le contrôleur
        if logged_in_user and 'id' in logged_in_user:
            settings_controller.set_current_user(logged_in_user['id'])

        # Fenêtre principale
        self.title("TechManage - IT Management System")
        self.geometry("1400x900")

        # Thème
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        # Grille pour organiser header/sidebar/content
        self.grid_rowconfigure(0, weight=0)   # header fixe
        self.grid_rowconfigure(1, weight=1)   # body extensible
        self.grid_columnconfigure(0, weight=0, minsize=self.SIDEBAR_WIDTH)
        self.grid_columnconfigure(1, weight=1)

        self.create_widgets()

    def create_widgets(self):
        # Header avec callbacks
        user_role = self.logged_in_user.get('role_name') if self.logged_in_user else None
        
        self.header = Header(
            self, 
            on_search=self.on_search,
            on_profile_click=self.on_profile_click,
            on_sidebar_toggle=self.toggle_sidebar,
            on_notification_click=self.open_notifications_window,
            user_role=user_role
        )
        self.header.grid(row=0, column=1, sticky="ew")
        
        # Charger les données utilisateur dans le header au démarrage
        self.refresh_header_user_info()

        # Sidebar (menu)
        user_role = self.logged_in_user.get('role_name') if self.logged_in_user else None
        self.sidebar = Sidebar(self, on_menu_click=self.handle_menu_click, width=self.SIDEBAR_WIDTH, user_role=user_role)
        self.sidebar.grid(row=0, column=0, rowspan=2, sticky="nsew")
        try:
            self.sidebar.grid_propagate(False)
        except Exception:
            pass

        # Zone centrale de contenu
        self.content_frame = ctk.CTkFrame(self, fg_color="#F8FAFC", corner_radius=0)
        self.content_frame.grid(row=1, column=1, sticky="nsew")
        self.content_frame.grid_rowconfigure(0, weight=1)
        self.content_frame.grid_columnconfigure(0, weight=1)

        # Vue actuellement affichée
        self.current_view = None

        # Vue initiale basée sur le rôle
        is_technician = str(user_role).upper() in ["IT_TECHNICIAN", "IT_TECHNICIEN"]
        is_ceo = str(user_role).upper() == "CEO"
        
        if is_technician:
            self.show_inventory_view()
            if "Inventory" in self.sidebar.menu_buttons:
                self.sidebar.set_active_button(self.sidebar.menu_buttons["Inventory"])
        elif is_ceo:
            self.show_dashboard_view()
            if "Dashboard" in self.sidebar.menu_buttons:
                self.sidebar.set_active_button(self.sidebar.menu_buttons["Dashboard"])
        else:
            # Fallback pour les autres rôles (IT Manager, etc.)
            self.show_dashboard_view()
            if "Dashboard" in self.sidebar.menu_buttons:
                self.sidebar.set_active_button(self.sidebar.menu_buttons["Dashboard"])

    def on_profile_click(self):
        logger.info("Profile clicked - navigating to Settings")
        self.show_settings_view(initial_page="personal")
        self.sidebar.set_active_button(self.sidebar.menu_buttons["Settings"])

    def open_notifications_window(self):
        """Ouvre la fenêtre de notifications."""
        logger.info("Opening Notifications window")
        # Crée et lance la fenêtre de notifications
        if hasattr(self, 'notifications_window') and self.notifications_window.winfo_exists():
            self.notifications_window.lift()
            self.notifications_window.focus_force()
        else:
            self.notifications_window = NotificationsApp(self)
            self.notifications_window.grab_set()    # Rend la fenêtre modale
            
            # Attendre la fermeture pour rafraîchir le badge
            def on_window_close():
                self.notifications_window.destroy()
                if hasattr(self.header, 'refresh_notification_badge'):
                    self.header.refresh_notification_badge()
            
            self.notifications_window.protocol("WM_DELETE_WINDOW", on_window_close)

    def toggle_sidebar(self, collapsed):
        """Réduire ou agrandir la sidebar"""
        if collapsed:
            new_width = self.COLLAPSED_SIDEBAR_WIDTH
            self.sidebar.collapse()
        else:
            new_width = self.SIDEBAR_WIDTH
            self.sidebar.expand()
        
        self.grid_columnconfigure(0, weight=0, minsize=new_width)
        self.update_idletasks()
        self.header.update_toggle_icon(collapsed)
        logger.info(f"Sidebar {'collapsed' if collapsed else 'expanded'}")

    def refresh_header_user_info(self):
        try:
            if not self.winfo_exists():
                return
            user_data = settings_controller.get_user_profile()
            self.header.update_user_info(user_data)
            
            # Rafraîchir le badge de notification
            if hasattr(self.header, 'refresh_notification_badge'):
                self.header.refresh_notification_badge()
        except Exception:
            pass
            
        # Reprogrammer le rafraîchissement dans 30 secondes (si l'app existe encore)
        try:
            if self.winfo_exists():
                self.after(30000, self.refresh_header_user_info)
        except Exception:
            pass

    def on_settings_saved(self, user_data):
        logger.info("Settings saved - updating header")
        self.header.update_user_info(user_data)

    def handle_menu_click(self, menu_name):
        user_role = self.logged_in_user.get('role_name') if self.logged_in_user else None
        is_technician = str(user_role).upper() in ["IT_TECHNICIAN", "IT_TECHNICIEN"]
        
        if menu_name == "Dashboard":
            if is_technician:
                logger.warning("Access to Dashboard denied for IT_TECHNICIAN")
                return
            self.show_dashboard_view()
            self.sidebar.set_active_button(self.sidebar.menu_buttons["Dashboard"])
        elif menu_name == "Inventory":
            self.show_inventory_view()
            self.sidebar.set_active_button(self.sidebar.menu_buttons["Inventory"])
        elif menu_name == "Consumable":
            if is_technician:
                logger.warning("Access to Consumable denied for IT_TECHNICIAN")
                return
            self.show_supplies_view()
            self.sidebar.set_active_button(self.sidebar.menu_buttons["Consumable"])
        elif menu_name == "Settings":
            self.show_settings_view()
            self.sidebar.set_active_button(self.sidebar.menu_buttons["Settings"])
        elif menu_name == "Map":  
            self.show_map_view()
            self.sidebar.set_active_button(self.sidebar.menu_buttons["Map"])
        elif menu_name == "Help":
            self.show_help_view()
            self.sidebar.set_active_button(self.sidebar.menu_buttons["Help"])
        elif menu_name == "Leave":
            self.handle_leave()

    def clear_content(self):
        if self.current_view:
            try:
                self.current_view.destroy()
            except Exception:
                pass
            self.current_view = None

    def show_dashboard_view(self):
        self.clear_content()
        self.current_view = DashboardView(self.content_frame, on_stat_click=self.navigate_to_inventory)
        self.current_view.grid(row=0, column=0, sticky="nsew")

    def show_inventory_view(self, filters=None):
        self.clear_content()
        user_role = self.logged_in_user.get('role_name') if self.logged_in_user else None
        self.current_view = InventoryView(self.content_frame, initial_filters=filters, user_role=user_role)
        self.current_view.grid(row=0, column=0, sticky="nsew")

    def show_supplies_view(self):
        self.clear_content()
        self.current_view = SuppliesView(self.content_frame)
        self.current_view.grid(row=0, column=0, sticky="nsew")

    def navigate_to_inventory(self, filter_type: str):
        if filter_type.startswith("map:"):
            room_name = filter_type.replace("map:", "")
            logger.info(f"Navigating to Map with room: {room_name}")
            self.show_map_view(room_name=room_name)
            self.sidebar.set_active_button(self.sidebar.menu_buttons["Map"])
            return
        
        if filter_type == "supplies":
            self.show_supplies_view()
            self.sidebar.set_active_button(self.sidebar.menu_buttons["Consumable"])
            return
        
        if filter_type.startswith("category:"):
            category = filter_type.replace("category:", "")
            logger.info(f"Navigating to Inventory with category filter: {category}")
            filters = {"category": [category]}
            self.show_inventory_view(filters=filters)
            self.sidebar.set_active_button(self.sidebar.menu_buttons["Inventory"])
            return

        filters_map = {
            "total":       None,
            "active":      {"status": ["ACTIVE"]},
            "warranty":    {"warranty_expiring": True},
            "lent_out":    {"status": ["LENT OUT"]},
            "available":   {"status": ["AVAILABLE"]},
            "maintenance": {"status": ["MAINTENANCE"]},
        }

        filters = filters_map.get(filter_type, None)
        self.show_inventory_view(filters=filters)
        self.sidebar.set_active_button(self.sidebar.menu_buttons["Inventory"])
    
    def show_settings_view(self, initial_page="personal"):
        self.clear_content()
        self.current_view = SettingsView(
            self.content_frame,
            on_save_callback=self.on_settings_saved,
            initial_page=initial_page,
            on_timer_format_change=self.on_timer_format_change
        )
        self.current_view.grid(row=0, column=0, sticky="nsew")
    
    def on_timer_format_change(self, is_24h):
        if hasattr(self, 'header') and self.header:
            self.header.set_timer_format(is_24h)

    def show_map_view(self, room_name=None):
        self.clear_content()
        self.current_view = FacilityMapView(self.content_frame, initial_room=room_name)
        self.current_view.grid(row=0, column=0, sticky="nsew")

    def show_help_view(self):
        self.clear_content()
        self.current_view = HelpView(self.content_frame)
        self.current_view.grid(row=0, column=0, sticky="nsew")

    def handle_leave(self):
        def actually_leave():
            self.quit()
            self.destroy()
            import sys
            sys.exit(0)

        show_confirm_toast(
            parent=self,
            message="Are you sure you want to leave?",
            on_confirm=actually_leave,
            on_cancel=None
        )

    def on_search(self, query):
        pass


def main():
    print("=" * 50)
    print("[OK] Demarrage de TechManage...")
    print("=" * 50)

    login_window = [None]

    def on_login_success(user_data):
        print("[OK] Connexion reussie - Chargement de l'application...")

        if login_window[0]:
            login_window[0].destroy()
            login_window[0] = None

        print("[OK] Interface chargee avec succes!")
        app = TechManageApp(logged_in_user=user_data)
        app.mainloop()

    print("[OK] Chargement de la page de connexion...")
    login = LoginApp(on_login_success=on_login_success)
    login_window[0] = login
    login.mainloop()


if __name__ == "__main__":
    main()
