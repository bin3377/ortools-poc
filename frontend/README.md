# Vehicle Scheduling System - Frontend

React frontend for the OR-Tools vehicle scheduling system.

## Features

- **Program Management**: Create and manage transportation programs
- **Vehicle Fleet**: Add/edit/delete vehicles with mobility assistance types
- **File Upload**: Upload JSON booking data for scheduling
- **Algorithm Selection**: Choose between Greedy and OR-Tools optimization
- **Results Display**: View optimized vehicle assignments and routes
- **Responsive Design**: Works on desktop and mobile devices

## Getting Started

### Prerequisites

- Node.js 16+ and npm
- Backend server running on http://localhost:8000

### Installation

1. **Install dependencies**:
   ```bash
   cd frontend
   npm install
   ```

2. **Start the development server**:
   ```bash
   npm start
   ```

3. **Open your browser**: http://localhost:3000

### Build for Production

```bash
npm run build
```

## Usage

### 1. Manage Programs & Vehicles

1. Go to "Programs & Vehicles" page
2. Click "New Program" to create a transportation program
3. Add vehicles to programs with different mobility assistance types:
   - **Ambulatory**: Walking passengers
   - **Wheelchair**: Wheelchair users
   - **Stretcher**: Stretcher patients

### 2. Schedule Trips

1. Go to "Scheduling" page
2. Upload a JSON file with booking data (format similar to `data/booking/simple.json`)
3. Choose scheduling algorithm:
   - **Greedy Algorithm**: Fast, priority-based scheduling
   - **OR-Tools Optimization**: Advanced constraint programming with options:
     - Chain bookings for same passenger
     - Minimize vehicles or total duration
4. Click "Run Scheduling" to process
5. View results showing vehicle assignments and trip details

### 3. JSON File Format

Upload files should match this structure:
```json
{
  "date": "February 20, 2026",
  "program_name": "Transportation Program",
  "before_pickup_time": 300,
  "after_pickup_time": 300,
  "pickup_loading_time": 3600,
  "dropoff_unloading_time": 900,
  "bookings": [
    {
      "booking_id": "...",
      "passenger_firstname": "John",
      "passenger_lastname": "Doe",
      "pickup_time": "05:22",
      "pickup_address": "123 Main St, City, State",
      "dropoff_address": "456 Oak Ave, City, State",
      "mobility_assistance": ["Ambulatory"],
      "additional_passenger": 0
    }
  ]
}
```

## API Integration

The frontend communicates with the backend via these endpoints:

- `GET /api/program/` - List all programs
- `POST /api/program/` - Create program
- `POST /api/program/{id}/vehicles` - Add vehicle
- `POST /api/schedule/` - Run scheduling
- `GET /api/health` - Health check

## Development

### Project Structure

```
src/
├── components/     # Reusable UI components
├── pages/          # Main application pages
├── services/       # API integration
├── App.js          # Main application component
└── index.js        # Application entry point
```

### Available Scripts

- `npm start` - Development server
- `npm run build` - Production build
- `npm test` - Run tests
- `npm run eject` - Eject from Create React App

### Technologies Used

- React 18
- React Router DOM
- Axios for API calls
- React Hot Toast for notifications
- Lucide React for icons

## Contributing

1. Follow the existing code style
2. Add proper error handling
3. Include user feedback via toast notifications
4. Test with the backend API