const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function AdmissionQueue({ admissions, onRefresh }) {
  const pending = admissions.filter(a => a.status === 'pending')

  const handleAction = async (id, action) => {
    try {
      await fetch(`${BASE}/admissions/${id}/${action}`, { method: 'POST' })
      onRefresh()
    } catch (e) {
      console.error(e)
    }
  }

  if (pending.length === 0) return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
      <h2 className="font-semibold text-gray-700 mb-2">🏥 Admission Requests</h2>
      <p className="text-sm text-gray-400">No pending admissions</p>
    </div>
  )

  return (
    <div className="bg-white rounded-xl shadow-sm border border-red-100 p-4">
      <h2 className="font-semibold text-gray-700 mb-3">
        🏥 Admission Requests
        <span className="ml-2 bg-red-100 text-red-700 text-xs px-2 py-0.5 rounded-full">
          {pending.length}
        </span>
      </h2>
      <div className="space-y-3">
        {pending.map(a => (
          <div key={a.id} className="border border-red-50 rounded-lg p-3 bg-red-50">
            <div className="flex justify-between items-start mb-1">
              <span className="font-medium text-sm text-gray-800">{a.patient_name}</span>
              <span className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded-full font-semibold">
                {a.risk_tier}
              </span>
            </div>
            <p className="text-xs text-gray-600 mb-1">{a.condition}</p>
            <p className="text-xs text-gray-500 mb-1">{a.reason || 'High risk detected'}</p>
            <p className="text-xs text-gray-400 mb-2">📞 {a.patient_phone}</p>
            <p className="text-xs text-gray-400 mb-2">
              {new Date(a.requested_at).toLocaleString('en-IN', {
                day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit'
              })}
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => handleAction(a.id, 'admit')}
                className="flex-1 py-1 bg-red-500 text-white text-xs rounded-lg font-semibold hover:bg-red-600 transition"
              >
                🏥 Admit (IPD)
              </button>
              <button
                onClick={() => handleAction(a.id, 'discharge')}
                className="flex-1 py-1 bg-gray-100 text-gray-600 text-xs rounded-lg font-semibold hover:bg-gray-200 transition"
              >
                ✕ Discharge
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}