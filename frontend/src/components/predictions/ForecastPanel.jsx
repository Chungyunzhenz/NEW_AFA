import { useMemo } from 'react';
import { formatCurrency, formatDate, formatPercent } from '../../utils/formatters';

/**
 * Determine confidence level from the width of the confidence interval
 * relative to the forecast value.
 */
function getConfidenceLevel(forecast) {
  if (!forecast?.value || !forecast?.ciLower || !forecast?.ciUpper) {
    return { level: 'unknown', label: '未知', color: 'gray' };
  }
  const width = forecast.ciUpper - forecast.ciLower;
  const ratio = width / forecast.value;

  if (ratio < 0.1) return { level: 'high', label: '高', color: 'emerald' };
  if (ratio < 0.25) return { level: 'medium', label: '中', color: 'amber' };
  return { level: 'low', label: '低', color: 'red' };
}

function ConfidenceBadge({ confidence }) {
  const colorMap = {
    emerald: 'bg-emerald-100 text-emerald-700 ring-emerald-600/20',
    amber: 'bg-amber-100 text-amber-700 ring-amber-600/20',
    red: 'bg-red-100 text-red-700 ring-red-600/20',
    gray: 'bg-gray-100 text-gray-600 ring-gray-500/20',
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold ring-1 ring-inset ${
        colorMap[confidence.color] || colorMap.gray
      }`}
    >
      <span
        className={`h-1.5 w-1.5 rounded-full ${
          confidence.color === 'emerald'
            ? 'bg-emerald-500'
            : confidence.color === 'amber'
            ? 'bg-amber-500'
            : confidence.color === 'red'
            ? 'bg-red-500'
            : 'bg-gray-400'
        }`}
      />
      信心度: {confidence.label}
    </span>
  );
}

function ForecastValueCard({ label, value, subLabel, highlight = false }) {
  return (
    <div
      className={`rounded-lg border p-4 ${
        highlight
          ? 'border-blue-200 bg-gradient-to-br from-blue-50 to-indigo-50'
          : 'border-gray-100 bg-gray-50/50'
      }`}
    >
      <p className="text-xs font-medium text-gray-500">{label}</p>
      <p
        className={`mt-1 text-xl font-bold tabular-nums ${
          highlight ? 'text-blue-700' : 'text-gray-800'
        }`}
      >
        {value}
      </p>
      {subLabel && <p className="mt-0.5 text-xs text-gray-400">{subLabel}</p>}
    </div>
  );
}

/**
 * Displays forecast results including predicted value, confidence interval,
 * and visual confidence indicator.
 *
 * @param {Object}  props
 * @param {Object}  props.forecast - {
 *   value, ciLower, ciUpper, horizon, forecastDate,
 *   generatedAt, cropName, unit
 * }
 * @param {boolean} [props.loading=false]
 */
export default function ForecastPanel({ forecast, loading = false }) {
  const confidence = useMemo(() => getConfidenceLevel(forecast), [forecast]);

  const intervalWidth = useMemo(() => {
    if (!forecast?.ciLower || !forecast?.ciUpper) return null;
    return forecast.ciUpper - forecast.ciLower;
  }, [forecast]);

  if (loading) {
    return (
      <div className="rounded-xl border border-gray-100 bg-white p-6 shadow-sm">
        <div className="h-5 w-32 animate-pulse rounded bg-gray-200" />
        <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-24 animate-pulse rounded-lg bg-gray-100" />
          ))}
        </div>
      </div>
    );
  }

  if (!forecast) {
    return (
      <div className="rounded-xl border border-gray-100 bg-white p-6 shadow-sm">
        <div className="flex h-32 items-center justify-center text-sm text-gray-400">
          <div className="text-center">
            <svg className="mx-auto h-10 w-10 text-gray-300" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 3v11.25A2.25 2.25 0 006 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0118 16.5h-2.25m-7.5 0h7.5m-7.5 0l-1 3m8.5-3l1 3m0 0l.5 1.5m-.5-1.5h-9.5m0 0l-.5 1.5" />
            </svg>
            <p className="mt-2">請選擇作物以查看預測結果</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-gray-100 bg-white shadow-sm">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-gray-100 px-6 py-4">
        <div>
          <h3 className="text-base font-semibold text-gray-800">
            預測結果
            {forecast.cropName && (
              <span className="ml-2 text-blue-600">- {forecast.cropName}</span>
            )}
          </h3>
          <p className="mt-0.5 text-xs text-gray-400">
            預測期間: {forecast.horizon || '-'} |
            預測日期: {formatDate(forecast.forecastDate)}
          </p>
        </div>
        <ConfidenceBadge confidence={confidence} />
      </div>

      {/* Content */}
      <div className="p-6">
        {/* Main forecast values */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <ForecastValueCard
            label="預測值"
            value={formatCurrency(forecast.value, 1)}
            subLabel={forecast.unit || '元/公斤'}
            highlight
          />
          <ForecastValueCard
            label="信賴區間下界"
            value={formatCurrency(forecast.ciLower, 1)}
            subLabel="95% CI 下限"
          />
          <ForecastValueCard
            label="信賴區間上界"
            value={formatCurrency(forecast.ciUpper, 1)}
            subLabel="95% CI 上限"
          />
        </div>

        {/* Confidence interval visual */}
        <div className="mt-6">
          <div className="mb-2 flex items-center justify-between text-xs text-gray-500">
            <span>信賴區間範圍</span>
            {intervalWidth != null && (
              <span className="tabular-nums">
                寬度: {formatCurrency(intervalWidth, 1)}
              </span>
            )}
          </div>
          <div className="relative h-8 w-full overflow-hidden rounded-full bg-gray-100">
            {/* Full range background */}
            <div className="absolute inset-0 flex items-center px-2">
              {forecast.ciLower != null && forecast.ciUpper != null && (
                <>
                  {/* CI band */}
                  <div
                    className={`absolute h-full opacity-20 ${
                      confidence.color === 'emerald'
                        ? 'bg-emerald-400'
                        : confidence.color === 'amber'
                        ? 'bg-amber-400'
                        : 'bg-red-400'
                    }`}
                    style={{
                      left: '10%',
                      right: '10%',
                    }}
                  />
                  {/* Predicted value marker */}
                  <div
                    className="absolute top-0 h-full w-0.5 bg-blue-600"
                    style={{ left: '50%' }}
                  />
                  <div
                    className="absolute top-1/2 h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-blue-600 bg-white"
                    style={{ left: '50%' }}
                  />
                </>
              )}
            </div>
            {/* Labels */}
            <div className="absolute inset-0 flex items-center justify-between px-3 text-xs font-medium">
              <span className="text-gray-500">
                {forecast.ciLower != null ? formatCurrency(forecast.ciLower, 1) : '-'}
              </span>
              <span className="font-bold text-blue-700">
                {formatCurrency(forecast.value, 1)}
              </span>
              <span className="text-gray-500">
                {forecast.ciUpper != null ? formatCurrency(forecast.ciUpper, 1) : '-'}
              </span>
            </div>
          </div>
        </div>

        {/* Meta info */}
        <div className="mt-5 flex flex-wrap items-center gap-x-6 gap-y-2 border-t border-gray-100 pt-4 text-xs text-gray-400">
          <span>
            產生時間: {formatDate(forecast.generatedAt, 'yyyy/MM/dd HH:mm')}
          </span>
          {forecast.modelName && (
            <span>模型: {forecast.modelName}</span>
          )}
          {forecast.dataPoints && (
            <span>訓練資料量: {forecast.dataPoints.toLocaleString()} 筆</span>
          )}
        </div>
      </div>
    </div>
  );
}
