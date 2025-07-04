import React, { useState } from 'react';
import { schedulingAPI } from '../services/api';
import { toast } from 'react-hot-toast';
import { Upload, Settings, Play, Clock, CheckCircle, XCircle, FileText, Download } from 'lucide-react';

const Scheduling = () => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [bookingData, setBookingData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [useOptimization, setUseOptimization] = useState(false);
  const [optimizationSettings, setOptimizationSettings] = useState({
    chain_bookings_for_same_passenger: true,
    minimize_vehicles: true,
    minimize_total_duration: false
  });

  const handleFileUpload = (event) => {
    const file = event.target.files[0];
    if (file) {
      setSelectedFile(file);
      const reader = new FileReader();
      reader.onload = (e) => {
        try {
          const data = JSON.parse(e.target.result);
          setBookingData(data);
          toast.success('Booking data loaded successfully');
        } catch (error) {
          console.error('Error parsing JSON:', error);
          toast.error('Invalid JSON file');
          setSelectedFile(null);
          setBookingData(null);
        }
      };
      reader.readAsText(file);
    }
  };

  const handleSchedule = async () => {
    if (!bookingData) {
      toast.error('Please upload booking data first');
      return;
    }

    setLoading(true);
    setResult(null);

    try {
      const scheduleRequest = {
        ...bookingData,
        optimization: useOptimization ? optimizationSettings : null
      };

      const response = await schedulingAPI.schedule(scheduleRequest);
      setResult(response.data);
      toast.success('Scheduling completed successfully');
    } catch (error) {
      console.error('Error scheduling:', error);
      toast.error('Scheduling failed: ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  const downloadResult = () => {
    if (result) {
      const dataStr = JSON.stringify(result, null, 2);
      const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
      const exportFileDefaultName = 'scheduling_result.json';
      const linkElement = document.createElement('a');
      linkElement.setAttribute('href', dataUri);
      linkElement.setAttribute('download', exportFileDefaultName);
      linkElement.click();
    }
  };

  const getMobilityBadge = (assistance) => {
    const badges = {
      AMBI: 'badge-ambi',
      WC: 'badge-wc',
      GUR: 'badge-gur'
    };
    return badges[assistance] || 'badge-ambi';
  };

  const getMobilityLabel = (assistance) => {
    const labels = {
      AMBI: 'Ambulatory',
      WC: 'Wheelchair',
      GUR: 'Stretcher'
    };
    return labels[assistance] || 'Unknown';
  };

  const renderBookingPreview = () => {
    if (!bookingData) return null;

    return (
      <div className="card">
        <h3 style={{ fontSize: '1.2rem', fontWeight: '600', marginBottom: '16px' }}>
          Booking Data Preview
        </h3>
        <div className="grid grid-2">
          <div>
            <p><strong>Date:</strong> {bookingData.date}</p>
            <p><strong>Total Bookings:</strong> {bookingData.bookings?.length || 0}</p>
            <p><strong>Program:</strong> {bookingData.program_name || 'Not specified'}</p>
          </div>
          <div>
            <p><strong>Before Pickup:</strong> {bookingData.before_pickup_time || 300}s</p>
            <p><strong>After Pickup:</strong> {bookingData.after_pickup_time || 300}s</p>
            <p><strong>Loading Time:</strong> {bookingData.pickup_loading_time || 3600}s</p>
            <p><strong>Unloading Time:</strong> {bookingData.dropoff_unloading_time || 900}s</p>
          </div>
        </div>
        
        {bookingData.bookings && bookingData.bookings.length > 0 && (
          <div style={{ marginTop: '16px' }}>
            <h4 style={{ marginBottom: '8px' }}>Sample Bookings:</h4>
            <table className="table">
              <thead>
                <tr>
                  <th>Passenger</th>
                  <th>Pickup Time</th>
                  <th>Pickup Address</th>
                  <th>Dropoff Address</th>
                  <th>Assistance</th>
                </tr>
              </thead>
              <tbody>
                {bookingData.bookings.slice(0, 3).map((booking, index) => (
                  <tr key={index}>
                    <td>{booking.passenger_firstname} {booking.passenger_lastname}</td>
                    <td>{booking.pickup_time}</td>
                    <td style={{ maxWidth: '200px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {booking.pickup_address}
                    </td>
                    <td style={{ maxWidth: '200px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {booking.dropoff_address}
                    </td>
                    <td>
                      {booking.mobility_assistance?.map((assistance, idx) => (
                        <span key={idx} className={`badge ${getMobilityBadge(assistance.toUpperCase())}`}>
                          {getMobilityLabel(assistance.toUpperCase())}
                        </span>
                      ))}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {bookingData.bookings.length > 3 && (
              <p style={{ fontSize: '14px', color: '#6b7280', marginTop: '8px' }}>
                ... and {bookingData.bookings.length - 3} more bookings
              </p>
            )}
          </div>
        )}
      </div>
    );
  };

  const renderResult = () => {
    if (!result) return null;

    const { result: scheduleResult } = result;
    const { status, message, data } = scheduleResult;

    return (
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <h3 style={{ fontSize: '1.2rem', fontWeight: '600' }}>Scheduling Result</h3>
          <button className="btn btn-secondary" onClick={downloadResult}>
            <Download size={16} style={{ marginRight: '8px' }} />
            Download Result
          </button>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
          {status === 'success' ? (
            <CheckCircle size={20} className="text-green-500" />
          ) : (
            <XCircle size={20} className="text-red-500" />
          )}
          <span style={{ fontWeight: '500' }}>Status: {status}</span>
        </div>

        <p style={{ marginBottom: '16px', color: '#6b7280' }}>{message}</p>

        {data && data.vehicle_trip_list && (
          <div>
            <h4 style={{ marginBottom: '12px' }}>Vehicle Assignments</h4>
            <p style={{ marginBottom: '16px', color: '#6b7280' }}>
              {data.vehicle_trip_list.length} vehicle{data.vehicle_trip_list.length !== 1 ? 's' : ''} assigned
            </p>
            
            <div className="grid">
              {data.vehicle_trip_list.map((shuttle, index) => (
                <div key={index} className="card" style={{ border: '1px solid #e5e7eb', margin: '0 0 16px 0' }}>
                  <h5 style={{ fontSize: '1.1rem', fontWeight: '600', marginBottom: '12px' }}>
                    Vehicle: {shuttle.shuttle_name}
                  </h5>
                  <p style={{ marginBottom: '8px', color: '#6b7280' }}>
                    {shuttle.trips?.length || 0} trip{shuttle.trips?.length !== 1 ? 's' : ''}
                  </p>
                  
                  {shuttle.trips && shuttle.trips.length > 0 && (
                    <table className="table">
                      <thead>
                        <tr>
                          <th>Trip ID</th>
                          <th>Pickup Time</th>
                          <th>Dropoff Time</th>
                          <th>Passengers</th>
                        </tr>
                      </thead>
                      <tbody>
                        {shuttle.trips.map((trip, tripIndex) => (
                          <tr key={tripIndex}>
                            <td>{trip.trip_id || `Trip ${tripIndex + 1}`}</td>
                            <td>{trip.first_pickup_time}</td>
                            <td>{trip.last_dropoff_time}</td>
                            <td>{trip.number_of_passengers}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div>
      <div className="card">
        <h1 style={{ fontSize: '1.8rem', fontWeight: 'bold', marginBottom: '16px' }}>
          Vehicle Scheduling
        </h1>
        <p style={{ color: '#6b7280', marginBottom: '24px' }}>
          Upload booking data and choose scheduling algorithm to optimize vehicle assignments.
        </p>
      </div>

      {/* File Upload */}
      <div className="card">
        <h2 style={{ fontSize: '1.4rem', fontWeight: '600', marginBottom: '16px' }}>
          <FileText size={20} style={{ display: 'inline', marginRight: '8px' }} />
          Upload Booking Data
        </h2>
        
        <div className="file-upload">
          <input
            type="file"
            accept=".json"
            onChange={handleFileUpload}
            style={{ marginBottom: '8px' }}
          />
          <p style={{ fontSize: '14px', color: '#6b7280' }}>
            Upload a JSON file containing booking data (similar to files in data/booking/)
          </p>
          {selectedFile && (
            <p style={{ fontSize: '14px', color: '#059669', marginTop: '8px' }}>
              ✓ File loaded: {selectedFile.name}
            </p>
          )}
        </div>
      </div>

      {/* Optimization Settings */}
      <div className="card">
        <h2 style={{ fontSize: '1.4rem', fontWeight: '600', marginBottom: '16px' }}>
          <Settings size={20} style={{ display: 'inline', marginRight: '8px' }} />
          Scheduling Algorithm
        </h2>
        
        <div style={{ marginBottom: '16px' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <input
              type="checkbox"
              checked={useOptimization}
              onChange={(e) => setUseOptimization(e.target.checked)}
            />
            <span>Use OR-Tools Optimization (otherwise use Greedy Algorithm)</span>
          </label>
        </div>

        {useOptimization && (
          <div style={{ border: '1px solid #e5e7eb', borderRadius: '8px', padding: '16px' }}>
            <h3 style={{ fontSize: '1.1rem', fontWeight: '600', marginBottom: '12px' }}>
              Optimization Settings
            </h3>
            
            <div style={{ marginBottom: '12px' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                <input
                  type="checkbox"
                  checked={optimizationSettings.chain_bookings_for_same_passenger}
                  onChange={(e) => setOptimizationSettings({
                    ...optimizationSettings,
                    chain_bookings_for_same_passenger: e.target.checked
                  })}
                />
                <span>Chain bookings for same passenger</span>
              </label>
              <p style={{ fontSize: '12px', color: '#6b7280', marginLeft: '24px' }}>
                Keep all trips for the same passenger on the same vehicle
              </p>
            </div>

            <div style={{ marginBottom: '12px' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                <input
                  type="radio"
                  name="objective"
                  checked={optimizationSettings.minimize_vehicles}
                  onChange={() => setOptimizationSettings({
                    ...optimizationSettings,
                    minimize_vehicles: true,
                    minimize_total_duration: false
                  })}
                />
                <span>Minimize number of vehicles</span>
              </label>
              <p style={{ fontSize: '12px', color: '#6b7280', marginLeft: '24px' }}>
                Use the fewest vehicles possible
              </p>
            </div>

            <div>
              <label style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                <input
                  type="radio"
                  name="objective"
                  checked={optimizationSettings.minimize_total_duration}
                  onChange={() => setOptimizationSettings({
                    ...optimizationSettings,
                    minimize_vehicles: false,
                    minimize_total_duration: true
                  })}
                />
                <span>Minimize total duration</span>
              </label>
              <p style={{ fontSize: '12px', color: '#6b7280', marginLeft: '24px' }}>
                Minimize the total time spent by all vehicles
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Schedule Button */}
      <div className="card">
        <button
          className="btn btn-primary"
          onClick={handleSchedule}
          disabled={!bookingData || loading}
          style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '16px', padding: '12px 24px' }}
        >
          {loading ? (
            <>
              <Clock size={20} />
              Processing...
            </>
          ) : (
            <>
              <Play size={20} />
              Run Scheduling
            </>
          )}
        </button>
        
        {!bookingData && (
          <p style={{ fontSize: '14px', color: '#6b7280', marginTop: '8px' }}>
            Please upload booking data first
          </p>
        )}
      </div>

      {/* Preview */}
      {renderBookingPreview()}

      {/* Results */}
      {renderResult()}
    </div>
  );
};

export default Scheduling;