import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { simulateCall } from '../api/client'
import RiskBadge from '../components/RiskBadge'

const SAMPLE_TRANSCRIPTS = [
  { label: 'Hindi - Fever & Weakness', text: 'मुझे बुखार है और बहुत कमजोरी लग रही है, दवाई नहीं ली', lang: 'hindi' },
  { label: 'Hindi - Chest Pain (RED)', text: 'सीने में बहुत तेज दर्द हो रहा है, सांस नहीं ले पा रहा', lang: 'hindi' },
  { label: 'Hindi - All Good', text: 'मैं बिल्कुल ठीक हूं, दवाई समय पर ले रहा हूं, खाना भी अच्छा खा रहा हूं', lang: 'hindi' },
  { label: 'English - Dizziness', text: 'I have been feeling dizzy and have not been eating properly', lang: 'english' },
]

export default function CallSimulator() {
  const navigate = useNavigate()
  const [patientId, setPatientId] = useState('1')
  const [transcript, setTranscript] = useState('')
  const [language, setLanguage] = useState('hindi')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSimulate = async () => {
    if (!transcript.trim()) { setError('Please enter a transcript'); return }
    setLoading(true)
    setError('')
    setResult(null)
    try {
      const res = await simulateCall({ patient_id: parseInt(patientId), transcript, language })
      setResult(res.data)
    } catch (e) {
      setError(e.response?.data?.detail || 'Simulation failed. Check backend.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white shadow-sm border-b px-6 py-4">
        <div className="max-w-3xl mx-auto flex items-center gap-4">
          <button onClick={() => navigate('/')} className="text-blue-600 hover:underline text-sm">← Back</button>
          <h1 className="text-xl font-bold text-gray-800">🎙️ Call Simulator</h1>
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-6 py-6 space-y-4">
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
          <h2 className="font-semibold text-gray-700 mb-4">Simulate AI Call Pipeline</h2>

          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <label className="text-sm text-gray-600 mb-1 block">Patient ID</label>
              <input type="number" value={patientId} onChange={e => setPatientId(e.target.value)}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-400" />
            </div>
            <div>
              <label className="text-sm text-gray-600 mb-1 block">Language</label>
              <select value={language} onChange={e => setLanguage(e.target.value)}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-400">
                {['hindi', 'marathi', 'bengali', 'tamil', 'telugu', 'gujarati', 'english'].map(l => (
                  <option key={l} value={l}>{l.charAt(0).toUpperCase() + l.slice(1)}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="mb-3">
            <label className="text-sm text-gray-600 mb-1 block">Sample Transcripts</label>
            <div className="flex flex-wrap gap-2">
              {SAMPLE_TRANSCRIPTS.map((s, i) => (
                <button key={i} onClick={() => { setTranscript(s.text); setLanguage(s.lang) }}
                  className="text-xs bg-blue-50 text-blue-600 border border-blue-200 px-2 py-1 rounded-full hover:bg-blue-100">
                  {s.label}
                </button>
              ))}
            </div>
          </div>

          <div className="mb-4">
            <label className="text-sm text-gray-600 mb-1 block">Patient Transcript</label>
            <textarea value={transcript} onChange={e => setTranscript(e.target.value)} rows={4}
              placeholder="Type or select a sample transcript above..."
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-400 resize-none" />
          </div>

          {error && <p className="text-red-500 text-sm mb-3">{error}</p>}

          <button onClick={handleSimulate} disabled={loading}
            className="w-full bg-blue-600 text-white py-2 rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50">
            {loading ? '⏳ Running AI Pipeline...' : '▶️ Run Simulation'}
          </button>
        </div>

        {result && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 space-y-3">
            <div className="flex justify-between items-center">
              <h2 className="font-semibold text-gray-700">Results — {result.patient_name}</h2>
              <RiskBadge tier={result.risk_tier} />
            </div>
            <div className="text-sm text-gray-600 bg-gray-50 rounded-lg p-3 italic">"{result.transcript}"</div>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div><span className="text-gray-400">Topic:</span> <span className="font-medium">{result.nlp?.topic}</span></div>
              <div><span className="text-gray-400">Sentiment:</span> <span className="font-medium">{result.nlp?.sentiment}</span></div>
              <div><span className="text-gray-400">Severity:</span> <span className="font-medium">{result.nlp?.severity}/5</span></div>
              <div><span className="text-gray-400">Pain Level:</span> <span className="font-medium">{result.nlp?.structured_answer?.pain_level}</span></div>
            </div>
            {result.nlp?.keywords?.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {result.nlp.keywords.map((k, i) => <span key={i} className="bg-blue-50 text-blue-600 text-xs px-2 py-0.5 rounded-full">{k}</span>)}
              </div>
            )}
            {result.escalate && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">
                🚨 <strong>Escalation Required:</strong> {result.escalation_reason}
              </div>
            )}
            <p className="text-sm text-gray-600"><strong>Patient Concern:</strong> {result.nlp?.structured_answer?.patient_concern}</p>
          </div>
        )}
      </div>
    </div>
  )
}