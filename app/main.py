from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base
from .routes import routes_endpoints, trips, requests, matching

# Auto-create the SQLite tables on startup
Base.metadata.create_all(bind=engine)

# Initialize the FastAPI App
app = FastAPI(
    title="Carpooling Real-time Direction & Navigation API",
    description="An API offering full CRUD operations, real-time driver tracking, and geographic route-matching algorithms for ride sharing.",
    version="1.0.0"
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Register routers
app.include_router(routes_endpoints.router)
app.include_router(trips.router)
app.include_router(requests.router)
app.include_router(matching.router)

@app.get("/")
def read_root():
    return {
        "message": "Welcome to the Carpooling Real-time Direction & Navigation API!",
        "documentation": "/docs",
        "redoc": "/redoc",
        "status": "healthy"
    }
