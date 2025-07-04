import React, { useState, useEffect } from 'react';
import { programsAPI } from '../services/api';
import { toast } from 'react-hot-toast';
import { Plus, Edit2, Trash2, Truck } from 'lucide-react';

const Programs = () => {
  const [programs, setPrograms] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showProgramForm, setShowProgramForm] = useState(false);
  const [showVehicleForm, setShowVehicleForm] = useState(false);
  const [selectedProgram, setSelectedProgram] = useState(null);
  const [editingProgram, setEditingProgram] = useState(null);
  const [editingVehicle, setEditingVehicle] = useState(null);

  const [programForm, setProgramForm] = useState({
    name: '',
    vehicles: []
  });

  const [vehicleForm, setVehicleForm] = useState({
    name: '',
    assistance: 'AMBI'
  });

  useEffect(() => {
    fetchPrograms();
  }, []);

  const fetchPrograms = async () => {
    try {
      const response = await programsAPI.getAll();
      setPrograms(response.data);
    } catch (error) {
      console.error('Error fetching programs:', error);
      toast.error('Failed to load programs');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateProgram = async (e) => {
    e.preventDefault();
    try {
      await programsAPI.create(programForm);
      toast.success('Program created successfully');
      setShowProgramForm(false);
      setProgramForm({ name: '', vehicles: [] });
      fetchPrograms();
    } catch (error) {
      console.error('Error creating program:', error);
      toast.error('Failed to create program');
    }
  };

  const handleUpdateProgram = async (e) => {
    e.preventDefault();
    try {
      await programsAPI.update(editingProgram.id, programForm);
      toast.success('Program updated successfully');
      setEditingProgram(null);
      setShowProgramForm(false);
      setProgramForm({ name: '', vehicles: [] });
      fetchPrograms();
    } catch (error) {
      console.error('Error updating program:', error);
      toast.error('Failed to update program');
    }
  };

  const handleDeleteProgram = async (programId) => {
    if (window.confirm('Are you sure you want to delete this program?')) {
      try {
        await programsAPI.delete(programId);
        toast.success('Program deleted successfully');
        fetchPrograms();
      } catch (error) {
        console.error('Error deleting program:', error);
        toast.error('Failed to delete program');
      }
    }
  };

  const handleAddVehicle = async (e) => {
    e.preventDefault();
    try {
      await programsAPI.addVehicle(selectedProgram.id, vehicleForm);
      toast.success('Vehicle added successfully');
      setShowVehicleForm(false);
      setVehicleForm({ name: '', assistance: 'AMBI' });
      fetchPrograms();
    } catch (error) {
      console.error('Error adding vehicle:', error);
      toast.error('Failed to add vehicle');
    }
  };

  const handleUpdateVehicle = async (e) => {
    e.preventDefault();
    try {
      await programsAPI.updateVehicle(selectedProgram.id, editingVehicle.id, vehicleForm);
      toast.success('Vehicle updated successfully');
      setEditingVehicle(null);
      setShowVehicleForm(false);
      setVehicleForm({ name: '', assistance: 'AMBI' });
      fetchPrograms();
    } catch (error) {
      console.error('Error updating vehicle:', error);
      toast.error('Failed to update vehicle');
    }
  };

  const handleDeleteVehicle = async (vehicleId) => {
    if (window.confirm('Are you sure you want to delete this vehicle?')) {
      try {
        await programsAPI.deleteVehicle(selectedProgram.id, vehicleId);
        toast.success('Vehicle deleted successfully');
        fetchPrograms();
      } catch (error) {
        console.error('Error deleting vehicle:', error);
        toast.error('Failed to delete vehicle');
      }
    }
  };

  const openProgramForm = (program = null) => {
    if (program) {
      setEditingProgram(program);
      setProgramForm({ name: program.name, vehicles: program.vehicles });
    } else {
      setEditingProgram(null);
      setProgramForm({ name: '', vehicles: [] });
    }
    setShowProgramForm(true);
  };

  const openVehicleForm = (vehicle = null) => {
    if (vehicle) {
      setEditingVehicle(vehicle);
      setVehicleForm({ name: vehicle.name, assistance: vehicle.assistance });
    } else {
      setEditingVehicle(null);
      setVehicleForm({ name: '', assistance: 'AMBI' });
    }
    setShowVehicleForm(true);
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

  if (loading) {
    return <div className="loading">Loading programs...</div>;
  }

  return (
    <div>
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
          <h1 style={{ fontSize: '1.8rem', fontWeight: 'bold' }}>Programs & Vehicles</h1>
          <button 
            className="btn btn-primary" 
            onClick={() => openProgramForm()}
            style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
          >
            <Plus size={16} />
            New Program
          </button>
        </div>

        {programs.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '40px', color: '#6b7280' }}>
            <Truck size={48} style={{ margin: '0 auto 16px' }} />
            <p>No programs found. Create your first program to get started.</p>
          </div>
        ) : (
          <div className="grid">
            {programs.map((program) => (
              <div key={program.id} className="card" style={{ border: '1px solid #e5e7eb' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                  <h3 style={{ fontSize: '1.2rem', fontWeight: '600' }}>{program.name}</h3>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <button 
                      className="btn btn-secondary" 
                      onClick={() => openProgramForm(program)}
                      style={{ padding: '4px 8px' }}
                    >
                      <Edit2 size={14} />
                    </button>
                    <button 
                      className="btn btn-danger" 
                      onClick={() => handleDeleteProgram(program.id)}
                      style={{ padding: '4px 8px' }}
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                  <p style={{ color: '#6b7280' }}>
                    {program.vehicles.length} vehicle{program.vehicles.length !== 1 ? 's' : ''}
                  </p>
                  <button 
                    className="btn btn-success" 
                    onClick={() => {
                      setSelectedProgram(program);
                      openVehicleForm();
                    }}
                    style={{ fontSize: '12px', padding: '4px 8px' }}
                  >
                    <Plus size={12} style={{ marginRight: '4px' }} />
                    Add Vehicle
                  </button>
                </div>

                {program.vehicles.length > 0 && (
                  <table className="table">
                    <thead>
                      <tr>
                        <th>Vehicle Name</th>
                        <th>Mobility Assistance</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {program.vehicles.map((vehicle) => (
                        <tr key={vehicle.id}>
                          <td>{vehicle.name}</td>
                          <td>
                            <span className={`badge ${getMobilityBadge(vehicle.assistance)}`}>
                              {getMobilityLabel(vehicle.assistance)}
                            </span>
                          </td>
                          <td>
                            <div style={{ display: 'flex', gap: '4px' }}>
                              <button 
                                className="btn btn-secondary" 
                                onClick={() => {
                                  setSelectedProgram(program);
                                  openVehicleForm(vehicle);
                                }}
                                style={{ padding: '2px 6px', fontSize: '12px' }}
                              >
                                <Edit2 size={12} />
                              </button>
                              <button 
                                className="btn btn-danger" 
                                onClick={() => {
                                  setSelectedProgram(program);
                                  handleDeleteVehicle(vehicle.id);
                                }}
                                style={{ padding: '2px 6px', fontSize: '12px' }}
                              >
                                <Trash2 size={12} />
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Program Form Modal */}
      {showProgramForm && (
        <div style={{ 
          position: 'fixed', 
          top: 0, 
          left: 0, 
          right: 0, 
          bottom: 0, 
          backgroundColor: 'rgba(0,0,0,0.5)', 
          display: 'flex', 
          justifyContent: 'center', 
          alignItems: 'center', 
          zIndex: 1000 
        }}>
          <div className="card" style={{ width: '400px', margin: '0' }}>
            <h2 style={{ marginBottom: '16px' }}>
              {editingProgram ? 'Edit Program' : 'Create New Program'}
            </h2>
            <form onSubmit={editingProgram ? handleUpdateProgram : handleCreateProgram}>
              <div className="form-group">
                <label className="form-label">Program Name</label>
                <input
                  type="text"
                  className="form-input"
                  value={programForm.name}
                  onChange={(e) => setProgramForm({ ...programForm, name: e.target.value })}
                  required
                />
              </div>
              <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
                <button 
                  type="button" 
                  className="btn btn-secondary"
                  onClick={() => setShowProgramForm(false)}
                >
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  {editingProgram ? 'Update' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Vehicle Form Modal */}
      {showVehicleForm && (
        <div style={{ 
          position: 'fixed', 
          top: 0, 
          left: 0, 
          right: 0, 
          bottom: 0, 
          backgroundColor: 'rgba(0,0,0,0.5)', 
          display: 'flex', 
          justifyContent: 'center', 
          alignItems: 'center', 
          zIndex: 1000 
        }}>
          <div className="card" style={{ width: '400px', margin: '0' }}>
            <h2 style={{ marginBottom: '16px' }}>
              {editingVehicle ? 'Edit Vehicle' : 'Add New Vehicle'}
            </h2>
            <form onSubmit={editingVehicle ? handleUpdateVehicle : handleAddVehicle}>
              <div className="form-group">
                <label className="form-label">Vehicle Name</label>
                <input
                  type="text"
                  className="form-input"
                  value={vehicleForm.name}
                  onChange={(e) => setVehicleForm({ ...vehicleForm, name: e.target.value })}
                  required
                />
              </div>
              <div className="form-group">
                <label className="form-label">Mobility Assistance</label>
                <select
                  className="form-select"
                  value={vehicleForm.assistance}
                  onChange={(e) => setVehicleForm({ ...vehicleForm, assistance: e.target.value })}
                >
                  <option value="AMBI">Ambulatory</option>
                  <option value="WC">Wheelchair</option>
                  <option value="GUR">Stretcher</option>
                </select>
              </div>
              <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
                <button 
                  type="button" 
                  className="btn btn-secondary"
                  onClick={() => setShowVehicleForm(false)}
                >
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  {editingVehicle ? 'Update' : 'Add'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default Programs;