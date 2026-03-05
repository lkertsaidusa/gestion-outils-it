import customtkinter as ctk
import tkinter as tk
import uuid
from tkinter import messagebox

import sys
import os
import logging
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageTk # Added PIL imports

# Add root path for imports
_project_root = Path(__file__).resolve().parents[3]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from controllers import consumable_controller # Import consumable_controller
from app.components.toast_success import show_success_toast # Import toast vert
from app.components.toast_error import show_error_toast # Import toast rouge
from app.components.delete_window import DeleteConfirmationWindow # Import fenêtre de confirmation

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO) # Ensure logging is configured

# Shared ICONS_DIR (moved to module level for wider access)
ICONS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "assets", "icons"))

# Application Theme Palette (Unified with SuppliesView)
THEME = {
    "bg": "#F0F4F9",
    "primary": "#166FFF",
    "primary_hover": "#5899FA",
    "text_dark": "#1E293B",
    "text_gray": "#9CA3AF",
    "text_medium": "#4B5563",
    "border": "#E5E7EB",
    "white": "#FFFFFF",
    "card_bg": "#FBFCFD",
    "icon_bg": "#F1F1F1",
    "row_hover": "#F8FAFC",
    "success_bg": "#F0FDF4",
    "success_text": "#2FC967",
    "warning_bg": "#FFF7ED",
    "warning_text": "#F97316",
    "inactive_bg": "#E5E7EB",
    "inactive_text": "#6B7280",
    # Specific colors from RegisterSupplyModal's original THEME
    "gray_dark": "#1E293B", 
    "gray_medium": "#CBD5E1",
    "gray_light": "#F8FAFC",
    "blue_active": "#2563EB",
    "blue_light": "#EFF6FF",
    "emerald": "#00C389", 
    "emerald_bg": "#ECFDF5",
    "red_soft": "#FFF1F2",
    "red_text": "#E11D48",
    "orange_bg": "#FFFBEB",
    "orange_text": "#D97706",
    "navy": "#0F172A",
    "text_dark": "#1E293B", # Duplicated, already "text_dark"
    "text_gray": "#94A3B8", # Duplicated, already "text_gray"
}

CATEGORIES = [
    "PRINTING", "CABLES", "ADAPTERS", 
    "PERIPHERALS", "STORAGE_MEDIA", "POWER_CHARGING"
]

CATEGORY_ICONS = {
    "PRINTING": "droplet",
    "CABLES": "cable", 
    "ADAPTERS": "hdmi-port",
    "PERIPHERALS": "mouse",
    "STORAGE_MEDIA": "database (2)",
    "POWER_CHARGING": "battery-charging"
}

# --- Helper functions for AnimatedSearchBar (from InventoryView) ---
def hex_to_rgb(hex_color: str):
    """Convertit une couleur hex en RGB tuple"""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))

def rgb_to_hex(rgb):
    """Convertit un tuple RGB en couleur hex"""
    return "#{:02x}{:02x}{:02x}".format(*rgb)

def lerp_color(a_hex, b_hex, t: float):
    """Interpolation linéaire entre deux couleurs hex (t entre 0 et 1)"""
    a = hex_to_rgb(a_hex)
    b = hex_to_rgb(b_hex)
    return rgb_to_hex(tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3)))

