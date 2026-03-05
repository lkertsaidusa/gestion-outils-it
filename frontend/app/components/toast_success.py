"""
toast_success.py
Toast notification moderne pour les messages de succès
Style moderne avec fond vert, icône et animation slide-in

Usage:
    from app.components.toast_success import show_success_toast
    
    # Affichage simple
    show_success_toast(
        parent=self.winfo_toplevel(),
        message="Equipment added successfully!"
    )
    
    # Avec durée personnalisée
    show_success_toast(
        parent=self.winfo_toplevel(),
        message="Changes saved!",
        duration=2000
    )
    
    # Avec padding personnalisé
    show_success_toast(
        parent=self.winfo_toplevel(),
        message="Equipment added!",
        top_padding=50
    )
"""

import customtkinter as ctk
from PIL import Image, ImageDraw
import os


class SuccessToast(ctk.CTkFrame):
    """
    Toast notification de succès avec animation slide-in/slide-out
    """
    
    # Style du toast
    TOAST_BG = "#10B981"              # Vert moderne
    TOAST_BG_HOVER = "#059669"        # Vert plus foncé au hover
    TEXT_COLOR = "#FFFFFF"            # Texte blanc
    ICON_COLOR = "#FFFFFF"            # Icône blanche
    
    # Dimensions
    TOAST_HEIGHT = 70
    TOAST_MIN_WIDTH = 300
    TOAST_MAX_WIDTH = 600
    CORNER_RADIUS = 20
    
    # Animation
    SLIDE_DURATION = 300              # ms pour l'animation slide
    SLIDE_STEPS = 15                  # Nombre d'étapes d'animation
    
    def __init__(self, parent, message, duration=3000, icons_dir=None):
        """
        Initialise le toast de succès
        
        Args:
            parent: Widget parent (fenêtre principale)
            message: Message à afficher
            duration: Durée d'affichage en ms (default: 3000)
            icons_dir: Chemin vers le dossier des icônes (optionnel)
        """
        super().__init__(parent, fg_color=self.TOAST_BG, corner_radius=self.CORNER_RADIUS)
        
        self.parent = parent
        self.message = message
        self.duration = duration
        self.icons_dir = icons_dir or self._find_icons_directory()
        
        # Jobs d'animation
        self._slide_job = None
        self._hide_job = None
        self._destroy_job = None
        
        # État
        self._is_hovering = False
        
        self._create_widgets()
        self._bind_events()
    
    def _create_widgets(self):
        """Crée les éléments du toast"""
        
        # Container principal
        self.configure(height=self.TOAST_HEIGHT)
        
        # === ICÔNE DE SUCCÈS ===
        icon_frame = ctk.CTkFrame(
            self,
            fg_color="transparent",
            width=50,
            height=50
        )
        icon_frame.pack(side="left", padx=(20, 0), pady=10)
        icon_frame.pack_propagate(False)
        
        # Cercle blanc pour l'icône
        icon_bg = ctk.CTkFrame(
            icon_frame,
            fg_color="#FFFFFF",
            corner_radius=25,
            width=50,
            height=50
        )
        icon_bg.pack(fill="both", expand=True)
        icon_bg.pack_propagate(False)
        
        # Essayer de charger l'icône check
        check_icon = self._load_check_icon(size=(28, 28))
        
        if check_icon:
            icon_label = ctk.CTkLabel(
                icon_bg,
                image=check_icon,
                text=""
            )
            icon_label.place(relx=0.5, rely=0.5, anchor="center")
            self._check_icon_img = check_icon  # Garder référence
        else:
            # Fallback: checkmark Unicode
            icon_label = ctk.CTkLabel(
                icon_bg,
                text="✓",
                font=ctk.CTkFont(family="Segoe UI", size=28, weight="bold"),
                text_color=self.TOAST_BG
            )
            icon_label.place(relx=0.5, rely=0.5, anchor="center")
        
        # === MESSAGE ===
        message_frame = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )
        message_frame.pack(side="left", fill="both", expand=True, padx=(15, 20), pady=10)
        
        self.message_label = ctk.CTkLabel(
            message_frame,
            text=self.message,
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color=self.TEXT_COLOR,
            anchor="w",
            justify="left"
        )
        self.message_label.pack(fill="both", expand=True)
        
        # === BOUTON FERMER (X) ===
        close_btn = ctk.CTkButton(
            self,
            text="✕",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color=self.TEXT_COLOR,
            fg_color="transparent",
            hover_color="#059669",
            width=40,
            height=40,
            corner_radius=20,
            command=self.hide
        )
        close_btn.pack(side="right", padx=(0, 15), pady=10)
        
        # Calculer la largeur nécessaire
        self.update_idletasks()
        text_width = len(self.message) * 8 + 150  # Estimation approximative
        toast_width = max(self.TOAST_MIN_WIDTH, min(text_width, self.TOAST_MAX_WIDTH))
        self.configure(width=toast_width)
    
    def _load_check_icon(self, size=(28, 28)):
        """Charge l'icône de check depuis les assets"""
        if not self.icons_dir:
            return None
        
        # Chercher différentes variantes
        candidates = [
            "check.png",
            "check-circle.png",
            "check_blue.png",
        ]
        
        for name in candidates:
            path = os.path.join(self.icons_dir, name)
            if os.path.exists(path):
                try:
                    img = Image.open(path).convert("RGBA")
                    
                    # Redimensionner
                    img = img.resize(size)
                    
                    # Convertir en vert (pour correspondre au toast)
                    pixels = img.load()
                    for i in range(img.size[0]):
                        for j in range(img.size[1]):
                            r, g, b, a = pixels[i, j]
                            if a > 128:  # Si pas transparent
                                # Remplacer par la couleur du toast
                                pixels[i, j] = (16, 185, 129, a)  # #10B981
                    
                    ctk_img = ctk.CTkImage(light_image=img, size=size)
                    return ctk_img
                    
                except Exception as e:
                    print(f"Erreur chargement icône {name}: {e}")
        
        return None
    
    def _find_icons_directory(self):
        """Trouve le répertoire des icônes"""
        possible_paths = [
            os.path.join(os.path.dirname(__file__), "..", "assets", "icons"),
            os.path.join(os.path.dirname(__file__), "..", "..", "assets", "icons"),
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "assets", "icons"),
            "assets/icons",
            "../assets/icons",
            "../../assets/icons",
            "../../../assets/icons",
        ]
        
        for path in possible_paths:
            abs_path = os.path.abspath(path)
            if os.path.exists(abs_path):
                return abs_path
        
        return None
    
    def _bind_events(self):
        """Bind les événements hover"""
        def on_enter(event):
            self._is_hovering = True
            self.configure(fg_color=self.TOAST_BG_HOVER)
        
        def on_leave(event):
            self._is_hovering = False
            self.configure(fg_color=self.TOAST_BG)
        
        self.bind("<Enter>", on_enter)
        self.bind("<Leave>", on_leave)
        
        # Bind récursivement sur tous les enfants
        for child in self.winfo_children():
            child.bind("<Enter>", on_enter)
            child.bind("<Leave>", on_leave)
            if hasattr(child, 'winfo_children'):
                for subchild in child.winfo_children():
                    subchild.bind("<Enter>", on_enter)
                    subchild.bind("<Leave>", on_leave)
    
    def show(self, final_y=30):
        """
        Affiche le toast avec animation slide-in depuis le haut
        
        Args:
            final_y: Position Y finale (top_padding) - par défaut 30px
        """
        # Forcer la mise à jour pour obtenir les bonnes dimensions
        self.update_idletasks()
        self.parent.update_idletasks()
        
        # Position initiale (hors écran, en haut)
        screen_width = self.parent.winfo_width()
        toast_width = self.winfo_reqwidth()
        
        # Centrage horizontal (utiliser relx au lieu de x absolu)
        # Position de départ (au-dessus de l'écran)
        start_y = -self.TOAST_HEIGHT - 20
        
        # Utiliser relx=0.5 pour centrer, puis ajuster avec anchor
        self.place(relx=0.5, y=start_y, anchor="n")
        
        # Animation slide-in
        self._animate_slide(start_y, final_y, on_complete=self._schedule_hide)
    
    def _animate_slide(self, start_y, end_y, on_complete=None):
        """Anime le toast de start_y à end_y"""
        step = [0]
        total_steps = self.SLIDE_STEPS
        delay = self.SLIDE_DURATION // total_steps
        
        def animate():
            if step[0] <= total_steps:
                # Easing out cubic
                progress = step[0] / total_steps
                ease = 1 - pow(1 - progress, 3)
                
                current_y = start_y + (end_y - start_y) * ease
                
                try:
                    # Maintenir le centrage horizontal avec relx=0.5
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
        """Programme la disparition du toast après la durée spécifiée"""
        # Ne pas cacher si l'utilisateur survole le toast
        def check_and_hide():
            if not self._is_hovering:
                self.hide()
            else:
                # Réessayer dans 500ms
                self._hide_job = self.after(500, check_and_hide)
        
        self._hide_job = self.after(self.duration, check_and_hide)
    
    def hide(self):
        """Cache le toast avec animation slide-out vers le haut"""
        # Annuler les jobs précédents
        if self._hide_job:
            self.after_cancel(self._hide_job)
            self._hide_job = None
        
        if self._slide_job:
            self.after_cancel(self._slide_job)
            self._slide_job = None
        
        # Position actuelle
        current_y = self.winfo_y()
        
        # Position finale (hors écran en haut)
        final_y = -self.TOAST_HEIGHT - 20
        
        # Animation slide-out
        self._animate_slide(current_y, final_y, on_complete=self._destroy_toast)
    
    def _destroy_toast(self):
        """Détruit le widget après l'animation"""
        try:
            self.place_forget()
            self.destroy()
        except Exception:
            pass


