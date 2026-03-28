import RiskBadge from './RiskBadge'

export default function CallTranscript({ messages }) {
  if (messages.length === 0) return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
      <h2 className="font-semibold text-gray-700 mb-2">📞 Live Call Feed</h2>
      <p className="text-sm text-gray-400">Waiting for calls...</p>
    </div>
  )

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
      <h2 className="font-semibold text-gray-700 mb-3">📞 Live Call Feed</h2>
      <div className="space-y-3 max-h-64 overflow-y-auto">
        {messages.map((m, i) => (
          <div key={i} className="border border-gray-100 rounded-lg p-3">
            <div className="flex justify-between items-center mb-1">
              <span className="text-xs font-medium text-gray-600">
                {m.patient_name || `Patient #${m.patient_id}`}
              </span>
              <RiskBadge tier={m.risk_tier} />
            </div>
            <p className="text-sm text-gray-700">"{m.transcript}"</p>
            {m.nlp?.structured_answer?.patient_concern && (
              <p className="text-xs text-gray-400 mt-1">
                💬 {m.nlp.structured_answer.patient_concern}
              </p>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}