from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.services.database import connect_to_mongo, close_mongo_connection
from app.routers import direction, program


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await connect_to_mongo()
    yield
    # Shutdown
    await close_mongo_connection()


# Create FastAPI app
app = FastAPI(
    title="Scheduler API",
    description="A FastAPI backend for the Scheduler application with Program and Vehicle management",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(program.router)
app.include_router(direction.router)


# Health check endpoint
@app.get("/api/health")
async def health_check():
    return {"message": "Server is running", "status": "OK"}


# Root endpoint
@app.get("/")
async def root():
    return {"message": "Welcome to Scheduler API", "docs": "/docs"}
