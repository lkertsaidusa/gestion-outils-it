import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

def _init_notifications_table():
    """Crée la table notifications si elle n'existe pas."""
    try:
        from database.database import execute, table_exists
        if not table_exists("notifications"):
            execute("""
                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type VARCHAR(50) NOT NULL,
                    content TEXT NOT NULL,
                    details TEXT,
                    related_id VARCHAR(50),
                    actor_name VARCHAR(100),
                    actor_role VARCHAR(50),
                    is_read INTEGER DEFAULT 0,
                    is_deleted INTEGER DEFAULT 0,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            logger.info("Notifications table created")
        else:
            # S'assurer que les colonnes existent
            try:
                execute("ALTER TABLE notifications ADD COLUMN details TEXT")
            except Exception: pass
            try:
                execute("ALTER TABLE notifications ADD COLUMN is_read INTEGER DEFAULT 0")
            except Exception: pass
            try:
                execute("ALTER TABLE notifications ADD COLUMN is_deleted INTEGER DEFAULT 0")
            except Exception: pass
    except Exception as e:
        logger.warning(f"Could not init notifications table: {e}")

# Initialiser la table au chargement du module
_init_notifications_table()

def archive_notification(notification_id: int):
    """Archive une notification (suppression logique)."""
    try:
        from database.database import execute
        execute("UPDATE notifications SET is_deleted = 1 WHERE id = ?", (notification_id,))
        return True
    except Exception as e:
        logger.error(f"Failed to archive notification: {e}")
        return False

def restore_notification(notification_id: int):
    """Restaure une notification archivée."""
    try:
        from database.database import execute
        execute("UPDATE notifications SET is_deleted = 0 WHERE id = ?", (notification_id,))
        return True
    except Exception as e:
        logger.error(f"Failed to restore notification: {e}")
        return False

def archive_all_notifications():
    """Archive toutes les notifications."""
    try:
        from database.database import execute
        execute("UPDATE notifications SET is_deleted = 1")
        return True
    except Exception as e:
        logger.error(f"Failed to archive all notifications: {e}")
        return False

def restore_all_notifications():
    """Restaure toutes les notifications."""
    try:
        from database.database import execute
        execute("UPDATE notifications SET is_deleted = 0")
        return True
    except Exception as e:
        logger.error(f"Failed to restore all notifications: {e}")
        return False

def mark_as_read(notification_id: int):
    """Marque une notification comme lue."""
    try:
        from database.database import execute
        execute("UPDATE notifications SET is_read = 1 WHERE id = ?", (notification_id,))
        return True
    except Exception as e:
        logger.error(f"Failed to mark notification as read: {e}")
        return False

def mark_all_as_read():
    """Marque toutes les notifications comme lues."""
    try:
        from database.database import execute
        execute("UPDATE notifications SET is_read = 1")
        return True
    except Exception as e:
        logger.error(f"Failed to mark all notifications as read: {e}")
        return False

def get_unread_count():
    """Récupère le nombre de notifications non lues."""
    try:
        from database.database import fetchone
        result = fetchone("SELECT COUNT(*) as count FROM notifications WHERE is_read = 0")
        return result['count'] if result else 0
    except Exception as e:
        logger.error(f"Failed to get unread count: {e}")
        return 0

# ═══════════════════════════════════════════════════
# ⚠️ CONFIGURATION EMAIL ⚠️
# ═══════════════════════════════════════════════════
DESTINATION_EMAIL = "saidlepro0@gmail.com"
SENDER_EMAIL = "saidlepro0@gmail.com"
SENDER_PASSWORD = "lmoy uzqv fplk haab"
# ═══════════════════════════════════════════════════════════

def send_inventory_notification(action: str, item_name: str, item_id: str, details: Optional[str] = None, user_name: str = "System", user_role: str = "Unknown"):
    """
    Sends an email notification when an inventory item is modified.
    Also stores the notification in the database for the CEO to view.
    """
    # Stocker la notification dans la DB
    try:
        from database.database import execute
        
        # Format action verb correctly
        if action.upper() == "ADD":
            action_verb = "ADDED"
        elif action.upper() == "UPDATE":
            action_verb = "UPDATED"
        elif action.upper() == "DELETE":
            action_verb = "DELETED"
        else:
            action_verb = f"{action}ED"
            
        # Example: Equipment: [LAPTOP DELL] (#ID: SN12345) was UPDATED by Said (CEO)
        content = f"Equipment: [{item_name.upper()}] (#ID: {str(item_id).upper()}) was {action_verb} by {user_name} ({user_role})"
        
        execute(
            """
            INSERT INTO notifications (type, content, details, related_id, actor_name, actor_role)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (f"INVENTORY_{action}", content, details, item_id, user_name, user_role)
        )
    except Exception as e:
        logger.warning(f"Failed to store notification: {e}")

    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = f"TechManage System <{SENDER_EMAIL}>"
        msg['To'] = DESTINATION_EMAIL
        
        subject_emoji = "➕" if action == "ADD" else "📝" if action == "UPDATE" else "🗑️"
        msg['Subject'] = f"{subject_emoji} [Inventory Alert] Item {action}: {item_name}"
        
        action_color = "#2FC967" if action == "ADD" else "#F97316" if action == "UPDATE" else "#EF4444"
        
        # HTML message body
        html_body = f"""
        <html>
            <body style="font-family: 'Segoe UI', Arial, sans-serif; padding: 20px; background-color: #f0f4f9;">
                <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 20px; padding: 30px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                    <h2 style="color: #166FFF; margin-bottom: 20px;">📦 Inventory Modification Alert</h2>

                    <div style="background: #f8fafc; padding: 15px; border-radius: 10px; margin-bottom: 20px; border-left: 5px solid {action_color};">
                        <p style="margin: 5px 0;"><strong>Action:</strong> <span style="color: {action_color}; font-weight: bold;">{action}</span></p>
                        <p style="margin: 5px 0;"><strong>Item Name:</strong> {item_name}</p>
                        <p style="margin: 5px 0;"><strong>Item ID/SN:</strong> {item_id}</p>
                    </div>

                    {f'''
                    <div style="background: #ffffff; padding: 20px; border: 1px solid #E5E7EB; border-radius: 8px;">
                        <h3 style="color: #1E293B; margin-top: 0;">Details:</h3>
                        <p style="color: #4B5563; line-height: 1.6; white-space: pre-wrap;">{details}</p>
                    </div>
                    ''' if details else ''}

                    <hr style="border: none; border-top: 1px solid #E5E7EB; margin: 20px 0;">

                    <p style="color: #9CA3AF; font-size: 12px; text-align: center; margin: 0;">
                        This is an automated notification from your TechManage System.
                    </p>
                </div>
            </body>
        </html>
        """
        
        msg.attach(MIMEText(html_body, 'html'))
        
        # Send via Gmail SMTP
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        logger.info(f"✅ Inventory notification ({action}) sent successfully to {DESTINATION_EMAIL}")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to send inventory notification: {e}")
        return False

