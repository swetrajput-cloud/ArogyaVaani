import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import PatientDetail from './pages/PatientDetail'
import WorkflowBuilder from './pages/WorkflowBuilder'
import CallSimulator from './pages/CallSimulator'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/patient/:id" element={<PatientDetail />} />
        <Route path="/workflow" element={<WorkflowBuilder />} />
        <Route path="/simulator" element={<CallSimulator />} />
      </Routes>
    </BrowserRouter>
  )
}