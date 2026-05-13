from sqlmodel import Session
from datetime import datetime
from app.models.notification import Notification # Model yolunu kontrol et

def create_system_notification(db: Session, driver_id: int, n_type: str, message: str):
    """
    Sistemin her yerinden bildirim oluşturmak için kullanılan yardımcı fonksiyon.
    n_type: 'reservation', 'session', 'alert', 'info'
    """
    try:
        new_notif = Notification(
            driver_id=driver_id,
            type=n_type,
            message=message,
            isRead=False,
            sentAt=datetime.utcnow()
        )
        db.add(new_notif)
        db.commit()
        db.refresh(new_notif)
        return new_notif
    except Exception as e:
        print(f"Notification error: {e}")
        db.rollback()
        return None