const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function ScheduledCallsPanel({ patients, onCallNow }) {
  const FOLLOWUP_HOURS = 2

  const redPatients = patients.filter(p => p.current_risk_tier === 'RED')

  const getNextCallTime = (lastCalledAt) => {
    if (!lastCalledAt) return null
    const last = new Date(lastCalledAt)
    return new Date(last.getTime() + FOLLOWUP_HOURS * 60 * 60 * 1000)
  }

  const getTimeUntil = (nextCall) => {
    if (!nextCall) return null
    const diff = nextCall - new Date()
    if (diff <= 0) return 'Due now'
    const h = Math.floor(diff / 3600000)
    const m = Math.floor((diff % 3600000) / 60000)
    return h > 0 ? `in ${h}h ${m}m` : `in ${m}m`
  }

  if (redPatients.length === 0) return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
      <h2 className="font-semibold text-gray-700 mb-2">🔁 Auto Follow-up Queue</h2>
      <p className="text-sm text-gray-400">No RED patients scheduled</p>
    </div>
  )

  return (
    <div className="bg-white rounded-xl shadow-sm border border-orange-100 p-4">
      <h2 className="font-semibold text-gray-700 mb-3">
        🔁 Auto Follow-up Queue
        <span className="ml-2 bg-orange-100 text-orange-700 text-xs px-2 py-0.5 rounded-full">
          {redPatients.length} RED
        </span>
      </h2>
      <div className="space-y-3">
        {redPatients.map(p => {
          const nextCall = getNextCallTime(p.last_called_at)
          const timeUntil = getTimeUntil(nextCall)
          const isDue = nextCall && nextCall <= new Date()

          return (
            <div key={p.id} className={`border rounded-lg p-3 ${isDue ? 'bg-red-50 border-red-200' : 'bg-orange-50 border-orange-100'}`}>
              <div className="flex justify-between items-start mb-1">
                <span className="font-medium text-sm text-gray-800">{p.name}</span>
                <span className={`text-xs px-2 py-0.5 rounded-full font-semibold ${isDue ? 'bg-red-100 text-red-700' : 'bg-orange-100 text-orange-700'}`}>
                  {isDue ? '🔴 Due now' : `⏰ ${timeUntil}`}
                </span>
              </div>
              <p className="text-xs text-gray-500 mb-1">{p.condition}</p>
              {p.last_called_at ? (
                <p className="text-xs text-gray-400 mb-2">
                  Last called: {new Date(p.last_called_at).toLocaleString('en-IN', {
                    day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit'
                  })}
                </p>
              ) : (
                <p className="text-xs text-gray-400 mb-2">Never called</p>
              )}
              {nextCall && (
                <p className="text-xs text-gray-400 mb-2">
                  Next auto-call: {nextCall.toLocaleString('en-IN', {
                    day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit'
                  })}
                </p>
              )}
              <button
                onClick={() => onCallNow(p.id)}
                className="w-full py-1 bg-orange-500 text-white text-xs rounded-lg font-semibold hover:bg-orange-600 transition"
              >
                📞 Call Now
              </button>
            </div>
          )
        })}
      </div>
    </div>
  )
}