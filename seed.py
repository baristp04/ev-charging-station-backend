"""
seed.py — Populate the EV Charging DB with 3 months of realistic data.
Run from your project root:  python seed.py
Requires: .env file with DATABASE_URL set (same as your FastAPI app).
"""

import os
import random
from datetime import datetime, timedelta
from dotenv import load_dotenv
from sqlmodel import create_engine, Session, SQLModel, select

# ── Import your models exactly as FastAPI does ──────────────────────────────
from app.models.station import ChargingStation
from app.models.charger import Charger
from app.models.driver import EVDriver
from app.models.vehicle import Vehicle
from app.models.reservation import Reservation
from app.models.session import ChargingSession
from app.models.payment import Payment
from app.models.operationspecialist import OperationsSpecialist
from app.models.notification import Notification

# ── DB connection (reuses your .env) ────────────────────────────────────────
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL, echo=False)
SQLModel.metadata.create_all(engine)   # safety: create tables if missing

# ── Helpers ──────────────────────────────────────────────────────────────────
def rand_dt(days_ago_max: int, days_ago_min: int = 0) -> datetime:
    """Random datetime between days_ago_min and days_ago_max days in the past."""
    delta_days = random.randint(days_ago_min, days_ago_max)
    delta_hours = random.randint(6, 22)        # realistic operating hours
    delta_minutes = random.choice([0, 15, 30, 45])
    return datetime.utcnow() - timedelta(days=delta_days, hours=delta_hours, minutes=delta_minutes)

CONNECTOR_TYPES = ["Type 2", "CCS", "CHAdeMO"]
CHARGER_TYPES   = ["AC", "DC"]
POWER_OUTPUTS   = [22.0, 50.0, 150.0]          # kW
PRICE_MAP       = {22.0: 3.5, 50.0: 4.0, 150.0: 5.5}   # TL / kWh
PAYMENT_METHODS = ["credit_card", "debit_card", "wallet"]

