import customtkinter as ctk
import os
import sys
import logging
from pathlib import Path
from PIL import Image, ImageTk

logger = logging.getLogger(__name__)

# --- TECHPRO PIXEL-PERFECT DESIGN SYSTEM ---
COLORS = {
    "bg_main": "#f0f4f9",
    "white": "#ffffff",
    "primary": "#4081f5",        # TechPro Blue
    "primary_light": "#ebf2fe",  # Soft blue for selection/badges
    "text_dark": "#1e293b",      # Slate 900
    "text_muted": "#94a3b8",     # Slate 500
    "border": "#f1f5f9",
    "red": "#ef4444",            # Delete/Cancel
    "red_light": "#fef2f2",
    "green": "#10b981",          # Active status
    "orange": "#f59e0b",          # Maintenance status
    "available": "#3b82f6",      # Available status
    "dock_bg": "#0f172a"          # Dark dock background
}

STATUS_OPTIONS = [
    ("ACTIVE", COLORS["green"]),
    ("AVAILABLE", COLORS["available"]),
    ("MAINTENANCE", COLORS["orange"]),
    ("LENT OUT", COLORS["red"])
]

LOCATIONS = [
    'CEO BUREAU', 'ADMINISTRATION', 'RECEPTION', 'OFFICE 101', 
    'MAIN STORAGE', 'SECTION A', 'SECTION B', 'SECTION C', 
    'SECRET ROOM', 'UNDERGROUND'
]

# --- COMPONENTS ---

