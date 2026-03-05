import os
import logging
import sys
import customtkinter as ctk
from PIL import Image, ImageDraw
from datetime import datetime

# Ajouter le chemin racine du projet pour les imports
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from database.database import fetchone
from controllers import map_controller

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

ICONS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "assets", "icons"))


class AddEquipmentWindow(ctk.CTkToplevel):
    """Fenêtre pour ajouter ou modifier un équipement."""

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
        "green": "#10B981",
        "disabled_bg": "#F3F4F6",
        "disabled_text": "#D1D5DB",
        "disabled_slider": "#E5E7EB",
        "error": "#EF4444"
    }

    STATUS_COLORS = {
        "Active": "#10B981",
        "Available": "#3B82F6",
        "Maintenance": "#F59E0B",
        "Lent Out": "#EF4444"
    }

    def __init__(self, parent, on_submit=None, on_update=None, existing_data=None, icons_dir=None, **kwargs):
        """
        Args:
            parent: Fenêtre parente
            on_submit: Callback pour la création (mode ADD)
            on_update: Callback pour la mise à jour (mode EDIT) — reçoit (tool_id, data)
            existing_data: Si fourni, active le mode EDIT avec ces données (dict brut de la DB via "raw")
            icons_dir: Chemin vers les icônes
        """
        super().__init__(parent, **kwargs)

        if icons_dir:
            self.icons_dir = icons_dir
        else:
            self.icons_dir = ICONS_DIR

        # ============================================================
        # MODE DÉTECTION : EDIT si existing_data est fourni, sinon ADD
        # ============================================================
        self.is_edit_mode = existing_data is not None
        self.existing_data = existing_data  # données brutes de la DB (champ "raw")
        self.on_submit = on_submit
        self.on_update = on_update

        # En mode edit, extraire l'ID de l'outil depuis existing_data
        self.editing_tool_id = None
        if self.is_edit_mode and self.existing_data:
            self.editing_tool_id = self.existing_data.get("id")
        # ============================================================

        self.geometry("700x650")
        self.title("")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.after(100, lambda: self.geometry(f"+{700}+{300}"))

        self.configure(fg_color=self.THEME["bg"])

        # Données du formulaire
        self.form_data = {
            "asset_model": "",
            "brand": "",
            "serial_number": "",
            "warranty_date": None,
            "category": "",
            "assigned_area": "",
            "status": "",
            "battery_health": None
        }
        
        # Variables pour les champs
        self.entries = {}
        self.dropdowns = {}
        self.dropdown_frames = {}
        
        # Variable pour le battery health slider
        self.battery_health_var = ctk.IntVar(value=100)
        self.battery_slider = None
        self.battery_value_label = None
        self.battery_container = None
        self.battery_minus_btn = None
        self.battery_plus_btn = None
        self.battery_is_enabled = False

        # Variable pour le message d'erreur du serial number
        self.serial_error_label = None
        self.serial_number_valid = True
        self.serial_validation_job = None

        # Charger les données de capacité des chambres
        try:
            self.facility_data = map_controller.get_facility_data()
            self.room_names = [room["name"] for room in self.facility_data]
            # Créer un dictionnaire pour accès rapide à l'occupation
            self.rooms_info = {room["name"]: {"full": room["max_capacity"] is not None and room["total_items"] >= room["max_capacity"], "current": room["total_items"], "max": room["max_capacity"]} for room in self.facility_data}
        except Exception as e:
            logger.error(f"Failed to load facility data for AddEquipmentWindow: {e}")
            self.room_names = ["CEO BUREAU", "ADMINISTRATION", "SECTION A", "SECTION B", "SECTION C", "MAIN STORAGE", "RECEPTION", "OFFICE 101", "OFFICE 105", "OFFICE 201", "OFFICE 302", "IT SERVER ROOM", "WAREHOUSE", "UNDERGROUND", "SECRET ROOM"]
            self.rooms_info = {}

        self._create_ui()

        # ============================================================
        # EN MODE EDIT : pré-remplir les champs APRÈS la création du UI
        # ============================================================
        if self.is_edit_mode and self.existing_data:
            self._prefill_form()
        # ============================================================
        
        # Bind global click pour retirer le focus des champs
        self.bind("<Button-1>", self._handle_global_click)

    # ============================================================
    # PRÉ-REMPLISSAGE DU FORMULAIRE (Mode Edit)
    # ============================================================
    def _prefill_form(self):
        """Remplir tous les champs avec les données existantes."""
        data = self.existing_data
        if not data:
            return

        logger.info(f"Pre-filling form for edit mode, tool ID: {self.editing_tool_id}")

        # --- Champs texte ---
        # asset_model ← name (colonne DB)
        if "asset_model" in self.entries:
            self.entries["asset_model"].delete(0, "end")
            self.entries["asset_model"].insert(0, data.get("name", ""))

        # brand
        if "brand" in self.entries:
            self.entries["brand"].delete(0, "end")
            self.entries["brand"].insert(0, data.get("brand", ""))

        # serial_number
        if "serial_number" in self.entries:
            self.entries["serial_number"].delete(0, "end")
            self.entries["serial_number"].insert(0, data.get("serial_number", ""))

        # --- Dropdowns ---
        # category ← type (colonne DB)
        category_val = (data.get("type") or "").strip().upper()
        if "category" in self.dropdowns and category_val:
            self.dropdowns["category"].set(category_val)
            # Trigger le callback pour activer/désactiver le slider batterie
            self._on_category_change(category_val)

        # assigned_area ← localisation (colonne DB)
        location_val = (data.get("localisation") or "").strip().upper()
        if "assigned_area" in self.dropdowns and location_val:
            self.dropdowns["assigned_area"].set(location_val)

        # status — normaliser : retirer le "•  " du début si présent
        status_val = (data.get("status") or "").strip().upper()
        # Mapper vers les valeurs du dropdown (ex: "ACTIVE" -> "Active")
        status_map = {
            "ACTIVE": "Active",
            "AVAILABLE": "Available",
            "MAINTENANCE": "Maintenance",
            "LENT OUT": "Lent Out"
        }
        status_display = status_map.get(status_val, status_val)
        if "status" in self.dropdowns and status_display:
            self.dropdowns["status"].set(status_display)

        # --- Date de garantie ---
        warranty_str = data.get("warranty_expiration")
        if warranty_str:
            try:
                # Format attendu de la DB : YYYY-MM-DD
                parts = str(warranty_str).split("-")
                if len(parts) == 3:
                    year, month, day = parts[0], parts[1], parts[2]
                    # Retirer les zéros en début pour le jour
                    day = str(int(day))
                    # Le mois reste sur 2 chiffres (format du dropdown)
                    month = month.zfill(2)

                    day_var = self.entries.get("warranty_date_day")
                    month_var = self.entries.get("warranty_date_month")
                    year_var = self.entries.get("warranty_date_year")

                    if day_var and isinstance(day_var, ctk.StringVar):
                        day_var.set(day)
                    if month_var and isinstance(month_var, ctk.StringVar):
                        month_var.set(month)
                    if year_var and isinstance(year_var, ctk.StringVar):
                        year_var.set(year)
            except Exception as e:
                logger.warning(f"Could not parse warranty date '{warranty_str}': {e}")

        # --- Battery Health ---
        battery_val = data.get("battery_health")
        if battery_val is not None:
            try:
                battery_int = int(battery_val)
                self.battery_health_var.set(battery_int)
                if self.battery_value_label:
                    self.battery_value_label.configure(text=f"{battery_int}%")
            except (ValueError, TypeError):
                pass

        logger.info("Form pre-filled successfully")
    # ============================================================

    def _handle_global_click(self, event):
        """Gérer les clics globaux pour retirer le focus des champs"""
        widget = event.widget
        
        if isinstance(widget, ctk.CTkEntry):
            return
        
        parent = widget
        while parent:
            if isinstance(parent, ctk.CTkEntry):
                return
            try:
                parent = parent.master
            except:
                break
        
        self.focus_set()

    def _create_ui(self):
        self.configure(fg_color=self.THEME["white"])

        # Header avec titre — dynamique selon le mode
        header = ctk.CTkFrame(self, fg_color="transparent", height=60)
        header.pack(fill="x", padx=30, pady=(25, 15))
        header.pack_propagate(False)

        # ============================================================
        # TITRE DYNAMIQUE selon le mode
        # ============================================================
        title_text = "EDIT EQUIPMENT" if self.is_edit_mode else "REGISTER EQUIPMENT"
        # ============================================================

        title_label = ctk.CTkLabel(
            header,
            text=title_text,
            font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"),
            text_color=self.THEME["text_dark"],
            anchor="w"
        )
        title_label.pack(side="left")

        separator = ctk.CTkFrame(self, fg_color=self.THEME["border"], height=1)
        separator.pack(fill="x", padx=30, pady=(0, 20))

        # Scrollable content
        content = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_fg_color="transparent",
            scrollbar_button_color="#CBD5E1",
            scrollbar_button_hover_color="#B3BAC2"
        )
        content.pack(fill="both", expand=True, padx=30, pady=(0, 20))

        # Row 1: Asset Model + Brand
        row1 = ctk.CTkFrame(content, fg_color="transparent")
        row1.pack(fill="x", pady=(0, 20))
        
        self._create_input_field(
            row1, 
            "ASSET MODEL", 
            "asset_model", 
            placeholder="SURFACE PRO",
            side="left",
            width=310
        )
        
        self._create_input_field(
            row1, 
            "BRAND", 
            "brand", 
            placeholder="HP / DELL",
            side="right",
            width=310
        )

        # Row 2: Serial Number + Warranty Date
        row2 = ctk.CTkFrame(content, fg_color="transparent")
        row2.pack(fill="x", pady=(0, 20))
        
        # Serial Number avec message d'erreur
        serial_container = ctk.CTkFrame(row2, fg_color="transparent", width=310)
        serial_container.pack(side="left", padx=(0, 15))
        
        self._create_input_field(
            serial_container, 
            "SERIAL NUMBER", 
            "serial_number", 
            placeholder="Max 9 chars (e.g., 13DZA3)",
            side="top",
            width=310
        )
        
        # Container pour le message d'erreur avec icône
        self.serial_error_container = ctk.CTkFrame(serial_container, fg_color="transparent")
        self.serial_error_container.pack(anchor="w", pady=(5, 0), padx=(10, 0))
        
        # Icône d'alerte
        try:
            alert_icon_path = os.path.join(self.icons_dir, "alert.png")
            alert_icon = ctk.CTkImage(
                light_image=Image.open(alert_icon_path),
                dark_image=Image.open(alert_icon_path),
                size=(14, 14)
            )
            self.serial_error_icon = ctk.CTkLabel(
                self.serial_error_container,
                image=alert_icon,
                text=""
            )
            self.serial_error_icon.pack(side="left", padx=(0, 5))
            self.serial_error_icon.pack_forget()  # Caché par défaut
        except Exception as e:
            logger.warning(f"Could not load alert icon: {e}")
            self.serial_error_icon = None
        
        # Message d'erreur pour serial number (caché par défaut)
        self.serial_error_label = ctk.CTkLabel(
            self.serial_error_container,
            text="",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=self.THEME["error"],
            anchor="w"
        )
        self.serial_error_label.pack(side="left")
        
        
        # Bind pour validation en temps réel
        self.entries["serial_number"].bind("<KeyRelease>", self._on_serial_number_change)
        
        self._create_date_picker(row2, "WARRANTY EXP.", "warranty_date")

        # Row 3: Category + Assigned Area
        row3 = ctk.CTkFrame(content, fg_color="transparent")
        row3.pack(fill="x", pady=(0, 20))
        
        self._create_dropdown_field(
            row3,
            "CATEGORY",
            "category",
            options=["PC", "PRINTER", "PHONE", "STORAGE", "MONITOR", "SERVER"],
            side="left",
            width=310
        )
        
        self._create_dropdown_field(
            row3,
            "ASSIGNED AREA",
            "assigned_area",
            options=self.room_names,
            side="right",
            width=310
        )

        # Row 4: Status + Battery Health
        row4 = ctk.CTkFrame(content, fg_color="transparent")
        row4.pack(fill="x", pady=(0, 20))
        
        self._create_dropdown_field(
            row4,
            "STATUS",
            "status",
            options=["Active", "Available", "Maintenance", "Lent Out"],
            side="left",
            width=310
        )
        
        self._create_battery_slider(row4)

        # Separator bottom
        separator_bottom = ctk.CTkFrame(self, fg_color=self.THEME["border"], height=1)
        separator_bottom.pack(fill="x", padx=30, pady=(0, 20))

        # Bottom buttons
        bottom = ctk.CTkFrame(self, fg_color="transparent", height=60)
        bottom.pack(fill="x", padx=30, pady=(0, 25))
        bottom.pack_propagate(False)

        # Bouton Cancel
        cancel_btn = ctk.CTkButton(
            bottom,
            text="CANCEL",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color="#FEF2F2",
            hover_color="#FEE5E5",
            text_color="#DD2A2A",
            border_width=1.5,
            border_color="#FEE5E5",
            corner_radius=16,
            width=140,
            height=54,
            command=self._cancel
        )
        cancel_btn.pack(side="left")

        # Bouton Reset
        reset_btn = ctk.CTkButton(
            bottom,
            text="RESET",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color="#F7F9FB",
            hover_color="#EFEFF2",
            text_color="#6B7280",
            corner_radius=16,
            width=140,
            height=54,
            border_color=self.THEME["border"],
            border_width=1.5,
            command=self._reset
        )
        reset_btn.pack(side="left", padx=(10, 0))

        # ============================================================
        # BOUTON PRINCIPAL : texte dynamique selon le mode
        # ============================================================
        confirm_text = "SAVE CHANGES" if self.is_edit_mode else "CONFIRM ENTRY"
        # ============================================================

        confirm_btn = ctk.CTkButton(
            bottom,
            text=confirm_text,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color=self.THEME["primary"],
            hover_color=self.THEME["primary_hover"],
            text_color=self.THEME["white"],
            corner_radius=16,
            width=340,
            height=54,
            command=self._submit
        )
        confirm_btn.pack(side="right")
        
        # Binding Enter key pour confirmer
        self.bind("<Return>", lambda e: self._submit())
        self.bind("<KP_Enter>", lambda e: self._submit())

    # ============================================================
    # VALIDATION DU SERIAL NUMBER
    # ============================================================
    def _validate_serial_length(self):
        """Valider la longueur du serial number (max 9 caractères)"""
        serial = self.entries["serial_number"].get().strip()
        
        # Vérifier si la longueur dépasse 9 caractères (sans compter #ID)
        if len(serial) > 9:
            self._show_serial_error("Serial ID must not exceed 9 characters (total: 11 with #ID)")
            return False
        else:
            # Effacer seulement si ce n'est pas une erreur d'unicité
            if self.serial_number_valid:
                self._clear_serial_error()
            return True
    
    def _on_serial_number_change(self, event=None):
        """Callback appelé quand le serial number change - validation en temps réel"""
        # Annuler la validation précédente si elle existe
        if self.serial_validation_job is not None:
            try:
                self.after_cancel(self.serial_validation_job)
            except:
                pass
        
        # Validation immédiate de la longueur
        self._validate_serial_length()
        
        # Délai de 500ms avant de valider l'unicité (pour éviter de valider à chaque frappe)
        self.serial_validation_job = self.after(500, self._validate_serial_number)
    
    def _validate_serial_number(self):
        """Valider le serial number en base de données"""
        serial = self.entries["serial_number"].get().strip()
        
        # Vérifier d'abord la longueur avant l'unicité
        if len(serial) > 9:
            self._show_serial_error("Serial ID must not exceed 9 characters (total: 11 with #ID)")
            self.serial_number_valid = False
            return
        
        # Effacer le message d'erreur si le champ est vide
        if not serial:
            self._clear_serial_error()
            self.serial_number_valid = True
            return
        
        try:
            # Vérifier si le serial number existe déjà en base
            # NOTE: Adaptez cette requête selon votre schéma de base de données
            # Je suppose que la table s'appelle "tools" ou "equipment" avec une colonne "serial_number"
            
            if self.is_edit_mode and self.editing_tool_id:
                # En mode édition, exclure l'outil actuel de la vérification
                result = fetchone(
                    """
                    SELECT id FROM tools 
                    WHERE serial_number = ? AND id != ?
                    """,
                    (serial, self.editing_tool_id)
                )
            else:
                # En mode ajout, vérifier simplement l'existence
                result = fetchone(
                    """
                    SELECT id FROM tools 
                    WHERE serial_number = ?
                    """,
                    (serial,)
                )
            
            if result is not None:
                # Serial number existe déjà
                self._show_serial_error("Serial number already exists")
                self.serial_number_valid = False
            else:
                # Serial number disponible
                self._clear_serial_error()
                self.serial_number_valid = True
                
        except Exception as e:
            logger.error(f"Error validating serial number: {e}")
            # En cas d'erreur, on considère que c'est valide pour ne pas bloquer l'utilisateur
            self._clear_serial_error()
            self.serial_number_valid = True
    
    def _show_serial_error(self, message):
        """Afficher le message d'erreur pour le serial number avec bordure rouge"""
        if self.serial_error_label:
            self.serial_error_label.configure(text=message, font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"))
        
        # Changer la bordure du champ en rouge
        if "serial_number" in self.entries:
            self.entries["serial_number"].configure(
                border_color=self.THEME["error"],
                border_width=2
            )
        
        # Afficher l'icône d'alerte si elle existe
        if hasattr(self, 'serial_error_icon') and self.serial_error_icon:
            try:
                self.serial_error_icon.pack(side="left", padx=(0, 5))
            except:
                pass
    
    def _clear_serial_error(self):
        """Effacer le message d'erreur pour le serial number et remettre la bordure normale"""
        if self.serial_error_label:
            self.serial_error_label.configure(text="")
        
        # Remettre la bordure normale
        if "serial_number" in self.entries:
            self.entries["serial_number"].configure(
                border_color=self.THEME["border"],
                border_width=1.5
            )
        
        # Cacher l'icône d'alerte si elle existe
        if hasattr(self, 'serial_error_icon') and self.serial_error_icon:
            try:
                self.serial_error_icon.pack_forget()
            except:
                pass
    # ============================================================

    # ============================================================
    # Battery Health Slider
    # ============================================================
    def _create_battery_slider(self, parent):
        """Créer un slider pour la santé de la batterie (à droite de Status)"""
        self.battery_container = ctk.CTkFrame(parent, fg_color="transparent", width=310)
        self.battery_container.pack(side="right")

        # Label avec icône batterie
        label_frame = ctk.CTkFrame(self.battery_container, fg_color="transparent")
        label_frame.pack(anchor="w", pady=(0, 8), padx=(10, 0))

        # Icône batterie
        try:
            battery_icon_path = os.path.join(self.icons_dir, "battery.png")
            battery_icon = ctk.CTkImage(
                light_image=Image.open(battery_icon_path),
                dark_image=Image.open(battery_icon_path),
                size=(14, 14)
            )
            icon_label = ctk.CTkLabel(
                label_frame,
                image=battery_icon,
                text=""
            )
            icon_label.pack(side="left", padx=(0, 5))
        except Exception as e:
            logger.warning(f"Could not load battery icon: {e}")

        label_widget = ctk.CTkLabel(
            label_frame,
            text="SANTÉ BATTERIE (%)",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=self.THEME["label_text"],
            anchor="w"
        )
        label_widget.pack(side="left")

        # Container pour le slider et les boutons
        slider_container = ctk.CTkFrame(
            self.battery_container,
            fg_color=self.THEME["input_bg"],
            corner_radius=16,
            border_width=1.5,
            border_color=self.THEME["border"],
            height=80,
            width=310
        )
        slider_container.pack(fill="x")
        slider_container.pack_propagate(False)

        self.battery_value_label = ctk.CTkLabel(
            slider_container,
            text="100%",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=self.THEME["disabled_text"],
            anchor="center"
        )
        self.battery_value_label.place(relx=0.5, rely=0.25, anchor="center")

        # Bouton MOINS avec icône
        try:
            minus_icon_path = os.path.join(self.icons_dir, "minus.png")
            minus_icon = ctk.CTkImage(
                light_image=Image.open(minus_icon_path),
                dark_image=Image.open(minus_icon_path),
                size=(14, 14)
            )
            self.battery_minus_btn = ctk.CTkButton(
                slider_container,
                image=minus_icon,
                text="",
                width=30,
                height=30,
                corner_radius=8,
                fg_color="transparent",
                hover_color="#F3F4F6",
                border_width=1.5,
                border_color=self.THEME["disabled_text"],
                command=self._decrease_battery,
                state="disabled"
            )
        except Exception as e:
            logger.warning(f"Could not load minus icon: {e}")
            self.battery_minus_btn = ctk.CTkButton(
                slider_container,
                text="–",
                width=30,
                height=30,
                corner_radius=8,
                fg_color="transparent",
                hover_color="#F3F4F6",
                border_width=1.5,
                border_color=self.THEME["disabled_text"],
                text_color=self.THEME["disabled_text"],
                font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
                command=self._decrease_battery,
                state="disabled"
            )
        self.battery_minus_btn.place(relx=0.08, rely=0.65, anchor="center")
        
        # Bouton PLUS avec icône
        try:
            plus_icon_path = os.path.join(self.icons_dir, "plus.png")
            plus_icon = ctk.CTkImage(
                light_image=Image.open(plus_icon_path),
                dark_image=Image.open(plus_icon_path),
                size=(14, 14)
            )
            self.battery_plus_btn = ctk.CTkButton(
                slider_container,
                image=plus_icon,
                text="",
                width=30,
                height=30,
                corner_radius=8,
                fg_color="transparent",
                hover_color="#F3F4F6",
                border_width=1.5,
                border_color=self.THEME["disabled_text"],
                command=self._increase_battery,
                state="disabled"
            )
        except Exception as e:
            logger.warning(f"Could not load plus icon: {e}")
            self.battery_plus_btn = ctk.CTkButton(
                slider_container,
                text="+",
                width=30,
                height=30,
                corner_radius=8,
                fg_color="transparent",
                hover_color="#F3F4F6",
                border_width=1.5,
                border_color=self.THEME["disabled_text"],
                text_color=self.THEME["disabled_text"],
                font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
                command=self._increase_battery,
                state="disabled"
            )
        self.battery_plus_btn.place(relx=0.92, rely=0.65, anchor="center")

        self.battery_slider = ctk.CTkSlider(
            slider_container,
            from_=0,
            to=100,
            number_of_steps=100,
            variable=self.battery_health_var,
            command=self._on_battery_change,
            progress_color=self.THEME["disabled_slider"],
            button_color=self.THEME["disabled_slider"],
            button_hover_color=self.THEME["disabled_slider"],
            height=10,
            width=200,
            state="disabled"
        )
        self.battery_slider.place(relx=0.5, rely=0.65, anchor="center")

        # Par défaut désactivé
        self.battery_is_enabled = False
    
    def _on_battery_change(self, value):
        """Callback quand le slider change"""
        if not self.battery_is_enabled:
            return
        int_value = int(value)
        self.battery_value_label.configure(text=f"{int_value}%")
    
    def _decrease_battery(self):
        """Diminuer la valeur de la batterie de 1%"""
        if not self.battery_is_enabled:
            return
        current = self.battery_health_var.get()
        new_value = max(0, current - 1)
        self.battery_health_var.set(new_value)
        self._on_battery_change(new_value)
    
    def _increase_battery(self):
        """Augmenter la valeur de la batterie de 1%"""
        if not self.battery_is_enabled:
            return
        current = self.battery_health_var.get()
        new_value = min(100, current + 1)
        self.battery_health_var.set(new_value)
        self._on_battery_change(new_value)
    
    def _set_battery_enabled(self, enabled):
        """Activer ou désactiver le slider de batterie"""
        self.battery_is_enabled = enabled
        
        if enabled:
            if self.battery_slider:
                self.battery_slider.configure(
                    state="normal",
                    progress_color=self.THEME["green"],
                    button_color=self.THEME["green"],
                    button_hover_color="#0EA574"
                )
            if self.battery_minus_btn:
                self.battery_minus_btn.configure(
                    state="normal",
                    border_color=self.THEME["border"],
                    text_color=self.THEME["text_medium"]
                )
            if self.battery_plus_btn:
                self.battery_plus_btn.configure(
                    state="normal",
                    border_color=self.THEME["border"],
                    text_color=self.THEME["text_medium"]
                )
            if self.battery_value_label:
                self.battery_value_label.configure(text_color=self.THEME["green"])
        else:
            if self.battery_slider:
                self.battery_slider.configure(
                    state="disabled",
                    progress_color=self.THEME["disabled_slider"],
                    button_color=self.THEME["disabled_slider"],
                    button_hover_color=self.THEME["disabled_slider"]
                )
            if self.battery_minus_btn:
                self.battery_minus_btn.configure(
                    state="disabled",
                    border_color=self.THEME["disabled_text"],
                    text_color=self.THEME["disabled_text"]
                )
            if self.battery_plus_btn:
                self.battery_plus_btn.configure(
                    state="disabled",
                    border_color=self.THEME["disabled_text"],
                    text_color=self.THEME["disabled_text"]
                )
            if self.battery_value_label:
                self.battery_value_label.configure(text_color=self.THEME["disabled_text"])
    
    def _on_category_change(self, category):
        """Callback quand la catégorie change - active/désactive le slider de batterie"""
        if category.upper() in ["PC", "PHONE"]:
            self._set_battery_enabled(True)
            logger.info(f"Battery slider ENABLED for category: {category}")
        else:
            self._set_battery_enabled(False)
            self.battery_health_var.set(100)
            self._on_battery_change(100)
            logger.info(f"Battery slider DISABLED for category: {category}")
    # ============================================================

    def _create_input_field(self, parent, label, key, placeholder="", side="left", width=230):
        """Créer un champ de saisie texte avec focus/blur effects."""
        container = ctk.CTkFrame(parent, fg_color="transparent", width=width)
        if side == "left":
            container.pack(side="left", padx=(0, 15))
        elif side == "right":
            container.pack(side="right")
        else:  # top
            container.pack(side="top", fill="x")
        
        label_widget = ctk.CTkLabel(
            container,
            text=label,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=self.THEME["label_text"],
            anchor="w"
        )
        label_widget.pack(anchor="w", pady=(0, 17), padx=(10,0))
        
        entry = ctk.CTkEntry(
            container,
            width=width,
            height=50,
            corner_radius=16,
            fg_color=self.THEME["input_bg"],
            border_width=1.5,
            border_color=self.THEME["border"],
            text_color=self.THEME["text_dark"],
            placeholder_text=placeholder,
            placeholder_text_color=self.THEME["text_gray"],
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")
        )
        entry.pack()
        
        def on_focus_in(event):
            entry.configure(border_color=self.THEME["primary"], border_width=2.3)
        
        def on_focus_out(event):
            entry.configure(border_color=self.THEME["border"], border_width=1)
        
        entry.bind("<FocusIn>", on_focus_in)
        entry.bind("<FocusOut>", on_focus_out)
        
        # Bind pour effacer l'erreur quand on tape
        def on_key_release(event):
            self._clear_field_error(key)
        
        entry.bind("<KeyRelease>", on_key_release)
        
        self.entries[key] = entry
    
    def _clear_field_error(self, field_key):
        """Effacer l'erreur d'un champ spécifique"""
        if field_key in self.entries:
            entry = self.entries[field_key]
            entry.configure(border_color=self.THEME["border"], border_width=1)
        
        if hasattr(self, f"{field_key}_error_container"):
            try:
                container = getattr(self, f"{field_key}_error_container")
                container.destroy()
                delattr(self, f"{field_key}_error_container")
                if hasattr(self, f"{field_key}_error_label"):
                    delattr(self, f"{field_key}_error_label")
            except:
                pass

    def _create_dropdown_field(self, parent, label, key, options, side="left", width=230):
        """Créer un champ dropdown avec style moderne et focus effects."""
        container = ctk.CTkFrame(parent, fg_color="transparent", width=width)
        if side == "left":
            container.pack(side="left", padx=(0, 15))
        else:
            container.pack(side="right")
        
        label_widget = ctk.CTkLabel(
            container,
            text=label,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=self.THEME["label_text"],
            anchor="w"
        )
        label_widget.pack(anchor="w", pady=(0, 8), padx=(10,0))
        
        dropdown_frame = ctk.CTkFrame(
            container,
            width=width,
            height=50,
            corner_radius=16,
            fg_color="#F7F9FB",
            border_width=1.5,
            border_color=self.THEME["border"]
        )
        dropdown_frame.pack()
        dropdown_frame.pack_propagate(False)
        
        self.dropdown_frames[key] = dropdown_frame
        
        selected_var = ctk.StringVar(value="SELECT OPTION")
        
        # Point de couleur pour le statut sélectionné
        selected_dot = {"widget": None}
        if key == "status":
            def update_selected_dot(*args):
                option = selected_var.get()
                if selected_dot["widget"]:
                    selected_dot["widget"].destroy()
                    selected_dot["widget"] = None
                
                color = self.STATUS_COLORS.get(option)
                if color:
                    selected_dot["widget"] = ctk.CTkFrame(
                        dropdown_frame,
                        width=8,
                        height=8,
                        corner_radius=4,
                        fg_color=color
                    )
                    selected_dot["widget"].place(relx=0.05, rely=0.5, anchor="center")
                    selected_label.place(relx=0.1, rely=0.5, anchor="w")
                    
                    # S'assurer que le point ne bloque pas les clics
                    selected_dot["widget"].bind("<Button-1>", toggle_dropdown)
                else:
                    selected_label.place(relx=0.05, rely=0.5, anchor="w")
            
            selected_var.trace_add("write", update_selected_dot)

        selected_label = ctk.CTkLabel(
            dropdown_frame,
            textvariable=selected_var,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=self.THEME["text_gray"],
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
        except Exception as e:
            logger.warning(f"Could not load chevron icon: {e}")
            arrow_label = ctk.CTkLabel(
                dropdown_frame,
                text="▼",
                font=ctk.CTkFont(size=10),
                text_color=self.THEME["text_gray"]
            )
            arrow_label.place(relx=0.92, rely=0.5, anchor="center")
        
        popup_window = {"window": None}
        
        def set_focus():
            dropdown_frame.configure(border_color=self.THEME["primary"], border_width=2)
        
        def remove_focus():
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
            
            list_width = width - 100 if key == "status" else width - 50
            
            option_height = 32
            calculated_height = len(options) * option_height + 16
            max_height = 160
            actual_height = min(calculated_height, max_height)
            
            scroll_frame = ctk.CTkScrollableFrame(
                popup_container,
                fg_color=self.THEME["white"],
                width=list_width,
                height=actual_height,
                scrollbar_button_color="#CBD5E1",
                scrollbar_button_hover_color="#9CA3AF"
            )
            scroll_frame.pack(padx=(8, 2), pady=8)
            
            def select_option(option):
                selected_var.set(option)
                selected_label.configure(text_color=self.THEME["text_dark"])
                popup.destroy()
                popup_window["window"] = None
                remove_focus()
                
                # Effacer l'erreur du dropdown si elle existe
                if hasattr(self, f"{key}_error_container"):
                    try:
                        container = getattr(self, f"{key}_error_container")
                        container.destroy()
                        delattr(self, f"{key}_error_container")
                        if hasattr(self, f"{key}_error_label"):
                            delattr(self, f"{key}_error_label")
                    except:
                        pass
                
                # Callback pour catégorie
                if key == "category":
                    self._on_category_change(option)
            
            for option in options:
                # ============================================================
                # En mode edit : highlight l'option actuellement sélectionnée
                # ============================================================
                is_current = (selected_var.get() == option)
                
                # Vérifier si la zone est pleine (seulement pour ASSIGNED AREA)
                is_full = False
                if key == "assigned_area" and hasattr(self, "rooms_info"):
                    info = self.rooms_info.get(option)
                    if info and info["full"]:
                        is_full = True
                
                # Définir les couleurs selon le statut
                if is_current:
                    fg_color = self.THEME["primary"]
                    text_color = self.THEME["white"]
                    hover_color = self.THEME["primary_hover"]
                elif is_full:
                    fg_color = "transparent"
                    text_color = self.THEME["error"]  # Rouge pour les zones pleines
                    hover_color = "#FEE2E2" # Rouge très clair au hover
                else:
                    fg_color = "transparent"
                    text_color = self.THEME["text_dark"]
                    hover_color = "#F3F4F6"
                
                # Ajouter des espaces au texte si c'est le champ status pour laisser de la place au point
                display_text = option + (" (FULL)" if is_full else "")
                if key == "status":
                    display_text = "     " + display_text
                
                option_btn = ctk.CTkButton(
                    scroll_frame,
                    text=display_text,
                    font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                    fg_color=fg_color,
                    hover_color=hover_color,
                    text_color=text_color,
                    anchor="w",
                    height=32,
                    corner_radius=8,
                    cursor="no" if is_full else "hand2",
                    command=lambda opt=option: select_option(opt) if not is_full else None
                )
                
                # Ajouter un point de couleur si c'est le champ status
                if key == "status":
                    color = self.STATUS_COLORS.get(option, "#9CA3AF")
                    dot = ctk.CTkFrame(
                        option_btn,
                        width=8,
                        height=8,
                        corner_radius=4,
                        fg_color=color
                    )
                    dot.place(relx=0.06, rely=0.5, anchor="center")
                    # S'assurer que le point ne bloque pas les clics
                    dot.bind("<Button-1>", lambda e, opt=option: select_option(opt) if not is_full else None)
                
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
        
        self.dropdowns[key] = selected_var

    def _create_date_picker(self, parent, label, key):
        """Créer un sélecteur de date avec dropdowns modernes."""
        container = ctk.CTkFrame(parent, fg_color="transparent", width=310)
        container.pack(side="right")
        
        label_frame = ctk.CTkFrame(container, fg_color="transparent")
        label_frame.pack(anchor="w", pady=(0, 0))
        
        try:
            calendar_icon_path = os.path.join(self.icons_dir, "calendar.png")
            calendar_icon = ctk.CTkImage(
                light_image=Image.open(calendar_icon_path),
                dark_image=Image.open(calendar_icon_path),
                size=(14, 14)
            )
            icon_label = ctk.CTkLabel(
                label_frame,
                image=calendar_icon,
                text=""
            )
            icon_label.pack(side="left", padx=(0, 5))
        except Exception as e:
            logger.warning(f"Could not load calendar icon: {e}")
        
        label_widget = ctk.CTkLabel(
            label_frame,
            text=label,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=self.THEME["label_text"],
            anchor="w"
        )
        label_widget.pack(side="left")
        
        date_frame = ctk.CTkFrame(container, fg_color="transparent")
        date_frame.pack(fill="x")
        
        day_var = ctk.StringVar(value=str(datetime.now().day))
        month_var = ctk.StringVar(value=f"{datetime.now().month:02d}")
        year_var = ctk.StringVar(value=str(datetime.now().year + 1))
        
        self._create_mini_dropdown(date_frame, "DAY", day_var, [str(i) for i in range(1, 32)], width=80, side="left", padx=(0, 10))
        
        self._create_mini_dropdown(date_frame, "MONTH", month_var, [f"{i:02d}" for i in range(1, 13)], width=80, side="left", padx=(0, 10))
        
        current_year = datetime.now().year
        year_options = [str(year) for year in range(current_year, current_year + 11)]
        self._create_mini_dropdown(date_frame, "YEAR", year_var, year_options, width=110, side="left")
        
        self.entries[f"{key}_day"] = day_var
        self.entries[f"{key}_month"] = month_var
        self.entries[f"{key}_year"] = year_var
    
    def _create_mini_dropdown(self, parent, label_text, variable, options, width, side="left", padx=(0, 0)):
        """Créer un mini dropdown pour la date avec focus effects."""
        container = ctk.CTkFrame(parent, fg_color="transparent")
        container.pack(side=side, padx=padx)
        
        label = ctk.CTkLabel(
            container,
            text=label_text,
            font=ctk.CTkFont(family="Segoe UI", size=9, weight="bold"),
            text_color=self.THEME["text_gray"]
        )
        label.pack(pady=(0,0))
        
        dropdown_frame = ctk.CTkFrame(
            container,
            width=width,
            height=50,
            corner_radius=16,
            fg_color="#F7F9FB",
            border_width=1.5,
            border_color=self.THEME["border"]
        )
        dropdown_frame.pack()
        dropdown_frame.pack_propagate(False)
        
        value_label = ctk.CTkLabel(
            dropdown_frame,
            textvariable=variable,
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color=self.THEME["text_medium"]
        )
        value_label.place(relx=0.5, rely=0.5, anchor="center")
        
        popup_window = {"window": None}
        
        def set_focus():
            dropdown_frame.configure(border_color=self.THEME["primary"], border_width=2)
        
        def remove_focus():
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
                corner_radius=16,
                border_width=1,
                border_color="#E5E7EB"
            )
            popup_container.pack(padx=2, pady=2)
            
            scroll_frame = ctk.CTkScrollableFrame(
                popup_container,
                fg_color=self.THEME["white"],
                width=width - 15,
                height=min(160, len(options) * 32),
                scrollbar_button_color="#CBD5E1",
                scrollbar_button_hover_color="#9CA3AF"
            )
            scroll_frame.pack(padx=(4, 2), pady=4)
            
            def select_option(option):
                variable.set(option)
                popup.destroy()
                popup_window["window"] = None
                remove_focus()
            
            for option in options:
                is_selected = (variable.get() == option)
                
                option_btn = ctk.CTkButton(
                    scroll_frame,
                    text=option,
                    font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                    fg_color=self.THEME["primary"] if is_selected else "transparent",
                    hover_color=self.THEME["primary_hover"] if is_selected else "#F3F4F6",
                    text_color=self.THEME["white"] if is_selected else self.THEME["text_dark"],
                    corner_radius=8,
                    height=32,
                    command=lambda opt=option: select_option(opt)
                )
                option_btn.pack(fill="x", pady=2, padx=4)
            
            popup.update_idletasks()
            popup.geometry(f"+{x}+{y}")
            
            def on_popup_click(e):
                try:
                    if popup.winfo_exists():
                        widget = e.widget
                        if widget not in [dropdown_frame, value_label]:
                            popup.destroy()
                            popup_window["window"] = None
                            remove_focus()
                except:
                    pass
            
            popup.after(100, lambda: popup.bind_all("<Button-1>", on_popup_click, add="+"))
            popup.focus_force()
        
        dropdown_frame.bind("<Button-1>", toggle_dropdown)
        value_label.bind("<Button-1>", toggle_dropdown)
        
        dropdown_frame.configure(cursor="hand2")
        value_label.configure(cursor="hand2")

    def _get_form_data(self):
        """Récupérer toutes les données du formulaire."""
        data = {}
        
        for key, entry in self.entries.items():
            if not key.endswith(("_day", "_month", "_year")):
                data[key] = entry.get().strip()
            elif key.endswith(("_day", "_month", "_year")):
                if isinstance(entry, ctk.StringVar):
                    continue
        
        for key, var in self.dropdowns.items():
            if isinstance(var, ctk.StringVar):
                value = var.get()
                if value != "SELECT OPTION":
                    data[key] = value
                else:
                    data[key] = ""
        
        try:
            day_var = self.entries.get("warranty_date_day")
            month_var = self.entries.get("warranty_date_month")
            year_var = self.entries.get("warranty_date_year")
            
            if day_var and month_var and year_var:
                day = day_var.get() if isinstance(day_var, ctk.StringVar) else day_var.get().strip()
                month = month_var.get() if isinstance(month_var, ctk.StringVar) else month_var.get().strip()
                year = year_var.get() if isinstance(year_var, ctk.StringVar) else year_var.get().strip()
                
                if day and month and year:
                    data["warranty_date"] = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                else:
                    data["warranty_date"] = ""
        except Exception as e:
            logger.warning(f"Error parsing warranty date: {e}")
            data["warranty_date"] = ""
        
        # Battery health : inclure uniquement si catégorie PC ou PHONE
        category = data.get("category", "").upper()
        if category in ["PC", "PHONE"]:
            data["battery_health"] = self.battery_health_var.get()
        else:
            data["battery_health"] = None
        
        return data

    def _validate_form(self):
        """Valider les données du formulaire - affiche les erreurs sous chaque champ."""
        data = self._get_form_data()
        is_valid = True
        
        # Réinitialiser toutes les erreurs
        self._clear_all_field_errors()
        
        # Valider Asset Model
        if not data.get("asset_model"):
            self._show_field_error("asset_model", "Asset Model is required")
            is_valid = False
        
        # Valider Brand
        if not data.get("brand"):
            self._show_field_error("brand", "Brand is required")
            is_valid = False
        
        # Valider Serial Number (utilise _show_serial_error pour éviter les doublons)
        serial = data.get("serial_number", "")
        if not serial:
            self._show_serial_error("Serial Number is required")
            is_valid = False
        elif len(serial) > 9:
            self._show_serial_error("Serial ID must not exceed 9 characters (total: 11 with #ID)")
            is_valid = False
        elif not self.serial_number_valid:
            self._show_serial_error("Serial Number already exists")
            is_valid = False
        
        # Valider Category
        if not data.get("category"):
            self._show_dropdown_error("category", "Category is required")
            is_valid = False
        
        # Valider Assigned Area et Capacité
        area = data.get("assigned_area")
        if not area:
            self._show_dropdown_error("assigned_area", "Area is required")
            is_valid = False
        elif hasattr(self, "rooms_info"):
            info = self.rooms_info.get(area)
            if info and info["full"]:
                # En mode EDIT, on autorise si la localisation n'a pas changé
                # (car l'outil occupe déjà une place)
                is_same_location = False
                if self.is_edit_mode and self.existing_data:
                    old_loc = (self.existing_data.get("localisation") or "").strip().upper()
                    if old_loc == area.upper():
                        is_same_location = True
                
                if not is_same_location:
                    self._show_dropdown_error("assigned_area", f"The area {area} is full ({info['current']}/{info['max']})")
                    is_valid = False
        
        # Valider Status
        if not data.get("status"):
            self._show_dropdown_error("status", "Status is required")
            is_valid = False
        
        return is_valid
    
    def _show_field_error(self, field_key, message):
        """Afficher une erreur sous un champ de saisie avec bordure rouge"""
        if field_key in self.entries:
            entry = self.entries[field_key]
            # Changer la bordure en rouge
            entry.configure(border_color=self.THEME["error"], border_width=2)
            
            # Créer ou mettre à jour le label d'erreur
            if not hasattr(self, f"{field_key}_error_label"):
                # Créer le container pour le message d'erreur
                error_container = ctk.CTkFrame(entry.master, fg_color="transparent")
                error_container.pack(anchor="w", pady=(5, 0), padx=(10, 0))
                
                # Icône d'erreur
                try:
                    alert_icon_path = os.path.join(self.icons_dir, "alert.png")
                    alert_icon = ctk.CTkImage(
                        light_image=Image.open(alert_icon_path),
                        dark_image=Image.open(alert_icon_path),
                        size=(14, 14)
                    )
                    icon_label = ctk.CTkLabel(error_container, image=alert_icon, text="")
                    icon_label.pack(side="left", padx=(0, 5))
                except:
                    pass
                
                # Label d'erreur
                error_label = ctk.CTkLabel(
                    error_container,
                    text=message,
                    font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                    text_color=self.THEME["error"],
                    anchor="w"
                )
                error_label.pack(side="left")
                setattr(self, f"{field_key}_error_label", error_label)
                setattr(self, f"{field_key}_error_container", error_container)
            else:
                error_label = getattr(self, f"{field_key}_error_label")
                error_label.configure(text=message)
    
    def _show_dropdown_error(self, field_key, message):
        """Afficher une erreur sous un dropdown avec bordure rouge"""
        if field_key in self.dropdown_frames:
            frame = self.dropdown_frames[field_key]
            # Changer la bordure en rouge
            frame.configure(border_color=self.THEME["error"], border_width=2)
            
            # Créer ou mettre à jour le label d'erreur
            if not hasattr(self, f"{field_key}_error_label"):
                # Créer le container pour le message d'erreur
                error_container = ctk.CTkFrame(frame.master, fg_color="transparent")
                error_container.pack(anchor="w", pady=(5, 0), padx=(10, 0))
                
                # Icône d'erreur
                try:
                    alert_icon_path = os.path.join(self.icons_dir, "alert.png")
                    alert_icon = ctk.CTkImage(
                        light_image=Image.open(alert_icon_path),
                        dark_image=Image.open(alert_icon_path),
                        size=(14, 14)
                    )
                    icon_label = ctk.CTkLabel(error_container, image=alert_icon, text="")
                    icon_label.pack(side="left", padx=(0, 5))
                except:
                    pass
                
                # Label d'erreur
                error_label = ctk.CTkLabel(
                    error_container,
                    text=message,
                    font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                    text_color=self.THEME["error"],
                    anchor="w"
                )
                error_label.pack(side="left")
                setattr(self, f"{field_key}_error_label", error_label)
                setattr(self, f"{field_key}_error_container", error_container)
            else:
                error_label = getattr(self, f"{field_key}_error_label")
                error_label.configure(text=message)
    
    def _clear_all_field_errors(self):
        """Effacer toutes les erreurs des champs (sauf serial_number qui a son propre système)"""
        # Réinitialiser les bordures des champs texte (sauf serial_number)
        for key, entry in self.entries.items():
            if isinstance(entry, ctk.CTkEntry) and key != "serial_number":
                entry.configure(border_color=self.THEME["border"], border_width=1)
        
        # Réinitialiser les bordures des dropdowns
        for key, frame in self.dropdown_frames.items():
            frame.configure(border_color=self.THEME["border"], border_width=1)
        
        # Cacher tous les messages d'erreur (sauf serial_number)
        error_fields = ["asset_model", "brand", "category", "status"]
        for field in error_fields:
            if hasattr(self, f"{field}_error_container"):
                container = getattr(self, f"{field}_error_container")
                try:
                    container.destroy()
                except:
                    pass
                delattr(self, f"{field}_error_container")
                if hasattr(self, f"{field}_error_label"):
                    delattr(self, f"{field}_error_label")

    def _cancel(self):
        """Fermer la fenêtre sans sauvegarder."""
        logger.info("Equipment registration cancelled")
        self.destroy()

    def _reset(self):
        """Réinitialiser tous les champs du formulaire."""
        logger.info("Form reset")
        
        # ============================================================
        # EN MODE EDIT : _reset re-remplit avec les données originales
        # EN MODE ADD  : _reset vide tout comme avant
        # ============================================================
        if self.is_edit_mode and self.existing_data:
            # Vider d'abord
            for key, entry in self.entries.items():
                if not key.endswith(("_day", "_month", "_year")):
                    if isinstance(entry, ctk.CTkEntry):
                        entry.delete(0, "end")
            for key, var in self.dropdowns.items():
                if isinstance(var, ctk.StringVar):
                    var.set("SELECT OPTION")

            # Puis re-remplir avec les données originales
            self._prefill_form()
            logger.info("Form reset to original values (edit mode)")
        else:
            # Mode ADD : réinitialiser classiquement
            for key, entry in self.entries.items():
                if not key.endswith(("_day", "_month", "_year")):
                    if isinstance(entry, ctk.CTkEntry):
                        entry.delete(0, "end")
            
            for key, var in self.dropdowns.items():
                if isinstance(var, ctk.StringVar):
                    var.set("SELECT OPTION")
            
            day_var = self.entries.get("warranty_date_day")
            month_var = self.entries.get("warranty_date_month")
            year_var = self.entries.get("warranty_date_year")
            
            if day_var and isinstance(day_var, ctk.StringVar):
                day_var.set(str(datetime.now().day))
            if month_var and isinstance(month_var, ctk.StringVar):
                month_var.set(f"{datetime.now().month:02d}")
            if year_var and isinstance(year_var, ctk.StringVar):
                year_var.set(str(datetime.now().year + 1))
            
            # Réinitialiser battery health
            self.battery_health_var.set(100)
            self.battery_value_label.configure(text="100%")
            self._set_battery_enabled(False)
            logger.info("Form reset (add mode)")
        
        # Effacer toutes les erreurs visuelles
        self._clear_all_field_errors()
        self._clear_serial_error()
        self.serial_number_valid = True
        # ============================================================

    def _submit(self):
        """Soumettre le formulaire — branche selon le mode."""
        if not self._validate_form():
            return
    
        data = self._get_form_data()
        logger.info(f"Equipment form submitted (mode={'edit' if self.is_edit_mode else 'add'}): {data}")
    
        # ✅ FERMER LA FENÊTRE AVANT d'appeler le callback
        self.destroy()
        
        # ✅ Le callback se charge d'afficher le message de succès
        if self.is_edit_mode:
            if callable(self.on_update):
                try:
                    self.on_update(self.editing_tool_id, data)
                except Exception as e:
                    logger.error(f"Failed to update equipment: {e}")
        else:
            if callable(self.on_submit):
                try:
                    self.on_submit(data)
                except Exception as e:
                    logger.error(f"Failed to add equipment: {e}")
                    
        
        
# Exemple d'utilisation standalone
def main():
    """Test de la fenêtre d'ajout d'équipement"""
    
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.title("Add Equipment Window - Test")
    root.geometry("800x600")
    root.configure(fg_color="#F8FAFC")

    def handle_submit(data):
        """Fonction callback pour gérer la soumission (ADD)"""
        print("\n=== Equipment Registered ===")
        for key, value in data.items():
            print(f"{key}: {value}")

    def handle_update(tool_id, data):
        """Fonction callback pour gérer la mise à jour (EDIT)"""
        print(f"\n=== Equipment Updated (ID: {tool_id}) ===")
        for key, value in data.items():
            print(f"{key}: {value}")
    
    def open_add():
        AddEquipmentWindow(root, on_submit=handle_submit)

    def open_edit():
        # Exemple de données simulées (comme elles viendraient de la DB via "raw")
        fake_existing = {
            "id": 42,
            "name": "Surface Laptop",
            "brand": "Microsoft",
            "serial_number": "SN12345",
            "type": "PC",
            "localisation": "OFFICE 201",
            "status": "ACTIVE",
            "warranty_expiration": "2027-04-25",
            "battery_health": 78,
        }
        AddEquipmentWindow(root, on_update=handle_update, existing_data=fake_existing)

    add_btn = ctk.CTkButton(
        root,
        text="Open ADD Window",
        font=ctk.CTkFont(size=14, weight="bold"),
        height=50,
        command=open_add
    )
    add_btn.pack(pady=10)

    edit_btn = ctk.CTkButton(
        root,
        text="Open EDIT Window (simulated)",
        font=ctk.CTkFont(size=14, weight="bold"),
        height=50,
        command=open_edit
    )
    edit_btn.pack(pady=10)

    root.mainloop()


if __name__ == "__main__":
    main()