import os
import sys
import logging
from pathlib import Path
import customtkinter as ctk
from PIL import Image
from app.components.toast_success import show_success_toast
from app.components.toast_error import show_error_toast

# Setup logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Icons directory
ICONS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "assets", "icons"))

# Theme matching inventory_view.py
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
    "red": "#EF4444",
    "inactive_text": "#6B7280",
    "primary_light": "#EBF2FE"  # Light blue for selection
}

FAQ_DATA = [
    {
        "q": "What is the strict constraint when entering a serial number?",
        "a": "The serial number must be unique across the entire database and must not exceed 9 characters. If you enter a duplicate, the system will block validation.",
        "icon": "box_blue"
    },
    {
        "q": "Why doesn't the battery health indicator appear on my printer sheet?",
        "a": "Battery diagnostics is a contextual feature. It only activates for mobile equipment categories, namely PC and PHONE.",
        "icon": "triangle-alert"
    },
    {
        "q": "What is the difference between 'HAND OUT' and 'INCREASE' in the supplies hub?",
        "a": "'INCREASE' allows you to record the arrival of new stock (replenishment), while 'HAND OUT' records the distribution of a unit to an employee.",
        "icon": "package"
    },
    {
        "q": "What does a red-colored zone on the office map mean?",
        "a": "This indicates a Density Alert. The zone contains more objects (assets + consumables) than the maximum authorized capacity defined for that office.",
        "icon": "triangle-alert"
    },
    {
        "q": "How can I modify the capacity alert threshold for a specific office?",
        "a": "Click on the zone on the Map, then in the side panel that opens, click on the blue gear icon ('Occupancy Threshold') to manually adjust the maximum number of units allowed.",
        "icon": "setting"
    },
    {
        "q": "How do I perform a location change for 20 screens at once?",
        "a": "In the inventory, check the screens concerned. The 'Action Dock' will appear at the bottom of the screen. Click on the geolocation icon (MapPin), choose the new zone, and validate to update everything simultaneously.",
        "icon": "map"
    },
    {
        "q": "What happens to equipment when I change its location from the Action Dock?",
        "a": "When you use the location change action from the Action Dock, the system updates the localisation field for all selected items and keeps their history so that the Dashboard and Map stay in sync.",
        "icon": "map"
    },
    {
        "q": "Why don’t I see consumables when I log in as IT Technician?",
        "a": "The IT Technician role is restricted to maintenance operations on equipment only. Supplies are hidden and the inventory is automatically filtered to show only items in MAINTENANCE.",
        "icon": "shield-alert"
    },
    {
        "q": "Why can’t I assign new items to SECTION A, B or C when they look full?",
        "a": "Each section has a maximum capacity. Once the total number of items and consumables reaches this limit, the section is marked as full, the card turns red, and the system blocks new assignments to avoid overloading.",
        "icon": "triangle-alert"
    },
    {
        "q": "How does the password strength indicator work in settings?",
        "a": "It uses a real-time entropy gauge. It goes from 'UNSAFE' (red, < 4 characters) to 'VERY SAFE' (green, > 10 characters) to ensure your security phrase is robust.",
        "icon": "shield-alert"
    }
]


