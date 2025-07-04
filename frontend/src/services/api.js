import axios from 'axios';

const API_BASE_URL = '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Programs API
export const programsAPI = {
  getAll: () => api.get('/program/'),
  getById: (id) => api.get(`/program/${id}`),
  create: (program) => api.post('/program/', program),
  update: (id, program) => api.put(`/program/${id}`, program),
  delete: (id) => api.delete(`/program/${id}`),
  
  // Vehicle management
  addVehicle: (programId, vehicle) => api.post(`/program/${programId}/vehicles`, vehicle),
  updateVehicle: (programId, vehicleId, vehicle) => api.put(`/program/${programId}/vehicles/${vehicleId}`, vehicle),
  deleteVehicle: (programId, vehicleId) => api.delete(`/program/${programId}/vehicles/${vehicleId}`),
};

// Scheduling API
export const schedulingAPI = {
  schedule: (request) => api.post('/schedule/', request),
};

// Tasks API
export const tasksAPI = {
  create: (request) => api.post('/task/', request),
  getById: (id) => api.get(`/task/${id}`),
};

// Health check
export const healthAPI = {
  check: () => api.get('/health'),
};

export default api;