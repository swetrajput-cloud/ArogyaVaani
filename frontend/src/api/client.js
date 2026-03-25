import axios from 'axios'

const api = axios.create({
  baseURL: 'http://localhost:8000',
  headers: { 'Content-Type': 'application/json' },
})

export const getPatients = (params = {}) => api.get('/patients', { params })
export const getPatient = (id) => api.get(`/patients/${id}`)
export const getStats = () => api.get('/stats')
export const initiateCall = (patientId) => api.post(`/webhook/initiate/${patientId}`)

export default api