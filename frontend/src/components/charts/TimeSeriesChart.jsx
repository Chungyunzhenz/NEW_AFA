import { useMemo } from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';
import { formatDate, formatNumber, formatCurrency } from '../../utils/formatters';
import { METRICS, METRIC_LABELS } from '../../utils/constants';

const PRICE_METRICS = new Set([
  METRICS.AVG_PRICE,
  METRICS.MAX_PRICE,
  METRICS.MIN_PRICE,
]);

function CustomTooltip({ active, payload, label, metric }) {
  if (!active || !payload?.length) return null;

  const isPrice = PRICE_METRICS.has(metric);
  const formatted = isPrice
    ? formatCurrency(payload[0].value, 1)
    : formatNumber(payload[0].value);

  return (
    <div className="chart-tooltip">
      <p className="chart-tooltip-label">{formatDate(label)}</p>
      <p className="chart-tooltip-value" style={{ color: payload[0].color }}>
        {METRIC_LABELS[metric] ?? metric}: {formatted}
      </p>
    </div>
  );
}

/**
 * Main time-series line chart.
 *
 * @param {Object}   props
 * @param {Array}    props.data   - Array of { date, value }.
 * @param {string}   props.metric - One of METRICS constants.
 * @param {string}   [props.title]
 * @param {string}   [props.color='#0ea5e9'] - Line stroke colour.
 * @param {number}   [props.height=380]
 */
export default function TimeSeriesChart({
  data = [],
  metric = METRICS.AVG_PRICE,
  title,
  color = '#0ea5e9',
  height = 380,
}) {
  const isPrice = PRICE_METRICS.has(metric);

  const chartData = useMemo(
    () =>
      data
        .map((d) => ({
          ...d,
          date: typeof d.date === 'string' ? d.date : d.date?.toISOString?.(),
        }))
        .sort((a, b) => String(a.date ?? '').localeCompare(String(b.date ?? ''))),
    [data],
  );

  const yLabel = METRIC_LABELS[metric] ?? metric;

  if (!chartData.length) {
    return (
      <div className="flex h-64 items-center justify-center text-gray-400">
        {title ? `${title} - ` : ''}暫無資料
      </div>
    );
  }

  return (
    <div className="w-full">
      {title && (
        <h3 className="mb-2 text-base font-semibold text-gray-700">{title}</h3>
      )}
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={chartData} margin={{ top: 8, right: 24, left: 8, bottom: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />

          <XAxis
            dataKey="date"
            tickFormatter={(v) => formatDate(v, 'MM/dd')}
            tick={{ fontSize: 12, fill: '#6b7280' }}
            tickLine={false}
            axisLine={{ stroke: '#d1d5db' }}
            minTickGap={40}
          />

          <YAxis
            tick={{ fontSize: 12, fill: '#6b7280' }}
            tickFormatter={(v) => (isPrice ? `$${formatNumber(v)}` : formatNumber(v))}
            tickLine={false}
            axisLine={false}
            label={{
              value: yLabel,
              angle: -90,
              position: 'insideLeft',
              offset: -4,
              style: { fontSize: 12, fill: '#9ca3af' },
            }}
          />

          <Tooltip content={<CustomTooltip metric={metric} />} />

          <Legend
            wrapperStyle={{ fontSize: 13 }}
            formatter={() => yLabel}
          />

          <Line
            type="monotone"
            dataKey="value"
            stroke={color}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 5, strokeWidth: 0, fill: color }}
            name={yLabel}
            animationDuration={600}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
