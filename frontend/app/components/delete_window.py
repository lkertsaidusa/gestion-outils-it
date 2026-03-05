import os
import logging
import customtkinter as ctk
from PIL import Image

logger = logging.getLogger(__name__)

class DeleteConfirmationWindow(ctk.CTkToplevel):
    """Fenêtre de confirmation de suppression moderne avec icône."""

    THEME = {
        "bg": "#F8F9FA",
        "white": "#FFFFFF",
        "danger": "#EF4444",
        "danger_hover": "#DC2626",
        "text_dark": "#1E293B",
        "text_gray": "#64748B",
        "cancel_bg": "#F1F5F9",
        "cancel_hover": "#E2E8F0",
        "cancel_text": "#475569",
        "icon_bg": "#FEE2E2",
        "icon_color": "#EF4444"
    }

    def __init__(self, parent, title="Delete article", message="Are you sure you want to delete this article?", 
                 subtitle="This action cannot be undone.", on_confirm=None, icons_dir=None, **kwargs):
        """
        Args:
            parent: Fenêtre parente
            title: Titre de la fenêtre
            message: Message principal
            subtitle: Message secondaire
            on_confirm: Callback appelé lors de la confirmation
            icons_dir: Chemin vers le dossier d'icônes
        """
        super().__init__(parent, **kwargs)

        self.on_confirm = on_confirm
        self.icons_dir = icons_dir or os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "assets", "icons"))

        # Configuration de la fenêtre
        self.geometry("520x370")
        self.title("")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        # Centrer la fenêtre
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 500) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 250) // 2
        self.geometry(f"+{x}+{y}")

        self.configure(fg_color=self.THEME["white"])

        self._create_ui(title, message, subtitle)

    def _create_ui(self, title, message, subtitle):
        """Créer l'interface utilisateur"""
        
        # Container principal
        main_container = ctk.CTkFrame(self, fg_color=self.THEME["white"], corner_radius=24)
        main_container.pack(fill="both", expand=True, padx=25, pady=25)

        # Icône d'alerte avec fond circulaire
        icon_container = ctk.CTkFrame(
            main_container,
            fg_color=self.THEME["icon_bg"],
            width=80,
            height=80,
            corner_radius=40
        )
        icon_container.pack(pady=(20, 20))
        icon_container.pack_propagate(False)

        # Charger l'icône d'alerte
        try:
            alert_icon_path = os.path.join(self.icons_dir, "alert-circle.png")
            if not os.path.exists(alert_icon_path):
                # Essayer avec triangle-alert si alert-circle n'existe pas
                alert_icon_path = os.path.join(self.icons_dir, "triangle-alert.png")
            
            alert_icon = ctk.CTkImage(
                light_image=Image.open(alert_icon_path),
                dark_image=Image.open(alert_icon_path),
                size=(36, 36)
            )
            icon_label = ctk.CTkLabel(
                icon_container,
                image=alert_icon,
                text=""
            )
            icon_label.place(relx=0.5, rely=0.5, anchor="center")
        except Exception as e:
            logger.warning(f"Could not load alert icon: {e}")
            # Fallback: utiliser un "!" en texte
            icon_label = ctk.CTkLabel(
                icon_container,
                text="!",
                font=ctk.CTkFont(family="Segoe UI", size=40, weight="bold"),
                text_color=self.THEME["icon_color"]
            )
            icon_label.place(relx=0.5, rely=0.5, anchor="center")

        # Titre
        title_label = ctk.CTkLabel(
            main_container,
            text=title,
            font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"),
            text_color=self.THEME["text_dark"]
        )
        title_label.pack(pady=(0, 8))

        # Message principal
        message_label = ctk.CTkLabel(
            main_container,
            text=message,
            font=ctk.CTkFont(family="Segoe UI", size=14),
            text_color=self.THEME["text_gray"]
        )
        message_label.pack(pady=(0, 2))

        # Sous-titre
        subtitle_label = ctk.CTkLabel(
            main_container,
            text=subtitle,
            font=ctk.CTkFont(family="Segoe UI", size=14),
            text_color=self.THEME["text_gray"]
        )
        subtitle_label.pack(pady=(0, 25))

        # Container pour les boutons
        button_container = ctk.CTkFrame(main_container, fg_color="transparent", height=50)
        button_container.pack(fill="x", padx=10, pady=(0, 15))
        button_container.pack_propagate(False)

        # Bouton Cancel
        cancel_btn = ctk.CTkButton(
            button_container,
            text="Cancel",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            fg_color=self.THEME["cancel_bg"],
            hover_color=self.THEME["cancel_hover"],
            text_color=self.THEME["cancel_text"],
            corner_radius=12,
            width=220,
            height=50,
            command=self._cancel
        )
        cancel_btn.pack(side="left", padx=(0, 10))

        # Bouton Delete
        delete_btn = ctk.CTkButton(
            button_container,
            text="Delete",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            fg_color=self.THEME["danger"],
            hover_color=self.THEME["danger_hover"],
            text_color=self.THEME["white"],
            corner_radius=12,
            width=220,
            height=50,
            command=self._confirm
        )
        delete_btn.pack(side="left")

        # Focus sur le bouton Cancel par défaut (sécurité)
        cancel_btn.focus_set()

        # Bind ESC pour annuler
        self.bind("<Escape>", lambda e: self._cancel())

    def _cancel(self):
        """Annuler et fermer la fenêtre"""
        logger.info("Delete operation cancelled")
        self.destroy()

    def _confirm(self):
        """Confirmer la suppression"""
        logger.info("Delete operation confirmed")
        
        # Appeler le callback si fourni
        if callable(self.on_confirm):
            try:
                self.on_confirm()
            except Exception as e:
                logger.error(f"Error in delete confirmation callback: {e}")
        
        # Fermer la fenêtre
        self.destroy()


