import os
import logging
import customtkinter as ctk
from PIL import Image, ImageDraw
from typing import Optional, Callable
from datetime import datetime
from app.components.toast_confirm import show_confirm_toast
from app.components.toast_success import show_success_toast

# Constante pour la compatibilité PIL/Pillow (LANCZOS = 1)
LANCZOS_FILTER = 1  # LANCZOS = 1 dans PIL

# Import du contrôleur
from controllers import settings_controller

# Import du date picker
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

ICONS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "assets", "icons"))


class AddEmployeeWindow(ctk.CTkToplevel):
    """Popup window to add a new employee"""

    THEME = {
        "bg": "#F8F9FA",
        "card_bg": "#FFFFFF",
        "white": "#FFFFFF",
        "primary": "#4081F5",
        "primary_hover": "#5899FA",
        "text_dark": "#1E293B",
        "text_gray": "#9CA3AF",
        "text_medium": "#6B7280",
        "border": "#E5E7EB",
        "input_bg": "#F7F9FB",
        "label_text": "#A0AEC0",
        "close_hover": "#F3F4F6",
        "danger": "#EF4444",
        "danger_hover": "#DC2626",
    }

    def __init__(self, parent, on_submit=None, icons_dir=None):
        super().__init__(parent)
        
        self.on_submit = on_submit
        self.icons_dir = icons_dir or ICONS_DIR
        self._icon_cache = {}
        
        self.title("Add Employee")
        self.geometry("600x750")
        self.resizable(False, False)
        self.configure(fg_color=self.THEME["white"])
        
        self.transient(parent)
        self.grab_set()
        
        print(f"[DEBUG] AddEmployeeWindow parent: {parent}")
        self._build_ui()
        print(f"[DEBUG] AddEmployeeWindow built successfully")

    def _build_ui(self):
        print(f"[DEBUG] _build_ui started")
        main = ctk.CTkFrame(self, fg_color=self.THEME["white"])
        main.pack(fill="both", expand=True, padx=30, pady=30)
        print(f"[DEBUG] main frame created")

        header = ctk.CTkFrame(main, fg_color="transparent")
        header.pack(fill="x", pady=(0, 25))

        ctk.CTkLabel(header, text="Add New Employee",
            font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"),
            text_color=self.THEME["text_dark"]
        ).pack(side="left")
        print(f"[DEBUG] header created")

        form = ctk.CTkFrame(main, fg_color="transparent")
        form.pack(fill="both", expand=True)

        form.grid_columnconfigure(0, weight=1, uniform="col")
        form.grid_columnconfigure(1, weight=1, uniform="col")

        self.first_name_var = ctk.StringVar()
        self.last_name_var = ctk.StringVar()
        self.email_var = ctk.StringVar()
        self.phone_var = ctk.StringVar()
        self.address_var = ctk.StringVar()
        self.password_var = ctk.StringVar()
        self.role_var = ctk.StringVar(value="IT_TECHNICIAN")
        self.gender_var = ctk.StringVar(value="male")

        print(f"[DEBUG] Creating form inputs...")
        self._form_input(form, 0, 0, "FIRST NAME", self.first_name_var)
        self._form_input(form, 0, 1, "LAST NAME", self.last_name_var)
        self._form_input(form, 1, 0, "EMAIL", self.email_var, colspan=2)
        self._form_input(form, 2, 0, "PASSWORD", self.password_var, colspan=2, is_password=True)
        self._form_input(form, 3, 0, "PHONE", self.phone_var, colspan=1)
        self._form_input(form, 3, 1, "ADDRESS", self.address_var, colspan=1)
        print(f"[DEBUG] Form inputs created")

        self._role_selector(form, 4, 0, colspan=1)
        self._gender_selector(form, 4, 1, colspan=1)
        print(f"[DEBUG] Role and gender selectors created")

        btn_frame = ctk.CTkFrame(main, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(25, 0))

        cancel_btn = ctk.CTkButton(
            btn_frame, text="CANCEL",
            height=48,
            width=140,
            fg_color="#FEF2F2",
            hover_color="#FEE5E5",
            text_color="#DD2A2A",
            border_width=1.5,
            border_color="#FEE5E5",
            corner_radius=16,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            command=self.destroy
        )
        cancel_btn.pack(side="left")

        reset_btn = ctk.CTkButton(
            btn_frame, text="RESET",
            height=48,
            width=140,
            fg_color="#F7F9FB",
            hover_color="#EFEFF2",
            text_color="#6B7280",
            corner_radius=16,
            border_width=1.5,
            border_color=self.THEME["border"],
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            command=self._reset_form
        )
        reset_btn.pack(side="left", padx=(10, 0))

        ctk.CTkButton(
            btn_frame, text="CONFIRM ENTRY",
            height=48,
            width=220,
            fg_color=self.THEME["primary"],
            hover_color=self.THEME["primary_hover"],
            text_color=self.THEME["white"],
            corner_radius=16,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            command=self._submit
        ).pack(side="right")

    def _form_input(self, grid, row, col, label_text, variable, colspan=1, is_password=False):
        container = ctk.CTkFrame(grid, fg_color="transparent", width=280)
        grid.grid_columnconfigure(col, weight=1)
        
        if colspan == 2:
            container.grid(row=row, column=col, columnspan=2, sticky="ew", padx=(0 if col == 0 else 8, 0), pady=(0, 20))
        else:
            container.grid(row=row, column=col, sticky="ew", padx=(0 if col == 0 else 8, 8), pady=(0, 20))

        label_widget = ctk.CTkLabel(container, text=label_text,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=self.THEME["label_text"], anchor="w"
        )
        label_widget.pack(anchor="w", pady=(0, 10))

        entry_frame = ctk.CTkFrame(
            container,
            fg_color=self.THEME["input_bg"],
            corner_radius=16,
            height=50,
            border_width=1.5,
            border_color=self.THEME["border"]
        )
        entry_frame.pack(fill="x")
        entry_frame.pack_propagate(False)

        show = "•" if is_password else None
        
        entry = ctk.CTkEntry(entry_frame, textvariable=variable,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color="transparent",
            text_color=self.THEME["text_dark"],
            border_width=0, show=show)
        entry.pack(side="left", fill="x", expand=True, padx=(16, 8), pady=(6, 6))
        
        def on_focus_in(event):
            label_widget.configure(text_color=self.THEME["primary"])
            entry_frame.configure(border_color=self.THEME["primary"], border_width=2.3)
        
        def on_focus_out(event):
            label_widget.configure(text_color=self.THEME["label_text"])
            entry_frame.configure(border_color=self.THEME["border"], border_width=1)
        
        entry.bind("<FocusIn>", on_focus_in)
        entry.bind("<FocusOut>", on_focus_out)
        entry_frame.bind("<Button-1>", lambda e: entry.focus_set())
        
        self._entry_refs = getattr(self, '_entry_refs', {})
        self._entry_refs[label_text] = (entry, entry_frame, label_widget)

    def _role_selector(self, grid, row, col, colspan=1):
        container = ctk.CTkFrame(grid, fg_color="transparent", width=280)
        grid.grid_columnconfigure(col, weight=1)
        
        if colspan == 2:
            container.grid(row=row, column=col, columnspan=2, sticky="ew", padx=(0 if col == 0 else 10, 0), pady=(0, 20))
        else:
            container.grid(row=row, column=col, sticky="ew", padx=(0 if col == 0 else 10, 8), pady=(0, 20))

        label_widget = ctk.CTkLabel(container, text="ROLE",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=self.THEME["label_text"], anchor="w"
        )
        label_widget.pack(anchor="w", pady=(0, 10))

        dropdown_frame = ctk.CTkFrame(
            container,
            fg_color=self.THEME["input_bg"],
            corner_radius=16,
            height=50,
            border_width=1.5,
            border_color=self.THEME["border"]
        )
        dropdown_frame.pack(fill="x")
        dropdown_frame.pack_propagate(False)

        options = ["IT_MANAGER", "IT_TECHNICIAN"]
        
        selected_var = ctk.StringVar(value=options[0] if self.role_var.get() not in options else self.role_var.get())
        
        selected_label = ctk.CTkLabel(
            dropdown_frame,
            textvariable=selected_var,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=self.THEME["text_dark"],
            anchor="w"
        )
        selected_label.place(relx=0.05, rely=0.5, anchor="w")
        
        try:
            chevron_icon_path = os.path.join(self.icons_dir, "chevron-down.png")
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
                text_color=self.THEME["text_gray"]
            )
            arrow_label.place(relx=0.92, rely=0.5, anchor="center")
        
        popup_window = {"window": None}
        
        def set_focus():
            label_widget.configure(text_color=self.THEME["primary"])
            dropdown_frame.configure(border_color=self.THEME["primary"], border_width=2)
        
        def remove_focus():
            label_widget.configure(text_color=self.THEME["label_text"])
            dropdown_frame.configure(border_color=self.THEME["border"], border_width=1)
        
        def toggle_dropdown(event=None):
            if popup_window["window"] and popup_window["window"].winfo_exists():
                popup_window["window"].destroy()
                popup_window["window"] = None
                remove_focus()
                return
            
            set_focus()
            
            popup = ctk.CTkToplevel(self)
            popup.wm_overrideredirect(True)
            popup.configure(fg_color=self.THEME["white"])
            popup_window["window"] = popup
            
            dropdown_frame.update_idletasks()
            x = dropdown_frame.winfo_rootx()
            y = dropdown_frame.winfo_rooty() + dropdown_frame.winfo_height() + 5
            
            popup_container = ctk.CTkFrame(
                popup,
                fg_color=self.THEME["white"],
                corner_radius=14,
                border_width=1.5,
                border_color="#E5E7EB"
            )
            popup_container.pack(padx=2, pady=2)
            
            scroll_frame = ctk.CTkScrollableFrame(
                popup_container,
                fg_color=self.THEME["white"],
                width=200,
                height=min(150, len(options) * 40),
                scrollbar_button_color="#CBD5E1",
                scrollbar_button_hover_color="#9CA3AF"
            )
            scroll_frame.pack(padx=(8, 2), pady=8)
            
            def select_option(option):
                selected_var.set(option)
                self.role_var.set(option)
                popup.destroy()
                popup_window["window"] = None
                remove_focus()
            
            for option in options:
                is_selected = (selected_var.get() == option)
                
                option_btn = ctk.CTkButton(
                    scroll_frame,
                    text=option,
                    font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                    fg_color=self.THEME["primary"] if is_selected else "transparent",
                    hover_color=self.THEME["primary_hover"] if is_selected else "#F3F4F6",
                    text_color=self.THEME["white"] if is_selected else self.THEME["text_dark"],
                    anchor="w",
                    height=36,
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

    def _gender_selector(self, grid, row, col, colspan=1):
        wrapper = ctk.CTkFrame(grid, fg_color="transparent")
        grid.grid_columnconfigure(col, weight=1)
        wrapper.grid(row=row, column=col, columnspan=colspan, sticky="ew",
                    padx=(0 if col == 0 else 10, 0 if (col + colspan) >= 2 else 10),
                    pady=(0, 16))

        label_widget = ctk.CTkLabel(wrapper, text="GENDER",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=self.THEME["label_text"], anchor="w"
        )
        label_widget.pack(anchor="w", pady=(0, 10))

        gender_row = ctk.CTkFrame(wrapper, fg_color="transparent")
        gender_row.pack(fill="x")

        self._radio_button(gender_row, "MALE", "male")
        self._radio_button(gender_row, "FEMALE", "female")

    def _radio_button(self, parent, label, value):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(side="left", padx=(0, 28))

        ring = ctk.CTkFrame(row, corner_radius=50, width=22, height=22,
                            border_width=2, border_color=self.THEME["text_gray"],
                            fg_color="transparent", cursor="hand2")
        ring.pack(side="left", padx=(0, 8))
        ring.pack_propagate(False)

        dot = ctk.CTkFrame(ring, fg_color=self.THEME["primary"],
                           corner_radius=50, width=10, height=10)

        def update_radio(*_):
            if self.gender_var.get() == value:
                ring.configure(border_color=self.THEME["primary"])
                dot.place(relx=0.5, rely=0.5, anchor="center")
            else:
                ring.configure(border_color=self.THEME["text_gray"])
                dot.place_forget()

        def on_click(e=None):
            self.gender_var.set(value)
            update_radio()

        text_lbl = ctk.CTkLabel(row, text=label,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=self.THEME["text_dark"], cursor="hand2")
        text_lbl.pack(side="left")

        for w in (ring, dot, text_lbl):
            w.bind("<Button-1>", on_click)

        self.gender_var.trace_add("write", lambda *_: update_radio())
        update_radio()

    def _submit(self):
        data = {
            "first_name": self.first_name_var.get().strip(),
            "last_name": self.last_name_var.get().strip(),
            "email": self.email_var.get().strip(),
            "password": self.password_var.get().strip(),
            "phone_number": self.phone_var.get().strip(),
            "address": self.address_var.get().strip(),
            "role_name": self.role_var.get(),
            "gender": self.gender_var.get(),
            "date_of_birth": "",
        }

        if not data["first_name"] or not data["last_name"] or not data["email"] or not data["password"]:
            from app.components.toast_error import show_error_toast
            show_error_toast(
                parent=self,
                message="Please fill in all required fields",
                duration=3000,
                top_padding=30
            )
            return

        if self.on_submit:
            self.on_submit(data)
        
        self.destroy()

    def _reset_form(self):
        self.first_name_var.set("")
        self.last_name_var.set("")
        self.email_var.set("")
        self.password_var.set("")
        self.phone_var.set("")
        self.address_var.set("")
        self.role_var.set("IT_TECHNICIAN")
        self.gender_var.set("male")


class SettingsView(ctk.CTkFrame):

    THEME = {
        "bg": "#F0F4F9",
        "primary": "#166FFF",
        "primary_hover": "#1258CC",
        "primary_light": "#E8F0FE",
        "text_dark": "#28313F",
        "text_gray": "#9CA3AF",
        "text_medium": "#6B7280",
        "white": "#FFFFFF",
        "input_bg": "#F0F4F9",
        "border": "#E5E7EB",
        "danger": "#EF4444",
        "danger_hover": "#DC2626",
    }

    NAV_ITEMS_CONFIG = [
        {"key": "personal",    "label": "PERSONAL INFORMATION", "icon": "user"},
        {"key": "password",    "label": "PASSWORD",             "icon": "lock"},
        {"key": "employees",   "label": "EMPLOYEE",             "icon": "users", "ceo_only": True},
    ]


    def __init__(self, parent, on_save_callback: Optional[Callable] = None, initial_page: str = "personal", on_timer_format_change: Optional[Callable] = None, **kwargs):
        super().__init__(parent, **kwargs)
        self.configure(fg_color=self.THEME["bg"], corner_radius=0)
        self.pack(fill="both", expand=True)

        self._icon_cache = {}
        self.on_save_callback = on_save_callback
        self.on_timer_format_change = on_timer_format_change
        self._active_key = initial_page
        self._nav_buttons = {}
        self._content_frames = {}

        try:
            self.user_data = settings_controller.get_user_profile()
            logger.info(f"Loaded user profile: {self.user_data.get('first_name')} {self.user_data.get('last_name')}")
        except Exception as e:
            logger.exception(f"Failed to load user profile: {e}")
            self.user_data = settings_controller.get_default_user_profile()
        
        self.original_data = self.user_data.copy()

        # Filtrer les items de navigation selon le rôle
        # Pour le debug, affichons le user_data
        print(f"[DEBUG] User data for role check (from __init__): {self.user_data}")
        is_ceo = self.user_data.get("role") == "CEO" # Strict check for CEO role

        self.nav_items = [
            item for item in self.NAV_ITEMS_CONFIG 
            if not item.get("ceo_only") or is_ceo
        ]

        # StringVars
        self.first_name_var    = ctk.StringVar(value=self.user_data.get("first_name", ""))
        self.last_name_var     = ctk.StringVar(value=self.user_data.get("last_name", ""))
        self.email_var         = ctk.StringVar(value=self.user_data.get("email", ""))
        self.phone_var         = ctk.StringVar(value=self.user_data.get("phone", ""))
        
        # Date de naissance avec 3 dropdowns (jour, mois, année)
        dob_value = self.user_data.get("date_of_birth", "")
        # Gérer les différents formats (string ou datetime.date)
        if hasattr(dob_value, 'year'):
            # C'est un objet datetime.date
            self.dob_day_var = ctk.StringVar(value=str(dob_value.day).zfill(2))
            self.dob_month_var = ctk.StringVar(value=str(dob_value.month).zfill(2))
            self.dob_year_var = ctk.StringVar(value=str(dob_value.year))
        elif isinstance(dob_value, str) and len(dob_value.split('-')) == 3:
            year, month, day = dob_value.split('-')
            self.dob_day_var = ctk.StringVar(value=day)
            self.dob_month_var = ctk.StringVar(value=month)
            self.dob_year_var = ctk.StringVar(value=year)
        else:
            # Valeurs par défaut si pas de date
            self.dob_day_var = ctk.StringVar(value="01")
            self.dob_month_var = ctk.StringVar(value="01")
            self.dob_year_var = ctk.StringVar(value=str(datetime.now().year - 25))
        
        self.address_var       = ctk.StringVar(value=self.user_data.get("address", ""))
        self.gender_var        = ctk.StringVar(value=self.user_data.get("gender", "male"))

        self._build_layout()

    # ──────────────────────────────────────────────────────────────
    # MAIN LAYOUT  →  outer padding → left card + right card side by side
    # ──────────────────────────────────────────────────────────────
    def _build_layout(self):
        # Outer container with uniform padding
        outer = ctk.CTkFrame(self, fg_color="transparent")
        outer.pack(fill="both", expand=True, padx=30, pady=30)

        # ── LEFT SIDEBAR CARD ─────────────────────────────────────
        sidebar = ctk.CTkFrame(outer, fg_color=self.THEME["white"],
                               corner_radius=28, border_width=0)
        sidebar.pack(side="left", fill="y", padx=(0, 16), pady=0)
        sidebar.pack_propagate(False)
        sidebar.configure(width=260)

        self._build_sidebar(sidebar)

        # ── RIGHT CONTENT CARD ────────────────────────────────────
        self.content_card = ctk.CTkFrame(outer, fg_color="transparent",
                                         corner_radius=0)
        self.content_card.pack(side="left", fill="both", expand=True, pady=0)

        # Build all pages based on filtered nav_items
        for item in self.nav_items:
            key = item["key"]
            if key == "personal":
                self._build_personal_page()
            elif key == "password":
                self._build_password_page()
            elif key == "employees":
                self._build_employees_page() # Only built if item is in nav_items

        # Show default
        self._switch_page("personal")

    # ──────────────────────────────────────────────────────────────
    # SIDEBAR  →  avatar block + nav list
    # ──────────────────────────────────────────────────────────────
    def _build_sidebar(self, sidebar):
        # ── Avatar block (centered) ───────────────────────────────
        avatar_block = ctk.CTkFrame(sidebar, fg_color="transparent")
        avatar_block.pack(pady=(40, 30))

        # Container pour l'avatar avec overlay
        avatar_wrapper = ctk.CTkFrame(avatar_block, fg_color="transparent")
        avatar_wrapper.pack()

        # Frame pour l'avatar avec effet hover
        self.avatar_container = ctk.CTkFrame(avatar_wrapper, 
                                             fg_color="transparent",
                                             width=100, height=100)
        self.avatar_container.pack()
        self.avatar_container.pack_propagate(False)

        # Avatar image
        self.avatar_img = self._make_avatar_image(size=100)
        self.avatar_label = ctk.CTkLabel(self.avatar_container, 
                                         image=self.avatar_img, 
                                         text="",
                                         fg_color="transparent")
        self.avatar_label.place(relx=0.5, rely=0.5, anchor="center")

        # Name
        full_name = "{} {}".format(
            self.user_data.get("first_name", "").upper(),
            self.user_data.get("last_name", "").upper()
        )
        self.name_label = ctk.CTkLabel(avatar_block, text=full_name,
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color=self.THEME["text_dark"]
        )
        self.name_label.pack(pady=(12, 2))

        # Title / role
        ctk.CTkLabel(avatar_block, text=self.user_data.get("title", ""),
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=self.THEME["primary"]
        ).pack()

        # ── Bouton CHANGE PHOTO (stylé comme CANCEL CHANGES) ────
        ctk.CTkButton(avatar_block, text="CHANGE PHOTO",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color="transparent",
            hover_color=self.THEME["primary_light"],
            text_color=self.THEME["primary"],
            corner_radius=10, width=130, height=34,
            border_width=2, border_color=self.THEME["primary"],
            command=self._change_profile_photo
        ).pack(pady=(14, 0))

        # ── Nav list ──────────────────────────────────────────────
        nav_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        nav_frame.pack(fill="x", padx=16, pady=(10, 0))

        # Build nav items based on self.nav_items (instance specific)
        for item in self.nav_items:
            self._create_nav_item(nav_frame, item)

        # Spacer pour pousser le bouton logout en bas
        spacer = ctk.CTkFrame(sidebar, fg_color="transparent")
        spacer.pack(fill="both", expand=True)

        # ── Bouton LOGOUT en bas ──────────────────────────────────
        logout_btn = ctk.CTkFrame(sidebar, fg_color="transparent",
                                   corner_radius=10, height=42, cursor="hand2")
        logout_btn.pack(fill="x", padx=16, pady=(0, 30))
        logout_btn.pack_propagate(False)

        # Icon logout
        logout_ico = self._load_icon("leave_red", size=(17, 17))
        logout_icon_lbl = ctk.CTkLabel(logout_btn, image=logout_ico if logout_ico else None,
                                        text="" if logout_ico else "X",
                                        fg_color="transparent", width=17)
        logout_icon_lbl.place(x=16, rely=0.5, anchor="w")

        # Text
        logout_text_lbl = ctk.CTkLabel(logout_btn, text="LOG OUT",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=self.THEME["danger"], anchor="w")
        logout_text_lbl.place(x=42, rely=0.5, anchor="w")

        # Configure background and hover
        logout_btn.configure(fg_color="#FEE2E2")  # Light red background

        # Bindings
        for w in (logout_btn, logout_icon_lbl, logout_text_lbl):
            w.bind("<Button-1>", lambda e: self._show_logout_confirmation())
            w.bind("<Enter>", lambda e: logout_btn.configure(fg_color="#FEE2E2"))
            w.bind("<Leave>", lambda e: logout_btn.configure(fg_color="#FEE2E2"))

    def _create_nav_item(self, parent, item):
        key   = item["key"]
        label = item["label"]
        icon_name = item["icon"]

        # Pill container
        pill = ctk.CTkFrame(parent, fg_color="transparent",
                            corner_radius=10, height=42, cursor="hand2")
        pill.pack(fill="x", pady=(3, 3))
        pill.pack_propagate(False)

        # Icon
        ico = self._load_icon(icon_name, size=(17, 17))
        icon_lbl = ctk.CTkLabel(pill, image=ico if ico else None,
                                text="" if ico else "?",
                                fg_color="transparent", width=17)
        icon_lbl.place(x=16, rely=0.5, anchor="w")

        # Text
        text_lbl = ctk.CTkLabel(pill, text=label,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=self.THEME["text_medium"], anchor="w")
        text_lbl.place(x=42, rely=0.5, anchor="w")

        self._nav_buttons[key] = (pill, icon_lbl, text_lbl)

        # Bindings on pill + children
        for w in (pill, icon_lbl, text_lbl):
            w.bind("<Button-1>", lambda e, k=key: self._switch_page(k))
            w.bind("<Enter>",    lambda e, k=key: self._nav_hover(k, True))
            w.bind("<Leave>",    lambda e, k=key: self._nav_hover(k, False))

    def _nav_hover(self, key, entering):
        if key == self._active_key:
            return
        pill, _, text_lbl = self._nav_buttons[key]
        if entering:
            pill.configure(fg_color="#F3F4F6")
            text_lbl.configure(text_color=self.THEME["text_dark"])
        else:
            pill.configure(fg_color="transparent")
            text_lbl.configure(text_color=self.THEME["text_medium"])

    def _switch_page(self, key):
        # Deactivate old
        if self._active_key and self._active_key in self._nav_buttons:
            pill, icon_lbl, text_lbl = self._nav_buttons[self._active_key]
            pill.configure(fg_color="transparent")
            text_lbl.configure(text_color=self.THEME["text_medium"])
            # Reset icon tint — reload normal icon (gray version)
            old_item = next((i for i in self.nav_items if i["key"] == self._active_key), None)
            if old_item:
                ico = self._load_icon(old_item["icon"], size=(17, 17))
                if ico:
                    icon_lbl.configure(image=ico)

        # Activate new
        self._active_key = key
        pill, icon_lbl, text_lbl = self._nav_buttons[key]

        pill.configure(fg_color=self.THEME["primary_light"])
        text_lbl.configure(text_color=self.THEME["primary"])
        # Charger l'icône bleue pour personal/password/employees
        new_item = next((i for i in self.nav_items if i["key"] == key), None)
        if new_item:
            colored_ico = self._load_icon(new_item["icon"] + "_blue", size=(17, 17))
            if colored_ico:
                icon_lbl.configure(image=colored_ico)

        # Show/hide pages
        for k, frame in self._content_frames.items():
            if k == key:
                frame.pack(fill="both", expand=True)
            else:
                frame.pack_forget()

    # ──────────────────────────────────────────────────────────────
    # PAGE: PERSONAL INFORMATION
    # ──────────────────────────────────────────────────────────────
    def _build_personal_page(self):
        page = ctk.CTkFrame(self.content_card,
                           fg_color=self.THEME["white"],
                           corner_radius=28,
                           border_width=0)
        self._content_frames["personal"] = page

        inner = ctk.CTkFrame(page, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=40, pady=40)

        # Cliquer sur l'inner force la perte de focus des champs
        inner.bind("<Button-1>", lambda e: self.focus_set(), add=True)

        # Page title
        self._personal_title = ctk.CTkLabel(inner, text="PERSONAL INFORMATION",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color=self.THEME["text_dark"], anchor="w"
        )
        self._personal_title.pack(anchor="w", pady=(0, 24))

        # ── Gender radio row ──────────────────────────────────────
        gender_row = ctk.CTkFrame(inner, fg_color="transparent")
        gender_row.pack(fill="x", pady=(0, 8))

        self._radio_button(gender_row, "MALE", "male")
        self._radio_button(gender_row, "FEMALE", "female")

        # ── Form grid (2 columns) ─────────────────────────────────
        grid = ctk.CTkFrame(inner, fg_color="transparent")
        grid.pack(fill="x", anchor="n")
        # Forcer une répartition égale 50/50 des colonnes
        grid.grid_columnconfigure(0, weight=1, uniform="col")
        grid.grid_columnconfigure(1, weight=1, uniform="col")

        # Row 0: First Name | Last Name
        self._form_input(grid, 0, 0, "FIRST NAME",  self.first_name_var)
        self._form_input(grid, 0, 1, "LAST NAME",   self.last_name_var)

        # Row 1: Email (full width)
        self._form_input(grid, 1, 0, "EMAIL ADDRESS", self.email_var, colspan=2)

        # Row 2: Address (full width)
        self._form_input(grid, 2, 0, "ADDRESS", self.address_var, colspan=2)

        # Row 3: Phone | Date of Birth
        # Ajouter extra_top_padding=4 pour aligner avec le calendrier qui a un label plus haut
        self._form_input(grid, 3, 0, "PHONE NUMBER",  self.phone_var, extra_top_padding=10)
        self._create_date_picker_grid(grid, 3, 1, "DATE OF BIRTH")

        # ── Bottom buttons (right-aligned) ────────────────────────
        btn_row = ctk.CTkFrame(inner, fg_color="transparent")
        btn_row.pack(fill="x", pady=(30, 0), side="bottom")

        # SAVE CHANGES
        ctk.CTkButton(btn_row, text="SAVE CHANGES",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color=self.THEME["primary"],
            hover_color=self.THEME["primary_hover"],
            text_color=self.THEME["white"],
            corner_radius=10, width=180, height=46, border_width=0,
            command=self._on_save
        ).pack(side="right")

        # CANCEL CHANGES
        ctk.CTkButton(btn_row, text="CANCEL CHANGES",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color=self.THEME["white"],
            hover_color="#FEE2E2",
            text_color="#DC2626",
            corner_radius=10, width=190, height=46,
            border_width=2, border_color="#DC2626",
            command=self._on_reset
        ).pack(side="right", padx=(0, 12))

    # ──────────────────────────────────────────────────────────────
    # PAGE: LOGIN & PASSWORD - Modern Design
    # ──────────────────────────────────────────────────────────────
    def _build_password_page(self):
        page = ctk.CTkFrame(self.content_card,
                           fg_color=self.THEME["white"],
                           corner_radius=28,
                           border_width=0)
        self._content_frames["password"] = page

        inner = ctk.CTkFrame(page, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=40, pady=40)

        # Cliquer sur l'inner force la perte de focus des champs
        inner.bind("<Button-1>", lambda e: self.focus_set(), add=True)

        # Header Section
        header_frame = ctk.CTkFrame(inner, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 10))

        self._password_title = ctk.CTkLabel(header_frame, text="PASSWORD",
            font=ctk.CTkFont(family="Segoe UI", size=26, weight="bold"),
            text_color=self.THEME["text_dark"]
        )
        self._password_title.pack(side="left")

        self._security_badge = ctk.CTkLabel(header_frame,
            text="ENHANCED SECURITY",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#059669",
            fg_color="#ecfdf5",
            corner_radius=25,
            padx=20,
            pady=8
        )
        self._security_badge.pack(side="right")

        # Footer Area (Success message + Button)
        self.password_footer_frame = ctk.CTkFrame(inner, fg_color="transparent")
        self.password_footer_frame.pack(side="bottom", fill="x", pady=(20, 0))

        # Success Label (hidden by default)
        self.password_success_label = ctk.CTkLabel(
            self.password_footer_frame, 
            text="Password changed successfully", 
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#059669"
        )

        # Submit Button - même style que SAVE CHANGES
        self.password_submit_btn = ctk.CTkButton(
            self.password_footer_frame,
            text="CHANGE PASSWORD",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color=self.THEME["primary"],
            hover_color=self.THEME["primary_hover"],
            text_color=self.THEME["white"],
            corner_radius=10,
            width=200,
            height=46,
            border_width=0,
            state="disabled",
            command=self._on_save_password
        )
        self.password_submit_btn.pack(side="right")

        # Error Banner (hidden by default)
        self.password_error_banner = ctk.CTkFrame(inner, fg_color="#fef2f2", border_color="#fee2e2", border_width=1, corner_radius=16)
        self.password_error_label = ctk.CTkLabel(
            self.password_error_banner,
            text="NEW PASSWORD CANNOT BE THE SAME AS CURRENT",
            text_color="#ef4444",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold")
        )

        # Blue Input Box
        self._password_input_box = ctk.CTkFrame(inner, fg_color="#f8fbff", corner_radius=40, border_color="#eff6ff", border_width=1)
        self._password_input_box.pack(fill="both", expand=True, pady=(10, 20))

        # State variables for animation
        self.password_target_progress = 0
        self.password_current_progress = 0
        self.password_animation_running = False

        # Current Password
        self.curr_label = self._create_password_label(self._password_input_box, "CURRENT PASSWORD")
        self.curr_label.pack(anchor="w", padx=40, pady=(30, 5))
        self.curr_entry_frame, self.curr_entry = self._create_password_entry(self._password_input_box, "current", self.curr_label)
        self.curr_entry_frame.pack(fill="x", padx=40, pady=(0, 20))

        # Divider
        divider = ctk.CTkFrame(self._password_input_box, height=1, fg_color=self.THEME["border"])
        divider.pack(fill="x", padx=40, pady=5)

        # New & Confirm Grid
        grid_frame = ctk.CTkFrame(self._password_input_box, fg_color="transparent")
        grid_frame.pack(fill="x", padx=40, pady=5)
        grid_frame.grid_columnconfigure((0, 1), weight=1)

        # New Password
        self.new_label = self._create_password_label(grid_frame, "NEW PASSWORD")
        self.new_label.grid(row=0, column=0, sticky="w", padx=(0, 15))
        self.new_entry_frame, self.new_entry = self._create_password_entry(grid_frame, "new", self.new_label)
        self.new_entry_frame.grid(row=1, column=0, sticky="ew", padx=(0, 15), pady=(0, 20))

        # Confirm Password
        self.conf_label = self._create_password_label(grid_frame, "CONFIRM PASSWORD")
        self.conf_label.grid(row=0, column=1, sticky="w", padx=(15, 0))
        self.conf_entry_frame, self.conf_entry = self._create_password_entry(grid_frame, "confirm", self.conf_label)
        self.conf_entry_frame.grid(row=1, column=1, sticky="ew", padx=(15, 0), pady=(0, 20))

        # Strength Bar Container
        strength_container = ctk.CTkFrame(self._password_input_box, fg_color="transparent")
        strength_container.pack(fill="x", padx=40, pady=(0, 30))

        strength_header = ctk.CTkFrame(strength_container, fg_color="transparent")
        strength_header.pack(fill="x")
        self._create_password_label(strength_header, "SECURITY STRENGTH").pack(side="left")
        self.strength_text = ctk.CTkLabel(strength_header, text="", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color="#94a3b8")
        self.strength_text.pack(side="right")

        self.strength_bar = ctk.CTkProgressBar(strength_container, height=10, fg_color="#f1f5f9", progress_color="#e2e8f0")
        self.strength_bar.pack(fill="x", pady=(8, 0))
        self.strength_bar.set(0)

    def _build_employees_page(self):
        page = ctk.CTkFrame(self.content_card,
                           fg_color=self.THEME["white"],
                           corner_radius=28,
                           border_width=0)
        self._content_frames["employees"] = page

        inner = ctk.CTkFrame(page, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=40, pady=40)

        header = ctk.CTkFrame(inner, fg_color="transparent", height=50)
        header.pack(fill="x", pady=(0, 24))
        header.pack_propagate(False)

        ctk.CTkLabel(header, text="EMPLOYEES & ROLES",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color=self.THEME["text_dark"]
        ).pack(side="left")

        spacer = ctk.CTkFrame(header, fg_color="transparent")
        spacer.pack(side="left", fill="both", expand=True)

        add_icon = self._load_icon("plus-480", size=(18, 18))
        add_btn = ctk.CTkButton(
            header,
            text="  Add Employee",
            text_color=self.THEME["white"],
            image=add_icon,
            fg_color=self.THEME["primary"],
            hover_color=self.THEME["primary_hover"],
            corner_radius=15,
            height=45,
            width=160,
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            command=self._add_employee,
            compound="left"
        )
        add_btn.pack(side="right")

        self.employees_scroll = ctk.CTkScrollableFrame(
            inner, fg_color="transparent",
            scrollbar_button_color=self.THEME["border"],
            scrollbar_button_hover_color=self.THEME["text_gray"]
        )
        self.employees_scroll.pack(fill="both", expand=True)
        self._refresh_employee_list()

    def _add_employee(self):
        logger.info("Opening Add Employee window")
        
        AddEmployeeWindow(
            parent=self.winfo_toplevel(),
            on_submit=self._on_employee_added,
            icons_dir=ICONS_DIR
        )
    
    def _on_employee_added(self, data):
        logger.info(f"New employee added: {data}")
        
        try:
            from database.database import execute
            
            role_name = data.get('role_name')
            role_map = {
                'IT_MANAGER': 2,
                'IT_TECHNICIAN': 3
            }
            role_id = role_map.get(role_name, 3)
            
            execute(
                """
                INSERT INTO users (first_name, last_name, email, phone_number, address, date_of_birth, gender, role_id, password)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data.get('first_name'),
                    data.get('last_name'),
                    data.get('email'),
                    data.get('phone_number'),
                    data.get('address'),
                    data.get('date_of_birth'),
                    data.get('gender'),
                    role_id,
                    data.get('password', 'password123')
                )
            )
            
            self._refresh_employee_list()
            
            show_success_toast(
                parent=self.winfo_toplevel(),
                message=f"Employee '{data.get('first_name')} {data.get('last_name')}' added successfully!",
                duration=3000,
                icons_dir=ICONS_DIR,
                top_padding=30
            )
            
        except Exception as e:
            logger.exception(f"Error adding employee: {e}")
            from app.components.toast_error import show_error_toast
            show_error_toast(
                parent=self.winfo_toplevel(),
                message=f"Error adding employee: {str(e)}",
                duration=3000,
                top_padding=30
            )

    def _delete_employee(self, user_id: int):
        logger.info(f"Attempting to delete employee with ID: {user_id}")
        try:
            success = settings_controller.delete_employee(user_id)
            if success:
                self._refresh_employee_list()
                show_success_toast(
                    parent=self.winfo_toplevel(),
                    message="Employee deleted successfully!",
                    duration=3000,
                    icons_dir=ICONS_DIR,
                    top_padding=30
                )
            else:
                from app.components.toast_error import show_error_toast
                show_error_toast(
                    parent=self.winfo_toplevel(),
                    message="Failed to delete employee.",
                    duration=3000,
                    top_padding=30
                )
        except Exception as e:
            logger.exception(f"Error deleting employee with ID {user_id}: {e}")
            from app.components.toast_error import show_error_toast
            show_error_toast(
                parent=self.winfo_toplevel(),
                message=f"Error deleting employee: {str(e)}",
                duration=3000,
                top_padding=30
            )

    def _refresh_employee_list(self):
        for widget in self.employees_scroll.winfo_children():
            widget.destroy()
        try:
            employees = settings_controller.get_all_employees()
            employees = [emp for emp in employees if emp.get('role_name') != 'CEO']
            if not employees:
                ctk.CTkLabel(self.employees_scroll, text="No employees found.").pack(pady=40)
                return

            self._employee_items = []
            
            for emp in employees:
                item = SettingsView._EmployeeItem(self.employees_scroll, emp, self)
                self._employee_items.append(item)
        except Exception as e:
            logger.exception(f"Error refreshing employee list: {e}")
            ctk.CTkLabel(self.employees_scroll, text="Error loading employees.", text_color=self.THEME["danger"]).pack(pady=20)


    class _EmployeeItem(ctk.CTkFrame):
        """Employee item expandable with details in bullet format"""

        def __init__(self, master, employee, parent_view):
            self.parent_view = parent_view
            self.THEME = parent_view.THEME
            
            super().__init__(
                master,
                fg_color=self.THEME["white"],
                corner_radius=20,
                border_width=2,
                border_color=self.THEME["border"]
            )

            self.employee = employee
            self.is_open = False
            
            self.pack(fill="x", pady=8, padx=0)

            self._build_header()
            self._build_details()

        def _build_header(self):
            self.header_container = ctk.CTkFrame(
                self,
                fg_color="transparent",
                height=70
            )
            self.header_container.pack(fill="x", padx=0, pady=0)
            self.header_container.pack_propagate(False)

            avatar_img = self.parent_view._make_employee_avatar(self.employee, size=40)
            self.avatar_label = ctk.CTkLabel(
                self.header_container, 
                image=avatar_img, 
                text="", 
                fg_color="transparent"
            )
            self.avatar_label.place(x=20, rely=0.5, anchor="w")

            info_container = ctk.CTkFrame(self.header_container, fg_color="transparent")
            info_container.place(x=70, rely=0.5, anchor="w")

            full_name = f"{self.employee['first_name']} {self.employee['last_name']}"
            ctk.CTkLabel(
                info_container,
                text=full_name,
                font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                text_color=self.THEME["text_dark"],
                anchor="w"
            ).pack(anchor="w")

            ctk.CTkLabel(
                info_container,
                text=f"{self.employee.get('role_name', 'N/A')} • {self.employee.get('email', 'N/A')}",
                font=ctk.CTkFont(family="Segoe UI", size=11),
                text_color=self.THEME["text_medium"],
                anchor="w"
            ).pack(anchor="w", pady=(2, 0))

            self.arrow_container = ctk.CTkFrame(
                self.header_container,
                width=45,
                height=45,
                corner_radius=12,
                fg_color="transparent"
            )
            self.arrow_container.place(relx=0.97, rely=0.5, anchor="e")
            self.arrow_container.pack_propagate(False)

            self.chevron_down = self.parent_view._load_icon("chevron-down_blue", size=(20, 20))
            self.chevron_left = self.parent_view._load_icon("chevron-left", size=(20, 20))

            self.arrow_label = ctk.CTkLabel(
                self.arrow_container,
                text="" if self.chevron_left else "›",
                image=self.chevron_left if self.chevron_left else None,
                fg_color="transparent"
            )
            self.arrow_label.place(relx=0.5, rely=0.5, anchor="center")

            self.configure(cursor="hand2")
            self.bind("<Button-1>", self.toggle)
            self.bind("<Enter>", self.on_hover)
            self.bind("<Leave>", self.on_leave)

            for child in [self.header_container, self.avatar_label, info_container, self.arrow_container, self.arrow_label]:
                try:
                    child.configure(cursor="hand2")
                    child.bind("<Button-1>", self.toggle)
                    child.bind("<Enter>", self.on_hover)
                    child.bind("<Leave>", self.on_leave)
                except:
                    pass

        def _build_details(self):
            self.details_outer = ctk.CTkFrame(
                self,
                fg_color="#F8FAFC",
                corner_radius=16,
                border_width=0
            )

            self.details_inner = ctk.CTkFrame(
                self.details_outer,
                fg_color="transparent"
            )
            self.details_inner.pack(fill="both", expand=True, padx=30, pady=20)

            emp = self.employee
            
            info_items = [
                ("NOM", emp.get('last_name', 'N/A')),
                ("PRÉNOM", emp.get('first_name', 'N/A')),
                ("EMAIL", emp.get('email', 'N/A')),
                ("TÉLÉPHONE", emp.get('phone_number', 'N/A')),
                ("ADRESSE", emp.get('address', 'N/A')),
                ("DATE DE NAISSANCE", emp.get('date_of_birth', 'N/A')),
                ("GENRE", emp.get('gender', 'N/A').upper() if emp.get('gender') else 'N/A'),
                ("RÔLE", emp.get('role_name', 'N/A')),
            ]

            for label, value in info_items:
                row = ctk.CTkFrame(self.details_inner, fg_color="transparent")
                row.pack(fill="x", pady=4)
                
                ctk.CTkLabel(
                    row,
                    text=f"• {label} :",
                    font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                    text_color=self.THEME["primary"],
                    anchor="w"
                ).pack(side="left")
                
                ctk.CTkLabel(
                    row,
                    text=str(value),
                    font=ctk.CTkFont(family="Segoe UI", size=13),
                    text_color=self.THEME["text_dark"],
                    anchor="w"
                ).pack(side="left", padx=(8, 0))
            
            # --- New Delete Button ---
            delete_btn_frame = ctk.CTkFrame(self.details_inner, fg_color="transparent")
            delete_btn_frame.pack(fill="x", pady=(10, 0))

            delete_btn = ctk.CTkButton(
                delete_btn_frame,
                text="Remove Employee",
                fg_color="transparent",
                text_color=self.THEME["danger"],
                hover_color=self.THEME["danger_hover"],
                border_color=self.THEME["danger"],
                border_width=2,
                corner_radius=10,
                font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                command=self._confirm_delete
            )
            def on_enter_delete_btn(event):
                delete_btn.configure(fg_color=self.THEME["danger"], text_color=self.THEME["white"])
            def on_leave_delete_btn(event):
                delete_btn.configure(fg_color="transparent", text_color=self.THEME["danger"])
            
            delete_btn.bind("<Enter>", on_enter_delete_btn)
            delete_btn.bind("<Leave>", on_leave_delete_btn)
            
            delete_btn.pack(side="right", padx=(0, 0))

        def on_hover(self, event=None):
            if not self.is_open:
                self.configure(
                    border_color=self.THEME["primary"],
                    fg_color=self.THEME["primary_light"],
                    corner_radius=20
                )

        def on_leave(self, event=None):
            if not self.is_open:
                self.configure(
                    border_color=self.THEME["border"],
                    fg_color=self.THEME["white"],
                    corner_radius=20
                )

        def toggle(self, event=None):
            if self.is_open:
                self.close()
            else:
                self.open()

        def open(self):
            for item in self.parent_view._employee_items:
                if item is not self and item.is_open:
                    item.close()

            self.is_open = True

            self.configure(
                fg_color=self.THEME["white"],
                border_color=self.THEME["white"],
                border_width=2
            )

            self.header_container.configure(fg_color="transparent")

            if self.chevron_down:
                self.arrow_label.configure(
                    image=self.chevron_down,
                    text=""
                )
            else:
                self.arrow_label.configure(
                    text="▼",
                    text_color=self.THEME["primary"]
                )

            self.details_outer.configure(
                border_width=3,
                border_color=self.THEME["primary"]
            )

            self.details_outer.pack(fill="x", padx=20, pady=(0, 20))
            self.update()

        def close(self):
            self.is_open = False

            self.configure(
                border_color=self.THEME["border"],
                fg_color=self.THEME["white"],
                border_width=2
            )

            self.header_container.configure(fg_color="transparent")

            if self.chevron_left:
                self.arrow_label.configure(
                    image=self.chevron_left,
                    text=""
                )
            else:
                self.arrow_label.configure(
                    text="›",
                    text_color=self.THEME["text_gray"]
                )

            self.details_outer.configure(border_width=0)
            self.details_outer.pack_forget()

        def _confirm_delete(self):
            # Pass the user_id to the SettingsView's _delete_employee method
            def on_confirm():
                self.parent_view._delete_employee(self.employee.get('id'))
            
            show_confirm_toast(
                parent=self.parent_view.winfo_toplevel(),
                message=f"Are you sure you want to delete {self.employee.get('first_name')} {self.employee.get('last_name')}?",
                on_confirm=on_confirm
            )

    def _make_employee_avatar(self, employee, size=40):
        """Create avatar image for employee with profile photo or initials."""
        profile_photo = employee.get('profile_photo')
        
        if profile_photo and os.path.exists(profile_photo):
            try:
                img = Image.open(profile_photo).convert("RGBA")
                w, h = img.size
                s = min(w, h)
                left = (w - s) // 2
                top = (h - s) // 2
                img = img.crop((left, top, left + s, top + s))
                img = img.resize((size, size), LANCZOS_FILTER)

                mask_size = size * 4
                mask = Image.new("L", (mask_size, mask_size), 0)
                draw = ImageDraw.Draw(mask)
                draw.ellipse((0, 0, mask_size - 1, mask_size - 1), fill=255)
                mask = mask.resize((size, size), LANCZOS_FILTER)
                
                img.putalpha(mask)

                return ctk.CTkImage(light_image=img, size=(size, size))
            except Exception:
                pass
        
        render_size = size * 4
        img = Image.new("RGBA", (render_size, render_size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse((0, 0, render_size - 1, render_size - 1), fill=(22, 111, 255, 255))

        first_name = employee.get('first_name', '?')[0:1].upper()
        last_name = employee.get('last_name', '?')[0:1].upper()
        initials = f"{first_name}{last_name}"
        
        try:
            from PIL import ImageFont
            font = ImageFont.truetype("arial.ttf", render_size // 3)
        except Exception:
            from PIL import ImageFont
            font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), initials, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text(((render_size - tw) // 2, (render_size - th) // 2), initials,
                  fill=(255, 255, 255, 255), font=font)

        img = img.resize((size, size), LANCZOS_FILTER)

        return ctk.CTkImage(light_image=img, size=(size, size))

    def _create_password_label(self, parent, text):
        return ctk.CTkLabel(parent, text=text, font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"), text_color="#94a3b8")


    def _create_password_entry(self, parent, field_type, label_widget=None):
        # Style AnimatedSearchBar avec animation de bordure
        frame = ctk.CTkFrame(parent, fg_color=self.THEME["input_bg"],
                             corner_radius=16, height=48,
                             border_width=1, border_color=self.THEME["border"])
        frame.pack_propagate(False)

        entry = ctk.CTkEntry(
            frame,
            show="•",
            border_width=0,
            fg_color="transparent",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color=self.THEME["text_dark"]
        )
        entry.pack(side="left", fill="both", expand=True, padx=(20, 5), pady=(10, 10))
        
        # Animation de bordure bleue au focus
        def on_focus_in(e):
            if label_widget:
                label_widget.configure(text_color=self.THEME["primary"])
            frame.configure(border_color=self.THEME["primary"], border_width=2)
        
        def on_focus_out(e):
            if label_widget:
                label_widget.configure(text_color="#94a3b8")
            frame.configure(border_color=self.THEME["border"], border_width=1)
        
        entry.bind("<FocusIn>", on_focus_in)
        entry.bind("<FocusOut>", on_focus_out)
        frame.bind("<Button-1>", lambda e: entry.focus_set())
        
        # Validation on key release
        entry.bind("<KeyRelease>", lambda e: self._validate_password_form())

        # Eye button avec icônes
        try:
            eye_open_path = os.path.join(ICONS_DIR, "eye.png")
            eye_closed_path = os.path.join(ICONS_DIR, "eye-off.png")
            
            eye_open_img = Image.open(eye_open_path).convert("RGBA")
            eye_open_img = eye_open_img.resize((20, 20), LANCZOS_FILTER)
            eye_open_icon = ctk.CTkImage(light_image=eye_open_img, dark_image=eye_open_img, size=(20, 20))
            
            eye_closed_img = Image.open(eye_closed_path).convert("RGBA")
            eye_closed_img = eye_closed_img.resize((20, 20), LANCZOS_FILTER)
            eye_closed_icon = ctk.CTkImage(light_image=eye_closed_img, dark_image=eye_closed_img, size=(20, 20))
        except Exception:
            eye_open_icon = None
            eye_closed_icon = None
        
        eye_btn = ctk.CTkButton(
            frame, 
            text="",
            image=eye_closed_icon,
            width=36, 
            height=36, 
            fg_color="transparent", 
            hover_color="#f8fafc",
            corner_radius=8
        )
        eye_btn.pack(side="right", padx=8, pady=6)
        
        # Configurer la commande avec les icônes
        eye_btn.configure(command=lambda: self._toggle_password_visibility(entry, eye_btn, eye_open_icon, eye_closed_icon))

        return frame, entry

    def _toggle_password_visibility(self, entry, button, eye_open_icon=None, eye_closed_icon=None):
        if entry.cget("show") == "•":
            entry.configure(show="")
            if eye_open_icon:
                button.configure(image=eye_open_icon)
        else:
            entry.configure(show="•")
            if eye_closed_icon:
                button.configure(image=eye_closed_icon)

    def _animate_password_strength(self):
        diff = self.password_target_progress - self.password_current_progress
        
        if abs(diff) < 0.0005:
            self.password_current_progress = self.password_target_progress
            self.strength_bar.set(self.password_current_progress)
            self.password_animation_running = False
            return
        
        self.password_current_progress += diff * 0.05
        self.strength_bar.set(self.password_current_progress)
        
        self.after(10, self._animate_password_strength)

    def _validate_password_form(self):
        new_val = self.new_entry.get()
        conf_val = self.conf_entry.get()
        current_val = self.curr_entry.get()
        length = len(new_val)
        old_target = self.password_target_progress
        
        if length == 0:
            self.strength_text.configure(text="", text_color="#94a3b8")
            self.password_target_progress = 0
            self.strength_bar.configure(progress_color="#e2e8f0")
        elif length < 4:
            self.strength_text.configure(text="UNSAFE", text_color="#ef4444")
            self.password_target_progress = 0.25
            self.strength_bar.configure(progress_color="#ef4444")
        elif length < 8:
            self.strength_text.configure(text="RISKY", text_color="#f97316")
            self.password_target_progress = 0.5
            self.strength_bar.configure(progress_color="#f97316")
        elif length < 11:
            self.strength_text.configure(text="SAFE", text_color="#10b981")
            self.password_target_progress = 0.75
            self.strength_bar.configure(progress_color="#10b981")
        else:
            self.strength_text.configure(text="VERY SAFE", text_color="#059669")
            self.password_target_progress = 1.0
            self.strength_bar.configure(progress_color="#059669")

        if old_target != self.password_target_progress and not self.password_animation_running:
            self.password_animation_running = True
            self._animate_password_strength()

        # Check if new password is same as current
        if new_val == current_val and new_val != "":
            self.password_error_banner.pack(fill="x", padx=40, pady=(0, 20), before=self.password_footer_frame)
            self.password_error_label.pack(pady=12)
        else:
            self.password_error_banner.pack_forget()

        # Check confirmation match
        if conf_val != "" and conf_val != new_val:
            self.conf_entry_frame.configure(border_color="#fca5a5", border_width=2)
        else:
            self.conf_entry_frame.configure(border_color=self.THEME["border"], border_width=1)

        # Vérifier que le current password est correct
        stored_password = self.user_data.get("password", "")
        is_current_valid = current_val == stored_password and current_val != ""
        
        # Enable/disable submit button - même style que SAVE CHANGES
        if length >= 4 and conf_val == new_val and new_val != current_val and is_current_valid:
            self.password_submit_btn.configure(state="normal", fg_color=self.THEME["primary"], text_color=self.THEME["white"], cursor="hand2")
        else:
            self.password_submit_btn.configure(state="disabled", fg_color="#cbd5e1", text_color="#94a3b8", cursor="arrow")

    # ──────────────────────────────────────────────────────────────
    # LOGOUT CONFIRMATION
    # ──────────────────────────────────────────────────────────────
    def _show_logout_confirmation(self):
        """Show confirmation toast for logout"""
        def on_confirm():
            logger.info("User logged out")
            # Import LoginApp here to avoid circular imports
            from app.views.login_view import LoginApp

            # Get the current TechManageApp window
            app = self.winfo_toplevel()

            # Store reference for callback
            login_window = [None]

            # Create the login window with callback
            def on_login_success(user_data):
                logger.info("Login successful after logout")
                # Import TechManageApp here to avoid circular imports
                import sys
                import os
                sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
                from main import TechManageApp

                # Destroy the login window
                if login_window[0]:
                    login_window[0].destroy()
                    login_window[0] = None

                # Create new TechManageApp
                new_app = TechManageApp(logged_in_user=user_data)
                new_app.mainloop()

            # Use after to ensure the toast is destroyed before we destroy the app
            def delayed_logout():
                # Destroy the current TechManageApp window
                app.destroy()

                # Create and show the login window
                login = LoginApp(on_login_success=on_login_success)
                login_window[0] = login
                login.mainloop()

            # Schedule the logout after a small delay to let the toast clean up
            app.after(100, delayed_logout)

        def on_cancel():
            logger.info("Logout cancelled")

        show_confirm_toast(
            parent=self.winfo_toplevel(),
            message="Are you sure you want to log out?",
            on_confirm=on_confirm,
            on_cancel=on_cancel
        )

    # ──────────────────────────────────────────────────────────────
    # PAGE: LOG OUT
    # ──────────────────────────────────────────────────────────────
    def _create_toggle_switch(self, parent, command=None):
        """Créer un switch toggle stylisé."""
        switch_frame = ctk.CTkFrame(parent, width=50, height=26, corner_radius=13,
                                     fg_color=self.THEME["border"], cursor="hand2")
        switch_frame.pack_propagate(False)
        
        dot = ctk.CTkFrame(switch_frame, width=20, height=20, corner_radius=10,
                          fg_color=self.THEME["white"])
        dot.place(relx=0.15, rely=0.5, anchor="w")
        
        state = {"active": False}
        
        def toggle(event=None):
            state["active"] = not state["active"]
            if state["active"]:
                switch_frame.configure(fg_color=self.THEME["primary"])
                dot.place(relx=0.85, rely=0.5, anchor="e")
            else:
                switch_frame.configure(fg_color=self.THEME["border"])
                dot.place(relx=0.15, rely=0.5, anchor="w")
            if command:
                command(state["active"])
        
        switch_frame.bind("<Button-1>", toggle)
        dot.bind("<Button-1>", toggle)
        
        def set_state(active):
            state["active"] = active
            if active:
                switch_frame.configure(fg_color=self.THEME["primary"])
                dot.place(relx=0.85, rely=0.5, anchor="e")
            else:
                switch_frame.configure(fg_color=self.THEME["border"])
                dot.place(relx=0.15, rely=0.5, anchor="w")
        
        switch_frame.set_state = set_state
        switch_frame.get_state = lambda: state["active"]
        
        return switch_frame

    def _create_time_dropdown(self, parent, variable, options, pady_val):
        """Créer un dropdown pour le temps (heures/minutes)."""
        container = ctk.CTkFrame(parent, fg_color="transparent")
        container.pack(side="left")

        dropdown_frame = ctk.CTkFrame(container, width=60, height=40,
                                      corner_radius=12, fg_color=self.THEME["input_bg"],
                                      border_width=1, border_color=self.THEME["border"])
        dropdown_frame.pack()
        dropdown_frame.pack_propagate(False)

        value_label = ctk.CTkLabel(dropdown_frame, textvariable=variable,
                                   font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                                   text_color=self.THEME["text_dark"])
        value_label.place(relx=0.5, rely=0.5, anchor="center")

        def show_popup(event=None):
            popup = ctk.CTkToplevel(self)
            popup.overrideredirect(True)
            popup.configure(fg_color=self.THEME["white"])
            popup.attributes('-topmost', True)

            # Position fixe basée sur les coordonnées absolues
            x = dropdown_frame.winfo_rootx()
            y = dropdown_frame.winfo_rooty() + dropdown_frame.winfo_height() + 5
            popup.geometry(f"70x200+{x}+{y}")

            scroll = ctk.CTkScrollableFrame(popup, fg_color=self.THEME["white"],
                                            width=50, height=180,
                                            scrollbar_button_color=self.THEME["border"],
                                            scrollbar_button_hover_color=self.THEME["text_gray"])
            scroll.pack(fill="both", expand=True, padx=5, pady=5)

            def select(val):
                variable.set(val)
                popup.destroy()

            buttons = []
            for opt in options:
                btn = ctk.CTkButton(scroll, text=opt,
                                    fg_color="transparent" if variable.get() != opt else self.THEME["primary"],
                                    text_color=self.THEME["text_dark"] if variable.get() != opt else self.THEME["white"],
                                    font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                                    hover_color=self.THEME["primary_light"],
                                    height=28,
                                    command=lambda v=opt: select(v))
                btn.pack(fill="x", pady=1)
                buttons.append(btn)

            # Centrer la valeur sélectionnée
            try:
                current_val = variable.get()
                if current_val in options:
                    selected_idx = options.index(current_val)
                    # Calculer la position de scroll pour centrer l'élément
                    total_items = len(options)
                    if total_items > 6:  # Seulement si la liste est assez longue
                        scroll_position = max(0, (selected_idx - 3) / (total_items - 1))
                        scroll._parent_canvas.yview_moveto(scroll_position)
            except:
                pass

            # Fermer au clic en dehors
            def close_popup(event):
                if event.widget != popup and not str(event.widget).startswith(str(popup)):
                    popup.destroy()

            popup.grab_set()
            popup.bind("<FocusOut>", lambda e: popup.destroy())
            self.bind_all("<Button-1>", lambda e: close_popup(e), add="+")
            popup.bind("<Destroy>", lambda e: self.unbind_all("<Button-1>"), add="+")

        dropdown_frame.bind("<Button-1>", show_popup)
        value_label.bind("<Button-1>", show_popup)
    
    def _create_time_dropdown_in_container(self, container, variable, options, is_hour):
        """Créer un dropdown dans un container spécifique (pour pouvoir le recréer)."""
        # Vider le container
        for widget in container.winfo_children():
            widget.destroy()

        dropdown_frame = ctk.CTkFrame(container, width=60, height=40,
                                      corner_radius=12, fg_color=self.THEME["input_bg"],
                                      border_width=1, border_color=self.THEME["border"])
        dropdown_frame.pack()
        dropdown_frame.pack_propagate(False)

        value_label = ctk.CTkLabel(dropdown_frame, textvariable=variable,
                                   font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                                   text_color=self.THEME["text_dark"])
        value_label.place(relx=0.5, rely=0.5, anchor="center")

        def show_popup(event=None):
            popup = ctk.CTkToplevel(self)
            popup.overrideredirect(True)
            popup.configure(fg_color=self.THEME["white"])
            popup.attributes('-topmost', True)

            # Position fixe basée sur les coordonnées absolues
            x = dropdown_frame.winfo_rootx()
            y = dropdown_frame.winfo_rooty() + dropdown_frame.winfo_height() + 5
            popup.geometry(f"70x200+{x}+{y}")

            scroll = ctk.CTkScrollableFrame(popup, fg_color=self.THEME["white"],
                                            width=50, height=180,
                                            scrollbar_button_color=self.THEME["border"],
                                            scrollbar_button_hover_color=self.THEME["text_gray"])
            scroll.pack(fill="both", expand=True, padx=5, pady=5)

            def select(val):
                variable.set(val)
                popup.destroy()

            buttons = []
            for opt in options:
                btn = ctk.CTkButton(scroll, text=opt,
                                    fg_color="transparent" if variable.get() != opt else self.THEME["primary"],
                                    text_color=self.THEME["text_dark"] if variable.get() != opt else self.THEME["white"],
                                    font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                                    hover_color=self.THEME["primary_light"],
                                    height=28,
                                    command=lambda v=opt: select(v))
                btn.pack(fill="x", pady=1)
                buttons.append(btn)

            # Centrer la valeur sélectionnée
            try:
                current_val = variable.get()
                if current_val in options:
                    selected_idx = options.index(current_val)
                    # Calculer la position de scroll pour centrer l'élément
                    total_items = len(options)
                    if total_items > 6:  # Seulement si la liste est assez longue
                        scroll_position = max(0, (selected_idx - 3) / (total_items - 1))
                        scroll._parent_canvas.yview_moveto(scroll_position)
            except:
                pass

            # Fermer au clic en dehors
            def close_popup(event):
                if event.widget != popup and not str(event.widget).startswith(str(popup)):
                    popup.destroy()

            popup.grab_set()
            popup.bind("<FocusOut>", lambda e: popup.destroy())
            self.bind_all("<Button-1>", lambda e: close_popup(e), add="+")
            popup.bind("<Destroy>", lambda e: self.unbind_all("<Button-1>"), add="+")

        dropdown_frame.bind("<Button-1>", show_popup)
        value_label.bind("<Button-1>", show_popup)

    # ──────────────────────────────────────────────────────────────
    # REUSABLE: Radio button
    # ──────────────────────────────────────────────────────────────
    def _radio_button(self, parent, label, value):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(side="left", padx=(0, 28))

        # Outer ring
        ring = ctk.CTkFrame(row, corner_radius=50, width=22, height=22,
                            border_width=2, border_color=self.THEME["text_gray"],
                            fg_color="transparent", cursor="hand2")
        ring.pack(side="left", padx=(0, 8))
        ring.pack_propagate(False)

        # Inner dot (hidden initially)
        dot = ctk.CTkFrame(ring, fg_color=self.THEME["primary"],
                           corner_radius=50, width=10, height=10)

        def update_radio(*_):
            if self.gender_var.get() == value:
                ring.configure(border_color=self.THEME["primary"])
                dot.place(relx=0.5, rely=0.5, anchor="center")
            else:
                ring.configure(border_color=self.THEME["text_gray"])
                dot.place_forget()

        def on_click(e=None):
            self.gender_var.set(value)
            # Refresh all radios
            update_radio()
            # Trigger sibling updates via trace
            self.gender_var.set(value)

        # Label
        text_lbl = ctk.CTkLabel(row, text=label,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=self.THEME["text_dark"], cursor="hand2")
        text_lbl.pack(side="left")

        for w in (ring, dot, text_lbl):
            w.bind("<Button-1>", on_click)

        # Trace gender_var so all radios stay in sync
        self.gender_var.trace_add("write", lambda *_: update_radio())
        update_radio()

    # ──────────────────────────────────────────────────────────────
    # REUSABLE: Form input field
    # ──────────────────────────────────────────────────────────────
    def _form_input(self, grid, row, col, label_text, variable,
                    colspan=1, is_password=False, icon_right=None, extra_top_padding=0):

        wrapper = ctk.CTkFrame(grid, fg_color="transparent")
        cs = colspan
        grid.grid_columnconfigure(col, weight=1)
        wrapper.grid(row=row, column=col, columnspan=cs, sticky="ew",
                     padx=(0 if col == 0 else 10, 0 if (col + cs) >= 2 else 10),
                     pady=(0, 18))

        # Label avec padding supplémentaire en haut si nécessaire
        label = ctk.CTkLabel(wrapper, text=label_text,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=self.THEME["text_gray"], anchor="w"
        )
        label.pack(anchor="w", pady=(extra_top_padding, 6))

        # Input container (the rounded box)
        container = ctk.CTkFrame(wrapper, fg_color=self.THEME["input_bg"],
                                 corner_radius=16, height=48,
                                 border_width=1, border_color=self.THEME["border"])
        container.pack(fill="x")
        container.pack_propagate(False)

        show = "•" if is_password else None

        entry = ctk.CTkEntry(container, textvariable=variable,
            font=ctk.CTkFont(family="Segoe UI", size=13),
            fg_color="transparent",
            text_color=self.THEME["text_dark"],
            border_width=0, show=show)
        entry.pack(side="left", fill="x", expand=True, padx=(16, 8), pady=(6, 6))

        # Optional right icon (e.g. calendar)
        if icon_right:
            ico = self._load_icon(icon_right, size=(18, 18))
            if ico:
                ico_lbl = ctk.CTkLabel(container, image=ico, text="",
                                       fg_color="transparent")
                ico_lbl.pack(side="right", padx=(0, 14))

        # Focus border animation avec label
        def on_focus_in(e, lbl=label, cont=container):
            lbl.configure(text_color=self.THEME["primary"])
            cont.configure(border_color=self.THEME["primary"], border_width=2)

        def on_focus_out(e, lbl=label, cont=container):
            lbl.configure(text_color=self.THEME["text_gray"])
            cont.configure(border_color=self.THEME["border"], border_width=1)

        entry.bind("<FocusIn>",  on_focus_in)
        entry.bind("<FocusOut>", on_focus_out)
        container.bind("<Button-1>", lambda e: entry.focus_set())

 


    # ──────────────────────────────────────────────────────────────
    # CHANGE PROFILE PHOTO
    # ──────────────────────────────────────────────────────────────
    def _change_profile_photo(self):
        """Open file dialog to select a new profile photo."""
        from tkinter import filedialog
        
        file_path = filedialog.askopenfilename(
            title="Select Profile Photo",
            filetypes=[
                ("Image Files", "*.png *.jpg *.jpeg *.gif *.bmp"),
                ("PNG Files", "*.png"),
                ("JPEG Files", "*.jpg *.jpeg"),
                ("All Files", "*.*")
            ]
        )
        
        if file_path:
            self.user_data["profile_photo"] = file_path
            
            try:
                img = Image.open(file_path).convert("RGBA")
                
                # Crop to square center then resize
                w, h = img.size
                s = min(w, h)
                left = (w - s) // 2
                top = (h - s) // 2
                img = img.crop((left, top, left + s, top + s))
                img = img.resize((100, 100), LANCZOS_FILTER)
                
                # Circular mask with anti-aliasing (4x supersampling)
                mask_size = 100 * 4
                mask = Image.new("L", (mask_size, mask_size), 0)
                draw = ImageDraw.Draw(mask)
                draw.ellipse((0, 0, mask_size - 1, mask_size - 1), fill=255)
                mask = mask.resize((100, 100), LANCZOS_FILTER)
                
                img.putalpha(mask)
                
                # Update the avatar image
                self.avatar_img = ctk.CTkImage(light_image=img, size=(100, 100))
                self.avatar_label.configure(image=self.avatar_img)
                
                # Sauvegarder via le contrôleur
                settings_controller.save_user_profile({"profile_photo": file_path})
                
                # Notifier le header via callback
                if self.on_save_callback:
                    self.on_save_callback(self.user_data)
                
                # Success Toast
                show_success_toast(
                    parent=self.winfo_toplevel(),
                    message="Profile photo updated successfully!",
                    duration=3000,
                    icons_dir=ICONS_DIR,
                    top_padding=30
                )
                
                logger.info(f"Profile photo updated: {file_path}")
                print(f"[OK] Photo de profil mise à jour: {file_path}")
                
            except Exception as e:
                logger.error(f"Error loading profile photo: {e}")
                print(f"❌ Erreur lors du chargement de la photo: {e}")

    # ──────────────────────────────────────────────────────────────
    # ACTIONS
    # ──────────────────────────────────────────────────────────────
    def _on_reset(self):
        """Réinitialiser tous les champs aux valeurs originales."""
        print("[DEBUG] Reset démarré...")
        print(f"[DEBUG] original_data: {self.original_data}")
        
        # Reset all variables to original values
        self.first_name_var.set(self.original_data.get("first_name", ""))
        self.last_name_var.set(self.original_data.get("last_name", ""))
        self.email_var.set(self.original_data.get("email", ""))
        self.phone_var.set(self.original_data.get("phone", ""))
        
        # Reset date de naissance (3 variables)
        dob_str = self.original_data.get("date_of_birth", "")
        print(f"[DEBUG] Date de naissance originale: {dob_str}")
        
        if dob_str and len(str(dob_str).split('-')) == 3:
            parts = str(dob_str).split('-')
            year, month, day = parts[0], parts[1], parts[2]
            print(f"[DEBUG] Reset date - Day: {day}, Month: {month}, Year: {year}")
            self.dob_day_var.set(str(day).zfill(2))
            self.dob_month_var.set(str(month).zfill(2))
            self.dob_year_var.set(str(year))
        else:
            print(f"[DEBUG] Date invalide, utilisation des valeurs par défaut")
            self.dob_day_var.set("01")
            self.dob_month_var.set("01")
            self.dob_year_var.set(str(datetime.now().year - 25))
        
        # Reset address
        original_address = self.original_data.get("address", "")
        print(f"[DEBUG] Reset address: '{original_address}'")
        self.address_var.set(original_address)
        
        # Reset gender
        original_gender = self.original_data.get("gender", "male")
        print(f"[DEBUG] Reset gender: '{original_gender}'")
        self.gender_var.set(original_gender)
        
        # Mettre à jour le nom dans le sidebar
        full_name = "{} {}".format(
            self.original_data.get("first_name", "").upper(),
            self.original_data.get("last_name", "").upper()
        )
        self.name_label.configure(text=full_name)
        
        # Forcer le rafraîchissement de l'interface
        self.update_idletasks()
        
        # Notifier le callback si défini
        if self.on_save_callback:
            self.on_save_callback(self.original_data.copy())
        
        logger.info("Personal info reset to original values.")
        print("[OK] Modifications annulées - Tous les champs restaurés aux valeurs originales")
        
        # Afficher les valeurs actuelles après reset
        print(f"[DEBUG] Valeurs après reset:")
        print(f"  - Address: '{self.address_var.get()}'")
        print(f"  - Day: '{self.dob_day_var.get()}'")
        print(f"  - Month: '{self.dob_month_var.get()}'")
        print(f"  - Year: '{self.dob_year_var.get()}'")

    def _on_save(self):
        self.user_data["first_name"]     = self.first_name_var.get()
        self.user_data["last_name"]      = self.last_name_var.get()
        self.user_data["email"]          = self.email_var.get()
        self.user_data["phone"]          = self.phone_var.get()
        
        # Combiner les 3 variables de date (format: YYYY-MM-DD)
        day = self.dob_day_var.get().zfill(2)
        month = self.dob_month_var.get().zfill(2)
        year = self.dob_year_var.get()
        self.user_data["date_of_birth"] = f"{year}-{month}-{day}"
        
        self.user_data["address"]        = self.address_var.get()
        self.user_data["gender"]         = self.gender_var.get()
        
        try:
            success = settings_controller.save_user_profile(self.user_data)
            if success:
                self.original_data = self.user_data.copy()
                
                full_name = "{} {}".format(
                    self.user_data.get("first_name", "").upper(),
                    self.user_data.get("last_name", "").upper()
                )
                self.name_label.configure(text=full_name)
                
                if self.on_save_callback:
                    self.on_save_callback(self.user_data)
                
                # Success Toast
                show_success_toast(
                    parent=self.winfo_toplevel(),
                    message="Personal information updated successfully!",
                    duration=3000,
                    icons_dir=ICONS_DIR,
                    top_padding=30
                )
                
                logger.info("Settings saved successfully: %s", self.user_data)
                print("[OK] Paramètres sauvegardés avec succès!")
            else:
                logger.error("Failed to save settings")
                print("❌ Erreur lors de la sauvegarde")
        except Exception as e:
            logger.exception(f"Error saving settings: {e}")
            print(f"❌ Erreur: {e}")

    def _on_save_password(self):
        current_p = self.curr_entry.get()
        new_p = self.new_entry.get()
        conf_p = self.conf_entry.get()
        
        if not new_p:
            logger.warning("New password is empty.")
            return
        
        if new_p != conf_p:
            logger.warning("Passwords do not match.")
            return
        
        try:
            success, message = settings_controller.update_password(current_p, new_p)
            
            if success:
                self.user_data["password"] = new_p
                # Clear entries
                self.curr_entry.delete(0, 'end')
                self.new_entry.delete(0, 'end')
                self.conf_entry.delete(0, 'end')
                # Reset validation
                self._validate_password_form()
                # Show success message in UI (keep existing one for redundancy)
                self.password_success_label.pack(side="left", padx=10)
                
                # Success Toast
                show_success_toast(
                    parent=self.winfo_toplevel(),
                    message="Password updated successfully!",
                    duration=3000,
                    icons_dir=ICONS_DIR,
                    top_padding=30
                )
                
                logger.info("Password updated successfully.")
                # Hide success message after 3 seconds
                self.after(3000, lambda: self.password_success_label.pack_forget())
            else:
                logger.warning(f"Password update failed: {message}")
                # Show error in banner
                self.password_error_label.configure(text=message)
                self.password_error_banner.pack(fill="x", padx=40, pady=(0, 20), before=self.password_footer_frame)
                self.password_error_label.pack(pady=12)
                self.after(3000, lambda: self.password_error_banner.pack_forget())
                
        except Exception as e:
            logger.exception(f"Error updating password: {e}")

    # ──────────────────────────────────────────────────────────────
    # AVATAR HELPER
    # ──────────────────────────────────────────────────────────────
    def _make_avatar_image(self, size=100):
        """Try to load user's profile photo, then assets/images/user.png, fall back to initials circle."""
        # D'abord essayer de charger la photo de profil personnalisée
        if "profile_photo" in self.user_data and self.user_data["profile_photo"]:
            try:
                img = Image.open(self.user_data["profile_photo"]).convert("RGBA")
                w, h = img.size
                s = min(w, h)
                left = (w - s) // 2
                top  = (h - s) // 2
                img = img.crop((left, top, left + s, top + s))
                img = img.resize((size, size), LANCZOS_FILTER)

                # Circular mask with anti-aliasing
                mask_size = size * 4
                mask = Image.new("L", (mask_size, mask_size), 0)
                draw = ImageDraw.Draw(mask)
                draw.ellipse((0, 0, mask_size - 1, mask_size - 1), fill=255)
                mask = mask.resize((size, size), LANCZOS_FILTER)
                
                img.putalpha(mask)

                return ctk.CTkImage(light_image=img, size=(size, size))
            except Exception:
                pass
        
        # Ensuite essayer de charger l'image par défaut
        img_path = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "..", "..", "assets", "images", "user.png"))
        try:
            img = Image.open(img_path).convert("RGBA")
            w, h = img.size
            s = min(w, h)
            left = (w - s) // 2
            top  = (h - s) // 2
            img = img.crop((left, top, left + s, top + s))
            img = img.resize((size, size), LANCZOS_FILTER)

            # Circular mask with anti-aliasing
            mask_size = size * 4
            mask = Image.new("L", (mask_size, mask_size), 0)
            draw = ImageDraw.Draw(mask)
            draw.ellipse((0, 0, mask_size - 1, mask_size - 1), fill=255)
            mask = mask.resize((size, size), LANCZOS_FILTER)
            
            img.putalpha(mask)

            return ctk.CTkImage(light_image=img, size=(size, size))
        except Exception:
            pass

        # Fallback: initials circle with smooth edges
        render_size = size * 4
        img = Image.new("RGBA", (render_size, render_size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse((0, 0, render_size - 1, render_size - 1), fill=(22, 111, 255, 255))

        initials = "{}{}".format(
            self.user_data.get("first_name", "?")[0:1].upper(),
            self.user_data.get("last_name", "?")[0:1].upper()
        )
        try:
            from PIL import ImageFont
            font = ImageFont.truetype("arial.ttf", render_size // 3)
        except Exception:
            from PIL import ImageFont
            font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), initials, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text(((render_size - tw) // 2, (render_size - th) // 2), initials,
                  fill=(255, 255, 255, 255), font=font)

        img = img.resize((size, size), LANCZOS_FILTER)

        return ctk.CTkImage(light_image=img, size=(size, size))

    # ──────────────────────────────────────────────────────────────
    # DATE PICKER MODERNE (pour Date of Birth)
    # ──────────────────────────────────────────────────────────────
    class CustomDatePicker(ctk.CTkFrame):
        """Date picker personnalisé avec les couleurs de l'application."""
        def __init__(self, parent, selected_date=None, callback=None, theme=None):
            super().__init__(parent, fg_color="transparent")
            
            self.callback = callback
            self.theme = theme or {"primary": "#166FFF", "primary_hover": "#1258CC", "white": "#ffffff", "text_dark": "#1a1a1a", "text_gray": "#9ca3af"}
            
            # Couleurs personnalisées (bleu au lieu de noir)
            self.bg_color = self.theme["white"]
            self.text_color = self.theme["text_dark"]
            self.text_light = self.theme["text_gray"]
            self.selected_bg = self.theme["primary"]  # BLEU au lieu de noir
            self.selected_text = self.theme["white"]
            self.hover_bg = "#f3f4f6"
            
            self.selected_date = selected_date if selected_date else datetime.now()
            self.current_date = self.selected_date
            self.display_month = self.current_date.month
            self.display_year = self.current_date.year
            
            self.calendar_window = None
            
            # Bouton principal affichant la date
            self.date_button = ctk.CTkButton(
                self,
                text=self.selected_date.strftime("%B %d, %Y"),
                height=48,
                fg_color=self.theme["white"],
                text_color=self.theme["text_dark"],
                hover_color="#f3f4f6",
                border_width=1,
                border_color="#e5e7eb",
                corner_radius=16,
                font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                anchor="w",
                command=self.show_calendar
            )
            self.date_button.pack(fill="x")
        
        def get_month_name(self, month_num):
            """Obtenir le nom du mois."""
            months = ["January", "February", "March", "April", "May", "June",
                     "July", "August", "September", "October", "November", "December"]
            return months[month_num - 1]
        
        def prev_year(self):
            """Année précédente."""
            self.display_year -= 1
            self.update_month_year_label()
            self.update_calendar()
        
        def next_year(self):
            """Année suivante."""
            self.display_year += 1
            self.update_month_year_label()
            self.update_calendar()
        
        def update_month_year_label(self):
            """Mettre à jour les boutons mois et année."""
            if hasattr(self, 'month_button') and self.month_button.winfo_exists():
                self.month_button.configure(text=self.get_month_name(self.display_month))
            if hasattr(self, 'year_button') and self.year_button.winfo_exists():
                self.year_button.configure(text=str(self.display_year))
        
        def show_month_selector(self):
            """Afficher un sélecteur de mois."""
            # Fermer les autres dropdowns
            if hasattr(self, 'year_dropdown') and self.year_dropdown.winfo_exists():
                self.year_dropdown.destroy()
            
            # Créer le dropdown
            self.month_dropdown = ctk.CTkFrame(
                self.calendar_window,
                fg_color=self.bg_color,
                corner_radius=10,
                border_width=2,
                border_color="#e5e7eb",
                width=150,
                height=320
            )
            
            # Position
            x = self.month_button.winfo_rootx() - self.calendar_window.winfo_rootx() - 200
            y = self.month_button.winfo_rooty() - self.calendar_window.winfo_rooty() + self.month_button.winfo_height() + 5
            self.month_dropdown.place(x=x, y=y)
            
            # Frame scrollable
            months_frame = ctk.CTkScrollableFrame(
                self.month_dropdown,
                fg_color=self.bg_color,
                width=130,
                height=300
            )
            months_frame.pack(fill="both", expand=True, padx=5, pady=5)
            
            def select_month(month_num):
                self.display_month = month_num
                self.update_month_year_label()
                self.update_calendar()
                self.month_dropdown.destroy()
            
            # Créer les boutons de mois
            for month_num in range(1, 13):
                month_name = self.get_month_name(month_num)
                is_current = month_num == self.display_month
                
                if is_current:
                    fg_color = self.selected_bg
                    text_color = self.selected_text
                    hover_color = self.theme["primary_hover"]
                else:
                    fg_color = self.bg_color
                    text_color = self.text_color
                    hover_color = self.hover_bg
                
                month_btn = ctk.CTkButton(
                    months_frame,
                    text=month_name,
                    height=40,
                    fg_color=fg_color,
                    text_color=text_color,
                    hover_color=hover_color,
                    corner_radius=6,
                    font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold" if is_current else "normal"),
                    command=lambda m=month_num: select_month(m)
                )
                month_btn.pack(fill="x", pady=2, padx=3)
            
            # Scroll vers le mois sélectionné
            self.after(100, lambda: months_frame._parent_canvas.yview_moveto((self.display_month - 1) / 12))
        
        def show_year_selector(self):
            """Afficher un sélecteur d'années."""
            # Fermer les autres dropdowns
            if hasattr(self, 'month_dropdown') and self.month_dropdown.winfo_exists():
                self.month_dropdown.destroy()
            
            # Créer le dropdown
            self.year_dropdown = ctk.CTkFrame(
                self.calendar_window,
                fg_color=self.bg_color,
                corner_radius=10,
                border_width=2,
                border_color="#e5e7eb",
                width=120,
                height=320
            )
            
            # Position
            x = self.year_button.winfo_rootx() - self.calendar_window.winfo_rootx() - 20
            y = self.year_button.winfo_rooty() - self.calendar_window.winfo_rooty() + self.year_button.winfo_height() + 5
            self.year_dropdown.place(x=x, y=y)
            
            # Frame scrollable
            years_frame = ctk.CTkScrollableFrame(
                self.year_dropdown,
                fg_color=self.bg_color,
                width=100,
                height=300
            )
            years_frame.pack(fill="both", expand=True, padx=5, pady=5)
            
            def select_year(year):
                self.display_year = year
                self.update_month_year_label()
                self.update_calendar()
                self.year_dropdown.destroy()
            
            # Générer les années (1900 à 2100)
            current_year = datetime.now().year
            start_year = 1900
            end_year = 2100
            
            # Créer les boutons d'année
            for year in range(end_year, start_year - 1, -1):
                is_current = year == self.display_year
                is_today = year == current_year
                
                if is_current:
                    fg_color = self.selected_bg
                    text_color = self.selected_text
                    hover_color = self.theme["primary_hover"]
                elif is_today:
                    fg_color = "#3b82f6"
                    text_color = "#ffffff"
                    hover_color = "#2563eb"
                else:
                    fg_color = self.bg_color
                    text_color = self.text_color
                    hover_color = self.hover_bg
                
                year_btn = ctk.CTkButton(
                    years_frame,
                    text=str(year),
                    height=40,
                    fg_color=fg_color,
                    text_color=text_color,
                    hover_color=hover_color,
                    corner_radius=6,
                    font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold" if is_current else "normal"),
                    command=lambda y=year: select_year(y)
                )
                year_btn.pack(fill="x", pady=2, padx=3)
            
            # Scroll vers l'année sélectionnée
            self.after(100, lambda: years_frame._parent_canvas.yview_moveto((end_year - self.display_year) / (end_year - start_year)))
        
        def show_calendar(self):
            """Afficher le calendrier moderne."""
            if self.calendar_window is None or not self.calendar_window.winfo_exists():
                self.calendar_window = ctk.CTkToplevel(self)
                self.calendar_window.title("")
                self.calendar_window.geometry("400x520")
                self.calendar_window.resizable(False, False)
                
                # Centrer la fenêtre
                self.calendar_window.update_idletasks()
                x = self.winfo_rootx() + (self.winfo_width() // 2) - (400 // 2)
                y = self.winfo_rooty() + self.winfo_height() + 5
                self.calendar_window.geometry(f"+{x}+{y}")
                
                # Frame principal
                calendar_frame = ctk.CTkFrame(self.calendar_window, fg_color=self.bg_color, corner_radius=15)
                calendar_frame.pack(fill="both", expand=True, padx=10, pady=10)
                
                # Header avec navigation avancée
                header_frame = ctk.CTkFrame(calendar_frame, fg_color=self.bg_color)
                header_frame.pack(fill="x", padx=15, pady=(15, 10))
                
                # Navigation années (<<)
                btn_prev_year = ctk.CTkButton(
                    header_frame, text="<<", width=35, height=35,
                    fg_color=self.bg_color, text_color=self.text_color,
                    hover_color=self.hover_bg, corner_radius=8,
                    font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                    command=self.prev_year
                )
                btn_prev_year.pack(side="left", padx=(0, 2))
                
                # Navigation mois (<)
                btn_prev_month = ctk.CTkButton(
                    header_frame, text="<", width=35, height=35,
                    fg_color=self.bg_color, text_color=self.text_color,
                    hover_color=self.hover_bg, corner_radius=8,
                    font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                    command=self.prev_month
                )
                btn_prev_month.pack(side="left", padx=2)
                
                # Frame pour mois et année (cliquables)
                month_year_frame = ctk.CTkFrame(header_frame, fg_color=self.bg_color)
                month_year_frame.pack(side="left", expand=True, padx=10)
                
                # Bouton mois (cliquable)
                self.month_button = ctk.CTkButton(
                    month_year_frame,
                    text=self.get_month_name(self.display_month),
                    font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
                    text_color=self.text_color,
                    fg_color=self.bg_color,
                    hover_color=self.hover_bg,
                    width=100,
                    height=32,
                    corner_radius=6,
                    command=self.show_month_selector
                )
                self.month_button.pack(side="left", padx=2)
                
                # Bouton année (cliquable)
                self.year_button = ctk.CTkButton(
                    month_year_frame,
                    text=str(self.display_year),
                    font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
                    text_color=self.text_color,
                    fg_color=self.bg_color,
                    hover_color=self.hover_bg,
                    width=70,
                    height=32,
                    corner_radius=6,
                    command=self.show_year_selector
                )
                self.year_button.pack(side="left", padx=2)
                
                # Navigation mois (>)
                btn_next_month = ctk.CTkButton(
                    header_frame, text=">", width=35, height=35,
                    fg_color=self.bg_color, text_color=self.text_color,
                    hover_color=self.hover_bg, corner_radius=8,
                    font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                    command=self.next_month
                )
                btn_next_month.pack(side="right", padx=2)
                
                # Navigation années (>>)
                btn_next_year = ctk.CTkButton(
                    header_frame, text=">>", width=35, height=35,
                    fg_color=self.bg_color, text_color=self.text_color,
                    hover_color=self.hover_bg, corner_radius=8,
                    font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                    command=self.next_year
                )
                btn_next_year.pack(side="right", padx=(2, 0))
                
                # Jours de la semaine
                days_frame = ctk.CTkFrame(calendar_frame, fg_color=self.bg_color)
                days_frame.pack(fill="x", padx=15, pady=5)
                
                weekdays = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
                for i, day in enumerate(weekdays):
                    day_label = ctk.CTkLabel(
                        days_frame, text=day, height=30,
                        font=ctk.CTkFont(family="Segoe UI", size=12),
                        text_color=self.text_light
                    )
                    day_label.grid(row=0, column=i, padx=2, sticky="ew")
                    days_frame.grid_columnconfigure(i, weight=1)
                
                # Frame pour les dates
                self.dates_frame = ctk.CTkFrame(calendar_frame, fg_color=self.bg_color)
                self.dates_frame.pack(fill="both", expand=True, padx=15, pady=10)
                
                self.update_calendar()
                
                # Boutons Cancel et Apply
                buttons_frame = ctk.CTkFrame(calendar_frame, fg_color=self.bg_color)
                buttons_frame.pack(fill="x", padx=15, pady=(5, 15))
                
                cancel_btn = ctk.CTkButton(
                    buttons_frame, text="Cancel", height=40,
                    fg_color=self.bg_color, text_color=self.text_color,
                    hover_color=self.hover_bg, border_width=0, corner_radius=8,
                    font=ctk.CTkFont(family="Segoe UI", size=14),
                    command=self.cancel
                )
                cancel_btn.pack(side="left", expand=True, padx=5)
                
                apply_btn = ctk.CTkButton(
                    buttons_frame, text="Apply", height=40,
                    fg_color=self.selected_bg, text_color=self.selected_text,
                    hover_color=self.theme["primary_hover"], corner_radius=8,
                    font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                    command=self.apply
                )
                apply_btn.pack(side="right", expand=True, padx=5)
                
                # Rendre modale
                self.calendar_window.transient(self.master)
                self.calendar_window.grab_set()
            else:
                self.calendar_window.focus()
        
        def update_calendar(self):
            """Mettre à jour l'affichage du calendrier."""
            for widget in self.dates_frame.winfo_children():
                widget.destroy()
            
            import calendar
            cal = calendar.monthcalendar(self.display_year, self.display_month)
            
            for week_num, week in enumerate(cal):
                self.dates_frame.grid_rowconfigure(week_num, weight=1)
                for day_num in range(7):
                    self.dates_frame.grid_columnconfigure(day_num, weight=1)
                    day = week[day_num]
                    
                    if day == 0:
                        # Jour vide
                        btn = ctk.CTkButton(
                            self.dates_frame, text="", height=40,
                            fg_color=self.bg_color, state="disabled",
                            corner_radius=8
                        )
                    else:
                        # Jour du mois
                        is_selected = (
                            day == self.selected_date.day and
                            self.display_month == self.selected_date.month and
                            self.display_year == self.selected_date.year
                        )
                        
                        btn = ctk.CTkButton(
                            self.dates_frame, text=str(day), height=40,
                            fg_color=self.selected_bg if is_selected else self.bg_color,
                            text_color=self.selected_text if is_selected else self.text_color,
                            hover_color=self.selected_bg if is_selected else self.hover_bg,
                            corner_radius=8,
                            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold" if is_selected else "normal"),
                            command=lambda d=day: self.select_date(d)
                        )
                    btn.grid(row=week_num, column=day_num, padx=2, pady=2, sticky="nsew")
        
        def select_date(self, day):
            """Sélectionner un jour."""
            self.selected_date = datetime(self.display_year, self.display_month, day)
            self.update_calendar()
        
        def prev_month(self):
            """Mois précédent."""
            if self.display_month == 1:
                self.display_month = 12
                self.display_year -= 1
            else:
                self.display_month -= 1
            self.update_month_year_label()
            self.update_calendar()
        
        def next_month(self):
            """Mois suivant."""
            if self.display_month == 12:
                self.display_month = 1
                self.display_year += 1
            else:
                self.display_month += 1
            self.update_month_year_label()
            self.update_calendar()
        
        def cancel(self):
            """Annuler la sélection."""
            if self.calendar_window:
                self.calendar_window.grab_release()
                self.calendar_window.destroy()
                self.calendar_window = None
        
        def apply(self):
            """Appliquer la date sélectionnée."""
            self.date_button.configure(text=self.selected_date.strftime("%B %d, %Y"))
            if self.callback:
                self.callback(self.selected_date)
            if self.calendar_window:
                self.calendar_window.grab_release()
                self.calendar_window.destroy()
                self.calendar_window = None
        
        def get_date(self):
            """Retourner la date sélectionnée."""
            return self.selected_date
    
    def _create_date_picker_grid(self, grid, row, col, label_text):
        """Sélecteur de date : Champs proportionnels (1:2:1) et Listes à tailles fixes."""
        wrapper = ctk.CTkFrame(grid, fg_color="transparent")
        grid.grid_columnconfigure(col, weight=1, uniform="col")
        wrapper.grid(row=row, column=col, sticky="ew",
                     padx=(10, 0), pady=(0, 18))
        
        # Label avec icône
        label_frame = ctk.CTkFrame(wrapper, fg_color="transparent")
        label_frame.pack(anchor="w", pady=(0, 8))
        
        try:
            calendar_icon_path = os.path.join(ICONS_DIR, "calendar.png")
            calendar_icon = ctk.CTkImage(
                light_image=Image.open(calendar_icon_path),
                dark_image=Image.open(calendar_icon_path),
                size=(14, 14)
            )
            icon_label = ctk.CTkLabel(label_frame, image=calendar_icon, text="")
            icon_label.pack(side="left", padx=(0, 5))
        except: pass
        
        ctk.CTkLabel(label_frame, text=label_text, font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                     text_color=self.THEME["text_gray"], anchor="w").pack(side="left")
        
        # Grille pour les champs (Ajusté : Month très grand, Day/Year au minimum)
        date_frame = ctk.CTkFrame(wrapper, fg_color="transparent")
        date_frame.pack(fill="x")
        date_frame.grid_columnconfigure(0, weight=4)  # DAY (Minimum)
        date_frame.grid_columnconfigure(1, weight=32) # MONTH (Maximum)
        date_frame.grid_columnconfigure(2, weight=4)  # YEAR (Minimum)
        
        # Formatter pour le mois
        months_options = [f"{i:02d} - {name}" for i, name in enumerate(
            ["January", "February", "March", "April", "May", "June",
             "July", "August", "September", "October", "November", "December"], 1)]
        months_values = [f"{i:02d}" for i in range(1, 13)]
        
        def month_display_formatter(val):
            if val and val in months_values:
                idx = months_values.index(val)
                return months_options[idx]
            return val
        
        # Day : Liste équitable de 124px
        self._create_mini_dropdown_grid(date_frame, 0, "DAY", self.dob_day_var, [str(i).zfill(2) for i in range(1, 32)], popup_width=124, padx=(0, 8))
        
        # Month : Liste équitable de 124px
        self._create_mini_dropdown_grid(date_frame, 1, "MONTH", self.dob_month_var, months_options, popup_width=124, padx=(0, 8), option_values=months_values, display_formatter=month_display_formatter)
        
        # Year : Liste équitable de 124px
        current_year = datetime.now().year
        year_options = [str(year) for year in range(current_year, 1899, -1)]
        self._create_mini_dropdown_grid(date_frame, 2, "YEAR", self.dob_year_var, year_options, popup_width=124)

    def _create_mini_dropdown_grid(self, parent, col, label_text, variable, options, popup_width, padx=(0, 0), option_values=None, display_formatter=None):
        """Champ extensible mais menu déroulant à taille fixe."""
        container = ctk.CTkFrame(parent, fg_color="transparent")
        container.grid(row=0, column=col, sticky="ew", padx=padx)
        
        label = ctk.CTkLabel(container, text=label_text, font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color=self.THEME["text_gray"])
        label.pack(pady=(0, 3))
        
        dropdown_frame = ctk.CTkFrame(container, height=48, corner_radius=16, fg_color=self.THEME["input_bg"], border_width=1, border_color=self.THEME["border"])
        dropdown_frame.pack(fill="x", expand=True)
        dropdown_frame.pack_propagate(False)

        value_label = ctk.CTkLabel(dropdown_frame, text="", font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), text_color=self.THEME["text_dark"])
        value_label.place(relx=0.5, rely=0.5, anchor="center")
        
        def update_display(*args):
            current_val = variable.get()
            value_label.configure(text=display_formatter(current_val) if display_formatter else current_val)
        
        variable.trace_add("write", update_display)
        update_display()
        
        def toggle_dropdown(event=None):
            dropdown_frame.configure(border_color=self.THEME["primary"], border_width=2)
            label.configure(text_color=self.THEME["primary"])
            
            popup = ctk.CTkToplevel(self)
            popup.wm_overrideredirect(True)
            popup.configure(fg_color=self.THEME["white"])
            
            dropdown_frame.update_idletasks()
            x = dropdown_frame.winfo_rootx()
            y = dropdown_frame.winfo_rooty() + dropdown_frame.winfo_height() + 5
            
            popup_container = ctk.CTkFrame(popup, fg_color=self.THEME["white"], corner_radius=16, border_width=1, border_color="#E5E7EB")
            popup_container.pack(padx=2, pady=2)
            
            # Utilisation de la taille fixe passée en paramètre
            scroll_frame = ctk.CTkScrollableFrame(
                popup_container, fg_color=self.THEME["white"],
                width=popup_width, 
                height=min(200, len(options) * 35),
                scrollbar_button_color="#CBD5E1", scrollbar_button_hover_color="#9CA3AF"
            )
            scroll_frame.pack(padx=(4, 2), pady=4)
            
            def select_option(option, idx=None):
                variable.set(option_values[idx] if idx is not None and option_values else option)
                popup.destroy()
                dropdown_frame.configure(border_color=self.THEME["border"], border_width=1)
                label.configure(text_color=self.THEME["text_gray"])
            
            for i, opt in enumerate(options):
                is_sel = (variable.get() == (option_values[i] if option_values else opt))
                ctk.CTkButton(
                    scroll_frame, text=opt, font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                    fg_color=self.THEME["primary"] if is_sel else "transparent",
                    text_color=self.THEME["white"] if is_sel else self.THEME["text_dark"],
                    hover_color=self.THEME["primary_hover"] if is_sel else "#F3F4F6",
                    corner_radius=8, height=32, command=lambda o=opt, idx=i: select_option(o, idx)
                ).pack(fill="x", pady=2, padx=4)
            
            popup.update_idletasks()
            popup.geometry(f"{popup_width + 20}x{min(200, len(options) * 35) + 20}+{x}+{y}")
            popup.bind("<FocusOut>", lambda e: (popup.after(100, popup.destroy), dropdown_frame.configure(border_color=self.THEME["border"], border_width=1), label.configure(text_color=self.THEME["text_gray"])))
            self.after(100, popup.focus_set)
        
        dropdown_frame.bind("<Button-1>", toggle_dropdown)
        value_label.bind("<Button-1>", toggle_dropdown)

    def _on_date_selected(self, date):
        """Callback quand une date est sélectionnée."""
        if date:
            self.dob_day_var.set(str(date.day).zfill(2))
            self.dob_month_var.set(str(date.month).zfill(2))
            self.dob_year_var.set(str(date.year))

    # ──────────────────────────────────────────────────────────────
    # ICON LOADER (cached)
    # ──────────────────────────────────────────────────────────────
    def _load_icon(self, base_name, size=(32, 32)):
        if not base_name:
            return None
        key = "{}_{}_{}".format(base_name, size[0], size[1])
        if key in self._icon_cache:
            return self._icon_cache[key]

        candidates = [
            "{}.png".format(base_name),
            "{}_icon.png".format(base_name),
        ]
        for name in candidates:
            p = os.path.join(ICONS_DIR, name)
            if os.path.exists(p):
                try:
                    img = Image.open(p).convert("RGBA")
                    img = img.resize(size, LANCZOS_FILTER)
                    ctk_img = ctk.CTkImage(light_image=img, size=size)
                    self._icon_cache[key] = ctk_img
                    return ctk_img
                except Exception:
                    logger.exception("Error loading icon %s", p)
                    break

        self._icon_cache[key] = None
        return None

    # ── Public helpers ────────────────────────────────────────────
    def get_user_data(self):
        return self.user_data.copy()

    def update_user_data(self, new_data):
        self.user_data.update(new_data)
        self.original_data = self.user_data.copy()
        self.first_name_var.set(self.user_data.get("first_name", ""))
        self.last_name_var.set(self.user_data.get("last_name", ""))
        self.email_var.set(self.user_data.get("email", ""))
        self.phone_var.set(self.user_data.get("phone", ""))
        
        # Mettre à jour les 3 variables de date
        dob_str = self.user_data.get("date_of_birth", "")
        if dob_str and len(dob_str.split('-')) == 3:
            year, month, day = dob_str.split('-')
            self.dob_day_var.set(day)
            self.dob_month_var.set(month)
            self.dob_year_var.set(year)
        else:
            self.dob_day_var.set("01")
            self.dob_month_var.set("01")
            self.dob_year_var.set(str(datetime.now().year - 25))
        
        self.address_var.set(self.user_data.get("address", ""))
        self.gender_var.set(self.user_data.get("gender", "male"))


# ── STANDALONE TEST ───────────────────────────────────────────────
if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.title("Settings")
    root.geometry("1100x700")
    root.configure(bg="#F0F4F9")
    root.minsize(900, 600)

    user_data = {
        "first_name": "Mohamed",
        "last_name": "Said",
        "title": "PDG / CEO",
        "email": "mohamed.said@techmanage.com",
        "phone": "+213698123456",
        "date_of_birth": "1990-01-01",
        "address": "Hong Bang",
        "location": "Hai Phong, Vietnam",
        "postal_code": "180000",
        "gender": "male",
        "password": "password123",
    }

    def on_save(data):
        print("Saved →", data)
    
    def on_timer_format_change(is_24h):
        print(f"Timer format changed to: {'24H' if is_24h else 'AM/PM'}")

    SettingsView(root, user_data=user_data, on_save_callback=on_save, on_timer_format_change=on_timer_format_change)
    root.mainloop()