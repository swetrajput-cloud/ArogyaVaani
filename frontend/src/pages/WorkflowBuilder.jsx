import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { initiateCall } from '../api/client'
import { ArrowLeft, Phone } from 'lucide-react'

export default function WorkflowBuilder() {
  const navigate = useNavigate()
  const [patientId, setPatientId] = useState('')
  const [status, setStatus] = useState(null)

  const handleCall = async () => {
    if (!patientId) return alert('Enter a patient ID')
    try {
      const res = await initiateCall(patientId)
      setStatus({ success: true, msg: `Call initiated! SID: ${res.data.call_sid}` })
    } catch (e) {
      setStatus({ success: false, msg: 'Call failed. Check Twilio credentials and ngrok.' })
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white border-b border-gray-200 px-6 py-4 flex items-center gap-4">
        <button onClick={() => navigate('/')} className="text-gray-400 hover:text-gray-700">
          <ArrowLeft size={20} />
        </button>
        <h1 className="font-bold text-gray-800">Workflow Builder — Initiate Call</h1>
      </div>

      <div className="max-w-lg mx-auto px-6 py-12">
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 space-y-4">
          <h2 className="font-semibold text-gray-700">Manually Trigger a Patient Call</h2>
          <p className="text-xs text-gray-400">Enter the patient ID from the dashboard to initiate an outbound call via Twilio.</p>

          <input
            type="number"
            placeholder="Patient ID (e.g. 1)"
            value={patientId}
            onChange={(e) => setPatientId(e.target.value)}
            className="w-full border border-gray-200 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
          />

          <button
            onClick={handleCall}
            className="w-full flex items-center justify-center gap-2 bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700 transition"
          >
            <Phone size={16} /> Initiate Call
          </button>

          {status && (
            <div className={`text-sm p-3 rounded-lg ${status.success ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-600'}`}>
              {status.msg}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}