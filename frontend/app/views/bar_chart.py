import customtkinter as ctk


class BarChart(ctk.CTkFrame):
    """
    Widget de graphique en barres avec animation fluide de montée.
    
    Features:
    - Animation de montée des barres depuis 0 jusqu'à leur valeur finale
    - Easing cubic-bezier (ease-out) pour un effet fluide
    - Toutes les barres s'animent simultanément
    - Redimensionnement automatique
    - Design responsive avec coins arrondis
    """
    
    # =====================================================================
    # CONFIGURATION VISUELLE
    # =====================================================================
    
    # Couleurs
    BG_COLOR = "white"
    BAR_COLOR = "#4081F5"
    GRID_COLOR = "#E8E8E8"
    LABEL_COLOR = "#888888"
    VALUE_COLOR = "#999999"
    
    # Marges
    LEFT_MARGIN = 60
    RIGHT_MARGIN = 40
    TOP_MARGIN = 20
    BOTTOM_MARGIN = 60
    
    # Dimensions barres
    MAX_BAR_WIDTH = 50
    BAR_WIDTH_RATIO = 0.6
    MIN_CORNER_RADIUS = 8
    
    # =====================================================================
    # CONFIGURATION ANIMATION
    # =====================================================================
    
    # Animation principale (montée des barres)
    RISE_DURATION_MS = 1000  # Durée totale de l'animation (1 seconde)
    RISE_FPS = 60  # 60 FPS pour fluidité maximale
    RISE_FRAME_DELAY = int(1000 / RISE_FPS)  # ~16ms par frame
    
    # Typographie
    FONT_FAMILY = "Segoe UI"
    LABEL_FONT_SIZE = 9
    VALUE_FONT_SIZE = 9
    
    def __init__(self, parent, data, on_bar_click=None, **kwargs):
        """
        Initialise le BarChart.
        
        Args:
            parent: Widget parent
            data: Dict {label: value} ou liste de tuples [(label, value), ...]
            on_bar_click: Callback quand on clique sur une barre (reçoit le label)
        """
        super().__init__(parent, fg_color="transparent", **kwargs)
        
        # Données
        self.data = list(data.items()) if isinstance(data, dict) else data
        self.max_value = max(value for _, value in self.data) if self.data else 1
        self.on_bar_click = on_bar_click
        
        # État de l'animation
        self._animation_job = None
        self._animation_progress = 0.0  # 0.0 à 1.0
        self._is_animating = False
        
        # Stocker les IDs des barres pour le click
        self._bar_ids = {}
        
        # Créer l'interface
        self._create_ui()
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # ANTI-FLASH : Délai plus long pour éviter l'affichage avant animation
        # dans les programmes chargés
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        self.after(300, self._initial_draw)
    
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
        
        # Événement redimensionnement
        self.bind("<Configure>", self._on_resize)
        
        # Événement clic sur les barres
        if self.on_bar_click:
            self.canvas.bind("<Button-1>", self._on_canvas_click)
            self.canvas.bind("<Motion>", self._on_mouse_move)
    
    # =====================================================================
    # GESTION DES DIMENSIONS
    # =====================================================================
    
    def _initial_draw(self):
        """Premier dessin avec animation de montée"""
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        
        if width > 1 and height > 1:
            # Marquer qu'on est prêt à animer AVANT de démarrer
            # (pour que _redraw ne bloque pas pendant l'animation)
            self._start_rise_animation()
    
    def _on_resize(self, event=None):
        """Redessine lors du redimensionnement (sans animation)"""
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        
        if width > 1 and height > 1:
            # Redessiner instantanément (pas d'animation au resize)
            self._animation_progress = 1.0
            self._redraw()
    
    # =====================================================================
    # ANIMATION DE MONTÉE DES BARRES
    # =====================================================================
    
    def _start_rise_animation(self):
        """Démarre l'animation de montée des barres depuis 0"""
        # Annuler toute animation en cours
        if self._animation_job is not None:
            try:
                self.after_cancel(self._animation_job)
            except Exception:
                pass
            self._animation_job = None
        
        # Réinitialiser
        self._animation_progress = 0.0
        self._is_animating = True
        
        # Calculer le nombre de frames
        total_frames = int(self.RISE_DURATION_MS / self.RISE_FRAME_DELAY)
        current_frame = [0]
        
        def animate_frame():
            if current_frame[0] <= total_frames:
                # Calculer la progression (0.0 à 1.0)
                linear_progress = current_frame[0] / total_frames
                
                # Appliquer l'easing cubic-bezier (ease-out)
                # Courbe: rapide au début, ralentit à la fin
                self._animation_progress = self._ease_out_cubic(linear_progress)
                
                # Redessiner avec la progression actuelle
                self._redraw()
                
                # Frame suivante
                current_frame[0] += 1
                self._animation_job = self.after(self.RISE_FRAME_DELAY, animate_frame)
            else:
                # Animation terminée
                self._animation_progress = 1.0
                self._is_animating = False
                self._animation_job = None
                self._redraw()
        
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
    
    def _redraw(self):
        """Redessiner le graphique complet"""
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        
        if width <= 1 or height <= 1:
            return
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # ANTI-FLASH : Ne rien dessiner si on n'a pas encore commencé l'animation
        # et que la progression est à 0 (évite l'affichage initial non animé)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        if self._animation_progress == 0.0 and not self._is_animating:
            return  # Ne rien dessiner avant le début de l'animation
        
        self.canvas.delete("all")
        self._draw_grid(width, height)
        self._draw_bars(width, height)
    
    def _draw_grid(self, width, height):
        """
        Dessiner la grille avec lignes horizontales et valeurs Y.
        
        Args:
            width: Largeur du canvas
            height: Hauteur du canvas
        """
        # Zone de dessin
        chart_height = height - self.TOP_MARGIN - self.BOTTOM_MARGIN
        
        num_lines = int(self.max_value) + 1
        
        for i in range(num_lines):
            # Position Y de la ligne
            y = self.TOP_MARGIN + chart_height - (i * chart_height / self.max_value)
            
            # Ligne horizontale
            self.canvas.create_line(
                self.LEFT_MARGIN, y,
                width - self.RIGHT_MARGIN, y,
                fill=self.GRID_COLOR,
                width=1,
                dash=(2, 4),
                tags="grid"
            )
            
            # Valeur sur l'axe Y
            self.canvas.create_text(
                self.LEFT_MARGIN - 25, y,
                text=str(i),
                font=(self.FONT_FAMILY, self.VALUE_FONT_SIZE, "bold"),
                fill=self.VALUE_COLOR,
                anchor="e",
                tags="grid"
            )
    
    def _draw_bars(self, width, height):
        """
        Dessiner les barres avec animation de montée.
        
        Args:
            width: Largeur du canvas
            height: Hauteur du canvas
        """
        if not self.data:
            return
        
        # Réinitialiser les IDs des barres
        self._bar_ids = {}
        
        # Zone de dessin
        chart_height = height - self.TOP_MARGIN - self.BOTTOM_MARGIN
        chart_width = width - self.LEFT_MARGIN - self.RIGHT_MARGIN
        
        num_bars = len(self.data)
        spacing = chart_width / num_bars
        
        # Largeur de barre adaptative (max 50px)
        bar_width = min(self.MAX_BAR_WIDTH, spacing * self.BAR_WIDTH_RATIO)
        radius = min(self.MIN_CORNER_RADIUS, bar_width / 5)
        
        for i, (label, value) in enumerate(self.data):
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # ANIMATION : Hauteur de la barre multipliée par la progression
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            animated_value = value * self._animation_progress
            bar_height = (animated_value / self.max_value) * chart_height
            
            # Position horizontale
            x = self.LEFT_MARGIN + i * spacing + (spacing - bar_width) / 2
            
            # Position verticale (du haut vers le bas)
            y_top = self.TOP_MARGIN + chart_height - bar_height
            y_bottom = self.TOP_MARGIN + chart_height
            
            # Dessiner la barre avec coins arrondis et stocker les IDs
            bar_ids = self._draw_rounded_rect(
                x=x,
                y=y_top,
                width=bar_width,
                height=bar_height,
                radius=radius,
                color=self.BAR_COLOR
            )
            
            # Stocker les IDs de cette barre avec son label
            for bar_id in bar_ids:
                self._bar_ids[bar_id] = label
            
            # ── Label sous la barre ──
            label_y = y_bottom + 15
            
            # Tronquer le label si trop long
            display_label = label if len(label) <= 10 else label[:9] + "..."
            
            self.canvas.create_text(
                x + bar_width / 2,
                label_y,
                text=display_label,
                font=(self.FONT_FAMILY, self.LABEL_FONT_SIZE, "bold"),
                fill=self.LABEL_COLOR,
                angle=0,
                tags="label"
            )
    
    def _draw_rounded_rect(self, x, y, width, height, radius, color):
        """
        Dessiner un rectangle avec coins arrondis.
        
        Args:
            x: Position X (coin haut-gauche)
            y: Position Y (coin haut-gauche)
            width: Largeur
            height: Hauteur
            radius: Rayon des coins arrondis
            color: Couleur de remplissage
            
        Returns:
            Liste des IDs canvas créés
        """
        ids = []
        
        if height < 1:
            return ids
        
        # Ajuster le radius si nécessaire
        radius = min(radius, width / 2, height / 2)
        
        if radius < 1:
            # Rectangle simple si trop petit
            id = self.canvas.create_rectangle(
                x, y, x + width, y + height,
                fill=color, outline=color,
                tags="bar"
            )
            ids.append(id)
            return ids
        
        # ── Coins arrondis (haut) ──
        id = self.canvas.create_arc(
            x, y, x + 2*radius, y + 2*radius,
            start=90, extent=90, fill=color, outline=color,
            tags="bar"
        )
        ids.append(id)
        
        id = self.canvas.create_arc(
            x + width - 2*radius, y, x + width, y + 2*radius,
            start=0, extent=90, fill=color, outline=color,
            tags="bar"
        )
        ids.append(id)
        
        # ── Coins arrondis (bas) ──
        id = self.canvas.create_arc(
            x, y + height - 2*radius, x + 2*radius, y + height,
            start=180, extent=90, fill=color, outline=color,
            tags="bar"
        )
        ids.append(id)
        
        id = self.canvas.create_arc(
            x + width - 2*radius, y + height - 2*radius, x + width, y + height,
            start=270, extent=90, fill=color, outline=color,
            tags="bar"
        )
        ids.append(id)
        
        # ── Rectangles de remplissage ──
        id = self.canvas.create_rectangle(
            x + radius, y, x + width - radius, y + height,
            fill=color, outline=color,
            tags="bar"
        )
        ids.append(id)
        
        id = self.canvas.create_rectangle(
            x, y + radius, x + width, y + height - radius,
            fill=color, outline=color,
            tags="bar"
        )
        ids.append(id)
        
        return ids
    
    def _on_mouse_move(self, event):
        """Gère le mouvement de la souris sur le canvas"""
        if not self.on_bar_click:
            return
        
        # Trouver les éléments sous le curseur
        overlapping = self.canvas.find_overlapping(event.x, event.y, event.x, event.y)
        
        bar_found = False
        for item_id in overlapping:
            if item_id in self._bar_ids:
                bar_found = True
                break
        
        if bar_found:
            self.canvas.config(cursor="hand2")
        else:
            self.canvas.config(cursor="")
    
    def _on_canvas_click(self, event):
        """Gère le clic sur une barre"""
        if not self.on_bar_click:
            return
        
        # Trouver les éléments sous le curseur
        overlapping = self.canvas.find_overlapping(event.x, event.y, event.x, event.y)
        
        for item_id in overlapping:
            if item_id in self._bar_ids:
                label = self._bar_ids[item_id]
                self.on_bar_click(label)
                break
    
    # =====================================================================
    # API PUBLIQUE
    # =====================================================================
    
    def update_data(self, new_data, animate=True):
        """
        Met à jour les données et redessine le graphique.
        
        Args:
            new_data: Nouveau dict {label: value} ou liste de tuples
            animate: Si True, relance l'animation de montée
        """
        self.data = list(new_data.items()) if isinstance(new_data, dict) else new_data
        self.max_value = max(value for _, value in self.data) if self.data else 1
        
        if animate:
            self._start_rise_animation()
        else:
            self._animation_progress = 1.0
            self._redraw()
    
    def draw_grid(self, width, height):
        """Alias pour compatibilité - dessine la grille"""
        self._draw_grid(width, height)
    
    def draw_bars(self, width, height):
        """Alias pour compatibilité - dessine les barres"""
        self._draw_bars(width, height)
    
    def draw_rounded_rect(self, x, y, width, height, radius, color):
        """Alias pour compatibilité - dessine un rectangle arrondi"""
        self._draw_rounded_rect(x, y, width, height, radius, color)


