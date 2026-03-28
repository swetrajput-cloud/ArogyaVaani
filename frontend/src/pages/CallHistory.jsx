import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

const RISK_COLORS = {
  RED:   { bg: 'bg-red-100',    text: 'text-red-700',    dot: 'bg-red-500',    label: 'High Risk' },
  AMBER: { bg: 'bg-yellow-100', text: 'text-yellow-700', dot: 'bg-yellow-500', label: 'Moderate' },
  GREEN: { bg: 'bg-green-100',  text: 'text-green-700',  dot: 'bg-green-500',  label: 'Low Risk' },
}

function RiskBadge({ tier }) {
  const c = RISK_COLORS[tier] || RISK_COLORS.GREEN
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${c.bg} ${c.text}`}>
      <span className={`w-2 h-2 rounded-full ${c.dot}`} />
      {c.label}
    </span>
  )
}

function StatCard({ label, value, color }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 flex flex-col gap-1 shadow-sm">
      <span className="text-sm text-gray-500">{label}</span>
      <span className={`text-3xl font-bold ${color}`}>{value}</span>
    </div>
  )
}

export default function CallHistory() {
  const navigate = useNavigate()
  const [calls, setCalls]       = useState([])
  const [stats, setStats]       = useState(null)
  const [loading, setLoading]   = useState(true)
  const [filter, setFilter]     = useState('ALL')
  const [escalated, setEscalated] = useState(false)
  const [selected, setSelected] = useState(null)

  useEffect(() => {
    fetchStats()
    fetchCalls()
  }, [filter, escalated])

  async function fetchStats() {
    const res = await fetch('http://localhost:8000/calls/stats')
    const data = await res.json()
    setStats(data)
  }

  async function fetchCalls() {
    setLoading(true)
    let url = 'http://localhost:8000/calls?limit=100'
    if (filter !== 'ALL') url += `&risk_tier=${filter}`
    if (escalated) url += `&escalated_only=true`
    const res = await fetch(url)
    const data = await res.json()
    setCalls(data.calls || [])
    setLoading(false)
  }

  function formatTime(iso) {
    if (!iso) return '—'
    return new Date(iso).toLocaleString('en-IN', {
      day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit'
    })
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button onClick={() => navigate('/')} className="text-gray-400 hover:text-gray-600 text-xl">←</button>
          <div>
            <h1 className="text-xl font-bold text-gray-900">Call History</h1>
            <p className="text-sm text-gray-500">All simulated & live calls</p>
          </div>
        </div>
        <button
          onClick={() => navigate('/simulator')}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700"
        >
          + New Simulation
        </button>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-6 space-y-6">
        {/* Stats */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <StatCard label="Total Calls"   value={stats.total_calls} color="text-gray-900" />
            <StatCard label="High Risk"     value={stats.red}         color="text-red-600" />
            <StatCard label="Moderate"      value={stats.amber}       color="text-yellow-600" />
            <StatCard label="Low Risk"      value={stats.green}       color="text-green-600" />
            <StatCard label="Escalated"     value={stats.escalated}   color="text-purple-600" />
          </div>
        )}

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex gap-2">
            {['ALL', 'RED', 'AMBER', 'GREEN'].map(f => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium border transition-all ${
                  filter === f
                    ? 'bg-blue-600 text-white border-blue-600'
                    : 'bg-white text-gray-600 border-gray-200 hover:border-blue-300'
                }`}
              >
                {f === 'ALL' ? 'All' : f === 'RED' ? '🔴 High' : f === 'AMBER' ? '🟡 Moderate' : '🟢 Low'}
              </button>
            ))}
          </div>
          <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer ml-2">
            <input
              type="checkbox"
              checked={escalated}
              onChange={e => setEscalated(e.target.checked)}
              className="rounded"
            />
            Escalated only
          </label>
          <span className="ml-auto text-sm text-gray-400">{calls.length} calls</span>
        </div>

        {/* Table */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          {loading ? (
            <div className="flex items-center justify-center py-20 text-gray-400">Loading calls...</div>
          ) : calls.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 text-gray-400 gap-3">
              <span className="text-4xl">📋</span>
              <p>No calls yet — run a simulation first!</p>
              <button onClick={() => navigate('/simulator')} className="text-blue-600 text-sm underline">
                Go to Simulator
              </button>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  {['Patient', 'Risk', 'Escalated', 'Topic', 'Severity', 'Transcript', 'Time', ''].map(h => (
                    <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {calls.map(call => (
                  <tr key={call.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-3">
                      <div className="font-medium text-gray-900">{call.patient_name}</div>
                      <div className="text-xs text-gray-400">{call.patient_phone}</div>
                    </td>
                    <td className="px-4 py-3"><RiskBadge tier={call.risk_tier} /></td>
                    <td className="px-4 py-3">
                      {call.escalate_flag
                        ? <span className="text-red-600 font-semibold">⚠ Yes</span>
                        : <span className="text-gray-400">No</span>}
                    </td>
                    <td className="px-4 py-3 text-gray-700 max-w-[140px] truncate">
                      {call.structured_output?.topic || '—'}
                    </td>
                    <td className="px-4 py-3">
                      {call.structured_output?.severity
                        ? <span className="font-semibold text-gray-800">{call.structured_output.severity}/5</span>
                        : '—'}
                    </td>
                    <td className="px-4 py-3 max-w-[200px]">
                      <p className="truncate text-gray-600">{call.transcript || '—'}</p>
                    </td>
                    <td className="px-4 py-3 text-gray-400 whitespace-nowrap">{formatTime(call.created_at)}</td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => setSelected(call)}
                        className="text-blue-600 hover:underline text-xs font-medium"
                      >
                        View
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Detail Modal */}
      {selected && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between p-6 border-b border-gray-200">
              <div>
                <h2 className="text-lg font-bold text-gray-900">{selected.patient_name}</h2>
                <p className="text-sm text-gray-500">{selected.call_sid}</p>
              </div>
              <button onClick={() => setSelected(null)} className="text-gray-400 hover:text-gray-600 text-2xl">×</button>
            </div>
            <div className="p-6 space-y-5">
              {/* Risk + Escalation */}
              <div className="flex gap-3 flex-wrap">
                <RiskBadge tier={selected.risk_tier} />
                {selected.escalate_flag && (
                  <span className="bg-red-50 text-red-700 px-3 py-1 rounded-full text-xs font-semibold">
                    ⚠ Escalated: {selected.escalation_reason}
                  </span>
                )}
              </div>

              {/* Transcript */}
              <div>
                <p className="text-xs font-semibold text-gray-500 uppercase mb-1">Transcript</p>
                <div className="bg-gray-50 rounded-lg p-3 text-gray-700 text-sm">{selected.transcript || '—'}</div>
              </div>

              {/* NLP Output */}
              {selected.structured_output && (
                <div>
                  <p className="text-xs font-semibold text-gray-500 uppercase mb-2">NLP Analysis</p>
                  <div className="grid grid-cols-2 gap-3">
                    {[
                      ['Topic',       selected.structured_output.topic],
                      ['Sentiment',   selected.structured_output.sentiment],
                      ['Severity',    selected.structured_output.severity ? `${selected.structured_output.severity}/5` : null],
                      ['Pain Level',  selected.structured_output.pain_level],
                      ['Needs Followup', selected.structured_output.needs_followup ? 'Yes' : 'No'],
                      ['Language',    selected.language],
                    ].map(([label, value]) => value && (
                      <div key={label} className="bg-gray-50 rounded-lg p-3">
                        <p className="text-xs text-gray-400">{label}</p>
                        <p className="font-semibold text-gray-800 capitalize">{value}</p>
                      </div>
                    ))}
                  </div>
                  {selected.structured_output.symptoms_detected?.length > 0 && (
                    <div className="mt-3">
                      <p className="text-xs text-gray-400 mb-1">Symptoms</p>
                      <div className="flex flex-wrap gap-2">
                        {selected.structured_output.symptoms_detected.map(s => (
                          <span key={s} className="bg-blue-50 text-blue-700 px-2 py-0.5 rounded-full text-xs">{s}</span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              <p className="text-xs text-gray-400 text-right">{formatTime(selected.created_at)}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}