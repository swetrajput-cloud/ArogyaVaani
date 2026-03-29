import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getPatient, initiateCall } from '../api/client'
import RiskBadge from '../components/RiskBadge'
import { ArrowLeft, Phone, Heart, Clock, AlertTriangle, TrendingUp, TrendingDown, Minus } from 'lucide-react'

const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const RISK_COLORS = {
  RED:   { bg: 'bg-red-100',    text: 'text-red-700',    dot: 'bg-red-500' },
  AMBER: { bg: 'bg-yellow-100', text: 'text-yellow-700', dot: 'bg-yellow-500' },
  GREEN: { bg: 'bg-green-100',  text: 'text-green-700',  dot: 'bg-green-500' },
}

function RiskPill({ tier }) {
  const c = RISK_COLORS[tier] || RISK_COLORS.GREEN
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${c.bg} ${c.text}`}>
      <span className={`w-2 h-2 rounded-full ${c.dot}`} />
      {tier}
    </span>
  )
}

function getTrend(calls) {
  if (!calls || calls.length < 2) return null
  const sorted = [...calls].reverse()
  const riskToNum = { GREEN: 1, AMBER: 2, RED: 3 }
  const recent = sorted.slice(-3)
  const first = riskToNum[recent[0]?.risk_tier] || 1
  const last  = riskToNum[recent[recent.length - 1]?.risk_tier] || 1
  if (last > first) return 'worsening'
  if (last < first) return 'improving'
  return 'stable'
}

function TrendBadge({ calls }) {
  const trend = getTrend(calls)
  if (!trend) return null
  const config = {
    worsening: { icon: <TrendingUp size={13} />,   label: 'Worsening', cls: 'bg-red-100 text-red-700'       },
    stable:    { icon: <Minus size={13} />,         label: 'Stable',    cls: 'bg-gray-100 text-gray-600'     },
    improving: { icon: <TrendingDown size={13} />,  label: 'Improving', cls: 'bg-green-100 text-green-700'   },
  }
  const { icon, label, cls } = config[trend]
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${cls}`}>
      {icon} {label}
    </span>
  )
}

function NextCallBadge({ patient }) {
  if (!patient) return null
  const isRed   = patient.current_risk_tier === 'RED'
  const isAmber = patient.current_risk_tier === 'AMBER'
  if (!isRed && !isAmber) return null

  const intervalMs = isRed
    ? 2 * 60 * 60 * 1000           // 2 hours
    : 14 * 24 * 60 * 60 * 1000     // 2 weeks

  if (!patient.last_called_at) {
    return (
      <div className="bg-orange-50 border border-orange-100 rounded-lg px-3 py-2 text-xs text-orange-700">
        ⏰ Auto follow-up: <strong>Never called — scheduler will call soon</strong>
      </div>
    )
  }

  const nextCall = new Date(new Date(patient.last_called_at).getTime() + intervalMs)
  const now      = new Date()
  const diff     = nextCall - now

  let timeLabel
  if (diff <= 0) {
    timeLabel = 'Due now'
  } else {
    const days  = Math.floor(diff / 86400000)
    const hours = Math.floor((diff % 86400000) / 3600000)
    const mins  = Math.floor((diff % 3600000) / 60000)
    timeLabel = days > 0 ? `in ${days}d ${hours}h` : hours > 0 ? `in ${hours}h ${mins}m` : `in ${mins}m`
  }

  return (
    <div className="bg-blue-50 border border-blue-100 rounded-lg px-3 py-2 text-xs text-blue-700">
      ⏰ Next auto follow-up: <strong>{timeLabel}</strong>
      {' '}({nextCall.toLocaleString('en-IN', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })})
      {isAmber && <span className="ml-2 text-yellow-600 font-medium">· AMBER 2-week schedule</span>}
      {isRed   && <span className="ml-2 text-red-600 font-medium">· RED 2-hour schedule</span>}
    </div>
  )
}