class FAQItem(ctk.CTkFrame):
    """FAQ item ultra moderne avec design amélioré"""

    all_items = []  # Liste pour tracker tous les items FAQ

    def __init__(self, master, data, index):
        super().__init__(
            master,
            fg_color=THEME["white"],
            corner_radius=20,
            border_width=2,
            border_color=THEME["border"]
        )

        self.data = data
        self.is_open = False
        self._icon_cache = {}
        FAQItem.all_items.append(self)  # Ajouter à la liste
        
        self.pack(fill="x", pady=8, padx=0)
        
        # ── MAIN CONTAINER (header always visible) ──
        self.header_container = ctk.CTkFrame(
            self,
            fg_color="transparent",
            height=85
        )
        self.header_container.pack(fill="x", padx=0, pady=0)
        self.header_container.pack_propagate(False)

        # ── Question avec meilleur spacing ──
        question_container = ctk.CTkFrame(self.header_container, fg_color="transparent")
        question_container.place(x=25, rely=0.5, anchor="w")
        
        self.question_label = ctk.CTkLabel(
            question_container,
            text=data.get("q"),
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=THEME["text_dark"],
            anchor="w"
        )
        self.question_label.pack(anchor="w")
        
        # Badge "Click to see answer"
        self.hint_badge = ctk.CTkLabel(
            question_container,
            text="Click to see answer",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=THEME["primary"],
            fg_color=THEME["primary_light"],
            corner_radius=8,
            padx=10,
            pady=4
        )
        self.hint_badge.pack(anchor="w", pady=(6, 0))
        
        # ── Arrow indicator plus moderne ──
        self.arrow_container = ctk.CTkFrame(
            self.header_container,
            width=45,
            height=45,
            corner_radius=12,
            fg_color="transparent"
        )
        self.arrow_container.place(relx=0.97, rely=0.5, anchor="e")
        self.arrow_container.pack_propagate(False)

        # Charger l'icône chevron
        self.chevron_down = self._load_icon("chevron-down_blue", size=(20, 20))
        self.chevron_left = self._load_icon("chevron-left", size=(20, 20))  # Pour l'état fermé

        self.arrow_label = ctk.CTkLabel(
            self.arrow_container,
            text="" if self.chevron_left else "›",
            image=self.chevron_left if self.chevron_left else None,
            fg_color="transparent"
        )
        self.arrow_label.place(relx=0.5, rely=0.5, anchor="center")
        
        # ── Answer container avec padding généreux ──
        self.answer_outer = ctk.CTkFrame(
            self,
            fg_color=THEME["row_hover"],
            corner_radius=16,
            border_width=0,
            border_color=THEME["border"]
        )
        
        self.answer_inner = ctk.CTkFrame(
            self.answer_outer,
            fg_color="transparent"
        )
        self.answer_inner.pack(fill="both", expand=True, padx=30, pady=25)
        
        # Label "Answer"
        ctk.CTkLabel(
            self.answer_inner,
            text="💡 ANSWER",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=THEME["primary"],
            anchor="w"
        ).pack(anchor="w", pady=(0, 10))
        
        self.answer_label = ctk.CTkLabel(
            self.answer_inner,
            text=data.get("a"),
            font=ctk.CTkFont(family="Segoe UI", size=14),
            text_color=THEME["text_dark"],
            wraplength=1000,
            justify="left",
            anchor="w"
        )
        self.answer_label.pack(anchor="w", fill="x")
        
        # ── Bindings - Tout le header est cliquable ──
        self.configure(cursor="hand2")
        self.bind("<Button-1>", self.toggle)
        self.bind("<Enter>", self.on_hover)
        self.bind("<Leave>", self.on_leave)

        # Rendre tous les enfants du header cliquables
        self.header_container.configure(cursor="hand2")
        self.header_container.bind("<Button-1>", self.toggle)
        self.header_container.bind("<Enter>", self.on_hover)
        self.header_container.bind("<Leave>", self.on_leave)

        for child in [question_container, self.question_label,
                      self.hint_badge, self.arrow_container, self.arrow_label]:
            try:
                child.configure(cursor="hand2")
                child.bind("<Button-1>", self.toggle)
                child.bind("<Enter>", self.on_hover)
                child.bind("<Leave>", self.on_leave)
            except:
                pass
    
    def _load_icon(self, base_name, size=(28, 28)):
        """Load icon from assets/icons directory"""
        if not base_name:
            return None
        
        key = f"{base_name}_{size[0]}x{size[1]}"
        if key in self._icon_cache:
            return self._icon_cache[key]
        
        candidates = [
            f"{base_name}.png",
            f"{base_name}_icon.png",
            f"{base_name}-icon.png"
        ]
        
        for name in candidates:
            path = os.path.join(ICONS_DIR, name)
            if os.path.exists(path):
                try:
                    img = Image.open(path).convert("RGBA")
                    img = img.resize(size)
                    ctk_img = ctk.CTkImage(light_image=img, size=size)
                    self._icon_cache[key] = ctk_img
                    return ctk_img
                except Exception as e:
                    logger.error(f"Error loading icon {path}: {e}")
        
        return None
    
    def on_hover(self, event=None):
        if not self.is_open:
            self.configure(
                border_color=THEME["primary"],
                fg_color=THEME["row_hover"]
            )
    
    def on_leave(self, event=None):
        if not self.is_open:
            self.configure(
                border_color=THEME["border"],
                fg_color=THEME["white"]
            )
    
    def toggle(self, event=None):
        if self.is_open:
            self.close()
        else:
            self.open()
    
    def open(self):
        """Open with beautiful animation effect"""
        # Fermer toutes les autres questions (comportement accordion)
        for item in FAQItem.all_items:
            if item is not self and item.is_open:
                item.close()

        self.is_open = True

        # Enlever visuellement les bordures en utilisant la couleur du fond blanc
        self.configure(
            fg_color=THEME["white"],
            border_color=THEME["white"],
            border_width=2
        )

        # Garder le header transparent
        self.header_container.configure(fg_color="transparent")

        self.question_label.configure(text_color=THEME["primary"])
        self.hint_badge.pack_forget()

        # Garder le container du chevron transparent
        self.arrow_container.configure(fg_color="transparent")

        # Afficher chevron-down_blue
        if self.chevron_down:
            self.arrow_label.configure(
                image=self.chevron_down,
                text=""
            )
        else:
            self.arrow_label.configure(
                text="▼",
                text_color=THEME["primary"]
            )

        # Ajouter les bordures bleues au container de la réponse
        self.answer_outer.configure(
            border_width=3,
            border_color=THEME["primary"]
        )

        self.answer_outer.pack(fill="x", padx=20, pady=(0, 20))
        self.update()
    
    def close(self):
        """Close the FAQ item"""
        self.is_open = False

        # Remettre les bordures normales
        self.configure(
            border_color=THEME["border"],
            fg_color=THEME["white"],
            border_width=2
        )

        # Remettre le header container en transparent
        self.header_container.configure(fg_color="transparent")

        self.question_label.configure(text_color=THEME["text_dark"])
        self.hint_badge.pack(anchor="w", pady=(6, 0))

        # Garder le container du chevron transparent
        self.arrow_container.configure(fg_color="transparent")

        # Afficher chevron-left
        if self.chevron_left:
            self.arrow_label.configure(
                image=self.chevron_left,
                text=""
            )
        else:
            self.arrow_label.configure(
                text="›",
                text_color=THEME["text_gray"]
            )

        # Enlever les bordures du container de réponse
        self.answer_outer.configure(
            border_width=0
        )

        self.answer_outer.pack_forget()



