"""
frontend/app/views/map.py

Vue de la Facility Map - Affiche la carte des installations avec les équipements.
Connectée à la base de données via map_controller.
"""
import os
import sys
import logging
from pathlib import Path

import customtkinter as ctk
from PIL import Image

# Configuration du chemin
_project_root = Path(__file__).resolve().parents[3]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

logger = logging.getLogger(__name__)

ICONS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "assets", "icons"))


def _get_display_room_name(room_name: str) -> str:
    """
    Mapping d'affichage des noms de rooms sans toucher aux valeurs en base.
    
    - ADMINISTRATION (DB) -> affiché comme "CEO BUREAU"
    - CEO BUREAU (DB)    -> affiché comme "ADMINISTRATION"
    - tout le reste      -> inchangé
    """
    upper = (room_name or "").upper()
    if upper == "ADMINISTRATION":
        return "CEO BUREAU"
    if upper == "CEO BUREAU":
        return "ADMINISTRATION"
    return room_name


def _get_display_room_icon(room_name: str, icon_name: str | None) -> str | None:
    """
    Mapping d'affichage des icônes pour rester cohérent avec les noms pivotés.
    
    On raisonne sur le NOM AFFICHÉ (après pivot éventuel), pas sur la valeur DB.
    
    - "CEO BUREAU"    -> icône "crown"
    - "ADMINISTRATION" -> icône "command"
    - tout le reste    -> icône inchangée
    """
    display = (_get_display_room_name(room_name) or "").upper()
    if display == "CEO BUREAU":
        return "crown"
    if display == "ADMINISTRATION":
        return "command"
    return icon_name


def update_room_capacity(room_name: str, new_capacity: int) -> bool:
    """Met à jour la capacité d'une room via le controller et retourne True si succès"""
    try:
        from controllers import map_controller
        success = map_controller.update_room_capacity(room_name, new_capacity)
        if success:
            logger.info(f"[OK] Capacite mise a jour pour {room_name}: {new_capacity}")
        else:
            logger.warning(f"[ERREUR] Echec de la mise a jour pour {room_name}")
        return success
    except Exception:
        logger.exception("Erreur lors de la mise à jour de la capacité")
        return False


