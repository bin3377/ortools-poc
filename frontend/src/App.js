import React from 'react';
import { Routes, Route } from 'react-router-dom';
import Navbar from './components/Navbar';
import Programs from './pages/Programs';
import Scheduling from './pages/Scheduling';
import Home from './pages/Home';

function App() {
  return (
    <div className="App">
      <Navbar />
      <div className="container">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/programs" element={<Programs />} />
          <Route path="/scheduling" element={<Scheduling />} />
        </Routes>
      </div>
    </div>
  );
}

export default App;