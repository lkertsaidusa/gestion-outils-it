import os
import logging
import customtkinter as ctk
from PIL import Image, ImageTk, ImageDraw
from datetime import datetime

# Constante pour la compatibilité PIL/Pillow (LANCZOS = 1)
LANCZOS_FILTER = 1  # LANCZOS = 1 dans PIL

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class Header(ctk.CTkFrame):
    ICONS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "assets", "icons"))
    IMAGES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "assets", "images"))

    # Visual tuning
    HEIGHT = 56
    HEADER_BG = "#F0F4F9"

    def __init__(self, parent, on_search=None, on_profile_click=None, on_sidebar_toggle=None, on_notification_click=None, user_role=None, **kwargs):
        super().__init__(parent, **kwargs)

        # Frame configuration
        self.configure(fg_color=self.HEADER_BG, height=self.HEIGHT, corner_radius=0)
        self.grid_columnconfigure(2, weight=1)
        # Notification column (only if CEO)
        self.grid_columnconfigure(3, weight=0)
        # Profile column
        self.grid_columnconfigure(4, weight=0)

        self.on_search = on_search
        self.on_profile_click = on_profile_click
        self.on_sidebar_toggle = on_sidebar_toggle
        self.on_notification_click = on_notification_click
        self.user_role = user_role
        self._images = {}
        self.parent = parent

        self.create_sidebar_toggle()
        self.create_greeting()
        self.create_timer_widget()
        
        # Show notification button only for CEO
        if self.user_role == "CEO":
            self.create_notification_button()
            
        self.create_user_profile()
        
        # Démarrer la mise à jour du timer automatiquement au lancement
        self._start_timer_update()

    def create_notification_button(self):
        """Crée le bouton de notification (cloche) pour le CEO"""
        try:
            bell_icon_normal = self._load_image_candidates(
                self.ICONS_DIR,
                ["bell.png", "bell_black.png"],
                size=(32, 32)
            )
            bell_icon_blue = self._load_image_candidates(
                self.ICONS_DIR,
                ["bell_blue.png"],
                size=(32, 32)
            )
        except Exception:
            bell_icon_normal = None
            bell_icon_blue = None

        btn_size = 50
        btn_radius = 14

        self.notification_btn = ctk.CTkButton(
            self,
            text="",
            image=bell_icon_normal,
            width=btn_size,
            height=btn_size,
            corner_radius=btn_radius,
            fg_color="#FFFFFF",
            hover_color="#FFFFFF",
            border_width=0,
            command=self._on_notification_click
        )
        self.notification_btn.grid(row=0, column=3, padx=(10, 10), pady=14, sticky="e")

        # Bindings pour le hover avec changement d'icône (comme le toggle)
        def on_enter_bell(e):
            if bell_icon_blue:
                self.notification_btn.configure(image=bell_icon_blue)
        
        def on_leave_bell(e):
            if bell_icon_normal:
                self.notification_btn.configure(image=bell_icon_normal)
        
        self.notification_btn.bind("<Enter>", on_enter_bell)
        self.notification_btn.bind("<Leave>", on_leave_bell)

        # Badge de notification (bulle rouge)
        self.notification_badge = ctk.CTkLabel(
            self,
            text="0",
            width=20,
            height=20,
            corner_radius=10,
            fg_color="#EF4444",  # Rouge
            text_color="white",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold")
        )
        # Positionnement sur le bouton (en haut à droite)
        # On utilise place pour le mettre par-dessus le bouton gridé
        self.notification_badge.place(in_=self.notification_btn, relx=1.0, rely=0.0, x=-5, y=5, anchor="center")
        self.notification_badge.place_forget() # Masqué par défaut
        
        self.refresh_notification_badge()

    def refresh_notification_badge(self):
        """Met à jour le nombre de notifications non lues sur le badge"""
        if self.user_role != "CEO":
            return
            
        try:
            from backend import notification_service
            count = notification_service.get_unread_count()
            
            if count > 0:
                # Afficher le badge avec le nombre
                display_text = str(count) if count <= 99 else "99+"
                self.notification_badge.configure(text=display_text)
                self.notification_badge.place(in_=self.notification_btn, relx=1.0, rely=0.0, x=-5, y=5, anchor="center")
                # S'assurer qu'il est au-dessus
                self.notification_badge.lift()
            else:
                # Masquer le badge
                self.notification_badge.place_forget()
        except Exception as e:
            logger.warning(f"Failed to refresh notification badge: {e}")
        
    def _on_notification_click(self):
        """Callback pour le bouton de notification"""
        logger.info("Notification button clicked")
        
        if self.on_notification_click:
            self.on_notification_click()
        else:
            logger.warning("No on_notification_click callback defined")
            
    def _round_image_corners(self, image, radius):
        """Arrondit les coins d'une image PIL."""
        mask = Image.new('L', image.size, 0)
        draw = ImageDraw.Draw(mask)
        draw.rounded_rectangle([(0, 0), image.size], radius=radius, fill=255)

        output = Image.new('RGBA', image.size, (0, 0, 0, 0))
        output.paste(image, (0, 0))
        output.putalpha(mask)

        return output

    def _load_image_candidates(self, directory, candidates, size=None, width=None, round_corners=None):
        for name in candidates:
            p = os.path.join(directory, name)
            if os.path.exists(p):
                try:
                    img = Image.open(p).convert("RGBA")
                    if width:
                        aspect_ratio = img.height / img.width
                        new_height = int(width * aspect_ratio)
                        img = img.resize((width, new_height), LANCZOS_FILTER)
                    elif size:
                        img = img.resize(size, LANCZOS_FILTER)

                    if round_corners:
                        img = self._round_image_corners(img, round_corners)

                    photo = ImageTk.PhotoImage(img)
                    self._images[p] = photo
                    return photo
                except Exception:
                    pass
        return None

    def create_sidebar_toggle(self):
        """Créer le bouton pour réduire/agrandir la sidebar - avec radius visible"""
        # Charger les icônes
        panel_icon_normal = self._load_image_candidates(
            self.ICONS_DIR,
            ["panel-right-open.png", "sidebar-toggle.png"],
            size=(32, 32)
        )
        panel_icon_blue = self._load_image_candidates(
            self.ICONS_DIR,
            ["panel-right-open_blue.png", "sidebar-toggle_blue.png"],
            size=(32, 32)
        )
        
        # Bouton toggle directement dans le header (sans container)
        # Taille 50x50 avec radius 14 pour bien voir les coins arrondis
        btn_size = 50
        btn_radius = 14
        
        if panel_icon_normal:
            self.toggle_btn = ctk.CTkButton(
                self,
                image=panel_icon_normal,
                text="",
                width=btn_size,
                height=btn_size,
                corner_radius=btn_radius,
                fg_color="#FFFFFF",
                hover_color="#FFFFFF",
                border_width=0,
                command=self._on_toggle_click
            )
            
            # Bindings pour le hover avec changement d'icône
            def on_enter_toggle(e):
                if panel_icon_blue:
                    self.toggle_btn.configure(image=panel_icon_blue)
            
            def on_leave_toggle(e):
                self.toggle_btn.configure(image=panel_icon_normal)
            
            self.toggle_btn.bind("<Enter>", on_enter_toggle)
            self.toggle_btn.bind("<Leave>", on_leave_toggle)
        else:
            self.toggle_btn = ctk.CTkButton(
                self,
                text="☰",
                width=btn_size,
                height=btn_size,
                corner_radius=btn_radius,
                fg_color="#FFFFFF",
                hover_color="#FFFFFF",
                border_width=0,
                command=self._on_toggle_click
            )
        
        # Positionnement dans la grille avec padding
        self.toggle_btn.grid(row=0, column=0, padx=(40, 10), pady=14, sticky="w")
        
        # Stocker les icônes pour pouvoir les changer
        self._panel_icon_normal = panel_icon_normal
        self._panel_icon_collapsed = None
        
        # Stocker l'état
        self.sidebar_collapsed = False
    
    def _on_toggle_click(self):
        """Callback quand on clique sur le bouton toggle"""
        self.sidebar_collapsed = not self.sidebar_collapsed
        if self.on_sidebar_toggle:
            self.on_sidebar_toggle(self.sidebar_collapsed)
    
    def update_toggle_icon(self, collapsed):
        """Mettre à jour l'icône selon l'état"""
        self.sidebar_collapsed = collapsed
        
        # Charger l'icône appropriée si pas déjà chargée
        if collapsed:
            if not hasattr(self, '_panel_icon_collapsed') or self._panel_icon_collapsed is None:
                self._panel_icon_collapsed = self._load_image_candidates(
                    self.ICONS_DIR,
                    ["panel-left-open.png"],
                    size=(36, 36)
                )
            icon_to_show = self._panel_icon_collapsed if self._panel_icon_collapsed else self._panel_icon_normal
        else:
            icon_to_show = self._panel_icon_normal
        
        if icon_to_show and self.toggle_btn:
            self.toggle_btn.configure(image=icon_to_show)

    def create_greeting(self):
        """Créer le message de bienvenue à gauche"""
        greeting_frame = ctk.CTkFrame(self, fg_color="transparent")
        greeting_frame.grid(row=0, column=1, padx=(10, 20), pady=14, sticky="w")

        self.greeting_label = ctk.CTkLabel(
            greeting_frame,
            text="Hello Said !",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color="#111827",
            anchor="w"
        )
        self.greeting_label.pack(anchor="w")

    def create_timer_widget(self):
        """Créer le widget timer avec point vert cliquable"""
        timer_col = 2
        
        timer_frame = ctk.CTkFrame(self, fg_color="transparent")
        timer_frame.grid(row=0, column=timer_col, padx=(0, 10), pady=14, sticky="e")
        
        # Frame pour l'heure et le point - CLIQUABLE
        timer_inner = ctk.CTkFrame(timer_frame, fg_color="transparent", cursor="hand2")
        timer_inner.pack(side="left")
        timer_inner.bind("<Button-1>", lambda e: self._toggle_timer_format())
        
        # Point vert (indicateur de synchronisation) - À GAUCHE maintenant
        self.sync_dot = ctk.CTkFrame(
            timer_inner, 
            width=8, 
            height=8, 
            corner_radius=4,
            fg_color="#10b981",  # Vert émeraude
            cursor="hand2"
        )
        self.sync_dot.pack(side="left", padx=(0, 6), pady=(0, 0))
        self.sync_dot.bind("<Button-1>", lambda e: self._toggle_timer_format())
        
        # Label pour l'heure (plus grand) - CLIQUABLE
        self.timer_label = ctk.CTkLabel(
            timer_inner,
            text="00:00:00",
            font=ctk.CTkFont(family="Segoe UI", size=23, weight="bold"),
            text_color="#111827",
            cursor="hand2"
        )
        self.timer_label.pack(side="left")
        self.timer_label.bind("<Button-1>", lambda e: self._toggle_timer_format())
        
        # Format par défaut: 24h
        self.timer_is_24h = True
    
    def _toggle_timer_format(self):
        """Basculer entre le format 24h et AM/PM"""
        self.timer_is_24h = not self.timer_is_24h
        self._update_timer_display()

    def set_timer_format(self, is_24h):
        """Changer le format d'affichage du timer (24h ou AM/PM)"""
        self.timer_is_24h = is_24h
        # Mettre à jour immédiatement l'affichage
        self._update_timer_display()

    def _start_timer_update(self):
        """Démarrer la boucle de mise à jour du timer"""
        self._update_timer()

    def _update_timer(self):
        """Mettre à jour l'affichage de l'heure"""
        try:
            self._update_timer_display()
        except Exception:
            pass
        
        # Programmer la prochaine mise à jour dans 1 seconde
        self.after(1000, self._update_timer)
    
    def _update_timer_display(self):
        """Mettre à jour l'affichage selon le format choisi"""
        if hasattr(self, 'timer_label') and self.timer_label.winfo_exists():
            now = datetime.now()
            if self.timer_is_24h:
                current_time = now.strftime("%H:%M:%S")
            else:
                current_time = now.strftime("%I:%M:%S %p")
            self.timer_label.configure(text=current_time)

    def create_user_profile(self):
        """Créer le container profil cliquable avec hover"""
        # Profile container CLIQUABLE
        # If notification button is shown (CEO), profile should be at column 4, else column 3
        profile_col = 4 if (hasattr(self, 'user_role') and self.user_role == "CEO") else 3
        self.profile_container = ctk.CTkFrame(
            self,
            fg_color="#FFFFFF",
            corner_radius=16,
            border_width=0,
            height=self.HEIGHT,
            cursor="hand2"
        )
        self.profile_container.grid(row=0, column=profile_col, padx=(6, 30), pady=8, sticky="e")
        self.profile_container.grid_propagate(False)
        
        # Fonctions pour gérer le hover - change juste la couleur du texte en bleu
        def on_profile_enter(e):
            self.user_name_label.configure(text_color="#3B82F6")  # Bleu
            self.user_role_label.configure(text_color="#3B82F6")  # Bleu
        
        def on_profile_leave(e):
            self.user_name_label.configure(text_color="#111827")  # Noir
            self.user_role_label.configure(text_color="#7E838B")  # Gris
        
        # Bind du clic et hover sur tout le container
        self.profile_container.bind("<Button-1>", lambda e: self._on_profile_container_click())
        self.profile_container.bind("<Enter>", on_profile_enter)
        self.profile_container.bind("<Leave>", on_profile_leave)

        # Inner layout
        inner = ctk.CTkFrame(self.profile_container, fg_color="transparent", cursor="hand2")
        inner.grid(row=0, column=0, padx=12, pady=0)
        inner.grid_columnconfigure(0, weight=1)
        inner.grid_rowconfigure(0, weight=1)  
        inner.place(relx=0.5, rely=0.5, anchor="center")
        
        # Bind aussi sur le inner frame
        inner.bind("<Button-1>", lambda e: self._on_profile_container_click())
        inner.bind("<Enter>", on_profile_enter)
        inner.bind("<Leave>", on_profile_leave)

        # Fonts: Segoe UI comme demandé
        user_name_font = ctk.CTkFont(family="Segoe UI", size=13, weight="bold")
        user_role_font = ctk.CTkFont(family="Segoe UI", size=11, weight="bold")

        user_info_frame = ctk.CTkFrame(inner, fg_color="transparent", cursor="hand2")
        user_info_frame.grid(row=0, column=0, sticky="nsew")
        user_info_frame.bind("<Button-1>", lambda e: self._on_profile_container_click())
        user_info_frame.bind("<Enter>", on_profile_enter)
        user_info_frame.bind("<Leave>", on_profile_leave)
        
        self.user_name_label = ctk.CTkLabel(
            user_info_frame,
            text="MOHAMED SAID",
            font=user_name_font,
            text_color="#111827",
            height=14,
            cursor="hand2"
        )
        self.user_name_label.pack(anchor="e", pady=(12, 0))
        self.user_name_label.bind("<Button-1>", lambda e: self._on_profile_container_click())
        self.user_name_label.bind("<Enter>", on_profile_enter)
        self.user_name_label.bind("<Leave>", on_profile_leave)

        self.user_role_label = ctk.CTkLabel(
            user_info_frame,
            text="ADMIN",
            font=user_role_font,
            text_color="#7E838B",
            height=12,
            cursor="hand2"
        )
        self.user_role_label.pack(anchor="e", pady=(5, 0))
        self.user_role_label.bind("<Button-1>", lambda e: self._on_profile_container_click())
        self.user_role_label.bind("<Enter>", on_profile_enter)
        self.user_role_label.bind("<Leave>", on_profile_leave)

        avatar_size = 58
        avatar_corner_radius = 14
        avatar_frame = ctk.CTkFrame(
            inner,
            width=avatar_size,
            height=avatar_size,
            corner_radius=12,
            fg_color="transparent",
            border_width=0,
            cursor="hand2"
        )
        avatar_frame.grid(row=0, column=1, padx=(12, 0), sticky="")
        avatar_frame.grid_propagate(False)
        avatar_frame.bind("<Button-1>", lambda e: self._on_profile_container_click())
        avatar_frame.bind("<Enter>", on_profile_enter)
        avatar_frame.bind("<Leave>", on_profile_leave)

        # Charger l'avatar
        self.current_avatar_path = None
        self.avatar_img = self._load_user_avatar(avatar_size, avatar_corner_radius)
        
        if self.avatar_img:
            self.avatar_label = ctk.CTkLabel(
                avatar_frame, 
                image=self.avatar_img, 
                text="",
                fg_color="transparent",
                cursor="hand2"
            )
            self.avatar_label.place(relx=0.5, rely=0.5, anchor="center")
            self.avatar_label.bind("<Button-1>", lambda e: self._on_profile_container_click())
            self.avatar_label.bind("<Enter>", on_profile_enter)
            self.avatar_label.bind("<Leave>", on_profile_leave)
        else:
            self.avatar_label = ctk.CTkLabel(
                avatar_frame, 
                text="🙂", 
                font=ctk.CTkFont(size=20),
                cursor="hand2"
            )
            self.avatar_label.place(relx=0.5, rely=0.5, anchor="center")
            self.avatar_label.bind("<Button-1>", lambda e: self._on_profile_container_click())
            self.avatar_label.bind("<Enter>", on_profile_enter)
            self.avatar_label.bind("<Leave>", on_profile_leave)

    def _load_user_avatar(self, size, corner_radius):
        """Charge l'avatar utilisateur depuis le contrôleur ou les assets."""
        try:
            # Import du contrôleur
            from controllers import settings_controller
            
            # Essayer d'obtenir le chemin de l'avatar personnalisé
            avatar_path = settings_controller.get_user_avatar_path()
            
            if avatar_path and os.path.exists(avatar_path):
                self.current_avatar_path = avatar_path
                return self._load_image_candidates(
                    os.path.dirname(avatar_path),
                    [os.path.basename(avatar_path)],
                    size=(size, size),
                    round_corners=corner_radius
                )
        except Exception as e:
            logger.warning(f"Could not load custom avatar: {e}")
        
        # Fallback sur l'image par défaut
        avatar_img = self._load_image_candidates(
            self.IMAGES_DIR, 
            ["avatar.png", "user.png", "me.png"], 
            size=(size, size),
            round_corners=corner_radius
        )
        
        if avatar_img:
            for name in ["avatar.png", "user.png", "me.png"]:
                p = os.path.join(self.IMAGES_DIR, name)
                if os.path.exists(p):
                    self.current_avatar_path = p
                    break
        
        return avatar_img

    def update_user_info(self, user_data: dict):
        """
        Met à jour les informations utilisateur affichées dans le header.
        
        Args:
            user_data: Dictionnaire contenant first_name, last_name, title, profile_photo, etc.
        """
        try:
            # Mettre à jour le nom
            first_name = user_data.get("first_name", "").upper()
            last_name = user_data.get("last_name", "").upper()
            full_name = f"{first_name} {last_name}".strip()
            
            if full_name:
                self.user_name_label.configure(text=full_name)
                # Mettre à jour aussi le greeting
                first = user_data.get("first_name", "User")
                self.greeting_label.configure(text=f"Hello {first} !")
            
            # Mettre à jour le rôle (si fourni)
            role = user_data.get("role") or user_data.get("title")
            if role:
                self.user_role_label.configure(text=role.upper())
            
            # Mettre à jour l'avatar si un nouveau chemin est fourni
            profile_photo = user_data.get("profile_photo")
            if profile_photo and os.path.exists(profile_photo):
                self.update_avatar(profile_photo)
                
            logger.info(f"Header user info updated: {full_name}")
            
        except Exception as e:
            logger.exception(f"Error updating header user info: {e}")

    def update_avatar(self, image_path: str):
        """
        Met à jour l'avatar affiché dans le header.
        
        Args:
            image_path: Chemin vers la nouvelle image d'avatar
        """
        try:
            if not os.path.exists(image_path):
                logger.warning(f"Avatar path does not exist: {image_path}")
                return
            
            avatar_size = 58
            avatar_corner_radius = 14
            
            # Charger la nouvelle image
            new_avatar = self._load_image_candidates(
                os.path.dirname(image_path),
                [os.path.basename(image_path)],
                size=(avatar_size, avatar_size),
                round_corners=avatar_corner_radius
            )
            
            if new_avatar:
                self.avatar_img = new_avatar
                self.current_avatar_path = image_path
                self.avatar_label.configure(image=self.avatar_img)
                logger.info(f"Avatar updated to: {image_path}")
            
        except Exception as e:
            logger.exception(f"Error updating avatar: {e}")

    def _on_dark_mode_click(self):
        """Callback pour le bouton dark mode"""
        logger.info("Dark mode button clicked")
        print("Dark mode clicked!")
    
    def _on_profile_container_click(self):
        """
        Callback pour le clic sur le profil - Navigation vers Settings
        """
        logger.info("Profile container clicked - Navigating to Settings")
        print("[USER] Clic sur le profil - Navigation vers Settings...")
        
        if self.on_profile_click:
            self.on_profile_click()
        else:
            logger.warning("No on_profile_click callback defined")