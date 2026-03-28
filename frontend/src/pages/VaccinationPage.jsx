import { useEffect, useState } from "react";
import axios from "axios";

const API = import.meta.env.VITE_API_URL || "https://arogyavaani-production.up.railway.app";

export default function VaccinationPage() {
  const [schedule, setSchedule] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    axios.get(`${API}/vaccination/schedule`)
      .then(r => setSchedule(r.data.schedule || []))
      .catch(() => setError("Failed to load vaccination schedule."))
      .finally(() => setLoading(false));
  }, []);

  const grouped = schedule.reduce((acc, row) => {
    acc[row.age_label] = acc[row.age_label] || [];
    acc[row.age_label].push(row);
    return acc;
  }, {});

  const ageOrder = ["Birth", "6 weeks", "10 weeks", "14 weeks", "9 months", "12 months"];

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-5xl mx-auto">

        {/* Header */}
        <div className="flex items-center gap-3 mb-8">
          <span className="text-4xl">🍼</span>
          <div>
            <h1 className="text-2xl font-bold text-gray-800">Newborn Vaccination Schedule</h1>
            <p className="text-gray-500 text-sm">India National Immunization Program — 0 to 12 Months</p>
          </div>
        </div>

        {loading && (
          <div className="text-center py-20 text-gray-400 text-lg">Loading schedule...</div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded-lg">
            {error}
          </div>
        )}

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

        {/* Summary bar */}
        {!loading && !error && (
          <div className="mt-6 bg-green-50 border border-green-200 rounded-xl px-5 py-4 flex items-center gap-3">
            <span className="text-2xl">✅</span>
            <p className="text-green-700 text-sm font-medium">
              Total {schedule.length} vaccines loaded from database across {Object.keys(grouped).length} age groups.
            </p>
          </div>
        )}

      </div>
    </div>
  );
}