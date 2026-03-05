import logging
import os
import math
import customtkinter as ctk
from PIL import Image, ImageTk, ImageChops

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

RESAMPLE = Image.BILINEAR


def hex_to_rgb(hex_color: str):
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb):
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def lerp_color(a_hex, b_hex, t: float):
    """Linear interpolation between two hex colors (t in [0,1])."""
    a = hex_to_rgb(a_hex)
    b = hex_to_rgb(b_hex)
    return rgb_to_hex(tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3)))


class Sidebar(ctk.CTkFrame):
    ICONS_DIR  = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "assets", "icons"))
    IMAGES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "assets", "images"))

    # ── Animation ────────────────────────────────────────────────────────────
    _ANIM_STEPS       = 5
    _ANIM_INTERVAL_MS = 12

    # ── Layout constants (tweak here to resize everything at once) ───────────
    _EXPANDED_WIDTH = 250   # sidebar plus large
    _BTN_HEIGHT     = 53    # hauteur bouton (diminuée)
    _BTN_RADIUS     = 15    # arrondi des boutons (comme toggle header)
    _BTN_PADX       = 10    # padding horizontal container
    _BTN_PADY       = 9     # padding vertical entre boutons
    _BTN_PADY_FIRST = 75    # espace avant le 1er bouton
    _BTN_INNER_PADX = 24    # padding interne du bouton (mode ouvert) - égal des deux côtés (+10px)
    _ICON_SIZE      = 40    # taille icône px (augmentée)
    _ICON_PAD_X     = 4     # padding interne icône x (réduit de 8 à 4)
    _ICON_PAD_Y     = 4     # padding interne icône y (réduit de 6 à 4)
    _FONT_SIZE      = 13    # taille police (augmentée de 12 à 13)

    # ── Collapsed state ───────────────────────────────────────────────────────
    _COLLAPSED_WIDTH = 110  # largeur sidebar réduite (augmentée de 90 à 110)
    _COLLAPSED_BTN   = 50   # bouton carré = hauteur du bouton ouvert (58x58)
    _COLLAPSED_BTN_TOP_ADJUST = 3  # ajustement vertical pour aligner avec mode ouvert

    def __init__(self, parent, on_menu_click=None, width=None, user_role=None, **kwargs):
        super().__init__(parent, **kwargs)

        self.configure(fg_color="#FFFFFF", width=width or self._EXPANDED_WIDTH, corner_radius=0)
        self.on_menu_click = on_menu_click
        self.active_button = None
        self.user_role = user_role

        self._icon_images  = {}
        self._blend_cache  = {}
        self._images       = {}

        self.menu_buttons        = {}
        self._button_containers  = {}
        self._button_text_labels = {}
        self._is_collapsed       = False
        self._logo_label         = None
        self._small_logo_label   = None
        self._leave_button       = None
        self._leave_container    = None

        # Base menu items
        self.menu_items = [
            {"name": "Dashboard",  "icon": "dashboard"},
            {"name": "Inventory",  "icon": "inventory"},
            {"name": "Consumable", "icon": "box"},
            {"name": "Map",        "icon": "map"},
            {"name": "Settings",   "icon": "setting"},
            {"name": "Help",       "icon": "help"},
        ]

        # Filter menu items based on role
        is_technician = str(self.user_role).upper() in ["IT_TECHNICIAN", "IT_TECHNICIEN"]
        if is_technician:
            forbidden = ["Dashboard", "Consumable"]
            self.menu_items = [item for item in self.menu_items if item["name"] not in forbidden]

        self._create_brand()

        for i, item in enumerate(self.menu_items):
            top_pad = self._BTN_PADY_FIRST if i == 0 else self._BTN_PADY
            btn = self._create_menu_button(item["name"], item["icon"], row=i + 1, top_padding=top_pad)
            self.menu_buttons[item["name"]] = btn

        spacer_row = len(self.menu_items) + 1
        self.grid_rowconfigure(spacer_row, weight=1)

        leave_row = spacer_row + 1
        self._leave_button = self._create_leave_button(
            row=leave_row, top_padding=self._BTN_PADY, bottom_padding=40
        )

        if "Inventory" in self.menu_buttons:
            self.set_active_button(self.menu_buttons["Inventory"])

    # ─────────────────────────────────────────────────────────────────────────
    #  Brand / logo
    # ─────────────────────────────────────────────────────────────────────────

    def _create_brand(self):
        candidates = ["logo.png", "techmanage_logo.png", "brand.png"]
        logo_photo = None

        for name in candidates:
            p = os.path.join(self.IMAGES_DIR, name)
            if os.path.exists(p):
                try:
                    img   = Image.open(p).convert("RGBA")
                    ratio = img.height / img.width

                    tw    = 240
                    pil   = img.resize((tw, int(tw * ratio)), RESAMPLE)
                    photo = ImageTk.PhotoImage(pil)
                    self._images["logo"] = photo
                    logo_photo = photo
                    break
                except Exception:
                    break

        # Charger le mini_logo spécifiquement pour le mode réduit
        mini_logo_path = os.path.join(self.IMAGES_DIR, "mini_logo.png")
        mini_logo_photo = None
        if os.path.exists(mini_logo_path):
            try:
                mini_img = Image.open(mini_logo_path).convert("RGBA")
                # Redimensionner en conservant le ratio - hauteur max de 30px
                ratio = mini_img.height / mini_img.width
                new_height = 30
                new_width = int(new_height / ratio)
                mini_img = mini_img.resize((new_width, new_height), RESAMPLE)
                mini_logo_photo = ImageTk.PhotoImage(mini_img)
                self._images["mini_logo"] = mini_logo_photo
            except Exception as e:
                logger.error(f"Erreur lors du chargement du mini_logo: {e}")

        if logo_photo or mini_logo_photo:
            logo_frame = ctk.CTkFrame(self, fg_color="transparent", height=100)
            logo_frame.grid(row=0, column=0, padx=30, pady=(20, 10), sticky="ew")
            logo_frame.grid_columnconfigure(0, weight=1)
            logo_frame.grid_propagate(False)

            if logo_photo:
                self._logo_label = ctk.CTkLabel(logo_frame, image=logo_photo, text="", fg_color="transparent")
                self._logo_label.pack(anchor="center")

            if mini_logo_photo:
                self._small_logo_label = ctk.CTkLabel(logo_frame, image=mini_logo_photo, text="", fg_color="transparent")
        else:
            spacer = ctk.CTkFrame(self, fg_color="transparent", height=50)
            spacer.grid(row=0, column=0, padx=20, pady=(14, 6), sticky="ew")
            spacer.grid_columnconfigure(0, weight=1)

    # ─────────────────────────────────────────────────────────────────────────
    #  Icon helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _try_load_image(self, path, size):
        try:
            if not os.path.exists(path):
                return None
            img = Image.open(path).convert("RGBA")
            return img.resize(size, RESAMPLE)
        except Exception:
            return None

    def _pil_to_photo(self, pil_img):
        try:
            return ImageTk.PhotoImage(pil_img)
        except Exception:
            return None

    def _add_padding_to_icon(self, pil_img, padding_x=8, padding_y=8):
        if pil_img is None:
            return None
        try:
            w, h    = pil_img.size
            new_img = Image.new("RGBA", (w + padding_x * 2, h + padding_y * 2), (0, 0, 0, 0))
            new_img.paste(pil_img, (padding_x, padding_y))
            return new_img
        except Exception:
            return pil_img

    def _load_icon_variants(self, base_name, size=None):
        size = size or (self._ICON_SIZE, self._ICON_SIZE)
        if base_name in self._icon_images and isinstance(self._icon_images[base_name].get("black"), Image.Image):
            return self._icon_images[base_name]

        variants = {"black": None, "white": None}

        if base_name == "box":
            candidates = {
                "black": [f"{base_name}_black.png"],
                "white": [f"{base_name}_white.png"],
            }
        else:
            candidates = {
                "black": [f"{base_name}_black.png", f"{base_name}-black.png", f"{base_name}.png"],
                "white": [f"{base_name}_white.png", f"{base_name}-white.png"],
            }

        for color, names in candidates.items():
            for name in names:
                p       = os.path.join(self.ICONS_DIR, name)
                pil_img = self._try_load_image(p, size)
                if pil_img:
                    pil_img           = self._add_padding_to_icon(pil_img, padding_x=self._ICON_PAD_X, padding_y=self._ICON_PAD_Y)
                    variants[color]   = pil_img
                    break

        if variants["white"] is None and variants["black"] is not None:
            variants["white"] = variants["black"].copy()

        self._icon_images[base_name] = variants
        return variants

    def _get_blended_icon(self, base_name, step_index):
        key = (base_name, step_index)
        if key in self._blend_cache:
            return self._blend_cache[key]

        variants = self._load_icon_variants(base_name)
        black    = variants.get("black")
        white    = variants.get("white")
        if black is None:
            return None

        t = step_index / float(self._ANIM_STEPS)
        try:
            if white is None:
                white = black.copy()
            if black.size != white.size:
                white = white.resize(black.size, RESAMPLE)
            blended = Image.blend(black, white, t).convert("RGBA")
            photo   = self._pil_to_photo(blended)
            self._blend_cache[key] = photo
            return photo
        except Exception:
            return None

    # ─────────────────────────────────────────────────────────────────────────
    #  Button creation
    # ─────────────────────────────────────────────────────────────────────────

    def _create_menu_button(self, text, icon_base, row, top_padding=None):
        top_padding = top_padding if top_padding is not None else self._BTN_PADY

        btn_container = ctk.CTkFrame(self, fg_color="transparent", height=self._BTN_HEIGHT)
        btn_container.grid(
            row=row, column=0,
            padx=self._BTN_PADX,
            pady=(top_padding, self._BTN_PADY),
            sticky="ew"
        )
        btn_container.grid_columnconfigure(0, weight=1)

        self._load_icon_variants(icon_base)
        img0 = self._get_blended_icon(icon_base, 0)

        inactive_bg   = "#FFFFFF"
        inactive_text = "#6B7280"
        hover_bg      = "#5899FA"
        hover_text    = "#585858"
        active_bg     = "#166FFF"
        active_text   = "#FFFFFF"

        original_text = f" {text}".upper()

        btn = ctk.CTkButton(
            master=btn_container,
            text=original_text,
            image=img0,
            compound="left",
            fg_color=inactive_bg,
            hover=False,
            corner_radius=self._BTN_RADIUS,
            height=self._BTN_HEIGHT,
            anchor="w",
            text_color=inactive_text,
            font=ctk.CTkFont(family="Segoe UI", size=self._FONT_SIZE, weight="bold"),
            command=lambda t=text, b=None: self.menu_clicked(t, btn),
        )
        btn.grid(row=0, column=0, sticky="ew", padx=(15, 5))

        btn._original_text            = original_text
        self._button_containers[text] = btn_container

        btn.icon_base         = icon_base
        btn._icon_blend_steps = self._ANIM_STEPS
        btn._inactive_bg      = inactive_bg
        btn._inactive_text    = inactive_text
        btn._hover_bg         = hover_bg
        btn._active_bg        = active_bg
        btn._active_text      = active_text
        btn._hover_text       = hover_text
        btn._anim_progress    = 0.0
        btn._anim_target      = 0.0
        btn._anim_job         = None

        btn.bind("<Enter>", lambda e, b=btn: self._on_button_enter(b))
        btn.bind("<Leave>", lambda e, b=btn: self._on_button_leave(b))
        return btn

    def _create_leave_button(self, row, top_padding=None, bottom_padding=40):
        top_padding = top_padding if top_padding is not None else self._BTN_PADY

        leave_container = ctk.CTkFrame(self, fg_color="transparent", height=self._BTN_HEIGHT)
        leave_container.grid(
            row=row, column=0,
            padx=self._BTN_PADX,
            pady=(top_padding, bottom_padding),
            sticky="ew"
        )
        leave_container.grid_columnconfigure(0, weight=1)

        self._load_icon_variants("leave")
        img0 = self._get_blended_icon("leave", 0)

        leave_bg       = "#FEF2F2"
        leave_hover_bg = "#FEE5E5"
        leave_text     = "#DD2A2A"
        original_text  = " LEAVE"

        btn = ctk.CTkButton(
            master=leave_container,
            text=original_text,
            image=img0,
            compound="left",
            fg_color=leave_bg,
            hover=False,
            corner_radius=self._BTN_RADIUS,
            height=self._BTN_HEIGHT,
            anchor="w",
            text_color=leave_text,
            font=ctk.CTkFont(family="Segoe UI", size=self._FONT_SIZE, weight="bold"),
            command=lambda: self.menu_clicked("Leave", None),
        )
        btn.grid(row=0, column=0, sticky="ew", padx=(15, 5))

        btn._original_text    = original_text
        self._leave_container = leave_container

        btn.icon_base         = "leave"
        btn._icon_blend_steps = self._ANIM_STEPS
        btn._anim_progress    = 0.0
        btn._anim_target      = 0.0
        btn._anim_job         = None
        btn._inactive_bg      = leave_bg
        btn._hover_bg         = leave_hover_bg
        btn._inactive_text    = leave_text
        btn._hover_text       = leave_text
        btn._is_leave_button  = True

        btn.bind("<Enter>", lambda e, b=btn: self._on_leave_button_enter(b))
        btn.bind("<Leave>", lambda e, b=btn: self._on_leave_button_leave(b))
        return btn

    # ─────────────────────────────────────────────────────────────────────────
    #  Hover & animation
    # ─────────────────────────────────────────────────────────────────────────

    def _on_button_enter(self, btn):
        if btn is self.active_button:
            return
        btn._anim_target = 0.1
        self._start_anim_loop(btn)

    def _on_button_leave(self, btn):
        if btn is self.active_button:
            return
        btn._anim_target = 0.0
        self._start_anim_loop(btn)

    def _on_leave_button_enter(self, btn):
        btn._anim_target = 0.1
        self._start_leave_anim_loop(btn)

    def _on_leave_button_leave(self, btn):
        btn._anim_target = 0.0
        self._start_leave_anim_loop(btn)

    def _start_anim_loop(self, btn):
        if btn._anim_job is not None:
            try:
                self.after_cancel(btn._anim_job)
            except Exception:
                pass
            btn._anim_job = None

        def step():
            progress = btn._anim_progress
            target   = btn._anim_target
            if math.isclose(progress, target, abs_tol=1e-3):
                btn._anim_progress = target
                btn._anim_job      = None
                self._apply_anim_state(btn)
                return
            delta = 0.7 / float(self._ANIM_STEPS)
            progress = min(target, progress + delta) if progress < target else max(target, progress - delta)
            btn._anim_progress = progress
            self._apply_anim_state(btn)
            btn._anim_job = self.after(self._ANIM_INTERVAL_MS, step)

        step()

    def _start_leave_anim_loop(self, btn):
        if btn._anim_job is not None:
            try:
                self.after_cancel(btn._anim_job)
            except Exception:
                pass
            btn._anim_job = None

        def step():
            progress = btn._anim_progress
            target   = btn._anim_target
            if math.isclose(progress, target, abs_tol=1e-3):
                btn._anim_progress = target
                btn._anim_job      = None
                self._apply_leave_anim_state(btn)
                return
            delta = 0.7 / float(self._ANIM_STEPS)
            progress = min(target, progress + delta) if progress < target else max(target, progress - delta)
            btn._anim_progress = progress
            self._apply_leave_anim_state(btn)
            btn._anim_job = self.after(self._ANIM_INTERVAL_MS, step)

        step()

    def _apply_anim_state(self, btn):
        p = btn._anim_progress
        try:
            if btn is self.active_button:
                btn.configure(fg_color=btn._active_bg, text_color=btn._active_text)
                white_img = self._get_blended_icon(btn.icon_base, self._ANIM_STEPS)
                if white_img:
                    btn.configure(image=white_img)
                return
            bg         = lerp_color(btn._inactive_bg, btn._hover_bg, p)
            text_color = lerp_color(btn._inactive_text, btn._hover_text, p)
            btn.configure(fg_color=bg, text_color=text_color)
            step_index = int(round(p * self._ANIM_STEPS))
            photo = self._get_blended_icon(btn.icon_base, step_index)
            if photo:
                btn.configure(image=photo)
        except Exception:
            pass

    def _apply_leave_anim_state(self, btn):
        p = btn._anim_progress
        try:
            bg = lerp_color(btn._inactive_bg, btn._hover_bg, p)
            btn.configure(fg_color=bg, text_color=btn._inactive_text)
            photo = self._get_blended_icon(btn.icon_base, 0)
            if photo:
                btn.configure(image=photo)
        except Exception:
            pass

    # ─────────────────────────────────────────────────────────────────────────
    #  Active state management
    # ─────────────────────────────────────────────────────────────────────────

    def menu_clicked(self, menu_name, button):
        if menu_name != "Leave" and button is not None:
            self.set_active_button(button)
        if self.on_menu_click:
            try:
                self.on_menu_click(menu_name)
            except Exception:
                pass

    def set_active_button(self, button):
        if self.active_button and self.active_button is not button:
            prev = self.active_button
            try:
                prev.configure(fg_color=prev._inactive_bg, text_color=prev._inactive_text)
                photo_black = self._get_blended_icon(prev.icon_base, 0)
                if photo_black:
                    prev.configure(image=photo_black)
                prev._anim_progress = 0.0
                prev._anim_target   = 0.0
                if prev._anim_job:
                    try:
                        self.after_cancel(prev._anim_job)
                    except Exception:
                        pass
                    prev._anim_job = None
            except Exception:
                pass

        self.active_button = button
        if button:
            try:
                button.configure(fg_color=button._active_bg, text_color=button._active_text)
                photo_white = self._get_blended_icon(button.icon_base, self._ANIM_STEPS)
                if photo_white:
                    button.configure(image=photo_white)
                button._anim_progress = 1.0
                button._anim_target   = 1.0
                if button._anim_job:
                    try:
                        self.after_cancel(button._anim_job)
                    except Exception:
                        pass
                    button._anim_job = None
            except Exception:
                pass

    # ─────────────────────────────────────────────────────────────────────────
    #  Collapse / Expand
    # ─────────────────────────────────────────────────────────────────────────

    def collapse(self):
        """Mode réduit : enlever le texte et réduire la largeur."""
        self._is_collapsed = True

        self.configure(width=self._COLLAPSED_WIDTH)

        if self._logo_label:
            try:
                self._logo_label.pack_forget()
            except Exception:
                pass
        
        if hasattr(self, '_small_logo_label') and self._small_logo_label:
            try:
                self.update()
                self._small_logo_label.pack(anchor="center", padx=(5, 10))
            except Exception:
                pass

        # Enlever le texte, centrer l'icône et réinitialiser le grid
        for name, btn in self.menu_buttons.items():
            if btn.winfo_exists():
                btn.configure(text="", anchor="center")
                btn.grid_configure(sticky="", padx=5)

        if self._leave_button and self._leave_button.winfo_exists():
            self._leave_button.configure(text="", anchor="center")
            self._leave_button.grid_configure(sticky="", padx=5)

    def expand(self):
        """Mode normal : boutons rectangulaires avec texte."""
        self._is_collapsed = False

        self.configure(width=self._EXPANDED_WIDTH)

        if hasattr(self, '_small_logo_label') and self._small_logo_label:
            try:
                self._small_logo_label.pack_forget()
            except Exception:
                pass
        if self._logo_label:
            try:
                self._logo_label.pack(anchor="center")
            except Exception:
                pass

        for i, (name, container) in enumerate(self._button_containers.items()):
            if container.winfo_exists():
                # Restaurer le padding original
                top_pad = self._BTN_PADY_FIRST if i == 0 else self._BTN_PADY
                container.configure(height=self._BTN_HEIGHT, width=0)
                container.grid_configure(padx=self._BTN_PADX, pady=(top_pad, self._BTN_PADY), sticky="ew")
                container.grid_propagate(True)

        for name, btn in self.menu_buttons.items():
            if btn.winfo_exists() and hasattr(btn, "_original_text"):
                btn.place_forget()
                btn.configure(
                    text=btn._original_text,
                    height=self._BTN_HEIGHT,
                    width=0,
                    anchor="w",
                    corner_radius=self._BTN_RADIUS,
                )
                btn.grid_configure(sticky="ew", padx=(15, 5))

        if self._leave_container and self._leave_container.winfo_exists():
            self._leave_container.configure(height=self._BTN_HEIGHT, width=0)
            self._leave_container.grid_configure(padx=self._BTN_PADX, sticky="ew")
            self._leave_container.grid_propagate(True)
        if self._leave_button and self._leave_button.winfo_exists() and hasattr(self._leave_button, "_original_text"):
            self._leave_button.place_forget()
            self._leave_button.configure(
                text=self._leave_button._original_text,
                height=self._BTN_HEIGHT,
                width=0,
                anchor="w",
                corner_radius=self._BTN_RADIUS,
            )
            self._leave_button.grid_configure(sticky="ew", padx=(15, 5))