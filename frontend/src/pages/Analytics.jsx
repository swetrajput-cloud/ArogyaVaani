import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts'
import { ArrowLeft, TrendingUp, Phone, AlertTriangle, Calendar } from 'lucide-react'

const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const COLORS = { RED: '#ef4444', AMBER: '#f59e0b', GREEN: '#22c55e' }
const PIE_COLORS = ['#ef4444', '#f59e0b', '#22c55e']

export default function Analytics() {
  const navigate = useNavigate()
  const [overview, setOverview]     = useState(null)
  const [callsData, setCallsData]   = useState([])
  const [symptoms, setSymptoms]     = useState({ topics: [], symptoms: [] })
  const [days, setDays]             = useState(7)
  const [loading, setLoading]       = useState(true)

  useEffect(() => { fetchAll() }, [days])

  const fetchAll = async () => {
    setLoading(true)
    try {
      const [ov, ct, sy] = await Promise.all([
        fetch(`${BASE}/analytics/overview`).then(r => r.json()),
        fetch(`${BASE}/analytics/calls-over-time?days=${days}`).then(r => r.json()),
        fetch(`${BASE}/analytics/top-symptoms`).then(r => r.json()),
      ])
      setOverview(ov)
      setCallsData(ct.data || [])
      setSymptoms(sy)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const pieData = overview ? [
    { name: 'High Risk',  value: overview.risk_distribution.RED   },
    { name: 'Moderate',   value: overview.risk_distribution.AMBER },
    { name: 'Low Risk',   value: overview.risk_distribution.GREEN },
  ] : []

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button onClick={() => navigate('/')}
            className="p-2 hover:bg-gray-100 rounded-lg transition">
            <ArrowLeft size={18} />
          </button>
          <div>
            <h1 className="text-xl font-bold text-gray-800">📊 Analytics</h1>
            <p className="text-xs text-gray-400">Structured data & reporting dashboard</p>
          </div>
        </div>
        <div className="flex gap-2">
          {[7, 14, 30].map(d => (
            <button key={d} onClick={() => setDays(d)}
              className={`px-3 py-1 rounded-full text-xs font-medium transition ${
                days === d ? 'bg-blue-600 text-white' : 'bg-white border border-gray-200 text-gray-500 hover:bg-gray-50'
              }`}>
              {d}d
            </button>
          ))}
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-6">
        {loading ? (
          <div className="text-center py-20 text-gray-400">Loading analytics...</div>
        ) : (
          <>
            {/* Overview cards */}
            {overview && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                {[
                  { label: 'Total Calls',      value: overview.total_calls,      icon: <Phone size={18} />,         color: 'text-blue-600 bg-blue-50'   },
                  { label: 'Escalated',         value: overview.escalated,         icon: <AlertTriangle size={18} />, color: 'text-red-600 bg-red-50'     },
                  { label: 'Appointments',      value: overview.appointments,      icon: <Calendar size={18} />,      color: 'text-purple-600 bg-purple-50'},
                  { label: 'Confirmed Appts',   value: overview.confirmed_appointments, icon: <TrendingUp size={18} />, color: 'text-green-600 bg-green-50'},
                ].map(s => (
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

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
              {/* Call volume over time */}
              <div className="lg:col-span-2 bg-white rounded-xl shadow-sm border border-gray-100 p-5">
                <h2 className="font-semibold text-gray-700 mb-4">📞 Call Volume by Risk — Last {days} days</h2>
                <ResponsiveContainer width="100%" height={240}>
                  <BarChart data={callsData} margin={{ top: 4, right: 16, left: 0, bottom: 4 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis dataKey="date" tick={{ fontSize: 11 }}
                      tickFormatter={d => d.slice(5)} />
                    <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                    <Tooltip
                      formatter={(val, name) => [val, name]}
                      labelFormatter={l => `Date: ${l}`}
                    />
                    <Legend wrapperStyle={{ fontSize: 12 }} />
                    <Bar dataKey="RED"   name="High Risk" fill={COLORS.RED}   stackId="a" radius={[0,0,0,0]} />
                    <Bar dataKey="AMBER" name="Moderate"  fill={COLORS.AMBER} stackId="a" />
                    <Bar dataKey="GREEN" name="Low Risk"  fill={COLORS.GREEN} stackId="a" radius={[4,4,0,0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* Risk distribution pie */}
              <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
                <h2 className="font-semibold text-gray-700 mb-4">🎯 Risk Distribution</h2>
                <ResponsiveContainer width="100%" height={200}>
                  <PieChart>
                    <Pie data={pieData} cx="50%" cy="50%" innerRadius={55} outerRadius={85}
                      paddingAngle={3} dataKey="value" label={({ name, percent }) =>
                        `${(percent * 100).toFixed(0)}%`
                      } labelLine={false}>
                      {pieData.map((_, i) => (
                        <Cell key={i} fill={PIE_COLORS[i]} />
                      ))}
                    </Pie>
                    <Tooltip />
                    <Legend wrapperStyle={{ fontSize: 12 }} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Top topics */}
              <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
                <h2 className="font-semibold text-gray-700 mb-4">🏥 Top Reported Topics</h2>
                {symptoms.topics.length === 0 ? (
                  <p className="text-sm text-gray-400">No topic data yet — make some calls first.</p>
                ) : (
                  <ResponsiveContainer width="100%" height={240}>
                    <BarChart data={symptoms.topics} layout="vertical"
                      margin={{ top: 4, right: 16, left: 60, bottom: 4 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                      <XAxis type="number" tick={{ fontSize: 11 }} allowDecimals={false} />
                      <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} width={80} />
                      <Tooltip />
                      <Bar dataKey="count" name="Calls" fill="#3b82f6" radius={[0,4,4,0]} />
                    </BarChart>
                  </ResponsiveContainer>
                )}
              </div>

              {/* Top symptoms */}
              <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
                <h2 className="font-semibold text-gray-700 mb-4">🩺 Top Reported Symptoms</h2>
                {symptoms.symptoms.length === 0 ? (
                  <p className="text-sm text-gray-400">No symptom data yet — make some calls first.</p>
                ) : (
                  <ResponsiveContainer width="100%" height={240}>
                    <BarChart data={symptoms.symptoms} layout="vertical"
                      margin={{ top: 4, right: 16, left: 60, bottom: 4 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                      <XAxis type="number" tick={{ fontSize: 11 }} allowDecimals={false} />
                      <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} width={80} />
                      <Tooltip />
                      <Bar dataKey="count" name="Count" fill="#8b5cf6" radius={[0,4,4,0]} />
                    </BarChart>
                  </ResponsiveContainer>
                )}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}