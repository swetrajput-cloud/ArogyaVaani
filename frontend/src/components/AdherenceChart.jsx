import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts'

const COLORS = { RED: '#ef4444', AMBER: '#f59e0b', GREEN: '#22c55e' }

export default function AdherenceChart({ stats }) {
  if (!stats) return null

  const data = [
    { name: 'High Risk', value: stats.red, color: COLORS.RED },
    { name: 'Moderate', value: stats.amber, color: COLORS.AMBER },
    { name: 'Low Risk', value: stats.green, color: COLORS.GREEN },
  ]

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
      <h2 className="font-semibold text-gray-700 mb-3">Risk Distribution</h2>
      <ResponsiveContainer width="100%" height={200}>
        <PieChart>
          <Pie data={data} cx="50%" cy="50%" innerRadius={55} outerRadius={80} dataKey="value">
            {data.map((entry, i) => (
              <Cell key={i} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}