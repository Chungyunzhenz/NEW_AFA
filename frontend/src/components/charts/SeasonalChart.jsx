import { useMemo } from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
  ReferenceLine,
} from 'recharts';
import { formatNumber } from '../../utils/formatters';

const MONTH_LABELS = [
  '1月', '2月', '3月', '4月', '5月', '6月',
  '7月', '8月', '9月', '10月', '11月', '12月',
];

const DEFAULT_COLOR = '#60a5fa';
const PEAK_COLOR = '#f59e0b';

function CustomTooltip({ active, payload, label, peakMonths }) {
  if (!active || !payload?.length) return null;
  const isPeak = peakMonths?.includes(payload[0]?.payload?.month);

  return (
    <div className="chart-tooltip">
      <p className="chart-tooltip-label">{label}</p>
      <p className="chart-tooltip-value" style={{ color: isPeak ? PEAK_COLOR : DEFAULT_COLOR }}>
        月均值: {formatNumber(payload[0].value, 1)}
      </p>
      {isPeak && (
        <p className="mt-0.5 text-xs text-amber-600 font-medium">盛產季</p>
      )}
    </div>
  );
}

/**
 * Seasonal pattern bar chart showing monthly averages.
 *
 * @param {Object}   props
 * @param {Array}    props.data        - Raw time series with { date, value }.
 *                                       Grouped internally by month.
 * @param {number[]} [props.peakMonths] - 1-indexed months considered peak season (e.g. [6,7,8]).
 * @param {string}   [props.title]
 * @param {number}   [props.height=340]
 */
export default function SeasonalChart({
  data = [],
  peakMonths = [],
  title,
  height = 340,
}) {
  const chartData = useMemo(() => {
    const buckets = Array.from({ length: 12 }, () => []);

    data.forEach((d) => {
      const dateObj = typeof d.date === 'string' ? new Date(d.date) : d.date;
      const monthIdx = dateObj.getMonth();
      if (d.value != null) buckets[monthIdx].push(d.value);
    });

    return buckets.map((values, idx) => {
      const avg =
        values.length > 0
          ? values.reduce((s, v) => s + v, 0) / values.length
          : 0;
      return {
        month: idx + 1,
        label: MONTH_LABELS[idx],
        average: Math.round(avg * 100) / 100,
      };
    });
  }, [data]);

  const peakSet = useMemo(() => new Set(peakMonths), [peakMonths]);

  const overallAvg = useMemo(() => {
    const nonZero = chartData.filter((d) => d.average > 0);
    if (!nonZero.length) return 0;
    return nonZero.reduce((s, d) => s + d.average, 0) / nonZero.length;
  }, [chartData]);

  if (!data.length) {
    return (
      <div className="flex h-64 items-center justify-center text-gray-400">
        {title ? `${title} - ` : ''}暫無季節性資料
      </div>
    );
  }

  return (
    <div className="w-full">
      {title && (
        <h3 className="mb-2 text-base font-semibold text-gray-700">{title}</h3>
      )}

      {peakMonths.length > 0 && (
        <div className="mb-2 flex items-center gap-4 text-xs text-gray-500">
          <span className="flex items-center gap-1">
            <span
              className="inline-block h-3 w-3 rounded-sm"
              style={{ backgroundColor: PEAK_COLOR }}
            />
            盛產季
          </span>
          <span className="flex items-center gap-1">
            <span
              className="inline-block h-3 w-3 rounded-sm"
              style={{ backgroundColor: DEFAULT_COLOR }}
            />
            一般月份
          </span>
        </div>
      )}

      <ResponsiveContainer width="100%" height={height}>
        <BarChart data={chartData} margin={{ top: 8, right: 16, left: 8, bottom: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" vertical={false} />

          <XAxis
            dataKey="label"
            tick={{ fontSize: 12, fill: '#6b7280' }}
            tickLine={false}
            axisLine={{ stroke: '#d1d5db' }}
          />

          <YAxis
            tick={{ fontSize: 12, fill: '#6b7280' }}
            tickFormatter={(v) => formatNumber(v)}
            tickLine={false}
            axisLine={false}
            label={{
              value: '月平均值',
              angle: -90,
              position: 'insideLeft',
              offset: -4,
              style: { fontSize: 12, fill: '#9ca3af' },
            }}
          />

          <Tooltip content={<CustomTooltip peakMonths={peakMonths} />} />

          {overallAvg > 0 && (
            <ReferenceLine
              y={overallAvg}
              stroke="#9ca3af"
              strokeDasharray="4 4"
              label={{
                value: `年均 ${formatNumber(overallAvg, 1)}`,
                position: 'right',
                fontSize: 11,
                fill: '#9ca3af',
              }}
            />
          )}

          <Bar
            dataKey="average"
            radius={[4, 4, 0, 0]}
            animationDuration={600}
            maxBarSize={48}
          >
            {chartData.map((entry) => (
              <Cell
                key={entry.month}
                fill={peakSet.has(entry.month) ? PEAK_COLOR : DEFAULT_COLOR}
                fillOpacity={peakSet.has(entry.month) ? 1 : 0.8}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
