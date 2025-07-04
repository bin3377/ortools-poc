# OR-Tools POC - Vehicle Scheduling System

A proof-of-concept vehicle scheduling system for medical transportation services, built with FastAPI and Google OR-Tools.

## Overview

This project optimizes vehicle scheduling for medical transportation, handling bookings with different mobility assistance requirements (ambulatory, wheelchair, stretcher) and optimizing routes using constraint programming.

## Features

- **Dual Scheduling Algorithms**
  - Greedy scheduler for fast allocation
  - OR-Tools constraint programming for optimal solutions
- **Mobility Assistance Support**
  - AMBI (Ambulatory): Walking passengers
  - WC (Wheelchair): Wheelchair passengers
  - GUR (Gurney/Stretcher): Stretcher patients
- **Route Optimization** with Google Maps API integration
- **Async Task Processing** for background scheduling
- **RESTful API** with FastAPI
- **MongoDB** for data persistence

## Tech Stack

- **Backend**: FastAPI + Uvicorn
- **Database**: MongoDB (async)
- **Optimization**: Google OR-Tools (CP-SAT solver)
- **External APIs**: Google Maps API
- **Language**: Python 3.12+

## Project Structure

```
app/
├── models/          # Data models (Booking, Vehicle, Program, Task)
├── routers/         # API endpoints
├── services/        # Business logic
│   └── scheduler/   # Scheduling algorithms
├── internal/        # Utilities and helpers
└── main.py         # FastAPI application
```

## Data Models

- **Booking**: Passenger reservation with pickup/dropoff details
- **Vehicle**: Transportation vehicle with mobility assistance capability
- **Program**: Service program containing multiple vehicles
- **Task**: Scheduling task with async processing status

## Scheduling Algorithms

### Greedy Scheduler
- Priority-based allocation by mobility assistance type
- Fast execution for real-time scheduling
- Considers passenger chaining for multi-leg trips

### OR-Tools Scheduler
- Constraint programming optimization
- Minimizes vehicle usage or total duration
- Handles complex constraints:
  - Mobility assistance compatibility
  - Time windows
  - Trip connections
  - Passenger chaining

## API Endpoints

- `GET /api/health` - Health check
- `POST /api/schedule` - Create scheduling task
- `GET /api/tasks/{id}` - Get task status
- Program and vehicle management endpoints

## Getting Started

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set environment variables**:
   ```bash
   export MONGODB_URL="mongodb://localhost:27017"
   export GOOGLE_MAPS_API_KEY="your_api_key"
   ```

3. **Run the server**:
   ```bash
   python run.py
   ```

4. **Access API docs**: http://localhost:8000/docs

## Development

The project uses:
- **uv** for dependency management
- **MongoDB** for data storage
- **Google Maps API** for route calculations
- **OR-Tools** for optimization

## License

This is a proof-of-concept project for vehicle scheduling optimization.