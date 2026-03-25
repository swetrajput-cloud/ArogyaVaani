import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import RiskBadge from '../components/RiskBadge'
import { ArrowLeft, Play, Loader } from 'lucide-react'

const SAMPLE_TRANSCRIPTS = [
  { label: '🔴 Critical - Chest Pain', text: 'मुझे सीने में बहुत तेज दर्द हो रहा है और सांस नहीं आ रही', language: 'hindi' },
  { label: '🟡 Moderate - Fever', text: 'मुझे बुखार है और सिरदर्द हो रहा है, दवाई नहीं ली', language: 'hindi' },
  { label: '🟢 Good - Stable', text: 'मैं ठीक हूं, दवाई समय पर ले रहा हूं और खाना भी खा रहा हूं', language: 'hindi' },
  { label: '🔴 Critical - Unconscious', text: 'मरीज बेहोश हो गए हैं और हिल नहीं रहे', language: 'hindi' },
  { label: '🟡 Moderate - High BP', text: 'आज बीपी ज्यादा है, चक्कर आ रहे हैं और पैरों में सूजन है', language: 'hindi' },
]

export default function CallSimulator() {
  const navigate = useNavigate()
  const [patientId, setPatientId] = useState('1')
  const [transcript, setTranscript] = useState('')
  const [language, setLanguage] = useState('hindi')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  const runSimulation = async () => {
    if (!transcript.trim()) return alert('Enter a transcript first')
    setLoading(true)
    setResult(null)
    setError(null)
    try {
      const res = await axios.post('http://localhost:8000/simulate/call', {
        patient_id: parseInt(patientId),
        transcript,
        language,
      })
      setResult(res.data)
    } catch (e) {
      setError(e.response?.data?.detail || 'Simulation failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4 flex items-center gap-4">
        <button onClick={() => navigate('/')} className="text-gray-400 hover:text-gray-700">
          <ArrowLeft size={20} />
        </button>
        <div>
          <h1 className="font-bold text-gray-800">🎭 Call Simulator</h1>
          <p className="text-xs text-gray-400">Simulate patient calls and see AI pipeline in action</p>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-6 py-6 grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Left: Input */}
        <div className="space-y-4">
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4 space-y-4">
            <h2 className="font-semibold text-gray-700">Simulation Input</h2>

            {/* Patient ID */}
            <div>
              <label className="text-xs text-gray-500 mb-1 block">Patient ID</label>
              <input
                type="number"
                value={patientId}
                onChange={(e) => setPatientId(e.target.value)}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
                placeholder="e.g. 1"
              />
            </div>

            {/* Language */}
            <div>
              <label className="text-xs text-gray-500 mb-1 block">Language</label>
              <select
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
              >
                <option value="hindi">Hindi</option>
                <option value="marathi">Marathi</option>
                <option value="english">English</option>
                <option value="bengali">Bengali</option>
                <option value="tamil">Tamil</option>
              </select>
            </div>

            {/* Transcript */}
            <div>
              <label className="text-xs text-gray-500 mb-1 block">Patient Transcript</label>
              <textarea
                value={transcript}
                onChange={(e) => setTranscript(e.target.value)}
                rows={4}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300 resize-none"
                placeholder="Type what the patient said..."
              />
            </div>

            <button
              onClick={runSimulation}
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 bg-blue-600 text-white py-2.5 rounded-lg hover:bg-blue-700 transition disabled:opacity-50"
            >
              {loading ? <Loader size={16} className="animate-spin" /> : <Play size={16} />}
              {loading ? 'Running AI Pipeline...' : 'Run Simulation'}
            </button>

            {error && (
              <div className="bg-red-50 text-red-600 text-sm p-3 rounded-lg">{error}</div>
            )}
          </div>

          {/* Sample Transcripts */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
            <h2 className="font-semibold text-gray-700 mb-3">Sample Transcripts</h2>
            <div className="space-y-2">
              {SAMPLE_TRANSCRIPTS.map((s, i) => (
                <button
                  key={i}
                  onClick={() => { setTranscript(s.text); setLanguage(s.language) }}
                  className="w-full text-left text-xs bg-gray-50 hover:bg-blue-50 border border-gray-100 hover:border-blue-200 rounded-lg px-3 py-2 transition"
                >
                  <span className="font-medium">{s.label}</span>
                  <p className="text-gray-400 mt-0.5 truncate">{s.text}</p>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Right: Results */}
        <div className="space-y-4">
          {!result && !loading && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-8 text-center text-gray-400">
              <Play size={32} className="mx-auto mb-3 opacity-30" />
              <p className="text-sm">Run a simulation to see the AI pipeline results here</p>
              <p className="text-xs mt-1">Results will also appear live on the Dashboard</p>
            </div>
          )}

          {loading && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-8 text-center">
              <Loader size={32} className="mx-auto mb-3 animate-spin text-blue-500" />
              <p className="text-sm text-gray-500">Claude is analyzing the transcript...</p>
            </div>
          )}

          {result && (
            <>
              {/* Risk Result */}
              <div className={`rounded-xl shadow-sm border p-4 ${
                result.risk_tier === 'RED' ? 'bg-red-50 border-red-200' :
                result.risk_tier === 'AMBER' ? 'bg-yellow-50 border-yellow-200' :
                'bg-green-50 border-green-200'
              }`}>
                <div className="flex justify-between items-center mb-2">
                  <h2 className="font-semibold text-gray-700">Risk Assessment</h2>
                  <RiskBadge tier={result.risk_tier} />
                </div>
                {result.escalate && (
                  <div className="bg-red-100 text-red-700 text-xs p-2 rounded-lg mt-2">
                    ⚠️ ESCALATION TRIGGERED: {result.escalation_reason}
                  </div>
                )}
                {result.keywords?.length > 0 && (
                  <p className="text-xs text-gray-500 mt-2">
                    Keywords: {result.keywords.join(', ')}
                  </p>
                )}
              </div>

              {/* NLP Output */}
              <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
                <h2 className="font-semibold text-gray-700 mb-3">Claude NLP Output</h2>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-400">Topic</span>
                    <span className="font-medium text-gray-700">{result.nlp?.topic}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Sentiment</span>
                    <span className="font-medium text-gray-700">{result.nlp?.sentiment}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Severity</span>
                    <span className="font-medium text-gray-700">{result.nlp?.severity} / 5</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Pain Level</span>
                    <span className="font-medium text-gray-700">{result.nlp?.structured_answer?.pain_level}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Needs Followup</span>
                    <span className="font-medium text-gray-700">{result.nlp?.structured_answer?.needs_followup ? 'Yes' : 'No'}</span>
                  </div>
                  {result.nlp?.structured_answer?.symptoms?.length > 0 && (
                    <div>
                      <span className="text-gray-400 block mb-1">Symptoms Detected</span>
                      <div className="flex flex-wrap gap-1">
                        {result.nlp.structured_answer.symptoms.map((s, i) => (
                          <span key={i} className="bg-blue-50 text-blue-600 text-xs px-2 py-0.5 rounded-full">{s}</span>
                        ))}
                      </div>
                    </div>
                  )}
                  <div>
                    <span className="text-gray-400 block mb-1">Patient Concern</span>
                    <p className="text-gray-700 text-xs bg-gray-50 p-2 rounded-lg">{result.nlp?.structured_answer?.patient_concern}</p>
                  </div>
                </div>
              </div>

              {/* Keywords */}
              {result.nlp?.keywords?.length > 0 && (
                <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
                  <h2 className="font-semibold text-gray-700 mb-2">Clinical Keywords</h2>
                  <div className="flex flex-wrap gap-2">
                    {result.nlp.keywords.map((k, i) => (
                      <span key={i} className="bg-purple-50 text-purple-600 text-xs px-2 py-1 rounded-full">{k}</span>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}