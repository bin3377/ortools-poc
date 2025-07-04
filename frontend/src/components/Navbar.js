import React from 'react';
import { Link, useLocation } from 'react-router-dom';

const Navbar = () => {
  const location = useLocation();
  
  const isActive = (path) => location.pathname === path;
  
  return (
    <nav className="nav">
      <div className="container">
        <div className="nav-content">
          <Link to="/" className="nav-brand">
            Vehicle Scheduling System
          </Link>
          <div className="nav-links">
            <Link 
              to="/" 
              className={`nav-link ${isActive('/') ? 'active' : ''}`}
            >
              Home
            </Link>
            <Link 
              to="/programs" 
              className={`nav-link ${isActive('/programs') ? 'active' : ''}`}
            >
              Programs & Vehicles
            </Link>
            <Link 
              to="/scheduling" 
              className={`nav-link ${isActive('/scheduling') ? 'active' : ''}`}
            >
              Scheduling
            </Link>
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;