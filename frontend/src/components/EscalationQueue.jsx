import RiskBadge from './RiskBadge'

export default function EscalationQueue({ messages }) {
  const escalations = messages.filter(m => m.escalate)

  if (escalations.length === 0) return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
      <h2 className="font-semibold text-gray-700 mb-2">🚨 Escalation Queue</h2>
      <p className="text-sm text-gray-400">No active escalations</p>
    </div>
  )

  return (
    <div className="bg-white rounded-xl shadow-sm border border-red-100 p-4">
      <h2 className="font-semibold text-gray-700 mb-3">🚨 Escalation Queue ({escalations.length})</h2>
      <div className="space-y-3">
        {escalations.map((m, i) => (
          <div key={i} className="border-l-4 border-red-400 pl-3 py-1">
            <div className="flex justify-between items-center">
              <span className="font-medium text-sm">{m.patient_name || `Patient #${m.patient_id}`}</span>
              <RiskBadge tier={m.risk_tier} />
            </div>
            <p className="text-xs text-gray-500 mt-1">{m.escalation_reason}</p>
            <p className="text-xs text-gray-400 italic mt-1">"{m.transcript?.slice(0, 80)}..."</p>
          </div>
        ))}
      </div>
    </div>
  )
}