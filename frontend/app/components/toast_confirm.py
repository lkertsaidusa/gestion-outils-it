"""
toast_confirm.py
Toast de confirmation pour actions importantes
Affiche un message avec boutons Yes/No
"""

import customtkinter as ctk
import os
from PIL import Image

ICONS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "assets", "icons"))

class ConfirmToast(ctk.CTkToplevel):
    THEME = {
        "bg": "#FFFFFF",
        "primary": "#166FFF",
        "text_dark": "#1E293B",
        "text_gray": "#64748B",
        "danger": "#EF4444",
        "danger_hover": "#DC2626",
        "cancel_bg": "#F1F5F9",
        "cancel_hover": "#E2E8F0",
        "cancel_text": "#475569",
        "icon_bg": "#FEF2F2"
    }

    def __init__(self, parent, message, on_confirm=None, on_cancel=None):
        super().__init__(parent)
        self.parent = parent
        self.message = message
        self.on_confirm = on_confirm
        self.on_cancel = on_cancel

        self.title("")
        # Height decreased to 200 to remove empty bottom space
        self.geometry("440x200")
        self.resizable(False, False)
        self.configure(fg_color=self.THEME["bg"])
        self.transient(parent)
        
        self.grab_set()

        # Centrer
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - 440) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - 200) // 2
        self.geometry(f"+{x}+{y}")

        self._create_widgets()

    def _create_widgets(self):
        # Container
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=30, pady=(15, 10))

        # --- ICON ---
        icon_size = 50
        icon_container = ctk.CTkFrame(
            container, 
            width=icon_size, 
            height=icon_size, 
            corner_radius=icon_size // 2, 
            fg_color=self.THEME["icon_bg"]
        )
        icon_container.pack(pady=(0, 8))
        icon_container.pack_propagate(False)

        try:
            icon_path = os.path.join(ICONS_DIR, "alert.png")
            if os.path.exists(icon_path):
                img = Image.open(icon_path).convert("RGBA")
                ctk_icon = ctk.CTkImage(light_image=img, dark_image=img, size=(24, 24))
                icon_label = ctk.CTkLabel(icon_container, image=ctk_icon, text="")
                icon_label.place(relx=0.5, rely=0.5, anchor="center")
            else:
                # Fallback emoji if icon missing
                icon_label = ctk.CTkLabel(icon_container, text="🚪", font=ctk.CTkFont(size=24))
                icon_label.place(relx=0.5, rely=0.5, anchor="center")
        except Exception:
            icon_label = ctk.CTkLabel(icon_container, text="!", font=ctk.CTkFont(size=24))
            icon_label.place(relx=0.5, rely=0.5, anchor="center")

        # Message
        message_label = ctk.CTkLabel(
            container, 
            text=self.message, 
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"), 
            text_color=self.THEME["text_dark"],
            wraplength=400
        )
        message_label.pack(pady=(0, 10))

        # Buttons container
        btn_frame = ctk.CTkFrame(container, fg_color="transparent")
        btn_frame.pack(fill="x")

        # No button (Cancel)
        no_btn = ctk.CTkButton(
            btn_frame, 
            text="NO", 
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), 
            fg_color=self.THEME["cancel_bg"], 
            hover_color=self.THEME["cancel_hover"], 
            text_color=self.THEME["cancel_text"], 
            width=185, 
            height=40, 
            corner_radius=12, 
            command=self._on_cancel
        )
        no_btn.pack(side="left", padx=(0, 10))

        # Yes button (Confirm)
        yes_btn = ctk.CTkButton(
            btn_frame, 
            text="YES", 
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), 
            fg_color=self.THEME["danger"], 
            hover_color=self.THEME["danger_hover"], 
            text_color="#FFFFFF", 
            width=185, 
            height=40, 
            corner_radius=12, 
            command=self._on_confirm
        )
        yes_btn.pack(side="left")

    def _on_confirm(self):
        self.destroy()
        if self.on_confirm:
            self.on_confirm()

    def _on_cancel(self):
        self.destroy()
        if self.on_cancel:
            self.on_cancel()

    def show(self):
        self.focus_force()


def show_confirm_toast(parent, message, on_confirm=None, on_cancel=None):
    return ConfirmToast(parent, message, on_confirm, on_cancel)
