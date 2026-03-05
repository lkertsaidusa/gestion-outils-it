import customtkinter as ctk
import tkinter as tk
import time
import os
import sys
from datetime import datetime, timedelta

# Application Theme Palette
THEME = {
    "bg": "#F0F4F9",
    "primary": "#166FFF",
    "primary_hover": "#1258CC",
    "primary_light": "#E8F0FE",
    "text_dark": "#28313F",
    "text_gray": "#9CA3AF",
    "text_medium": "#6B7280",
    "text_red": "#EF4444",
    "text_green": "#10B981",
    "green_hover": "#ECFDF5",
    "white": "#FFFFFF",
    "border": "#E2E8F0",
    "nav_bg": "#F1F5F9"
}

def _format_time(timestamp_str):
    """Convert timestamp string to 'Xh ago' format"""
    try:
        if isinstance(timestamp_str, datetime):
            dt = timestamp_str
        else:
            # timestamp_str is like "2026-02-23 18:05:51" (UTC from SQLite)
            dt = datetime.strptime(str(timestamp_str), "%Y-%m-%d %H:%M:%S")
        
        now = datetime.utcnow()
        diff = now - dt
        
        # Handle slight clock skews or future timestamps
        seconds = diff.total_seconds()
        if seconds < 0:
            return "Just now"
            
        if seconds < 60:
            return "Just now"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            return f"{minutes}m ago"
        elif seconds < 86400:
            hours = int(seconds / 3600)
            return f"{hours}h ago"
        elif diff.days < 7:
            return f"{diff.days}d ago"
        else:
            return f"{int(diff.days / 7)}w ago"
    except:
        return "Unknown"


class NotificationItem(ctk.CTkFrame):
    def __init__(self, master, n_data, on_delete, on_toggle, on_recover, is_archived_mode=False, is_last=False, **kwargs):
        super().__init__(master, fg_color="transparent", cursor="hand2", **kwargs)
        
        self.n_id = n_data["id"]
        self.is_expanded = n_data.get("is_expanded", False)
        self.is_read = n_data["is_read"]
        self.on_delete = on_delete
        self.on_toggle = on_toggle
        self.on_recover = on_recover
        self.is_archived_mode = is_archived_mode
        
        # Right: Action Column
        self.action_col = ctk.CTkFrame(self, fg_color="transparent")
        self.action_col.pack(side="right", padx=(10, 10), pady=10, fill="y")
        
        if self.is_archived_mode:
            self.rec_btn = ctk.CTkButton(self.action_col, text="\u21BA", font=("Inter", 12, "bold"), 
                                         text_color=THEME["primary"], fg_color="transparent", 
                                         hover_color=THEME["primary_light"], width=22, height=22, corner_radius=11,
                                         command=lambda: self.on_recover(self.n_id))
            self.rec_btn.pack(side="top", anchor="ne")
        else:
            self.del_btn = ctk.CTkButton(self.action_col, text="\u2715", font=("Inter", 10, "bold"), 
                                         text_color=THEME["text_gray"], fg_color="transparent", 
                                         hover_color="#FEF2F2", width=22, height=22, corner_radius=11,
                                         command=lambda: self.on_delete(self.n_id))
            self.del_btn.pack(side="top", anchor="ne")

        self.time_label = ctk.CTkLabel(self.action_col, text=n_data["time"], font=("Inter", 9), text_color=THEME["text_gray"])
        self.time_label.pack(side="top", anchor="ne", pady=(4, 0))
        
        # Middle: Content
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.pack(side="left", fill="both", expand=True, pady=10)
        
        self.header_row = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.header_row.pack(fill="x")
        
        self.dot = ctk.CTkLabel(self.header_row, text="•", text_color=THEME["primary"], font=("Inter", 20, "bold"))
        self.dot.pack(side="left", anchor="n")
        
        self.title_label = ctk.CTkLabel(
            self.header_row, 
            text=n_data["title"], 
            text_color=THEME["text_dark"],
            wraplength=600,
            justify="left",
            anchor="w",
            font=("Inter", 16, "bold")
        )
        self.title_label.pack(side="left", padx=(5, 0), fill="x", expand=True)
        
        self.desc_label = ctk.CTkLabel(
            self.content_frame, 
            text=n_data["description"], 
            font=("Inter", 14), 
            text_color=THEME["text_medium"], 
            wraplength=620, 
            justify="left",
            anchor="w"
        )
        
        self.snippet_label = ctk.CTkLabel(
            self.content_frame, 
            text=n_data["description"][:60] + "...", 
            font=("Inter", 13), 
            text_color=THEME["text_gray"],
            wraplength=620,
            justify="left",
            anchor="w"
        )
        
        self.refresh_ui()

        if not is_last:
            self.sep = ctk.CTkFrame(self, height=1, fg_color=THEME["border"])
            self.sep.place(relx=0.5, rely=1.0, relwidth=0.9, anchor="s")

        widgets_to_bind = [self, self.content_frame, self.header_row, self.title_label, 
                           self.snippet_label, self.desc_label, self.time_label]
        for widget in widgets_to_bind:
            widget.bind("<Button-1>", lambda e: self.on_toggle(self.n_id))

    def refresh_ui(self):
        if self.is_read:
            self.dot.configure(text="")
            self.title_label.configure(font=("Inter", 16), text_color=THEME["text_medium"])
        else:
            self.dot.configure(text="•")
            self.title_label.configure(font=("Inter", 16, "bold"), text_color=THEME["text_dark"])
            
        if self.is_expanded:
            self.snippet_label.pack_forget()
            self.desc_label.pack(anchor="w", pady=(2, 0))
        else:
            self.desc_label.pack_forget()
            self.snippet_label.pack(anchor="w", pady=(0, 0))

