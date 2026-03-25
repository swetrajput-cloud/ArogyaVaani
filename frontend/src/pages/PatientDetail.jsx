import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getPatient, initiateCall } from '../api/client'
import RiskBadge from '../components/RiskBadge'
import { ArrowLeft, Phone, Heart, Droplets, Wind, Thermometer } from 'lucide-react'

export default function PatientDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [patient, setPatient] = useState(null)

  useEffect(() => {
    getPatient(id).then((r) => setPatient(r.data)).catch(console.error)
  }, [id])

  if (!patient) return <div className="text-center py-20 text-gray-400">Loading...</div>

  const handleCall = async () => {
    try {
      await initiateCall(id)
      alert('Call initiated!')
    } catch {
      alert('Call failed — check Twilio credentials')
    }
  }

  const Stat = ({ label, value, unit }) => (
    <div className="bg-gray-50 rounded-lg p-3 text-center">
      <p className="text-xs text-gray-400 mb-1">{label}</p>
      <p className="font-bold text-gray-800">{value ?? '—'} <span className="text-xs font-normal text-gray-400">{unit}</span></p>
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

  return (
    <div className="min-h-screen bg-gray-50">
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
            <Stat label="Systolic BP" value={patient.systolic_bp} unit="mmHg" />
            <Stat label="Diastolic BP" value={patient.diastolic_bp} unit="mmHg" />
            <Stat label="Heart Rate" value={patient.heart_rate} unit="bpm" />
            <Stat label="SpO2" value={patient.oxygen_saturation} unit="%" />
            <Stat label="Temperature" value={patient.temperature} unit="°F" />
            <Stat label="Blood Glucose" value={patient.blood_glucose} unit="mg/dL" />
            <Stat label="BMI" value={patient.bmi?.toFixed(1)} unit="" />
            <Stat label="BMI Category" value={patient.bmi_category} unit="" />
          </div>
        </div>

        {/* Risk Scores */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
          <h2 className="font-semibold text-gray-700 mb-3">Risk Assessment</h2>
          <RiskRow label="Heart Risk" level={patient.heart_risk_level} score={patient.heart_risk_total_score} />
          <RiskRow label="Diabetic Risk" level={patient.diabetic_risk_level} score={patient.diabetic_risk_total_score} />
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
              ['Chest Discomfort', patient.chest_discomfort],
              ['Breathlessness', patient.breathlessness],
              ['Palpitations', patient.palpitations],
              ['Fatigue / Weakness', patient.fatigue_weakness],
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
              ['Sleep Duration', patient.sleep_duration],
              ['Stress / Anxiety', patient.stress_anxiety],
              ['Physical Inactivity', patient.physical_inactivity],
              ['Diet Quality', patient.diet_quality],
              ['Family History', patient.family_history],
            ].map(([label, val]) => (
              <div key={label} className="flex justify-between py-1.5 border-b border-gray-50 text-sm">
                <span className="text-gray-500">{label}</span>
                <span className="font-medium text-gray-600">{val || '—'}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}