class ContactForm(ctk.CTkFrame):
    """Contact form matching inventory design"""
    
    def __init__(self, master):
        super().__init__(
            master,
            fg_color=THEME["white"],
            corner_radius=20,
            border_width=1,
            border_color=THEME["border"]
        )
        
        self._icon_cache = {}
        
        # ── Header ──
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=30, pady=(30, 20))
        
        # Icon
        mail_icon = self._load_icon("mail", size=(24, 24))
        if mail_icon:
            icon_container = ctk.CTkFrame(
                header,
                width=50,
                height=50,
                corner_radius=12,
                fg_color=THEME["icon_bg"]
            )
            icon_container.pack(side="left", padx=(0, 15))
            icon_container.pack_propagate(False)
            
            ctk.CTkLabel(
                icon_container,
                image=mail_icon,
                text=""
            ).place(relx=0.5, rely=0.5, anchor="center")
        
        # Title
        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.pack(side="left")

        ctk.CTkLabel(
            title_frame,
            text="Contact Support",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color=THEME["text_dark"]
        ).pack(anchor="w")

        ctk.CTkLabel(
            title_frame,
            text="Our team will respond within 24 hours",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#2563EB"
        ).pack(anchor="w", pady=(2, 0))
        
        # ── Form fields ──
        form = ctk.CTkFrame(self, fg_color="transparent")
        form.pack(fill="x", padx=30, pady=15)
        
        # Row 1: Name and Email
        row1 = ctk.CTkFrame(form, fg_color="transparent")
        row1.pack(fill="x", pady=(0, 15))
        
        # Name
        name_col = ctk.CTkFrame(row1, fg_color="transparent")
        name_col.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.name_label = ctk.CTkLabel(
            name_col,
            text="FULL NAME",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=THEME["text_gray"]
        )
        self.name_label.pack(anchor="w", pady=(0, 6))

        self.name_entry = ctk.CTkEntry(
            name_col,
            placeholder_text="Enter your name",
            height=48,
            corner_radius=12,
            border_width=2,
            border_color=THEME["border"],
            fg_color=THEME["white"],
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color=THEME["text_dark"]
        )
        self.name_entry.pack(fill="x")
        self.name_entry.bind("<FocusIn>", lambda e: self._on_focus_name(True))
        self.name_entry.bind("<FocusOut>", lambda e: self._on_focus_name(False))

        # Store entry reference
        self._name_entry_widget = self.name_entry

        # Email
        email_col = ctk.CTkFrame(row1, fg_color="transparent")
        email_col.pack(side="left", fill="x", expand=True, padx=(8, 0))

        self.email_label = ctk.CTkLabel(
            email_col,
            text="EMAIL",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=THEME["text_gray"]
        )
        self.email_label.pack(anchor="w", pady=(0, 6))

        self.email_entry = ctk.CTkEntry(
            email_col,
            placeholder_text="your.email@example.com",
            height=48,
            corner_radius=12,
            border_width=2,
            border_color=THEME["border"],
            fg_color=THEME["white"],
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color=THEME["text_dark"]
        )
        self.email_entry.pack(fill="x")
        self.email_entry.bind("<FocusIn>", lambda e: self._on_focus_email(True))
        self.email_entry.bind("<FocusOut>", lambda e: self._on_focus_email(False))

        # Store entry reference
        self._email_entry_widget = self.email_entry
        
        # Priority selector
        priority_container = ctk.CTkFrame(form, fg_color="transparent")
        priority_container.pack(fill="x", pady=(0, 15))

        ctk.CTkLabel(
            priority_container,
            text="PRIORITY",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=THEME["text_gray"]
        ).pack(anchor="w", pady=(0, 6))

        priority_row = ctk.CTkFrame(priority_container, fg_color="transparent")
        priority_row.pack(fill="x")

        self.selected_priority = "NORMAL"
        self.priority_buttons = {}

        priorities = [
            ("🟢  NORMAL", "NORMAL", THEME["success_text"], THEME["success_bg"]),
            ("🟡  HIGH", "HIGH", THEME["warning_text"], THEME["warning_bg"]),
            ("🔴  CRITICAL", "CRITICAL", THEME["red"], "#FEF2F2")
        ]
        
        for i, (label, value, color, bg) in enumerate(priorities):
            btn = ctk.CTkButton(
                priority_row,
                text=label,
                height=48,
                corner_radius=12,
                fg_color=THEME["white"],
                hover_color=THEME["row_hover"],
                font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                text_color=THEME["text_gray"],
                border_width=2,
                border_color=THEME["border"],
                command=lambda v=value, c=color, b=bg: self.select_priority(v, c, b)
            )
            btn.grid(row=0, column=i, padx=4, sticky="ew")
            priority_row.grid_columnconfigure(i, weight=1)
            self.priority_buttons[value] = (btn, color, bg)
        
        self.select_priority("NORMAL", THEME["success_text"], THEME["success_bg"])

        # Message field
        msg_container = ctk.CTkFrame(form, fg_color="transparent")
        msg_container.pack(fill="x")

        self.message_label = ctk.CTkLabel(
            msg_container,
            text="MESSAGE",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=THEME["text_gray"]
        )
        self.message_label.pack(anchor="w", pady=(0, 6))

        self.message_text = ctk.CTkTextbox(
            msg_container,
            height=120,
            corner_radius=12,
            border_width=2,
            border_color=THEME["border"],
            fg_color=THEME["white"],
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color=THEME["text_dark"]
        )
        self.message_text.pack(fill="x")
        self.message_text.bind("<FocusIn>", lambda e: self._on_focus_message(True))
        self.message_text.bind("<FocusOut>", lambda e: self._on_focus_message(False))

        # Store textbox reference
        self._message_text_widget = self.message_text

        # Bind global click to parent to handle defocus
        try:
            parent = self.winfo_toplevel()
            parent.bind("<Button-1>", self._on_global_click, add="+")
        except Exception:
            pass

        # Submit button
        submit_btn = ctk.CTkButton(
            self,
            text="SEND MESSAGE",
            height=55,
            corner_radius=16,
            fg_color=THEME["primary"],
            hover_color=THEME["primary_hover"],
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            command=self.submit
        )
        submit_btn.pack(fill="x", padx=30, pady=(15, 30))
    
    def _load_icon(self, base_name, size=(24, 24)):
        """Load icon from assets/icons directory"""
        if not base_name:
            return None
        
        key = f"{base_name}_{size[0]}x{size[1]}"
        if key in self._icon_cache:
            return self._icon_cache[key]
        
        candidates = [
            f"{base_name}.png",
            f"{base_name}_icon.png"
        ]
        
        for name in candidates:
            path = os.path.join(ICONS_DIR, name)
            if os.path.exists(path):
                try:
                    img = Image.open(path).convert("RGBA")
                    img = img.resize(size)
                    ctk_img = ctk.CTkImage(light_image=img, size=size)
                    self._icon_cache[key] = ctk_img
                    return ctk_img
                except Exception:
                    pass
        
        return None

    def _on_focus_name(self, focused):
        """Handle focus change for name field"""
        if focused:
            self.name_entry.configure(border_color=THEME["primary"])
            self.name_label.configure(text_color=THEME["primary"])
        else:
            self.name_entry.configure(border_color=THEME["border"])
            self.name_label.configure(text_color=THEME["text_gray"])

    def _on_focus_email(self, focused):
        """Handle focus change for email field"""
        if focused:
            self.email_entry.configure(border_color=THEME["primary"])
            self.email_label.configure(text_color=THEME["primary"])
        else:
            self.email_entry.configure(border_color=THEME["border"])
            self.email_label.configure(text_color=THEME["text_gray"])

    def _on_focus_message(self, focused):
        """Handle focus change for message field"""
        if focused:
            self.message_text.configure(border_color=THEME["primary"])
            self.message_label.configure(text_color=THEME["primary"])
        else:
            self.message_text.configure(border_color=THEME["border"])
            self.message_label.configure(text_color=THEME["text_gray"])

    def _on_global_click(self, event):
        """Remove focus from fields when clicking outside"""
        try:
            x_root = event.x_root
            y_root = event.y_root

            # Check if click is inside any of the entry fields
            for widget in [self._name_entry_widget, self._email_entry_widget, self._message_text_widget]:
                try:
                    wx = widget.winfo_rootx()
                    wy = widget.winfo_rooty()
                    ww = widget.winfo_width()
                    wh = widget.winfo_height()

                    inside = (wx <= x_root <= wx + ww) and (wy <= y_root <= wy + wh)

                    if inside:
                        return  # Click is inside one of the fields, don't defocus
                except Exception:
                    pass

            # Click is outside all fields, remove focus
            try:
                self.focus_set()
            except Exception:
                pass
        except Exception:
            pass

    def select_priority(self, priority, color, bg):
        self.selected_priority = priority
        
        for p, (btn, c, b) in self.priority_buttons.items():
            if p == priority:
                btn.configure(
                    fg_color=bg,
                    border_color=color,
                    text_color=color
                )
            else:
                btn.configure(
                    fg_color=THEME["white"],
                    border_color=THEME["border"],
                    text_color=THEME["text_gray"]
                )
    
    def submit(self):
        """Envoyer le message par email"""
        # Récupérer les données du formulaire
        name = self.name_entry.get().strip()
        email = self.email_entry.get().strip()
        message = self.message_text.get("1.0", "end-1c").strip()
        priority = self.selected_priority
        
        # Basic validation
        if not name or not email or not message:
            show_error_toast(
                parent=self.winfo_toplevel(),
                message="Please fill in all fields",
                duration=3000,
                top_padding=50
            )
            return

        # Simple email validation
        if "@" not in email or "." not in email:
            show_error_toast(
                parent=self.winfo_toplevel(),
                message="Please enter a valid email address",
                duration=3000,
                top_padding=50
            )
            return
        
        # Envoyer l'email
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            # ═══════════════════════════════════════════════════════════
            # ⚠️ CONFIGURATION EMAIL - MODIFIE CES VALEURS ⚠️
            # ═══════════════════════════════════════════════════════════
            
            # TON EMAIL PROFESSIONNEL (où tu veux recevoir les messages)
            DESTINATION_EMAIL = "saidlepro0@gmail.com"  # ← CHANGE ICI
            
            # EMAIL D'ENVOI (Gmail recommandé)
            SENDER_EMAIL = "saidlepro0@gmail.com"  # ← CHANGE ICI
            SENDER_PASSWORD = "lmoy uzqv fplk haab"  # ← CHANGE ICI
            
            # ═══════════════════════════════════════════════════════════
            
            # Créer le message
            msg = MIMEMultipart()
            msg['From'] = f"{name} <{SENDER_EMAIL}>"
            msg['To'] = DESTINATION_EMAIL
            msg['Subject'] = f"[TechPro Support] Message from {name} - Priority: {priority}"
            
            # HTML message body
            html_body = f"""
            <html>
                <body style="font-family: Arial, sans-serif; padding: 20px; background-color: #f0f4f9;">
                    <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 20px; padding: 30px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                        <h2 style="color: #166FFF; margin-bottom: 20px;">📧 New support message</h2>

                        <div style="background: #f8fafc; padding: 15px; border-radius: 10px; margin-bottom: 20px;">
                            <p style="margin: 5px 0;"><strong>Name:</strong> {name}</p>
                            <p style="margin: 5px 0;"><strong>Email:</strong> {email}</p>
                            <p style="margin: 5px 0;"><strong>Priority:</strong> <span style="color: {'#2FC967' if priority == 'NORMAL' else '#F97316' if priority == 'HIGH' else '#EF4444'}">{priority}</span></p>
                        </div>

                        <div style="background: #ffffff; padding: 20px; border-left: 4px solid #166FFF; border-radius: 8px;">
                            <h3 style="color: #1E293B; margin-top: 0;">Message:</h3>
                            <p style="color: #4B5563; line-height: 1.6; white-space: pre-wrap;">{message}</p>
                        </div>

                        <hr style="border: none; border-top: 1px solid #E5E7EB; margin: 20px 0;">

                        <p style="color: #9CA3AF; font-size: 12px; text-align: center; margin: 0;">
                            This message was sent from TechPro Help Center
                        </p>
                    </div>
                </body>
            </html>
            """
            
            msg.attach(MIMEText(html_body, 'html'))
            
            # Envoyer via Gmail SMTP
            try:
                server = smtplib.SMTP('smtp.gmail.com', 587)
                server.starttls()
                server.login(SENDER_EMAIL, SENDER_PASSWORD)
                server.send_message(msg)
                server.quit()
                
                logger.info(f"✅ Email envoyé avec succès à {DESTINATION_EMAIL}")
                
                # Show success with modern toast
                show_success_toast(
                    parent=self.winfo_toplevel(),
                    message="Message sent successfully!",
                    duration=3000,
                    top_padding=50
                )
                
                # Réinitialiser le formulaire
                self.name_entry.delete(0, "end")
                self.email_entry.delete(0, "end")
                self.message_text.delete("1.0", "end")
                
            except smtplib.SMTPAuthenticationError:
                logger.error("❌ Gmail authentication error")
                show_error_toast(
                    parent=self.winfo_toplevel(),
                    message="Unable to connect to Gmail. Check your credentials.",
                    duration=4000,
                    top_padding=50
                )
            except Exception as e:
                logger.error(f"❌ SMTP Error: {e}")
                show_error_toast(
                    parent=self.winfo_toplevel(),
                    message=f"Unable to send email: {str(e)[:50]}",
                    duration=4000,
                    top_padding=50
                )

        except ImportError:
            logger.error("❌ smtplib module not available")
            show_error_toast(
                parent=self.winfo_toplevel(),
                message="Email functionality is not available",
                duration=3000,
                top_padding=50
            )
        except Exception as e:
            logger.error(f"❌ General error: {e}")
            show_error_toast(
                parent=self.winfo_toplevel(),
                message=f"An error occurred: {str(e)[:50]}",
                duration=3000,
                top_padding=50
            )
    
