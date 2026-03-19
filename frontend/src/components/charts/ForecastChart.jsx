import { useMemo } from 'react';
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
} from 'recharts';
import { formatDate, formatCurrency, formatNumber } from '../../utils/formatters';

const HISTORICAL_COLOR = '#0ea5e9';
const FORECAST_COLOR = '#f97316';
const CONFIDENCE_COLOR = '#fdba74';

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;

  const point = payload[0]?.payload;
  const isForecast = point?._isForecast;

  return (
    <div className="chart-tooltip">
      <p className="chart-tooltip-label">
        {formatDate(label)}
        {isForecast && (
          <span className="ml-1.5 text-xs text-orange-500 font-medium">預測</span>
        )}
      </p>

      {point?.historical != null && (
        <p className="chart-tooltip-value" style={{ color: HISTORICAL_COLOR }}>
          實際值: {formatCurrency(point.historical, 1)}
        </p>
      )}

      {point?.forecast != null && (
        <p className="chart-tooltip-value" style={{ color: FORECAST_COLOR }}>
          預測值: {formatCurrency(point.forecast, 1)}
        </p>
      )}

      {point?.upper != null && point?.lower != null && (
        <p className="text-xs text-gray-400 mt-0.5">
          信賴區間: {formatCurrency(point.lower, 1)} ~ {formatCurrency(point.upper, 1)}
        </p>
      )}
    </div>
  );
}

/**
 * Forecast chart showing historical data, predicted values, and confidence interval.
 *
 * @param {Object}  props
 * @param {Array}   props.historicalData  - Array of { date, value }.
 * @param {Array}   props.forecastData    - Array of { date, yhat, yhat_lower, yhat_upper }.
 * @param {string}  [props.title]
 * @param {number}  [props.height=400]
 */
export default function ForecastChart({
  historicalData = [],
  forecastData = [],
  title,
  height = 400,
  metric = 'price',
}) {
  const { merged, boundaryDate } = useMemo(() => {
    const historicalSorted = [...historicalData].sort(
      (a, b) => new Date(a.date) - new Date(b.date),
    );
    const forecastSorted = [...forecastData].sort(
      (a, b) => new Date(a.date) - new Date(b.date),
    );

    const boundary =
      historicalSorted.length > 0
        ? historicalSorted[historicalSorted.length - 1].date
        : forecastSorted.length > 0
          ? forecastSorted[0].date
          : null;

    const points = [];

    historicalSorted.forEach((d) => {
      points.push({
        date: d.date,
        historical: d.value,
        forecast: null,
        upper: null,
        lower: null,
        _isForecast: false,
      });
    });

    // Bridge point: last historical value also starts the forecast line for visual continuity
    if (historicalSorted.length > 0 && forecastSorted.length > 0) {
      const last = historicalSorted[historicalSorted.length - 1];
      const firstForecast = forecastSorted[0];

      // Only add bridge if dates differ
      if (last.date !== firstForecast.date) {
        points.push({
          date: last.date,
          historical: last.value,
          forecast: last.value,
          upper: last.value,
          lower: last.value,
          _isForecast: false,
        });
      }
    }

    forecastSorted.forEach((d) => {
      // Check if this date already exists from historical data
      const existing = points.find((p) => p.date === d.date);
      if (existing) {
        existing.forecast = d.yhat;
        existing.upper = d.yhat_upper;
        existing.lower = d.yhat_lower;
      } else {
        points.push({
          date: d.date,
          historical: null,
          forecast: d.yhat,
          upper: d.yhat_upper,
          lower: d.yhat_lower,
          _isForecast: true,
        });
      }
    });

    points.sort((a, b) => new Date(a.date) - new Date(b.date));

    return { merged: points, boundaryDate: boundary };
  }, [historicalData, forecastData]);

  if (!merged.length) {
    return (
      <div className="flex h-64 items-center justify-center text-gray-400">
        {title ? `${title} - ` : ''}暫無預測資料
      </div>
    );
  }

  return (
    <div className="w-full">
      {title && (
        <h3 className="mb-2 text-base font-semibold text-gray-700">{title}</h3>
      )}
      <ResponsiveContainer width="100%" height={height}>
        <ComposedChart data={merged} margin={{ top: 8, right: 24, left: 8, bottom: 8 }}>
          <defs>
            <linearGradient id="confidenceFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={CONFIDENCE_COLOR} stopOpacity={0.35} />
              <stop offset="100%" stopColor={CONFIDENCE_COLOR} stopOpacity={0.08} />
            </linearGradient>
          </defs>

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
            tickFormatter={(v) =>
              metric === 'volume' ? formatNumber(v) : `$${formatNumber(v)}`
            }
            tickLine={false}
            axisLine={false}
            label={{
              value: metric === 'volume' ? '交易量 (公斤)' : '價格 (NT$/公斤)',
              angle: -90,
              position: 'insideLeft',
              offset: -4,
              style: { fontSize: 12, fill: '#9ca3af' },
            }}
          />

          <Tooltip content={<CustomTooltip />} />

          <Legend wrapperStyle={{ fontSize: 13 }} />

          {/* Confidence interval shaded band */}
          <Area
            type="monotone"
            dataKey="upper"
            stroke="none"
            fill="url(#confidenceFill)"
            name="信賴區間上界"
            legendType="none"
            activeDot={false}
            animationDuration={600}
          />
          <Area
            type="monotone"
            dataKey="lower"
            stroke="none"
            fill="#ffffff"
            name="信賴區間下界"
            legendType="none"
            activeDot={false}
            animationDuration={600}
          />

          {/* Forecast boundary reference line */}
          {boundaryDate && (
            <ReferenceLine
              x={boundaryDate}
              stroke="#9ca3af"
              strokeDasharray="6 4"
              label={{
                value: '預測起點',
                position: 'top',
                fontSize: 11,
                fill: '#9ca3af',
              }}
            />
          )}

          {/* Historical line (solid) */}
          <Line
            type="monotone"
            dataKey="historical"
            stroke={HISTORICAL_COLOR}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4, strokeWidth: 0, fill: HISTORICAL_COLOR }}
            name="歷史資料"
            connectNulls={false}
            animationDuration={600}
          />

          {/* Forecast line (dashed) */}
          <Line
            type="monotone"
            dataKey="forecast"
            stroke={FORECAST_COLOR}
            strokeWidth={2}
            strokeDasharray="6 3"
            dot={false}
            activeDot={{ r: 4, strokeWidth: 0, fill: FORECAST_COLOR }}
            name="預測值"
            connectNulls={false}
            animationDuration={600}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
