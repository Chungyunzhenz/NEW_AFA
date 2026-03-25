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
import { formatNumber, formatCurrency } from '../../utils/formatters';

const MONTH_LABELS = [
  '1月', '2月', '3月', '4月', '5月', '6月',
  '7月', '8月', '9月', '10月', '11月', '12月',
];

const YEAR_COLORS = ['#3b82f6', '#f59e0b', '#10b981'];
const AVG_COLOR = '#9ca3af';

/**
 * Seasonal comparison chart: shows price by month (1-12) with
 * one line per year (most recent 3 years) plus a dashed historical average.
 *
 * @param {Object}  props
 * @param {Array}   props.data   - Array of { date, value } historical records.
 * @param {string}  [props.title]
 * @param {number}  [props.height=340]
 */
export default function SeasonalChart({
  data = [],
  title,
  height = 340,
}) {
  const { chartData, years } = useMemo(() => {
    if (!data || data.length === 0) return { chartData: [], years: [] };

    // Group values by year and month
    const byYearMonth = {};
    data.forEach((d) => {
      if (d.value == null || d.date == null) return;
      const dateObj = typeof d.date === 'string' ? new Date(d.date) : d.date;
      if (isNaN(dateObj.getTime())) return;
      const year = dateObj.getFullYear();
      const month = dateObj.getMonth(); // 0-indexed
      if (!byYearMonth[year]) byYearMonth[year] = Array.from({ length: 12 }, () => []);
      byYearMonth[year][month].push(d.value);
    });

    // Get the most recent 3 years that have data
    const allYears = Object.keys(byYearMonth)
      .map(Number)
      .sort((a, b) => b - a)
      .slice(0, 3)
      .sort((a, b) => a - b);

    // Build chart data: one row per month with columns for each year + average
    const rows = Array.from({ length: 12 }, (_, monthIdx) => {
      const row = { month: monthIdx + 1, label: MONTH_LABELS[monthIdx] };

      // Per-year monthly average
      const allValues = [];
      allYears.forEach((year) => {
        const values = byYearMonth[year]?.[monthIdx] ?? [];
        if (values.length > 0) {
          const avg = values.reduce((s, v) => s + v, 0) / values.length;
          row[`y${year}`] = Math.round(avg * 100) / 100;
          allValues.push(...values);
        } else {
          row[`y${year}`] = null;
        }
      });

      // Historical average across ALL years (not just recent 3)
      const allYearsValues = [];
      Object.values(byYearMonth).forEach((months) => {
        const vals = months[monthIdx] ?? [];
        allYearsValues.push(...vals);
      });
      row.average =
        allYearsValues.length > 0
          ? Math.round((allYearsValues.reduce((s, v) => s + v, 0) / allYearsValues.length) * 100) / 100
          : null;

      return row;
    });

    return { chartData: rows, years: allYears };
  }, [data]);

  if (!data.length || !years.length) {
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

      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={chartData} margin={{ top: 8, right: 16, left: 8, bottom: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" vertical={false} />

          <XAxis
            dataKey="label"
            tick={{ fontSize: 12, fill: '#6b7280' }}
            tickLine={false}
            axisLine={{ stroke: '#d1d5db' }}
          />

          <YAxis
            tick={{ fontSize: 12, fill: '#6b7280' }}
            tickFormatter={(v) => `$${formatNumber(v)}`}
            tickLine={false}
            axisLine={false}
            label={{
              value: '價格',
              angle: -90,
              position: 'insideLeft',
              offset: -4,
              style: { fontSize: 12, fill: '#9ca3af' },
            }}
          />

          <Tooltip
            content={({ active, payload, label }) => {
              if (!active || !payload?.length) return null;
              return (
                <div className="rounded-lg border border-gray-200 bg-white p-3 text-sm shadow-lg">
                  <p className="mb-1.5 font-medium text-gray-700">{label}</p>
                  {payload.map((p) => (
                    <p key={p.dataKey} style={{ color: p.color }}>
                      {p.name}: {formatCurrency(p.value, 1)}
                    </p>
                  ))}
                </div>
              );
            }}
          />

          <Legend wrapperStyle={{ fontSize: 13 }} />

          {/* One line per year */}
          {years.map((year, idx) => (
            <Line
              key={year}
              type="monotone"
              dataKey={`y${year}`}
              name={`${year} 年`}
              stroke={YEAR_COLORS[idx % YEAR_COLORS.length]}
              strokeWidth={2}
              dot={{ r: 3 }}
              activeDot={{ r: 5 }}
              connectNulls
            />
          ))}

          {/* Historical average dashed line */}
          <Line
            type="monotone"
            dataKey="average"
            name="歷史平均"
            stroke={AVG_COLOR}
            strokeWidth={2}
            strokeDasharray="6 3"
            dot={false}
            activeDot={{ r: 4 }}
            connectNulls
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