function RiskTrendChart({ calls }) {
  if (!calls || calls.length === 0) return null

  const sorted = [...calls].reverse()
  const riskToNum  = { GREEN: 1, AMBER: 2, RED: 3 }
  const numToLabel = { 1: 'Low', 2: 'Moderate', 3: 'High' }
  const numToColor = { 1: '#22c55e', 2: '#f59e0b', 3: '#ef4444' }

  const points = sorted.map((c, i) => ({
    x: i, y: riskToNum[c.risk_tier] || 1,
    label: new Date(c.created_at).toLocaleDateString('en-IN', { day: '2-digit', month: 'short' }),
    tier: c.risk_tier,
  }))

  const W = 500, H = 120
  const PAD = { top: 16, bottom: 32, left: 40, right: 16 }
  const chartW = W - PAD.left - PAD.right
  const chartH = H - PAD.top - PAD.bottom
  const xStep  = points.length > 1 ? chartW / (points.length - 1) : chartW / 2
  const yScale = (val) => chartH - ((val - 1) / 2) * chartH
  const toXY   = (p, i) => ({
    cx: PAD.left + (points.length > 1 ? i * xStep : chartW / 2),
    cy: PAD.top + yScale(p.y),
  })
  const coords = points.map((p, i) => toXY(p, i))
  const pathD  = coords.map((c, i) => `${i === 0 ? 'M' : 'L'} ${c.cx} ${c.cy}`).join(' ')

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
      <div className="flex items-center justify-between mb-3">
        <h2 className="font-semibold text-gray-700 flex items-center gap-2">
          <TrendingUp size={16} className="text-blue-500" /> Risk Trend
        </h2>
        <TrendBadge calls={calls} />
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ height: 140 }}>
        {[1, 2, 3].map(v => (
          <g key={v}>
            <line x1={PAD.left} y1={PAD.top + yScale(v)} x2={W - PAD.right} y2={PAD.top + yScale(v)}
              stroke="#f3f4f6" strokeWidth="1" />
            <text x={PAD.left - 6} y={PAD.top + yScale(v) + 4}
              textAnchor="end" fontSize="9" fill="#9ca3af">{numToLabel[v]}</text>
          </g>
        ))}
        {points.length > 1 && (
          <path d={pathD} fill="none" stroke="#3b82f6" strokeWidth="2" strokeLinejoin="round" />
        )}
        {coords.map((c, i) => (
          <g key={i}>
            <circle cx={c.cx} cy={c.cy} r="5"
              fill={numToColor[points[i].y]} stroke="white" strokeWidth="2" />
            <text x={c.cx} y={H - 6} textAnchor="middle" fontSize="9" fill="#9ca3af">
              {points[i].label}
            </text>
          </g>
        ))}
      </svg>
      <div className="flex gap-4 mt-1 justify-center">
        {[['#22c55e', 'Low'], ['#f59e0b', 'Moderate'], ['#ef4444', 'High']].map(([color, label]) => (
          <div key={label} className="flex items-center gap-1.5 text-xs text-gray-500">
            <span className="w-2.5 h-2.5 rounded-full" style={{ background: color }} />
            {label}
          </div>
        ))}
      </div>
    </div>
  )
}

