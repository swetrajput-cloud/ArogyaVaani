import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getPatients, getStats, initiateCall } from '../api/client'
import PatientCard from '../components/PatientCard'
import AdherenceChart from '../components/AdherenceChart'
import EscalationQueue from '../components/EscalationQueue'
import CallTranscript from '../components/CallTranscript'
import useWebSocket from '../hooks/useWebSocket'
import { Users, AlertTriangle, Activity, Wifi, WifiOff, Calendar } from 'lucide-react'

export default function Dashboard() {
  const [patients, setPatients] = useState([])
  const [stats, setStats] = useState(null)
  const [filter, setFilter] = useState('')
  const [dateFilter, setDateFilter] = useState('')
  const [loading, setLoading] = useState(true)
  const { messages, connected } = useWebSocket()
  const navigate = useNavigate()

  useEffect(() => {
    fetchData()
  }, [filter])

  const fetchData = async () => {
    setLoading(true)
    try {
      const [pRes, sRes] = await Promise.all([
        getPatients({ risk_tier: filter || undefined, limit: 120 }),
        getStats(),
      ])
      setPatients(pRes.data.patients)
      setStats(sRes.data)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const handleCall = async (id) => {
    try {
      await initiateCall(id)
      alert(`Call initiated for Patient #${id}`)
    } catch (e) {
      alert('Call failed — check Twilio credentials')
    }
  }

  // Filter by visit date on frontend
  const displayedPatients = dateFilter
    ? patients.filter(p => p.visit_date && p.visit_date === dateFilter)
    : patients

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-800">🏥 AarogyaVaani</h1>
          <p className="text-xs text-gray-400">AI-Powered Multilingual Patient Engagement</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/simulator')}
            className="flex items-center gap-2 bg-purple-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-purple-700 transition"
          >
            🎭 Call Simulator
          </button>
          {connected
            ? <span className="flex items-center gap-1 text-xs text-green-600"><Wifi size={13} /> Live</span>
            : <span className="flex items-center gap-1 text-xs text-gray-400"><WifiOff size={13} /> Offline</span>
          }
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-6">
        {/* Stats Cards */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            {[
              { label: 'Total Patients', value: stats.total_patients, icon: <Users size={18} />, color: 'text-blue-600 bg-blue-50' },
              { label: 'High Risk', value: stats.red, icon: <AlertTriangle size={18} />, color: 'text-red-600 bg-red-50' },
              { label: 'Moderate', value: stats.amber, icon: <Activity size={18} />, color: 'text-yellow-600 bg-yellow-50' },
              { label: 'Low Risk', value: stats.green, icon: <Activity size={18} />, color: 'text-green-600 bg-green-50' },
            ].map((s) => (
              <div key={s.label} className="bg-white rounded-xl shadow-sm border border-gray-100 p-4 flex items-center gap-3">
                <div className={`p-2 rounded-lg ${s.color}`}>{s.icon}</div>
                <div>
                  <p className="text-2xl font-bold text-gray-800">{s.value}</p>
                  <p className="text-xs text-gray-400">{s.label}</p>
                </div>
              </div>
            ))}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left: Patient List */}
          <div className="lg:col-span-2">
            {/* Risk Filter + Date Filter */}
            <div className="flex flex-wrap gap-2 mb-4 items-center">
              {['', 'RED', 'AMBER', 'GREEN'].map((t) => (
                <button
                  key={t}
                  onClick={() => setFilter(t)}
                  className={`px-3 py-1 rounded-full text-xs font-medium transition ${
                    filter === t
                      ? 'bg-blue-600 text-white'
                      : 'bg-white text-gray-500 border border-gray-200 hover:bg-gray-50'
                  }`}
                >
                  {t === '' ? 'All' : t}
                </button>
              ))}

              {/* Date filter */}
              <div className="flex items-center gap-1 ml-auto">
                <Calendar size={14} className="text-gray-400" />
                <input
                  type="date"
                  value={dateFilter}
                  onChange={e => setDateFilter(e.target.value)}
                  className="text-xs border border-gray-200 rounded-lg px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-300"
                />
                {dateFilter && (
                  <button
                    onClick={() => setDateFilter('')}
                    className="text-xs text-gray-400 hover:text-red-500 ml-1"
                  >
                    ✕
                  </button>
                )}
              </div>
            </div>

            {/* Visit date label */}
            {dateFilter && (
              <p className="text-xs text-blue-600 mb-3 font-medium">
                Showing patients who visited on {dateFilter} — {displayedPatients.length} found
              </p>
            )}
            {!dateFilter && (
              <p className="text-xs text-gray-400 mb-3">
                Sorted by visit date — most recent first
              </p>
            )}

            {loading ? (
              <div className="text-center py-12 text-gray-400">Loading patients...</div>
            ) : displayedPatients.length === 0 ? (
              <div className="text-center py-12 text-gray-400">No patients found for this date.</div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {displayedPatients.map((p) => (
                  <PatientCard key={p.id} patient={p} onCall={handleCall} />
                ))}
              </div>
            )}
          </div>

          {/* Right: Live Feed */}
          <div className="space-y-4">
            <AdherenceChart stats={stats} />
            <EscalationQueue messages={messages} />
            <CallTranscript messages={messages} />
          </div>
        </div>
      </div>
    </div>
  )
}