# ============================================================
# FONCTION UTILITAIRE POUR AFFICHAGE RAPIDE
# ============================================================

def show_success_toast(parent, message, duration=3000, icons_dir=None, top_padding=30):
    """
    Affiche un toast de succès en haut au centre de la fenêtre
    
    Args:
        parent: Fenêtre parent
        message: Message à afficher
        duration: Durée d'affichage en ms (défaut: 3000)
        icons_dir: Répertoire des icônes
        top_padding: Distance depuis le haut en pixels (défaut: 30)
    """
    # Créer le toast
    toast = SuccessToast(parent, message, duration, icons_dir)
    
    # Afficher avec le top_padding personnalisé
    toast.show(final_y=top_padding)


# ============================================================
# TEST STANDALONE
# ============================================================

if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")
    
    # Fenêtre de test
    root = ctk.CTk()
    root.title("Success Toast Test")
    root.geometry("900x600")
    root.configure(fg_color="#F0F4F9")
    
    # Titre
    title = ctk.CTkLabel(
        root,
        text="SUCCESS TOAST DEMO",
        font=ctk.CTkFont(family="Segoe UI", size=32, weight="bold"),
        text_color="#1E293B"
    )
    title.pack(pady=(80, 10))
    
    subtitle = ctk.CTkLabel(
        root,
        text="Click buttons to see different toast notifications",
        font=ctk.CTkFont(family="Segoe UI", size=14),
        text_color="#9CA3AF"
    )
    subtitle.pack(pady=(0, 60))
    
    # Boutons de test
    btn1 = ctk.CTkButton(
        root,
        text="Show Success Toast (3s)",
        font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
        fg_color="#166FFF",
        hover_color="#1258CC",
        corner_radius=12,
        width=280,
        height=55,
        command=lambda: show_success_toast(
            root, 
            "Equipment added successfully!"
        )
    )
    btn1.pack(pady=10)
    
    btn2 = ctk.CTkButton(
        root,
        text="Show Long Message Toast",
        font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
        fg_color="#10B981",
        hover_color="#059669",
        corner_radius=20,
        width=280,
        height=55,
        command=lambda: show_success_toast(
            root, 
            "Your changes have been saved successfully and synced to the database!"
        )
    )
    btn2.pack(pady=10)
    
    btn3 = ctk.CTkButton(
        root,
        text="Show Short Duration Toast (1.5s)",
        font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
        fg_color="#F59E0B",
        hover_color="#D97706",
        corner_radius=12,
        width=280,
        height=55,
        command=lambda: show_success_toast(
            root, 
            "Quick notification!",
            duration=1500
        )
    )
    btn3.pack(pady=10)
    
    btn4 = ctk.CTkButton(
        root,
        text="Custom Padding (80px from top)",
        font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
        fg_color="#8B5CF6",
        hover_color="#7C3AED",
        corner_radius=12,
        width=280,
        height=55,
        command=lambda: show_success_toast(
            root, 
            "Custom top padding!",
            top_padding=80
        )
    )
    btn4.pack(pady=10)
    
    btn5 = ctk.CTkButton(
        root,
        text="Multiple Toasts Test",
        font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
        fg_color="#EF4444",
        hover_color="#DC2626",
        corner_radius=12,
        width=280,
        height=55,
        command=lambda: [
            show_success_toast(root, "First notification!"),
            root.after(400, lambda: show_success_toast(root, "Second notification!")),
            root.after(800, lambda: show_success_toast(root, "Third notification!"))
        ]
    )
    btn5.pack(pady=10)
    
    # Info
    info = ctk.CTkLabel(
        root,
        text="💡 Hover over the toast to pause auto-hide",
        font=ctk.CTkFont(family="Segoe UI", size=12),
        text_color="#6B7280"
    )
    info.pack(side="bottom", pady=30)
    
    root.mainloop()