export default function PatientDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [patient, setPatient]         = useState(null)
  const [calls, setCalls]             = useState([])
  const [selectedCall, setSelectedCall] = useState(null)
  const [callsLoading, setCallsLoading] = useState(true)
  const [calling, setCalling]         = useState(false)
  const [callStatus, setCallStatus]   = useState('')

  useEffect(() => {
    getPatient(id).then((r) => setPatient(r.data)).catch(console.error)
    fetchPatientCalls()
  }, [id])

  const fetchPatientCalls = async () => {
    setCallsLoading(true)
    try {
      const res  = await fetch(`${BASE}/calls/patient/${id}`)
      const data = await res.json()
      setCalls(data.calls || [])
    } catch (e) { console.error(e) }
    finally { setCallsLoading(false) }
  }

  const handleCall = async () => {
    setCalling(true); setCallStatus('')
    try {
      await initiateCall(id)
      setCallStatus('success')
      const res  = await getPatient(id)
      setPatient(res.data)
    } catch { setCallStatus('error') }
    finally { setCalling(false); setTimeout(() => setCallStatus(''), 3000) }
  }

  function formatTime(iso) {
    if (!iso) return '—'
    return new Date(iso).toLocaleString('en-IN', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })
  }

  const Stat = ({ label, value, unit }) => (
    <div className="bg-gray-50 rounded-lg p-3 text-center">
      <p className="text-xs text-gray-400 mb-1">{label}</p>
      <p className="font-bold text-gray-800">
        {value ?? '—'} <span className="text-xs font-normal text-gray-400">{unit}</span>
      </p>
    </div>
  )

  const RiskRow = ({ label, level, score }) => {
    const color = level === 'High' ? 'text-red-600' : level === 'Moderate' ? 'text-yellow-600' : 'text-green-600'
    return (
      <div className="flex justify-between items-center py-2 border-b border-gray-50">
        <span className="text-sm text-gray-600">{label}</span>
        <div className="text-right">
          <span className={`text-sm font-semibold ${color}`}>{level || '—'}</span>
          {score != null && <span className="text-xs text-gray-400 ml-2">({score.toFixed(1)})</span>}
        </div>
      </div>
    )
  }

  if (!patient) return <div className="text-center py-20 text-gray-400">Loading...</div>

  const redCalls   = calls.filter(c => c.risk_tier === 'RED').length
  const amberCalls = calls.filter(c => c.risk_tier === 'AMBER').length
  const escalated  = calls.filter(c => c.escalate_flag).length

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white border-b border-gray-200 px-6 py-4 flex items-center gap-4">
        <button onClick={() => navigate('/')} className="text-gray-400 hover:text-gray-700">
          <ArrowLeft size={20} />
        </button>
        <div className="flex-1">
          <h1 className="font-bold text-gray-800">{patient.name}</h1>
          <p className="text-xs text-gray-400">{patient.health_camp_name} · {patient.phone}</p>
        </div>
        <RiskBadge tier={patient.current_risk_tier} />
        <button onClick={() => navigate(`/simulator?patient_id=${id}`)}
          className="flex items-center gap-2 bg-purple-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-purple-700 transition">
          🎯 Simulate
        </button>
        <button onClick={handleCall} disabled={calling}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition
            ${calling ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
              : callStatus === 'success' ? 'bg-green-500 text-white'
              : callStatus === 'error'   ? 'bg-red-500 text-white'
              : 'bg-blue-600 text-white hover:bg-blue-700'}`}>
          <Phone size={14} />
          {calling ? 'Calling...' : callStatus === 'success' ? '✅ Called' : callStatus === 'error' ? '❌ Failed' : 'Call Patient'}
        </button>
      </div>

      <div className="max-w-4xl mx-auto px-6 py-6 space-y-6">

        {/* Quick stats */}
        <div className="grid grid-cols-4 gap-3">
          {[
            { label: 'Total Calls', value: calls.length,  color: 'text-blue-600'   },
            { label: 'High Risk',   value: redCalls,       color: 'text-red-600'    },
            { label: 'Moderate',    value: amberCalls,     color: 'text-yellow-600' },
            { label: 'Escalated',   value: escalated,      color: 'text-purple-600' },
          ].map(s => (
            <div key={s.label} className="bg-white rounded-xl shadow-sm border border-gray-100 p-3 text-center">
              <p className={`text-2xl font-bold ${s.color}`}>{s.value}</p>
              <p className="text-xs text-gray-400 mt-1">{s.label}</p>
            </div>
          ))}
        </div>

        {/* Next scheduled call info */}
        <NextCallBadge patient={patient} />

        {/* Risk trend chart */}
        <RiskTrendChart calls={calls} />

        {/* Condition */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
          <h2 className="font-semibold text-gray-700 mb-1">Condition</h2>
          <p className="text-gray-600">{patient.condition}</p>
          <p className="text-xs text-gray-400 mt-1">Module: {patient.module_type} | Language: {patient.language}</p>
        </div>

        {/* Vitals */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
          <h2 className="font-semibold text-gray-700 mb-3 flex items-center gap-2">
            <Heart size={16} className="text-red-500" /> Vitals
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <Stat label="Systolic BP"   value={patient.systolic_bp}       unit="mmHg"  />
            <Stat label="Diastolic BP"  value={patient.diastolic_bp}      unit="mmHg"  />
            <Stat label="Heart Rate"    value={patient.heart_rate}         unit="bpm"   />
            <Stat label="SpO2"          value={patient.oxygen_saturation}  unit="%"     />
            <Stat label="Temperature"   value={patient.temperature}        unit="°F"    />
            <Stat label="Blood Glucose" value={patient.blood_glucose}      unit="mg/dL" />
            <Stat label="BMI"           value={patient.bmi?.toFixed(1)}    unit=""      />
            <Stat label="BMI Category"  value={patient.bmi_category}       unit=""      />
          </div>
        </div>

        {/* Risk Assessment */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
          <h2 className="font-semibold text-gray-700 mb-3">Risk Assessment</h2>
          <RiskRow label="Heart Risk"        level={patient.heart_risk_level}        score={patient.heart_risk_total_score}        />
          <RiskRow label="Diabetic Risk"     level={patient.diabetic_risk_level}     score={patient.diabetic_risk_total_score}     />
          <RiskRow label="Hypertension Risk" level={patient.hypertension_risk_level} score={patient.hypertension_risk_total_score} />
          <div className="flex justify-between items-center pt-2">
            <span className="text-sm font-semibold text-gray-700">Overall Risk Score</span>
            <span className="text-lg font-bold text-gray-800">{patient.overall_risk_score?.toFixed(1) ?? '—'}</span>
          </div>
        </div>

        {/* Symptoms + Lifestyle */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
            <h2 className="font-semibold text-gray-700 mb-3">Symptoms</h2>
            {[
              ['Chest Discomfort',      patient.chest_discomfort],
              ['Breathlessness',        patient.breathlessness],
              ['Palpitations',          patient.palpitations],
              ['Fatigue / Weakness',    patient.fatigue_weakness],
              ['Dizziness / Blackouts', patient.dizziness_blackouts],
            ].map(([label, val]) => (
              <div key={label} className="flex justify-between py-1.5 border-b border-gray-50 text-sm">
                <span className="text-gray-500">{label}</span>
                <span className={`font-medium ${val === 'Yes' ? 'text-red-500' : 'text-gray-400'}`}>{val || '—'}</span>
              </div>
            ))}
          </div>
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
            <h2 className="font-semibold text-gray-700 mb-3">Lifestyle</h2>
            {[
              ['Sleep Duration',      patient.sleep_duration],
              ['Stress / Anxiety',    patient.stress_anxiety],
              ['Physical Inactivity', patient.physical_inactivity],
              ['Diet Quality',        patient.diet_quality],
              ['Family History',      patient.family_history],
            ].map(([label, val]) => (
              <div key={label} className="flex justify-between py-1.5 border-b border-gray-50 text-sm">
                <span className="text-gray-500">{label}</span>
                <span className="font-medium text-gray-600">{val || '—'}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Call History */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
          <h2 className="font-semibold text-gray-700 mb-4 flex items-center gap-2">
            <Clock size={16} className="text-blue-500" /> Call History
            <span className="ml-auto text-xs text-gray-400 font-normal">{calls.length} calls</span>
          </h2>
          {callsLoading ? (
            <p className="text-center text-gray-400 py-6 text-sm">Loading calls...</p>
          ) : calls.length === 0 ? (
            <div className="text-center py-8 text-gray-400">
              <p className="text-sm">No calls yet for this patient</p>
              <button onClick={() => navigate(`/simulator?patient_id=${id}`)}
                className="mt-2 text-blue-600 text-sm underline">Run a simulation</button>
            </div>
          ) : (
            <div className="space-y-3">
              {calls.map(call => (
                <div key={call.id}
                  onClick={() => setSelectedCall(selectedCall?.id === call.id ? null : call)}
                  className="border border-gray-100 rounded-lg p-3 cursor-pointer hover:bg-gray-50 transition-colors">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <RiskPill tier={call.risk_tier} />
                      {call.escalate_flag && (
                        <span className="flex items-center gap-1 text-xs text-red-600 font-medium">
                          <AlertTriangle size={12} /> Escalated
                        </span>
                      )}
                      <span className="text-sm text-gray-600 font-medium">
                        {call.structured_output?.topic || 'General'}
                      </span>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-xs text-gray-400">{formatTime(call.created_at)}</span>
                      <span className="text-xs text-blue-500">{selectedCall?.id === call.id ? '▲' : '▼'}</span>
                    </div>
                  </div>
                  {selectedCall?.id === call.id && (
                    <div className="mt-3 pt-3 border-t border-gray-100 space-y-3">
                      <div>
                        <p className="text-xs font-semibold text-gray-400 uppercase mb-1">Transcript</p>
                        <p className="text-sm text-gray-700 bg-gray-50 rounded p-2">{call.transcript || '—'}</p>
                      </div>
                      {call.structured_output && (
                        <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                          {[
                            ['Sentiment',  call.structured_output.sentiment],
                            ['Severity',   call.structured_output.severity ? `${call.structured_output.severity}/5` : null],
                            ['Pain Level', call.structured_output.structured_answer?.pain_level],
                            ['Followup',   call.structured_output.structured_answer?.needs_followup ? 'Yes' : 'No'],
                            ['Language',   call.language],
                            ['Status',     call.call_status],
                          ].filter(([, v]) => v).map(([label, value]) => (
                            <div key={label} className="bg-gray-50 rounded p-2">
                              <p className="text-xs text-gray-400">{label}</p>
                              <p className="text-sm font-semibold text-gray-800 capitalize">{value}</p>
                            </div>
                          ))}
                        </div>
                      )}
                      {call.escalation_reason && (
                        <p className="text-xs text-red-600 bg-red-50 rounded p-2">⚠ {call.escalation_reason}</p>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}