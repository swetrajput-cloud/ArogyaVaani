import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Calendar, Clock, Users, Filter, Trash2, Phone, ChevronLeft, Search } from 'lucide-react'

const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function SchedulerPage() {
  const navigate = useNavigate()

  // ── State ──────────────────────────────────────────
  const [tab, setTab] = useState('single')       // 'single' | 'bulk' | 'list'

  // Single scheduling
  const [patientId, setPatientId]   = useState('')
  const [scheduledAt, setScheduledAt] = useState('')
  const [customNote, setCustomNote] = useState('')
  const [patientSearch, setPatientSearch] = useState('')
  const [patients, setPatients]     = useState([])
  const [selectedPatient, setSelectedPatient] = useState(null)

  // Bulk scheduling
  const [bulkCondition, setBulkCondition] = useState('')
  const [bulkRisk, setBulkRisk]           = useState('')
  const [bulkCamp, setBulkCamp]           = useState('')
  const [bulkDate, setBulkDate]           = useState('')
  const [bulkNote, setBulkNote]           = useState('')
  const [preview, setPreview]             = useState(null)
  const [previewing, setPreviewing]       = useState(false)

  // Scheduled list
  const [scheduled, setScheduled]   = useState([])
  const [listFilter, setListFilter] = useState('')

  // UI
  const [loading, setLoading]   = useState(false)
  const [message, setMessage]   = useState(null)   // {type: 'success'|'error', text}

  // ── Load patients for single tab ───────────────────
  useEffect(() => {
    fetch(`${BASE}/patients?limit=120`)
      .then(r => r.json())
      .then(d => setPatients(d.patients || []))
      .catch(console.error)
  }, [])

  // ── Load scheduled list ────────────────────────────
  useEffect(() => {
    if (tab === 'list') fetchScheduled()
  }, [tab, listFilter])

  const fetchScheduled = async () => {
    try {
      const url = listFilter
        ? `${BASE}/scheduler/list?status=${listFilter}`
        : `${BASE}/scheduler/list`
      const res  = await fetch(url)
      const data = await res.json()
      setScheduled(data)
    } catch (e) {
      console.error(e)
    }
  }

  // ── Flash message ──────────────────────────────────
  const flash = (type, text) => {
    setMessage({ type, text })
    setTimeout(() => setMessage(null), 4000)
  }

  // ── Single schedule ────────────────────────────────
  const handleSingle = async () => {
    if (!selectedPatient || !scheduledAt) {
      flash('error', 'Please select a patient and date/time')
      return
    }
    setLoading(true)
    try {
      const res = await fetch(`${BASE}/scheduler/single`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          patient_id:   selectedPatient.id,
          scheduled_at: new Date(scheduledAt).toISOString(),
          custom_note:  customNote || null,
        }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail)
      flash('success', `✅ Call scheduled for ${data.patient} at ${new Date(data.scheduled_at).toLocaleString()}`)
      setSelectedPatient(null)
      setPatientSearch('')
      setScheduledAt('')
      setCustomNote('')
    } catch (e) {
      flash('error', `❌ ${e.message}`)
    } finally {
      setLoading(false)
    }
  }

  // ── Bulk preview ───────────────────────────────────
  const handlePreview = async () => {
    setPreviewing(true)
    try {
      const params = new URLSearchParams()
      if (bulkCondition) params.append('condition', bulkCondition)
      if (bulkRisk)      params.append('risk_tier', bulkRisk)
      if (bulkCamp)      params.append('camp_name', bulkCamp)
      const res  = await fetch(`${BASE}/scheduler/preview?${params}`)
      const data = await res.json()
      setPreview(data)
    } catch (e) {
      flash('error', 'Preview failed')
    } finally {
      setPreviewing(false)
    }
  }

  // ── Bulk schedule ──────────────────────────────────
  const handleBulk = async () => {
    if (!bulkDate) { flash('error', 'Please select a date and time'); return }
    if (!preview || preview.total === 0) { flash('error', 'No patients match — preview first'); return }
    setLoading(true)
    try {
      const res = await fetch(`${BASE}/scheduler/bulk`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          scheduled_at: new Date(bulkDate).toISOString(),
          custom_note:  bulkNote || null,
          condition:    bulkCondition || null,
          risk_tier:    bulkRisk     || null,
          camp_name:    bulkCamp     || null,
        }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail)
      flash('success', `✅ Scheduled ${data.total_patients} patients successfully`)
      setPreview(null)
      setBulkCondition(''); setBulkRisk(''); setBulkCamp('')
      setBulkDate(''); setBulkNote('')
    } catch (e) {
      flash('error', `❌ ${e.message}`)
    } finally {
      setLoading(false)
    }
  }

  // ── Cancel scheduled call ──────────────────────────
  const handleCancel = async (id) => {
    if (!confirm('Cancel this scheduled call?')) return
    try {
      const res = await fetch(`${BASE}/scheduler/${id}`, { method: 'DELETE' })
      if (!res.ok) { const d = await res.json(); throw new Error(d.detail) }
      flash('success', 'Cancelled successfully')
      fetchScheduled()
    } catch (e) {
      flash('error', `❌ ${e.message}`)
    }
  }

  // ── Filtered patient search ────────────────────────
  const filteredPatients = patients.filter(p =>
    p.name.toLowerCase().includes(patientSearch.toLowerCase()) ||
    String(p.id).includes(patientSearch)
  )

  // ── Status badge ───────────────────────────────────
  const statusBadge = (s) => {
    const map = {
      pending:   'bg-yellow-100 text-yellow-700',
      called:    'bg-green-100 text-green-700',
      cancelled: 'bg-gray-100 text-gray-500',
      failed:    'bg-red-100 text-red-700',
    }
    return <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${map[s] || 'bg-gray-100'}`}>{s}</span>
  }

  const riskColor = (r) => ({
    RED: 'text-red-600 bg-red-50', AMBER: 'text-yellow-600 bg-yellow-50', GREEN: 'text-green-600 bg-green-50'
  })[r] || 'text-gray-600 bg-gray-50'

  // ── Render ─────────────────────────────────────────
  return (
    <div className="min-h-screen bg-gray-50">

      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button onClick={() => navigate('/')}
            className="text-gray-400 hover:text-gray-600 transition">
            <ChevronLeft size={20} />
          </button>
          <div>
            <h1 className="text-xl font-bold text-gray-800">📅 Call Scheduler</h1>
            <p className="text-xs text-gray-400">Schedule follow-up calls for individual patients or groups</p>
          </div>
        </div>
        <button onClick={() => { setTab('list'); fetchScheduled() }}
          className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-700 transition">
          <Clock size={14} /> View Scheduled
        </button>
      </div>

      {/* Flash message */}
      {message && (
        <div className={`mx-6 mt-4 px-4 py-3 rounded-lg text-sm font-medium ${
          message.type === 'success' ? 'bg-green-50 text-green-700 border border-green-200' : 'bg-red-50 text-red-700 border border-red-200'
        }`}>
          {message.text}
        </div>
      )}

      <div className="max-w-4xl mx-auto px-6 py-6">

        {/* Tabs */}
        <div className="flex gap-2 mb-6">
          {[
            { key: 'single', label: '👤 Single Patient', icon: null },
            { key: 'bulk',   label: '👥 Bulk by Filter', icon: null },
            { key: 'list',   label: '📋 Scheduled List', icon: null },
          ].map(t => (
            <button key={t.key} onClick={() => setTab(t.key)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition ${
                tab === t.key
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'bg-white text-gray-500 border border-gray-200 hover:bg-gray-50'
              }`}>
              {t.label}
            </button>
          ))}
        </div>

        {/* ── SINGLE TAB ── */}
        {tab === 'single' && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 space-y-5">
            <h2 className="text-base font-semibold text-gray-700 flex items-center gap-2">
              <Users size={16} /> Schedule a call for one patient
            </h2>

            {/* Patient search */}
            <div>
              <label className="text-xs font-medium text-gray-500 mb-1 block">Search Patient</label>
              <div className="relative">
                <Search size={14} className="absolute left-3 top-3 text-gray-400" />
                <input
                  value={patientSearch}
                  onChange={e => { setPatientSearch(e.target.value); setSelectedPatient(null) }}
                  placeholder="Type name or patient ID..."
                  className="w-full pl-8 pr-4 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              {/* Dropdown results */}
              {patientSearch && !selectedPatient && (
                <div className="border border-gray-200 rounded-lg mt-1 max-h-48 overflow-y-auto shadow-sm">
                  {filteredPatients.slice(0, 8).map(p => (
                    <div key={p.id}
                      onClick={() => { setSelectedPatient(p); setPatientSearch(p.name) }}
                      className="flex items-center justify-between px-4 py-2 hover:bg-blue-50 cursor-pointer text-sm border-b border-gray-50 last:border-0">
                      <div>
                        <span className="font-medium text-gray-800">{p.name}</span>
                        <span className="text-gray-400 text-xs ml-2">#{p.id}</span>
                        <p className="text-xs text-gray-400">{p.condition}</p>
                      </div>
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${riskColor(p.current_risk_tier)}`}>
                        {p.current_risk_tier}
                      </span>
                    </div>
                  ))}
                  {filteredPatients.length === 0 && (
                    <p className="text-xs text-gray-400 px-4 py-3">No patients found</p>
                  )}
                </div>
              )}

              {/* Selected patient chip */}
              {selectedPatient && (
                <div className="mt-2 flex items-center gap-2 bg-blue-50 border border-blue-200 rounded-lg px-3 py-2">
                  <div className="flex-1">
                    <p className="text-sm font-medium text-blue-800">{selectedPatient.name}</p>
                    <p className="text-xs text-blue-500">{selectedPatient.condition} · {selectedPatient.phone}</p>
                  </div>
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${riskColor(selectedPatient.current_risk_tier)}`}>
                    {selectedPatient.current_risk_tier}
                  </span>
                  <button onClick={() => { setSelectedPatient(null); setPatientSearch('') }}
                    className="text-blue-400 hover:text-blue-600 text-xs">✕</button>
                </div>
              )}
            </div>

            {/* Date/time */}
            <div>
              <label className="text-xs font-medium text-gray-500 mb-1 block">Date & Time</label>
              <input
                type="datetime-local"
                value={scheduledAt}
                onChange={e => setScheduledAt(e.target.value)}
                className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {/* Custom note */}
            <div>
              <label className="text-xs font-medium text-gray-500 mb-1 block">
                Custom Note for AI <span className="text-gray-400 font-normal">(optional — AI will mention this naturally in the call)</span>
              </label>
              <textarea
                value={customNote}
                onChange={e => setCustomNote(e.target.value)}
                rows={3}
                placeholder="e.g. Remind patient that the diabetes camp is next Monday at Civil Hospital. Please bring medicine records."
                className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
              />
            </div>

            <button onClick={handleSingle} disabled={loading}
              className="w-full bg-blue-600 text-white py-2.5 rounded-lg text-sm font-medium hover:bg-blue-700 transition disabled:opacity-50 flex items-center justify-center gap-2">
              <Phone size={14} />
              {loading ? 'Scheduling...' : 'Schedule Call'}
            </button>
          </div>
        )}

        {/* ── BULK TAB ── */}
        {tab === 'bulk' && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 space-y-5">
            <h2 className="text-base font-semibold text-gray-700 flex items-center gap-2">
              <Filter size={16} /> Bulk schedule by filters
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Condition */}
              <div>
                <label className="text-xs font-medium text-gray-500 mb-1 block">Disease / Condition</label>
                <select value={bulkCondition} onChange={e => { setBulkCondition(e.target.value); setPreview(null) }}
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
                  <option value="">All conditions</option>
                  <option value="Diabetes">Diabetes</option>
                  <option value="Heart Disease">Heart Disease</option>
                  <option value="Hypertension">Hypertension</option>
                  <option value="General Monitoring">General Monitoring</option>
                </select>
              </div>

              {/* Risk tier */}
              <div>
                <label className="text-xs font-medium text-gray-500 mb-1 block">Risk Tier</label>
                <select value={bulkRisk} onChange={e => { setBulkRisk(e.target.value); setPreview(null) }}
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
                  <option value="">All tiers</option>
                  <option value="RED">🔴 RED (High Risk)</option>
                  <option value="AMBER">🟡 AMBER (Moderate)</option>
                  <option value="GREEN">🟢 GREEN (Low Risk)</option>
                </select>
              </div>

              {/* Camp name */}
              <div>
                <label className="text-xs font-medium text-gray-500 mb-1 block">Health Camp Name</label>
                <input
                  value={bulkCamp}
                  onChange={e => { setBulkCamp(e.target.value); setPreview(null) }}
                  placeholder="e.g. Old Age Camp"
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            {/* Preview button */}
            <button onClick={handlePreview} disabled={previewing}
              className="flex items-center gap-2 bg-gray-100 text-gray-700 px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-200 transition disabled:opacity-50">
              <Search size={14} />
              {previewing ? 'Loading...' : 'Preview Matching Patients'}
            </button>

            {/* Preview results */}
            {preview && (
              <div className="border border-gray-200 rounded-lg overflow-hidden">
                <div className="bg-gray-50 px-4 py-2 flex items-center justify-between">
                  <span className="text-xs font-medium text-gray-600">
                    {preview.total} patient{preview.total !== 1 ? 's' : ''} match your filters
                  </span>
                  {preview.total === 0 && (
                    <span className="text-xs text-red-500">No patients found — adjust filters</span>
                  )}
                </div>
                {preview.patients.slice(0, 6).map(p => (
                  <div key={p.id} className="flex items-center justify-between px-4 py-2 border-t border-gray-100 text-sm">
                    <div>
                      <span className="font-medium text-gray-800">{p.name}</span>
                      <span className="text-gray-400 text-xs ml-2">#{p.id} · {p.condition}</span>
                    </div>
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${riskColor(p.risk_tier)}`}>
                      {p.risk_tier}
                    </span>
                  </div>
                ))}
                {preview.total > 6 && (
                  <div className="px-4 py-2 text-xs text-gray-400 border-t border-gray-100">
                    +{preview.total - 6} more patients
                  </div>
                )}
              </div>
            )}

            {/* Date/time */}
            <div>
              <label className="text-xs font-medium text-gray-500 mb-1 block">Date & Time for All</label>
              <input
                type="datetime-local"
                value={bulkDate}
                onChange={e => setBulkDate(e.target.value)}
                className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {/* Custom note */}
            <div>
              <label className="text-xs font-medium text-gray-500 mb-1 block">
                Custom Note for AI <span className="text-gray-400 font-normal">(optional)</span>
              </label>
              <textarea
                value={bulkNote}
                onChange={e => setBulkNote(e.target.value)}
                rows={3}
                placeholder="e.g. The diabetes camp is next Monday at Civil Hospital. All patients should bring their medicine records."
                className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
              />
            </div>

            <button onClick={handleBulk} disabled={loading || !preview || preview.total === 0}
              className="w-full bg-blue-600 text-white py-2.5 rounded-lg text-sm font-medium hover:bg-blue-700 transition disabled:opacity-50 flex items-center justify-center gap-2">
              <Phone size={14} />
              {loading ? 'Scheduling...' : `Schedule Calls for ${preview?.total || 0} Patients`}
            </button>
          </div>
        )}

        {/* ── LIST TAB ── */}
        {tab === 'list' && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
            {/* Filter bar */}
            <div className="px-4 py-3 border-b border-gray-100 flex items-center gap-2">
              {['', 'pending', 'called', 'cancelled', 'failed'].map(s => (
                <button key={s} onClick={() => setListFilter(s)}
                  className={`px-3 py-1 rounded-full text-xs font-medium transition ${
                    listFilter === s
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
                  }`}>
                  {s === '' ? 'All' : s.charAt(0).toUpperCase() + s.slice(1)}
                </button>
              ))}
              <button onClick={fetchScheduled}
                className="ml-auto text-xs text-blue-600 hover:text-blue-800 transition">
                ↻ Refresh
              </button>
            </div>

            {scheduled.length === 0 ? (
              <div className="text-center py-12 text-gray-400 text-sm">
                No scheduled calls found
              </div>
            ) : (
              <div className="divide-y divide-gray-50">
                {scheduled.map(s => (
                  <div key={s.id} className="px-4 py-3 flex items-center justify-between hover:bg-gray-50 transition">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-gray-800">{s.patient_name}</span>
                        <span className="text-xs text-gray-400">#{s.patient_id}</span>
                        {statusBadge(s.status)}
                      </div>
                      <div className="flex items-center gap-3 mt-0.5">
                        <span className="text-xs text-gray-400 flex items-center gap-1">
                          <Clock size={10} />
                          {new Date(s.scheduled_at).toLocaleString()}
                        </span>
                        {s.custom_note && (
                          <span className="text-xs text-blue-500 truncate max-w-xs" title={s.custom_note}>
                            📝 {s.custom_note.slice(0, 50)}{s.custom_note.length > 50 ? '...' : ''}
                          </span>
                        )}
                      </div>
                      {s.fired_at && (
                        <p className="text-xs text-green-600 mt-0.5">
                          Called at {new Date(s.fired_at).toLocaleString()}
                        </p>
                      )}
                    </div>
                    {s.status === 'pending' && (
                      <button onClick={() => handleCancel(s.id)}
                        className="ml-3 text-gray-400 hover:text-red-500 transition p-1 rounded-lg hover:bg-red-50"
                        title="Cancel">
                        <Trash2 size={14} />
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}