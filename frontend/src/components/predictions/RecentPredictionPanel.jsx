import { useState, useCallback } from 'react';
import useFilterStore from '../../stores/useFilterStore';
import { formatCurrency } from '../../utils/formatters';

const DAYS_OPTIONS = [
  { value: 7, label: '7 天' },
  { value: 14, label: '14 天' },
  { value: 30, label: '30 天' },
];

function getDiffColor(pct) {
  const abs = Math.abs(pct);
  if (abs < 5) return { bg: 'bg-emerald-50', text: 'text-emerald-700', ring: 'ring-emerald-600/20', dot: 'bg-emerald-500', label: '穩定' };
  if (abs < 15) return { bg: 'bg-amber-50', text: 'text-amber-700', ring: 'ring-amber-600/20', dot: 'bg-amber-500', label: '中等偏離' };
  return { bg: 'bg-red-50', text: 'text-red-700', ring: 'ring-red-600/20', dot: 'bg-red-500', label: '顯著偏離' };
}

/**
 * Recent data quick prediction panel.
 * Allows users to select a day range and run predictions from recent data.
 */
export default function RecentPredictionPanel() {
  const { selectedCrop, selectedCropLabel } = useFilterStore();

  const [days, setDays] = useState(14);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handlePredict = useCallback(async () => {
    if (!selectedCrop) return;
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await fetch(`/api/v1/predictions/${selectedCrop}/predict-from-recent?days=${days}`, {
        method: 'POST',
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || errData.message || `預測失敗 (${res.status})`);
      }
      const data = await res.json();
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [selectedCrop, days]);

  const diffPct = result
    ? ((result.predicted_price ?? result.predictedPrice ?? 0) - (result.recent_avg_price ?? result.recentAvgPrice ?? 0))
      / (result.recent_avg_price ?? result.recentAvgPrice ?? 1) * 100
    : 0;

  return (
    <div className="rounded-xl border border-gray-100 bg-white shadow-sm">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-gray-100 px-6 py-4">
        <div>
          <h3 className="text-base font-semibold text-gray-800">
            近期資料快速預測
          </h3>
          <p className="mt-0.5 text-xs text-gray-400">
            根據近期實際資料進行即時預測分析
          </p>
        </div>
        <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700 ring-1 ring-inset ring-emerald-600/20">
          <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 3v11.25A2.25 2.25 0 006 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0118 16.5h-2.25m-7.5 0h7.5m-7.5 0l-1 3m8.5-3l1 3m0 0l.5 1.5m-.5-1.5h-9.5m0 0l-.5 1.5m.75-9l3-3 2.148 2.148A12.061 12.061 0 0116.5 7.605" />
          </svg>
          即時預測
        </span>
      </div>

      {/* Controls */}
      <div className="p-6">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          {/* Days select */}
          <div>
            <label className="mb-1.5 block text-xs font-medium text-gray-500">
              資料天數
            </label>
            <select
              value={days}
              onChange={(e) => setDays(Number(e.target.value))}
              className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700 shadow-sm transition-colors focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
            >
              {DAYS_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          {/* Crop display */}
          <div>
            <label className="mb-1.5 block text-xs font-medium text-gray-500">
              作物
            </label>
            <div className="flex h-[38px] items-center rounded-lg border border-gray-200 bg-gray-50 px-3 text-sm text-gray-700">
              {selectedCropLabel || selectedCrop || '未選擇'}
            </div>
          </div>

          {/* Predict button */}
          <div className="flex items-end">
            <button
              onClick={handlePredict}
              disabled={loading || !selectedCrop}
              className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-emerald-700 disabled:cursor-not-allowed disabled:bg-emerald-400"
            >
              {loading ? (
                <>
                  <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  預測中...
                </>
              ) : (
                <>
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.348a1.125 1.125 0 010 1.971l-11.54 6.347a1.125 1.125 0 01-1.667-.986V5.653z" />
                  </svg>
                  執行預測
                </>
              )}
            </button>
          </div>
        </div>

        {/* No crop selected hint */}
        {!selectedCrop && (
          <p className="mt-3 text-xs text-gray-400">請先選擇作物再進行預測</p>
        )}

        {/* Error */}
        {error && (
          <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            <div className="flex items-center gap-2">
              <svg className="h-4 w-4 shrink-0 text-red-500" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z" clipRule="evenodd" />
              </svg>
              預測失敗: {error}
            </div>
          </div>
        )}

        {/* Result */}
        {result && (
          <div className="mt-6 space-y-4">
            {/* Diff badge */}
            {(() => {
              const color = getDiffColor(diffPct);
              return (
                <div className={`flex items-center gap-2 rounded-lg ${color.bg} px-4 py-3`}>
                  <span className={`h-2 w-2 rounded-full ${color.dot}`} />
                  <span className={`text-sm font-semibold ${color.text}`}>
                    差異程度: {color.label} ({diffPct > 0 ? '+' : ''}{diffPct.toFixed(1)}%)
                  </span>
                </div>
              );
            })()}

            {/* Price comparison */}
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <div className="rounded-lg border border-gray-100 bg-gray-50/50 p-4">
                <p className="text-xs font-medium text-gray-500">近期平均價格</p>
                <p className="mt-1 text-xl font-bold tabular-nums text-gray-800">
                  {formatCurrency(result.recent_avg_price ?? result.recentAvgPrice ?? 0, 1)}
                </p>
                <p className="mt-0.5 text-xs text-gray-400">
                  過去 {days} 天均價
                </p>
              </div>
              <div className="rounded-lg border border-blue-200 bg-gradient-to-br from-blue-50 to-indigo-50 p-4">
                <p className="text-xs font-medium text-blue-500">模型預測值</p>
                <p className="mt-1 text-xl font-bold tabular-nums text-blue-700">
                  {formatCurrency(result.predicted_price ?? result.predictedPrice ?? 0, 1)}
                </p>
                <p className="mt-0.5 text-xs text-blue-400">
                  {selectedCropLabel || selectedCrop} 元/公斤
                </p>
              </div>
              <div className={`rounded-lg border p-4 ${
                Math.abs(diffPct) < 5
                  ? 'border-emerald-200 bg-gradient-to-br from-emerald-50 to-green-50'
                  : Math.abs(diffPct) < 15
                    ? 'border-amber-200 bg-gradient-to-br from-amber-50 to-yellow-50'
                    : 'border-red-200 bg-gradient-to-br from-red-50 to-orange-50'
              }`}>
                <p className={`text-xs font-medium ${
                  Math.abs(diffPct) < 5 ? 'text-emerald-500' : Math.abs(diffPct) < 15 ? 'text-amber-500' : 'text-red-500'
                }`}>差異百分比</p>
                <p className={`mt-1 text-xl font-bold tabular-nums ${
                  Math.abs(diffPct) < 5 ? 'text-emerald-700' : Math.abs(diffPct) < 15 ? 'text-amber-700' : 'text-red-700'
                }`}>
                  {diffPct > 0 ? '+' : ''}{diffPct.toFixed(1)}%
                </p>
                <p className={`mt-0.5 text-xs ${
                  Math.abs(diffPct) < 5 ? 'text-emerald-400' : Math.abs(diffPct) < 15 ? 'text-amber-400' : 'text-red-400'
                }`}>
                  {Math.abs(diffPct) < 5 ? '價格穩定' : diffPct > 0 ? '預測上漲' : '預測下跌'}
                </p>
              </div>
            </div>

            {/* Additional info */}
            {(result.data_points ?? result.dataPoints) && (
              <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
                <div className="flex items-start gap-3">
                  <svg className="mt-0.5 h-5 w-5 shrink-0 text-gray-400" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a.75.75 0 000 1.5h.253a.25.25 0 01.244.304l-.459 2.066A1.75 1.75 0 0010.747 15H11a.75.75 0 000-1.5h-.253a.25.25 0 01-.244-.304l.459-2.066A1.75 1.75 0 009.253 9H9z" clipRule="evenodd" />
                  </svg>
                  <p className="text-sm text-gray-600">
                    使用 {result.data_points ?? result.dataPoints} 筆近期資料進行預測分析
                    {(result.model_used ?? result.modelUsed) && `，模型: ${result.model_used ?? result.modelUsed}`}
                  </p>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
