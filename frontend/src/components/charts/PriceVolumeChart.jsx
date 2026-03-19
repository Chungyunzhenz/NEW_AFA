import { useMemo } from 'react';
import {
  ResponsiveContainer,
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';
import { formatDate, formatNumber, formatCurrency } from '../../utils/formatters';

const PRICE_COLOR = '#0ea5e9';
const VOLUME_COLOR = '#a78bfa';

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;

  return (
    <div className="chart-tooltip">
      <p className="chart-tooltip-label">{formatDate(label)}</p>
      {payload.map((entry) => (
        <p
          key={entry.dataKey}
          className="chart-tooltip-value"
          style={{ color: entry.color }}
        >
          {entry.name}:{' '}
          {entry.dataKey === 'price_avg'
            ? formatCurrency(entry.value, 1)
            : formatNumber(entry.value)}
        </p>
      ))}
    </div>
  );
}

/**
 * Dual-axis composed chart for price (line) + volume (bar).
 *
 * @param {Object}  props
 * @param {Array}   props.data   - Array of { date, price_avg, volume }.
 * @param {string}  [props.title]
 * @param {number}  [props.height=400]
 */
export default function PriceVolumeChart({
  data = [],
  title,
  height = 400,
}) {
  const chartData = useMemo(
    () =>
      data.map((d) => ({
        ...d,
        date: typeof d.date === 'string' ? d.date : d.date?.toISOString?.(),
      })),
    [data],
  );

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
        <ComposedChart data={chartData} margin={{ top: 8, right: 24, left: 8, bottom: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />

          <XAxis
            dataKey="date"
            tickFormatter={(v) => formatDate(v, 'MM/dd')}
            tick={{ fontSize: 12, fill: '#6b7280' }}
            tickLine={false}
            axisLine={{ stroke: '#d1d5db' }}
            minTickGap={40}
          />

          {/* Left axis: price */}
          <YAxis
            yAxisId="price"
            orientation="left"
            tick={{ fontSize: 12, fill: PRICE_COLOR }}
            tickFormatter={(v) => `$${formatNumber(v)}`}
            tickLine={false}
            axisLine={false}
            label={{
              value: '價格 (NT$)',
              angle: -90,
              position: 'insideLeft',
              offset: -4,
              style: { fontSize: 12, fill: PRICE_COLOR },
            }}
          />

          {/* Right axis: volume */}
          <YAxis
            yAxisId="volume"
            orientation="right"
            tick={{ fontSize: 12, fill: VOLUME_COLOR }}
            tickFormatter={(v) => formatNumber(v)}
            tickLine={false}
            axisLine={false}
            label={{
              value: '交易量',
              angle: 90,
              position: 'insideRight',
              offset: 4,
              style: { fontSize: 12, fill: VOLUME_COLOR },
            }}
          />

          <Tooltip content={<CustomTooltip />} />

          <Legend wrapperStyle={{ fontSize: 13 }} />

          <Bar
            yAxisId="volume"
            dataKey="volume"
            name="交易量"
            fill={VOLUME_COLOR}
            fillOpacity={0.45}
            radius={[3, 3, 0, 0]}
            maxBarSize={24}
            animationDuration={600}
          />

          <Line
            yAxisId="price"
            type="monotone"
            dataKey="price_avg"
            name="平均價格"
            stroke={PRICE_COLOR}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4, strokeWidth: 0, fill: PRICE_COLOR }}
            animationDuration={600}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
