import { MessageSquare } from 'lucide-react'
import RiskBadge from './RiskBadge'

export default function CallTranscript({ messages }) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
      <h2 className="font-semibold text-gray-700 flex items-center gap-2 mb-3">
        <MessageSquare size={16} /> Live Call Feed
      </h2>

      {messages.length === 0 ? (
        <p className="text-xs text-gray-400 text-center py-4">Waiting for live calls...</p>
      ) : (
        <div className="space-y-2 max-h-72 overflow-y-auto">
          {messages.map((m, i) => (
            <div key={i} className="border border-gray-100 rounded-lg p-2">
              <div className="flex justify-between items-center mb-1">
                <span className="text-xs font-semibold text-gray-600">Patient #{m.patient_id}</span>
                <RiskBadge tier={m.risk_tier} />
              </div>
              <p className="text-xs text-gray-700 italic">"{m.transcript}"</p>
              {m.nlp?.structured_answer?.symptoms?.length > 0 && (
                <p className="text-xs text-gray-400 mt-1">
                  Symptoms: {m.nlp.structured_answer.symptoms.join(', ')}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}