class BaseModal(ctk.CTkToplevel):
    """Refined smaller shared base for white-themed high-fidelity modals."""
    def __init__(self, master, title_text, icon_text, width=420, height=580, icon_color=COLORS["primary"]):
        super().__init__(master)
        self.title("")
        self.geometry(f"{width}x{height}")
        self.configure(fg_color=COLORS["white"])
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.transient(master)
        self.grab_set()
        
        # Center Modal
        self.update_idletasks()
        try:
            master_x = master.winfo_x()
            master_y = master.winfo_y()
            master_w = master.winfo_width()
            master_h = master.winfo_height()
            
            x = master_x + (master_w // 2) - (width // 2)
            y = master_y + (master_h // 2) - (height // 2)
            self.geometry(f"+{x}+{max(y, 20)}")
        except:
            self.geometry(f"+{500}+{300}")

        # Header Section (More compact)
        self.header = ctk.CTkFrame(self, fg_color="transparent")
        self.header.pack(fill="x", pady=(35, 15))

        # Icon Squircle (Smaller)
        self.icon_box = ctk.CTkFrame(self.header, width=70, height=70, corner_radius=24, fg_color=COLORS["primary_light"])
        self.icon_box.pack(pady=(0, 15))
        self.icon_box.pack_propagate(False)
        ctk.CTkLabel(self.icon_box, text=icon_text, font=("Segoe UI", 28), text_color=icon_color).place(relx=0.5, rely=0.5, anchor="center")

        # Titles (Smaller fonts)
        ctk.CTkLabel(self.header, text=title_text.upper(), font=("Segoe UI", 24, "bold"), text_color=COLORS["text_dark"]).pack()
        self.subtitle = ctk.CTkLabel(self.header, text="UPDATING SELECTION", font=("Segoe UI", 10, "bold"), text_color=COLORS["text_muted"])
        self.subtitle.pack(pady=(2, 5))

        # Content Area
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True, padx=35)

    def create_label(self, parent, text):
        return ctk.CTkLabel(parent, text=text, font=("Segoe UI", 9, "bold"), text_color=COLORS["text_muted"])

class UpdateStatusModal(BaseModal):
    def __init__(self, master, count, callback, current_status=None, user_role=None):
        super().__init__(master, "Update Status", "⚡", height=640)
        self.callback = callback
        self.current_status = current_status
        self.selected_status = current_status
        self.user_role = user_role
        self.subtitle.configure(text=f"UPDATING {count} ASSETS")
        
        self.status_cards = {}
        self.check_labels = {}
        
        # Filter status options for IT_TECHNICIAN
        options = STATUS_OPTIONS
        if self.user_role == "IT_TECHNICIAN":
            options = [opt for opt in STATUS_OPTIONS if opt[0] != "MAINTENANCE"]

        # Create status option cards
        for status, color in options:
            is_current = status == current_status
            
            # Container frame for each option
            card_frame = ctk.CTkFrame(
                self.container,
                height=65,
                corner_radius=18,
                fg_color=COLORS["primary_light"] if is_current else COLORS["bg_main"],
                border_width=2 if is_current else 0,
                border_color=COLORS["primary"] if is_current else COLORS["bg_main"],
                cursor="hand2"
            )
            card_frame.pack(fill="x", pady=5)
            card_frame.pack_propagate(False)
            
            self.status_cards[status] = card_frame
            
            # Make the entire card clickable
            card_frame.bind("<Button-1>", lambda e, s=status: self.on_select(s))
            card_frame.bind("<Enter>", lambda e, f=card_frame: f.configure(fg_color="#e2e8f0") if f not in [self.status_cards.get(self.selected_status)] else None)
            card_frame.bind("<Leave>", lambda e, s=status, f=card_frame: f.configure(fg_color=COLORS["primary_light"] if s == self.selected_status else COLORS["bg_main"]))
            
            # Indicator Dot
            dot = ctk.CTkFrame(
                card_frame,
                width=10,
                height=10,
                corner_radius=5,
                fg_color=color
            )
            dot.place(relx=0.08, rely=0.5, anchor="center")
            dot.bind("<Button-1>", lambda e, s=status: self.on_select(s))
            
            # Status label
            lbl = ctk.CTkLabel(
                card_frame,
                text=status,
                font=("Segoe UI", 12, "bold"),
                text_color=COLORS["text_dark"]
            )
            lbl.place(relx=0.18, rely=0.5, anchor="w")
            lbl.bind("<Button-1>", lambda e, s=status: self.on_select(s))
            
            # Check icon
            check_lbl = ctk.CTkLabel(
                card_frame,
                text="✓" if is_current else "",
                font=("Segoe UI", 14, "bold"),
                text_color=COLORS["primary"]
            )
            check_lbl.place(relx=0.92, rely=0.5, anchor="center")
            check_lbl.bind("<Button-1>", lambda e, s=status: self.on_select(s))
            self.check_labels[status] = check_lbl

        # Bottom Actions
        self.footer = ctk.CTkFrame(self, fg_color="transparent")
        self.footer.pack(side="bottom", fill="x", padx=35, pady=30)
        
        ctk.CTkButton(
            self.footer,
            text="CANCEL",
            font=("Segoe UI", 13, "bold"),
            fg_color="#FEF2F2",
            text_color="#DD2A2A",
            border_width=1.5,
            border_color="#FEE5E5",
            height=54,
            corner_radius=16,
            hover_color="#FEE5E5",
            cursor="hand2",
            command=self.destroy
        ).pack(side="left", expand=True, padx=(0, 8), fill="x")
        
        ctk.CTkButton(
            self.footer,
            text="SAVE CHANGES",
            font=("Segoe UI", 13, "bold"),
            fg_color=COLORS["primary"],
            text_color="white",
            height=54,
            corner_radius=16,
            hover_color="#5899FA",
            cursor="hand2",
            command=self.on_confirm
        ).pack(side="left", expand=True, padx=(8, 0), fill="x")

    def on_select(self, status):
        self.selected_status = status
        
        # Update all cards
        for stat, card in self.status_cards.items():
            if stat == status:
                card.configure(
                    fg_color=COLORS["primary_light"],
                    border_width=2,
                    border_color=COLORS["primary"]
                )
                self.check_labels[stat].configure(text="✓")
            else:
                card.configure(
                    fg_color=COLORS["bg_main"],
                    border_width=0,
                    border_color=COLORS["bg_main"]
                )
                self.check_labels[stat].configure(text="")

    def on_confirm(self):
        if self.selected_status:
            self.callback(self.selected_status)
        self.destroy()

class ChangeLocationModal(BaseModal):
    def __init__(self, master, count, callback):
        super().__init__(master, "Change Location", "📍", height=680)
        self.callback = callback
        self.subtitle.configure(text=f"RELOCATING {count} ASSETS")
        
        # Local import to avoid circular dependency
        try:
            from controllers import map_controller
        except ImportError:
            # Try to add path manually if it fails
            _project_root = Path(__file__).resolve().parents[3]
            if str(_project_root) not in sys.path:
                sys.path.insert(0, str(_project_root))
            from controllers import map_controller
        
        # Charger les données de capacité des chambres
        try:
            facility_data = map_controller.get_facility_data()
            self.rooms_info = {room["name"]: {"full": room["max_capacity"] is not None and room["total_items"] >= room["max_capacity"], "current": room["total_items"], "max": room["max_capacity"]} for room in facility_data}
            
            # Combiner LOCATIONS statiques et rooms de la DB pour être sûr d'avoir tout
            db_locations = [room["name"] for room in facility_data]
            locations_to_use = list(dict.fromkeys(LOCATIONS + db_locations)) # Unique items preserve order
        except Exception as e:
            logger.error(f"Failed to load facility data for ChangeLocationModal: {e}")
            self.rooms_info = {}
            locations_to_use = LOCATIONS

        self.create_label(self.container, "DESTINATION").pack(anchor="w", pady=(0, 5))
        
        # Scrollable list
        self.scroll = ctk.CTkScrollableFrame(self.container, fg_color="transparent", height=320)
        self.scroll.pack(fill="both", expand=True)
        
        self.selected_loc = None
        for loc in locations_to_use:
            if not self.rooms_info.get(loc, {}).get("full"):
                self.selected_loc = loc
                break
        if not self.selected_loc:
            self.selected_loc = locations_to_use[0]

        self.btns = []
        
        for loc in locations_to_use:
            info = self.rooms_info.get(loc, {})
            is_full = info.get("full", False)
            is_selected = (loc == self.selected_loc)
            
            # Style du bouton selon l'état
            if is_full:
                fg = COLORS["white"]
                text_col = COLORS["red"]
                border_w = 0
                cursor = "not-allowed"
                disp_text = f"{loc} (FULL)"
            else:
                fg = COLORS["white"] if is_selected else COLORS["bg_main"]
                text_col = COLORS["text_dark"]
                border_w = 2 if is_selected else 0
                cursor = "hand2"
                disp_text = loc

            btn = ctk.CTkButton(
                self.scroll, 
                text=disp_text, 
                font=("Segoe UI", 11, "bold"), 
                height=55, 
                corner_radius=15, 
                fg_color=fg,
                border_width=border_w,
                border_color=COLORS["primary"] if border_w > 0 else COLORS["bg_main"],
                text_color=text_col, 
                anchor="w", 
                hover_color="#fecaca" if is_full else "#e2e8f0",
                cursor=cursor if not is_full else "no",
                command=lambda l=loc: self.update_selection(l) if not self.rooms_info.get(l, {}).get("full") else None
            )
            btn.pack(fill="x", pady=3)
            self.btns.append((loc, btn))

        # Bottom Actions
        self.footer = ctk.CTkFrame(self, fg_color="transparent")
        self.footer.pack(side="bottom", fill="x", padx=35, pady=30)
        
        ctk.CTkButton(
            self.footer, 
            text="CANCEL", 
            font=("Segoe UI", 13, "bold"), 
            fg_color="#FEF2F2", 
            text_color="#DD2A2A", 
            border_width=1.5,
            border_color="#FEE5E5",
            height=54, 
            corner_radius=16,
            hover_color="#FEE5E5",
            cursor="hand2",
            command=self.destroy
        ).pack(side="left", expand=True, padx=(0, 8), fill="x")
        
        ctk.CTkButton(
            self.footer, 
            text="SAVE CHANGES", 
            font=("Segoe UI", 13, "bold"), 
            fg_color=COLORS["primary"], 
            text_color="white", 
            height=54, 
            corner_radius=16,
            hover_color="#5899FA",
            cursor="hand2",
            command=self.on_confirm
        ).pack(side="left", expand=True, padx=(8, 0), fill="x")

    def update_selection(self, loc):
        self.selected_loc = loc
        for name, btn in self.btns:
            if name == loc:
                btn.configure(border_width=2, border_color=COLORS["primary"], fg_color=COLORS["white"])
            else:
                btn.configure(border_width=0, border_color=COLORS["bg_main"], fg_color=COLORS["bg_main"])

    def on_confirm(self):
        self.callback(self.selected_loc)
        self.destroy()

class StatusDock(ctk.CTkFrame):
    def __init__(self, master, on_dismiss, on_action, parent_bg=None, icons_dir=None, user_role=None, **kwargs):
        if parent_bg:
            kwargs["bg_color"] = parent_bg
        super().__init__(master, fg_color=COLORS["dock_bg"], corner_radius=24, height=90, **kwargs)
        self.on_dismiss = on_dismiss
        self.on_action = on_action
        self.icons_dir = icons_dir
        self.user_role = user_role
        self._images = {}
        self.pack_propagate(False)
        
        self.left = ctk.CTkFrame(self, fg_color="transparent")
        self.left.pack(side="left", padx=(25, 20))
        
        self.right = ctk.CTkFrame(self, fg_color="transparent")
        self.right.pack(side="right", padx=(0, 25))

        self.counter_box = ctk.CTkFrame(self.left, width=48, height=48, corner_radius=16, fg_color=COLORS["primary"])
        self.counter_box.pack(side="left")
        self.counter_box.pack_propagate(False)
        self.count_lbl = ctk.CTkLabel(self.counter_box, text="0", font=("Segoe UI", 20, "bold"), text_color="white")
        self.count_lbl.place(relx=0.5, rely=0.5, anchor="center")
        
        self.txt = ctk.CTkFrame(self.left, fg_color="transparent")
        self.txt.pack(side="left", padx=15)
        ctk.CTkLabel(self.txt, text="BULK ACTION MODE", font=("Segoe UI", 8, "bold"), text_color=COLORS["text_muted"]).pack(anchor="w")
        self.item_lbl = ctk.CTkLabel(self.txt, text="0 Items Selected", font=("Segoe UI", 12, "bold"), text_color="white")
        self.item_lbl.pack(anchor="w")

        self.btn_status = self.add_btn("activity_white", "status", fallback="⚡")
        
        if self.user_role != "IT_TECHNICIAN":
            self.btn_edit = self.add_btn("pen_white", "edit", fallback="✎")
            self.btn_loc = self.add_btn("map-pin_white", "location", fallback="📍")
            self.btn_del = self.add_delete_btn()
        else:
            self.btn_edit = None
            self.btn_loc = None
            self.btn_del = None
        
        ctk.CTkButton(self.right, text="✕", width=40, height=40, corner_radius=12, fg_color="transparent", text_color=COLORS["text_muted"], font=("Segoe UI", 18), hover_color="#1e293b", cursor="hand2", command=on_dismiss).pack(side="left", padx=(8, 0))

    def _load_icon(self, name):
        if not self.icons_dir or not name:
            return None
        if name in self._images:
            return self._images[name]
            
        candidates = [name, f"{name}.png"]
        for candidate in candidates:
            path = os.path.join(self.icons_dir, candidate)
            if os.path.exists(path):
                try:
                    img = Image.open(path).convert("RGBA")
                    img = img.resize((20, 20))
                    ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(20, 20))
                    self._images[name] = ctk_img
                    return ctk_img
                except Exception:
                    pass
        return None

    def add_btn(self, icon_name, action, fallback="", color="white", hover="#334155"):
        icon_img = self._load_icon(icon_name)
        text = fallback if not icon_img else ""
        
        btn = ctk.CTkButton(self.right, text=text, image=icon_img, width=42, height=42, corner_radius=12, fg_color="#1e293b", border_width=1, border_color="#334155", text_color=color, font=("Segoe UI", 18), hover_color=hover, cursor="hand2", command=lambda: self.on_action(action))
        btn.pack(side="left", padx=4)
        return btn

    def add_delete_btn(self):
        icon_red = self._load_icon("trash_red")
        icon_white = self._load_icon("trash_white")
        text = "🗑" if not icon_red else ""
        
        btn = ctk.CTkButton(self.right, text=text, image=icon_red, width=42, height=42, corner_radius=12, fg_color="#1e293b", border_width=1, border_color="#334155", text_color=COLORS["red"], font=("Segoe UI", 18), hover_color="#EF4444", cursor="hand2", command=lambda: self.on_action("delete"))
        btn.pack(side="left", padx=4)
        
        if icon_white and icon_red:
            def on_enter(e):
                btn.configure(image=icon_white, border_color="#EF4444", fg_color="#EF4444")
            def on_leave(e):
                btn.configure(image=icon_red, border_color="#334155", fg_color="#1e293b")
            btn.bind("<Enter>", on_enter)
            btn.bind("<Leave>", on_leave)
            
        return btn

    def update(self, count):
        self.count_lbl.configure(text=str(count))
        self.item_lbl.configure(text=f"{count} {'Item' if count==1 else 'Items'} Selected")
        if self.btn_edit:
            if count > 1:
                self.btn_edit.pack_forget()
            else:
                self.btn_edit.pack(side="left", padx=5, before=self.btn_loc)
    