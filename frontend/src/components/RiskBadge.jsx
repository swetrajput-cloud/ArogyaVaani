export default function RiskBadge({ tier }) {
  const styles = {
    RED:   'bg-red-100 text-red-700 border border-red-300',
    AMBER: 'bg-yellow-100 text-yellow-700 border border-yellow-300',
    GREEN: 'bg-green-100 text-green-700 border border-green-300',
  }
  const labels = { RED: '🔴 HIGH', AMBER: '🟡 MODERATE', GREEN: '🟢 LOW' }
  return (
    <span className={`px-2 py-1 rounded-full text-xs font-semibold ${styles[tier] || styles.GREEN}`}>
      {labels[tier] || tier}
    </span>
  )
}