import customtkinter as ctk
import math


class DonutChart(ctk.CTkFrame):
    """
    Widget de graphique en donut interactif avec animation radial sweep premium.
    
    Features:
    - Animation de balayage radial (radial sweep) depuis 12h
    - Tous les segments s'animent simultanément
    - Easing cubic-bezier (ease-out) pour un effet fluide
    - Fade-in du texte central (affichage direct de la valeur, pas d'incrémentation)
    - Animation d'incrémentation UNIQUEMENT au hover entre segments
    - Redimensionnement automatique
    """
    
    # =====================================================================
    # CONFIGURATION VISUELLE
    # =====================================================================
    
    # Couleurs
    BG_COLOR = "white"
    CENTER_CIRCLE_COLOR = "white"
    TEXT_PRIMARY = "#1E293B"
    TEXT_SECONDARY = "#9CA3AF"
    
    # Dimensions (ratios par rapport à la taille du canvas)
    OUTER_RADIUS_RATIO = 0.50
    INNER_RADIUS_RATIO = 0.35
    
    # Espacement entre segments
    GAP_ANGLE = 5  # degrés
    START_ANGLE = 90  # Commence en haut (12h)
    
    # =====================================================================
    # CONFIGURATION ANIMATION RADIAL SWEEP
    # =====================================================================
    
    # Animation principale (balayage radial)
    SWEEP_DURATION_MS = 1200  # Durée totale de l'animation (1.2 secondes)
    SWEEP_FPS = 60  # 60 FPS pour fluidité maximale
    SWEEP_FRAME_DELAY = int(1000 / SWEEP_FPS)  # ~16ms par frame
    
    # Animation du texte central (fade-in)
    TEXT_FADE_START_PROGRESS = 0.3  # Le texte commence à apparaître à 30% de l'animation
    TEXT_MIN_OPACITY_THRESHOLD = 0.05  # Opacité minimale pour rendre le texte visible
    
    # Animation hover (transition rapide)
    HOVER_ANIMATION_STEPS = 8
    HOVER_ANIMATION_DELAY_MS = 20
    
    # Typographie
    FONT_FAMILY = "Segoe UI"
    VALUE_FONT_SIZE = 56
    LABEL_FONT_SIZE = 12
    
    def __init__(self, parent, data, center_text="TOTAL", on_segment_click=None, **kwargs):
        """
        Initialise le DonutChart.
        
        Args:
            parent: Widget parent
            data: Liste de tuples (label, value, color)
            center_text: Texte à afficher au centre par défaut
            on_segment_click: Callback quand on clique sur un segment (reçoit le filter_key)
        """
        super().__init__(parent, fg_color="transparent", **kwargs)
        
        # Données
        self.data = data
        self.center_text = center_text
        self.on_segment_click = on_segment_click
        
        # Dimensions calculées
        self.center_x = 225
        self.center_y = 225
        self.outer_radius = 120
        self.inner_radius = 80
        
        # État du hover
        self.segment_ids = {}
        self.hovered_segment = None
        
        # État de l'animation radial sweep
        self._sweep_animation_job = None
        self._sweep_progress = 0.0  # 0.0 à 1.0
        self._is_animating = False
        
        # État de l'animation hover (texte central)
        self._text_animation_job = None
        self._current_value = 0
        self._current_label = self.center_text
        self._text_opacity = 0.0  # Pour le fade-in
        
        # Créer l'interface
        self._create_ui()
        
        # Lancer l'animation au démarrage (après un court délai)
        self.after(150, self._initial_draw)
    
    # =====================================================================
    # CRÉATION DE L'INTERFACE
    # =====================================================================
    
    def _create_ui(self):
        """Crée le canvas et configure les événements"""
        self.canvas = ctk.CTkCanvas(
            self,
            bg=self.BG_COLOR,
            highlightthickness=0
        )
        self.canvas.pack(fill="both", expand=True)
        
        # Masquer le canvas initialement avec une couleur de fond
        # pour éviter le flash du contenu non initialisé
        self.canvas.configure(bg=self.BG_COLOR)
        
        # Événements souris
        self.canvas.bind("<Motion>", self._on_mouse_move)
        self.canvas.bind("<Leave>", self._on_mouse_leave)
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        
        # Événement redimensionnement
        self.bind("<Configure>", self._on_resize)
    
    # =====================================================================
    # GESTION DES DIMENSIONS
    # =====================================================================
    
    def _initial_draw(self):
        """Premier dessin avec animation de balayage radial"""
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        
        if width > 1 and height > 1:
            self._update_dimensions(width, height)
            self._start_sweep_animation()
        else:
            # Si les dimensions ne sont pas encore prêtes, réessayer plus tard
            self.after(50, self._initial_draw)
    
    def _on_resize(self, event=None):
        """Redessine lors du redimensionnement (sans animation)"""
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        
        if width > 1 and height > 1:
            self._update_dimensions(width, height)
            # Redessiner instantanément (pas d'animation au resize)
            self._sweep_progress = 1.0
            self._text_opacity = 1.0
            self._render_chart()
    
    def _update_dimensions(self, width, height):
        """Met à jour les dimensions du donut"""
        self.center_x = width / 2
        self.center_y = height / 2
        
        min_dim = min(width, height)
        self.outer_radius = min_dim * self.OUTER_RADIUS_RATIO
        self.inner_radius = min_dim * self.INNER_RADIUS_RATIO
    
    # =====================================================================
    # ANIMATION RADIAL SWEEP (EFFET DE BALAYAGE CIRCULAIRE)
    # =====================================================================
    
    def _start_sweep_animation(self):
        """Démarre l'animation de balayage radial depuis 12h"""
        # Annuler toute animation en cours
        if self._sweep_animation_job is not None:
            try:
                self.after_cancel(self._sweep_animation_job)
            except Exception:
                pass
            self._sweep_animation_job = None
        
        # Réinitialiser
        self._sweep_progress = 0.0
        self._text_opacity = 0.0
        self._is_animating = True
        
        # Calculer le nombre de frames
        total_frames = int(self.SWEEP_DURATION_MS / self.SWEEP_FRAME_DELAY)
        current_frame = [0]
        
        def animate_frame():
            if current_frame[0] <= total_frames:
                # Calculer la progression (0.0 à 1.0)
                linear_progress = current_frame[0] / total_frames
                
                # Appliquer l'easing cubic-bezier (ease-out)
                # Courbe: rapide au début, ralentit à la fin
                self._sweep_progress = self._ease_out_cubic(linear_progress)
                
                # Animation du texte (fade-in progressif à partir de 30%)
                if linear_progress >= self.TEXT_FADE_START_PROGRESS:
                    fade_progress = (linear_progress - self.TEXT_FADE_START_PROGRESS) / (1.0 - self.TEXT_FADE_START_PROGRESS)
                    self._text_opacity = self._ease_out_cubic(fade_progress)
                else:
                    self._text_opacity = 0.0
                
                # Redessiner avec la progression actuelle
                self._render_chart()
                
                # Frame suivante
                current_frame[0] += 1
                self._sweep_animation_job = self.after(self.SWEEP_FRAME_DELAY, animate_frame)
            else:
                # Animation terminée
                self._sweep_progress = 1.0
                self._text_opacity = 1.0
                self._is_animating = False
                self._sweep_animation_job = None
                self._render_chart()
        
        animate_frame()
    
    def _ease_out_cubic(self, t):
        """
        Fonction d'easing cubic-bezier (ease-out).
        Commence vite, ralentit à la fin.
        
        Args:
            t: Progression linéaire (0.0 à 1.0)
            
        Returns:
            Progression avec easing (0.0 à 1.0)
        """
        return 1 - pow(1 - t, 3)
    
    # =====================================================================
    # RENDU DU GRAPHIQUE
    # =====================================================================
    
    def _render_chart(self):
        """Rendu complet du graphique avec progression d'animation"""
        # Ne pas dessiner si les dimensions ne sont pas encore initialisées
        # ou si le rayon extérieur est trop petit (évite le flash initial)
        if self.outer_radius < 10:
            return
        
        self.canvas.delete("all")
        self.segment_ids = {}
        
        self._draw_donut()
        self._draw_center_circle()
        self._draw_center_text()
    
    def _draw_donut(self):
        """Dessine tous les segments du donut avec animation de balayage"""
        # Filtrer les données actives
        active_data = [(label, value, color) for label, value, color in self.data if value > 0]
        
        if not active_data:
            return
        
        # Calculer le total
        total = sum(value for _, value, _ in active_data)
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # ANIMATION RADIAL SWEEP : Tous les segments grandissent simultanément
        # depuis 12h (START_ANGLE = 90°) dans le sens horaire
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        
        # Angle maximum de balayage (0° à 360° × progression)
        max_sweep_angle = 360 * self._sweep_progress
        
        # Position angulaire de départ
        current_angle = self.START_ANGLE
        drawn_angle = 0  # Angle total dessiné jusqu'à présent
        
        for label, value, color in active_data:
            # Étendue réelle du segment (une fois l'animation terminée)
            full_extent = (value / total * 360) - self.GAP_ANGLE
            
            # ── CALCUL DE L'ÉTENDUE ANIMÉE ──
            # Chaque segment grandit proportionnellement à la progression globale
            if drawn_angle + full_extent <= max_sweep_angle:
                # Le segment est entièrement visible
                animated_extent = full_extent
            elif drawn_angle < max_sweep_angle:
                # Le segment est partiellement visible
                animated_extent = max_sweep_angle - drawn_angle
            else:
                # Le segment n'est pas encore visible
                animated_extent = 0
            
            # Dessiner le segment avec l'étendue animée
            if animated_extent > 0:
                segment_ids = self._draw_segment(current_angle, animated_extent, color)
                
                # Stocker les infos du segment pour le hover
                segment_info = {
                    'label': label,
                    'value': value,
                    'color': color
                }
                
                for seg_id in segment_ids:
                    self.segment_ids[seg_id] = segment_info
            
            # Avancer pour le prochain segment
            current_angle += full_extent + self.GAP_ANGLE
            drawn_angle += full_extent + self.GAP_ANGLE
    
    def _draw_segment(self, start_angle, extent, color):
        """
        Dessine un segment individuel du donut.
        
        Args:
            start_angle: Angle de départ (degrés)
            extent: Étendue angulaire (degrés)
            color: Couleur du segment
            
        Returns:
            Liste des IDs canvas créés
        """
        if extent <= 0:
            return []
        
        # Conversion en radians
        start_rad = math.radians(start_angle)
        end_rad = math.radians(start_angle + extent)
        
        # Nombre de points pour lisser l'arc
        num_points = max(int(abs(extent)), 20)
        
        points = []
        
        # ── Arc extérieur (sens horaire) ──
        for i in range(num_points + 1):
            progress = i / num_points
            angle = start_rad + (end_rad - start_rad) * progress
            
            x = self.center_x + self.outer_radius * math.cos(angle)
            y = self.center_y - self.outer_radius * math.sin(angle)
            points.append((x, y))
        
        # ── Arc intérieur (sens anti-horaire) ──
        for i in range(num_points, -1, -1):
            progress = i / num_points
            angle = start_rad + (end_rad - start_rad) * progress
            
            x = self.center_x + self.inner_radius * math.cos(angle)
            y = self.center_y - self.inner_radius * math.sin(angle)
            points.append((x, y))
        
        # Créer le polygone
        poly_id = self.canvas.create_polygon(
            points,
            fill=color,
            outline=color,
            smooth=False,
            width=1,
            tags="segment"
        )
        
        return [poly_id]
    
    def _draw_center_circle(self):
        """Dessine le cercle blanc au centre pour créer l'effet donut"""
        self.canvas.create_oval(
            self.center_x - self.inner_radius,
            self.center_y - self.inner_radius,
            self.center_x + self.inner_radius,
            self.center_y + self.inner_radius,
            fill=self.CENTER_CIRCLE_COLOR,
            outline=self.CENTER_CIRCLE_COLOR,
            width=0,
            tags="center_circle"
        )
    
    # =====================================================================
    # TEXTE CENTRAL (avec fade-in et animation hover)
    # =====================================================================
    
    def _draw_center_text(self, label=None, value=None):
        """
        Dessine le texte au centre du donut avec fade-in pendant l'animation.
        
        Args:
            label: Label à afficher (None = afficher total)
            value: Valeur à afficher (None = calculer total)
        """
        # Supprimer l'ancien texte
        self.canvas.delete("center_text")
        
        if label is None and value is None:
            # Mode TOTAL
            total = sum(val for _, val, _ in self.data if val > 0)
            target_value = total
            target_label = self.center_text
        else:
            # Mode SEGMENT HOVER
            target_value = value
            target_label = label
        
        # Si on est en mode animation initiale, utiliser le fade-in SANS incrémentation
        if self._is_animating or self._text_opacity < 1.0:
            # Calculer la couleur avec opacité
            color_value = self._apply_opacity(self.TEXT_PRIMARY, self._text_opacity)
            color_label = self._apply_opacity(self.TEXT_SECONDARY, self._text_opacity)
            
            # Afficher directement la valeur finale (pas d'incrémentation au démarrage)
            self._render_text(target_value, target_label, color_value, color_label)
            self._current_value = target_value
            self._current_label = target_label
        else:
            # Mode normal avec animation de valeur (UNIQUEMENT pour le hover)
            self._animate_value(target_value, target_label)
    
    def _apply_opacity(self, hex_color, opacity):
        """
        Applique une opacité à une couleur hex (simulation via interpolation avec blanc).
        
        Args:
            hex_color: Couleur au format #RRGGBB
            opacity: Opacité (0.0 à 1.0)
            
        Returns:
            Couleur hex avec opacité simulée
        """
        # Convertir hex en RGB
        hex_color = hex_color.lstrip('#')
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        
        # Interpoler vers blanc (255, 255, 255) pour simuler l'opacité
        white = 255
        r_final = int(r * opacity + white * (1 - opacity))
        g_final = int(g * opacity + white * (1 - opacity))
        b_final = int(b * opacity + white * (1 - opacity))
        
        return f'#{r_final:02x}{g_final:02x}{b_final:02x}'
    
    def _animate_value(self, target_value, target_label):
        """
        Anime la transition de la valeur affichée (pour le hover).
        
        Args:
            target_value: Valeur cible
            target_label: Label cible
        """
        # Annuler l'animation en cours
        if self._text_animation_job is not None:
            try:
                self.after_cancel(self._text_animation_job)
            except Exception:
                pass
            self._text_animation_job = None
        
        # Si même valeur, pas d'animation
        if target_value == self._current_value and target_label == self._current_label:
            self._render_text(self._current_value, self._current_label)
            return
        
        # Démarrer l'animation
        start_value = self._current_value
        steps = self.HOVER_ANIMATION_STEPS
        current_step = [0]
        
        def step():
            if current_step[0] <= steps:
                progress = current_step[0] / steps
                ease = 1 - pow(1 - progress, 2)
                
                interpolated_value = int(start_value + (target_value - start_value) * ease)
                
                self._current_value = interpolated_value
                self._current_label = target_label
                self._render_text(interpolated_value, target_label)
                
                current_step[0] += 1
                self._text_animation_job = self.after(self.HOVER_ANIMATION_DELAY_MS, step)
            else:
                self._current_value = target_value
                self._current_label = target_label
                self._render_text(target_value, target_label)
                self._text_animation_job = None
        
        step()
    
    def _render_text(self, value, label, color_value=None, color_label=None):
        """
        Affiche le texte au centre (valeur + label).
        
        Args:
            value: Nombre à afficher
            label: Label à afficher
            color_value: Couleur du nombre (None = défaut)
            color_label: Couleur du label (None = défaut)
        """
        self.canvas.delete("center_text")
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # ANTI-CLIGNOTEMENT : Ne pas afficher le texte si l'opacité est trop faible
        # Cela évite le flash initial avant le début de l'animation
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        if self._is_animating and self._text_opacity < self.TEXT_MIN_OPACITY_THRESHOLD:
            return  # Ne rien dessiner si l'opacité est quasi nulle
        
        if color_value is None:
            color_value = self.TEXT_PRIMARY
        if color_label is None:
            color_label = self.TEXT_SECONDARY
        
        # Valeur (grand nombre)
        self.canvas.create_text(
            self.center_x,
            self.center_y - 20,
            text=str(value),
            font=(self.FONT_FAMILY, self.VALUE_FONT_SIZE, "bold"),
            fill=color_value,
            tags="center_text"
        )
        
        # Label (petit texte)
        self.canvas.create_text(
            self.center_x,
            self.center_y + 30,
            text=label.upper(),
            font=(self.FONT_FAMILY, self.LABEL_FONT_SIZE, "bold"),
            fill=color_label,
            tags="center_text"
        )
    
    # =====================================================================
    # GESTION DES ÉVÉNEMENTS SOURIS
    # =====================================================================
    
    def _on_mouse_move(self, event):
        """Gère le mouvement de la souris sur le canvas"""
        # Pas d'interaction pendant l'animation initiale
        if self._is_animating:
            return
        
        # Trouver tous les éléments sous le curseur
        overlapping = self.canvas.find_overlapping(event.x, event.y, event.x, event.y)
        
        segment_found = None
        for item_id in overlapping:
            if item_id in self.segment_ids:
                segment_found = self.segment_ids[item_id]
                break
        
        if segment_found:
            self.canvas.config(cursor="hand2")
            
            if self.hovered_segment != segment_found:
                self.hovered_segment = segment_found
                self._draw_center_text(segment_found['label'], segment_found['value'])
        else:
            self.canvas.config(cursor="")
            
            if self.hovered_segment is not None:
                self.hovered_segment = None
                self._draw_center_text()
    
    def _on_mouse_leave(self, event):
        """Gère la sortie de la souris du canvas"""
        self.canvas.config(cursor="")
        
        if self.hovered_segment is not None:
            self.hovered_segment = None
            self._draw_center_text()
    
    def _on_canvas_click(self, event):
        """Gère le clic sur un segment du donut"""
        if self.on_segment_click is None:
            return
        
        # Trouver le segment sous le curseur
        overlapping = self.canvas.find_overlapping(event.x, event.y, event.x, event.y)
        
        for item_id in overlapping:
            if item_id in self.segment_ids:
                segment_info = self.segment_ids[item_id]
                label = segment_info['label']
                
                # Mapper les labels vers les filter_keys
                status_to_filter = {
                    "ACTIVE": "active",
                    "AVAILABLE": "available",
                    "MAINTENANCE": "maintenance",
                    "LENT OUT": "lent_out"
                }
                
                filter_key = status_to_filter.get(label.upper())
                if filter_key:
                    self.on_segment_click(filter_key)
                break
    
    # =====================================================================
    # API PUBLIQUE
    # =====================================================================
    
    def update_data(self, new_data, animate=True):
        """
        Met à jour les données et redessine le graphique.
        
        Args:
            new_data: Nouvelle liste de tuples (label, value, color)
            animate: Si True, relance l'animation de balayage
        """
        self.data = new_data
        self.hovered_segment = None
        self._current_value = 0
        
        if animate:
            self._start_sweep_animation()
        else:
            self._sweep_progress = 1.0
            self._text_opacity = 1.0
            self._render_chart()
    
    def draw_donut(self):
        """Alias pour compatibilité - dessine l'anneau du donut"""
        self._draw_donut()
    
    def draw_center_text(self, label=None, value=None):
        """Alias pour compatibilité - dessine le texte central"""
        self._draw_center_text(label, value)


