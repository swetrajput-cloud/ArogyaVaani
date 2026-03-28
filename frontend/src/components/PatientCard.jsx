import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import RiskBadge from './RiskBadge'

const API = import.meta.env.VITE_API_URL || "https://arogyavaani-production.up.railway.app"

export default function PatientCard({ patient }) {
  const navigate = useNavigate()
  const [calling, setCalling] = useState(false)
  const [callStatus, setCallStatus] = useState("") // "", "success", "error"

  const handleCall = async (e) => {
    e.stopPropagation() // prevent card navigation
    setCalling(true)
    setCallStatus("")
    try {
      const res = await fetch(`${API}/outbound/call`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ patient_id: patient.id }),
      })
      if (res.ok) {
        setCallStatus("success")
      } else {
        setCallStatus("error")
      }
    } catch {
      setCallStatus("error")
    } finally {
      setCalling(false)
      setTimeout(() => setCallStatus(""), 3000)
    }
  }

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

      {/* Call Button */}
      <div className="mt-3 pt-2 border-t border-gray-100">
        <button
          onClick={handleCall}
          disabled={calling}
          className={`w-full py-1.5 rounded-lg text-xs font-semibold transition flex items-center justify-center gap-1.5
            ${calling
              ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
              : callStatus === 'success'
              ? 'bg-green-50 text-green-600 border border-green-200'
              : callStatus === 'error'
              ? 'bg-red-50 text-red-500 border border-red-200'
              : 'bg-blue-600 text-white hover:bg-blue-700'
            }`}
        >
          {calling
            ? <>⏳ Calling...</>
            : callStatus === 'success'
            ? <>✅ Call Initiated</>
            : callStatus === 'error'
            ? <>❌ Call Failed</>
            : <>📞 Call Patient</>
          }
        </button>
      </div>
    </div>
  )
}