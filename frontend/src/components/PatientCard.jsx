import { useNavigate } from 'react-router-dom'
import RiskBadge from './RiskBadge'
import { Phone, MapPin, Activity } from 'lucide-react'

export default function PatientCard({ patient, onCall }) {
  const navigate = useNavigate()

  return (
    <div
      className="bg-white rounded-xl shadow-sm border border-gray-100 p-4 hover:shadow-md transition cursor-pointer"
      onClick={() => navigate(`/patient/${patient.id}`)}
    >
      <div className="flex justify-between items-start mb-2">
        <div>
          <h3 className="font-semibold text-gray-800">{patient.name}</h3>
          <p className="text-xs text-gray-400 flex items-center gap-1 mt-0.5">
            <MapPin size={11} /> {patient.health_camp_name || 'Unknown Camp'}
          </p>
        </div>
        <RiskBadge tier={patient.current_risk_tier} />
      </div>

      <p className="text-xs text-gray-500 mb-3">{patient.condition}</p>

      <div className="grid grid-cols-3 gap-2 text-center text-xs mb-3">
        <div className="bg-gray-50 rounded-lg p-1.5">
          <p className="text-gray-400">BP</p>
          <p className="font-semibold text-gray-700">
            {patient.systolic_bp && patient.diastolic_bp
              ? `${patient.systolic_bp}/${patient.diastolic_bp}`
              : '—'}
          </p>
        </div>
        <div className="bg-gray-50 rounded-lg p-1.5">
          <p className="text-gray-400">BMI</p>
          <p className="font-semibold text-gray-700">{patient.bmi?.toFixed(1) || '—'}</p>
        </div>
        <div className="bg-gray-50 rounded-lg p-1.5">
          <p className="text-gray-400">Glucose</p>
          <p className="font-semibold text-gray-700">{patient.blood_glucose || '—'}</p>
        </div>
      </div>

      <div className="flex items-center justify-between">
        <span className="text-xs text-gray-400 flex items-center gap-1">
          <Activity size={11} /> Risk: {patient.overall_risk_score?.toFixed(1) || '—'}
        </span>
        <button
          onClick={(e) => { e.stopPropagation(); onCall(patient.id) }}
          className="flex items-center gap-1 text-xs bg-blue-600 text-white px-3 py-1 rounded-full hover:bg-blue-700 transition"
        >
          <Phone size={11} /> Call
        </button>
      </div>
    </div>
  )
}