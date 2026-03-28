import { useNavigate } from 'react-router-dom'
import RiskBadge from './RiskBadge'

export default function PatientCard({ patient }) {
  const navigate = useNavigate()
  return (
    <div
      onClick={() => navigate(`/patient/${patient.id}`)}
      className="bg-white rounded-xl shadow-sm border border-gray-100 p-4 cursor-pointer hover:shadow-md transition-shadow"
    >
      <div className="flex justify-between items-start mb-2">
        <div>
          <h3 className="font-semibold text-gray-800">{patient.name}</h3>
          <p className="text-xs text-gray-400">{patient.health_camp_name}</p>
        </div>
        <RiskBadge tier={patient.current_risk_tier} />
      </div>
      <p className="text-sm text-gray-600 mb-2">{patient.condition}</p>
      <div className="grid grid-cols-3 gap-2 text-xs text-gray-500">
        <div>
          <span className="font-medium">BP</span>
          <p>{patient.systolic_bp}/{patient.diastolic_bp}</p>
        </div>
        <div>
          <span className="font-medium">Glucose</span>
          <p>{patient.blood_glucose ?? '—'}</p>
        </div>
        <div>
          <span className="font-medium">BMI</span>
          <p>{patient.bmi ?? '—'}</p>
        </div>
      </div>
      <div className="mt-2 pt-2 border-t border-gray-50 flex justify-between text-xs text-gray-400">
        <span>Risk Score: {patient.overall_risk_score?.toFixed(1) ?? '—'}</span>
        <span className="capitalize">{patient.module_type?.replace('_', ' ')}</span>
      </div>
    </div>
  )
}