def send_bulk_inventory_notification(action: str, items: List[Dict[str, Any]], user_name: str, details: Optional[str] = None, user_role: str = "Unknown"):
    """
    Sends a single email notification for multiple inventory modifications.
    Also stores a bulk notification in the database.
    """
    # Stocker la notification groupée dans la DB
    try:
        from database.database import execute
        
        # Format action verb correctly
        if action.upper() == "ADD":
            action_verb = "ADDED"
        elif action.upper() == "UPDATE":
            action_verb = "UPDATED"
        elif action.upper() == "DELETE":
            action_verb = "DELETED"
        else:
            action_verb = f"{action}ED"
            
        content = f"BULK {action_verb}: {len(items)} items were processed by {user_name} ({user_role})"
        
        execute(
            """
            INSERT INTO notifications (type, content, details, actor_name, actor_role)
            VALUES (?, ?, ?, ?, ?)
            """,
            (f"INVENTORY_BULK_{action}", content, details, user_name, user_role)
        )
    except Exception as e:
        logger.warning(f"Failed to store bulk notification: {e}")

    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = f"TechManage System <{SENDER_EMAIL}>"
        msg['To'] = DESTINATION_EMAIL
        
        subject_emoji = "📝" if action == "UPDATE" else "🗑️"
        msg['Subject'] = f"{subject_emoji} [Inventory Bulk Alert] {len(items)} items {action}D"
        
        action_color = "#F97316" if action == "UPDATE" else "#EF4444"
        
        # Build items table
        items_html = ""
        for item in items:
            name = item.get('name', 'Unknown')
            sn = item.get('serial_number', 'N/A')
            items_html += f"<tr><td style='padding: 8px; border-bottom: 1px solid #E5E7EB;'>{name}</td><td style='padding: 8px; border-bottom: 1px solid #E5E7EB;'>{sn}</td></tr>"

        # HTML message body
        html_body = f"""
        <html>
            <body style="font-family: 'Segoe UI', Arial, sans-serif; padding: 20px; background-color: #f0f4f9;">
                <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 20px; padding: 30px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                    <h2 style="color: #166FFF; margin-bottom: 20px;">📦 Bulk Inventory Modification Alert</h2>

                    <div style="background: #f8fafc; padding: 15px; border-radius: 10px; margin-bottom: 20px; border-left: 5px solid {action_color};">
                        <p style="margin: 5px 0;"><strong>Action:</strong> <span style="color: {action_color}; font-weight: bold;">BULK {action}</span></p>
                        <p style="margin: 5px 0;"><strong>Performed by:</strong> {user_name}</p>
                        <p style="margin: 5px 0;"><strong>Total Items:</strong> {len(items)}</p>
                    </div>

                    {f'''
                    <div style="background: #ffffff; padding: 20px; border: 1px solid #E5E7EB; border-radius: 8px; margin-bottom: 20px;">
                        <h3 style="color: #1E293B; margin-top: 0;">Description:</h3>
                        <p style="color: #4B5563; line-height: 1.6;">{details}</p>
                    </div>
                    ''' if details else ''}

                    <div style="margin-bottom: 20px;">
                        <h3 style="color: #1E293B;">Affected Items:</h3>
                        <table style="width: 100%; border-collapse: collapse;">
                            <thead>
                                <tr style="background-color: #F1F5F9;">
                                    <th style="padding: 10px; text-align: left; border-bottom: 2px solid #E5E7EB;">Item Name</th>
                                    <th style="padding: 10px; text-align: left; border-bottom: 2px solid #E5E7EB;">Serial Number</th>
                                </tr>
                            </thead>
                            <tbody>
                                {items_html}
                            </tbody>
                        </table>
                    </div>

                    <hr style="border: none; border-top: 1px solid #E5E7EB; margin: 20px 0;">

                    <p style="color: #9CA3AF; font-size: 12px; text-align: center; margin: 0;">
                        This is an automated notification from your TechManage System.
                    </p>
                </div>
            </body>
        </html>
        """
        
        msg.attach(MIMEText(html_body, 'html'))
        
        # Send via Gmail SMTP
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        logger.info(f"✅ Bulk inventory notification sent successfully to {DESTINATION_EMAIL}")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to send bulk inventory notification: {e}")
        return False

def get_notifications():
    """
    Récupère toutes les notifications d'inventaire depuis la base de données.
    """
    try:
        from database.database import fetchall
        notifications = fetchall(
            """
            SELECT id, type, content, details, related_id, actor_name, actor_role, is_read, is_deleted, timestamp
            FROM notifications
            WHERE type LIKE 'INVENTORY%'
            ORDER BY timestamp DESC
            LIMIT 50
            """
        )
        return notifications
    except Exception as e:
        logger.error(f"Failed to fetch notifications: {e}")
        return []

