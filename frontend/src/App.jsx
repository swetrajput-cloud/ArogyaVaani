import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import PatientDetail from './pages/PatientDetail'
import WorkflowBuilder from './pages/WorkflowBuilder'
import CallSimulator from './pages/CallSimulator'
import CallHistory from './pages/CallHistory'
import VaccinationPage from './pages/VaccinationPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/"              element={<Dashboard />} />
        <Route path="/patient/:id"   element={<PatientDetail />} />
        <Route path="/workflow"      element={<WorkflowBuilder />} />
        <Route path="/simulator"     element={<CallSimulator />} />
        <Route path="/calls"         element={<CallHistory />} />
        <Route path="/vaccination"   element={<VaccinationPage />} />
      </Routes>
    </BrowserRouter>
  )
}