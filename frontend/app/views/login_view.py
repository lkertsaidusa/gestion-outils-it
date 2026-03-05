import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import os
import sys

# Ajouter le chemin racine du projet pour les imports
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from database.database import fetchone

# Set the appearance mode and color theme
ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")


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


class ScrollingText(ctk.CTkFrame):
    """Widget de texte défilant en boucle infinie"""
    
    def __init__(self, parent, text, font, text_color="#FFFFFF", bg_color="#2D3FE3", speed=2, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.configure(fg_color=bg_color, height=40)
        self.text = text
        self.speed = speed
        self.text_color = text_color
        self.font = font
        
        self.canvas = tk.Canvas(
            self,
            bg=bg_color,
            highlightthickness=0,
            height=40
        )
        self.canvas.pack(fill="both", expand=True)
        
        self.x_pos = 0
        self.text_width = 0
        self.canvas_width = 0
        self.animation_job = None
        
        self.bind("<Configure>", self._on_configure)
        
    def _on_configure(self, event=None):
        self.canvas_width = self.canvas.winfo_width()
        if self.canvas_width > 1:
            self._create_text()
            self._start_animation()
    
    def _create_text(self):
        self.canvas.delete("all")
        
        temp_text = self.canvas.create_text(
            0, 20,
            text=self.text,
            font=self.font,
            fill=self.text_color,
            anchor="w"
        )
        
        bbox = self.canvas.bbox(temp_text)
        if bbox:
            self.text_width = bbox[2] - bbox[0]
        
        self.canvas.delete(temp_text)
        
        self.text_id1 = self.canvas.create_text(
            self.canvas_width, 20,
            text=self.text,
            font=self.font,
            fill=self.text_color,
            anchor="w"
        )
        
        self.text_id2 = self.canvas.create_text(
            self.canvas_width + self.text_width + 100, 20,
            text=self.text,
            font=self.font,
            fill=self.text_color,
            anchor="w"
        )
        
        self.x_pos = self.canvas_width
    
    def _start_animation(self):
        if self.animation_job is not None:
            try:
                self.after_cancel(self.animation_job)
            except:
                pass
        self._animate()
    
    def _animate(self):
        if self.text_width == 0 or self.canvas_width == 0:
            return
        
        self.x_pos -= self.speed
        
        self.canvas.coords(self.text_id1, self.x_pos, 20)
        self.canvas.coords(self.text_id2, self.x_pos + self.text_width + 100, 20)
        
        if self.x_pos + self.text_width < 0:
            self.x_pos = 0
        
        self.animation_job = self.after(30, self._animate)
    
    def stop(self):
        if self.animation_job is not None:
            try:
                self.after_cancel(self.animation_job)
            except:
                pass
            self.animation_job = None

    def destroy(self):
        self.stop()
        super().destroy()


class AnimatedInputField(ctk.CTkFrame):
    """Champ de saisie avec animation de bordure"""
    
    BORDER_COLOR = "#2D3FE3"
    BORDER_WIDTH_FOCUS = 2
    BORDER_WIDTH_NORMAL = 0
    BG_COLOR = "#FFFFFF"
    
    _ANIM_STEPS = 4
    _ANIM_INTERVAL_MS = 12
    
    def __init__(self, parent, placeholder="", is_password=False, icons_dir=None, width=400, height=50, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.configure(fg_color="transparent")
        self.is_password = is_password
        self.field_height = height
        self._images = {}
        
        if icons_dir:
            self.ICONS_DIR = icons_dir
        else:
            self.ICONS_DIR = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..", "assets", "icons")
            )
        
        self._border_anim_job = None
        self._border_progress = 0.0
        self.password_visible = False
        
        self._create_field(placeholder)
    
    def _load_icon(self, candidates, size=(24, 24)):
        for name in candidates:
            path = os.path.join(self.ICONS_DIR, name)
            if os.path.exists(path):
                try:
                    img = Image.open(path).convert("RGBA")
                    img = img.resize(size)
                    photo = ImageTk.PhotoImage(img)
                    self._images[path] = photo
                    return photo
                except Exception as e:
                    print(f"Error loading icon {path}: {e}")
        return None
    
    def _create_field(self, placeholder):
        self.field_frame = ctk.CTkFrame(
            self,
            fg_color=self.BG_COLOR,
            corner_radius=15,
            height=self.field_height,
            border_width=self.BORDER_WIDTH_NORMAL,
            border_color=self.BORDER_COLOR
        )
        self.field_frame.pack(fill="x", expand=True)
        self.field_frame.pack_propagate(False)
        
        inter_font = ctk.CTkFont(family="Inter", size=15)
        show_char = "•" if self.is_password else ""
        
        self.entry = ctk.CTkEntry(
            self.field_frame,
            placeholder_text=placeholder,
            fg_color=self.BG_COLOR,
            border_width=0,
            font=inter_font,
            text_color="#000000",
            placeholder_text_color="#9CA3AF",
            show=show_char
        )
        self.entry.pack(side="left", fill="both", expand=True, padx=15, pady=10)
        
        if self.is_password:
            self.eye_open_icon = self._load_icon(["eye-off.png"], size=(30, 30))
            self.eye_closed_icon = self._load_icon(["eye.png"], size=(30, 30))
            
            if self.eye_open_icon and self.eye_closed_icon:
                self.toggle_btn = ctk.CTkLabel(
                    self.field_frame,
                    image=self.eye_open_icon,
                    text="",
                    cursor="hand2",
                    fg_color=self.BG_COLOR
                )
                self.toggle_btn.pack(side="right", padx=(0, 15))
                self.toggle_btn.bind("<Button-1>", lambda e: self.toggle_password_visibility())
            else:
                self.toggle_btn = ctk.CTkLabel(
                    self.field_frame,
                    text="👁",
                    cursor="hand2",
                    font=ctk.CTkFont(size=16),
                    fg_color=self.BG_COLOR
                )
                self.toggle_btn.pack(side="right", padx=(0, 15))
                self.toggle_btn.bind("<Button-1>", lambda e: self.toggle_password_visibility())
        
        self.entry.bind("<FocusIn>", self._on_focus_in)
        self.entry.bind("<FocusOut>", self._on_focus_out)
        self._set_border_progress(0.0, instant=True)
    
    def _set_border_progress(self, target, instant=False):
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
        p = max(0.0, min(1.0, float(self._border_progress)))
        bw = int(round(self.BORDER_WIDTH_FOCUS * p))
        color = lerp_color(self.BG_COLOR, self.BORDER_COLOR, p)
        
        try:
            self.field_frame.configure(border_width=bw, border_color=color)
        except Exception:
            try:
                self.field_frame.configure(border_width=bw)
            except Exception:
                pass
    
    def _on_focus_in(self, event=None):
        self._set_border_progress(1.0)
    
    def _on_focus_out(self, event=None):
        self._set_border_progress(0.0)
    
    def destroy(self):
        if self._border_anim_job is not None:
            try:
                self.after_cancel(self._border_anim_job)
            except:
                pass
            self._border_anim_job = None
        super().destroy()
    
    def toggle_password_visibility(self):
        if not self.is_password:
            return
        
        if self.password_visible:
            self.entry.configure(show="•")
            if hasattr(self, 'eye_open_icon') and self.eye_open_icon:
                self.toggle_btn.configure(image=self.eye_open_icon)
            else:
                self.toggle_btn.configure(text="👁")
            self.password_visible = False
        else:
            self.entry.configure(show="")
            if hasattr(self, 'eye_closed_icon') and self.eye_closed_icon:
                self.toggle_btn.configure(image=self.eye_closed_icon)
            else:
                self.toggle_btn.configure(text="👁‍🗨")
            self.password_visible = True
    
    def get(self):
        return self.entry.get()
    
    def set(self, text):
        self.entry.delete(0, "end")
        self.entry.insert(0, text)


class LoginApp(ctk.CTk):
    def __init__(self, on_login_success=None):
        """
        on_login_success: callback appelé après connexion réussie.
            Reçoit un dictionnaire contenant les données de l'utilisateur connecté.
        """
        super().__init__()

        self.on_login_success = on_login_success

        # Window configuration
        self.title("Get Started Now - Modern Login")
        self.geometry("1440x900")
        
        self.configure(fg_color="#F3F4F6")
        
        self.bind('<Escape>', lambda e: self.attributes('-fullscreen', False))
        
        self._images = {}

        # Create main container with padding
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=30, pady=30)

        # Create two-column layout (exactly 50/50)
        self.main_container.grid_columnconfigure(0, weight=1, uniform="column")
        self.main_container.grid_columnconfigure(1, weight=1, uniform="column")
        self.main_container.grid_rowconfigure(0, weight=1)

        # --- LEFT PANEL: BRANDING ---
        self.left_frame = ctk.CTkFrame(
            self.main_container, 
            fg_color="#2D3FE3", 
            corner_radius=30
        )
        self.left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 15))

        # Logo
        logo_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "assets", "images", "logo_white.png")
        )
        try:
            if os.path.exists(logo_path):
                logo_image = Image.open(logo_path)
                logo_image.thumbnail((250, 250))
                logo_photo = ctk.CTkImage(light_image=logo_image, dark_image=logo_image, size=logo_image.size)
                
                self.logo_label = ctk.CTkLabel(
                    self.left_frame,
                    image=logo_photo,
                    text=""
                )
                self.logo_label.place(x=40, y=40)
            else:
                print(f"Logo not found at: {logo_path}")
                self.logo_label = ctk.CTkLabel(
                    self.left_frame,
                    text="LOGO",
                    font=("Segoe UI", 24, "bold"),
                    text_color="#FFFFFF"
                )
                self.logo_label.place(x=40, y=40)
        except Exception as e:
            print(f"Error loading logo: {e}")
            self.logo_label = ctk.CTkLabel(
                self.left_frame,
                text="LOGO",
                font=("Segoe UI", 24, "bold"),
                text_color="#FFFFFF"
            )
            self.logo_label.place(x=40, y=40)

        # Slogan
        self.left_content = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        self.left_content.place(x=40, rely=0.3, anchor="w")

        self.slogan = ctk.CTkLabel(
            self.left_content, 
            text="Track it. Own it.", 
            font=("Segoe UI", 52, "bold"), 
            text_color="#FFFFFF",
            justify="left"
        )
        self.slogan.pack(anchor="w", pady=(0, 20))

        self.subtitle = ctk.CTkLabel(
            self.left_content, 
            text="Your IT, under control. Inventory made smart.", 
            font=("Segoe UI", 20, "bold"), 
            text_color="#FFFFFF",
            justify="left"
        )
        self.subtitle.pack(anchor="w", pady=0)

        # Texte défilant
        self.scrolling_text = ScrollingText(
            self.left_frame,
            text="Mohamed Said LKERT  •  Said HOUACINE  •  Mahdi CHIBA    ",
            font=("Segoe UI", 16, "bold"),
            text_color="#FFFFFF",
            bg_color="#2D3FE3",
            speed=2
        )
        self.scrolling_text.place(x=0, rely=1.0, y=-50, relwidth=1.0)

        # --- RIGHT PANEL: LOGIN FORM ---
        self.right_frame = ctk.CTkFrame(
            self.main_container, 
            fg_color="transparent", 
            corner_radius=20
        )
        self.right_frame.grid(row=0, column=1, sticky="nsew", padx=(15, 0))

        self.form_container = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        self.form_container.place(relx=0.5, rely=0.5, anchor="center")

        # Header
        ctk.CTkLabel(
            self.form_container, 
            text="Get Started Now", 
            font=("Segoe UI", 36, "bold"), 
            text_color="#111827"
        ).pack(anchor="w", pady=(0, 8))

        ctk.CTkLabel(
            self.form_container, 
            text="Please log in to your account to continue.", 
            font=("Segoe UI", 15), 
            text_color="#6B7280"
        ).pack(anchor="w", pady=(0, 35))

        # Email
        ctk.CTkLabel(
            self.form_container, 
            text="Email address", 
            font=("Segoe UI", 15, "bold"), 
            text_color="#374151"
        ).pack(anchor="w", pady=(20, 8))
        
        self.email_field = AnimatedInputField(
            self.form_container,
            placeholder="BusinessMail@gmail.com",
            is_password=False,
            width=480,
            height=55
        )
        self.email_field.pack(fill="x")

        # Password
        ctk.CTkLabel(
            self.form_container, 
            text="Password", 
            font=("Segoe UI", 15, "bold"), 
            text_color="#374151"
        ).pack(anchor="w", pady=(20, 8))
        
        self.password_field = AnimatedInputField(
            self.form_container,
            placeholder="••••••••",
            is_password=True,
            width=480,
            height=55
        )
        self.password_field.pack(fill="x")

        # Message d'erreur (caché par défaut)
        self.error_label = ctk.CTkLabel(
            self.form_container,
            text="",
            font=("Segoe UI", 13),
            text_color="#EF4444"
        )
        self.error_label.pack(anchor="w", pady=(12, 0))

        # Login Button
        self.login_button = ctk.CTkButton(
            self.form_container, 
            text="Log in", 
            command=self.handle_login,
            font=("Segoe UI", 17, "bold"),
            fg_color="#2D3FE3",
            hover_color="#2535B8",
            height=55,
            corner_radius=10
        )
        self.login_button.pack(fill="x", pady=(25, 5))

        # Binder Enter pour déclencher le login
        self.password_field.entry.bind("<Return>", lambda e: self.handle_login())

    def _show_error(self, message):
        """Affiche un message d'erreur sous les champs"""
        self.error_label.configure(text=message)

    def _clear_error(self):
        """Cache le message d'erreur"""
        self.error_label.configure(text="")

    def handle_login(self):
        """
        Vérifie les identifiants directement en base de données.
        Requête simple : chercher un utilisateur par email + mot de passe + actif.
        """
        self._clear_error()

        email = self.email_field.get().strip()
        password = self.password_field.get()

        # Validation des champs
        if not email or not password:
            self._show_error("Please fill in all fields.")
            return

        # Désactiver le bouton pendant la vérification
        self.login_button.configure(state="disabled", text="Signing in...")

        try:
            # Requête : chercher l'utilisateur par email, mot de passe en clair, et actif
            user = fetchone(
                """
                SELECT u.id, u.first_name, u.last_name, u.email, u.phone_number,
                       u.date_of_birth, u.address, u.role_id, u.is_active,
                       r.name as role_name
                FROM users u
                JOIN roles r ON u.role_id = r.id
                WHERE u.email = ? AND u.password = ? AND u.is_active = 1;
                """,
                (email, password)
            )

            if user is None:
                # Aucun utilisateur trouvé → identifiants incorrects
                self._show_error("Invalid email or password.")
                self.login_button.configure(state="normal", text="Log in")
                return

            # [OK] Connexion réussie
            print(f"[OK] Login successful: {user['first_name']} {user['last_name']} ({user['role_name']})")

            # Appeler le callback pour passer à l'application principale
            if self.on_login_success:
                self.on_login_success(user)
            else:
                # Si pas de callback, juste afficher un message (mode standalone)
                messagebox.showinfo("Success", f"Logged in as {user['first_name']} {user['last_name']}")
                self.login_button.configure(state="normal", text="Log in")

        except Exception as e:
            import traceback
            traceback.print_exc()
            self._show_error(f"ERROR: {e}")
            self.login_button.configure(state="normal", text="Log in")


if __name__ == "__main__":
    app = LoginApp()
    app.mainloop()