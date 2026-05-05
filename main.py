from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database import create_db_and_tables
from app.api.reservation import station_router 
from app.api.maintenance import maintenance_router
from app.api.navigation import navigation_router
from app.api.analytics import analytics_router
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import os

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

# Define the lifespan event (The modern replacement for on_event)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # This runs exactly once when the server starts up
    create_db_and_tables()
    yield
    # Anything after the 'yield' would run when the server shuts down

app = FastAPI(title="EV Charging Station Management System", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="."), name="static")

app.include_router(station_router)
app.include_router(maintenance_router)
app.include_router(navigation_router)
app.include_router(analytics_router)

@app.get("/")
def root():
    return {"message": "EV Charging System API is running"}

@app.get("/map", response_class=HTMLResponse)
def get_map():
    with open("navigation.html", "r", encoding="utf-8") as f:
        html = f.read()
    api_key = os.getenv("GOOGLE_MAPS_API_KEY", "")
    return html.replace("API_KEY", api_key)