import type { Metrics } from '../../packages/api-client/src';
import { money } from '../../packages/api-client/src';
import { Empty } from './ui';

export function SalesChart({ metrics }: { metrics: Metrics }) {
  const days = metrics.daily_sales.slice(-14); const max = Math.max(1, ...days.map(day => day.gross_minor));
  return <>{days.length ? <><div className="report-chart" role="img" aria-label="Simulated daily gross sales for the last 14 available days. Exact values are listed below.">{days.map(day => <div className="report-bar" key={day.date}><i style={{ height: `${Math.max(2, day.gross_minor / max * 85)}%` }} /><span>{day.date.slice(5)}</span></div>)}</div><ul className="sales-values">{days.map(day => <li key={day.date}>{day.date} · {day.orders} orders · {money(day.gross_minor, metrics.currency)}</li>)}</ul></> : <Empty>No simulated sales recorded yet. Reports update after a completed payment.</Empty>}</>;
}
