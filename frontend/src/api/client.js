import axios from 'axios'

const BACKEND_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: BACKEND_URL,
  headers: { 'Content-Type': 'application/json' },
})

export const getPatients = (params = {}) => api.get('/patients', { params })
export const getPatient = (id) => api.get(`/patients/${id}`)
export const getStats = () => api.get('/stats')
export const initiateCall = (patientId) => api.post('/outbound/call', { patient_id: patientId })
export const simulateCall = (data) => api.post('/simulate/call', data)

export default api