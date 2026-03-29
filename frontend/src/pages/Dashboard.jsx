import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getPatients, getStats, initiateCall } from '../api/client'
import PatientCard from '../components/PatientCard'
import AdherenceChart from '../components/AdherenceChart'
import EscalationQueue from '../components/EscalationQueue'
import CallTranscript from '../components/CallTranscript'
import AppointmentQueue from '../components/AppointmentQueue'
import AdmissionQueue from '../components/AdmissionQueue'
import ScheduledCallsPanel from '../components/ScheduledCallsPanel'
import useWebSocket from '../hooks/useWebSocket'
import { Users, AlertTriangle, Activity, Wifi, WifiOff } from 'lucide-react'

const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function Dashboard() {
  const [patients, setPatients] = useState([])
  const [allRedPatients, setAllRedPatients] = useState([])
  const [stats, setStats] = useState(null)
  const [filter, setFilter] = useState('')
  const [loading, setLoading] = useState(true)
  const [appointments, setAppointments] = useState([])
  const [admissions, setAdmissions] = useState([])
  const { messages, connected } = useWebSocket()
  const navigate = useNavigate()

  useEffect(() => {
    fetchData()
    fetchAppointments()
    fetchAdmissions()
  }, [filter])

  useEffect(() => {
    const latest = messages[0]
    if (latest?.type === 'appointment') fetchAppointments()
    if (latest?.type === 'admission') fetchAdmissions()
    if (latest?.risk_tier === 'RED') fetchRedPatients()
  }, [messages])

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
    fetchRedPatients()
  }

  const fetchRedPatients = async () => {
    try {
      const res = await getPatients({ risk_tier: 'RED', limit: 120 })
      setAllRedPatients(res.data.patients || [])
    } catch (e) {
      console.error(e)
    }
  }

  const fetchAppointments = async () => {
    try {
      const res = await fetch(`${BASE}/appointments`)
      const data = await res.json()
      setAppointments(data.appointments || [])
    } catch (e) {
      console.error(e)
    }
  }

  const fetchAdmissions = async () => {
    try {
      const res = await fetch(`${BASE}/admissions`)
      const data = await res.json()
      setAdmissions(data.admissions || [])
    } catch (e) {
      console.error(e)
    }
  }

  const handleCall = async (id) => {
    try {
      await initiateCall(id)
      alert(`Call initiated for Patient #${id}`)
      fetchRedPatients()
    } catch (e) {
      alert('Call failed — check Twilio credentials')
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-800">🏥 AarogyaVaani</h1>
          <p className="text-xs text-gray-400">AI-Powered Multilingual Patient Engagement</p>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={() => navigate('/vaccination')}
            className="flex items-center gap-2 bg-green-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-green-700 transition">
            🍼 Vaccination
          </button>
          <button onClick={() => navigate('/calls')}
            className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-700 transition">
            📋 Call History
          </button>
          <button onClick={() => navigate('/simulator')}
            className="flex items-center gap-2 bg-purple-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-purple-700 transition">
            🎯 Call Simulator
          </button>
          <button onClick={() => navigate('/analytics')}
            className="flex items-center gap-2 bg-orange-500 text-white px-4 py-2 rounded-lg text-sm hover:bg-orange-600 transition">
            📊 Analytics
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
              { label: 'Total Patients', value: stats.total_patients, icon: <Users size={18} />,        color: 'text-blue-600 bg-blue-50'    },
              { label: 'High Risk',      value: stats.red,            icon: <AlertTriangle size={18} />, color: 'text-red-600 bg-red-50'      },
              { label: 'Moderate',       value: stats.amber,          icon: <Activity size={18} />,      color: 'text-yellow-600 bg-yellow-50'},
              { label: 'Low Risk',       value: stats.green,          icon: <Activity size={18} />,      color: 'text-green-600 bg-green-50'  },
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
            <div className="flex gap-2 mb-4">
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
            </div>

            {loading ? (
              <div className="text-center py-12 text-gray-400">Loading patients...</div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {patients.map((p) => (
                  <PatientCard key={p.id} patient={p} onCall={handleCall} />
                ))}
              </div>
            )}
          </div>

          {/* Right: Live Feed */}
          <div className="space-y-4">
            <AdherenceChart stats={stats} />
            <ScheduledCallsPanel patients={allRedPatients} onCallNow={handleCall} />
            <AdmissionQueue admissions={admissions} onRefresh={fetchAdmissions} />
            <AppointmentQueue appointments={appointments} onRefresh={fetchAppointments} />
            <EscalationQueue messages={messages} />
            <CallTranscript messages={messages} />
          </div>
        </div>
      </div>
    </div>
  )
}