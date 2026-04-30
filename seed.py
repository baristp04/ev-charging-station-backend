# seed.py
from app.database import create_db_and_tables, engine
from app.models.station import ChargingStation
from app.models.charger import Charger
from app.models.reservation import Reservation
from app.models.session import ChargingSession
from app.models.payment import Payment
from app.models.driver import EVDriver
from app.models.vehicle import Vehicle
from sqlmodel import Session

create_db_and_tables()

with Session(engine) as session:
    stations = [
        ChargingStation(name='Karşıyaka Hub', location='Karşıyaka, İzmir', latitude=38.4553, longitude=27.1174, status='available'),
        ChargingStation(name='Bornova Station', location='Bornova, İzmir', latitude=38.4648, longitude=27.2162, status='occupied'),
        ChargingStation(name='Buca Point', location='Buca, İzmir', latitude=38.3834, longitude=27.1800, status='offline'),
        ChargingStation(name='Alsancak Charger', location='Alsancak, İzmir', latitude=38.4378, longitude=27.1435, status='available'),
    ]
    for s in stations:
        session.add(s)
    session.commit()
    print('Test verileri eklendi!')

    #python seed.py komutunu çalıştırarak bu dosyayı çalıştırabilirsiniz. Bu, veritabanına örnek istasyon verilerini ekleyecektir. İsterseniz burada daha fazla veri ekleyebilir veya diğer modeller için de benzer şekilde test verileri oluşturabilirsiniz.