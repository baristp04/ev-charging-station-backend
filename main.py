from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database import create_db_and_tables
from app.api.reservation import station_router
from app.api.maintenance import maintenance_router
from app.api.analytics import analytics_router

# Model imports (CRITICAL: These must be imported here so SQLModel knows they exist before creating tables)
from app.models.driver import EVDriver
from app.models.vehicle import Vehicle
from app.models.operationspecialist import OperationsSpecialist  # ADDED
from app.models.station import ChargingStation
from app.models.charger import Charger
from app.models.reservation import Reservation
from app.models.session import ChargingSession
from app.models.payment import Payment
from app.models.SystemAnalyst import SystemAnalyst               # ADDED
from app.models.EVTechnician import EVTechnician                 # ADDED
from app.models.notification import Notification                 # ADDED

# 1. Define the lifespan event (The modern replacement for on_event)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # This runs exactly once when the server starts up
    create_db_and_tables()
    yield
    # Anything after the 'yield' would run when the server shuts down

# 2. Start the FastAPI app and attach the lifespan
app = FastAPI(title="EV Charging Station Management System", lifespan=lifespan)

# 3. Include Routers
app.include_router(station_router)
app.include_router(maintenance_router)
app.include_router(analytics_router)

@app.get("/")
def root():
    return {"message": "EV Charging System API is running on PostgreSQL!"}

# ... your existing code ...
@app.get("/")
def root():
    return {"message": "EV Charging System API is running on PostgreSQL!"}

# ADD THIS TO THE VERY BOTTOM:
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)


    from app.api.analytics import analytics_router
    app.include_router(analytics_router)