# =====================================================================
# TEST STANDALONE
# =====================================================================

if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    root = ctk.CTk()
    root.geometry("700x700")
    root.title("Donut Chart - Radial Sweep Animation")
    
    # Container
    container = ctk.CTkFrame(root, fg_color="white", corner_radius=20)
    container.pack(fill="both", expand=True, padx=40, pady=40)
    
    # Données de test
    test_data = [
        ("ACTIVE", 4, "#10B981"),
        ("AVAILABLE", 10, "#3B82F6"),
        ("MAINTENANCE", 2, "#F59E0B"),
        ("LENT OUT", 7, "#EF4444")
    ]
    
    # Créer le chart
    chart = DonutChart(container, test_data, center_text="GLOBAL ITEMS")
    chart.pack(fill="both", expand=True, padx=20, pady=20)
    
    # Boutons de test
    btn_frame = ctk.CTkFrame(root, fg_color="transparent")
    btn_frame.pack(pady=10)
    
    def replay_animation():
        """Rejoue l'animation de balayage"""
        chart._start_sweep_animation()
    
    def update_with_animation():
        """Met à jour avec de nouvelles données et animation"""
        import random
        new_data = [
            ("ACTIVE", random.randint(1, 15), "#10B981"),
            ("AVAILABLE", random.randint(1, 15), "#3B82F6"),
            ("MAINTENANCE", random.randint(1, 15), "#F59E0B"),
            ("LENT OUT", random.randint(1, 15), "#EF4444")
        ]
        chart.update_data(new_data, animate=True)
    
    btn_replay = ctk.CTkButton(
        btn_frame,
        text="🔁 Replay Animation",
        command=replay_animation,
        font=ctk.CTkFont(size=14, weight="bold"),
        height=40,
        width=180
    )
    btn_replay.pack(side="left", padx=5)
    
    btn_update = ctk.CTkButton(
        btn_frame,
        text="🔄 Update Data (Animated)",
        command=update_with_animation,
        font=ctk.CTkFont(size=14, weight="bold"),
        height=40,
        width=200
    )
    btn_update.pack(side="left", padx=5)
    
    root.mainloop()