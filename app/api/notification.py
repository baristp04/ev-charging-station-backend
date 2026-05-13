from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select, desc
from typing import List
from app.database import get_session
from app.models.notification import Notification # Modelinin yolunu kontrol et

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])

# 1. Bildirimleri Listeleme
@router.get("/{driver_id}", response_model=List[Notification])
def get_notifications(driver_id: int, db: Session = Depends(get_session)):
    # SQLModel tarzı sorgu: select(Notification)
    statement = select(Notification).where(
        Notification.driver_id == driver_id
    ).order_by(desc(Notification.sentAt))
    
    results = db.exec(statement).all()
    return results

# 2. Bildirimi Okundu Olarak İşaretleme
@router.put("/read/{notification_id}")
def mark_notification_as_read(notification_id: int, db: Session = Depends(get_session)):
    statement = select(Notification).where(Notification.notificationID == notification_id)
    notification = db.exec(statement).first()
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    notification.isRead = True
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return {"status": "success", "message": "Notification marked as read"}

# 3. Tümünü Okundu Yap (Bonus: Hocalar sever)
@router.put("/read-all/{driver_id}")
def mark_all_as_read(driver_id: int, db: Session = Depends(get_session)):
    statement = select(Notification).where(
        Notification.driver_id == driver_id, 
        Notification.isRead == False
    )
    unread_notifications = db.exec(statement).all()
    
    for notif in unread_notifications:
        notif.isRead = True
        db.add(notif)
    
    db.commit()
    return {"status": "success", "message": f"{len(unread_notifications)} notifications marked as read"}