# =====================================================================
# TEST STANDALONE
# =====================================================================

if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    root = ctk.CTk()
    root.geometry("900x600")
    root.title("Bar Chart - Rise Animation")
    
    # Container
    container = ctk.CTkFrame(root, fg_color="white", corner_radius=20)
    container.pack(fill="both", expand=True, padx=40, pady=40)
    
    # Données de test
    test_data = {
        "Computers": 2,
        "Routers": 5,
        "Screens": 4,
        "Accessories": 7,
        "Phones": 1,
        "Servers": 3,
        "Printers": 2
    }
    
    # Créer le chart
    chart = BarChart(container, test_data)
    chart.pack(fill="both", expand=True, padx=20, pady=20)
    
    # Boutons de test
    btn_frame = ctk.CTkFrame(root, fg_color="transparent")
    btn_frame.pack(pady=10)
    
    def replay_animation():
        """Rejoue l'animation de montée"""
        chart._start_rise_animation()
    
    def update_with_animation():
        """Met à jour avec de nouvelles données et animation"""
        import random
        new_data = {
            "Computers": random.randint(1, 10),
            "Routers": random.randint(1, 10),
            "Screens": random.randint(1, 10),
            "Accessories": random.randint(1, 10),
            "Phones": random.randint(1, 10),
            "Servers": random.randint(1, 10),
            "Printers": random.randint(1, 10)
        }
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