class RoomDetailsPopup(ctk.CTkToplevel):
    """Fenêtre popup pour afficher les détails d'une zone"""
    
    THEME = {
        "bg": "#F0F4F9",
        "primary": "#166FFF",
        "text_dark": "#1E293B",
        "text_gray": "#9CA3AF",
        "text_medium": "#6B7280",
        "white": "#FFFFFF",
        "blue": "#4B9EFF",
        "green": "#16A34A",
        "red": "#DF3D3D",
        "orange": "#F59E0B",
        "light_blue": "#E0F2FE",
        "light_green": "#DCFDEC",
        "light_red": "#FDECEC",
        "light_orange": "#FEF3C7",
    }

    def __init__(self, parent, room_name: str, equipment: list, consumables: list = None, max_capacity: int = None, icon_name: str = None, on_capacity_changed=None, user_role=None):
        super().__init__(parent)

        self.room_name = room_name
        self.display_room_name = _get_display_room_name(room_name)
        self.equipment = equipment
        self.consumables = consumables or []
        self.max_capacity = max_capacity
        # Appliquer le mapping d'icône pour l'affichage
        self.icon_name = _get_display_room_icon(room_name, icon_name)
        self.total_items = len(equipment) + len(self.consumables)
        self.user_role = user_role
        self._icon_cache = {}
        self._on_capacity_changed = on_capacity_changed
        
        # Vérifier si c'est une section A, B ou C
        self.is_section_abc = room_name.upper() in ["SECTION A", "SECTION B", "SECTION C"]
        
        # IT_TECHNICIAN always sees simple view (no consumables)
        if self.user_role == "IT_TECHNICIAN":
            self.is_section_abc = False

        self.title(f"{self.display_room_name} - Equipment Details")
        
        # Taille réduite selon le type de section
        if self.is_section_abc:
            self.geometry("950x750")
        else:
            self.geometry("480x650")
            
        self.configure(fg_color=self.THEME["bg"])
        
        # Centrer la fenêtre
        self.update_idletasks()
        if self.is_section_abc:
            x = (self.winfo_screenwidth() // 2) - (950 // 2)
            y = (self.winfo_screenheight() // 2) - (750 // 2)
            self.geometry(f"950x750+{x}+{y}")
        else:
            x = (self.winfo_screenwidth() // 2) - (480 // 2)
            y = (self.winfo_screenheight() // 2) - (650 // 2)
            self.geometry(f"480x650+{x}+{y}")
        
        self.transient(parent)
        self.grab_set()
        
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        
        self._create_ui()
    
    def _on_close(self):
        """Called when window is closed"""
        self.grab_release()
        self.destroy()

    def _create_ui(self):
        """Créer l'interface de la popup"""
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        # Padding réduit en bas pour que la liste occupe tout l'espace
        main_frame.pack(fill="both", expand=True, padx=20, pady=(20, 5))
        
        # Header
        self.header_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        self.header_frame.pack(fill="x", pady=(0, 20))
        
        header_content = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        header_content.pack(fill="x", padx=0, pady=15)
        
        # Icône
        icon_frame = ctk.CTkFrame(header_content, fg_color=self.THEME["primary"], corner_radius=12, width=50, height=50)
        icon_frame.pack(side="left", padx=(0, 15))
        icon_frame.pack_propagate(False)
        
        if self.icon_name:
            icon_suffix = "_white" if self.icon_name in ["zap", "lock", "package", "crown", "command", "bell", "building"] else ""
            icon_img = self._load_icon(f"{self.icon_name}{icon_suffix}", (28, 28))
            if icon_img:
                ctk.CTkLabel(icon_frame, image=icon_img, text="", fg_color="transparent").place(relx=0.5, rely=0.5, anchor="center")
        
        # Titre
        ctk.CTkLabel(header_content, text=self.display_room_name, font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"),
                     text_color=self.THEME["text_dark"], anchor="w").pack(side="left", fill="x", expand=True)
        
        # Stats cards (Hidden for IT_TECHNICIAN)
        if self.user_role != "IT_TECHNICIAN":
            stats_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
            stats_frame.pack(fill="x", pady=(0, 20))
            stats_frame.grid_columnconfigure((0, 1), weight=1)
            
            # Count card
            count_card = ctk.CTkFrame(stats_frame, fg_color=self.THEME["light_blue"], corner_radius=20, border_width=1.5, border_color="#BAE6FD")
            count_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
            
            count_content = ctk.CTkFrame(count_card, fg_color="transparent")
            count_content.pack(fill="both", expand=True, padx=20, pady=12)
            
            ctk.CTkLabel(count_content, text="EQUIPMENT COUNT", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                         text_color=self.THEME["blue"], anchor="w").pack(anchor="w")
            
            count_frame = ctk.CTkFrame(count_content, fg_color="transparent")
            count_frame.pack(anchor="w", pady=(5, 0))
            
            ctk.CTkLabel(count_frame, text=str(self.total_items), font=ctk.CTkFont(family="Segoe UI", size=32, weight="bold"),
                         text_color=self.THEME["text_dark"]).pack(side="left", pady=(0, 10))
            
            ctk.CTkLabel(count_frame, text=" UNITS", font=ctk.CTkFont(family="Segoe UI", size=12),
                         text_color=self.THEME["text_gray"]).pack(side="left", anchor="s", pady=(0, 10))
            
            # Occupancy card
            occ_status = self._get_occupancy_status()
            occupancy_card = ctk.CTkFrame(stats_frame, fg_color=self._get_occ_color(occ_status), corner_radius=20,
                                          border_width=1, border_color=self._get_occ_border(occ_status))
            occupancy_card.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
            
            occ_content = ctk.CTkFrame(occupancy_card, fg_color="transparent")
            occ_content.pack(fill="both", expand=True, padx=20, pady=12)
            
            occ_header = ctk.CTkFrame(occ_content, fg_color="transparent")
            occ_header.pack(fill="x")
            
            ctk.CTkLabel(occ_header, text="OCCUPANCY", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                         text_color=self._get_occ_text(occ_status), anchor="w").pack(side="left")
            
            # Row avec le statut et le bouton modifier
            occ_status_row = ctk.CTkFrame(occ_content, fg_color="transparent")
            occ_status_row.pack(fill="x", pady=(10, 0))
            
            ctk.CTkLabel(occ_status_row, text=occ_status, font=ctk.CTkFont(family="Segoe UI", size=21, weight="bold", slant="italic"),
                         text_color=self._get_occ_text(occ_status), anchor="w").pack(side="left")
            
            # Bouton modifier capacité (icône sliders-horizontal)
            edit_icon = self._load_icon("sliders-horizontal", (20, 20))
            if edit_icon:
                edit_btn = ctk.CTkButton(
                    occ_status_row,
                    image=edit_icon,
                    text="",
                    fg_color=self.THEME["white"],
                    hover_color=self.THEME["light_blue"],
                    border_width=1.5,
                    border_color=self.THEME["primary"],
                    width=36,
                    height=36,
                    corner_radius=10,
                    command=self._toggle_capacity_editor
                )
            else:
                edit_btn = ctk.CTkButton(
                    occ_status_row,
                    text="⚙",
                    font=ctk.CTkFont(size=16),
                    fg_color=self.THEME["white"],
                    hover_color=self.THEME["light_blue"],
                    border_width=1.5,
                    border_color=self.THEME["primary"],
                    text_color=self.THEME["primary"],
                    width=36,
                    height=36,
                    corner_radius=10,
                    command=self._toggle_capacity_editor
                )
            edit_btn.pack(side="right")
        
            # Container pour modifier la capacité (entre les stats cards et la liste)
            self.capacity_editor = ctk.CTkFrame(main_frame, fg_color=self.THEME["light_blue"], corner_radius=16,
                                                border_width=2, border_color="#BAE6FD")
            self.capacity_editor.pack(fill="x", pady=(0, 20))
            self.capacity_editor.pack_forget()
            
            editor_content = ctk.CTkFrame(self.capacity_editor, fg_color="transparent")
            editor_content.pack(fill="x", padx=20, pady=18)
            
            ctk.CTkLabel(editor_content, text="OCCUPANCY THRESHOLD", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                         text_color=self.THEME["primary"]).pack(anchor="w", pady=(0, 12))
            
            # Row avec le champ et le bouton
            threshold_row = ctk.CTkFrame(editor_content, fg_color="transparent")
            threshold_row.pack(fill="x")
            
            # Container pour l'entrée avec icône
            entry_container = ctk.CTkFrame(threshold_row, fg_color=self.THEME["white"], corner_radius=12,
                                           border_width=1.5, border_color="#E5E7EB", width=80, height=45)
            entry_container.pack(side="left", padx=(0, 12))
            entry_container.pack_propagate(False)
            
            self.capacity_entry = ctk.CTkEntry(
                entry_container,
                placeholder_text=str(self.max_capacity) if self.max_capacity else "10",
                width=50,
                height=35,
                corner_radius=0,
                border_width=0,
                fg_color="transparent",
                font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                justify="center"
            )
            self.capacity_entry.place(relx=0.5, rely=0.5, anchor="center")
            self.capacity_entry.insert(0, str(self.max_capacity) if self.max_capacity else "10")
            
            # Bouton UPDATE THRESHOLD
            update_btn = ctk.CTkButton(
                threshold_row,
                text="UPDATE THRESHOLD",
                font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                fg_color=self.THEME["primary"],
                hover_color="#1258CC",
                text_color=self.THEME["white"],
                height=45,
                corner_radius=12,
                command=self._save_capacity
            )
            update_btn.pack(side="left", fill="x", expand=True)
        
        # Container principal - 2 colonnes pour sections A/B/C, 1 colonne pour les autres
        if self.is_section_abc:
            # Deux colonnes pour Section A, B, C
            self.inventory_container = ctk.CTkFrame(main_frame, fg_color="transparent")
            self.inventory_container.pack(fill="both", expand=True)
            self.inventory_container.grid_columnconfigure(0, weight=1)
            self.inventory_container.grid_columnconfigure(1, weight=1)
            
            # ========== COLONNE 1: INVENTORY ==========
            inventory_col = ctk.CTkFrame(self.inventory_container, fg_color="transparent")
            inventory_col.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
            
            # Header Inventory
            inventory_header = ctk.CTkFrame(inventory_col, fg_color="transparent")
            inventory_header.pack(fill="x", pady=(0, 10))
            
            menu_img = self._load_icon("menu", (18, 18))
            if menu_img:
                ctk.CTkLabel(inventory_header, image=menu_img, text="", fg_color="transparent").pack(side="left", padx=(0, 8))
            
            ctk.CTkLabel(inventory_header, text="INVENTORY", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                         text_color=self.THEME["text_gray"], anchor="w").pack(side="left")
            
            # Container Inventory
            inventory_container = ctk.CTkFrame(inventory_col, fg_color=self.THEME["white"], corner_radius=20, border_width=1.5, border_color="#E5E7EB")
            inventory_container.pack(fill="both", expand=True)
            
            inventory_frame = ctk.CTkScrollableFrame(inventory_container, fg_color="transparent", corner_radius=0, border_width=0,
                                                     scrollbar_fg_color=self.THEME["white"], scrollbar_button_color="#CBD5E1",
                                                     scrollbar_button_hover_color=self.THEME["text_gray"])
            inventory_frame.pack(fill="both", expand=True, padx=8, pady=15)
            
            if self.equipment:
                for item in self.equipment:
                    self._create_equipment_card(inventory_frame, item)
            else:
                ctk.CTkLabel(inventory_frame, text="No equipment", font=ctk.CTkFont(family="Segoe UI", size=14),
                            text_color=self.THEME["text_gray"]).pack(pady=40)
            
            # ========== COLONNE 2: CONSUMABLE ==========
            consumable_col = ctk.CTkFrame(self.inventory_container, fg_color="transparent")
            consumable_col.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
            
            # Header Consommable
            consumable_header = ctk.CTkFrame(consumable_col, fg_color="transparent")
            consumable_header.pack(fill="x", pady=(0, 10))
            
            package_img = self._load_icon("package", (18, 18))
            if package_img:
                ctk.CTkLabel(consumable_header, image=package_img, text="", fg_color="transparent").pack(side="left", padx=(0, 8))
            
            ctk.CTkLabel(consumable_header, text="CONSUMABLE", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                         text_color=self.THEME["text_gray"], anchor="w").pack(side="left")
            
            # Container Consommable
            consumable_container = ctk.CTkFrame(consumable_col, fg_color=self.THEME["white"], corner_radius=20, border_width=1.5, border_color="#E5E7EB")
            consumable_container.pack(fill="both", expand=True)
            
            consumable_frame = ctk.CTkScrollableFrame(consumable_container, fg_color="transparent", corner_radius=0, border_width=0,
                                                      scrollbar_fg_color=self.THEME["white"], scrollbar_button_color="#CBD5E1",
                                                      scrollbar_button_hover_color=self.THEME["text_gray"])
            consumable_frame.pack(fill="both", expand=True, padx=8, pady=15)
            
            if self.consumables:
                for item in self.consumables:
                    self._create_consumable_card_abc(consumable_frame, item)
            else:
                ctk.CTkLabel(consumable_frame, text="No consumables", font=ctk.CTkFont(family="Segoe UI", size=14),
                            text_color=self.THEME["text_gray"]).pack(pady=40)
        else:
            # Une seule colonne pour les autres sections
            self.inventory_container = ctk.CTkFrame(main_frame, fg_color="transparent")
            self.inventory_container.pack(fill="both", expand=True)
            
            # Header
            list_header = ctk.CTkFrame(self.inventory_container, fg_color="transparent")
            list_header.pack(fill="x", pady=(0, 15))
            
            menu_img = self._load_icon("menu", (18, 18))
            if menu_img:
                ctk.CTkLabel(list_header, image=menu_img, text="", fg_color="transparent").pack(side="left", padx=(0, 8))
            
            ctk.CTkLabel(list_header, text="EQUIPMENT INVENTORY", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                         text_color=self.THEME["text_gray"], anchor="w").pack(side="left")
            
            # Container
            container = ctk.CTkFrame(self.inventory_container, fg_color=self.THEME["white"], corner_radius=20, border_width=1.5, border_color="#E5E7EB")
            container.pack(fill="both", expand=True)
            
            frame = ctk.CTkScrollableFrame(container, fg_color="transparent", corner_radius=0, border_width=0,
                                           scrollbar_fg_color=self.THEME["white"], scrollbar_button_color="#CBD5E1",
                                           scrollbar_button_hover_color=self.THEME["text_gray"])
            frame.pack(fill="both", expand=True, padx=8, pady=15)
            
            if self.equipment:
                for item in self.equipment:
                    self._create_equipment_card(frame, item)
            else:
                ctk.CTkLabel(frame, text="No equipment in this location", font=ctk.CTkFont(family="Segoe UI", size=14),
                            text_color=self.THEME["text_gray"]).pack(pady=40)

    def _create_equipment_card(self, parent, item: dict):
        """Créer une carte d'équipement"""
        card = ctk.CTkFrame(parent, fg_color=self.THEME["bg"], corner_radius=17, border_width=1.5, border_color="#E5E7EB")
        card.pack(fill="x", padx=15, pady=(15, 0))
        
        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill="x", padx=12, pady=12)
        
        # Icône
        icon_frame = ctk.CTkFrame(content, fg_color="#F9FAFB", corner_radius=10, width=40, height=40)
        icon_frame.pack(side="left", padx=(5, 12))
        icon_frame.pack_propagate(False)
        
        eq_icon = self._load_icon(item.get('icon', 'monitor'), (20, 20))
        if eq_icon:
            ctk.CTkLabel(icon_frame, image=eq_icon, text="", fg_color="transparent").place(relx=0.5, rely=0.5, anchor="center")
        
        # Info
        info_frame = ctk.CTkFrame(content, fg_color="transparent")
        info_frame.pack(side="left", fill="x", expand=True)
        
        ctk.CTkLabel(info_frame, text=item.get('name', 'Unknown').upper(), font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                     text_color=self.THEME["text_dark"], anchor="w").pack(anchor="w")
        
        detail_frame = ctk.CTkFrame(info_frame, fg_color="transparent")
        detail_frame.pack(anchor="w")
        
        ctk.CTkLabel(detail_frame, text=item.get('id', 'N/A'), font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                     text_color=self.THEME["primary"], anchor="w").pack(side="left", padx=(0, 10))
        
        ctk.CTkLabel(detail_frame, text=item.get('serial', 'N/A'), font=ctk.CTkFont(family="Segoe UI", size=11),
                     text_color=self.THEME["text_gray"], anchor="w").pack(side="left")
        
        # Status badge
        status = item.get('status', '').upper()
        text_color, border_color, bg_color = self._status_colors(status)
        
        badge = ctk.CTkFrame(content, fg_color=bg_color, border_color=border_color, border_width=1.5, corner_radius=10, height=31, width=110)
        badge.pack(side="right", padx=(12, 0))
        badge.pack_propagate(False)
        
        ctk.CTkLabel(badge, text=status, text_color=text_color, font=ctk.CTkFont(family="Tahoma", size=10, weight="bold"),
                     fg_color="transparent").pack(expand=True)
    
    def _create_consumable_card(self, parent, item: dict):
        """Créer une carte de consommable"""
        card = ctk.CTkFrame(parent, fg_color=self.THEME["bg"], corner_radius=17, border_width=1.5, border_color="#E5E7EB")
        card.pack(fill="x", padx=15, pady=(15, 0))
        
        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill="x", padx=12, pady=12)
        
        # Icône
        icon_frame = ctk.CTkFrame(content, fg_color="#F9FAFB", corner_radius=10, width=40, height=40)
        icon_frame.pack(side="left", padx=(5, 12))
        icon_frame.pack_propagate(False)
        
        # Icône selon la catégorie
        category_icons = {
            "PRINTING": "droplet",
            "CABLES": "cable",
            "ADAPTERS": "hdmi-port",
            "PERIPHERALS": "mouse",
            "STORAGE_MEDIA": "database",
            "POWER_CHARGING": "battery-charging"
        }
        icon_name = category_icons.get(item.get('category', ''), 'package')
        con_icon = self._load_icon(icon_name, (20, 20))
        if con_icon:
            ctk.CTkLabel(icon_frame, image=con_icon, text="", fg_color="transparent").place(relx=0.5, rely=0.5, anchor="center")
        
        # Info
        info_frame = ctk.CTkFrame(content, fg_color="transparent")
        info_frame.pack(side="left", fill="x", expand=True)
        
        ctk.CTkLabel(info_frame, text=item.get('name', 'Unknown').upper(), font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                     text_color=self.THEME["text_dark"], anchor="w").pack(anchor="w")
        
        detail_frame = ctk.CTkFrame(info_frame, fg_color="transparent")
        detail_frame.pack(anchor="w")
        
        ctk.CTkLabel(detail_frame, text=item.get('category', 'N/A'), font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                     text_color=self.THEME["primary"], anchor="w").pack(side="left", padx=(0, 10))
        
        ctk.CTkLabel(detail_frame, text=f"Qty: {item.get('in_storage', 0)}", font=ctk.CTkFont(family="Segoe UI", size=11),
                     text_color=self.THEME["text_gray"], anchor="w").pack(side="left")
        
        # Status badge pour consommable
        status = item.get('status', '').upper()
        text_color, border_color, bg_color = self._consumable_status_colors(status)
        
        badge = ctk.CTkFrame(content, fg_color=bg_color, border_color=border_color, border_width=1.5, corner_radius=10, height=31, width=110)
        badge.pack(side="right", padx=(12, 0))
        badge.pack_propagate(False)
        
        ctk.CTkLabel(badge, text=status, text_color=text_color, font=ctk.CTkFont(family="Tahoma", size=10, weight="bold"),
                     fg_color="transparent").pack(expand=True)
    
    def _consumable_status_colors(self, status):
        """Retourne les couleurs pour le statut d'un consommable"""
        colors = {
            "STOCKED": ("#16A34A", "#86EFAC", "#DCFCE7"),
            "CRITICAL": ("#F59E0B", "#FCD34D", "#FEF3C7"),
            "OUT": ("#DC2626", "#FCA5A5", "#FEE2E2")
        }
        return colors.get(status, (self.THEME["text_medium"], "#E5E7EB", "#F3F4F6"))
    
    def _create_consumable_card_abc(self, parent, item: dict):
        """Créer une carte de consommable pour Section A/B/C avec badge de statut (style inventory)"""
        card = ctk.CTkFrame(parent, fg_color=self.THEME["bg"], corner_radius=17, border_width=1.5, border_color="#E5E7EB")
        card.pack(fill="x", padx=15, pady=(15, 0))
        
        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill="x", padx=12, pady=12)
        
        # Icône
        icon_frame = ctk.CTkFrame(content, fg_color="#F9FAFB", corner_radius=10, width=40, height=40)
        icon_frame.pack(side="left", padx=(5, 12))
        icon_frame.pack_propagate(False)
        
        # Icône selon la catégorie
        category_icons = {
            "PRINTING": "droplet",
            "CABLES": "cable",
            "ADAPTERS": "hdmi-port",
            "PERIPHERALS": "mouse",
            "STORAGE_MEDIA": "database",
            "POWER_CHARGING": "battery-charging"
        }
        icon_name = category_icons.get(item.get('category', ''), 'package')
        con_icon = self._load_icon(icon_name, (20, 20))
        if con_icon:
            ctk.CTkLabel(icon_frame, image=con_icon, text="", fg_color="transparent").place(relx=0.5, rely=0.5, anchor="center")
        
        # Info
        info_frame = ctk.CTkFrame(content, fg_color="transparent")
        info_frame.pack(side="left", fill="x", expand=True)
        
        ctk.CTkLabel(info_frame, text=item.get('name', 'Unknown').upper(), font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                     text_color=self.THEME["text_dark"], anchor="w").pack(anchor="w")
        
        detail_frame = ctk.CTkFrame(info_frame, fg_color="transparent")
        detail_frame.pack(anchor="w")
        
        ctk.CTkLabel(detail_frame, text=item.get('category', 'N/A'), font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                     text_color=self.THEME["primary"], anchor="w").pack(side="left", padx=(0, 10))
        
        ctk.CTkLabel(detail_frame, text=f"Qty: {item.get('in_storage', 0)}", font=ctk.CTkFont(family="Segoe UI", size=11),
                     text_color=self.THEME["text_gray"], anchor="w").pack(side="left")
        
        # Status badge (matching inventory style)
        status = item.get('status', '').upper()
        text_color, border_color, bg_color = self._consumable_status_colors(status)
        
        badge = ctk.CTkFrame(content, fg_color=bg_color, border_color=border_color, border_width=1.5, corner_radius=10, height=31, width=110)
        badge.pack(side="right", padx=(12, 0))
        badge.pack_propagate(False)
        
        ctk.CTkLabel(badge, text=status, text_color=text_color, font=ctk.CTkFont(family="Tahoma", size=10, weight="bold"),
                     fg_color="transparent").pack(expand=True)

    def _status_colors(self, status):
        colors = {
            "ACTIVE": ("#1CBD87", "#C6EFE0", "#F0FBF7"),
            "MAINTENANCE": ("#F59E0B", "#FCE8C5", "#FEF9F0"),
            "AVAILABLE": ("#3B82F6", "#CEDEFB", "#F0F4FC"),
            "LENT OUT": ("#EF4444", "#FBD2D2", "#FEF3F3")
        }
        for key in colors:
            if key in status:
                return colors[key]
        return (self.THEME["text_medium"], "#E5E7EB", "#F3F4F6")

    def _get_occupancy_status(self):
        if self.total_items == 0:
            return "NONE"
        if not self.max_capacity:
            return "NORMAL"
        pct = (self.total_items / self.max_capacity) * 100
        if pct >= 90:
            return "HIGH"
        elif pct >= 70:
            return "MEDIUM"
        return "NORMAL"

    def _get_occ_color(self, status):
        return {"NONE": "#F3F4F6", "NORMAL": self.THEME["light_green"], "MEDIUM": "#FEF3C7",
                "HIGH": self.THEME["light_red"]}.get(status, self.THEME["light_green"])

    def _get_occ_border(self, status):
        return {"NONE": "#D1D5DB", "NORMAL": "#86EFAC", "MEDIUM": "#F59E0B",
                "HIGH": "#FCA5A5"}.get(status, "#86EFAC")

    def _get_occ_text(self, status):
        return {"NONE": self.THEME["text_gray"], "NORMAL": self.THEME["green"], "MEDIUM": "#F59E0B",
                "HIGH": self.THEME["red"]}.get(status, self.THEME["green"])
    
    def _toggle_capacity_editor(self):
        """Affiche ou cache l'éditeur de capacité"""
        if self.capacity_editor.winfo_ismapped():
            self.capacity_editor.pack_forget()
        else:
            # Afficher le container avant la liste d'inventaire (2ème ligne)
            self.capacity_editor.pack(fill="x", pady=(0, 20), before=self.inventory_container)
            self.capacity_entry.focus()
    
    def _save_capacity(self):
        """Sauvegarde la nouvelle capacité et rafraîchit immédiatement"""
        try:
            new_capacity = int(self.capacity_entry.get())
            if new_capacity < 0:
                new_capacity = 0
        except ValueError:
            return
        
        if update_room_capacity(self.room_name, new_capacity):
            self.max_capacity = new_capacity
            self.capacity_entry.delete(0, "end")
            self.capacity_entry.insert(0, str(new_capacity))
            self.capacity_editor.pack_forget()
            
            # Rafraîchir la carte principale pour mettre à jour les couleurs
            self._refresh_parent_map()
            
            # Recharger les données depuis la base et rafraîchir la popup
            self._reload_and_refresh_popup()

            # Appeler le callback si défini
            if self._on_capacity_changed:
                self._on_capacity_changed()
    
    def _reload_and_refresh_popup(self):
        """Recharge les données depuis la base et rafraîchit la popup"""
        try:
            from controllers import map_controller
            # Recharger les données de la room depuis la base
            room_data = map_controller.get_room_details(self.room_name)
            if room_data:
                self.equipment = room_data["equipment"]
                self.consumables = room_data.get("consumables", [])
                self.max_capacity = room_data["max_capacity"]
        except Exception as e:
            logger.error(f"Erreur lors du rechargement des données: {e}")
        
        # Rafraîchir l'affichage de la popup
        self._refresh_ui()
    
    def _refresh_ui(self):
        """Rafraîchit l'affichage de la popup avec les nouvelles données"""
        parent = self.master
        x = self.winfo_x()
        y = self.winfo_y()
        self.destroy()
        # Créer une nouvelle popup avec les données à jour et la même position
        new_popup = RoomDetailsPopup(
            parent,
            self.room_name,
            self.equipment,
            self.consumables,
            self.max_capacity,
            self.icon_name,
            on_capacity_changed=self._on_capacity_changed,
            user_role=self.user_role
        )
        # Taille différente selon le type de section
        if self.is_section_abc:
            new_popup.geometry(f"1100x750+{x}+{y}")
        else:
            new_popup.geometry(f"550x650+{x}+{y}")
    
    def _refresh_parent_map(self):
        """Rafraîchit la vue map principale pour mettre à jour les couleurs"""
        # Chercher la fenêtre principale
        root = self.winfo_toplevel()
        
        # Fonction récursive pour chercher la FacilityMapView
        def find_map_view(widget):
            if hasattr(widget, 'reload_data') and hasattr(widget, 'facility_data'):
                return widget
            for child in widget.winfo_children():
                result = find_map_view(child)
                if result:
                    return result
            return None
        
        # Chercher et rafraîchir la vue map
        map_view = find_map_view(root)
        if map_view:
            try:
                map_view.reload_data()
                logger.info("[OK] Carte rafraîchie après modification de capacité")
            except Exception as e:
                logger.error(f"[ERREUR] Impossible de rafraîchir la carte: {e}")

    def _load_icon(self, name, size=(32, 32)):
        if not name:
            return None
        key = f"{name}_{size[0]}x{size[1]}"
        if key in self._icon_cache:
            return self._icon_cache[key]
        for fname in [f"{name}.png", f"{name}.jpg", f"{name}_icon.png"]:
            path = os.path.join(ICONS_DIR, fname)
            if os.path.exists(path):
                try:
                    img = Image.open(path).convert("RGBA").resize(size)
                    ctk_img = ctk.CTkImage(light_image=img, size=size)
                    self._icon_cache[key] = ctk_img
                    return ctk_img
                except:
                    break
        self._icon_cache[key] = None
        return None


class FacilityMapView(ctk.CTkFrame):
    """Vue de la carte des installations - Connectée à la base de données"""
    
    THEME = {
        "bg": "#F0F4F9",
        "primary": "#166FFF",
        "text_dark": "#1E293B",
        "text_gray": "#9CA3AF",
        "text_medium": "#6B7280",
        "white": "#FFFFFF",
        "zone_green": "#DCFBEB",
        "zone_red": "#FDECEC",
        "zone_gray": "#F3F4F6",
        "zone_orange": "#FEF3C7"
    }

    def __init__(self, parent, initial_room=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.configure(fg_color=self.THEME["bg"], corner_radius=0)
        self.pack(fill="both", expand=True)
        self._icon_cache = {}
        self.initial_room = initial_room  # ← AJOUT

        from controllers import settings_controller
        self.user_role = settings_controller.get_user_role()

        self._load_data()
        self._create_ui()

    def _load_data(self):
        """Charger les données depuis la base de données"""
        try:
            from controllers import map_controller
            self.facility_data = map_controller.get_facility_data()
            self.total_equipment = sum(z["total_items"] for z in self.facility_data)
            self.total_locations = len(self.facility_data)
        except Exception:
            logger.exception("Failed to load facility data")
            self.facility_data = []
            self.total_equipment = 0
            self.total_locations = 0

    def reload_data(self):
        """Recharger les données"""
        self._load_data()
        for widget in self.winfo_children():
            widget.destroy()
        self._create_ui()

    def _create_ui(self):
        """Créer l'interface"""
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=40, pady=40)
        
        # Titre
        title_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        title_frame.pack(fill="x", pady=(0, 20))
        
        ctk.CTkLabel(title_frame, text="FACILITY", font=ctk.CTkFont(family="Segoe UI", size=32, weight="bold"),
                     text_color=self.THEME["text_dark"], anchor="w").pack(side="left")
        
        ctk.CTkLabel(title_frame, text=" MAP", font=ctk.CTkFont(family="Segoe UI", size=32, weight="bold"),
                     text_color=self.THEME["primary"], anchor="w").pack(side="left")
        
        # Stats
        is_technician = str(self.user_role).upper() in ["IT_TECHNICIAN", "IT_TECHNICIEN"]
        if not is_technician:
            stats_frame = ctk.CTkFrame(title_frame, fg_color="transparent")
            stats_frame.pack(side="right")
            
            ctk.CTkLabel(stats_frame, text=f"{self.total_equipment} Equipment  •  {self.total_locations} Locations",
                         font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                         text_color=self.THEME["text_gray"]).pack()
        
        # Container principal
        container = ctk.CTkFrame(main_frame, fg_color=self.THEME["white"], corner_radius=35, border_width=2, border_color="#E5E7EB")
        container.pack(fill="both", expand=True)
        
        if not self.facility_data:
            ctk.CTkLabel(container, text="No facility data available", font=ctk.CTkFont(family="Segoe UI", size=16),
                        text_color=self.THEME["text_gray"]).pack(pady=50)
            return
        
        # Grille
        grid = ctk.CTkFrame(container, fg_color="transparent")
        grid.pack(fill="both", expand=True, padx=30, pady=30)
        
        for i in range(4):
            grid.grid_columnconfigure(i, weight=1, uniform="zone")
            grid.grid_rowconfigure(i, weight=1, uniform="row")
        
        # Positions des zones
        positions = [
            (0, 0, 1, 1), (0, 1, 1, 1), (0, 3, 3, 1), (1, 1, 2, 1),
            (1, 0, 2, 1), (3, 0, 1, 1), (0, 2, 1, 1),
            (1, 2, 1, 1),
            (2, 2, 1, 1), (3, 1, 1, 3),
        ]
        
        for i, (row, col, rowspan, colspan) in enumerate(positions):
            if i < len(self.facility_data):
                card = self._create_zone_card(grid, self.facility_data[i])
                pad_right = 10 if col < 3 else 0
                pad_bottom = 10 if row < 3 else 0
                card.grid(row=row, column=col, rowspan=rowspan, columnspan=colspan, sticky="nsew",
                         padx=(0, pad_right), pady=(0, pad_bottom))
            
        if self.initial_room:
            self.after(200, lambda: self._open_room_popup(self.initial_room))

    def _open_room_popup(self, room_name):
        """Ouvrir la popup d'une room spécifique"""
        # Chercher la zone correspondante
        is_technician = str(self.user_role).upper() in ["IT_TECHNICIAN", "IT_TECHNICIEN"]
        for zone in self.facility_data:
            if zone["name"].upper() == room_name.upper():
                # For IT_TECHNICIAN, only open if there are items (MAINTENANCE filtered in load_data)
                if is_technician and zone["total_items"] == 0:
                    logger.warning(f"IT_TECHNICIAN tried to open empty room: {room_name}")
                    return

                logger.info(f"Opening popup for room: {room_name}")
                RoomDetailsPopup(
                    self.winfo_toplevel(),
                    zone["name"],
                    zone["equipment"],
                    zone.get("consumables", []),
                    zone["max_capacity"],
                    zone["icon"],
                    on_capacity_changed=self.reload_data,
                    user_role=self.user_role
                )
                return

        # Si la room n'existe pas, logger un warning
        logger.warning(f"Room '{room_name}' not found in facility data")
    
    def _create_zone_card(self, parent, zone: dict):
        """Créer une carte de zone"""
        name = zone["name"]
        display_name = _get_display_room_name(name)
        equipment = zone["equipment"]
        consumables = zone.get("consumables", [])
        max_capacity = zone["max_capacity"]
        icon = zone["icon"]
        items_count = zone["total_items"]
        
        # Couleurs selon l'occupation
        is_technician = str(self.user_role).upper() in ["IT_TECHNICIAN", "IT_TECHNICIEN"]
        is_clickable = True
        if items_count == 0:
            bg, hover, border = self.THEME["zone_gray"], "#F9FAFB", "#D1D5DB"
            if is_technician:
                is_clickable = False
        elif max_capacity and items_count >= max_capacity:
            # HIGH (>= 100% ou >= 90% selon ta logique)
            bg, hover, border = self.THEME["zone_red"], "#FEF2F2", "#FCA5A5"
        elif max_capacity and items_count >= max_capacity * 0.7:
            # MEDIUM (entre 70% et 100%)
            bg, hover, border = self.THEME["zone_orange"], "#FFFBEB", "#F59E0B"
        else:
            # NORMAL (< 70%)
            bg, hover, border = self.THEME["zone_green"], "#ECFDF5", "#86EFAC"
        
        card_cursor = "hand2" if is_clickable else ""
        card = ctk.CTkFrame(parent, fg_color=bg, corner_radius=20, border_width=1.5, border_color=border, cursor=card_cursor)
        card._orig = bg
        card._hover = hover
        
        def on_enter(e):
            if is_clickable:
                card.configure(fg_color=card._hover)
        def on_leave(e):
            card.configure(fg_color=card._orig)
        def on_click(e):
            if is_clickable:
                disp_icon = _get_display_room_icon(name, icon)
                RoomDetailsPopup(self.winfo_toplevel(), name, equipment, consumables, max_capacity, disp_icon, on_capacity_changed=self.reload_data, user_role=self.user_role)
        
        card.bind("<Enter>", on_enter)
        card.bind("<Leave>", on_leave)
        card.bind("<Button-1>", on_click)
        
        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=10, pady=10)
        
        center = ctk.CTkFrame(content, fg_color="transparent")
        center.place(relx=0.5, rely=0.5, anchor="center")
        
        for w in [content, center]:
            w.bind("<Enter>", on_enter)
            w.bind("<Leave>", on_leave)
            w.bind("<Button-1>", on_click)
        
        # Icône (avec mapping d'affichage éventuel)
        disp_icon = _get_display_room_icon(name, icon)
        icon_img = self._load_icon(disp_icon, (32, 32))
        if icon_img:
            lbl = ctk.CTkLabel(center, image=icon_img, text="", fg_color="transparent")
            lbl.pack(anchor="center", pady=(0, 10))
            lbl.bind("<Enter>", on_enter)
            lbl.bind("<Leave>", on_leave)
            lbl.bind("<Button-1>", on_click)
        
        # Nom
        name_box = ctk.CTkFrame(center, fg_color=self.THEME["white"], corner_radius=12)
        name_box.pack(anchor="center", pady=(0, 8))
        name_box.bind("<Enter>", on_enter)
        name_box.bind("<Leave>", on_leave)
        name_box.bind("<Button-1>", on_click)
        
        name_lbl = ctk.CTkLabel(name_box, text=display_name, font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                                text_color=self.THEME["text_medium"], anchor="center")
        name_lbl.pack(padx=10, pady=0)
        name_lbl.bind("<Enter>", on_enter)
        name_lbl.bind("<Leave>", on_leave)
        name_lbl.bind("<Button-1>", on_click)
        
        # Count
        if items_count > 0:
            count_lbl = ctk.CTkLabel(center, text=f"({items_count})", font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                                     text_color=self.THEME["text_medium"], anchor="center")
            count_lbl.pack(anchor="center")
            count_lbl.bind("<Enter>", on_enter)
            count_lbl.bind("<Leave>", on_leave)
            count_lbl.bind("<Button-1>", on_click)
        
        return card

    def _load_icon(self, name, size=(32, 32)):
        if not name:
            return None
        key = f"{name}_{size[0]}x{size[1]}"
        if key in self._icon_cache:
            return self._icon_cache[key]
        for fname in [f"{name}.png", f"{name}.jpg", f"{name}_icon.png"]:
            path = os.path.join(ICONS_DIR, fname)
            if os.path.exists(path):
                try:
                    img = Image.open(path).convert("RGBA").resize(size)
                    ctk_img = ctk.CTkImage(light_image=img, size=size)
                    self._icon_cache[key] = ctk_img
                    return ctk_img
                except:
                    break
        self._icon_cache[key] = None
        return None
