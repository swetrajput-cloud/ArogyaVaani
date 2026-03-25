import RiskBadge from './RiskBadge'
import { useNavigate } from 'react-router-dom'
import { AlertTriangle } from 'lucide-react'

export default function EscalationQueue({ messages }) {
  const navigate = useNavigate()
  const escalations = messages.filter((m) => m.escalate)

  return (
    <div className="bg-white rounded-xl shadow-sm border border-red-100 p-4">
      <h2 className="font-semibold text-red-600 flex items-center gap-2 mb-3">
        <AlertTriangle size={16} /> Escalation Queue
        {escalations.length > 0 && (
          <span className="ml-auto bg-red-500 text-white text-xs px-2 py-0.5 rounded-full">
            {escalations.length}
          </span>
        )}
      </h2>

      {escalations.length === 0 ? (
        <p className="text-xs text-gray-400 text-center py-4">No active escalations</p>
      ) : (
        <div className="space-y-2 max-h-64 overflow-y-auto">
          {escalations.map((m, i) => (
            <div
              key={i}
              className="border border-red-100 rounded-lg p-2 cursor-pointer hover:bg-red-50 transition"
              onClick={() => navigate(`/patient/${m.patient_id}`)}
            >
              <div className="flex justify-between items-center mb-1">
                <span className="text-xs font-semibold text-gray-700">Patient #{m.patient_id}</span>
                <RiskBadge tier={m.risk_tier} />
              </div>
              <p className="text-xs text-gray-500 truncate">{m.transcript}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}