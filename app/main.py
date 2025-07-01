import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import direction, program, schedule, task
from app.services.database import close_mongo_connection, connect_to_mongo
from app.services.processor import start_processor

load_dotenv()

PORT = os.getenv("PORT", "8000")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await connect_to_mongo()
    # Start the background task processor
    start_processor()
    print(f"🚀 Server is starting on port {PORT}")

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
app.include_router(task.router)
app.include_router(schedule.router)


# Health check endpoint
@app.get("/api/health")
async def health_check():
    return {"message": "Server is running", "status": "OK"}


# Root endpoint
@app.get("/")
async def root():
    return {"message": "Welcome to Scheduler API", "docs": "/docs"}
