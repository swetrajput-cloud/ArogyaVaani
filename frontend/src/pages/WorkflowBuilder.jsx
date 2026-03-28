import { useNavigate } from 'react-router-dom'

export default function WorkflowBuilder() {
  const navigate = useNavigate()
  const modules = [
    { name: 'Pre-Arrival Triage', icon: '🏥', desc: 'OPD intake, pain scale, pre-fill', color: 'blue' },
    { name: 'Post-Discharge', icon: '🏠', desc: '24hr/48hr danger sign surveillance', color: 'green' },
    { name: 'Chronic Coach', icon: '💊', desc: 'Weekly diabetes/hypertension adherence', color: 'purple' },
    { name: 'Caregiver Proxy', icon: '👨‍👩‍👦', desc: 'Family-mediated call routing', color: 'orange' },
  ]
  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white shadow-sm border-b px-6 py-4">
        <div className="max-w-4xl mx-auto flex items-center gap-4">
          <button onClick={() => navigate('/')} className="text-blue-600 hover:underline text-sm">← Back</button>
          <h1 className="text-xl font-bold text-gray-800">⚙️ Workflow Builder</h1>
        </div>
      </div>
      <div className="max-w-4xl mx-auto px-6 py-6">
        <p className="text-gray-500 mb-6">Select a call module to view its question flow.</p>
        <div className="grid grid-cols-2 gap-4">
          {modules.map((m, i) => (
            <div key={i} className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 hover:shadow-md cursor-pointer transition-shadow">
              <div className="text-3xl mb-2">{m.icon}</div>
              <h3 className="font-semibold text-gray-800">{m.name}</h3>
              <p className="text-sm text-gray-500 mt-1">{m.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}