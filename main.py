from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api import charging
from app.database import create_db_and_tables
from app.api.reservation import station_router 
from app.api.maintenance import maintenance_router
from app.api.navigation import navigation_router
from app.api import vehicleRegistration
from app.api.analytics import analytics_router  # Router imported from main
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import os
from pathlib import Path  # Library used for safe and cross-platform path handling
from app.api.auth import auth_router
from app.api.vehicleRegistration import router as vehicle_router
from app.api.payment import router as payment_router
from app.api.notification import router as notification_router
from app.api.report import router as report_router



# Import all models (including the ones newly added in main)
from app.models.driver import EVDriver
from app.models.vehicle import Vehicle
from app.models.operationspecialist import OperationsSpecialist  
from app.models.station import ChargingStation
from app.models.charger import Charger
from app.models.reservation import Reservation
from app.models.session import ChargingSession
from app.models.payment import Payment
from app.models.SystemAnalyst import SystemAnalyst               
from app.models.EVTechnician import EVTechnician                 
from app.models.notification import Notification
from app.models.report import Report                 

# Lifespan event handler (recommended over on_event in modern FastAPI)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # This block runs once when the server starts
    create_db_and_tables()
    yield
    # Code after yield runs when the server shuts down

app = FastAPI(title="EV Charging Station Management System", lifespan=lifespan)

# Configure CORS middleware (currently allows all origins, methods, and headers)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files directory
app.mount("/static", StaticFiles(directory="."), name="static")

# Register all routers
app.include_router(station_router)
app.include_router(maintenance_router)
app.include_router(navigation_router)
app.include_router(charging.router)
app.include_router(vehicleRegistration.router)
app.include_router(analytics_router)  # Router integrated from main
app.include_router(auth_router)
app.include_router(vehicle_router)  # Vehicle registration endpoints
app.include_router(payment_router)
app.include_router(notification_router)
app.include_router(report_router)

@app.get("/")
def root():
    return {"message": "EV Charging System API is running"}

# Configuration endpoint for frontend usage
@app.get("/api/config")
def get_config():
    """Returns configuration values required by the frontend"""
    return {
        "google_maps_api_key": os.getenv("GOOGLE_MAPS_API_KEY", "")
    }

# Map endpoint with safe path resolution
@app.get("/map", response_class=HTMLResponse)
def get_map():
    """Serves the navigation.html file used in the frontend"""
    frontend_nav_path = Path(__file__).parent.parent / "ev-charging-station-frontend" / "navigation.html"
    try:
        with open(frontend_nav_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>navigation.html not found</h1>"