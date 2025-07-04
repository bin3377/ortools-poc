import React, { useState, useEffect } from 'react';
import { healthAPI } from '../services/api';
import { Activity, Users, Calendar, Truck } from 'lucide-react';

const Home = () => {
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const response = await healthAPI.check();
        setHealth(response.data);
      } catch (error) {
        console.error('Health check failed:', error);
        setHealth({ status: 'ERROR', message: 'Service unavailable' });
      } finally {
        setLoading(false);
      }
    };

    checkHealth();
  }, []);

  const features = [
    {
      icon: <Users className="w-8 h-8 text-blue-500" />,
      title: 'Program Management',
      description: 'Create and manage transportation programs with multiple vehicles.'
    },
    {
      icon: <Truck className="w-8 h-8 text-green-500" />,
      title: 'Vehicle Fleet',
      description: 'Track vehicles with different mobility assistance capabilities.'
    },
    {
      icon: <Calendar className="w-8 h-8 text-purple-500" />,
      title: 'Smart Scheduling',
      description: 'Optimize routes using greedy algorithms or OR-Tools constraint programming.'
    },
    {
      icon: <Activity className="w-8 h-8 text-orange-500" />,
      title: 'Real-time Status',
      description: 'Monitor scheduling tasks and view optimization results.'
    }
  ];

  return (
    <div>
      <div className="card">
        <h1 style={{ fontSize: '2rem', fontWeight: 'bold', marginBottom: '16px' }}>
          Vehicle Scheduling System
        </h1>
        <p style={{ fontSize: '1.1rem', color: '#6b7280', marginBottom: '24px' }}>
          Optimize medical transportation scheduling with advanced algorithms and real-time management.
        </p>
        
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div 
            style={{ 
              width: '8px', 
              height: '8px', 
              borderRadius: '50%', 
              backgroundColor: health?.status === 'OK' ? '#10b981' : '#ef4444' 
            }}
          />
          <span style={{ fontSize: '14px', color: '#6b7280' }}>
            {loading ? 'Checking service status...' : `Service: ${health?.status || 'Unknown'}`}
          </span>
        </div>
      </div>

      <div className="grid grid-2">
        {features.map((feature, index) => (
          <div key={index} className="card">
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
              {feature.icon}
              <h3 style={{ fontSize: '1.2rem', fontWeight: '600' }}>{feature.title}</h3>
            </div>
            <p style={{ color: '#6b7280', lineHeight: '1.5' }}>{feature.description}</p>
          </div>
        ))}
      </div>

      <div className="card">
        <h2 style={{ fontSize: '1.5rem', fontWeight: '600', marginBottom: '16px' }}>
          Getting Started
        </h2>
        <ol style={{ paddingLeft: '20px', lineHeight: '1.6', color: '#374151' }}>
          <li style={{ marginBottom: '8px' }}>
            <strong>Manage Programs:</strong> Create transportation programs and add vehicles with different mobility assistance types.
          </li>
          <li style={{ marginBottom: '8px' }}>
            <strong>Upload Booking Data:</strong> Upload JSON files containing passenger booking information.
          </li>
          <li style={{ marginBottom: '8px' }}>
            <strong>Choose Algorithm:</strong> Select between greedy scheduling or OR-Tools optimization.
          </li>
          <li>
            <strong>View Results:</strong> Review the optimized vehicle assignments and routes.
          </li>
        </ol>
      </div>
    </div>
  );
};

export default Home;