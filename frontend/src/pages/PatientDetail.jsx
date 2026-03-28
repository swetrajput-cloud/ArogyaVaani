import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getPatient, initiateCall } from '../api/client'
import RiskBadge from '../components/RiskBadge'
import { ArrowLeft, Phone, Heart, Clock, AlertTriangle } from 'lucide-react'

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

export default function PatientDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [patient, setPatient] = useState(null)
  const [calls, setCalls] = useState([])
  const [selectedCall, setSelectedCall] = useState(null)
  const [callsLoading, setCallsLoading] = useState(true)

  useEffect(() => {
    getPatient(id).then((r) => setPatient(r.data)).catch(console.error)
    fetchPatientCalls()
  }, [id])

  // ✅ UPDATED: uses dedicated patient calls endpoint
  const fetchPatientCalls = async () => {
    setCallsLoading(true)
    try {
      const res = await fetch(`http://localhost:8000/calls/patient/${id}`)
      const data = await res.json()
      setCalls(data.calls || [])
    } catch (e) {
      console.error(e)
    } finally {
      setCallsLoading(false)
    }
  }

  const handleCall = async () => {
    try {
      await initiateCall(id)
      alert('Call initiated!')
    } catch {
      alert('Call failed — check Twilio credentials')
    }
  }

  function formatTime(iso) {
    if (!iso) return '—'
    return new Date(iso).toLocaleString('en-IN', {
      day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit'
    })
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

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4 flex items-center gap-4">
        <button onClick={() => navigate('/')} className="text-gray-400 hover:text-gray-700">
          <ArrowLeft size={20} />
        </button>
        <div className="flex-1">
          <h1 className="font-bold text-gray-800">{patient.name}</h1>
          <p className="text-xs text-gray-400">{patient.health_camp_name}</p>
        </div>
        <RiskBadge tier={patient.current_risk_tier} />
        <button
          onClick={() => navigate(`/simulator?patient_id=${id}`)}
          className="flex items-center gap-2 bg-purple-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-purple-700 transition"
        >
          🎯 Simulate Call
        </button>
        <button
          onClick={handleCall}
          className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-700 transition"
        >
          <Phone size={14} /> Call Patient
        </button>
      </div>

      <div className="max-w-4xl mx-auto px-6 py-6 space-y-6">

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
            <Stat label="Systolic BP"   value={patient.systolic_bp}        unit="mmHg" />
            <Stat label="Diastolic BP"  value={patient.diastolic_bp}       unit="mmHg" />
            <Stat label="Heart Rate"    value={patient.heart_rate}          unit="bpm"  />
            <Stat label="SpO2"          value={patient.oxygen_saturation}   unit="%"    />
            <Stat label="Temperature"   value={patient.temperature}         unit="°F"   />
            <Stat label="Blood Glucose" value={patient.blood_glucose}       unit="mg/dL"/>
            <Stat label="BMI"           value={patient.bmi?.toFixed(1)}     unit=""     />
            <Stat label="BMI Category"  value={patient.bmi_category}        unit=""     />
          </div>
        </div>

        {/* Risk Scores */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
          <h2 className="font-semibold text-gray-700 mb-3">Risk Assessment</h2>
          <RiskRow label="Heart Risk"        level={patient.heart_risk_level}        score={patient.heart_risk_total_score} />
          <RiskRow label="Diabetic Risk"     level={patient.diabetic_risk_level}     score={patient.diabetic_risk_total_score} />
          <RiskRow label="Hypertension Risk" level={patient.hypertension_risk_level} score={patient.hypertension_risk_total_score} />
          <div className="flex justify-between items-center pt-2">
            <span className="text-sm font-semibold text-gray-700">Overall Risk Score</span>
            <span className="text-lg font-bold text-gray-800">{patient.overall_risk_score?.toFixed(1) ?? '—'}</span>
          </div>
        </div>

        {/* Symptoms & Lifestyle */}
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
                <span className={`font-medium ${val === 'Yes' ? 'text-red-500' : 'text-gray-400'}`}>
                  {val || '—'}
                </span>
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
              <button
                onClick={() => navigate(`/simulator?patient_id=${id}`)}
                className="mt-2 text-blue-600 text-sm underline"
              >
                Run a simulation
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              {calls.map(call => (
                <div
                  key={call.id}
                  onClick={() => setSelectedCall(selectedCall?.id === call.id ? null : call)}
                  className="border border-gray-100 rounded-lg p-3 cursor-pointer hover:bg-gray-50 transition-colors"
                >
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
                      <span className="text-xs text-blue-500">
                        {selectedCall?.id === call.id ? '▲' : '▼'}
                      </span>
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
                        <p className="text-xs text-red-600 bg-red-50 rounded p-2">
                          ⚠ {call.escalation_reason}
                        </p>
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