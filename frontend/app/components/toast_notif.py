import customtkinter as ctk

class ToastNotification:
    """
    A reusable toast notification component for CustomTkinter applications.
    
    Usage:
        # In your main window class __init__:
        self.toast = ToastNotification(self)
        
        # To show a notification:
        self.toast.show("Operation completed successfully!")
    """
    
    def __init__(self, parent, duration=3000, bg_color="#0F172A", text_color="white", 
                 corner_radius=20, font=("Inter", 12, "bold"), top_padding=20):
        """
        Initialize the toast notification system.
        
        Args:
            parent: The parent CTk window or frame
            duration: How long to show the toast in milliseconds (default: 3000)
            bg_color: Background color of the toast (default: navy)
            text_color: Text color (default: white)
            corner_radius: Border radius (default: 20)
            font: Font tuple (default: ("Inter", 12, "bold"))
            top_padding: Distance from top in pixels (default: 20)
        """
        self.parent = parent
        self.duration = duration
        self.bg_color = bg_color
        self.text_color = text_color
        self.corner_radius = corner_radius
        self.font = font
        self.top_padding = top_padding  # Nouveau paramètre
        
        # Create the toast frame (hidden by default)
        self.toast_frame = ctk.CTkFrame(
            parent, 
            fg_color=bg_color, 
            corner_radius=corner_radius
        )
        
        # Create the label inside the frame
        self.toast_label = ctk.CTkLabel(
            self.toast_frame, 
            text="", 
            font=font, 
            text_color=text_color
        )
        self.toast_label.pack(padx=30, pady=15)
        
        # Store the after_id to allow cancellation if needed
        self.after_id = None
    
    def show(self, message, duration=None):
        """
        Display a toast notification with the given message.
        
        Args:
            message: The text to display
            duration: Optional override for display duration in milliseconds
        """
        # Cancel any pending hide operation
        if self.after_id:
            self.parent.after_cancel(self.after_id)
        
        # Update the message (convert to uppercase for consistency with original)
        self.toast_label.configure(text=message.upper())
        
        # Position the toast at the top center with custom padding
        self.toast_frame.place(relx=0.5, y=self.top_padding, anchor="n")
        
        # Schedule automatic hiding
        hide_duration = duration if duration is not None else self.duration
        self.after_id = self.parent.after(hide_duration, self.hide)
    
    def hide(self):
        """Hide the toast notification."""
        self.toast_frame.place_forget()
        self.after_id = None
    
    def update_style(self, bg_color=None, text_color=None, corner_radius=None, font=None, top_padding=None):
        """
        Update the visual style of the toast.
        
        Args:
            bg_color: New background color (optional)
            text_color: New text color (optional)
            corner_radius: New corner radius (optional)
            font: New font (optional)
            top_padding: New top padding in pixels (optional)
        """
        if bg_color:
            self.bg_color = bg_color
            self.toast_frame.configure(fg_color=bg_color)
        
        if text_color:
            self.text_color = text_color
            self.toast_label.configure(text_color=text_color)
        
        if corner_radius:
            self.corner_radius = corner_radius
            self.toast_frame.configure(corner_radius=corner_radius)
        
        if font:
            self.font = font
            self.toast_label.configure(font=font)
        
        if top_padding is not None:
            self.top_padding = top_padding
# Demo application
if __name__ == "__main__":
    class DemoApp(ctk.CTk):
        def __init__(self):
            super().__init__()
            self.title("Toast Notification Demo")
            self.geometry("800x600")
            self.configure(fg_color="#F0F4F9")
            
            # Initialize toast notification
            self.toast = ToastNotification(self)
            

            
            subtitle = ctk.CTkLabel(
                self, 
                text="Click buttons to see different toast notifications", 
                font=("Inter", 12),
                text_color="#94A3B8"
            )
            subtitle.pack(pady=(0, 50))
            
            # Success toast
            btn1 = ctk.CTkButton(
                self,
                text="Show Success Message",
                command=lambda: self.toast.show("Item saved successfully!"),
                width=300,
                height=50,
                corner_radius=15,
                fg_color="#2563EB",
                font=("Inter", 12, "bold")
            )
            btn1.pack(pady=10)
            
            # Delete toast
            btn2 = ctk.CTkButton(
                self,
                text="Show Delete Message",
                command=lambda: self.toast.show("Item deleted successfully!"),
                width=300,
                height=50,
                corner_radius=15,
                fg_color="#E11D48",
                font=("Inter", 12, "bold")
            )
            btn2.pack(pady=10)
            
            # Custom duration toast
            btn3 = ctk.CTkButton(
                self,
                text="Show Long Message (5 seconds)",
                command=lambda: self.toast.show("This message stays longer", duration=5000),
                width=300,
                height=50,
                corner_radius=15,
                fg_color="#00C389",
                font=("Inter", 12, "bold")
            )
            btn3.pack(pady=10)
            
            # Change style button
            btn4 = ctk.CTkButton(
                self,
                text="Change Toast Style",
                command=self.change_toast_style,
                width=300,
                height=50,
                corner_radius=15,
                fg_color="#D97706",
                font=("Inter", 12, "bold")
            )
            btn4.pack(pady=10)
            
            self.style_changed = False
        
        def change_toast_style(self):
            if not self.style_changed:
                # Change to a green style
                self.toast.update_style(
                    bg_color="#00C389",
                    text_color="white",
                    corner_radius=15,
                    font=("Inter", 14, "bold")
                )
                self.toast.show("Style changed to green!")
                self.style_changed = True
            else:
                # Change back to original navy style
                self.toast.update_style(
                    bg_color="#0F172A",
                    text_color="white",
                    corner_radius=20,
                    font=("Inter", 12, "bold")
                )
                self.toast.show("Style reset to navy!")
                self.style_changed = False
    
    ctk.set_appearance_mode("light")
    app = DemoApp()
    app.mainloop()