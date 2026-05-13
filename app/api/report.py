from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from app.database import get_session  # DB bağlantısı için doğru import
from app.models.report import Report
from app.models.driver import EVDriver # Driver kontrolü yapmak istersen lazım

router = APIRouter(prefix="/api/report", tags=["Report"])

@router.post("/issue")
def report_issue(report_data: dict, session: Session = Depends(get_session)):
    try:
        # 1. Gelen veride gerekli alanlar var mı kontrolü (Basit bir validation)
        if "driver_id" not in report_data or "message" not in report_data:
            raise HTTPException(status_code=400, detail="Missing driver_id or message")

        # 2. Opsiyonel: Gerçekten böyle bir driver var mı kontrolü?
        # (Bu kısım sistemin tutarlılığı için iyi olur)
        driver = session.get(EVDriver, report_data["driver_id"])
        if not driver:
            raise HTTPException(status_code=404, detail="Driver not found")

        # 3. Yeni rapor nesnesini oluştur
        new_report = Report(
            driver_id=report_data["driver_id"],
            message=report_data["message"]
        )
        
        # 4. Veritabanına kaydet
        session.add(new_report)
        session.commit()
        session.refresh(new_report)
        
        return {
            "status": "success",
            "message": "Report saved successfully", 
            "report_id": new_report.id
        }

    except HTTPException as http_exc:
        # FastAPI'nin kendi fırlattığı hataları olduğu gibi ilet
        raise http_exc
    except Exception as e:
        # Beklenmedik bir hata olursa (DB bağlantısı vb.) geri al ve 500 dön
        session.rollback()
        print(f"Report Error: {e}") # Konsolda hatayı görebilmen için
        raise HTTPException(status_code=500, detail="An internal server error occurred")