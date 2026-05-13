from app.database import get_session
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.models.driver import EVDriver
from app.models.card import Card
from app.utils.notifications import create_system_notification

router = APIRouter(prefix="/api/wallet", tags=["wallet"])

# Bring the current balance of driver
@router.get("/balance/{driver_id}")
def get_wallet_balance(driver_id: int, session: Session = Depends(get_session)):
    driver = session.get(EVDriver, driver_id)
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")
    
    # --- LOW BALANCE NOTIFICATION LOGIC ---
    if driver.balance < 20:
        # Burada sadece bildirim oluşturuyoruz. 
        # Eğer "Notification" tablanda 'is_read' gibi bir kontrolün varsa, 
        # mükerrer bildirimleri engellemek için son bildirimi kontrol eden bir logic de eklenebilir.
        create_system_notification(
            session, 
            driver_id=driver_id, 
            n_type="system", # Tipini 'system' veya 'alert' yapabilirsin
            message=f"Low balance alert! Your balance is ₺{driver.balance:.2f}. Please top up soon."
        )
    # --------------------------------------
    return {"balance": driver.balance}

'''
# Add money to wallet (top-up)
@router.post("/deposit")
def deposit_to_wallet(payload: dict, session: Session = Depends(get_session)):
    driver_id = payload.get("driver_id")
    amount = payload.get("amount")
    
    # Burada 'EVDriver' sınıf ismini kullanıyoruz, 
    # 'driver_obj' ise bizim yeni yarattığımız değişken ismi.
    driver_obj = session.get(EVDriver, driver_id) 
    
    if not driver_obj:
        raise HTTPException(status_code=404, detail="Driver not found")
    
    if amount is None or amount <= 0:
        raise HTTPException(status_code=400, detail="Invalid amount")
    
    # Bakiyeyi güncelle
    driver_obj.balance += amount
    
    session.add(driver_obj)
    session.commit()
    session.refresh(driver_obj)
    
    return {"message": "Success", "new_balance": driver_obj.balance}

    '''

# 1. Kullanıcının kayıtlı kartlarını listeleme
@router.get("/cards/{driver_id}")
def get_user_cards(driver_id: int, session: Session = Depends(get_session)):
    cards = session.exec(select(Card).where(Card.driver_id == driver_id)).all()
    return cards

# 2. Yeni kart ekleme
@router.post("/cards")
def add_new_card(card_data: Card, session: Session = Depends(get_session)):
    # Küçük bir güvenlik: Kartın zaten var olup olmadığını kontrol edebilirsin
    session.add(card_data)
    session.commit()
    session.refresh(card_data)
    return {"message": "Card saved successfully!", "card": card_data}

# 3. Bakiye yükleme (Top-up) işlemi
@router.post("/top-up")
def top_up_balance(driver_id: int, amount: float, card_id: int, session: Session = Depends(get_session)):
    driver = session.get(EVDriver, driver_id)
    card = session.get(Card, card_id)
    
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")
    if not card or card.driver_id != driver_id:
        raise HTTPException(status_code=404, detail="Payment method not found or unauthorized")

    # Burada normalde bir banka API'sine gidilir ama biz simüle ediyoruz
    # Ödeme başarılı kabul edildi:
    driver.balance += amount
    session.add(driver)
    session.commit()
    session.refresh(driver)

    # Bakiye yüklendikten sonra:
    create_system_notification(
        session, 
        driver_id=driver_id, 
        n_type="session", 
        message=f"Successfully topped up ₺{amount} to your wallet."
    )
    
    return {
        "message": f"Successfully added ₺{amount}",
        "new_balance": driver.balance
    }