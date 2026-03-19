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
import { formatDate, formatCurrency } from '../../utils/formatters';

/**
 * Distinct, colour-blind-friendly palette for up to 6 model lines.
 */
const MODEL_COLORS = {
  Prophet: '#0ea5e9',
  SARIMA: '#8b5cf6',
  XGBoost: '#10b981',
  Ensemble: '#f59e0b',
  LSTM: '#ec4899',
  Actual: '#374151',
};

const DEFAULT_PALETTE = ['#0ea5e9', '#8b5cf6', '#10b981', '#f59e0b', '#ec4899', '#64748b'];

function getColor(name, index) {
  return MODEL_COLORS[name] ?? DEFAULT_PALETTE[index % DEFAULT_PALETTE.length];
}

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
          {entry.name}: {formatCurrency(entry.value, 1)}
        </p>
      ))}
    </div>
  );
}

/**
 * Multi-model comparison line chart.
 *
 * @param {Object}  props
 * @param {Object}  props.models       - Dict of model_name -> Array of { date, value }.
 * @param {Array}   [props.actualData]  - Optional actual values for the validation period
 *                                        Array of { date, value }.
 * @param {string}  [props.title]
 * @param {number}  [props.height=400]
 */
export default function ModelComparisonChart({
  models = {},
  actualData,
  title,
  height = 400,
}) {
  const { chartData, modelNames } = useMemo(() => {
    const names = Object.keys(models);
    const dateMap = new Map();

    // Merge all model predictions by date
    names.forEach((name) => {
      (models[name] ?? []).forEach((d) => {
        const key = d.date;
        if (!dateMap.has(key)) dateMap.set(key, { date: key });
        dateMap.get(key)[name] = d.value;
      });
    });

    // Merge actual data if provided
    if (actualData?.length) {
      actualData.forEach((d) => {
        const key = d.date;
        if (!dateMap.has(key)) dateMap.set(key, { date: key });
        dateMap.get(key).Actual = d.value;
      });
    }

    const sorted = [...dateMap.values()].sort(
      (a, b) => new Date(a.date) - new Date(b.date),
    );

    const allNames = actualData?.length ? ['Actual', ...names] : names;

    return { chartData: sorted, modelNames: allNames };
  }, [models, actualData]);

  if (!chartData.length) {
    return (
      <div className="flex h-64 items-center justify-center text-gray-400">
        {title ? `${title} - ` : ''}暫無模型比較資料
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
            tickFormatter={(v) => formatDate(v, 'yyyy/MM')}
            tick={{ fontSize: 12, fill: '#6b7280' }}
            tickLine={false}
            axisLine={{ stroke: '#d1d5db' }}
            minTickGap={40}
          />

          <YAxis
            tick={{ fontSize: 12, fill: '#6b7280' }}
            tickFormatter={(v) => `$${v}`}
            tickLine={false}
            axisLine={false}
            label={{
              value: '價格 (NT$)',
              angle: -90,
              position: 'insideLeft',
              offset: -4,
              style: { fontSize: 12, fill: '#9ca3af' },
            }}
          />

          <Tooltip content={<CustomTooltip />} />

          <Legend wrapperStyle={{ fontSize: 13 }} />

          {modelNames.map((name, idx) => (
            <Line
              key={name}
              type="monotone"
              dataKey={name}
              name={name === 'Actual' ? '實際值' : name}
              stroke={getColor(name, idx)}
              strokeWidth={name === 'Actual' ? 2.5 : 2}
              strokeDasharray={name === 'Actual' ? undefined : undefined}
              dot={false}
              activeDot={{ r: 4, strokeWidth: 0, fill: getColor(name, idx) }}
              connectNulls={false}
              animationDuration={600}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