# Exemple d'utilisation standalone
def main():
    """Test de la fenêtre de confirmation de suppression"""
    
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.title("Delete Window - Test")
    root.geometry("800x600")
    root.configure(fg_color="#F8FAFC")

    def handle_delete():
        """Fonction callback pour gérer la confirmation de suppression"""
        print("\n=== ITEM DELETED ===")
        print("The item has been successfully deleted!")

    def open_delete_window():
        DeleteConfirmationWindow(
            root,
            title="Delete equipment",
            message="Are you sure you want to delete this equipment?",
            subtitle="This action cannot be undone.",
            on_confirm=handle_delete
        )

    def open_article_delete():
        DeleteConfirmationWindow(
            root,
            title="Delete article",
            message="Are you sure you want to delete this article?",
            subtitle="This action cannot be undone.",
            on_confirm=handle_delete
        )

    def open_user_delete():
        DeleteConfirmationWindow(
            root,
            title="Delete user",
            message="Are you sure you want to delete this user account?",
            subtitle="All associated data will be permanently removed.",
            on_confirm=handle_delete
        )

    # Boutons de test
    test_label = ctk.CTkLabel(
        root,
        text="Delete Confirmation Window Examples",
        font=ctk.CTkFont(size=20, weight="bold")
    )
    test_label.pack(pady=20)

    equipment_btn = ctk.CTkButton(
        root,
        text="Delete Equipment",
        font=ctk.CTkFont(size=14, weight="bold"),
        height=50,
        width=250,
        command=open_delete_window
    )
    equipment_btn.pack(pady=10)

    article_btn = ctk.CTkButton(
        root,
        text="Delete Article",
        font=ctk.CTkFont(size=14, weight="bold"),
        height=50,
        width=250,
        command=open_article_delete
    )
    article_btn.pack(pady=10)

    user_btn = ctk.CTkButton(
        root,
        text="Delete User",
        font=ctk.CTkFont(size=14, weight="bold"),
        height=50,
        width=250,
        command=open_user_delete
    )
    user_btn.pack(pady=10)

    root.mainloop()


if __name__ == "__main__":
    main()