class HelpView(ctk.CTkFrame):
    """Help center view matching inventory design exactly"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.configure(fg_color=THEME["bg"], corner_radius=0)
        self.pack(fill="both", expand=True)
        
        self._icon_cache = {}
        self._create_ui()
    
    def _create_ui(self):
        # ── TITLE + SEPARATOR (same as inventory) ──
        title_container = ctk.CTkFrame(self, fg_color="transparent")
        title_container.pack(fill="x", padx=40, pady=(30, 0))
        
        title = ctk.CTkLabel(
            title_container,
            text="Help Center",
            font=ctk.CTkFont(family="Segoe UI", size=32, weight="bold"),
            text_color=THEME["text_dark"],
            anchor="w"
        )
        title.pack(fill="x")
        
        separator = ctk.CTkFrame(
            self,
            fg_color=THEME["border"],
            height=1
        )
        separator.pack(fill="x", padx=40, pady=(12, 0))
        
        # ── SUBTITLE ──
        subtitle_container = ctk.CTkFrame(self, fg_color="transparent")
        subtitle_container.pack(fill="x", padx=40, pady=(15, 25))

        ctk.CTkLabel(
            subtitle_container,
            text="Quickly find answers to your questions",
            font=ctk.CTkFont(family="Segoe UI", size=14),
            text_color=THEME["text_gray"],
            anchor="w"
        ).pack(anchor="w")
        
        # ── MAIN CARD (same style as inventory table card) ──
        main_card = ctk.CTkFrame(
            self,
            fg_color=THEME["white"],
            corner_radius=40
        )
        main_card.pack(fill="both", expand=True, padx=40, pady=(0, 40))
        
        # Scrollable content
        scroll = ctk.CTkScrollableFrame(
            main_card,
            fg_color="transparent",
            scrollbar_fg_color=THEME["white"],
            scrollbar_button_color="#CBD5E1",
            scrollbar_button_hover_color=THEME["text_gray"]
        )
        scroll.pack(fill="both", expand=True, padx=25, pady=25)
        
        # ── FAQ SECTION ──
        faq_header = ctk.CTkFrame(scroll, fg_color="transparent")
        faq_header.pack(fill="x", pady=(0, 20))
        
        # Icon
        help_icon = self._load_icon("shield-question-mark", size=(28, 28))
        if help_icon:
            icon_container = ctk.CTkFrame(
                faq_header,
                width=55,
                height=55,
                corner_radius=14,
                fg_color=THEME["icon_bg"]
            )
            icon_container.pack(side="left", padx=(0, 15))
            icon_container.pack_propagate(False)

            ctk.CTkLabel(
                icon_container,
                image=help_icon,
                text=""
            ).place(relx=0.5, rely=0.5, anchor="center")
        
        # Title
        title_frame = ctk.CTkFrame(faq_header, fg_color="transparent")
        title_frame.pack(side="left")
        
        ctk.CTkLabel(
            title_frame,
            text="Frequently Asked Questions",
            font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"),
            text_color=THEME["text_dark"],
            anchor="w"
        ).pack(anchor="w")

        ctk.CTkLabel(
            title_frame,
            text="Click on a question to see the detailed answer",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=THEME["primary"],
            anchor="w"
        ).pack(anchor="w", pady=(2, 0))
        
        # FAQ items
        for i, faq in enumerate(FAQ_DATA):
            FAQItem(scroll, faq, i)
        
        # ── CONTACT SECTION ──
        ctk.CTkFrame(scroll, fg_color="transparent", height=30).pack()
        
        contact_header = ctk.CTkFrame(scroll, fg_color="transparent")
        contact_header.pack(fill="x", pady=(10, 20))
        
        bell_icon = self._load_icon("bell_blue", size=(28, 28))
        if bell_icon:
            icon_container = ctk.CTkFrame(
                contact_header,
                width=55,
                height=55,
                corner_radius=14,
                fg_color=THEME["icon_bg"]
            )
            icon_container.pack(side="left", padx=(0, 15))
            icon_container.pack_propagate(False)
            
            ctk.CTkLabel(
                icon_container,
                image=bell_icon,
                text=""
            ).place(relx=0.5, rely=0.5, anchor="center")
        
        title_frame = ctk.CTkFrame(contact_header, fg_color="transparent")
        title_frame.pack(side="left")
        
        ctk.CTkLabel(
            title_frame,
            text="Need Additional Help?",
            font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"),
            text_color=THEME["text_dark"],
            anchor="w"
        ).pack(anchor="w")

        ctk.CTkLabel(
            title_frame,
            text="Our support team is here to assist you",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=THEME["primary"],
            anchor="w"
        ).pack(anchor="w", pady=(2, 0))
        
        ContactForm(scroll).pack(fill="x", pady=(0, 20))
    
    def _load_icon(self, base_name, size=(28, 28)):
        """Load icon from assets/icons directory"""
        if not base_name:
            return None
        
        key = f"{base_name}_{size[0]}x{size[1]}"
        if key in self._icon_cache:
            return self._icon_cache[key]
        
        candidates = [
            f"{base_name}.png",
            f"{base_name}_icon.png"
        ]
        
        for name in candidates:
            path = os.path.join(ICONS_DIR, name)
            if os.path.exists(path):
                try:
                    img = Image.open(path).convert("RGBA")
                    img = img.resize(size)
                    ctk_img = ctk.CTkImage(light_image=img, size=size)
                    self._icon_cache[key] = ctk_img
                    return ctk_img
                except Exception as e:
                    logger.error(f"Error loading icon {path}: {e}")
        
        return None


# ── STANDALONE TEST ──
if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")
    
    root = ctk.CTk()
    root.title("Help Center")
    root.geometry("1400x850")
    
    view = HelpView(root)
    
    root.mainloop()