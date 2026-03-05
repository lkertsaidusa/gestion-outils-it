import os
import logging
import customtkinter as ctk
from PIL import Image, ImageDraw, ImageTk

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


class FilterWindow(ctk.CTkToplevel):
    """Fenêtre de filtrage avec sélection multiple style pills horizontaux et recherche par ID."""

    THEME = {
        "bg": "#FFFFFF",
        "card_bg": "#FFFFFF",
        "pill_bg": "#F7F9FB",
        "white": "#FFFFFF",
        "primary": "#4081F5",
        "primary_hover": "#5899FA",
        "text_dark": "#0F1724",
        "text_gray": "#6B7280",
        "text_light_gray": "#9CA3AF",
        "border": "#E5E7EB",
        "pill_selected_bg": "#EFF6FF",
        "pill_selected_border": "#4081F5",
        "pill_unselected": "#FFFFFF"
    }
    
    # Configuration de la barre de recherche
    SEARCH_WIDTH = 700
    SEARCH_HEIGHT = 56
    SEARCH_CORNER = 14
    SEARCH_BORDER_COLOR = "#166FFF"
    SEARCH_BORDER_COLOR_NORMAL = "#D1D5DB"  # Gris un peu plus foncé
    SEARCH_BORDER_WIDTH_FOCUS = 3
    SEARCH_BORDER_WIDTH_NORMAL = 2  # Bordure visible par défaut
    SEARCH_BG = "#FFFFFF"
    
    # Paramètres d'animation
    _ANIM_STEPS = 4
    _ANIM_INTERVAL_MS = 12

    def __init__(self, parent, on_apply=None, icons_dir=None, **kwargs):
        super().__init__(parent, **kwargs)

        if icons_dir:
            self.icons_dir = icons_dir
        else:
            self.icons_dir = ICONS_DIR

        self.geometry("700x920")
        self.title("")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.after(100, lambda: self.geometry(f"+{700}+{100}"))

        self.configure(fg_color=self.THEME["bg"])

        self.on_apply = on_apply
        self.filters = {
            "search_id": "",  # Nouveau: recherche par ID
            "status": [],
            "category": [],
            "location": [],
            "warranty": []
        }
        
        # Stocker les options de chaque section
        self.filter_options = {}
        
        # Stocker les boutons "All"
        self.all_buttons = {}
        
        # Variables pour l'animation de la barre de recherche
        self._border_anim_job = None
        self._placeholder_anim_job = None
        self._icon_anim_job = None  # Nouvelle: animation de l'icône
        self._border_progress = 0.0
        self._placeholder_progress = 1.0
        self._icon_progress = 0.0  # 0: normale, 1: bleue
        self._images = {}
        self._search_icon_label = None  # Référence à l'icône de recherche
        self._search_icon_normal = None  # Icône normale
        self._search_icon_blue = None  # Icône bleue

        self._create_ui()

    def _create_ui(self):
        # Main container with rounded corners
        self.card = ctk.CTkFrame(self, fg_color=self.THEME["card_bg"], corner_radius=28)
        self.card.pack(fill="both", expand=True, padx=18, pady=18)

        # Header
        header = ctk.CTkFrame(self.card, fg_color="transparent")
        header.pack(fill="x", padx=28, pady=(18, 8))

        # Icon container bleu
        icon_container = ctk.CTkFrame(header, width=50, height=50, corner_radius=14, fg_color=self.THEME["primary"])
        icon_container.pack(side="left", padx=(0, 8))
        icon_container.pack_propagate(False)

        icon_img = self._load_icon_image("filter_white", size=(26, 26))
        if not icon_img:
            icon_img = self._create_filter_square_icon(size=(26, 26))
        icon_label = ctk.CTkLabel(icon_container, image=icon_img, text="", fg_color="transparent")
        icon_label.image = icon_img
        icon_label.place(relx=0.5, rely=0.5, anchor="center")

        # Title block
        title_block = ctk.CTkFrame(header, fg_color="transparent")
        title_block.pack(side="left", padx=(9, 0), anchor="w")

        title_label = ctk.CTkLabel(
            title_block,
            text="FILTER ENGINE",
            font=ctk.CTkFont(family="Segoe UI", size=26, weight="bold"),
            text_color=self.THEME["text_dark"]
        )
        title_label.pack(anchor="w", pady=(7, 0))

        subtitle_label = ctk.CTkLabel(
            title_block,
            text="S E L E C T I O N   I N T E L L I G E N C E",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=self.THEME["primary"]
        )
        subtitle_label.pack(anchor="w", pady=(0, 10))
        
        separator = ctk.CTkFrame(self.card, fg_color=self.THEME["border"], height=1)
        separator.pack(fill="x", padx=28, pady=(10, 0))

        # Content frame avec scrollbar
        self.scroll_container = ctk.CTkFrame(self.card, fg_color="transparent")
        self.scroll_container.pack(fill="both", expand=True, padx=20, pady=(10, 10))
        self.scroll_container.grid_columnconfigure(0, weight=1)
        self.scroll_container.grid_rowconfigure(0, weight=1)
        
        self.content = ctk.CTkScrollableFrame(
            self.scroll_container,
            fg_color="transparent",
            corner_radius=0,
            scrollbar_fg_color=self.THEME["bg"],
            scrollbar_button_color="#CBD5E1",
            scrollbar_button_hover_color="#9CA3AF"
        )
        self.content.grid(row=0, column=0, sticky="nsew")

        # ===== BARRE DE RECHERCHE PAR ID =====
        self._create_search_section(self.content)

        # Create filter sections
        self._create_filter_section(
            self.content,
            title="Asset Status",
            key="status",
            options=["Active", "Maintenance", "Lent Out", "Available"]
        )

        self._create_filter_section(
            self.content,
            title="Equipment Category",
            key="category",
            options=["PC", "PRINTER", "PHONE", "STORAGE", "MONITOR"]
        )

        self._create_filter_section(
            self.content,
            title="Deployment Zone",
            key="location",
            options=["RECEPTION", "IT SERVER ROOM", "SECTION A", "SECTION B", "SECTION C", "MAIN STORAGE", "UNDERGROUND", "OFFICE 101", "CEO BUREAU", "ADMINISTRATION", "SECRET ROOM"]
        )

        self._create_filter_section(
            self.content,
            title="Warranty Exp",
            key="warranty",
            options=["Valid", "Expiring Soon", "Expired"]
        )

        separator_bottom = ctk.CTkFrame(self.card, fg_color=self.THEME["border"], height=1)
        separator_bottom.pack(fill="x", padx=28, pady=(0, 10))

        # Bottom buttons
        bottom = ctk.CTkFrame(self.card, fg_color="transparent", height=70)
        bottom.pack(fill="x", padx=28, pady=(7, 10))
        bottom.pack_propagate(False)

        # Bouton Cancel (à gauche)
        cancel_btn = ctk.CTkButton(
            bottom,
            text="Cancel".upper(),
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color="#FEF2F2",
            hover_color="#FEE5E5",
            text_color="#DD2A2A",
            border_width=1.5,
            border_color="#FEE5E5",
            corner_radius=14,
            width=140,
            height=54,
            command=self._cancel
        )
        cancel_btn.pack(side="left")

        # Bouton Reset (au milieu gauche)
        reset_btn = ctk.CTkButton(
            bottom,
            text="RESET",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color=self.THEME["pill_bg"],
            hover_color="#EFEFF2",
            text_color="#6B7280",
            corner_radius=14,
            width=140,
            height=54,
            border_color=self.THEME["border"],
            border_width=1.5,
            command=self._reset_filters
        )
        reset_btn.pack(side="left", padx=(15, 15))

        # Bouton Apply (à droite)
        apply_btn = ctk.CTkButton(
            bottom,
            text="APPLY FILTERS",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color=self.THEME["primary"],
            hover_color=self.THEME["primary_hover"],
            text_color=self.THEME["white"],
            corner_radius=16,
            width=340,
            height=54,
            command=self._apply_filters
        )
        apply_btn.pack(side="right")
        
        # Binding Enter key pour appliquer les filtres
        self.bind("<Return>", lambda e: self._apply_filters())
        self.bind("<KP_Enter>", lambda e: self._apply_filters())

    def _create_search_section(self, parent):
        """Créer la section de recherche par ID avec barre animée."""
        
        # Section container
        search_section = ctk.CTkFrame(parent, fg_color="transparent")
        search_section.pack(fill="x", pady=(0, 25))

        # Header
        header_frame = ctk.CTkFrame(search_section, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 12))

        # Title
        title_label = ctk.CTkLabel(
            header_frame,
            text="Search by Product ID",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=self.THEME["text_dark"],
            anchor="w"
        )
        title_label.pack(side="left", anchor="w")

        # Subtitle/description
        desc_label = ctk.CTkLabel(
            header_frame,
            text="Direct ID lookup",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=self.THEME["primary"],
            anchor="w"
        )
        desc_label.pack(side="left", anchor="w", padx=(12, 0), pady=(6, 0))

        # Container de la barre de recherche
        search_container = ctk.CTkFrame(search_section, fg_color="transparent")
        search_container.pack(fill="x", pady=(0, 0))

        # Search pill frame
        self.search_frame = ctk.CTkFrame(
            search_container,
            fg_color=self.SEARCH_BG,
            corner_radius=self.SEARCH_CORNER,
            height=self.SEARCH_HEIGHT,
            border_width=self.SEARCH_BORDER_WIDTH_NORMAL,
            border_color=self.SEARCH_BORDER_COLOR_NORMAL  # Gris par défaut
        )
        self.search_frame.pack(fill="x", expand=True)
        self.search_frame.configure(width=self.SEARCH_WIDTH)
        self.search_frame.pack_propagate(False)
        self.search_frame.grid_columnconfigure(1, weight=1)

        # Icône de recherche (avec versions normale et bleue)
        self._search_icon_normal = self._load_search_icon(size=(20, 20), icon_name="search")
        self._search_icon_blue = self._load_search_icon(size=(20, 20), icon_name="search_blue")
        
        # Utiliser l'icône normale par défaut
        search_icon = self._search_icon_normal
        
        if search_icon:
            icon_label = ctk.CTkLabel(
                self.search_frame,
                image=search_icon,
                text="",
                fg_color=self.SEARCH_BG
            )
            icon_label.grid(row=0, column=0, padx=(22, 8), pady=(12, 12))
            self._search_icon_label = icon_label  # Stocker la référence
        else:
            # Fallback emoji
            icon_label = ctk.CTkLabel(
                self.search_frame,
                text="🔍",
                fg_color=self.SEARCH_BG,
                font=ctk.CTkFont(size=16)
            )
            icon_label.grid(row=0, column=0, padx=(22, 8), pady=(12, 12))
            self._search_icon_label = icon_label

        # Entry avec préfixe "#ID" intégré
        inter_font = ctk.CTkFont(family="Inter", size=16, weight="bold")
        
        # Frame pour contenir le préfixe et l'entry
        entry_container = ctk.CTkFrame(self.search_frame, fg_color=self.SEARCH_BG)
        entry_container.grid(row=0, column=1, padx=(0, 20), pady=(8, 8), sticky="ew")
        
        # Label préfixe "#ID"
        prefix_label = ctk.CTkLabel(
            entry_container,
            text="#ID",
            font=inter_font,
            text_color="#111827",
            fg_color=self.SEARCH_BG
        )
        prefix_label.pack(side="left", padx=(4, 2))
        
        # Entry (sans préfixe puisqu'il est affiché séparément)
        self.search_entry = ctk.CTkEntry(
            master=entry_container,
            placeholder_text="",
            fg_color=self.SEARCH_BG,
            border_width=0,
            font=inter_font,
            text_color="#111827",
            width=self.SEARCH_WIDTH - 150
        )
        self.search_entry.pack(side="left", fill="x", expand=True)

        # Label placeholder animé
        self.placeholder_label = ctk.CTkLabel(
            entry_container,
            text="13DZA3...",
            font=inter_font,
            text_color="#D1D5DB",  # Gris un peu plus foncé
            fg_color=self.SEARCH_BG
        )
        self.placeholder_label.place(in_=self.search_entry, x=4, y=0, relheight=1.0)
        self.placeholder_label.lift(self.search_entry)

        # Bindings
        self.search_entry.bind("<FocusIn>", self._on_search_focus_in)
        self.search_entry.bind("<FocusOut>", self._on_search_focus_out)
        self.search_entry.bind("<KeyRelease>", self._on_search_key)

        # Clic sur le frame/icône/placeholder -> focus l'entry
        def focus_entry(event):
            try:
                self.search_entry.focus_set()
            except Exception:
                pass

        self.search_frame.bind("<Button-1>", focus_entry)
        icon_label.bind("<Button-1>", focus_entry)
        self.placeholder_label.bind("<Button-1>", focus_entry)
        prefix_label.bind("<Button-1>", focus_entry)
        entry_container.bind("<Button-1>", focus_entry)
        
        # Binding global pour défocus quand on clique ailleurs
        def on_global_click(event):
            try:
                # Obtenir les coordonnées du clic
                x_root = event.x_root
                y_root = event.y_root
                
                # Obtenir la position et taille du search_frame
                sx = self.search_frame.winfo_rootx()
                sy = self.search_frame.winfo_rooty()
                sw = self.search_frame.winfo_width()
                sh = self.search_frame.winfo_height()
                
                # Vérifier si le clic est en dehors
                inside = (sx <= x_root <= sx + sw) and (sy <= y_root <= sy + sh)
                
                if not inside:
                    # Retirer le focus du search_entry
                    self.focus_set()
            except Exception:
                pass
        
        self.bind("<Button-1>", on_global_click, add="+")
        self.card.bind("<Button-1>", on_global_click, add="+")
        self.content.bind("<Button-1>", on_global_click, add="+")

        # État initial
        self._set_placeholder_progress(1.0, instant=True)
        self._set_border_progress(0.0, instant=True)
        self._set_icon_progress(0.0, instant=True)  # Icône normale au départ

    def _load_search_icon(self, size=(32, 32), icon_name="search"):
        """Charger l'icône de recherche."""
        candidates = [
            f"{icon_name}.png",
            f"icon-{icon_name}.png",
            f"{icon_name}_icon.png"
        ]
        
        for name in candidates:
            path = os.path.join(self.icons_dir, name)
            if os.path.exists(path):
                try:
                    img = Image.open(path).convert("RGBA")
                    img = img.resize(size)
                    # Utiliser CTkImage au lieu de PhotoImage
                    ctk_img = ctk.CTkImage(light_image=img, size=size)
                    return ctk_img
                except Exception:
                    logger.exception("Error loading search icon %s", path)
        return None

    def _set_icon_progress(self, target, instant=False):
        """Anime la progression de l'icône entre 0 (normale) et 1 (bleue)"""
        if self._icon_anim_job is not None:
            try:
                self.after_cancel(self._icon_anim_job)
            except Exception:
                pass
            self._icon_anim_job = None

        if instant:
            self._icon_progress = float(target)
            self._apply_icon_state()
            return

        # Animation par étapes
        start = self._icon_progress
        steps = self._ANIM_STEPS

        def step(i):
            t = i / float(steps)
            prog = start + (target - start) * t
            self._icon_progress = prog
            self._apply_icon_state()

            if i < steps:
                self._icon_anim_job = self.after(
                    self._ANIM_INTERVAL_MS,
                    lambda: step(i + 1)
                )
            else:
                self._icon_anim_job = None

        step(0)

    def _apply_icon_state(self):
        """Applique l'état de l'icône selon self._icon_progress avec transition fluide"""
        if not hasattr(self, '_search_icon_label'):
            return
            
        p = max(0.0, min(1.0, float(self._icon_progress)))

        # Transition progressive: utiliser un seuil plus bas pour commencer le changement plus tôt
        # Cela donne une impression de fondu plus fluide
        if p < 0.3:
            # Phase 1: Icône normale (0-30%)
            if self._search_icon_normal:
                try:
                    self._search_icon_label.configure(image=self._search_icon_normal)
                except Exception:
                    pass
        elif p < 0.7:
            # Phase 2: Transition (30-70%) - alterner rapidement pour simuler un fade
            # On pourrait aussi créer une image interpolée ici si nécessaire
            if p < 0.5:
                if self._search_icon_normal:
                    try:
                        self._search_icon_label.configure(image=self._search_icon_normal)
                    except Exception:
                        pass
            else:
                if self._search_icon_blue:
                    try:
                        self._search_icon_label.configure(image=self._search_icon_blue)
                    except Exception:
                        pass
        else:
            # Phase 3: Icône bleue (70-100%)
            if self._search_icon_blue:
                try:
                    self._search_icon_label.configure(image=self._search_icon_blue)
                except Exception:
                    pass

    # =====================================================================
    # ANIMATION DE LA BORDURE DE RECHERCHE
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

        # Animation par étapes
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

        # Largeur de bordure interpolée (reste à 2px mais peut augmenter légèrement)
        bw = int(round(self.SEARCH_BORDER_WIDTH_NORMAL + (self.SEARCH_BORDER_WIDTH_FOCUS - self.SEARCH_BORDER_WIDTH_NORMAL) * p))

        # Couleur de bordure interpolée (de gris à bleu)
        color = lerp_color(self.SEARCH_BORDER_COLOR_NORMAL, self.SEARCH_BORDER_COLOR, p)

        try:
            self.search_frame.configure(border_width=bw, border_color=color)
        except Exception:
            try:
                self.search_frame.configure(border_width=bw)
            except Exception:
                pass

    # =====================================================================
    # ANIMATION DU PLACEHOLDER DE RECHERCHE
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

        # Interpolation de couleur (de invisible à gris un peu plus foncé)
        invisible = self.SEARCH_BG
        visible_color = "#D1D5DB"  # Gris un peu plus foncé
        color = lerp_color(invisible, visible_color, p)

        try:
            self.placeholder_label.configure(text_color=color)

            # Si complètement caché, lower pour ne pas intercepter les clics
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

    def _set_search_icon_blue(self):
        """Changer l'icône de recherche en bleu"""
        if self._search_icon_label and self._search_icon_blue:
            try:
                self._search_icon_label.configure(image=self._search_icon_blue)
            except Exception:
                pass

    def _set_search_icon_normal(self):
        """Changer l'icône de recherche en normale"""
        if self._search_icon_label and self._search_icon_normal:
            try:
                self._search_icon_label.configure(image=self._search_icon_normal)
            except Exception:
                pass

    # =====================================================================
    # GESTION DES ÉVÉNEMENTS DE RECHERCHE
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
        self._set_icon_progress(1.0)  # Animation vers l'icône bleue

    def _on_search_focus_out(self, event=None):
        """Anime la bordure et restaure le placeholder si vide"""
        self._set_border_progress(0.0)
        self._set_icon_progress(0.0)  # Animation vers l'icône normale

        try:
            content = self.search_entry.get().strip()
        except Exception:
            content = ""

        if content == "":
            self._set_placeholder_progress(1.0)

    def _create_filter_section(self, parent, title, key, options):
        """Créer une section de filtres avec pills multi-sélection."""
        
        # Stocker les options pour cette section
        self.filter_options[key] = options
        
        # Section container
        section = ctk.CTkFrame(parent, fg_color="transparent")
        section.pack(fill="x", pady=(0, 25))

        # Header avec titre et boutons Select All / Clear
        header_frame = ctk.CTkFrame(section, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 12))

        # Title
        title_label = ctk.CTkLabel(
            header_frame,
            text=title,
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=self.THEME["text_dark"],
            anchor="w"
        )
        title_label.pack(side="left", anchor="w")

        # Bouton "Clear" avec style rouge
        clear_btn = ctk.CTkButton(
            header_frame,
            text="Clear",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color="#FEF2F2",
            hover_color="#FEE5E5",
            text_color="#DD2A2A",
            border_width=1.5,
            border_color="#FEE5E5",
            corner_radius=20,
            width=70,
            height=28,
            command=lambda: self._clear_section(key)
        )
        clear_btn.pack(side="right", padx=(10, 5))
        
        # Bouton "Select All" avec bordure bleue
        select_all_btn = ctk.CTkButton(
            header_frame,
            text="Select All",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color="#F3F7FE",
            hover_color="#D0E0FC",
            text_color=self.THEME["primary"],
            border_width=1.5,
            border_color="#DBE8FF",
            corner_radius=20,
            width=80,
            height=28,
            command=lambda: self._toggle_all(key)
        )
        select_all_btn.pack(side="right", padx=(0, 0))
        
        # Stocker l'élément "Select All" pour mise à jour future si nécessaire
        self.all_buttons[key] = select_all_btn

        # Pills container (wrapping)
        pills_container = ctk.CTkFrame(section, fg_color="transparent")
        pills_container.pack(fill="x")

        # Create pills in a grid-like layout
        pills_frame = ctk.CTkFrame(pills_container, fg_color="transparent")
        pills_frame.pack(fill="x")

        row_frame = None
        pills_per_row = 0
        max_pills_per_row = 4

        for idx, option in enumerate(options):
            if pills_per_row == 0 or pills_per_row >= max_pills_per_row:
                row_frame = ctk.CTkFrame(pills_frame, fg_color="transparent")
                row_frame.pack(fill="x", pady=4)
                pills_per_row = 0

            pill_btn = self._create_pill_button(row_frame, option, key)
            pill_btn.pack(side="left", padx=6, pady=4)
            pills_per_row += 1

    def _create_pill_button(self, parent, option, key):
        """Créer un bouton pill individuel."""
        
        is_selected = option in self.filters.get(key, [])
        
        btn = ctk.CTkButton(
            parent,
            text=option,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold" if is_selected else "bold"),
            fg_color=self.THEME["pill_selected_bg"] if is_selected else self.THEME["pill_unselected"],
            hover_color="#DBEAFE" if is_selected else "#F3F4F6",
            text_color=self.THEME["primary"] if is_selected else self.THEME["text_gray"],
            corner_radius=20,
            height=38,
            border_width=2,
            border_color=self.THEME["pill_selected_border"] if is_selected else self.THEME["border"],
            command=lambda: self._toggle_pill(key, option, btn)
        )
        
        # Store reference
        if not hasattr(self, '_pill_buttons'):
            self._pill_buttons = {}
        if key not in self._pill_buttons:
            self._pill_buttons[key] = {}
        self._pill_buttons[key][option] = btn
        
        return btn

    def _toggle_pill(self, key, option, btn):
        """Toggle pill selection avec animation fluide."""
        
        if option in self.filters[key]:
            # Déselectionner avec transition
            self.filters[key].remove(option)
            self._animate_pill_deselect(btn)
        else:
            # Sélectionner avec transition
            self.filters[key].append(option)
            self._animate_pill_select(btn)
        
        # Mettre à jour le bouton All
        self._update_all_button(key)
        
        logger.info(f"Filter updated - {key}: {self.filters[key]}")

    def _clear_section(self, key):
        """Effacer toutes les sélections d'une section."""
        
        self.filters[key] = []
        
        # Désélectionner visuellement tous les pills de cette section
        if hasattr(self, '_pill_buttons') and key in self._pill_buttons:
            for option, btn in self._pill_buttons[key].items():
                self._animate_pill_deselect(btn)
        
        # Mettre à jour le bouton All
        self._update_all_button(key)
        
        logger.info(f"Section cleared - {key}")

    def _toggle_all(self, key):
        """Toggle toutes les options d'une section."""
        
        all_options = self.filter_options[key]
        
        # Si toutes les options sont sélectionnées, tout désélectionner
        if len(self.filters[key]) == len(all_options):
            self.filters[key] = []
            # Désélectionner visuellement tous les pills
            if hasattr(self, '_pill_buttons') and key in self._pill_buttons:
                for option, btn in self._pill_buttons[key].items():
                    self._animate_pill_deselect(btn)
        else:
            # Sinon, tout sélectionner
            self.filters[key] = all_options.copy()
            # Sélectionner visuellement tous les pills
            if hasattr(self, '_pill_buttons') and key in self._pill_buttons:
                for option, btn in self._pill_buttons[key].items():
                    self._animate_pill_select(btn)
        
        # Mettre à jour le bouton All
        self._update_all_button(key)
        
        logger.info(f"All toggled - {key}: {self.filters[key]}")

    def _update_all_button(self, key):
        """Mettre à jour l'état visuel du bouton Select All (optionnel maintenant)."""
        pass

    def _animate_pill_select(self, btn):
        """Animation de sélection du pill."""
        btn.configure(
            fg_color="#DBEAFE",
            border_color=self.THEME["pill_selected_border"]
        )
        self.after(50, lambda: self._animate_pill_select_step2(btn))
    
    def _animate_pill_select_step2(self, btn):
        """Étape 2 de l'animation de sélection."""
        btn.configure(
            fg_color=self.THEME["pill_selected_bg"],
            text_color=self.THEME["primary"],
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold")
        )
    
    def _animate_pill_deselect(self, btn):
        """Animation de désélection du pill."""
        btn.configure(
            fg_color="#F3F4F6",
            border_color="#D1D5DB"
        )
        self.after(50, lambda: self._animate_pill_deselect_step2(btn))
    
    def _animate_pill_deselect_step2(self, btn):
        """Étape 2 de l'animation de désélection."""
        btn.configure(
            fg_color=self.THEME["pill_unselected"],
            text_color=self.THEME["text_gray"],
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            border_color=self.THEME["border"]
        )

    def _cancel(self):
        """Fermer la fenêtre sans appliquer les filtres."""
        logger.info("Filters cancelled")
        self.destroy()

    def _reset_filters(self):
        """Réinitialiser tous les filtres."""
        
        for key in self.filters:
            if key == "search_id":
                self.filters[key] = ""
            else:
                self.filters[key] = []
        
        # Reset search entry
        try:
            self.search_entry.delete(0, "end")
            self._set_placeholder_progress(1.0, instant=True)
        except Exception:
            pass
        
        # Reset all pill buttons
        if hasattr(self, '_pill_buttons'):
            for key in self._pill_buttons:
                for option, btn in self._pill_buttons[key].items():
                    btn.configure(
                        fg_color=self.THEME["pill_unselected"],
                        hover_color="#F3F4F6",
                        text_color=self.THEME["text_gray"],
                        border_width=2,
                        border_color=self.THEME["border"],
                        font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold")
                    )
        
        # Reset all "Select All" circles
        for key in self.all_buttons:
            self._update_all_button(key)
        
        logger.info("All filters reset")

    def _apply_filters(self):
        """Appliquer les filtres sélectionnés."""
        
        # Récupérer l'ID de recherche avec préfixe "#ID"
        try:
            search_value = self.search_entry.get().strip()
            if search_value:
                self.filters["search_id"] = f"#ID{search_value}"
            else:
                self.filters["search_id"] = ""
        except Exception:
            self.filters["search_id"] = ""
        
        logger.info(f"Filters applied: {self.filters}")
        if callable(self.on_apply):
            self.on_apply(self.filters)
        self.destroy()

    def _load_icon_image(self, base_name, size=(84, 84)):
        """Charger une icône depuis le répertoire des icônes."""
        if not base_name or not os.path.exists(self.icons_dir):
            logger.debug(f"Icons directory not found: {self.icons_dir}")
            return None

        candidates = [
            f"{base_name}.png",
            f"{base_name}.jpg",
            f"{base_name}.jpeg",
            f"{base_name}.svg",
            f"{base_name}_icon.png",
            f"{base_name}-icon.png",
            base_name.replace(" ", "_") + ".png",
            base_name.replace("-", "_") + ".png",
        ]

        for filename in candidates:
            path = os.path.join(self.icons_dir, filename)
            
            if os.path.exists(path):
                try:
                    img = Image.open(path).convert("RGBA")
                    img = img.resize(size)
                    ctk_img = ctk.CTkImage(light_image=img, size=size)
                    logger.info(f"Successfully loaded icon: {filename}")
                    return ctk_img
                except Exception as e:
                    logger.warning(f"Failed to load/resize {filename}: {e}")
                    return None

        logger.warning(f"Icon not found for: {base_name}")
        return None

    def _create_filter_square_icon(self, size=(26, 26)):
        """Créer l'icône de filtre par défaut."""
        w, h = size
        img = Image.new("RGBA", (w, h), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)
        
        # Dessiner un entonnoir blanc
        funnel = [(w * 0.33, h * 0.30), (w * 0.67, h * 0.30), (w * 0.55, h * 0.55), (w * 0.45, h * 0.55)]
        draw.polygon(funnel, fill=(255, 255, 255, 255))
        draw.rectangle([(w * 0.45, h * 0.55), (w * 0.55, h * 0.67)], fill=(255, 255, 255, 255))
        
        ctk_img = ctk.CTkImage(light_image=img, size=size)
        return ctk_img


# Exemple d'utilisation directe dans votre inventory_view
def main():
    """Exemple d'intégration dans votre programme inventory_view"""
    
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.title("Inventory View - Filter Integration")
    root.geometry("1200x800")

    def handle_filters(filters):
        """Fonction callback pour gérer les filtres appliqués"""
        print("\n=== Filtres appliqués ===")
        if filters.get("search_id"):
            print(f"Search ID: {filters['search_id']}")
        for key, values in filters.items():
            if key != "search_id" and values:
                print(f"{key}: {', '.join(values)}")
    
    # Ouvrir directement la fenêtre de filtres au démarrage
    filter_window = FilterWindow(root, on_apply=handle_filters)

    root.mainloop()


if __name__ == "__main__":
    main()