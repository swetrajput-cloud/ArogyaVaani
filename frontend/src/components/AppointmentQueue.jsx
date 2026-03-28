const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function AppointmentQueue({ appointments, onRefresh }) {
  const pending = appointments.filter(a => a.status === 'pending')

  const handleAction = async (id, action) => {
    try {
      await fetch(`${BASE}/appointments/${id}/${action}`, { method: 'POST' })
      onRefresh()
    } catch (e) {
      console.error(e)
    }
  }

  if (pending.length === 0) return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
      <h2 className="font-semibold text-gray-700 mb-2">📅 Appointment Requests</h2>
      <p className="text-sm text-gray-400">No pending appointments</p>
    </div>
  )

  return (
    <div className="bg-white rounded-xl shadow-sm border border-blue-100 p-4">
      <h2 className="font-semibold text-gray-700 mb-3">
        📅 Appointment Requests
        <span className="ml-2 bg-blue-100 text-blue-700 text-xs px-2 py-0.5 rounded-full">
          {pending.length}
        </span>
      </h2>
      <div className="space-y-3">
        {pending.map(a => (
          <div key={a.id} className="border border-gray-100 rounded-lg p-3">
            <div className="flex justify-between items-start mb-1">
              <span className="font-medium text-sm text-gray-800">{a.patient_name}</span>
              <span className="text-xs text-gray-400">
                {new Date(a.requested_at).toLocaleString('en-IN', {
                  day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit'
                })}
              </span>
            </div>
            <p className="text-xs text-gray-500 mb-1">{a.reason || 'Appointment requested'}</p>
            <p className="text-xs text-gray-400 mb-2">📞 {a.patient_phone}</p>
            <div className="flex gap-2">
              <button
                onClick={() => handleAction(a.id, 'confirm')}
                className="flex-1 py-1 bg-green-500 text-white text-xs rounded-lg font-semibold hover:bg-green-600 transition"
              >
                ✅ Confirm
              </button>
              <button
                onClick={() => handleAction(a.id, 'reject')}
                className="flex-1 py-1 bg-red-100 text-red-600 text-xs rounded-lg font-semibold hover:bg-red-200 transition"
              >
                ❌ Reject
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}