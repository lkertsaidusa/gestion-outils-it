import os
import sys
import logging
from pathlib import Path

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFont, ImageTk
from app.views.filter_window import FilterWindow
from app.views.add_window import AddEquipmentWindow
from app.components.toast_success import show_success_toast
from app.components.delete_window import DeleteConfirmationWindow
from app.components.action_toast import StatusDock, UpdateStatusModal, ChangeLocationModal

_project_root = Path(__file__).resolve().parents[3]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

ICONS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "assets", "icons"))


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
                text="🔍",
                fg_color=self.PILL_BG,
                font=ctk.CTkFont(size=18)
            )
            icon_label.grid(row=0, column=0, padx=(25, 8), pady=(17, 17))
        
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


class InventoryView(ctk.CTkFrame):
    ICONS_DIR = ICONS_DIR

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
        "inactive_text": "#6B7280" 
    }

    def __init__(self, parent, initial_filters=None, user_role=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.configure(fg_color=self.THEME["bg"], corner_radius=0)
        self.pack(fill="both", expand=True)
        self._icon_cache = {}
        
        self.user_role = user_role
        
        self.active_row = None
        self.current_filters = initial_filters

        # Référence vers la search bar (initialisée dans _create_ui)
        self.search_bar = None
        
        # =====================================================================
        # SYSTÈME DE SÉLECTION (CHECKBOXES)
        # =====================================================================
        self.selection_mode = False  # Mode sélection activé/désactivé
        self.selected_items = set()  # IDs des items sélectionnés
        self.header_checkbox = None  # Checkbox du header
        self.row_checkboxes = {}  # {item_id: checkbox_widget}
        self.checkbox_animation_job = None  # Job d'animation en cours
        
        # =====================================================================
        # STATUS DOCK (barre d'actions en bas)
        # =====================================================================
        self.status_dock = None  # Initialisé dynamiquement

        self._load_inventory_data(filters=initial_filters)
        self._create_ui()

    def destroy(self):
        """Nettoyage lors de la destruction de la vue (suppression du dock flottant)"""
        self._hide_dock()
        super().destroy()

    # =====================================================================
    # CHARGEMENT DE DONNÉES
    # =====================================================================

    def _load_inventory_data(self, filters=None):
        try:
            from controllers import inventory_controller as inv_ctrl
            
            # Strict enforcement for IT_TECHNICIAN
            is_technician = str(self.user_role).upper() in ["IT_TECHNICIAN", "IT_TECHNICIEN"]
            if is_technician:
                if not filters:
                    filters = {}
                filters["status"] = ["MAINTENANCE"]
            
            if filters and filters.get("warranty_expiring"):
                all_tools = inv_ctrl.list_tools()
                self.inventory_data = [
                    tool for tool in all_tools
                    if tool.get("warranty_expiration", {}).get("is_expiring", False)
                    or tool.get("warranty_expiration", {}).get("is_expired", False)
                ]
                self.current_filters = filters
            elif filters:
                self.inventory_data = inv_ctrl.apply_filters(filters)
                self.current_filters = filters
            else:
                self.inventory_data = inv_ctrl.list_tools()
                self.current_filters = None
            
            if not isinstance(self.inventory_data, list):
                raise RuntimeError("inventory_controller.list_tools did not return a list")
                
            logger.info(f"Loaded {len(self.inventory_data)} items from database")
            
        except Exception as e:
            logger.exception("Failed to load inventory data")
            self.inventory_data = []
            self._show_error("Failed to load inventory data", str(e))

    def reload_data(self, filters=None):
        logger.info("Reloading inventory data...")
        self._load_inventory_data(filters)
        
        # Réinitialiser la sélection
        self.selection_mode = False
        self.selected_items.clear()
        self.row_checkboxes.clear()
        
        # Masquer le dock
        if self.status_dock:
            self.status_dock.destroy()
            self.status_dock = None
        
        for widget in self.winfo_children():
            widget.destroy()
        
        self._create_ui()
        logger.info("Inventory reloaded successfully")

    # =====================================================================
    # CONSTRUCTION DE L'UI
    # =====================================================================

    def _create_ui(self):
        # ==================== TITRE + LIGNE SÉPARATRICE ====================
        title_container = ctk.CTkFrame(self, fg_color="transparent")
        title_container.pack(fill="x", padx=40, pady=(30, 0))
        
        title = ctk.CTkLabel(
            title_container,
            text="Inventory",
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
        
        # ==================== BARRE D'OUTILS (Search + Boutons) ====================
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

        # Si on recharge l'UI alors qu'une recherche est active, on restaure le texte
        if self.current_filters and self.current_filters.get("q"):
            self.search_bar.set_value(self.current_filters["q"])
        
        is_technician = str(self.user_role).upper() in ["IT_TECHNICIAN", "IT_TECHNICIEN"]
        if not is_technician:
            # ── BOUTON FILTER ──
            filter_icon = self._load_icon_image("filter", size=(18, 18))
            if not filter_icon:
                filter_icon = self._create_filter_icon()
            
            filter_btn = ctk.CTkButton(
                toolbar,
                text="Filter Engine",
                image=filter_icon,
                fg_color=self.THEME["white"],
                text_color="#6B7280",
                hover_color=self.THEME["row_hover"],
                corner_radius=15,
                height=60,
                width=130,
                font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                command=self._open_filter_window,
                compound="left"
            )
            filter_btn.pack(side="left", padx=(0, 12))
            
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
        
        # ── SPACER pour pousser "Add equipment" à droite ──
        spacer = ctk.CTkFrame(toolbar, fg_color="transparent")
        spacer.pack(side="left", fill="both", expand=True)
        
        is_technician = str(self.user_role).upper() in ["IT_TECHNICIAN", "IT_TECHNICIEN"]
        if not is_technician:
            # ── BOUTON ADD EQUIPMENT (à droite) ──
            add_icon = self._load_icon_image("plus-480", size=(18, 18))
            add_btn = ctk.CTkButton(
                toolbar,
                text="  Add equipment",
                text_color=self.THEME["white"],
                image=add_icon,
                fg_color=self.THEME["primary"],
                hover_color=self.THEME["primary_hover"],
                corner_radius=15,
                height=60,
                width=180,
                font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
                command=self.add_product,
                compound="left"
            )
            add_btn.pack(side="right")
        
        # ==================== TABLE CARD ====================
        table_card = ctk.CTkFrame(
            self,
            fg_color=self.THEME["white"],
            corner_radius=40
        )
        table_card.pack(fill="both", expand=True, padx=40, pady=(0, 40))

        # Table Header
        header = ctk.CTkFrame(table_card, fg_color="transparent", height=60)
        header.pack(fill="x", padx=25, pady=(8, 8))
        
        # Container pour la checkbox du header (invisible au départ, hors écran à gauche)
        self.header_checkbox_container = ctk.CTkFrame(header, fg_color="transparent", width=40)
        self.header_checkbox_container.place(x=-60, rely=0.5, anchor="w")  # Commence hors écran
        
        # Checkbox du header (select all)
        self.header_checkbox = ctk.CTkCheckBox(
            self.header_checkbox_container,
            text="",
            width=20,
            height=20,
            checkbox_width=20,
            checkbox_height=20,
            corner_radius=6,
            fg_color=self.THEME["primary"],
            hover_color=self.THEME["primary_hover"],
            border_color=self.THEME["border"],
            command=self._toggle_select_all
        )
        self.header_checkbox.pack()

        separator = ctk.CTkFrame(table_card, fg_color="#E5E7EB", height=1)
        separator.pack(fill="x", pady=0)

        # POSITIONS DES COLONNES
        labels = [
            ("PRODUCT NAME", 0.06),
            ("ID/BRAND", 0.268),
            ("CATEGORY", 0.394),
            ("LOCATION", 0.505),
            ("WARRANTY EXP.", 0.64),
            ("STATUS", 0.78),
            ("ACTIONS", 0.883)
        ]

        padding = {
            "PRODUCT NAME": (0, 0),
            "ID/BRAND": (0, 0),
            "CATEGORY": (0, 0),
            "LOCATION": (0, 0),
            "WARRANTY EXP.": (0, 0), 
            "STATUS": (0, 0),
            "ACTIONS": (40, 0)
        }

        for text, relx in labels:
            label_frame = ctk.CTkFrame(header, fg_color="transparent")
            label_frame.place(relx=relx, rely=0.5, anchor="w")

            ctk.CTkLabel(
                label_frame,
                text=text.upper(),
                font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                text_color=self.THEME["text_gray"]
            ).pack(padx=padding[text])

        # Table Content (scrollable)
        scroll = ctk.CTkScrollableFrame(
            table_card, 
            fg_color="transparent",
            scrollbar_fg_color=self.THEME["white"],         
            scrollbar_button_color="#CBD5E1",     
            scrollbar_button_hover_color=self.THEME["text_gray"]
        )
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        if not self.inventory_data:
            no_data_label = ctk.CTkLabel(
                scroll,
                text="No equipment found.\nClick 'Add Equipment' to add new items.",
                font=ctk.CTkFont(family="Segoe UI", size=16),
                text_color=self.THEME["text_gray"]
            )
            no_data_label.pack(pady=50)
        else:
            for item in self.inventory_data:
                self._create_row(scroll, item)
        
        # Note: Le StatusDock est créé dynamiquement dans _update_dock()

    # =====================================================================
    # SYSTÈME DE SÉLECTION — ANIMATION OPTIMISÉE DES CHECKBOXES
    # =====================================================================
    
    def _toggle_select_all(self):
        """Sélectionne/désélectionne tous les items via la checkbox du header"""
        if len(self.selected_items) == len(self.inventory_data):
            # Tout désélectionner
            self.selected_items.clear()
            self.selection_mode = False
            logger.info("🔴 ALL items deselected - Selection mode OFF")
            self._animate_checkboxes(direction="hide")
            
            # Masquer le dock
            self._hide_dock()
            
            # Masquer aussi les boutons actions
            if self.active_row is not None:
                if "hide_func" in self.active_row:
                    self.active_row["hide_func"]()
                self.active_row = None
        else:
            # Tout sélectionner
            self.selection_mode = True
            if not self._checkboxes_visible():
                self._animate_checkboxes(direction="show")
            
            for item in self.inventory_data:
                item_id = item.get("raw", {}).get("id")
                if item_id:
                    self.selected_items.add(item_id)
            logger.info(f"✅ ALL {len(self.selected_items)} items selected")
            
            # Afficher le dock
            self._update_dock()
        
        self._update_checkboxes_state()
    
    def _update_checkboxes_state(self):
        """Met à jour l'état visuel de toutes les checkboxes"""
        # Mettre à jour la checkbox du header
        if self.header_checkbox:
            if len(self.selected_items) == len(self.inventory_data) and len(self.inventory_data) > 0:
                try:
                    self.header_checkbox.select()
                    self.header_checkbox.update_idletasks()
                except Exception:
                    pass
            else:
                try:
                    self.header_checkbox.deselect()
                    self.header_checkbox.update_idletasks()
                except Exception:
                    pass
        
        # Mettre à jour les checkboxes des rows
        for item_id, checkbox_data in self.row_checkboxes.items():
            checkbox_widget = checkbox_data.get('widget') if isinstance(checkbox_data, dict) else None
            if checkbox_widget:
                if item_id in self.selected_items:
                    try:
                        checkbox_widget.select()
                        checkbox_widget.update_idletasks()
                    except Exception:
                        pass
                else:
                    try:
                        checkbox_widget.deselect()
                        checkbox_widget.update_idletasks()
                    except Exception:
                        pass
    
    def _checkboxes_visible(self):
        """Vérifie si les checkboxes sont actuellement visibles"""
        try:
            info = self.header_checkbox_container.place_info()
            x = float(info.get('x', -60))
            return x >= 0
        except Exception:
            return False
    
    def _animate_checkboxes(self, direction="show"):
        """
        Animation fluide de gauche à droite pour les checkboxes
        Identique au style des boutons edit/delete mais dans l'autre sens
        """
        if self.checkbox_animation_job is not None:
            try:
                self.after_cancel(self.checkbox_animation_job)
            except Exception:
                pass
            self.checkbox_animation_job = None
        
        # Positions X absolues (de gauche à droite)
        start_x = -60 if direction == "show" else 11  # Hors écran vs visible
        end_x = 11 if direction == "show" else -60    # Position finale alignée à gauche
        
        # PARAMÈTRES D'ANIMATION OPTIMISÉS (identiques aux boutons)
        steps = 15          # Animation ultra-fluide avec 15 étapes
        duration = 50       # 90ms au total (rapide et responsive)
        delay = max(1, duration // steps)
        
        current_step = [0]
        
        def step():
            if current_step[0] <= steps:
                progress = current_step[0] / steps
                # Easing out cubic pour naturalité (même fonction que les boutons)
                ease = 1 - pow(1 - progress, 3)
                new_x = start_x + (end_x - start_x) * ease
                
                # Animer le header checkbox
                try:
                    self.header_checkbox_container.place(x=new_x, rely=0.5, anchor="w")
                except Exception:
                    pass
                
                # Animer toutes les checkboxes des rows
                for checkbox_data in self.row_checkboxes.values():
                    try:
                        checkbox_container = checkbox_data.get('container') if isinstance(checkbox_data, dict) else checkbox_data
                        if checkbox_container:
                            checkbox_container.place(x=new_x, rely=0.5, anchor="w")
                    except Exception:
                        pass
                
                current_step[0] += 1
                self.checkbox_animation_job = self.after(delay, step)
            else:
                self.checkbox_animation_job = None
                # Position finale garantie
                try:
                    self.header_checkbox_container.place(x=end_x, rely=0.5, anchor="w")
                except Exception:
                    pass
                for checkbox_data in self.row_checkboxes.values():
                    try:
                        checkbox_container = checkbox_data.get('container') if isinstance(checkbox_data, dict) else checkbox_data
                        if checkbox_container:
                            checkbox_container.place(x=end_x, rely=0.5, anchor="w")
                    except Exception:
                        pass
        
        step()
    
    def _update_dock(self):
        """Met à jour l'affichage du StatusDock selon les sélections"""
        count = len(self.selected_items)
    
        if count == 0:
            # Pas de sélection → masquer le dock
            self._hide_dock()
        else:
            # Des items sont sélectionnés → afficher/mettre à jour le dock
            if not self.status_dock:
                self.status_dock = StatusDock(
                    self.winfo_toplevel(),
                    on_dismiss=self._dock_dismiss,
                    on_action=self._dock_action,
                    parent_bg=self.THEME["bg"],
                    icons_dir=self.ICONS_DIR,
                    user_role=self.user_role
                )
            
            # Ajuster la largeur selon le nombre d'items sélectionnés et le rôle
            is_technician = str(self.user_role).upper() in ["IT_TECHNICIAN", "IT_TECHNICIEN"]
            if is_technician:
                width = 0.30  # Beaucoup plus étroit (un seul bouton + close)
            elif count == 1:
                width = 0.42  # Plus large pour 1 item (5 boutons: Status, Edit, Location, Delete, Close)
            else:
                width = 0.38  # Plus étroit pour 2+ items (4 boutons: Status, Location, Delete, Close)
            
            # Positionner avec la nouvelle largeur
            self.status_dock.place(relx=0.55, rely=0.88, anchor="center", relwidth=width)
            
            # Mettre à jour le contenu du dock
            self.status_dock.update(count)

    def _hide_dock(self):
        """Masque et détruit le StatusDock"""
        if self.status_dock:
            self.status_dock.destroy()
            self.status_dock = None

    def _dock_dismiss(self):
        """Callback quand on ferme le dock (bouton X)"""
        self.selected_items.clear()
        self.selection_mode = False
        self._animate_checkboxes(direction="hide")
        self._update_checkboxes_state()
        self._hide_dock()

    def _dock_action(self, action):
        """Callback pour les actions du dock"""
        if action == "edit":
            self._toast_edit_action()
        elif action == "status":
            self._toast_status_action()
        elif action == "location":
            self._toast_location_action()
        elif action == "delete":
            self._toast_delete_action()

    # =====================================================================
    # RECHERCHE — LOGIQUE PRINCIPALE
    # =====================================================================

    def _on_search(self, query):
        """
        Callback principal de la recherche.
        Appelé uniquement sur <Return> (via AnimatedSearchBar).

        Comportement :
          - query vide  → efface le filtre "q" et recharge (garde les autres filtres)
          - query non vide → ajoute/met à jour le filtre "q" et recharge
        """
        logger.info(f"Search query: '{query}'")

        if query.strip() == "":
            # ── Vider la recherche : on garde les filtres du FilterWindow s'ils existent
            if self.current_filters:
                merged = {k: v for k, v in self.current_filters.items() if k != "q"}
                # Si plus aucun filtre ne reste, on passe None
                self.reload_data(filters=merged if merged else None)
            else:
                self.reload_data(filters=None)
        else:
            # ── Recherche active : on fusionne avec les filtres existants
            if self.current_filters:
                merged = dict(self.current_filters)
                merged["q"] = query.strip()
            else:
                merged = {"q": query.strip()}
            self.reload_data(filters=merged)

    # =====================================================================
    # ROWS
    # =====================================================================

    def _create_row(self, parent, data):
        row = ctk.CTkFrame(parent, fg_color="transparent", height=90, corner_radius=15)
        row.pack(fill="x", pady=2, padx=(0, 5))  # Réduire le padding gauche pour étendre le hover
        
        item_id = data.get("raw", {}).get("id")

        def on_enter(event):
            row.configure(fg_color=self.THEME["row_hover"])

        def on_leave(event):
            row.configure(fg_color="transparent")
        
        # ── Container pour la checkbox de la row (hors écran à gauche au départ) ──
        checkbox_container = ctk.CTkFrame(row, fg_color="transparent", width=40)
        checkbox_container.place(x=-60, rely=0.5, anchor="w")  # Commence hors écran
        
        row_checkbox = ctk.CTkCheckBox(
            checkbox_container,
            text="",
            width=20,
            height=20,
            checkbox_width=20,
            checkbox_height=20,
            corner_radius=6,
            fg_color=self.THEME["primary"],
            hover_color=self.THEME["primary_hover"],
            border_color=self.THEME["border"],
            command=lambda: self._on_row_checkbox_click(item_id)
        )
        row_checkbox.pack()
        
        # Stocker DEUX références : le container ET le widget checkbox lui-même
        if item_id:
            self.row_checkboxes[item_id] = {
                'container': checkbox_container,
                'widget': row_checkbox
            }

        # ── Icône catégorie (position ajustée pour laisser espace à la checkbox) ──
        icon_container = ctk.CTkFrame(
            row,
            width=50,
            height=50,
            corner_radius=15,
            fg_color=self.THEME["icon_bg"]
        )
        icon_container.place(x=75, rely=0.5, anchor="w")  # x=60 -> x=75 pour plus d'espace

        icon_img = self._load_icon_image(data.get("icon"), size=(20, 20))
        if icon_img:
            icon_label = ctk.CTkLabel(
                icon_container,
                image=icon_img,
                text="",
                fg_color=self.THEME["icon_bg"]
            )
            icon_label.place(relx=0.5, rely=0.5, anchor="center")
            icon_label.bind("<Enter>", on_enter)
            icon_label.bind("<Leave>", on_leave)

        # ── Nom + Serial ──
        name_label = ctk.CTkLabel(
            row,
            text=data.get("name", "").upper(),
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color=self.THEME["text_dark"]
        )
        name_label.place(relx=0.12, rely=0.5, anchor="w")

        # ── ID + Brand ──
        id_label = ctk.CTkLabel(
            row,
            text=data.get("id", "").upper(),
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color=self.THEME["text_dark"]
        )
        id_label.place(relx=0.27, rely=0.4, anchor="w")

        brand_label = ctk.CTkLabel(
            row,
            text=data.get("brand", "").upper(),
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=self.THEME["text_gray"]
        )
        brand_label.place(relx=0.27, rely=0.63, anchor="w")

        # ── Category ──
        category_label = ctk.CTkLabel(
            row,
            text=data.get("category", "").upper(),
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color=self.THEME["text_dark"]
        )
        category_label.place(relx=0.40, rely=0.5, anchor="w")

        # ── Location ──
        location_label = ctk.CTkLabel(
            row,
            text=data.get("location", "").upper(),
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color=self.THEME["text_dark"]
        )
        location_label.place(relx=0.51, rely=0.5, anchor="w")

        # ── Status badge ──
        status_text = data.get("status", "").upper()
        text_color, border_color, bg_color = self._status_colors(status_text)

        text_length = len(status_text)
        badge_width = max(90, text_length * 8 + 24)

        badge = ctk.CTkFrame(
            row,
            fg_color=bg_color,
            border_color=border_color,
            border_width=2,
            corner_radius=13,
            height=32,
            width=badge_width
        )
        badge.pack_propagate(False)
        badge.place(relx=0.79, rely=0.5, anchor="w")
        
        status_label = ctk.CTkLabel(
            badge,
            text=status_text.upper(),
            text_color=text_color,
            font=ctk.CTkFont(family="Tahoma", size=12, weight="bold"),
            fg_color="transparent",
            anchor="w"
        )
        status_label.pack(side="left", padx=(12, 12), pady=0)
        
        # ── Boutons Actions (edit / delete) ──
        is_technician = str(self.user_role).upper() in ["IT_TECHNICIAN", "IT_TECHNICIEN"]
        if not is_technician:
            actions_container = ctk.CTkFrame(row, fg_color="transparent")
            actions_container.place(relx=1.08, rely=0.5, anchor="center")
            
            edit_icon_normal = self._load_icon_image("pen", size=(16, 16))
            edit_icon_hover = self._load_icon_image("pen-blue", size=(16, 16))
            
            edit_btn = ctk.CTkButton(
                actions_container,
                text="",
                image=edit_icon_normal,
                width=36,
                height=36,
                corner_radius=10,
                fg_color=self.THEME["white"],
                hover_color=self.THEME["white"],
                border_width=1,
                border_color=self.THEME["border"],
                command=lambda d=data: self._edit_item(d)
            )
            edit_btn.pack(side="left", padx=4)
            
            delete_icon_normal = self._load_icon_image("trash_red", size=(16, 16))
            delete_icon_hover = self._load_icon_image("trash_white", size=(16, 16))
            
            delete_btn = ctk.CTkButton(
                actions_container,
                text="",
                image=delete_icon_normal,
                width=36,
                height=36,
                corner_radius=10,
                fg_color="#FEF2F2",
                hover=False,
                border_width=1,
                border_color="#FCA5A5",
                command=lambda d=data: self._delete_item(d)
            )
            delete_btn.pack(side="left", padx=4)
            
            # ── Animation slide des boutons actions (droite à gauche) ──
            animation_state = {
                "current_animation": None,
                "is_visible": False
            }
            
            def animate_buttons(direction="show"):
                if animation_state["current_animation"] is not None:
                    try:
                        row.after_cancel(animation_state["current_animation"])
                    except Exception:
                        pass
                    animation_state["current_animation"] = None
                
                if direction == "show" and animation_state["is_visible"]:
                    return
                if direction == "hide" and not animation_state["is_visible"]:
                    return
                
                animation_state["is_visible"] = (direction == "show")
                
                start_relx = 1.08 if direction == "show" else 0.95
                end_relx = 0.95 if direction == "show" else 1.08
                steps = 15  # Même fluidité que les checkboxes
                duration = 90
                delay = max(1, duration // steps)
                
                current_step = [0]
                
                def step():
                    if current_step[0] <= steps:
                        progress = current_step[0] / steps
                        # Easing out cubic
                        ease = 1 - pow(1 - progress, 3)
                        new_relx = start_relx + (end_relx - start_relx) * ease
                        try:
                            actions_container.place(relx=new_relx, rely=0.5, anchor="center")
                        except Exception:
                            return
                        current_step[0] += 1
                        animation_state["current_animation"] = row.after(delay, step)
                    else:
                        animation_state["current_animation"] = None
                        try:
                            actions_container.place(relx=end_relx, rely=0.5, anchor="center")
                        except Exception:
                            pass
                
                step()
            
            def toggle_buttons(event):
                # Si on clique sur la checkbox, ne pas toggler les boutons
                widget = event.widget
                if widget == row_checkbox or widget == checkbox_container:
                    return
                
                if self.active_row == animation_state:
                    animate_buttons("hide")
                    self.active_row = None
                else:
                    if self.active_row is not None and self.active_row != animation_state:
                        if "hide_func" in self.active_row:
                            self.active_row["hide_func"]()
                    
                    animate_buttons("show")
                    self.active_row = animation_state
                    animation_state["hide_func"] = lambda: animate_buttons("hide")
        else:
            actions_container = None
            def animate_buttons(direction="show"): pass
            def toggle_buttons(event): pass
            animation_state = None
        
        # ── Warranty date + badges expiring/expired ──
        warranty_info = data.get("warranty_expiration", {})
        warranty_date = warranty_info.get("display_date", "N/A")
        is_expiring = warranty_info.get("is_expiring", False)
        is_expired = warranty_info.get("is_expired", False)
        
        if is_expired:
            warranty_color = "#EF4444"
        elif is_expiring:
            warranty_color = "#EF4444"
        else:
            warranty_color = self.THEME["text_dark"]
        
        warranty_container = ctk.CTkFrame(row, fg_color="transparent")
        warranty_container.place(relx=0.65, rely=0.5, anchor="w")
        
        warranty_date_label = ctk.CTkLabel(
            warranty_container,
            text=warranty_date,
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color=warranty_color,
            fg_color="transparent"
        )
        warranty_date_label.pack(side="top", anchor="w", pady=(0, 2))
        
        if is_expiring and not is_expired:
            expiring_label = ctk.CTkLabel(
                warranty_container,
                text="(EXPIRING SOON)",
                font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
                text_color="#EF4444",
                fg_color="transparent"
            )
            expiring_label.pack(side="top", anchor="w", pady=(0, 0))
        elif is_expired:
            expired_label = ctk.CTkLabel(
                warranty_container,
                text="(EXPIRED)",
                font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
                text_color="#EF4444",
                fg_color="transparent"
            )
            expired_label.pack(side="top", anchor="w", pady=(0, 0))
        
        # ── Bindings hover / click sur la row ──
        def row_click_handler(event):
            # Si on clique directement sur la checkbox, laisser le handler de checkbox gérer
            if event.widget == row_checkbox or event.widget == checkbox_container:
                return
            
            # Activer le mode sélection si pas encore activé
            if not self.selection_mode:
                self.selection_mode = True
                self._animate_checkboxes(direction="show")
            
            # TOGGLE la sélection de la ligne
            if item_id in self.selected_items:
                # DÉCOCHER la ligne
                self.selected_items.discard(item_id)
                logger.info(f"❌ Row click - Item {item_id} deselected")
                
                # Masquer les boutons actions
                animate_buttons("hide")
                self.active_row = None
                
                # Si plus aucune sélection, masquer les checkboxes
                if len(self.selected_items) == 0:
                    self.selection_mode = False
                    logger.info("🔴 Selection mode DEACTIVATED")
                    self._animate_checkboxes(direction="hide")
                
                try:
                    row_checkbox.deselect()
                    row_checkbox.update_idletasks()
                except Exception:
                    pass
                self._update_checkboxes_state()
                
            else:
                # COCHER la ligne
                self.selected_items.add(item_id)
                logger.info(f"✅ Row click - Item {item_id} selected")
                
                # Afficher les boutons actions
                if self.active_row == animation_state:
                    animate_buttons("hide")
                    self.active_row = None
                else:
                    if self.active_row is not None and self.active_row != animation_state:
                        if "hide_func" in self.active_row:
                            self.active_row["hide_func"]()
                    
                    animate_buttons("show")
                    self.active_row = animation_state
                    animation_state["hide_func"] = lambda: animate_buttons("hide")
                
                # Forcer la checkbox à se cocher visuellement
                try:
                    row_checkbox.select()
                    row_checkbox.update_idletasks()
                except Exception:
                    pass
                self._update_checkboxes_state()
            
            # ── MISE À JOUR DU DOCK APRÈS TOGGLE ──
            self._update_dock()
        
        warranty_container.bind("<Enter>", on_enter)
        warranty_container.bind("<Leave>", on_leave)
        warranty_container.bind("<Button-1>", row_click_handler)
        warranty_date_label.bind("<Enter>", on_enter)
        warranty_date_label.bind("<Leave>", on_leave)
        warranty_date_label.bind("<Button-1>", row_click_handler)
        
        row.bind("<Enter>", lambda e: on_enter(e))
        row.bind("<Leave>", lambda e: on_leave(e))
        row.bind("<Button-1>", row_click_handler)
        
        if actions_container:
            actions_container.bind("<Enter>", lambda e: on_enter(e))
            actions_container.bind("<Leave>", lambda e: on_leave(e))
            edit_btn.bind("<Enter>", lambda e: on_enter(e))
            edit_btn.bind("<Leave>", lambda e: on_leave(e))
            delete_btn.bind("<Enter>", lambda e: on_enter(e))
            delete_btn.bind("<Leave>", lambda e: on_leave(e))
        
        # ── Hover des icônes edit / delete ──
        if not is_technician:
            def edit_icon_enter(e):
                edit_btn.configure(image=edit_icon_hover)
            
            def edit_icon_leave(e):
                edit_btn.configure(image=edit_icon_normal)
            
            def delete_icon_enter(e):
                delete_btn.configure(
                    image=delete_icon_hover, 
                    fg_color="#EF4444",
                    border_color="#DC2626"
                )
            
            def delete_icon_leave(e):
                delete_btn.configure(
                    image=delete_icon_normal, 
                    fg_color="#FEF2F2",
                    border_color="#FCA5A5"
                )
            
            edit_btn.bind("<Enter>", lambda e: (on_enter(e), edit_icon_enter(e)))
            edit_btn.bind("<Leave>", lambda e: (on_leave(e), edit_icon_leave(e)))
            delete_btn.bind("<Enter>", lambda e: (on_enter(e), delete_icon_enter(e)))
            delete_btn.bind("<Leave>", lambda e: (on_leave(e), delete_icon_leave(e)))

        # Binder tous les enfants restants de la row
        for child in row.winfo_children():
            if child != actions_container and child != checkbox_container:
                child.bind("<Enter>", lambda e: on_enter(e))
                child.bind("<Leave>", lambda e: on_leave(e))
                child.bind("<Button-1>", row_click_handler)
                if isinstance(child, ctk.CTkFrame) and child != actions_container and child != checkbox_container:
                    for sub_child in child.winfo_children():
                        sub_child.bind("<Enter>", lambda e: on_enter(e))
                        sub_child.bind("<Leave>", lambda e: on_leave(e))
                        sub_child.bind("<Button-1>", row_click_handler)
    
    def _on_row_checkbox_click(self, item_id):
        """Gère le clic direct sur une checkbox de row - TOGGLE uniquement"""
        # Toggle la sélection
        if item_id in self.selected_items:
            self.selected_items.discard(item_id)
            logger.info(f"❌ Checkbox click - Item {item_id} deselected")
        else:
            self.selected_items.add(item_id)
            logger.info(f"✅ Checkbox click - Item {item_id} selected")
        
        # Si plus aucune sélection, désactiver le mode
        if len(self.selected_items) == 0:
            self.selection_mode = False
            logger.info("🔴 Selection mode DEACTIVATED via checkbox")
            self._animate_checkboxes(direction="hide")

        self._update_checkboxes_state()

        # ── MISE À JOUR DU DOCK APRÈS TOGGLE ──
        self._update_dock()
        

    # =====================================================================
    # TOAST ACTION CALLBACKS
    # =====================================================================
    
    def _toast_edit_action(self):
        """Callback du bouton Edit du toast (uniquement si 1 seul item sélectionné)"""
        if len(self.selected_items) != 1:
            logger.warning("Edit action called but selection count is not 1")
            return
        
        # Récupérer l'item sélectionné
        selected_id = list(self.selected_items)[0]
        
        # Chercher l'item dans inventory_data
        selected_item = None
        for item in self.inventory_data:
            if item.get("raw", {}).get("id") == selected_id:
                selected_item = item
                break
        
        if selected_item:
            logger.info(f"📝 Toast EDIT action - Item: {selected_item.get('name')}")
            self._edit_item(selected_item)
        else:
            logger.error(f"Item {selected_id} not found in inventory_data")
    
    def _toast_status_action(self):
        """Callback du bouton Status du toast"""
        logger.info(f"📊 Toast STATUS action - {len(self.selected_items)} items selected")
        
        # Récupérer le status actuel du premier item pour l'UI
        current_status = None
        if self.selected_items:
            first_id = next(iter(self.selected_items))
            for item in self.inventory_data:
                if item.get("raw", {}).get("id") == first_id:
                    current_status = item.get("raw", {}).get("status")
                    break
        
        def on_status_selected(new_status):
            try:
                from controllers import inventory_controller as inv_ctrl
                from backend import notification_service
                from controllers import settings_controller
                
                updated_count = 0
                affected_items = []
                
                # Pre-fetch items info for bulk email
                for item_id in self.selected_items:
                    for item in self.inventory_data:
                        if item.get("raw", {}).get("id") == item_id:
                            affected_items.append({
                                "name": item.get("name"),
                                "serial_number": item.get("id") # 'id' in UI is serial_number
                            })
                            break

                for item_id in self.selected_items:
                    try:
                        # Use silent=True to avoid individual emails
                        inv_ctrl.update_tool(item_id, {"status": new_status}, silent=True)
                        updated_count += 1
                    except Exception as e:
                        logger.error(f"Failed to update item {item_id}: {e}")
                
                if updated_count > 0:
                    # Send bulk notification
                    user_name = settings_controller.get_user_display_name()
                    user_role = self.user_role or settings_controller.get_user_role()
                    notification_service.send_bulk_inventory_notification(
                        action="UPDATE",
                        items=affected_items,
                        user_name=user_name,
                        user_role=user_role,
                        details=f"Status updated to {new_status}"
                    )

                    self.reload_data(filters=self.current_filters)
                    
                    show_success_toast(
                        parent=self.winfo_toplevel(),
                        message=f"Status updated to {new_status} for {updated_count} items!",
                        duration=3000,
                        icons_dir=self.ICONS_DIR,
                        top_padding=30
                    )
            except Exception as e:
                logger.exception("Error updating status")
                self._show_error("Update Error", str(e))

        UpdateStatusModal(self.winfo_toplevel(), len(self.selected_items), on_status_selected, current_status=current_status, user_role=self.user_role)
    
    def _toast_location_action(self):
        """Callback du bouton Location du toast"""
        logger.info(f"📍 Toast LOCATION action - {len(self.selected_items)} items selected")
        
        def on_location_selected(new_location):
            try:
                from controllers import inventory_controller as inv_ctrl
                from backend import notification_service
                from controllers import settings_controller
                
                updated_count = 0
                affected_items = []
                
                # Pre-fetch items info for bulk email
                for item_id in self.selected_items:
                    for item in self.inventory_data:
                        if item.get("raw", {}).get("id") == item_id:
                            affected_items.append({
                                "name": item.get("name"),
                                "serial_number": item.get("id")
                            })
                            break

                for item_id in self.selected_items:
                    try:
                        # Use silent=True to avoid individual emails
                        inv_ctrl.update_tool(item_id, {"location": new_location}, silent=True)
                        updated_count += 1
                    except Exception as e:
                        logger.error(f"Failed to update item {item_id}: {e}")
                
                if updated_count > 0:
                    # Send bulk notification
                    user_name = settings_controller.get_user_display_name()
                    user_role = self.user_role or settings_controller.get_user_role()
                    notification_service.send_bulk_inventory_notification(
                        action="UPDATE",
                        items=affected_items,
                        user_name=user_name,
                        user_role=user_role,
                        details=f"Location updated to {new_location}"
                    )

                    self.reload_data(filters=self.current_filters)
                    
                    show_success_toast(
                        parent=self.winfo_toplevel(),
                        message=f"Location updated to {new_location} for {updated_count} items!",
                        duration=3000,
                        icons_dir=self.ICONS_DIR,
                        top_padding=30
                    )
            except Exception as e:
                logger.exception("Error updating location")
                self._show_error("Update Error", str(e))

        ChangeLocationModal(self.winfo_toplevel(), len(self.selected_items), on_location_selected)
    
    def _toast_delete_action(self):
        """Callback du bouton Delete du toast"""
        logger.info(f"🗑️ Toast DELETE action - {len(self.selected_items)} items selected")
        
        # Récupérer les noms des items à supprimer
        items_to_delete = []
        for item in self.inventory_data:
            if item.get("raw", {}).get("id") in self.selected_items:
                items_to_delete.append(item)
        
        if len(items_to_delete) == 1:
            # 1 seul item → message simple
            message = f"Are you sure you want to delete '{items_to_delete[0].get('name')}'?"
        else:
            # Plusieurs items → message de groupe
            message = f"Are you sure you want to delete {len(items_to_delete)} items?"
        
        def on_confirm_delete():
            try:
                from controllers import inventory_controller as inv_ctrl
                from backend import notification_service
                from controllers import settings_controller
                
                deleted_count = 0
                affected_items = []
                
                # Pre-fetch items info for bulk email
                for item in items_to_delete:
                    affected_items.append({
                        "name": item.get("name"),
                        "serial_number": item.get("id")
                    })

                for item in items_to_delete:
                    equipment_id = item.get("raw", {}).get("id")
                    if equipment_id:
                        # Use silent=True to avoid individual emails
                        success = inv_ctrl.delete_tool(equipment_id, silent=True)
                        if success:
                            deleted_count += 1
                
                logger.info(f"✅ {deleted_count} items deleted successfully")
                
                if deleted_count > 0:
                    # Send bulk notification
                    user_name = settings_controller.get_user_display_name()
                    user_role = self.user_role or settings_controller.get_user_role()
                    notification_service.send_bulk_inventory_notification(
                        action="DELETE",
                        items=affected_items,
                        user_name=user_name,
                        user_role=user_role,
                        details="Selected items were removed from inventory"
                    )

                self.reload_data(filters=self.current_filters)
                
                # TOAST DE SUCCÈS
                if deleted_count == 1:
                    toast_message = f"Equipment '{items_to_delete[0].get('name')}' deleted successfully!"
                else:
                    toast_message = f"{deleted_count} equipments deleted successfully!"
                
                show_success_toast(
                    parent=self.winfo_toplevel(),
                    message=toast_message,
                    duration=3000,
                    icons_dir=self.ICONS_DIR,
                    top_padding=30
                )
                
            except Exception as e:
                logger.exception("Error deleting equipment(s)")
                self._show_error("Delete Error", str(e))
        
        DeleteConfirmationWindow(
            parent=self.winfo_toplevel(),
            title="Delete Equipment",
            message=message,
            subtitle="This action cannot be undone.",
            on_confirm=on_confirm_delete,
            icons_dir=self.ICONS_DIR
        )

    # =====================================================================
    # HELPERS VISUELS
    # =====================================================================

    def _status_colors(self, status_text):
        if status_text == "•  ACTIVE":
            return ("#1CBD87", "#C6EFE0", "#F0FBF7")
        elif status_text == "•  MAINTENANCE":
            return ("#F59E0B", "#FCE8C5", "#FEF9F0")
        elif status_text == "•  AVAILABLE":
            return ("#3B82F6", "#CEDEFB", "#F0F4FC")
        elif status_text == "•  LENT OUT":
            return ("#EF4444", "#FBD2D2", "#FEF3F3")
        else:
            return (self.THEME["text_medium"], self.THEME["border"], self.THEME["icon_bg"])

    def _load_icon_image(self, base_name, size=(84, 84)):
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
                f = ImageFont.truetype("DejaVuSans-Bold.ttf", font_size)
            except Exception:
                try:
                    f = ImageFont.truetype("arial.ttf", font_size)
                except Exception:
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

    def _create_filter_icon(self):
        size = (18, 18)
        img = Image.new("RGBA", size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.line([(2, 2), (16, 2), (9, 14), (2, 2)], fill=(22, 111, 255, 255), width=2)
        ctk_img = ctk.CTkImage(light_image=img, size=size)
        return ctk_img

    # =====================================================================
    # FILTRES (FilterWindow)
    # =====================================================================

    def _open_filter_window(self):
        FilterWindow(self, on_apply=self._apply_filters)

    def _apply_filters(self, filters):
        """
        Callback du FilterWindow.
        On fusionne les filtres reçus avec la recherche en cours (si elle existe)
        pour qu'ils coexistent.
        """
        logger.info(f"Applied filters from FilterWindow: {filters}")

        # Récupérer le texte actuel de la search bar
        current_query = ""
        if self.search_bar:
            current_query = self.search_bar.search_entry.get().strip()

        # Fusionner : filtres du FilterWindow + recherche texte actuelle
        if current_query:
            filters["q"] = current_query

        self.reload_data(filters=filters)

    def _show_all(self):
        """Réinitialise tout : filtres ET recherche."""
        logger.info("Showing all equipment (filters + search cleared)")
        if self.search_bar:
            self.search_bar.clear()
        self.reload_data(filters=None)

    # =====================================================================
    # CRUD — ADD / EDIT / DELETE
    # =====================================================================

    def _edit_item(self, data):
        logger.info(f"Edit item: {data.get('name')} - {data.get('id')}")

        raw_data = data.get("raw")
        if not raw_data:
            logger.error("Cannot edit: 'raw' data not found in item dict")
            self._show_error("Edit Error", "Raw data not available for this item.")
            return

        AddEquipmentWindow(
            parent=self.winfo_toplevel(),
            on_update=self._on_equipment_updated,
            existing_data=raw_data,
            icons_dir=self.ICONS_DIR
        )

    def _on_equipment_updated(self, tool_id, data):
        logger.info(f"Equipment update requested — ID: {tool_id}, data: {data}")

        if not tool_id:
            logger.error("Cannot update: tool_id is None")
            self._show_error("Update Error", "Tool ID is missing — cannot save changes.")
            return

        try:
            from controllers import inventory_controller as inv_ctrl
            updated = inv_ctrl.update_tool(tool_id, data)
            logger.info(f"Equipment ID {tool_id} updated successfully: {updated.get('name')}")
            self.reload_data(filters=self.current_filters)
            
            # TOAST DE SUCCÈS
            show_success_toast(
                parent=self.winfo_toplevel(),
                message=f"Equipment '{data.get('asset_model', updated.get('name', ''))}' updated successfully!",
                duration=3000,
                icons_dir=self.ICONS_DIR,
                top_padding=30
            )

        except ValueError as e:
            logger.warning(f"Validation error updating tool {tool_id}: {e}")
            self._show_error("Validation Error", str(e))
        except Exception as e:
            logger.exception(f"Error updating equipment {tool_id}")
            self._show_error("Update Error", f"Failed to update equipment: {str(e)}")
    
    def _delete_item(self, data):
        logger.info(f"Delete item requested: {data.get('name')} - {data.get('id')}")
        
        equipment_name = data.get("name", "Unknown Equipment")
        
        def on_confirm_delete():
            try:
                from controllers import inventory_controller as inv_ctrl
                
                raw_data = data.get("raw", {})
                equipment_id = raw_data.get("id")
                
                if not equipment_id:
                    logger.error("Cannot delete: equipment ID not found")
                    self._show_error("Delete Error", "Equipment ID not found")
                    return
                
                success = inv_ctrl.delete_tool(equipment_id)
                
                if success:
                    logger.info(f"Equipment {equipment_id} deleted successfully")
                    self.reload_data(filters=self.current_filters)
                    
                    # TOAST DE SUCCÈS
                    show_success_toast(
                        parent=self.winfo_toplevel(),
                        message=f"Equipment '{equipment_name}' deleted successfully!",
                        duration=3000,
                        icons_dir=self.ICONS_DIR,
                        top_padding=30
                    )
                else:
                    logger.error(f"Failed to delete equipment {equipment_id}")
                    self._show_error("Delete Error", "Failed to delete equipment from database")
                    
            except Exception as e:
                logger.exception("Error deleting equipment")
                self._show_error("Delete Error", str(e))
        
        DeleteConfirmationWindow(
            parent=self.winfo_toplevel(),
            title="Delete Equipment",
            message=f"Are you sure you want to delete '{equipment_name}'?",
            subtitle="This action cannot be undone.",
            on_confirm=on_confirm_delete,
            icons_dir=self.ICONS_DIR
        )

    def add_product(self):
        logger.info("Opening Add Equipment window")
        
        AddEquipmentWindow(
            parent=self.winfo_toplevel(),
            on_submit=self._on_equipment_added,
            icons_dir=self.ICONS_DIR
        )
    
    def _on_equipment_added(self, data):
        logger.info(f"New equipment added: {data}")

        try:
            from controllers import inventory_controller as inv_ctrl
            created_equipment = inv_ctrl.create_tool(data)
            logger.info(f"Equipment saved to database with ID: {created_equipment.get('id')}")
            self.reload_data(filters=self.current_filters)
            
            # TOAST DE SUCCÈS
            show_success_toast(
                parent=self.winfo_toplevel(),
                message=f"Equipment '{data.get('asset_model')}' added successfully!",
                duration=3000,
                icons_dir=self.ICONS_DIR,
                top_padding=30
            )
            
        except ValueError as e:
            logger.warning(f"Validation error: {e}")
            self._show_error("Validation Error", str(e))
        except Exception as e:
            logger.exception("Error adding equipment")
            self._show_error("Error", f"Failed to add equipment: {str(e)}")

    # =====================================================================
    # DIALOGS — ERROR
    # =====================================================================

    def _show_error(self, title, message):
        error_dialog = ctk.CTkToplevel(self.winfo_toplevel())
        error_dialog.title(title)
        error_dialog.geometry("400x180")
        error_dialog.transient(self.winfo_toplevel())
        error_dialog.grab_set()
        error_dialog.resizable(False, False)
        
        error_dialog.update_idletasks()
        x = self.winfo_toplevel().winfo_x() + (self.winfo_toplevel().winfo_width() - 400) // 2
        y = self.winfo_toplevel().winfo_y() + (self.winfo_toplevel().winfo_height() - 180) // 2
        error_dialog.geometry(f"+{x}+{y}")
        
        error_frame = ctk.CTkFrame(error_dialog, fg_color=self.THEME["white"])
        error_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        error_label = ctk.CTkLabel(
            error_frame,
            text=message,
            font=ctk.CTkFont(family="Segoe UI", size=14),
            text_color=self.THEME["text_dark"],
            wraplength=350
        )
        error_label.pack(pady=20)
        
        ok_btn = ctk.CTkButton(
            error_frame,
            text="OK",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color=self.THEME["primary"],
            hover_color=self.THEME["primary_hover"],
            width=100,
            height=40,
            command=error_dialog.destroy
        )
        ok_btn.pack(pady=(0, 10))


# =====================================================================
# ENTRY POINT (test standalone)
# =====================================================================

if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.title("Inventory System")
    root.geometry("1400x800")

    view = InventoryView(root)

    root.mainloop()