# ── Seed ─────────────────────────────────────────────────────────────────────
with Session(engine) as session:

    # ── 1. Operations Specialist ─────────────────────────────────────────────
    existing_op = session.exec(select(OperationsSpecialist).limit(1)).first()
    if existing_op:
        op = existing_op
        print("Operator already exists, skipping.")
    else:
        op = OperationsSpecialist(
            name="Ahmet Yılmaz",
            email="ahmet@evcharge.tr",
            phone="05551234567",
            passwordHash="hashed_pw_placeholder"
        )
        session.add(op)
        session.commit()
        session.refresh(op)
        print(f"Created operator: {op.name}")

    # ── 2. Charging Stations (5 real İzmir locations) ────────────────────────
    STATIONS_DATA = [
        ("Karşıyaka Hub",     "Karşıyaka, İzmir",   38.4565, 27.1123),
        ("Bornova Station",   "Bornova, İzmir",      38.4667, 27.2167),
        ("Alsancak Point",    "Alsancak, İzmir",     38.4382, 27.1440),
        ("Buca Charge",       "Buca, İzmir",         38.3833, 27.1833),
        ("Konak Plaza",       "Konak, İzmir",        38.4189, 27.1287),
    ]

    stations = []
    existing_stations = session.exec(select(ChargingStation)).all()
    if existing_stations:
        stations = existing_stations
        print(f"Using {len(stations)} existing stations.")
    else:
        for name, loc, lat, lon in STATIONS_DATA:
            st = ChargingStation(
                name=name, location=loc,
                latitude=lat, longitude=lon,
                status="available", operator_id=op.operatorID
            )
            session.add(st)
        session.commit()
        stations = session.exec(select(ChargingStation)).all()
        print(f"Created {len(stations)} stations.")

    # ── 3. Chargers (3 per station, varied specs) ────────────────────────────
    chargers = []
    existing_chargers = session.exec(select(Charger)).all()
    if existing_chargers:
        chargers = existing_chargers
        print(f"Using {len(chargers)} existing chargers.")
    else:
        specs = [
            ("AC",  22.0,  "Type 2"),
            ("DC",  50.0,  "CCS"),
            ("DC", 150.0,  "CHAdeMO"),
        ]
        for st in stations:
            for ctype, power, connector in specs:
                c = Charger(
                    type=ctype,
                    powerOutput=power,
                    connectorType=connector,
                    pricePerKwh=PRICE_MAP[power],
                    status="available",
                    station_id=st.stationID
                )
                session.add(c)
        session.commit()
        chargers = session.exec(select(Charger)).all()
        print(f"Created {len(chargers)} chargers.")

    # ── 4. EV Drivers (10 drivers) ───────────────────────────────────────────
    drivers = []
    existing_drivers = session.exec(select(EVDriver)).all()
    if existing_drivers:
        drivers = existing_drivers
        print(f"Using {len(drivers)} existing drivers.")
    else:
        DRIVER_DATA = [
            ("Hasan Akpınar",  "hasan@mail.com",  "05551110001"),
            ("Merve Özkan",    "merve@mail.com",  "05551110002"),
            ("Barış Tepe",     "baris@mail.com",  "05551110003"),
            ("Sercan Coşar",   "sercan@mail.com", "05551110004"),
            ("Ayşe Kaya",      "ayse@mail.com",   "05551110005"),
            ("Murat Demir",    "murat@mail.com",  "05551110006"),
            ("Elif Şahin",     "elif@mail.com",   "05551110007"),
            ("Kemal Arslan",   "kemal@mail.com",  "05551110008"),
            ("Zeynep Çelik",   "zeynep@mail.com", "05551110009"),
            ("Tolga Yıldız",   "tolga@mail.com",  "05551110010"),
        ]
        for name, email, phone in DRIVER_DATA:
            d = EVDriver(name=name, email=email, phoneNumber=phone, passwordHash="hashed_pw")
            session.add(d)
        session.commit()
        drivers = session.exec(select(EVDriver)).all()
        print(f"Created {len(drivers)} drivers.")

    # ── 5. Vehicles (1–2 per driver) ─────────────────────────────────────────
    vehicles = []
    existing_vehicles = session.exec(select(Vehicle)).all()
    if existing_vehicles:
        vehicles = existing_vehicles
        print(f"Using {len(vehicles)} existing vehicles.")
    else:
        VEHICLE_DATA = [
            ("Tesla",       "Model 3",   75.0, "CCS"),
            ("Tesla",       "Model Y",   82.0, "CCS"),
            ("Renault",     "Zoe",       52.0, "Type 2"),
            ("BMW",         "i3",        42.2, "Type 2"),
            ("Hyundai",     "Ioniq 5",   77.4, "CHAdeMO"),
            ("Kia",         "EV6",       77.4, "CCS"),
            ("VW",          "ID.4",      82.0, "Type 2"),
            ("Nissan",      "Leaf",      40.0, "CHAdeMO"),
            ("Mercedes",    "EQC",       80.0, "CCS"),
            ("Audi",        "e-tron",    95.0, "CCS"),
            ("Peugeot",     "e-208",     50.0, "Type 2"),
            ("Fiat",        "500e",      42.0, "Type 2"),
        ]
        plate_counter = 1
        for i, driver in enumerate(drivers):
            num_vehicles = random.randint(1, 2)
            for _ in range(num_vehicles):
                vd = VEHICLE_DATA[plate_counter % len(VEHICLE_DATA)]
                v = Vehicle(
                    brand=vd[0], model=vd[1],
                    plateNumber=f"35 EV {1000 + plate_counter:04d}",
                    batteryCapacity=vd[2],
                    connectorType=vd[3],
                    driver_id=driver.driverID
                )
                session.add(v)
                plate_counter += 1
        session.commit()
        vehicles = session.exec(select(Vehicle)).all()
        print(f"Created {len(vehicles)} vehicles.")

    # ── 6. Reservations + Sessions + Payments (90 days of history) ───────────
    existing_res = session.exec(select(Reservation)).all()
    if existing_res:
        print(f"Using {len(existing_res)} existing reservations — skipping session/payment seed.")
    else:
        # Build a charger→connector lookup for compatibility matching
        charger_by_connector: dict[str, list[Charger]] = {}
        for c in chargers:
            charger_by_connector.setdefault(c.connectorType, []).append(c)

        sessions_created = 0
        res_created      = 0

        # ~6 sessions per day × 90 days = ~540 completed sessions
        for days_ago in range(1, 91):
            daily_count = random.randint(3, 9)
            for _ in range(daily_count):
                # Pick a random vehicle and find a compatible charger
                vehicle = random.choice(vehicles)
                compatible = charger_by_connector.get(vehicle.connectorType, [])
                if not compatible:
                    continue
                charger = random.choice(compatible)

                # Build realistic time window (30 min – 2 hours)
                duration_minutes = random.choice([30, 45, 60, 75, 90, 105, 120])
                base_hour = random.randint(7, 21)
                base_minute = random.choice([0, 15, 30, 45])
                start_dt = (datetime.utcnow()
                            - timedelta(days=days_ago)
                            + timedelta(hours=base_hour, minutes=base_minute))
                end_dt   = start_dt + timedelta(minutes=duration_minutes)

                # Reservation
                res = Reservation(
                    date=start_dt,
                    startTime=start_dt,
                    endTime=end_dt,
                    status="completed",
                    driver_id=vehicle.driver_id,
                    charger_id=charger.chargerID,
                    vehicle_id=vehicle.vehicleID
                )
                session.add(res)
                session.flush()   # get reservationID

                # Energy consumed: realistic % of battery filled
                energy_kwh = round(
                    charger.powerOutput * (duration_minutes / 60) * random.uniform(0.7, 1.0),
                    2
                )
                total_cost = round(energy_kwh * charger.pricePerKwh, 2)

                # Charging Session
                cs = ChargingSession(
                    startTime=start_dt,
                    endTime=end_dt,
                    energyConsumed=energy_kwh,
                    totalCost=total_cost,
                    status="completed",
                    reservation_id=res.reservationID
                )
                session.add(cs)
                session.flush()

                # Payment
                pay = Payment(
                    amount=total_cost,
                    method=random.choice(PAYMENT_METHODS),
                    status="completed",
                    transactionDate=end_dt,
                    receiptURL=f"https://receipts.evcharge.tr/{res.reservationID}",
                    session_id=cs.sessionID
                )
                session.add(pay)
                sessions_created += 1
                res_created += 1

        session.commit()
        print(f"Created {res_created} reservations, {sessions_created} sessions & payments.")

print("\n✅ Seed complete. Your database is ready for UC-04.")
