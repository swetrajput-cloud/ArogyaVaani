import { useEffect, useState } from "react";
import axios from "axios";

const API = import.meta.env.VITE_API_URL || "https://arogyavaani-production.up.railway.app";

export default function VaccinationPage() {
  const [schedule, setSchedule] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Register baby form
  const [patientId, setPatientId] = useState("");
  const [babyDob, setBabyDob] = useState("");
  const [registerMsg, setRegisterMsg] = useState("");
  const [registering, setRegistering] = useState(false);

  // All reminders panel
  const [reminders, setReminders] = useState([]);
  const [remindersLoading, setRemindersLoading] = useState(false);
  const [activeTab, setActiveTab] = useState("schedule"); // schedule | register | reminders

  useEffect(() => {
    axios.get(`${API}/vaccination/schedule`)
      .then(r => setSchedule(r.data.schedule || []))
      .catch(() => setError("Failed to load vaccination schedule."))
      .finally(() => setLoading(false));
  }, []);

  const loadReminders = () => {
    setRemindersLoading(true);
    axios.get(`${API}/vaccination-reminders/all`)
      .then(r => setReminders(r.data.reminders || []))
      .catch(() => setReminders([]))
      .finally(() => setRemindersLoading(false));
  };

  const handleRegister = async () => {
    if (!patientId || !babyDob) {
      setRegisterMsg("Please enter both Patient ID and Date.");
      return;
    }
    setRegistering(true);
    setRegisterMsg("");
    try {
      const res = await axios.post(`${API}/vaccination-reminders/register`, {
        patient_id: parseInt(patientId),
        baby_dob: babyDob,
      });
      if (res.data.error) {
        setRegisterMsg(`Error: ${res.data.error}`);
      } else {
        setRegisterMsg(`✅ Success! ${res.data.created} reminder calls scheduled for Patient #${patientId} from ${babyDob}.`);
        setPatientId("");
        setBabyDob("");
      }
    } catch (e) {
      setRegisterMsg("Failed to register. Check Patient ID and try again.");
    } finally {
      setRegistering(false);
    }
  };

  const grouped = schedule.reduce((acc, row) => {
    acc[row.age_label] = acc[row.age_label] || [];
    acc[row.age_label].push(row);
    return acc;
  }, {});

  const ageOrder = ["Birth", "6 weeks", "10 weeks", "14 weeks", "9 months", "12 months"];

  const statusColor = (s) => ({
    pending: "bg-yellow-100 text-yellow-700",
    called: "bg-green-100 text-green-700",
    failed: "bg-red-100 text-red-700",
  }[s] || "bg-gray-100 text-gray-600");

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-5xl mx-auto">

        {/* Header */}
        <div className="flex items-center gap-3 mb-6">
          <span className="text-4xl">🍼</span>
          <div>
            <h1 className="text-2xl font-bold text-gray-800">Newborn Vaccination</h1>
            <p className="text-gray-500 text-sm">India National Immunization Program — Schedule & Auto-Reminders</p>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6">
          {[
            { key: "schedule", label: "📅 Schedule" },
            { key: "register", label: "➕ Register Baby" },
            { key: "reminders", label: "🔔 Reminders" },
          ].map(tab => (
            <button
              key={tab.key}
              onClick={() => { setActiveTab(tab.key); if (tab.key === "reminders") loadReminders(); }}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition ${
                activeTab === tab.key
                  ? "bg-blue-600 text-white shadow"
                  : "bg-white text-gray-600 border border-gray-200 hover:bg-gray-50"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* TAB: Schedule */}
        {activeTab === "schedule" && (
          <>
            {loading && <div className="text-center py-20 text-gray-400 text-lg">Loading schedule...</div>}
            {error && <div className="bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded-lg">{error}</div>}
            {!loading && !error && ageOrder.map(age => {
              const vaccines = grouped[age];
              if (!vaccines || vaccines.length === 0) return null;
              return (
                <div key={age} className="mb-6 rounded-xl shadow-sm overflow-hidden border border-gray-200">
                  <div className="bg-blue-600 px-5 py-3 flex items-center gap-2">
                    <span className="text-white font-semibold text-base">📅 {age}</span>
                    <span className="ml-auto bg-blue-500 text-white text-xs px-2 py-1 rounded-full">
                      {vaccines.length} vaccine{vaccines.length > 1 ? "s" : ""}
                    </span>
                  </div>
                  <table className="w-full text-sm">
                    <thead className="bg-blue-50">
                      <tr>
                        <th className="text-left px-5 py-2 text-blue-800 font-semibold">Vaccine</th>
                        <th className="text-left px-5 py-2 text-blue-800 font-semibold">Dose</th>
                        <th className="text-left px-5 py-2 text-blue-800 font-semibold">Route / Site</th>
                        <th className="text-left px-5 py-2 text-blue-800 font-semibold">Remarks</th>
                      </tr>
                    </thead>
                    <tbody>
                      {vaccines.map((v, i) => (
                        <tr key={i} className={i % 2 === 0 ? "bg-white" : "bg-gray-50"}>
                          <td className="px-5 py-3 font-medium text-gray-800">{v.vaccine_name}</td>
                          <td className="px-5 py-3 text-gray-600">{v.dose}</td>
                          <td className="px-5 py-3 text-gray-600">{v.route_site}</td>
                          <td className="px-5 py-3 text-gray-500 italic">{v.remarks}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              );
            })}
            {!loading && !error && (
              <div className="mt-4 bg-green-50 border border-green-200 rounded-xl px-5 py-4 flex items-center gap-3">
                <span className="text-2xl">✅</span>
                <p className="text-green-700 text-sm font-medium">
                  {schedule.length} vaccines across {Object.keys(grouped).length} age groups loaded.
                </p>
              </div>
            )}
          </>
        )}

        {/* TAB: Register Baby */}
        {activeTab === "register" && (
          <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm max-w-lg">
            <h2 className="text-lg font-semibold text-gray-800 mb-1">Register Baby & Auto-Schedule Calls</h2>
            <p className="text-sm text-gray-500 mb-5">
              Enter the patient ID and the baby's date of birth (or vaccination start date).
              All future reminder calls will be auto-scheduled 7 days before each dose is due.
            </p>

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">Patient ID</label>
              <input
                type="number"
                placeholder="e.g. 42"
                value={patientId}
                onChange={e => setPatientId(e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
              />
            </div>

            <div className="mb-5">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Baby Date of Birth / Vaccination Start Date
              </label>
              <input
                type="date"
                value={babyDob}
                onChange={e => setBabyDob(e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
              />
              <p className="text-xs text-gray-400 mt-1">
                All dose call dates are calculated from this date using India NIS schedule.
              </p>
            </div>

            <button
              onClick={handleRegister}
              disabled={registering}
              className="w-full bg-blue-600 text-white py-2 rounded-lg text-sm font-semibold hover:bg-blue-700 transition disabled:opacity-50"
            >
              {registering ? "Scheduling..." : "📅 Auto-Schedule All Reminder Calls"}
            </button>

            {registerMsg && (
              <div className={`mt-4 px-4 py-3 rounded-lg text-sm ${
                registerMsg.startsWith("✅") ? "bg-green-50 text-green-700 border border-green-200" : "bg-red-50 text-red-600 border border-red-200"
              }`}>
                {registerMsg}
              </div>
            )}
          </div>
        )}

        {/* TAB: Reminders */}
        {activeTab === "reminders" && (
          <div>
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-semibold text-gray-800">All Scheduled Reminders</h2>
              <button
                onClick={loadReminders}
                className="text-sm text-blue-600 hover:underline"
              >
                🔄 Refresh
              </button>
            </div>
            {remindersLoading && <div className="text-center py-10 text-gray-400">Loading reminders...</div>}
            {!remindersLoading && reminders.length === 0 && (
              <div className="text-center py-10 text-gray-400">No reminders scheduled yet. Register a baby first.</div>
            )}
            {!remindersLoading && reminders.length > 0 && (
              <div className="rounded-xl border border-gray-200 overflow-hidden shadow-sm">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 border-b border-gray-200">
                    <tr>
                      <th className="text-left px-4 py-3 text-gray-600 font-semibold">Patient</th>
                      <th className="text-left px-4 py-3 text-gray-600 font-semibold">Vaccine</th>
                      <th className="text-left px-4 py-3 text-gray-600 font-semibold">Age</th>
                      <th className="text-left px-4 py-3 text-gray-600 font-semibold">Due Date</th>
                      <th className="text-left px-4 py-3 text-gray-600 font-semibold">Call Date</th>
                      <th className="text-left px-4 py-3 text-gray-600 font-semibold">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {reminders.map((r, i) => (
                      <tr key={r.id} className={i % 2 === 0 ? "bg-white" : "bg-gray-50"}>
                        <td className="px-4 py-3 font-medium text-gray-800">{r.patient_name}</td>
                        <td className="px-4 py-3 text-gray-700">{r.vaccine_name}</td>
                        <td className="px-4 py-3 text-gray-500">{r.age_label}</td>
                        <td className="px-4 py-3 text-gray-600">{r.due_date}</td>
                        <td className="px-4 py-3 text-gray-600">{r.reminder_date}</td>
                        <td className="px-4 py-3">
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${statusColor(r.call_status)}`}>
                            {r.call_status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

      </div>
    </div>
  );
}