class NotificationsApp(ctk.CTkToplevel):
    def __init__(self, master=None):
        super().__init__(master)

        self.title("Notifications Center")
        
        # Fixed size and centered position
        width, height = 750, 750
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.resizable(False, False)
        self.configure(fg_color=THEME["bg"])
        
        # Make it stay on top
        self.after(100, self.lift)
        self.after(100, self.focus_force)
        
        # Load real notifications from database
        self.notifications = []
        try:
            # Add frontend path to sys.path to import backend modules
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
            if project_root not in sys.path:
                sys.path.insert(0, project_root)
            
            from backend import notification_service
            
            raw_notifications = notification_service.get_notifications()
            
            for n in raw_notifications:
                timestamp = n.get("timestamp", "")
                time_ago = _format_time(timestamp)
                
                # Determine category
                cat = "This Month"
                try:
                    if isinstance(timestamp, datetime):
                        dt = timestamp
                    else:
                        dt = datetime.strptime(str(timestamp), "%Y-%m-%d %H:%M:%S")
                    
                    now = datetime.utcnow()
                    
                    # Calculate date-based difference
                    delta_days = (now.date() - dt.date()).days
                    
                    if delta_days == 0:
                        cat = "Today"
                    elif delta_days < 7:
                        cat = "This Week"
                    else:
                        cat = "This Month"
                except Exception as e:
                    print(f"Error parsing timestamp {timestamp}: {e}")
                    pass
                
                # Format title
                n_type = n.get("type", "INFO").replace("INVENTORY_", "").replace("_", " ")
                actor = n.get("actor_name", "Unknown")
                role = n.get("actor_role", "")
                content = n.get("content", "")
                details = n.get("details", "")
                is_read_db = n.get("is_read", 0) == 1
                is_deleted_db = n.get("is_deleted", 0) == 1
                
                # We use the clear content we just formatted as the title
                title = content
                # And the type/actor/details as the description (expanded view)
                description = f"Type: {n_type} | Actor: {actor} ({role})"
                if details:
                    description += f"\n\n{details}"
                
                self.notifications.append({
                    "id": str(n.get("id", 0)),
                    "cat": cat,
                    "title": title,
                    "description": description,
                    "time": time_ago,
                    "is_read": is_read_db,
                    "is_expanded": False,
                    "is_deleted": is_deleted_db,
                    "deleted_at": 0
                })
                
        except Exception as e:
            print(f"Failed to load notifications: {e}")
            # Fallback to empty list if error
            self.notifications = []
        
        self.current_category = "Today"
        self.widget_map = {}
        
        self.canvas = tk.Canvas(self, bg=THEME["bg"], highlightthickness=0)
        self.canvas.place(relx=0, rely=0, relwidth=1, relheight=1)
        grid_size = 40
        for i in range(0, 1200, grid_size):
            self.canvas.create_line(i, 0, i, 750, fill=THEME["border"], width=1)
            self.canvas.create_line(0, i, 900, i, fill=THEME["border"], width=1)

        # Container fills the whole window now
        self.card = ctk.CTkFrame(self, corner_radius=0, fg_color=THEME["white"], border_width=0)
        self.card.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.card.pack_propagate(False)

        # Header Container
        self.header_container = ctk.CTkFrame(self.card, fg_color="transparent")
        self.header_container.pack(fill="x", padx=30, pady=(25, 5))

        self.header_top = ctk.CTkFrame(self.header_container, fg_color="transparent")
        self.header_top.pack(fill="x")
        ctk.CTkLabel(self.header_top, text="NOTIFICATIONS CENTER", font=("Inter", 18, "bold"), text_color=THEME["text_dark"]).pack(side="left")

        self.bulk_actions = ctk.CTkFrame(self.header_top, fg_color="transparent")
        self.bulk_actions.pack(side="right")
        
        self.mark_read_btn = ctk.CTkButton(
            self.bulk_actions, 
            text="MARK ALL READ", 
            font=("Inter", 11, "bold"), 
            text_color=THEME["primary"], 
            fg_color="transparent", 
            hover_color=THEME["primary_light"], 
            width=110, 
            height=32,
            command=self.mark_all_read
        )
        self.mark_read_btn.pack(side="left", padx=10)
        
        self.dynamic_action_btn = ctk.CTkButton(
            self.bulk_actions, 
            text="ARCHIVE ALL", 
            font=("Inter", 11, "bold"), 
            text_color=THEME["text_red"], 
            fg_color="transparent", 
            hover_color="#FEF2F2", 
            width=110, 
            height=32,
            command=self.archive_all
        )
        self.dynamic_action_btn.pack(side="left")

        # Search Bar
        self.search_frame = ctk.CTkFrame(self.card, fg_color="transparent")
        self.search_frame.pack(fill="x", padx=30, pady=(5, 10))
        self.search_entry = ctk.CTkEntry(self.search_frame, placeholder_text="Search notifications...", height=35, corner_radius=12, border_width=1, border_color=THEME["border"], fg_color="#F8FAFC", text_color="#1A1A1A", placeholder_text_color="#9CA3AF", font=("Inter", 12))
        self.search_entry.pack(fill="x")
        self.search_entry.bind("<KeyRelease>", lambda e: self.update_list(reset_scroll=False))

        # NAVIGATION
        self.nav_wrapper = ctk.CTkFrame(self.card, height=48, fg_color="transparent")
        self.nav_wrapper.pack(fill="x", padx=30, pady=5)
        self.nav_wrapper.pack_propagate(False)

        self.segments_container = ctk.CTkFrame(self.nav_wrapper, height=40, corner_radius=12, fg_color=THEME["nav_bg"], border_width=1, border_color=THEME["border"])
        self.segments_container.place(relx=0, rely=0.5, relwidth=0.72, anchor="w")

        self.tab_buttons = {}
        tabs = ["Today", "This Week", "This Month"]
        for i, tab in enumerate(tabs):
            btn = ctk.CTkButton(self.segments_container, text=tab, corner_radius=10, 
                                 fg_color="transparent", text_color=THEME["text_gray"], 
                                 font=("Inter", 11, "bold"), hover_color="#E2E8F0", 
                                 command=lambda t=tab: self.switch_tab(t))
            btn.place(relx=i/3 + 0.02, rely=0.5, relwidth=0.3, relheight=0.8, anchor="w")
            self.tab_buttons[tab] = btn

        self.archive_tab_btn = ctk.CTkButton(self.nav_wrapper, text="\uD83D\uDCC1 ARCHIVE", 
                                             height=40, corner_radius=12,
                                             fg_color=THEME["nav_bg"], text_color=THEME["text_gray"], 
                                             font=("Inter", 11, "bold"), border_width=1, border_color=THEME["border"],
                                             hover_color="#E2E8F0",
                                             command=lambda: self.switch_tab("Archive"))
        self.archive_tab_btn.place(relx=1.0, rely=0.5, relwidth=0.25, anchor="e")
        self.tab_buttons["Archive"] = self.archive_tab_btn

        self.scroll_frame = ctk.CTkScrollableFrame(self.card, fg_color="transparent", scrollbar_button_color=THEME["border"], scrollbar_button_hover_color=THEME["text_gray"])
        self.scroll_frame.pack(fill="both", expand=True, padx=20, pady=10)

        self.switch_tab("Today")

    def switch_tab(self, tab_name):
        self.current_category = tab_name
        
        if tab_name == "Archive":
            self.dynamic_action_btn.configure(text="RESTORE ALL", text_color=THEME["text_green"], 
                                             hover_color=THEME["green_hover"], command=self.restore_all)
        else:
            self.dynamic_action_btn.configure(text="ARCHIVE ALL", text_color=THEME["text_red"], 
                                             hover_color="#FEF2F2", command=self.archive_all)

        for name, btn in self.tab_buttons.items():
            if name == tab_name:
                if name == "Archive":
                    btn.configure(fg_color=THEME["white"], text_color=THEME["text_dark"], border_width=1)
                else:
                    btn.configure(fg_color=THEME["white"], text_color=THEME["primary"], border_width=0)
            else:
                if name == "Archive":
                    btn.configure(fg_color=THEME["nav_bg"], text_color=THEME["text_gray"], border_width=1)
                else:
                    btn.configure(fg_color="transparent", text_color=THEME["text_gray"], border_width=0)
                    
        self.update_list(reset_scroll=True)

    def get_filtered(self):
        query = self.search_entry.get().lower()
        filtered = []
        for n in self.notifications:
            matches_search = query in n["title"].lower() or query in n["description"].lower()
            if not matches_search: continue
            if self.current_category == "Archive":
                if n["is_deleted"]: filtered.append(n)
            else:
                if n["is_deleted"]: continue
                matches_tab = False
                if self.current_category == "Today": matches_tab = n["cat"] == "Today"
                elif self.current_category == "This Week": matches_tab = n["cat"] in ["Today", "This Week"]
                else: matches_tab = True 
                if matches_tab: filtered.append(n)
        
        if self.current_category == "Archive":
            filtered.sort(key=lambda x: x["deleted_at"], reverse=True)
        return filtered

    def mark_all_read(self):
        try:
            from backend import notification_service
            notification_service.mark_all_as_read()
        except:
            pass
            
        visible = self.get_filtered()
        visible_ids = [n["id"] for n in visible]
        for n in self.notifications:
            if n["id"] in visible_ids:
                n["is_read"] = True
                if n["id"] in self.widget_map:
                    widget = self.widget_map[n["id"]]
                    widget.is_read = True
                    widget.refresh_ui()

    def archive_all(self):
        try:
            from backend import notification_service
            notification_service.archive_all_notifications()
        except:
            pass
            
        visible = self.get_filtered()
        visible_ids = [n["id"] for n in visible]
        now = time.time()
        for n in self.notifications:
            if n["id"] in visible_ids:
                n["is_deleted"] = True
                n["deleted_at"] = now
        self.update_list(reset_scroll=True)

    def restore_all(self):
        try:
            from backend import notification_service
            notification_service.restore_all_notifications()
        except:
            pass
            
        visible = self.get_filtered()
        visible_ids = [n["id"] for n in visible]
        for n in self.notifications:
            if n["id"] in visible_ids:
                n["is_deleted"] = False
                n["deleted_at"] = 0
        self.update_list(reset_scroll=True)

    def handle_delete(self, n_id):
        try:
            from backend import notification_service
            notification_service.archive_notification(int(n_id))
        except:
            pass
            
        now = time.time()
        for n in self.notifications:
            if n["id"] == n_id:
                n["is_deleted"] = True
                n["deleted_at"] = now
                break
        
        # Surgical Fix: Remove just the widget to avoid white flash
        if n_id in self.widget_map:
            widget = self.widget_map.pop(n_id)
            widget.destroy()
            
        # If the list is now empty, refresh to show empty state message
        if not self.get_filtered():
            self.update_list(reset_scroll=False)

    def handle_recover(self, n_id):
        try:
            from backend import notification_service
            notification_service.restore_notification(int(n_id))
        except:
            pass
            
        for n in self.notifications:
            if n["id"] == n_id:
                n["is_deleted"] = False
                n["deleted_at"] = 0
                break
        
        # Surgical Fix: Remove just the widget to avoid white flash
        if n_id in self.widget_map:
            widget = self.widget_map.pop(n_id)
            widget.destroy()
            
        # If the list is now empty, refresh to show empty state message
        if not self.get_filtered():
            self.update_list(reset_scroll=False)

    def handle_toggle(self, n_id):
        for n in self.notifications:
            if n["id"] == n_id:
                if not n["is_read"]:
                    n["is_read"] = True
                    try:
                        from backend import notification_service
                        notification_service.mark_as_read(int(n_id))
                    except:
                        pass
                
                n["is_expanded"] = not n.get("is_expanded", False)
                if n_id in self.widget_map:
                    widget = self.widget_map[n_id]
                    widget.is_read = True
                    widget.is_expanded = n["is_expanded"]
                    widget.refresh_ui()
                break

    def update_list(self, reset_scroll=False):
        if reset_scroll:
            try:
                self.scroll_frame._parent_canvas.yview_moveto(0)
            except:
                pass
        for child in self.scroll_frame.winfo_children():
            child.destroy()
        self.widget_map = {}
        filtered = self.get_filtered()
        if not filtered:
            msg = "Your archive is empty." if self.current_category == "Archive" else "No notifications found."
            ctk.CTkLabel(self.scroll_frame, text=msg, font=("Inter", 13), text_color=THEME["text_gray"]).pack(pady=40)
            return
        for i, item in enumerate(filtered):
            is_last = (i == len(filtered) - 1)
            row = NotificationItem(self.scroll_frame, item, 
                                   on_delete=self.handle_delete, 
                                   on_toggle=self.handle_toggle,
                                   on_recover=self.handle_recover,
                                   is_archived_mode=(self.current_category == "Archive"),
                                   is_last=is_last)
            row.pack(fill="x", padx=8)
            self.widget_map[item["id"]] = row

if __name__ == "__main__":
    app = NotificationsApp()
    app.mainloop()