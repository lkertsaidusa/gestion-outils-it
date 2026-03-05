"""
toast_error.py
Toast notification moderne pour les messages d erreur
Style moderne avec fond rouge, icône croix et animation slide-in
"""

import customtkinter as ctk
from PIL import Image
import os


class ErrorToast(ctk.CTkFrame):
    TOAST_BG = "#EF4444"
    TOAST_BG_HOVER = "#DC2626"
    TEXT_COLOR = "#FFFFFF"
    TOAST_HEIGHT = 70
    TOAST_MIN_WIDTH = 300
    TOAST_MAX_WIDTH = 600
    CORNER_RADIUS = 20
    SLIDE_DURATION = 300
    SLIDE_STEPS = 15

    def __init__(self, parent, message, duration=3000, icons_dir=None):
        super().__init__(parent, fg_color=self.TOAST_BG, corner_radius=self.CORNER_RADIUS)
        self.parent = parent
        self.message = message
        self.duration = duration
        self._slide_job = None
        self._hide_job = None
        self._is_hovering = False
        self._create_widgets()
        self._bind_events()

    def _create_widgets(self):
        self.configure(height=self.TOAST_HEIGHT)
        
        icon_frame = ctk.CTkFrame(self, fg_color="transparent", width=50, height=50)
        icon_frame.pack(side="left", padx=(20, 0), pady=10)
        icon_frame.pack_propagate(False)
        
        icon_bg = ctk.CTkFrame(icon_frame, fg_color="#FFFFFF", corner_radius=25, width=50, height=50)
        icon_bg.pack(fill="both", expand=True)
        icon_bg.pack_propagate(False)
        
        icon_label = ctk.CTkLabel(icon_bg, text="✕", font=ctk.CTkFont(family="Segoe UI", size=28, weight="bold"), text_color=self.TOAST_BG)
        icon_label.place(relx=0.5, rely=0.5, anchor="center")
        
        message_frame = ctk.CTkFrame(self, fg_color="transparent")
        message_frame.pack(side="left", fill="both", expand=True, padx=(15, 20), pady=10)
        
        self.message_label = ctk.CTkLabel(message_frame, text=self.message, font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"), text_color=self.TEXT_COLOR, anchor="w", justify="left")
        self.message_label.pack(fill="both", expand=True)
        
        close_btn = ctk.CTkButton(self, text="✕", font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"), text_color=self.TEXT_COLOR, fg_color="transparent", hover_color="#DC2626", width=40, height=40, corner_radius=20, command=self.hide)
        close_btn.pack(side="right", padx=(0, 15), pady=10)
        
        self.update_idletasks()
        text_width = len(self.message) * 8 + 150
        toast_width = max(self.TOAST_MIN_WIDTH, min(text_width, self.TOAST_MAX_WIDTH))
        self.configure(width=toast_width)

    def _bind_events(self):
        def on_enter(event):
            self._is_hovering = True
            self.configure(fg_color=self.TOAST_BG_HOVER)
        
        def on_leave(event):
            self._is_hovering = False
            self.configure(fg_color=self.TOAST_BG)
        
        self.bind("<Enter>", on_enter)
        self.bind("<Leave>", on_leave)
        
        for child in self.winfo_children():
            child.bind("<Enter>", on_enter)
            child.bind("<Leave>", on_leave)
            if hasattr(child, "winfo_children"):
                for subchild in child.winfo_children():
                    subchild.bind("<Enter>", on_enter)
                    subchild.bind("<Leave>", on_leave)

    def show(self, final_y=30):
        self.update_idletasks()
        self.parent.update_idletasks()
        start_y = -self.TOAST_HEIGHT - 20
        self.place(relx=0.5, y=start_y, anchor="n")
        self._animate_slide(start_y, final_y, on_complete=self._schedule_hide)

    def _animate_slide(self, start_y, end_y, on_complete=None):
        step = [0]
        total_steps = self.SLIDE_STEPS
        delay = self.SLIDE_DURATION // total_steps

        def animate():
            if step[0] <= total_steps:
                progress = step[0] / total_steps
                ease = 1 - pow(1 - progress, 3)
                current_y = start_y + (end_y - start_y) * ease
                try:
                    self.place(relx=0.5, y=int(current_y), anchor="n")
                except Exception:
                    return
                step[0] += 1
                self._slide_job = self.after(delay, animate)
            else:
                if on_complete:
                    on_complete()
        animate()

    def _schedule_hide(self):
        def check_and_hide():
            if not self._is_hovering:
                self.hide()
            else:
                self._hide_job = self.after(500, check_and_hide)
        self._hide_job = self.after(self.duration, check_and_hide)

    def hide(self):
        if self._hide_job:
            self.after_cancel(self._hide_job)
            self._hide_job = None
        if self._slide_job:
            self.after_cancel(self._slide_job)
            self._slide_job = None
        current_y = self.winfo_y()
        final_y = -self.TOAST_HEIGHT - 20
        self._animate_slide(current_y, final_y, on_complete=self._destroy_toast)

    def _destroy_toast(self):
        try:
            self.place_forget()
            self.destroy()
        except Exception:
            pass


def show_error_toast(parent, message, duration=3000, icons_dir=None, top_padding=30):
    toast = ErrorToast(parent, message, duration, icons_dir)
    toast.show(final_y=top_padding)