class AnimatedSearchBar(ctk.CTkFrame):
    """Barre de recherche avec animations de bordure et placeholder"""
    
    # Configuration visuelle
    SEARCH_WIDTH = 460
    SEARCH_HEIGHT = 60
    SEARCH_CORNER = 16
    
    # Bordure animée quand focus
    PILL_BORDER_COLOR = "#166FFF"
    PILL_BORDER_WIDTH_FOCUS = 3
    PILL_BORDER_WIDTH_NORMAL = 0
    PILL_BG = "#FFFFFF"
    
    # Paramètres d'animation
    _ANIM_STEPS = 4
    _ANIM_INTERVAL_MS = 12
    
    def __init__(self, parent, on_search=None, icons_dir=None, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.configure(fg_color="transparent")
        self.on_search = on_search
        self._images = {}
        
        if icons_dir:
            self.ICONS_DIR = icons_dir
        else:
            self.ICONS_DIR = ICONS_DIR
        
        # État des animations
        self._border_anim_job = None
        self._placeholder_anim_job = None
        self._border_progress = 0.0
        self._placeholder_progress = 1.0
        
        self._create_search_bar()
        
        try:
            parent.winfo_toplevel().bind("<Button-1>", self._on_global_click, add="+")
        except Exception:
            logger.exception("Could not bind global click")
    
    def _load_icon(self, candidates, size=(36, 36)):
        """Charge une icône depuis une liste de noms candidats"""
        for name in candidates:
            path = os.path.join(self.ICONS_DIR, name)
            if os.path.exists(path):
                try:
                    img = Image.open(path).convert("RGBA")
                    img = img.resize(size)
                    photo = ImageTk.PhotoImage(img)
                    self._images[path] = photo
                    return photo
                except Exception:
                    logger.exception("Error loading icon %s", path)
        return None
    
    def _create_search_bar(self):
        """Créer la barre de recherche avec icône statique et placeholder/bordure animés"""
        
        # Container principal de la search pill (un seul frame, bordure animée dessus)
        self.search_frame = ctk.CTkFrame(
            self,
            fg_color=self.PILL_BG,
            corner_radius=self.SEARCH_CORNER,
            height=self.SEARCH_HEIGHT,
            border_width=self.PILL_BORDER_WIDTH_NORMAL,
            border_color=self.PILL_BORDER_COLOR
        )
        self.search_frame.pack(fill="x", expand=True)
        self.search_frame.configure(width=self.SEARCH_WIDTH)
        self.search_frame.pack_propagate(False)
        self.search_frame.grid_columnconfigure(1, weight=1)
        
        # Icône de recherche (statique)
        search_icon = self._load_icon(
            ["search.png", "icon-search.png", "search_icon.png"],
            size=(36, 36)
        )
        if search_icon:
            icon_label = ctk.CTkLabel(
                self.search_frame,
                image=search_icon,
                text="",
                fg_color=self.PILL_BG
            )
            icon_label.grid(row=0, column=0, padx=(25, 8), pady=(17, 17))
        else:
            # Fallback emoji si pas d'icône trouvée
            icon_label = ctk.CTkLabel(
                self.search_frame,
                text="",
                fg_color=self.PILL_BG
            )
            icon_label.grid(row=0, column=0, padx=(25, 8), pady=(17, 17))
            # Load search icon
            try:
                search_path = os.path.join(self.ICONS_DIR, "search.png")
                search_img = Image.open(search_path).convert("RGBA")
                search_img = search_img.resize((18, 18))
                search_icon = ctk.CTkImage(light_image=search_img, dark_image=search_img, size=(18, 18))
                icon_label.configure(image=search_icon)
            except Exception:
                pass
        
        # Entry (sans placeholder_text car on gère le nôtre)
        inter_font = ctk.CTkFont(family="Segoe UI", size=14, weight="bold")
        self.search_entry = ctk.CTkEntry(
            master=self.search_frame,
            placeholder_text="",
            fg_color=self.PILL_BG,
            border_width=0,
            font=inter_font,
            text_color="#111827",
            width=self.SEARCH_WIDTH - 120
        )
        self.search_entry.grid(row=0, column=1, padx=(0, 20), pady=(10, 10), sticky="ew")
        
        # Label placeholder superposé (animé)
        placeholder_color = "#6B7280"
        self.placeholder_label = ctk.CTkLabel(
            self.search_frame,
            text="Search by name, serial ID, category…",
            font=inter_font,
            text_color=placeholder_color,
            fg_color=self.PILL_BG
        )
        self.placeholder_label.grid(row=0, column=1, padx=(4, 20), pady=(10, 10), sticky="w")
        self.placeholder_label.lift(self.search_entry)
        
        # Bindings pour les événements
        self.search_entry.bind("<FocusIn>", self._on_search_focus_in)
        self.search_entry.bind("<FocusOut>", self._on_search_focus_out)
        self.search_entry.bind("<KeyRelease>", self._on_search_key)
        self.search_entry.bind("<Return>", lambda e: self._perform_search())
        
        # Clic sur le frame/icône/placeholder -> focus l'entry
        def focus_entry(event):
            try:
                self.search_entry.focus_set()
            except Exception:
                pass
        
        self.search_frame.bind("<Button-1>", focus_entry)
        icon_label.bind("<Button-1>", focus_entry)
        self.placeholder_label.bind("<Button-1>", focus_entry)
        
        # État initial
        self._set_placeholder_progress(1.0, instant=True)
        self._set_border_progress(0.0, instant=True)
    
    # =====================================================================
    # ANIMATION DE LA BORDURE
    # =====================================================================
    
    def _set_border_progress(self, target, instant=False):
        """Anime la progression de la bordure entre 0 et 1"""
        if self._border_anim_job is not None:
            try:
                self.after_cancel(self._border_anim_job)
            except Exception:
                pass
            self._border_anim_job = None
        
        if instant:
            self._border_progress = float(target)
            self._apply_border_state()
            return
        
        start = self._border_progress
        steps = self._ANIM_STEPS
        
        def step(i):
            t = i / float(steps)
            prog = start + (target - start) * t
            self._border_progress = prog
            self._apply_border_state()
            
            if i < steps:
                self._border_anim_job = self.after(
                    self._ANIM_INTERVAL_MS,
                    lambda: step(i + 1)
                )
            else:
                self._border_anim_job = None
        
        step(0)
    
    def _apply_border_state(self):
        """Applique l'état de la bordure selon self._border_progress"""
        p = max(0.0, min(1.0, float(self._border_progress)))
        bw = int(round(self.PILL_BORDER_WIDTH_FOCUS * p))
        color = lerp_color(self.PILL_BG, self.PILL_BORDER_COLOR, p)
        
        try:
            self.search_frame.configure(border_width=bw, border_color=color)
        except Exception:
            try:
                self.search_frame.configure(border_width=bw)
            except Exception:
                pass
    
    # =====================================================================
    # ANIMATION DU PLACEHOLDER
    # =====================================================================
    
    def _set_placeholder_progress(self, target, instant=False):
        """Anime la visibilité du placeholder entre 0 et 1 (1=visible)"""
        if self._placeholder_anim_job is not None:
            try:
                self.after_cancel(self._placeholder_anim_job)
            except Exception:
                pass
            self._placeholder_anim_job = None
        
        if instant:
            self._placeholder_progress = float(target)
            self._apply_placeholder_state()
            return
        
        start = self._placeholder_progress
        steps = self._ANIM_STEPS
        
        def step(i):
            t = i / float(steps)
            prog = start + (target - start) * t
            self._placeholder_progress = prog
            self._apply_placeholder_state()
            
            if i < steps:
                self._placeholder_anim_job = self.after(
                    self._ANIM_INTERVAL_MS,
                    lambda: step(i + 1)
                )
            else:
                self._placeholder_anim_job = None
        
        step(0)
    
    def _apply_placeholder_state(self):
        """Applique la couleur du placeholder selon self._placeholder_progress"""
        p = max(0.0, min(1.0, float(self._placeholder_progress)))
        invisible = self.PILL_BG
        visible_color = "#6B7280"
        color = lerp_color(invisible, visible_color, p)
        
        try:
            self.placeholder_label.configure(text_color=color)
            
            if p <= 0.01:
                try:
                    self.placeholder_label.lower(self.search_entry)
                except Exception:
                    pass
            else:
                try:
                    self.placeholder_label.lift(self.search_entry)
                except Exception:
                    pass
        except Exception:
            pass
    
    # =====================================================================
    # GESTION DES ÉVÉNEMENTS
    # =====================================================================
    
    def _on_search_key(self, event=None):
        """Cache le placeholder quand du contenu est présent"""
        try:
            content = self.search_entry.get()
            if content.strip() != "":
                self._set_placeholder_progress(0.0)
            else:
                self._set_placeholder_progress(1.0)
        except Exception:
            pass
    
    def _on_search_focus_in(self, event=None):
        """Anime la bordure et cache le placeholder au focus"""
        self._set_border_progress(1.0)
        self._set_placeholder_progress(0.0)
    
    def _on_search_focus_out(self, event=None):
        """Anime la bordure et restaure le placeholder si vide"""
        self._set_border_progress(0.0)
        
        try:
            content = self.search_entry.get().strip()
        except Exception:
            content = ""
        
        if content == "":
            self._set_placeholder_progress(1.0)
    
    def _on_global_click(self, event):
        """Retire le focus si on clique en dehors de la search bar"""
        try:
            x_root = event.x_root
            y_root = event.y_root
            
            sx = self.search_frame.winfo_rootx()
            sy = self.search_frame.winfo_rooty()
            sw = self.search_frame.winfo_width()
            sh = self.search_frame.winfo_height()
            
            inside = (sx <= x_root <= sx + sw) and (sy <= y_root <= sy + sh)
            
            if not inside:
                try:
                    self.winfo_toplevel().focus_set()
                except Exception:
                    pass
        except Exception:
            pass
    
    def _perform_search(self):
        """Exécute la recherche et appelle le callback"""
        query = ""
        try:
            query = self.search_entry.get().strip()
        except Exception:
            query = ""
        
        if callable(self.on_search):
            try:
                self.on_search(query)
            except Exception:
                logger.exception("Error in on_search callback")
        else:
            logger.info("Search triggered: %s", query)
    
    def get_value(self):
        """Retourne la valeur actuelle de la search bar"""
        try:
            return self.search_entry.get()
        except Exception:
            return ""
    
    def set_value(self, text):
        """Définit la valeur de la search bar"""
        try:
            self.search_entry.delete(0, "end")
            self.search_entry.insert(0, text)
            self._on_search_key()
        except Exception:
            pass
    
    def clear(self):
        """Vide la search bar et restaure le placeholder"""
        self.set_value("")


class RegisterSupplyModal(ctk.CTkToplevel):
    def __init__(self, master, on_save, initial_data=None):
        super().__init__(master)
        self.title("")
        self.geometry("600x720")
        self.configure(fg_color=THEME["white"])
        self.on_save = on_save
        self.initial_data = initial_data

        self.transient(master)
        self.grab_set()
        self.resizable(False, False)

        # Centrer la fenêtre
        self.update_idletasks()
        x = master.winfo_x() + (master.winfo_width() - 600) // 2
        y = master.winfo_y() + (master.winfo_height() - 720) // 2
        self.geometry(f"+{x}+{y}")

        # Handle mapping between SQLite column names and modal variables
        limit_val = initial_data.get("limit_alert") if initial_data and "limit_alert" in initial_data else initial_data.get("limit", 5) if initial_data else 5

        self.selected_section = initial_data.get("section", "SECTION A") if initial_data else "SECTION A"

        # Local import to avoid circular dependency
        from controllers import map_controller
        
        # Charger les données de capacité des chambres
        try:
            facility_data = map_controller.get_facility_data()
            self.rooms_info = {room["name"]: {"full": room["max_capacity"] is not None and room["total_items"] >= room["max_capacity"], "current": room["total_items"], "max": room["max_capacity"]} for room in facility_data}
        except Exception as e:
            logger.error(f"Failed to load facility data for RegisterSupplyModal: {e}")
            self.rooms_info = {}

        # Si on est en mode ajout et que toutes les sections sont pleines,
        # on empêche l'ajout et on affiche un message d'erreur clair en anglais.
        if not self.initial_data:
            target_sections = ["SECTION A", "SECTION B", "SECTION C"]
            all_full = True
            for sec in target_sections:
                info = self.rooms_info.get(sec, {})
                if not info.get("full", False):
                    all_full = False
                    break

            if all_full:
                try:
                    show_error_toast(
                        self.winfo_toplevel(),
                        "Unable to add a new supply. All storage sections are currently full.",
                        duration=4000
                    )
                except Exception:
                    messagebox.showerror(
                        "Sections full",
                        "Unable to add a new supply. All storage sections are currently full."
                    )
                # Fermer immédiatement la fenêtre d'ajout
                self.after(50, self.destroy)
                return

        # Header avec icône et titre
        self.header = ctk.CTkFrame(self, fg_color="transparent", height=70)
        self.header.pack(fill="x", padx=30, pady=(25, 20))
        self.header.pack_propagate(False)

        # Icône dans le header - utiliser l'icône selon catégorie
        self.icon_box = ctk.CTkFrame(self.header, width=48, height=48, corner_radius=12, fg_color=THEME["blue_light"])
        self.icon_box.pack(side="left")
        self.icon_box.pack_propagate(False)
        
        # Charger l'icône selon la catégorie (inventory_white si aucune catégorie, sinon package_blue)
        initial_category = initial_data.get("category") if initial_data else ""
        if not initial_category:
            category_icon_name = "inventory_white"
        else:
            category_icon_name = "package_blue"
        
        try:
            icon_path = os.path.join(ICONS_DIR, f"{category_icon_name}.png")
            img = Image.open(icon_path).convert("RGBA")
            img = img.resize((24, 24))
            modal_icon = ctk.CTkImage(light_image=img, dark_image=img, size=(24, 24))
        except Exception:
            modal_icon = None
        self.modal_icon_lbl = ctk.CTkLabel(self.icon_box, image=modal_icon, text="")
        self.modal_icon_lbl.place(relx=0.5, rely=0.52, anchor="center")
        
        # Stocker la catégorie actuelle pour mise à jour
        self.current_category = initial_category

        # Titre et sous-titre
        self.title_group = ctk.CTkFrame(self.header, fg_color="transparent")
        self.title_group.pack(side="left", padx=15)

        # Titre dynamique selon mode edit ou add
        title_text = "EDIT SUPPLY" if initial_data else "REGISTER SUPPLY"
        ctk.CTkLabel(
            self.title_group,
            text=title_text,
            font=("Segoe UI", 18, "bold"),
            text_color=THEME["text_dark"]
        ).pack(anchor="w")
        ctk.CTkLabel(
            self.title_group,
            text="LOGISTICS INTERFACE",
            font=("Segoe UI", 10, "bold"),
            text_color=THEME["blue_active"]
        ).pack(anchor="w")

        # Footer avec boutons
        self.footer = ctk.CTkFrame(self, fg_color="transparent", height=60)
        self.footer.pack(fill="x", side="bottom", padx=30, pady=(15, 20))
        self.footer.pack_propagate(False)

        self.cancel_btn = ctk.CTkButton(
            self.footer,
            text="CANCEL",
            height=40,
            corner_radius=12,
            fg_color="#FFF1F2",
            text_color="#E11D48",
            font=("Segoe UI", 14, "bold"),
            hover_color="#FFE4E6",
            command=self.destroy
        )
        self.cancel_btn.pack(side="left", fill="both", expand=True, padx=(0, 8))

        self.confirm_btn = ctk.CTkButton(
            self.footer,
            text="CONFIRM",
            height=40,
            corner_radius=12,
            fg_color=THEME["blue_active"],
            text_color="white",
            font=("Segoe UI", 14, "bold"),
            hover_color="#1d4ed8",
            command=self.save
        )
        self.confirm_btn.pack(side="left", fill="both", expand=True, padx=(8, 0))
        
        # Binding Enter key pour confirmer
        self.bind("<Return>", lambda e: self.save())
        self.bind("<KP_Enter>", lambda e: self.save())

        # Body scrollable
        self.body = ctk.CTkScrollableFrame(self, fg_color="transparent", corner_radius=0)
        self.body.pack(fill="both", expand=True, padx=30, pady=(0, 10)) 

        # Supply Name Field
        self.name_label = ctk.CTkLabel(
            self.body,
            text="SUPPLY NAME",
            font=("Segoe UI", 11, "bold"),
            text_color=THEME["text_gray"]
        )
        self.name_label.pack(anchor="w", padx=0, pady=(10, 5))

        self.name_entry = ctk.CTkEntry(
            self.body,
            placeholder_text="E.G. CAT6 ETHERNET CABLE",
            height=50,
            corner_radius=16,
            border_width=2,
            border_color=THEME["border"],
            fg_color="#F8FAFC",
            font=("Segoe UI", 14, "bold"),
            text_color=THEME["text_dark"]
        )
        self.name_entry.pack(fill="x", pady=(0, 20), padx=0)
        
        def on_name_focus_in(event):
            self.name_entry.configure(border_color=THEME["primary"], border_width=2.5)
            self.name_label.configure(text_color=THEME["primary"])
        
        def on_name_focus_out(event):
            self.name_entry.configure(border_color=THEME["border"], border_width=2)
            self.name_label.configure(text_color=THEME["text_gray"])
        
        self.name_entry.bind("<FocusIn>", on_name_focus_in)
        self.name_entry.bind("<FocusOut>", on_name_focus_out)
        
        if initial_data:
            self.name_entry.insert(0, initial_data["name"])

        # Location Section
        ctk.CTkLabel(
            self.body,
            text="LOCATION",
            font=("Segoe UI", 11, "bold"),
            text_color=THEME["text_gray"]
        ).pack(anchor="w", padx=0, pady=(0, 5))

        self.loc_frame = ctk.CTkFrame(self.body, fg_color="transparent")
        self.loc_frame.pack(fill="x", padx=0, pady=(0, 20))
        self.loc_buttons = {}

        for i, sec in enumerate(["SECTION A", "SECTION B", "SECTION C"]):
            info = self.rooms_info.get(sec, {})
            is_full = info.get("full", False)
            
            # En mode EDIT, on autorise si la section est celle de l'item
            if self.initial_data and self.initial_data.get("section") == sec:
                is_full = False

            btn = ctk.CTkFrame(
                self.loc_frame,
                width=100,
                height=120,
                corner_radius=14,
                fg_color=THEME["red_soft"] if is_full else "#F8FAFC",
                border_width=1.5,
                border_color=THEME["red_text"] if is_full else THEME["border"],
                cursor="no" if is_full else "hand2"
            )
            btn.grid(row=0, column=i, padx=6, sticky="ew")
            self.loc_frame.grid_columnconfigure(i, weight=1)
            btn.pack_propagate(False)

            ibg = ctk.CTkFrame(btn, width=32, height=32, corner_radius=8, fg_color="white")
            ibg.place(relx=0.5, rely=0.35, anchor="center")
            ibg.pack_propagate(False)

            # Load icon for location button
            try:
                icon_name = "box_red.png" if is_full else "package_blue.png"
                loc_icon_path = os.path.join(ICONS_DIR, icon_name)
                loc_img = Image.open(loc_icon_path).convert("RGBA")
                loc_img = loc_img.resize((18, 18))
                loc_icon = ctk.CTkImage(light_image=loc_img, dark_image=loc_img, size=(18, 18))
            except Exception:
                loc_icon = None
            self.licon = ctk.CTkLabel(ibg, image=loc_icon, text="")
            self.licon.place(relx=0.5, rely=0.52, anchor="center")

            tlbl = ctk.CTkLabel(
                btn,
                text=sec + ("\n(FULL)" if is_full else ""),
                font=("Segoe UI", 10, "bold"),
                text_color="#E11D48" if is_full else THEME["text_gray"]
            )
            tlbl.place(relx=0.5, rely=0.75, anchor="center")

            chk = ctk.CTkLabel(
                btn,
                text="",
                font=("Segoe UI", 12, "bold"),
                text_color=THEME["blue_active"]
            )

            # Ne lier le clic que si la zone n'est pas pleine
            if not is_full:
                click_func = lambda e, s=sec: self.update_location(s)
                self._bind_click_recursive(btn, click_func)
                # Hover en bleu clair sur zones disponibles
                hover_enter = lambda e, s=sec: self._on_loc_hover_enter(s)
                hover_leave = lambda e, s=sec: self._on_loc_hover_leave(s)
                self._bind_hover_recursive(btn, hover_enter, hover_leave)
            else:
                # Hover en rouge sur zones saturées
                hover_enter = lambda e, s=sec: self._on_loc_hover_enter(s)
                hover_leave = lambda e, s=sec: self._on_loc_hover_leave(s)
                self._bind_hover_recursive(btn, hover_enter, hover_leave)
            
            self.loc_buttons[sec] = (btn, ibg, tlbl, chk, self.licon)
            
        self.update_location(self.selected_section)

        # Category Field
        ctk.CTkLabel(
            self.body,
            text="CATEGORY",
            font=("Segoe UI", 11, "bold"),
            text_color=THEME["text_gray"]
        ).pack(anchor="w", padx=0, pady=(0, 5))

        # Custom dropdown pour la catégorie (style add_window.py)
        self._create_category_dropdown()

        # Storage and Limit Row
        self.stepper_row = ctk.CTkFrame(self.body, fg_color="transparent")
        self.stepper_row.pack(fill="x", padx=0, pady=(0, 20))
        self.stepper_row.grid_columnconfigure(0, weight=1)
        self.stepper_row.grid_columnconfigure(1, weight=1)

        # IN STORAGE field
        storage_frame = ctk.CTkFrame(self.stepper_row, fg_color="transparent")
        storage_frame.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        self.storage_label = ctk.CTkLabel(
            storage_frame,
            text="IN STORAGE",
            font=("Segoe UI", 11, "bold"),
            text_color=THEME["text_gray"]
        )
        self.storage_label.pack(anchor="w", padx=0, pady=(0, 5))

        self.storage_entry = ctk.CTkEntry(
            storage_frame,
            placeholder_text="0",
            height=50,
            corner_radius=16,
            border_width=2,
            border_color=THEME["border"],
            fg_color="#F8FAFC",
            font=("Segoe UI", 14, "bold"),
            text_color=THEME["text_dark"],
            justify="center"
        )
        self.storage_entry.pack(fill="x", pady=0, padx=0)

        def on_storage_focus_in(event):
            self.storage_entry.configure(border_color=THEME["primary"], border_width=2.5)
            self.storage_label.configure(text_color=THEME["primary"])

        def on_storage_focus_out(event):
            self.storage_entry.configure(border_color=THEME["border"], border_width=2)
            self.storage_label.configure(text_color=THEME["text_gray"])

        self.storage_entry.bind("<FocusIn>", on_storage_focus_in)
        self.storage_entry.bind("<FocusOut>", on_storage_focus_out)

        if initial_data:
            self.storage_entry.insert(0, str(initial_data.get("in_storage", 0)))

        # LIMIT ALERT field
        limit_frame = ctk.CTkFrame(self.stepper_row, fg_color="transparent")
        limit_frame.grid(row=0, column=1, sticky="ew", padx=(6, 0))

        self.limit_label = ctk.CTkLabel(
            limit_frame,
            text="LIMIT ALERT",
            font=("Segoe UI", 11, "bold"),
            text_color=THEME["text_gray"]
        )
        self.limit_label.pack(anchor="w", padx=0, pady=(0, 5))

        self.limit_entry = ctk.CTkEntry(
            limit_frame,
            placeholder_text="5",
            height=50,
            corner_radius=16,
            border_width=2,
            border_color=THEME["border"],
            fg_color="#F8FAFC",
            font=("Segoe UI", 14, "bold"),
            text_color=THEME["text_dark"],
            justify="center"
        )
        self.limit_entry.pack(fill="x", pady=0, padx=0)

        def on_limit_focus_in(event):
            self.limit_entry.configure(border_color=THEME["primary"], border_width=2.5)
            self.limit_label.configure(text_color=THEME["primary"])

        def on_limit_focus_out(event):
            self.limit_entry.configure(border_color=THEME["border"], border_width=2)
            self.limit_label.configure(text_color=THEME["text_gray"])

        self.limit_entry.bind("<FocusIn>", on_limit_focus_in)
        self.limit_entry.bind("<FocusOut>", on_limit_focus_out)

        if initial_data:
            self.limit_entry.insert(0, str(limit_val))
        
        # Liste des entry fields pour la gestion du focus global
        self.entry_fields = [self.name_entry, self.storage_entry, self.limit_entry]
        
        # Binding global pour retirer le focus quand on clique en dehors
        self.bind("<Button-1>", self._on_global_click)
        self.body.bind("<Button-1>", self._on_global_click)
        self.header.bind("<Button-1>", self._on_global_click)
        self.footer.bind("<Button-1>", self._on_global_click)

    def _on_global_click(self, event):
        """Retire le focus si on clique en dehors des entry fields"""
        try:
            x_root = event.x_root
            y_root = event.y_root
            
            # Vérifier si le clic est dans l'une des entry fields
            clicked_inside_entry = False
            for entry in self.entry_fields:
                try:
                    ex = entry.winfo_rootx()
                    ey = entry.winfo_rooty()
                    ew = entry.winfo_width()
                    eh = entry.winfo_height()
                    
                    if (ex <= x_root <= ex + ew) and (ey <= y_root <= ey + eh):
                        clicked_inside_entry = True
                        break
                except Exception:
                    pass
            
            # Si on n'a pas cliqué dans une entry, retirer le focus
            if not clicked_inside_entry:
                try:
                    self.focus_set()
                except Exception:
                    pass
        except Exception:
            pass

    def _on_category_change(self, choice):
        self.current_category = choice
        if not choice:
            category_icon_name = "inventory_white"
        else:
            category_icon_name = "package_blue"
        try:
            icon_path = os.path.join(ICONS_DIR, f"{category_icon_name}.png")
            img = Image.open(icon_path).convert("RGBA")
            img = img.resize((24, 24))
            modal_icon = ctk.CTkImage(light_image=img, dark_image=img, size=(24, 24))
            self.modal_icon_lbl.configure(image=modal_icon, text="")
        except Exception:
            pass

    def _bind_click_recursive(self, widget, callback):
        widget.bind("<Button-1>", callback)
        for child in widget.winfo_children():
            self._bind_click_recursive(child, callback)

    def _bind_hover_recursive(self, widget, on_enter, on_leave):
        if on_enter is not None:
            widget.bind("<Enter>", on_enter, add="+")
        if on_leave is not None:
            widget.bind("<Leave>", on_leave, add="+")
        for child in widget.winfo_children():
            self._bind_hover_recursive(child, on_enter, on_leave)

    def _on_loc_hover_enter(self, section):
        """Gère le hover des sections A, B, C.
        - Bleu clair si disponible
        - Rouge si saturée
        """
        info = self.rooms_info.get(section, {})
        is_full = info.get("full", False)
        if self.initial_data and self.initial_data.get("section") == section:
            is_full = False

        btn_tuple = self.loc_buttons.get(section)
        if not btn_tuple:
            return

        b, ibg, tlbl, chk, licon = btn_tuple

        if is_full:
            # Hover rouge pour les zones saturées (plus marqué que l'état normal)
            try:
                b.configure(fg_color="#FECACA", border_width=2, border_color=THEME["red_text"])
                tlbl.configure(text_color=THEME["red_text"])
            except Exception:
                pass
        else:
            # Hover bleu clair sur zones disponibles (même si sélectionnées)
            try:
                b.configure(fg_color=THEME["blue_light"], border_width=1.5, border_color=THEME["blue_active"])
            except Exception:
                pass

    def _on_loc_hover_leave(self, section):
        """Restaure le style normal de LA section quittée après le hover."""
        info = self.rooms_info.get(section, {})
        is_full = info.get("full", False)
        if self.initial_data and self.initial_data.get("section") == section:
            is_full = False

        btn_tuple = self.loc_buttons.get(section)
        if not btn_tuple:
            return

        b, ibg, tlbl, chk, licon = btn_tuple

        if is_full:
            # Zone saturée : rester en rouge
            try:
                b.configure(fg_color=THEME["red_soft"], border_width=1.5, border_color=THEME["red_text"])
                ibg.configure(fg_color="white")
                tlbl.configure(text_color=THEME["red_text"])
            except Exception:
                pass
            return

        # Zone disponible : revenir à l'état "sélectionné" ou "normal"
        active = (section == self.selected_section)
        try:
            b.configure(
                fg_color="#F8FAFC",
                border_width=1.5,
                border_color=THEME["blue_active"] if active else THEME["border"]
            )
            ibg.configure(fg_color=THEME["blue_active"] if active else "white")
            tlbl.configure(text_color=THEME["blue_active"] if active else THEME["text_gray"])
        except Exception:
            pass

    def update_location(self, s):
        # Vérifier si la zone est pleine (sauf si c'est la zone actuelle en mode edit)
        info = self.rooms_info.get(s, {})
        is_full = info.get("full", False)
        if self.initial_data and self.initial_data.get("section") == s:
            is_full = False
            
        if is_full:
            return

        self.selected_section = s
        for k, (b, ibg, tlbl, chk, licon) in self.loc_buttons.items():
            active = k == s
            
            # Ne pas modifier le style des boutons FULL (qui doivent rester rouges)
            k_info = self.rooms_info.get(k, {})
            k_full = k_info.get("full", False)
            if self.initial_data and self.initial_data.get("section") == k:
                k_full = False
                
            if k_full:
                # Style + icône rouges pour les zones saturées
                b.configure(fg_color=THEME["red_soft"], border_width=1.5, border_color=THEME["red_text"])
                ibg.configure(fg_color="white")
                tlbl.configure(text_color=THEME["red_text"])
                try:
                    loc_icon_path = os.path.join(ICONS_DIR, "box_red.png")
                    loc_img = Image.open(loc_icon_path).convert("RGBA")
                    loc_img = loc_img.resize((18, 18))
                    loc_icon = ctk.CTkImage(light_image=loc_img, dark_image=loc_img, size=(18, 18))
                    licon.configure(image=loc_icon, text="")
                except Exception:
                    pass
                chk.place_forget()
                continue

            # Style de base : fond neutre + bordure grise.
            # La sélection est indiquée par le texte/icone et le check, pas par le fond.
            b.configure(
                fg_color="#F8FAFC",
                border_width=1.5,
                border_color=THEME["blue_active"] if active else THEME["border"]
            )
            ibg.configure(fg_color=THEME["blue_active"] if active else "white")
            tlbl.configure(text_color=THEME["blue_active"] if active else THEME["text_gray"])
            
            # Change icon based on selection: inventory_white if selected, package_blue if not
            try:
                icon_name = "inventory_white.png" if active else "package_blue.png"
                loc_icon_path = os.path.join(ICONS_DIR, icon_name)
                loc_img = Image.open(loc_icon_path).convert("RGBA")
                loc_img = loc_img.resize((18, 18))
                loc_icon = ctk.CTkImage(light_image=loc_img, dark_image=loc_img, size=(18, 18))
                licon.configure(image=loc_icon, text="")
            except Exception:
                pass
            
            if active: chk.place(relx=0.88, rely=0.18, anchor="center")
            else: chk.place_forget()

    def _create_category_dropdown(self):
        """Créer un dropdown personnalisé pour la catégorie (exactement comme add_window.py)"""
        container = ctk.CTkFrame(self.body, fg_color="transparent")
        container.pack(fill="x", pady=(0, 20), padx=0)
        
        dropdown_frame = ctk.CTkFrame(
            container,
            height=50,
            corner_radius=16,
            fg_color="#F7F9FB",
            border_width=1.5,
            border_color=THEME["border"]
        )
        dropdown_frame.pack(fill="x")
        dropdown_frame.pack_propagate(False)
        
        self.category_dropdown_frame = dropdown_frame
        
        self.category_var = ctk.StringVar(value="SELECT CATEGORY")
        
        selected_label = ctk.CTkLabel(
            dropdown_frame,
            textvariable=self.category_var,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=THEME["text_gray"],
            anchor="w"
        )
        selected_label.place(relx=0.05, rely=0.5, anchor="w")
        
        try:
            chevron_icon_path = os.path.join(ICONS_DIR, "chevron-down.png")
            chevron_icon = ctk.CTkImage(
                light_image=Image.open(chevron_icon_path),
                dark_image=Image.open(chevron_icon_path),
                size=(12, 12)
            )
            arrow_label = ctk.CTkLabel(
                dropdown_frame,
                image=chevron_icon,
                text=""
            )
            arrow_label.place(relx=0.92, rely=0.5, anchor="center")
        except Exception:
            arrow_label = ctk.CTkLabel(
                dropdown_frame,
                text="▼",
                font=ctk.CTkFont(size=10),
                text_color=THEME["text_gray"]
            )
            arrow_label.place(relx=0.92, rely=0.5, anchor="center")
        
        popup_window = {"window": None}
        
        def set_focus():
            dropdown_frame.configure(border_color=THEME["primary"], border_width=2)
        
        def remove_focus():
            dropdown_frame.configure(border_color=THEME["border"], border_width=1.5)
        
        def toggle_dropdown(event=None):
            if popup_window["window"] and popup_window["window"].winfo_exists():
                popup_window["window"].destroy()
                popup_window["window"] = None
                remove_focus()
                return
            
            set_focus()
            
            popup = ctk.CTkToplevel(self)
            popup.wm_overrideredirect(True)
            popup.configure(fg_color=THEME["white"])
            popup_window["window"] = popup
            
            dropdown_frame.update_idletasks()
            x = dropdown_frame.winfo_rootx()
            y = dropdown_frame.winfo_rooty() + dropdown_frame.winfo_height() + 5
            
            popup_container = ctk.CTkFrame(
                popup,
                fg_color=THEME["white"],
                corner_radius=14,
                border_width=1.5,
                border_color="#E5E7EB"
            )
            popup_container.pack(padx=2, pady=2)
            
            list_width = 480
            actual_height = 220
            
            scroll_frame = ctk.CTkScrollableFrame(
                popup_container,
                fg_color=THEME["white"],
                width=list_width,
                height=actual_height,
                scrollbar_button_color="#CBD5E1",
                scrollbar_button_hover_color="#9CA3AF"
            )
            scroll_frame.pack(padx=(8, 2), pady=8)
            
            def select_option(option):
                self.category_var.set(option)
                selected_label.configure(text_color=THEME["text_dark"])
                popup.destroy()
                popup_window["window"] = None
                remove_focus()
                self._on_category_change(option)
            
            for option in CATEGORIES:
                is_current = (self.category_var.get() == option)
                
                option_btn = ctk.CTkButton(
                    scroll_frame,
                    text=option,
                    font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                    fg_color=THEME["primary"] if is_current else "transparent",
                    hover_color=THEME["primary_hover"] if is_current else "#F3F4F6",
                    text_color=THEME["white"] if is_current else THEME["text_dark"],
                    anchor="w",
                    height=32,
                    corner_radius=8,
                    command=lambda opt=option: select_option(opt)
                )
                option_btn.pack(fill="x", pady=2, padx=4)
            
            popup.update_idletasks()
            popup.geometry(f"+{x}+{y}")
            
            def on_popup_click(e):
                try:
                    if popup.winfo_exists():
                        widget = e.widget
                        if widget not in [dropdown_frame, selected_label, arrow_label]:
                            popup.destroy()
                            popup_window["window"] = None
                            remove_focus()
                except:
                    pass
            
            popup.after(100, lambda: popup.bind_all("<Button-1>", on_popup_click, add="+"))
            popup.focus_force()
        
        dropdown_frame.bind("<Button-1>", toggle_dropdown)
        selected_label.bind("<Button-1>", toggle_dropdown)
        arrow_label.bind("<Button-1>", toggle_dropdown)
        
        dropdown_frame.configure(cursor="hand2")
        selected_label.configure(cursor="hand2")
        arrow_label.configure(cursor="hand2")
        
        if self.initial_data:
            category_val = self.initial_data.get("category", "")
            if category_val:
                self.category_var.set(category_val)
                selected_label.configure(text_color=THEME["text_dark"])
                self._on_category_change(category_val)

    def save(self):
        name = self.name_entry.get().strip().upper()
        category = self.category_var.get()

        # Validation: champs vides
        if not name or not category:
            show_error_toast(self.winfo_toplevel(), "Supply name and category are required!", duration=3000)
            return

        # Validation: vérifier les doublons (si c'est un nouvel item)
        if not self.initial_data:
            # Récupérer tous les supplies existants
            all_supplies = consumable_controller.get_all_supplies()
            for supply in all_supplies:
                if supply["name"].upper() == name and supply["category"] == category:
                    show_error_toast(self.winfo_toplevel(), "This supply already exists in the same category!", duration=3000)
                    return

        # Get values from entry fields
        try:
            in_storage = int(self.storage_entry.get().strip() or "0")
            limit = int(self.limit_entry.get().strip() or "5")

            # Validate positive numbers
            if in_storage < 0 or limit < 0:
                show_error_toast(self.winfo_toplevel(), "Quantities must be positive numbers!", duration=3000)
                return

        except ValueError:
            show_error_toast(self.winfo_toplevel(), "Please enter valid numbers for storage and limit!", duration=3000)
            return

        # Validation: vérifier si la section est pleine
        info = self.rooms_info.get(self.selected_section, {})
        is_full = info.get("full", False)
        if self.initial_data and self.initial_data.get("section") == self.selected_section:
            is_full = False
            
        if is_full:
            show_error_toast(self.winfo_toplevel(), f"The section {self.selected_section} is full!", duration=3000)
            return

        status = "STOCKED" if in_storage >= limit else ("CRITICAL" if in_storage > 0 else "OUT")
        self.on_save({
            "id": self.initial_data["id"] if self.initial_data else str(uuid.uuid4()),
            "name": name,
            "category": category,
            "section": self.selected_section,
            "in_storage": in_storage,
            "limit_alert": limit,
            "status": status
        })
        self.after(50, self.destroy)

class SupplyCard(ctk.CTkFrame):
    def __init__(self, master, data, on_edit, on_delete, on_adjust, load_icon_method, **kwargs): # Added load_icon_method
        super().__init__(master, fg_color=THEME["white"], corner_radius=32, **kwargs)
        self.pack_propagate(False)
        self.configure(width=420, height=380)
        self.on_edit = on_edit
        self.on_delete = on_delete
        self.on_adjust = on_adjust
        self._load_icon_image = load_icon_method # Store the method
        self.setup_ui(data)

    def _truncate_name(self, name, max_len=15):
        """Tronque le nom à max_len caractères et ajoute '...' si nécessaire"""
        if len(name) > max_len:
            return name[:max_len] + "..."
        return name

    def setup_ui(self, data):
        self.ft = ctk.CTkFrame(self, fg_color="transparent")
        self.ft.pack(side="bottom", fill="x", padx=20, pady=(0, 30))

        ctk.CTkButton(self.ft, text="− DECREASE", height=60, corner_radius=16, fg_color=THEME["blue_light"], text_color=THEME["blue_active"], font=("Inter", 12, "bold"), hover_color="#DBEAFE", command=lambda: self.on_adjust(data["id"], -1)).pack(side="left", fill="both", expand=True, padx=(0, 10))
        ctk.CTkButton(self.ft, text="+ INCREASE", height=60, corner_radius=16, fg_color=THEME["blue_active"], text_color="white", font=("Inter", 12, "bold"), hover_color=THEME["primary_hover"], command=lambda: self.on_adjust(data["id"], 1)).pack(side="left", fill="both", expand=True, padx=(10, 0))

        self.status_bar = ctk.CTkFrame(self, height=60, corner_radius=12)
        self.status_bar.pack(side="bottom", fill="x", padx=20, pady=(0, 12))
        self.status_lbl = ctk.CTkLabel(self.status_bar, font=("Inter", 12, "bold"))
        self.status_lbl.place(relx=0.5, rely=0.5, anchor="center")

        self.sr = ctk.CTkFrame(self, fg_color="transparent")
        self.sr.pack(side="bottom", fill="x", padx=20, pady=(0, 12))
        self.vlabels = {}

        # IN STORAGE container
        self.f_storage = ctk.CTkFrame(self.sr, fg_color=THEME["gray_light"], corner_radius=16, border_width=0)
        self.f_storage.pack(side="left", fill="both", expand=True, padx=(0, 6))
        self.storage_label_title = ctk.CTkLabel(self.f_storage, text="IN STORAGE", font=("Inter", 9, "bold"), text_color=THEME["text_gray"])
        self.storage_label_title.pack(anchor="w", padx=15, pady=(8, 0))
        val_storage = ctk.CTkLabel(self.f_storage, text=str(data["in_storage"]), font=("Inter", 24, "bold"), text_color=THEME["text_dark"])
        val_storage.pack(anchor="center", padx=15, pady=(2, 14))
        self.vlabels["in_storage"] = val_storage

        # LIMIT ALERT container
        f_limit = ctk.CTkFrame(self.sr, fg_color=THEME["gray_light"], corner_radius=16)
        f_limit.pack(side="left", fill="both", expand=True, padx=(6, 0))
        ctk.CTkLabel(f_limit, text="LIMIT ALERT", font=("Inter", 9, "bold"), text_color=THEME["text_gray"]).pack(anchor="w", padx=15, pady=(8, 0))
        val_limit = ctk.CTkLabel(f_limit, text=f"< {data['limit_alert']}", font=("Inter", 24, "bold"), text_color=THEME["text_dark"])
        val_limit.pack(anchor="center", padx=15, pady=(2, 14))
        self.vlabels["limit_alert"] = val_limit

        self.header = ctk.CTkFrame(self, fg_color="transparent")
        self.header.pack(fill="x", padx=20, pady=(20, 0))

        # Container for icon and title on the same row
        self.title_row = ctk.CTkFrame(self.header, fg_color="transparent")
        self.title_row.pack(fill="x", side="left", expand=True)

        self.ib = ctk.CTkFrame(self.title_row, width=46, height=46, corner_radius=14, fg_color=THEME["blue_light"])
        self.ib.pack(side="left")
        self.ib.pack_propagate(False)

        # Load category icon image instead of emoji
        self.current_category = data["category"]
        icon_name = CATEGORY_ICONS.get(data["category"], "box_blue")
        self.icon_img = self._load_icon_image(icon_name, size=(22, 22))
        self.icon_lbl = ctk.CTkLabel(self.ib, image=self.icon_img, text="")
        self.icon_lbl.place(relx=0.5, rely=0.52, anchor="center")

        # Title next to icon - use truncated name for display
        truncated_name = self._truncate_name(data["name"])
        self.tl = ctk.CTkLabel(self.title_row, text=truncated_name, font=("Inter", 18, "bold"), text_color=THEME["text_dark"], anchor="w", wraplength=280, justify="left")
        self.tl.pack(side="left", fill="x", expand=True, padx=(12, 0))

        self.act = ctk.CTkFrame(self.header, fg_color="transparent", corner_radius=10)
        self.act.pack(side="right")
        edit_icon = self._load_icon_image("pen_gray", size=(16, 16))
        delete_icon = self._load_icon_image("trash_gray", size=(16, 16))

        ctk.CTkButton(self.act, text="", width=36, height=36, corner_radius=10, fg_color="#F3F4F6", border_width=0, image=edit_icon, hover_color="#E5E7EB", command=lambda: self.on_edit(data)).pack(side="left", padx=3)
        ctk.CTkButton(self.act, text="", width=36, height=36, corner_radius=10, fg_color="#F3F4F6", border_width=0, image=delete_icon, hover_color="#FEE2E2", command=lambda: self.on_delete(data["id"])).pack(side="left", padx=3)

        self.mr = ctk.CTkFrame(self, fg_color="transparent")
        self.mr.pack(fill="x", padx=20, pady=(8, 10))
        self.cat_txt_lbl = ctk.CTkLabel(self.mr, text=data["category"], font=("Inter", 10, "bold"), text_color=THEME["text_gray"])
        self.cat_txt_lbl.pack(side="left")
        
        self.sb = ctk.CTkFrame(self.mr, fg_color=THEME["blue_light"], corner_radius=8)
        self.sb.pack(side="left", padx=12)
        self.sl = ctk.CTkLabel(self.sb, text=data['section'], font=("Inter", 9, "bold"), text_color=THEME["blue_active"])
        self.sl.pack(padx=8, pady=3)
        self.current_data = data
        self.update_data(data)

    def update_data(self, data):
        self.current_data = data
        truncated_name = self._truncate_name(data["name"])
        self.tl.configure(text=truncated_name)
        self.cat_txt_lbl.configure(text=data["category"])
        if data["category"] != self.current_category:
            self.current_category = data["category"]
            icon_name = CATEGORY_ICONS.get(data["category"], "box_blue")
            self.icon_img = self._load_icon_image(icon_name, size=(22, 22))
            self.icon_lbl.configure(image=self.icon_img)
        self.vlabels["in_storage"].configure(text=str(data["in_storage"]))
        self.vlabels["limit_alert"].configure(text=f"< {data['limit_alert']}")

        # Update status bar and IN STORAGE container
        if data["status"] == "STOCKED":
            self.status_bar.configure(fg_color=THEME["emerald_bg"])
            self.status_lbl.configure(text="STOCKED", text_color=THEME["emerald"])
            # Reset IN STORAGE container to normal
            self.f_storage.configure(border_width=0, fg_color=THEME["gray_light"])
            self.storage_label_title.configure(text_color=THEME["text_gray"])
            self.vlabels["in_storage"].configure(text_color=THEME["text_dark"])
        elif data["status"] == "CRITICAL":
            self.status_bar.configure(fg_color=THEME["orange_bg"])
            self.status_lbl.configure(text="CRITICAL", text_color=THEME["orange_text"])
            # IN STORAGE container with orange border
            self.f_storage.configure(border_width=2, border_color=THEME["orange_text"], fg_color=THEME["orange_bg"])
            self.storage_label_title.configure(text_color=THEME["orange_text"])
            self.vlabels["in_storage"].configure(text_color=THEME["orange_text"])
        else:
            self.status_bar.configure(fg_color=THEME["red_soft"])
            self.status_lbl.configure(text="DEPLETED", text_color=THEME["red_text"])
            # IN STORAGE container with red border
            self.f_storage.configure(border_width=2, border_color=THEME["red_text"], fg_color=THEME["red_soft"])
            self.storage_label_title.configure(text_color=THEME["red_text"])
            self.vlabels["in_storage"].configure(text_color=THEME["red_text"])

class SuppliesView(ctk.CTkFrame): # Renamed from SuppliesApp
    ICONS_DIR = ICONS_DIR # Added ICONS_DIR to class
    THEME = THEME # Ensure class uses module-level THEME

    def __init__(self, master, initial_filters=None, **kwargs): # Added initial_filters
        super().__init__(master, **kwargs)
        self.configure(fg_color=self.THEME["bg"], corner_radius=0)
        self.pack(fill="both", expand=True)
        self._icon_cache = {} # Added for _load_icon_image

        # No direct DatabaseManager instantiation, use consumable_controller directly
        self.card_widgets = {} 
        self.empty_label = None

        self.current_filters = initial_filters # Initialize current_filters
        self.search_bar = None # Initialize search_bar (AnimatedSearchBar)

        # Removed direct header creation from here. It will be in _create_ui.
        
        self.supplies_data = [] # Will be loaded by _load_supplies_data
        
        self._create_ui() # Call _create_ui to build the interface

    def _load_supplies_data(self, filters=None):
        """Loads supplies data from the database using the search query from filters."""
        query = filters.get("q") if filters else None
        logger.info(f"Loading supplies data with query: {query}")
        self.supplies_data = consumable_controller.get_all_supplies(search_query=query)

    def reload_data(self, filters=None):
        logger.info("Reloading supplies data...")
        self._load_supplies_data(filters)
        
        # Clear existing widgets from the scrollable frame before re-rendering
        for widget in self.sf.winfo_children():
            widget.destroy()
        
        self.render_grid()
        logger.info("Supplies reloaded successfully")

    def _create_ui(self):
        # ==================== TITRE + LIGNE SÉPARATRICE (from InventoryView style) ====================
        title_container = ctk.CTkFrame(self, fg_color="transparent")
        title_container.pack(fill="x", padx=40, pady=(30, 0))
        
        title = ctk.CTkLabel(
            title_container,
            text="Supplies", # Title for this view
            font=ctk.CTkFont(family="Segoe UI", size=32, weight="bold"),
            text_color=self.THEME["text_dark"],
            anchor="w"
        )
        title.pack(fill="x")
        
        separator_line = ctk.CTkFrame(
            self,
            fg_color=self.THEME["border"],
            height=1
        )
        separator_line.pack(fill="x", padx=40, pady=(12, 0))
        
        # ==================== BARRE D'OUTILS (Search + Show All + Add Button) ====================
        toolbar = ctk.CTkFrame(self, fg_color="transparent", height=60)
        toolbar.pack(fill="x", padx=40, pady=(20, 20))
        toolbar.pack_propagate(False)
        
        # ── SEARCH BAR (à gauche) ──
        self.search_bar = AnimatedSearchBar(
            toolbar,
            on_search=self._on_search,
            icons_dir=self.ICONS_DIR
        )
        self.search_bar.pack(side="left", padx=(0, 12))

        # Restore search query if any
        if self.current_filters and self.current_filters.get("q"):
            self.search_bar.set_value(self.current_filters["q"])
        
        # ── BOUTON SHOW ALL ──
        show_all_icon = self._load_icon_image("rotate-ccw", size=(18, 18))
        
        show_all_btn = ctk.CTkButton(
            toolbar,
            text="Show all",
            image=show_all_icon,
            fg_color=self.THEME["white"],
            text_color="#6B7280",
            hover_color=self.THEME["row_hover"],
            corner_radius=15,
            height=60,
            width=140,
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            command=self._show_all,
            compound="left"
        )
        show_all_btn.pack(side="left", padx=(0, 0))
        
        # ── SPACER pour pousser le bouton ADD à droite ──
        spacer = ctk.CTkFrame(toolbar, fg_color="transparent")
        spacer.pack(side="left", fill="both", expand=True)

        # ── BOUTON ADD ITEM (à droite) ──
        add_icon = self._load_icon_image("plus-480", size=(18, 18))
        add_btn = ctk.CTkButton(
            toolbar,
            text="  Add item", # Changed text for supplies context
            text_color=self.THEME["white"],
            image=add_icon,
            fg_color=self.THEME["primary"],
            hover_color=self.THEME["primary_hover"],
            corner_radius=15,
            height=60,
            width=180,
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            command=self._add_consumable_item,
            compound="left"
        )
        add_btn.pack(side="right")
        
        # --- Scrollable Frame for cards ---
        self.sf = ctk.CTkScrollableFrame(self, fg_color=self.THEME["bg"], corner_radius=0)
        self.sf.pack(fill="both", expand=True, padx=(40, 40), pady=(0, 20))
        for i in range(3): self.sf.grid_columnconfigure(i, weight=1, uniform="group1")

        # Initial data load and render
        self._load_supplies_data(filters=self.current_filters)
        self.render_grid()

    def _on_search(self, query):
        """Callback for search bar in Supplies view."""
        logger.info(f"Supplies search query: '{query}'")
        filters = self.current_filters or {} # Ensure current_filters is a dict
        if query.strip():
            filters["q"] = query.strip()
        else:
            filters.pop("q", None) # Remove 'q' if query is empty
        self.current_filters = filters # Update current_filters
        self.reload_data(filters=self.current_filters)

    def _show_all(self):
        """Clears all filters and reloads supplies data."""
        logger.info("Showing all supplies (filters + search cleared)")
        if self.search_bar:
            self.search_bar.clear()
        self.current_filters = None # Clear all filters
        self.reload_data(filters=None)

    def _add_consumable_item(self):
        """Opens the RegisterSupplyModal to add a new consumable item."""
        logger.info("Opening RegisterSupplyModal to add new item")
        RegisterSupplyModal(self.winfo_toplevel(), on_save=self.save_item)



    def open_edit(self, item): 
        RegisterSupplyModal(self.winfo_toplevel(), self.save_item, initial_data=item)
    
    def adjust_val(self, supply_id, delta):
        """Ajuste la quantité d'un supply avec validation et gestion d'erreurs"""
        # Fetch item to calculate new state
        item = next((dict(i) for i in self.supplies_data if i["id"] == supply_id), None)
        if not item:
            show_error_toast(self.winfo_toplevel(), "Supply not found!")
            return

        new_qty = item["in_storage"] + delta

        # Validation: quantité ne peut pas être négative (silencieuse)
        if new_qty < 0:
            return

        try:
            # Recalculate status
            limit = item["limit_alert"]
            new_status = "STOCKED" if new_qty >= limit else ("CRITICAL" if new_qty > 0 else "OUT")

            # Update SQLite
            consumable_controller.update_supply_quantity(supply_id, new_qty, new_status)

            # Update UI Widget
            if supply_id in self.card_widgets:
                item["in_storage"] = new_qty
                item["status"] = new_status
                self.card_widgets[supply_id].update_data(item)

            self._load_supplies_data(filters=self.current_filters)

        except Exception as e:
            logger.error(f"Error adjusting supply quantity: {e}")
            show_error_toast(self.winfo_toplevel(), "Failed to update quantity. Please try again.")
            
    def save_item(self, data):
        """Sauvegarde un supply avec gestion d'erreurs"""
        try:
            # Save to SQLite
            consumable_controller.upsert_supply(data)
            show_success_toast(self.winfo_toplevel(), "Supply saved successfully!")
            self.reload_data(filters=self.current_filters)
        except Exception as e:
            logger.error(f"Error saving supply: {e}")
            show_error_toast(self.winfo_toplevel(), "Failed to save supply. Please try again.")

    def delete_item(self, supply_id):
        """Ouvre la fenêtre de confirmation stylée pour supprimer un item"""
        def confirm_delete():
            try:
                consumable_controller.delete_supply(supply_id)
                show_success_toast(self.winfo_toplevel(), "Supply deleted successfully!")
                self.reload_data(filters=self.current_filters)
            except Exception as e:
                logger.error(f"Error deleting supply: {e}")
                show_error_toast(self.winfo_toplevel(), "Failed to delete supply. Please try again.")

        DeleteConfirmationWindow(
            self.winfo_toplevel(),
            title="Delete supply",
            message="Are you sure you want to delete this supply?",
            subtitle="This action cannot be undone.",
            on_confirm=confirm_delete,
            icons_dir=self.ICONS_DIR
        )

    # Removed get_filtered_supplies as _load_supplies_data now handles search query directly

    # FONCTION CORRIGÉE À REMPLACER dans consomable_view.py (ligne ~865)
    
    def render_grid(self, event=None):
        """Render the grid of supply cards with safe widget destruction."""
        # 1. Clear current UI widgets mapping - SAFE DESTRUCTION
        for id in list(self.card_widgets.keys()):
            try:
                widget = self.card_widgets[id]
                if widget.winfo_exists():  # Vérifier si le widget existe encore
                    widget.grid_forget()
                    widget.destroy()
            except Exception as e:
                logger.warning(f"Could not destroy widget {id}: {e}")
            finally:
                # Toujours supprimer de la map même en cas d'erreur
                if id in self.card_widgets:
                    del self.card_widgets[id]
    
        # 2. Use self.supplies_data which is already filtered by _load_supplies_data
        filtered_supplies = self.supplies_data
        
        # 3. Render filtered list
        if not filtered_supplies:
            if not self.empty_label:
                self.empty_label = ctk.CTkLabel(
                    self.sf, 
                    text="NO ITEMS FOUND", 
                    font=("Inter", 20, "bold"), 
                    text_color=self.THEME["text_gray"]
                )
            self.empty_label.grid(row=0, column=0, columnspan=3, pady=100)
            self.empty_label.lift() # Ensure it's on top
        else:
            # Hide empty label if it exists
            if self.empty_label:
                try:
                    if self.empty_label.winfo_exists():
                        self.empty_label.grid_forget()
                except Exception:
                    pass
                
            # Render all filtered supply cards
            for idx, item in enumerate(filtered_supplies):
                id = item["id"]
                card = SupplyCard(self.sf, item, self.open_edit, self.delete_item, self.adjust_val, self._load_icon_image)
                self.card_widgets[id] = card
                # Adjust padx for left-most column to align with search bar
                col = idx % 3
                padx_value = (0, 12) if col == 0 else (12, 12) if col == 1 else (12, 0)
                card.grid(row=idx//3, column=col, padx=padx_value, pady=16, sticky="nw")


    def _load_icon_image(self, base_name, size=(84, 84)):
        """
        Loads an icon image from the ICONS_DIR, with a fallback to a
        placeholder circle with the first letter if the image is not found.
        """
        if not base_name:
            return None

        key = f"{base_name}_{size[0]}x{size[1]}"
        if key in self._icon_cache:
            return self._icon_cache[key]

        candidates = [
            f"{base_name}.png",
            f"{base_name}".replace(" ", "_") + ".png",
            f"{base_name}_icon.png",
            f"{base_name}-icon.png"
        ]

        for name in candidates:
            p = os.path.join(self.ICONS_DIR, name)
            if os.path.exists(p):
                try:
                    img = Image.open(p).convert("RGBA")
                    img = img.resize(size)
                    ctk_img = ctk.CTkImage(light_image=img, size=size)
                    self._icon_cache[key] = ctk_img
                    return ctk_img
                except Exception:
                    logger.exception("Error loading icon %s", p)
                    break

        # Fallback : cercle avec la première lettre
        try:
            w, h = size
            img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            bg_color = (248, 250, 252, 255)
            draw.ellipse((0, 0, w - 1, h - 1), fill=bg_color)

            initial = (base_name[0] if base_name else "?").upper()
            font_size = max(10, int(min(w, h) * 0.5))
            try:
                # Attempt to load a system font first
                f = ImageFont.truetype("arial.ttf", font_size) # Common font on Windows
            except IOError: # If font is not found, fallback to default
                f = ImageFont.load_default()

            text_bbox = draw.textbbox((0, 0), initial, font=f)
            text_w = text_bbox[2] - text_bbox[0]
            text_h = text_bbox[3] - text_bbox[1]
            text_x = (w - text_w) / 2
            text_y = (h - text_h) / 2
            draw.text((text_x, text_y), initial, fill=(75, 85, 99, 255), font=f)

            ctk_img = ctk.CTkImage(light_image=img, size=size)
            self._icon_cache[key] = ctk_img
            return ctk_img
        except Exception:
            logger.exception("Error generating placeholder icon for '%s'", base_name)

        self._icon_cache[key] = None
        return None

if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.title("Supplies View Test")
    root.geometry("1400x800")

    view = SuppliesView(root)

    root.mainloop()