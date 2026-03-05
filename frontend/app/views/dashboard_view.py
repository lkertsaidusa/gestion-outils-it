import os
import sys
import logging
from pathlib import Path

import customtkinter as ctk
from PIL import Image, ImageDraw
import math
from app.views.bar_chart import BarChart
from app.views.donut_chart import DonutChart

_project_root = Path(__file__).resolve().parents[3]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Shared icons directory
ICONS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "assets", "icons"))


class DashboardView(ctk.CTkFrame):
    ICONS_DIR = ICONS_DIR

    THEME = {
        "bg": "#F0F4F9",
        "primary": "#166FFF",
        "text_dark": "#1E293B",
        "text_gray": "#9CA3AF",
        "text_medium": "#6B7280",
        "white": "#FFFFFF",
        "card_bg": "#FFFFFF",
        "blue": "#4B9EFF",
        "green": "#10B981",
        "red": "#EF4444",
        "orange": "#F59E0B",
        "light_blue": "#E0F2FE",
        "light_green": "#D1FAE5",
        "light_red": "#FEF2F2",
        "light_orange": "#FFF9F5",
        "item_bg": "#FAFAFA",
        "item_bg_red": "#FEF2F2",
        "item_bg_orange": "#FFF9F5",
        "border_light": "#E5E7EB"
    }

    def __init__(self, parent, on_stat_click=None, **kwargs):
        """
        on_stat_click: callback(filter_type: str)
            Appelé quand on clique une stat card.
            filter_type sera "total", "active", "warranty" ou "lent_out".
        """
        super().__init__(parent, **kwargs)
        self.configure(fg_color=self.THEME["bg"], corner_radius=0)
        self.pack(fill="both", expand=True)
        self._icon_cache = {}
        self._hovered_scroll_frame = None # To track which scrollable frame is currently under the mouse
        self._frame_scroll_speed = {} # To store scroll speed for each frame

        # ============================================================
        # STOCKER LE CALLBACK
        # ============================================================
        self.on_stat_click = on_stat_click
        
        # Bind global mousewheel event to DashboardView
        self.bind("<MouseWheel>", self._on_global_mousewheel)

        # ============================================================

        # Créer un scrollable frame pour tout le contenu
        self.scroll_container = ctk.CTkScrollableFrame(
            self,
            fg_color=self.THEME["bg"],
            scrollbar_fg_color=self.THEME["bg"],
            scrollbar_button_color="#CBD5E1",
            scrollbar_button_hover_color=self.THEME["text_gray"]
        )
        self.scroll_container.pack(fill="both", expand=True)
        self._configure_scrollable_widget(self.scroll_container, scroll_speed_divisor=20) # Configure main scroll container

        # Charger les vraies données depuis la base de données
        self._load_dashboard_data()

        # Créer l'interface
        self._create_ui()

    def _load_dashboard_data(self):
        """Charge les données depuis la base de données via le controller"""
        try:
            from controllers import dashboard_controller as dash_ctrl
            
            # Charger toutes les données
            self.stats = dash_ctrl.get_overview_stats()
            self.equipment_distribution = dash_ctrl.get_bar_chart_data(limit=12)
            self.status_breakdown = dash_ctrl.get_donut_chart_data()
            self.battery_hub_items = dash_ctrl.get_battery_hub_items(threshold=80, limit=10)
            self.repair_hub_items = dash_ctrl.get_repair_hub_items(limit=10)
            self.critical_supplies = dash_ctrl.get_critical_supplies(limit=5)
            self.intelligence_feed = dash_ctrl.get_intelligence_feed(limit=10)
            
            logger.info("Dashboard data loaded successfully")
            logger.info(f"Stats: {self.stats}")
            logger.info(f"Equipment distribution: {self.equipment_distribution}")
            logger.info(f"Status breakdown: {self.status_breakdown}")
            
        except Exception as e:
            logger.exception("Failed to load dashboard data")
            # Valeurs par défaut en cas d'erreur
            self.stats = {
                "total_assets": 0,
                "active_units": 0,
                "warranty_alerts": 0,
                "lent_out_assets": 0
            }
            self.equipment_distribution = {}
            self.status_breakdown = []
            self.battery_hub_items = []
            self.repair_hub_items = []
            self.critical_supplies = []
            self.intelligence_feed = []

    def reload_data(self):
        """
        Recharge les données depuis la base et reconstruit l'interface.
        Peut être appelée après des modifications dans l'inventaire.
        """
        logger.info("Reloading dashboard data...")
        
        # Recharger les données
        self._load_dashboard_data()
        
        # Détruire tous les widgets existants dans le scroll container
        for widget in self.scroll_container.winfo_children():
            widget.destroy()
        
        # Reconstruire l'interface
        self._create_ui()
        
        logger.info("Dashboard reloaded successfully")

    def _create_ui(self):
        # Titre
        title_frame = ctk.CTkFrame(self.scroll_container, fg_color="transparent")
        title_frame.pack(fill="x", padx=40, pady=(24, 8))

        title = ctk.CTkLabel(
            title_frame,
            text="Dashboard Overview",
            font=ctk.CTkFont(family="Segoe UI", size=32, weight="bold"),
            text_color=self.THEME["text_dark"],
            anchor="w"
        )
        title.pack(anchor="w")

        subtitle = ctk.CTkLabel(
            title_frame,
            text="EQUIPMENT STATUS",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=self.THEME["primary"],
            anchor="w"
        )
        subtitle.pack(anchor="w", pady=(0, 0), padx=(2,0))

        # Cartes de stats (VRAIES DONNÉES + CLIQUABLES)
        stats_container = ctk.CTkFrame(self.scroll_container, fg_color="transparent")
        stats_container.pack(fill="x", padx=40, pady=(20, 30))

        self._create_stat_card(
            stats_container,
            "TOTAL ASSETS",
            str(self.stats.get("total_assets", 0)),
            "cube",
            self.THEME["blue"],
            self.THEME["light_blue"],
            filter_type="total"
        ).pack(side="left", padx=(0, 15), fill="both", expand=True)

        self._create_stat_card(
            stats_container,
            "ACTIVE UNITS",
            str(self.stats.get("active_units", 0)),
            "check-circle",
            self.THEME["green"],
            self.THEME["light_green"],
            filter_type="active"
        ).pack(side="left", padx=(0, 15), fill="both", expand=True)

        self._create_stat_card(
            stats_container,
            "WARRANTY ALERTS",
            str(self.stats.get("warranty_alerts", 0)),
            "alert",
            self.THEME["red"],
            self.THEME["light_red"],
            filter_type="warranty"
        ).pack(side="left", padx=(0, 15), fill="both", expand=True)

        self._create_stat_card(
            stats_container,
            "LENT OUT ASSETS",
            str(self.stats.get("lent_out_assets", 0)),
            "lent_out",
            self.THEME["red"],
            self.THEME["light_red"],
            filter_type="lent_out"
        ).pack(side="left", fill="both", expand=True)

        # Container pour les graphiques
        charts_container = ctk.CTkFrame(self.scroll_container, fg_color="transparent")
        charts_container.pack(fill="both", expand=True, padx=40, pady=(0, 40))

        # Graphique Equipment Distribution (gauche, 60%) - VRAIES DONNÉES
        dist_card = ctk.CTkFrame(
            charts_container,
            fg_color=self.THEME["white"],
            corner_radius=35,
            width=750,
            height=500
        )
        dist_card.pack(side="left", fill="both", expand=True, padx=(0, 20))
        dist_card.pack_propagate(False)

        dist_title = ctk.CTkLabel(
            dist_card,
            text="EQUIPMENT DISTRIBUTION",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=self.THEME["text_dark"],
            anchor="w"
        )
        dist_title.pack(anchor="w", padx=30, pady=(25, 20))

        # Utiliser la classe BarChart avec VRAIES DONNÉES
        if self.equipment_distribution:
            self.bar_chart = BarChart(
                dist_card, 
                self.equipment_distribution,
                on_bar_click=self._on_bar_click
            )
            self.bar_chart.pack(fill="both", expand=True, padx=30, pady=(10, 30))
        else:
            # Message si aucune donnée
            no_data_label = ctk.CTkLabel(
                dist_card,
                text="No equipment data available",
                font=ctk.CTkFont(family="Segoe UI", size=14),
                text_color=self.THEME["text_gray"]
            )
            no_data_label.pack(fill="both", expand=True, padx=30, pady=30)

        # Graphique Status Breakdown (droite, 40%) - VRAIES DONNÉES
        status_card = ctk.CTkFrame(
            charts_container,
            fg_color=self.THEME["white"],
            corner_radius=35,
            width=500,
            height=500
        )
        status_card.pack(side="right", fill="both", padx=(0, 0))
        status_card.pack_propagate(False)

        status_title = ctk.CTkLabel(
            status_card,
            text="STATUS BREAKDOWN",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=self.THEME["text_dark"],
            anchor="w"
        )
        status_title.pack(anchor="w", padx=30, pady=(25, 20))

        # Utiliser la classe DonutChart avec VRAIES DONNÉES
        if self.status_breakdown:
            self.donut_chart = DonutChart(
                status_card, 
                self.status_breakdown, 
                center_text="GLOBAL ITEMS",
                on_segment_click=self.on_stat_click
            )
            self.donut_chart.pack(fill="both", expand=True, padx=30, pady=(10, 30))
            
            # Légende pour le donut chart (MAINTENANT CLIQUABLE)
            self._create_donut_legend(status_card)
        else:
            # Message si aucune donnée
            no_data_label = ctk.CTkLabel(
                status_card,
                text="No status data available",
                font=ctk.CTkFont(family="Segoe UI", size=14),
                text_color=self.THEME["text_gray"]
            )
            no_data_label.pack(fill="both", expand=True, padx=30, pady=30)

        # Container pour les 4 cartes supplémentaires
        bottom_cards_container = ctk.CTkFrame(self.scroll_container, fg_color="transparent")
        bottom_cards_container.pack(fill="x", padx=40, pady=(0, 40))

        # Battery Hub (VRAIES DONNÉES)
        self._create_battery_hub(bottom_cards_container).pack(side="left", fill="both", expand=True, padx=(0, 15))

        # Repair Hub (VRAIES DONNÉES)
        self._create_repair_hub(bottom_cards_container).pack(side="left", fill="both", expand=True, padx=(0, 15))

        # Critical Supplies (VRAIES DONNÉES)
        self._create_critical_supplies(bottom_cards_container).pack(side="left", fill="both", expand=True, padx=(0, 15))

        # Intelligence Feed (VRAIES DONNÉES)
        self._create_intelligence_feed(bottom_cards_container).pack(side="left", fill="both", expand=True, padx=(0, 15))

    # ============================================================
    # MODIFICATION MAJEURE : Légende cliquable
    # ============================================================
    def _create_donut_legend(self, parent):
        """Créer la légende pour le donut chart en grille 2x2 avec items CLIQUABLES"""
        # Container principal avec grid
        legend_frame = ctk.CTkFrame(parent, fg_color="transparent")
        legend_frame.pack(fill="x", padx=30, pady=(10, 30))

        # Configurer les colonnes pour qu'elles aient la même largeur
        legend_frame.grid_columnconfigure(0, weight=1, uniform="legend")
        legend_frame.grid_columnconfigure(1, weight=1, uniform="legend")

        # Mapper les status vers les filtres d'inventaire
        status_to_filter = {
            "ACTIVE": "active",
            "AVAILABLE": "available",
            "MAINTENANCE": "maintenance",
            "LENT OUT": "lent_out"
        }

        # Créer les items de légende (seulement ceux qui existent)
        row = 0
        col = 0
        for label, value, color in self.status_breakdown:
            # Créer l'item avec callback si on_stat_click existe
            filter_key = status_to_filter.get(label.upper())
            
            legend_item = self._create_legend_item(
                legend_frame, 
                label, 
                value, 
                color,
                filter_key=filter_key  # Passer le filter_key
            )
            
            legend_item.grid(
                row=row, column=col, sticky="ew", 
                padx=(0 if col == 0 else 5, 5 if col == 0 else 0), 
                pady=(0, 10 if row == 0 else 0)
            )
            
            col += 1
            if col > 1:
                col = 0
                row += 1

    def _create_legend_item(self, parent, label, value, color, filter_key=None):
        """
        Créer un item de légende avec son propre container bordé.
        MAINTENANT CLIQUABLE si filter_key est fourni et on_stat_click existe.
        """
        # Container avec bordure
        item = ctk.CTkFrame(
            parent,
            fg_color="#F9FAFB",
            corner_radius=15,
        )
        
        # Contenu interne avec grid pour meilleur contrôle
        content = ctk.CTkFrame(item, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=12, pady=5)
        
        # Configurer grid : colonne 0 pour le contenu gauche, colonne 1 pour la valeur droite
        content.grid_columnconfigure(0, weight=1)
        content.grid_columnconfigure(1, weight=0)
        
        # Frame gauche (point + label)
        left_frame = ctk.CTkFrame(content, fg_color="transparent")
        left_frame.grid(row=0, column=0, sticky="w")
        
        # Point de couleur
        dot = ctk.CTkFrame(left_frame, width=8, height=8, corner_radius=5, fg_color=color)
        dot.pack(side="left", padx=(10, 8))
        dot.pack_propagate(False)
        
        # Label
        text = ctk.CTkLabel(
            left_frame, 
            text=label, 
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=self.THEME["text_medium"], 
            anchor="w"
        )
        text.pack(side="left", padx=(0, 0))
        
        # Valeur (colonne droite, alignée à droite)
        val = ctk.CTkLabel(
            content, 
            text=str(value), 
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=self.THEME["text_medium"], 
            anchor="e"
        )
        val.grid(row=0, column=1, sticky="e", padx=(0, 10))
        
        # ============================================================
        # RENDRE CLIQUABLE si filter_key fourni et callback existe
        # ============================================================
        if filter_key and self.on_stat_click:
            # Couleurs pour le hover
            normal_bg = "#F9FAFB"
            hover_bg = "#EEF4FE"
            
            # Collecter tous les widgets pour binder les events
            all_widgets = [item, content, left_frame, dot, text, val]
            
            def on_click(event=None):
                """Naviguer vers l'inventaire avec le filtre approprié"""
                logger.info(f"Legend item clicked: {label} -> filter: {filter_key}")
                self.on_stat_click(filter_key)
            
            def on_enter(event=None):
                """Effet hover"""
                item.configure(fg_color=hover_bg)
                content.configure(fg_color=hover_bg)
                left_frame.configure(fg_color=hover_bg)
            
            def on_leave(event=None):
                """Retour à la normale"""
                item.configure(fg_color=normal_bg)
                content.configure(fg_color=normal_bg)
                left_frame.configure(fg_color=normal_bg)
            
            # Binder tous les widgets
            for widget in all_widgets:
                widget.configure(cursor="hand2")
                widget.bind("<Button-1>", on_click)
                widget.bind("<Enter>", on_enter)
                widget.bind("<Leave>", on_leave)
        # ============================================================
        
        return item
    # ============================================================

    # ============================================================
    # STAT CARD CLIQUABLE — avec effet lift up
    # ============================================================
    def _create_stat_card(self, parent, label, value, icon_name, color, bg_color, filter_type=None):
        """
        Crée une carte de stats avec effet lift up au hover.
        filter_type: si fourni, la carte sera cliquable et appellera on_stat_click(filter_type).
        """
        # Container pour l'animation lift
        lift_container = ctk.CTkFrame(parent, fg_color="transparent", height=110)
        lift_container.pack_propagate(False)
        
        card = ctk.CTkFrame(
            lift_container,
            fg_color=self.THEME["white"],
            corner_radius=35,
            width=200,
            height=100
        )
        card.place(x=5, y=5, relwidth=1, relheight=1)

        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=(25,25), pady=10)

        # Texte à gauche
        text_frame = ctk.CTkFrame(content, fg_color="transparent")
        text_frame.pack(side="left", fill="both", expand=True)

        label_widget = ctk.CTkLabel(
            text_frame,
            text=label,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=self.THEME["text_gray"],
            anchor="w"
        )
        label_widget.pack(anchor="w", pady=(10,0))

        value_widget = ctk.CTkLabel(
            text_frame,
            text=value,
            font=ctk.CTkFont(family="Segoe UI", size=30, weight="bold"),
            text_color=self.THEME["text_dark"],
            anchor="w"
        )
        value_widget.pack(anchor="w", pady=(0,10))

        # Icône à droite
        icon_container = ctk.CTkFrame(
            content,
            width=56,
            height=56,
            corner_radius=20,
            fg_color=bg_color
        )
        icon_container.pack(side="right")
        icon_container.pack_propagate(False)

        icon_img = self._load_icon_image(icon_name, size=(28, 28))
        if icon_img:
            icon_label = ctk.CTkLabel(
                icon_container,
                image=icon_img,
                text="",
                fg_color=bg_color
            )
            icon_label.place(relx=0.5, rely=0.5, anchor="center")

        # Rendre la carte cliquable si filter_type est fourni
        if filter_type and self.on_stat_click:
            # Collecter tous les widgets pour binder les events
            all_widgets = [lift_container, card, content, text_frame, label_widget, value_widget, icon_container]
            if icon_img:
                all_widgets.append(icon_label)

            # Animation lift up
            LIFT_DISTANCE = 8  # pixels à remonter
            ANIMATION_DURATION = 150  # ms
            
            def on_click(event=None):
                self.on_stat_click(filter_type)

            def animate_lift(target_offset):
                """Anime la carte vers le target_offset"""
                def ease_out_quad(t):
                    return 1 - (1 - t) * (1 - t)
                
                start_offset = getattr(lift_container, '_current_offset', 0)
                start_time = lift_container.winfo_toplevel().winfo_exists() and lift_container.winfo_toplevel().winfo_id()
                
                if start_time:
                    start_ms = lift_container.winfo_toplevel().winfo_exists() and lift_container.winfo_toplevel().winfo_id()
                    
                steps = 10
                step_duration = ANIMATION_DURATION // steps
                current_step = [0]
                
                def step():
                    if current_step[0] <= steps:
                        progress = current_step[0] / steps
                        eased = ease_out_quad(progress)
                        offset = start_offset + (target_offset - start_offset) * eased
                        
                        # Utiliser place avec des valeurs y négatives pour l'effet lift
                        # au lieu de pack_configure qui ne supporte pas les pady négatifs
                        card.place_configure(y=5 - offset)
                        lift_container._current_offset = offset
                        
                        current_step[0] += 1
                        lift_container.after(step_duration, step)
                
                step()

            def on_enter(event=None):
                animate_lift(LIFT_DISTANCE)

            def on_leave(event=None):
                animate_lift(0)

            # Binder sur tous les widgets pour éviter les "trous" du hover
            for widget in all_widgets:
                widget.configure(cursor="hand2")
                widget.bind("<Button-1>", on_click)
                widget.bind("<Enter>", on_enter)
                widget.bind("<Leave>", on_leave)

        return lift_container

    def _create_battery_hub(self, parent):
        """Carte Battery Hub avec batteries dégradées (VRAIES DONNÉES)"""
        card = ctk.CTkFrame(
            parent,
            fg_color=self.THEME["white"],
            corner_radius=28,
            width=300
        )

        # Header
        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=24, pady=(20, 16))

        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.pack(side="left", fill="x", expand=True)

        title = ctk.CTkLabel(
            title_frame,
            text="BATTERY HUB",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=self.THEME["text_dark"],
            anchor="w"
        )
        title.pack(anchor="w", pady=(0, 0))

        subtitle = ctk.CTkLabel(
            title_frame,
            text="DEGRADED CELLS (< 80%)",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color=self.THEME["orange"],
            anchor="w"
        )
        subtitle.pack(anchor="w", pady=(0, 0))

        # Icône batterie dans un container
        icon_container = ctk.CTkFrame(
            header,
            width=44,
            height=44,
            corner_radius=22,
            fg_color=self.THEME["light_orange"]
        )
        icon_container.pack(side="right")
        icon_container.pack_propagate(False)

        battery_icon = self._load_icon_image("battery", size=(22, 22))
        if battery_icon:
            icon_label = ctk.CTkLabel(icon_container, image=battery_icon, text="")
            icon_label.place(relx=0.5, rely=0.5, anchor="center")

        # Liste des batteries (VRAIES DONNÉES depuis la DB)
        if self.battery_hub_items:
            battery_items_container = ctk.CTkScrollableFrame(
                card,
                fg_color="transparent",
                height=150,
                scrollbar_fg_color="white",
                scrollbar_button_color="#CBD5E1",
                scrollbar_button_hover_color="#AABECB"
            )
            battery_items_container.pack(fill="both", expand=True, padx=(0, 8), pady=0)
            self._configure_scrollable_widget(battery_items_container)

            for item in self.battery_hub_items:
                battery_health = item.get("battery_health", 0)
                device_name = (item.get("name") or "UNKNOWN DEVICE").upper()

                item_container = ctk.CTkFrame(
                    battery_items_container,
                    fg_color=self.THEME["item_bg"],
                    corner_radius=20,
                    border_width=1,
                    border_color=self.THEME["border_light"]
                )
                item_container.pack(fill="x", padx=12, pady=(0, 12))

                content_frame = ctk.CTkFrame(item_container, fg_color="transparent")
                content_frame.pack(fill="both", expand=True, padx=18, pady=14)
                
                # Device name et percentage
                info_row = ctk.CTkFrame(content_frame, fg_color="transparent")
                info_row.pack(fill="x", pady=(0, 5))

                device_label = ctk.CTkLabel(
                    info_row,
                    text=device_name[:20],
                    font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                    text_color=self.THEME["text_dark"],
                    anchor="w"
                )
                device_label.pack(side="left")

                percentage_label = ctk.CTkLabel(
                    info_row,
                    text=f"{battery_health}%",
                    font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                    text_color="#F97316" if battery_health >= 70 else self.THEME["red"],  # Orange if close to 80, red if far
                    anchor="e"
                )
                percentage_label.pack(side="right")

                # Barre de progression
                progress_bg = ctk.CTkFrame(content_frame, fg_color="#F3F4F6", height=6, corner_radius=3)
                progress_bg.pack(fill="x", pady=(8, 0))
                progress_bg.pack_propagate(False)

                bar_color = "#F97316" if battery_health >= 70 else self.THEME["red"]  # Orange if close to 80, red if far
                progress_fill = ctk.CTkFrame(
                    progress_bg,
                    fg_color=bar_color,
                    height=6,
                    corner_radius=3
                )
                progress_fill.place(x=0, y=0, relwidth=max(battery_health / 100, 0.05))
        else:
            # Aucune batterie dégradée
            no_data_label = ctk.CTkLabel(
                card,
                text="No degraded batteries found.\nAll batteries are in good condition!",
                font=ctk.CTkFont(family="Segoe UI", size=12),
                text_color=self.THEME["green"],
                justify="center"
            )
            no_data_label.pack(fill="x", padx=30, pady=20)

        # Remarque CRITICALFLOOR en bas
        critical_frame = ctk.CTkFrame(
            card,
            fg_color=self.THEME["light_red"],
            corner_radius=16,
            height=82
        )
        critical_frame.pack(fill="x", padx=20, pady=(10, 20))
        critical_frame.pack_propagate(False)

        critical_content = ctk.CTkFrame(critical_frame, fg_color="transparent")
        critical_content.pack(fill="both", expand=True, padx=15, pady=12)

        # Icône d'alerte à gauche
        alert_icon = self._load_icon_image("alert", size=(24, 24))
        if alert_icon:
            alert_label = ctk.CTkLabel(critical_content, image=alert_icon, text="", fg_color="transparent")
            alert_label.pack(side="left", padx=(0, 12))

        # Textes CRITICALFLOOR et description
        text_frame = ctk.CTkFrame(critical_content, fg_color="transparent")
        text_frame.pack(side="left", fill="both", expand=True)

        # Check if any device is below 60%
        has_critical_battery = any(item.get("battery_health", 100) < 60 for item in self.battery_hub_items)
        
        status_title = "ACTION REQUIRED" if has_critical_battery else "HEALTH STATUS"
        # Même message pédagogique dans les deux cas, pour cohérence visuelle
        status_desc = "Batteries under 60% lose reliability; plan to replace them as soon as possible"

        # Wrap remark text so it fits nicely inside the container
        def _wrap_by_words(text: str, max_words: int = 7) -> str:
            words = text.split()
            lines = []
            for i in range(0, len(words), max_words):
                lines.append(" ".join(words[i:i + max_words]))

            # Évite une dernière ligne avec un seul mot : on "remonte" un mot
            if len(lines) >= 2:
                last = lines[-1].split()
                if len(last) == 1:
                    prev = lines[-2].split()
                    if len(prev) >= 2:
                        # Déplacer le dernier mot de la ligne précédente vers la dernière ligne
                        moved_word = prev.pop()
                        lines[-2] = " ".join(prev)
                        lines[-1] = moved_word + " " + last[0]

            return "\n".join(line for line in lines if line.strip())

        status_desc_wrapped = _wrap_by_words(status_desc, max_words=7)

        ctk.CTkLabel(
            text_frame,
            text=status_title,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=self.THEME["red"],
            anchor="w"
        ).pack(anchor="w")

        ctk.CTkLabel(
            text_frame,
            text=status_desc_wrapped,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="normal"),
            text_color=self.THEME["text_gray"],
            anchor="w",
            justify="left"
        ).pack(anchor="w")

        return card

    def _create_repair_hub(self, parent):
        """Carte Repair Hub avec unités en réparation (VRAIES DONNÉES)"""
        card = ctk.CTkFrame(
            parent,
            fg_color=self.THEME["white"],
            corner_radius=28,
            width=300
        )

        # Header
        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=24, pady=(20, 16))

        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.pack(side="left", fill="x", expand=True)

        title = ctk.CTkLabel(
            title_frame,
            text="REPAIR HUB",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=self.THEME["text_dark"],
            anchor="w"
        )
        title.pack(anchor="w", pady=(0, 0))

        subtitle = ctk.CTkLabel(
            title_frame,
            text="CURRENT REPAIRS",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color=self.THEME["orange"],
            anchor="w"
        )
        subtitle.pack(anchor="w", pady=(0, 0))

        # Icône construction dans un container
        icon_container = ctk.CTkFrame(
            header,
            width=44,
            height=44,
            corner_radius=22,
            fg_color=self.THEME["light_orange"]
        )
        icon_container.pack(side="right")
        icon_container.pack_propagate(False)

        repair_icon = self._load_icon_image("construction", size=(22, 22))
        if repair_icon:
            icon_label = ctk.CTkLabel(icon_container, image=repair_icon, text="")
            icon_label.place(relx=0.5, rely=0.5, anchor="center")

        # Grand texte X UNITS IN REPAIR (VRAIES DONNÉES) avec fond orange très clair
        units_count = len(self.repair_hub_items)
        units_frame = ctk.CTkFrame(card, fg_color=self.THEME["light_orange"], corner_radius=20, height=80)
        units_frame.pack(fill="x", padx=20, pady=(10, 20))
        units_frame.pack_propagate(False)

        units_label = ctk.CTkLabel(
            units_frame,
            text=f"{units_count} UNIT{'S' if units_count != 1 else ''} IN REPAIR",
            font=ctk.CTkFont(family="Segoe UI", size=26, weight="bold"),
            text_color=self.THEME["orange"],
            anchor="w"
        )
        units_label.pack(anchor="w", padx=20, pady=20)

        # Section titre et contenu
        if units_count > 0:
            section_title = ctk.CTkLabel(
                card,
                text="UNITS IN REPAIR",
                font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                text_color=self.THEME["text_gray"],
                anchor="w"
            )
            section_title.pack(anchor="w", padx=30, pady=(0, 12))

            # Liste des réparations (VRAIES DONNÉES depuis la DB)
            repair_items_container = ctk.CTkScrollableFrame(
                card,
                fg_color="transparent",
                height=200,
                scrollbar_fg_color="white",
                scrollbar_button_color="#CBD5E1",
                scrollbar_button_hover_color="#AABECB"
            )
            repair_items_container.pack(fill="both", expand=True, padx=(0, 8), pady=0)
            self._configure_scrollable_widget(repair_items_container)

            for item in self.repair_hub_items:
                device_name = (item.get("name") or "UNKNOWN").upper()
                device_type = (item.get("type") or "").upper()
                serial = item.get("serial_number") or "N/A"
                
                # Estimate repair time based on type
                if "SERVER" in device_name or "SERVER" in device_type:
                    repair_time = "15 DAYS"
                elif "PC" in device_name or "PC" in device_type or "DESKTOP" in device_name:
                    repair_time = "5 DAYS"
                elif "MONITOR" in device_name or "MONITOR" in device_type or "SCREEN" in device_name:
                    repair_time = "2 DAYS"
                elif "PRINTER" in device_name or "PRINTER" in device_type:
                    repair_time = "4 DAYS"
                elif "LAPTOP" in device_name or "LAPTOP" in device_type or "NOTEBOOK" in device_name:
                    repair_time = "6 DAYS"
                elif "PHONE" in device_name:
                    repair_time = "3 DAYS"
                else:
                    repair_time = "7 DAYS"

                item_container = ctk.CTkFrame(
                    repair_items_container,
                    fg_color=self.THEME["white"],
                    corner_radius=20,
                    border_width=1,
                    border_color=self.THEME["border_light"]
                )
                item_container.pack(fill="x", padx=12, pady=(0, 12))

                content_frame = ctk.CTkFrame(item_container, fg_color="transparent")
                content_frame.pack(fill="both", expand=True, padx=18, pady=16)
                content_frame.grid_columnconfigure(0, weight=1)
                content_frame.grid_columnconfigure(1, weight=0)

                # --- Left Side avec icône et info ---
                left_side = ctk.CTkFrame(content_frame, fg_color="transparent")
                left_side.grid(row=0, column=0, sticky="w")
                
                # Icône d'activité en orange
                activity_icon = self._load_icon_image("activity-orange", size=(18, 18))
                icon_label = None
                if activity_icon:
                    icon_label = ctk.CTkLabel(left_side, image=activity_icon, text="", fg_color="transparent")
                    icon_label.pack(side="left", padx=(0, 12))

                info_frame = ctk.CTkFrame(left_side, fg_color="transparent")
                info_frame.pack(side="left")

                device_label = ctk.CTkLabel(info_frame, text=device_name[:18] + "..." if len(device_name) > 18 else device_name, font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), text_color=self.THEME["text_dark"], anchor="w")
                device_label.pack(anchor="w")

                serial_label = ctk.CTkLabel(info_frame, text=f"#{serial}", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color=self.THEME["text_gray"], anchor="w")
                serial_label.pack(anchor="w")
                
                # --- Right Side avec ESTIMATED et durée ---
                right_side = ctk.CTkFrame(content_frame, fg_color="transparent")
                right_side.grid(row=0, column=1, sticky="e")

                eta_title = ctk.CTkLabel(right_side, text="ESTIMATED", font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"), text_color=self.THEME["text_gray"], anchor="e")
                eta_title.pack(anchor="e")

                eta_frame = ctk.CTkFrame(right_side, fg_color="transparent")
                eta_frame.pack(anchor="e")

                # Icône horloge orange
                clock_icon = self._load_icon_image("clock-orange", size=(16, 16))
                if clock_icon:
                    clock_label = ctk.CTkLabel(eta_frame, image=clock_icon, text="", fg_color="transparent")
                    clock_label.pack(side="left", padx=(0, 6))

                eta_label = ctk.CTkLabel(eta_frame, text=repair_time, font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color=self.THEME["orange"], anchor="e")
                eta_label.pack(side="left")
        else:
            # Aucune réparation
            no_repairs_label = ctk.CTkLabel(
                card,
                text="No equipment currently in repair.\nAll systems operational!",
                font=ctk.CTkFont(family="Segoe UI", size=12),
                text_color=self.THEME["green"],
                justify="center"
            )
            no_repairs_label.pack(fill="both", expand=True, padx=30, pady=20)

        # Bouton VIEW MAINTENANCE avec style moderne
        check_btn = ctk.CTkButton(
            card,
            text="VIEW MAINTENANCE  >",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color=self.THEME["white"],
            fg_color="#1F2937",
            hover_color="#374151",
            corner_radius=16,
            height=52,
            command=self._navigate_to_repair_items
        )
        check_btn.pack(fill="x", padx=20, pady=(12, 20))

        return card

    def _create_critical_supplies(self, parent):
        """Carte Critical Supplies avec consommables en rupture (VRAIES DONNÉES)"""
        card = ctk.CTkFrame(
            parent,
            fg_color=self.THEME["white"],
            corner_radius=28,
            width=300
        )

        # Header
        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=24, pady=(20, 16))

        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.pack(side="left", fill="x", expand=True)

        title = ctk.CTkLabel(
            title_frame,
            text="CRITICAL SUPPLIES",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=self.THEME["text_dark"],
            anchor="w"
        )
        title.pack(anchor="w", pady=(0, 0))

        subtitle = ctk.CTkLabel(
            title_frame,
            text="LOW STOCK ALERTS",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color=self.THEME["text_gray"],
            anchor="w"
        )
        subtitle.pack(anchor="w", pady=(0, 0))

        # Icône triangle-alert dans un container
        icon_container = ctk.CTkFrame(
            header,
            width=44,
            height=44,
            corner_radius=22,
            fg_color=self.THEME["light_red"]
        )
        icon_container.pack(side="right")
        icon_container.pack_propagate(False)

        alert_icon = self._load_icon_image("triangle-alert", size=(22, 22))
        if alert_icon:
            icon_label = ctk.CTkLabel(icon_container, image=alert_icon, text="")
            icon_label.place(relx=0.5, rely=0.5, anchor="center")

        # Liste des supplies critiques
        if self.critical_supplies:
            critical_supplies_container = ctk.CTkScrollableFrame(
                card,
                fg_color="transparent",
                height=150,
                scrollbar_fg_color="white",
                scrollbar_button_color="#CBD5E1",
                scrollbar_button_hover_color="#AABECB"
            )
            critical_supplies_container.pack(fill="both", expand=True, padx=(0, 8), pady=0)
            self._configure_scrollable_widget(critical_supplies_container)

            for item in self.critical_supplies:
                name = item.get("name", "UNKNOWN")
                stock = item.get("in_storage", 0)
                limit = item.get("limit_alert", 0)
                
                item_container = ctk.CTkFrame(
                    critical_supplies_container,
                    fg_color=self.THEME["item_bg_red"],
                    corner_radius=20,
                    border_width=1,
                    border_color="#FECACA"
                )
                item_container.pack(fill="x", padx=12, pady=(0, 12))

                content_frame = ctk.CTkFrame(item_container, fg_color="transparent")
                content_frame.pack(fill="both", expand=True, padx=18, pady=14)
                content_frame.grid_columnconfigure(0, weight=1)

                # --- Row 0: Name and Badge ---
                top_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
                top_frame.grid(row=0, column=0, sticky="ew", pady=(0,5))

                item_icon = self._load_icon_image("box-logo", size=(16, 16))
                if item_icon:
                    icon_label = ctk.CTkLabel(top_frame, image=item_icon, text="")
                    icon_label.pack(side="left", padx=(0, 8))

                name_lbl = ctk.CTkLabel(top_frame, text=name[:20], font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"), text_color=self.THEME["text_dark"])
                name_lbl.pack(side="left", anchor="w")

                badge = ctk.CTkFrame(top_frame, fg_color=self.THEME["red"], corner_radius=6)
                badge.pack(side="right", anchor="e")
                badge_label = ctk.CTkLabel(badge, text="LOW", font=ctk.CTkFont(family="Segoe UI", size=9, weight="bold"), text_color="white")
                badge_label.pack(padx=8, pady=2)

                # --- Row 1: "AVAILABLE UNITS" ---
                units_title = ctk.CTkLabel(content_frame, text="AVAILABLE UNITS", font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"), text_color=self.THEME["text_gray"], anchor="w")
                units_title.grid(row=1, column=0, sticky="w", pady=(10, 0))

                # --- Row 2: Count ---
                bottom_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
                bottom_frame.grid(row=2, column=0, sticky="ew")

                count_text = ctk.CTkLabel(bottom_frame, text=f"{stock}", font=ctk.CTkFont(family="Segoe UI", size=30, weight="bold"), text_color=self.THEME["red"])
                count_text.pack(side="left", anchor="w")
                
                limit_text = ctk.CTkLabel(bottom_frame, text=f" / {limit} LIMIT", font=ctk.CTkFont(family="Segoe UI", size=12, weight="normal"), text_color=self.THEME["text_gray"])
                limit_text.pack(side="left", anchor="sw", pady=(0, 5), padx=5)
                
        else:
            # Tout va bien
            ok_label = ctk.CTkLabel(
                card,
                text="All supplies are well stocked.\nNo shortages detected.",
                font=ctk.CTkFont(family="Segoe UI", size=12),
                text_color=self.THEME["green"],
                justify="center"
            )
            ok_label.pack(fill="both", expand=True, padx=30, pady=30)

        # Bouton d'action VIEW MORE
        check_btn = ctk.CTkButton(
            card,
            text="VIEW MORE  >",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=self.THEME["white"],
            fg_color=self.THEME["red"],
            hover_color="#DC2626",
            corner_radius=14,
            height=48,
            command=self._navigate_to_supplies
        )
        check_btn.pack(fill="x", padx=20, pady=(12, 20))

        return card
        
    def _navigate_to_supplies(self):
        """Naviguer vers la vue Supplies"""
        if self.on_stat_click:
            logger.info("Navigating to Supplies view")
            self.on_stat_click("supplies")

    def _create_intelligence_feed(self, parent):
        """Carte Intelligence Feed avec statistiques par localisation (VRAIES DONNÉES)"""
        card = ctk.CTkFrame(
            parent,
            fg_color=self.THEME["white"],
            corner_radius=28,
            width=300
        )

        # Header
        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=24, pady=(20, 12))

        title = ctk.CTkLabel(
            header,
            text="ACTIVE ALERTS",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=self.THEME["text_dark"],
            anchor="w"
        )
        title.pack(side="left")

        # Icône shield-x dans un container
        icon_container = ctk.CTkFrame(
            header,
            width=44,
            height=44,
            corner_radius=22,
            fg_color=self.THEME["light_red"]
        )
        icon_container.pack(side="right")
        icon_container.pack_propagate(False)

        shield_icon = self._load_icon_image("shield-x", size=(22, 22))
        if shield_icon:
            icon_label = ctk.CTkLabel(icon_container, image=shield_icon, text="")
            icon_label.place(relx=0.5, rely=0.5, anchor="center")

        # Sous-titre
        subtitle = ctk.CTkLabel(
            card,
            text="DENSITY VIOLATIONS",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color=self.THEME["red"],
            anchor="w"
        )
        subtitle.pack(anchor="w", padx=24, pady=(0, 16))

        # Afficher les localisations (VRAIES DONNÉES depuis la DB)
        if self.intelligence_feed:
            intelligence_feed_container = ctk.CTkScrollableFrame(
                card,
                fg_color="transparent",
                height=250,
                scrollbar_fg_color="white",
                scrollbar_button_color="#CBD5E1",
                scrollbar_button_hover_color="#AABECB"
            )
            intelligence_feed_container.pack(fill="both", expand=True, padx=(8, 8), pady=(0, 20))
            self._configure_scrollable_widget(intelligence_feed_container)

            for feed_item in self.intelligence_feed:
                location = feed_item.get("location", "UNKNOWN")
                count = feed_item.get("count", 0)
                max_capacity = feed_item.get("max_capacity", 0)
                
                # ============================================================
                # NEW FACTORY FUNCTION
                # ============================================================
                def create_location_card(loc, cnt, max_cap):
                    """Factory function pour créer une carte avec les bons closures"""
                    normal_bg = self.THEME["item_bg_red"]
                    hover_bg = "#FEE2E2"
                    
                    violation_box = ctk.CTkFrame(
                        intelligence_feed_container,
                        fg_color=self.THEME["item_bg_red"],
                        corner_radius=20,
                        cursor="hand2",
                        border_width=1,
                        border_color="#FECACA"
                    )
                    violation_box.pack(fill="x", padx=12, pady=(0, 12))

                    violation_content = ctk.CTkFrame(violation_box, fg_color="transparent")
                    violation_content.pack(fill="both", expand=True, padx=18, pady=14)
                    
                    # GRID layout for content
                    violation_content.grid_columnconfigure(0, weight=1)
                    violation_content.grid_columnconfigure(1, weight=0)

                    # --- Handlers ---
                    def on_click(event=None):
                        if self.on_stat_click: self.on_stat_click(f"map:{loc}")
                    def on_enter(event=None): 
                        violation_box.configure(fg_color=hover_bg)
                        arrow_bg.configure(fg_color="#F3F4F6")  # Gris clair au survol
                    def on_leave(event=None): 
                        violation_box.configure(fg_color=normal_bg)
                        arrow_bg.configure(fg_color="white")  # Retour au blanc
                    
                    # --- Row 0: Location and Badge ---
                    top_frame = ctk.CTkFrame(violation_content, fg_color="transparent")
                    top_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0,5))
                    
                    map_icon = self._load_icon_image("map-pin", size=(14, 14))
                    if map_icon:
                        icon_label = ctk.CTkLabel(top_frame, image=map_icon, text="")
                        icon_label.pack(side="left", padx=(0, 8))

                    location_label = ctk.CTkLabel(
                        top_frame, text=loc.upper()[:12] + "..." if len(loc) > 12 else loc.upper(),
                        font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                        text_color=self.THEME["text_dark"]
                    )
                    location_label.pack(side="left", anchor="w")

                    badge = ctk.CTkFrame(top_frame, fg_color="white", corner_radius=8)
                    badge.pack(side="right", anchor="e")
                    badge_label = ctk.CTkLabel(
                        badge, text="HIGH OCCUPANCY",
                        font=ctk.CTkFont(family="Segoe UI", size=9, weight="bold"),
                        text_color=self.THEME["red"]
                    )
                    badge_label.pack(padx=10, pady=4)
                    
                    # --- Row 1: "TOTAL ASSETS" ---
                    assets_title = ctk.CTkLabel(
                        violation_content, text="TOTAL ASSETS",
                        font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
                        text_color=self.THEME["text_gray"], anchor="w"
                    )
                    assets_title.grid(row=1, column=0, sticky="w", pady=(10, 0))

                    # --- Row 2: Count and Arrow ---
                    bottom_frame = ctk.CTkFrame(violation_content, fg_color="transparent")
                    bottom_frame.grid(row=2, column=0, columnspan=2, sticky="ew")

                    count_text = ctk.CTkLabel(
                        bottom_frame, text=f"{cnt}",
                        font=ctk.CTkFont(family="Segoe UI", size=30, weight="bold"),
                        text_color=self.THEME["red"]
                    )
                    count_text.pack(side="left", anchor="w")
                    
                    max_text = ctk.CTkLabel(
                        bottom_frame, text=f" / {max_cap} MAX",
                        font=ctk.CTkFont(family="Segoe UI", size=12, weight="normal"),
                        text_color=self.THEME["text_gray"]
                    )
                    max_text.pack(side="left", anchor="sw", pady=(0, 5), padx=5)

                    arrow_bg = ctk.CTkFrame(bottom_frame, fg_color="white", corner_radius=12, width=32, height=32)
                    arrow_bg.pack(side="right", anchor="e")
                    arrow_bg.pack_propagate(False)

                    arrow_icon = self._load_icon_image("chevron-left", size=(18, 18))
                    arrow_label = None  # Initialize arrow_label
                    if arrow_icon:
                        arrow_label = ctk.CTkLabel(arrow_bg, image=arrow_icon, text="")
                        arrow_label.place(relx=0.5, rely=0.5, anchor="center")
                        
                    # --- Bind all ---
                    # Conditionally add arrow_label if it exists
                    all_widgets = [violation_box, violation_content, top_frame, icon_label, location_label, badge, badge_label,
                                   assets_title, bottom_frame, count_text, max_text, arrow_bg]
                    if arrow_label:
                        all_widgets.append(arrow_label)
                    for widget in all_widgets:
                        if widget:
                            widget.bind("<Button-1>", on_click)
                            widget.bind("<Enter>", on_enter)
                            widget.bind("<Leave>", on_leave)

                create_location_card(location, count, max_capacity)
               
        else:
            no_data_label = ctk.CTkLabel(
                card, text="No location data available",
                font=ctk.CTkFont(family="Segoe UI", size=12), text_color=self.THEME["text_gray"],
                justify="center"
            )
            no_data_label.pack(fill="x", padx=30, pady=40)

        return card

    def _navigate_to_repair_items(self):
        """Naviguer vers l'inventaire avec filtre MAINTENANCE"""
        if self.on_stat_click:
            logger.info("Navigating to repair items (MAINTENANCE filter)")
            self.on_stat_click("maintenance")
    
    def _on_bar_click(self, category):
        """Naviguer vers l'inventaire avec filtre catégorie"""
        if self.on_stat_click:
            logger.info(f"Bar clicked: {category} -> filter: category:{category}")
            self.on_stat_click(f"category:{category}")

    def _configure_scrollable_widget(self, scrollable_frame, scrollbar_width=16, scroll_speed_divisor=20):
        """Configure un scrollbar de widget avec width normal.
        Gère les événements Enter/Leave pour le scroll conditionnel.
        """
        try:
            scrollbar = scrollable_frame._scrollbar
            
            if scrollbar:
                scrollbar.configure(width=scrollbar_width)
            
            # Store scroll speed for this frame
            self._frame_scroll_speed[scrollable_frame] = scroll_speed_divisor

            # Bind Enter/Leave events to manage the currently hovered frame
            def on_enter(event):
                self._hovered_scroll_frame = scrollable_frame

            def on_leave(event):
                if self._hovered_scroll_frame == scrollable_frame:
                    self._hovered_scroll_frame = None
            
            scrollable_frame.bind("<Enter>", on_enter)
            scrollable_frame.bind("<Leave>", on_leave)
            
            # Also bind to internal canvas to ensure events are captured if mouse moves directly to canvas
            if hasattr(scrollable_frame, '_parent_canvas') and scrollable_frame._parent_canvas:
                scrollable_frame._parent_canvas.bind("<Enter>", on_enter)
                scrollable_frame._parent_canvas.bind("<Leave>", on_leave)
            
        except Exception as e:
            logger.warning(f"Could not configure scrollable widget: {e}")

    def _on_global_mousewheel(self, event):
        """Global mousewheel handler that directs scroll events to the currently hovered frame.
        
        Quand on est dans une frame interne (card), le scroll reste TOUJOURS dans cette frame
        et bloque completement le scroll de la page principale, meme aux limites.
        Le scroll principal ne s'active QUE si le curseur est completement en dehors des cards.
        """
        target_frame = self._hovered_scroll_frame
        
        # Si une frame interne est survolee (n'importe quelle card scrollable)
        # on bloque COMPLETEMENT le scroll principal, peu importe la position
        if target_frame is not None and target_frame != self.scroll_container:
            try:
                canvas = target_frame._parent_canvas
                scroll_speed = self._frame_scroll_speed.get(target_frame, 20)
                
                # Toujours essayer de scroller la frame interne
                # Le canvas lui-meme gerera les limites
                canvas.yview_scroll(int(-1*(event.delta/scroll_speed)), "units")
                
                # TOUJOURS bloquer la propagation pour empecher le scroll principal
                return "break"
            except Exception as e:
                logger.warning(f"Error scrolling target frame {target_frame}: {e}")
                # Meme en cas d'erreur, on bloque la propagation
                return "break"
        
        # Si aucune frame interne n'est survolee, scroller SEULEMENT le main dashboard
        # Ceci ne s'execute QUE si le curseur est completement en dehors des cards
        try:
            canvas = self.scroll_container._parent_canvas
            scroll_speed = self._frame_scroll_speed.get(self.scroll_container, 20)
            canvas.yview_scroll(int(-1*(event.delta/scroll_speed)), "units")
        except Exception as e:
            logger.warning(f"Error scrolling main container: {e}")
        
        return "break"

    def _load_icon_image(self, base_name, size=(84, 84)):
        if not base_name:
            return None

        key = f"{base_name}_{size[0]}x{size[1]}"
        if key in self._icon_cache:
            return self._icon_cache[key]

        candidates = [
            f"{base_name}.png",
            f"{base_name}".replace(" ", "_") + ".png",
            f"{base_name}_icon.png",
            f"{base_name}-icon.png"
        ]

        for name in candidates:
            p = os.path.join(self.ICONS_DIR, name)
            if os.path.exists(p):
                try:
                    img = Image.open(p).convert("RGBA")
                    img = img.resize(size)
                    ctk_img = ctk.CTkImage(light_image=img, size=size)
                    self._icon_cache[key] = ctk_img
                    return ctk_img
                except Exception:
                    logger.exception("Error loading icon %s", p)
                    break

        self._icon_cache[key] = None
        return None


if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.title("Dashboard")
    root.geometry("1400x900")

    view = DashboardView(root)

    root.mainloop()