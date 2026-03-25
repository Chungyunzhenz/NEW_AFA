import { useState, useCallback } from 'react';
import useFilterStore from '../../stores/useFilterStore';
import { simulateTyphoon } from '../../api/typhoon';
import { formatCurrency } from '../../utils/formatters';

const INTENSITY_OPTIONS = [
  { value: 'mild', label: '輕度颱風' },
  { value: 'moderate', label: '中度颱風' },
  { value: 'severe', label: '強烈颱風' },
];

const MONTH_OPTIONS = Array.from({ length: 12 }, (_, i) => ({
  value: i + 1,
  label: `${i + 1} 月`,
}));

function getImpactColor(pct) {
  const abs = Math.abs(pct);
  if (abs < 10) return { bg: 'bg-emerald-50', text: 'text-emerald-700', ring: 'ring-emerald-600/20', dot: 'bg-emerald-500', label: '輕微' };
  if (abs < 25) return { bg: 'bg-amber-50', text: 'text-amber-700', ring: 'ring-amber-600/20', dot: 'bg-amber-500', label: '中等' };
  return { bg: 'bg-red-50', text: 'text-red-700', ring: 'ring-red-600/20', dot: 'bg-red-500', label: '嚴重' };
}

/**
 * Typhoon scenario simulation panel.
 * Allows users to select intensity and month, then view the predicted impact.
 */
export default function TyphoonSimulator() {
  const { selectedCrop, selectedCropLabel } = useFilterStore();

  const [intensity, setIntensity] = useState('moderate');
  const [month, setMonth] = useState(new Date().getMonth() + 1);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSimulate = useCallback(async () => {
    if (!selectedCrop) return;
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const data = await simulateTyphoon({
        crop_key: selectedCrop,
        intensity,
        month,
      });
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [selectedCrop, intensity, month]);

  return (
    <div className="rounded-xl border border-gray-100 bg-white shadow-sm">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-gray-100 px-6 py-4">
        <div>
          <h3 className="text-base font-semibold text-gray-800">
            颱風情境模擬
          </h3>
          <p className="mt-0.5 text-xs text-gray-400">
            模擬不同強度颱風對農產品價格的影響
          </p>
        </div>
        <span className="inline-flex items-center gap-1.5 rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-700 ring-1 ring-inset ring-blue-600/20">
          <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
          </svg>
          情境分析
        </span>
      </div>

      {/* Controls */}
      <div className="p-6">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          {/* Intensity select */}
          <div>
            <label className="mb-1.5 block text-xs font-medium text-gray-500">
              颱風強度
            </label>
            <select
              value={intensity}
              onChange={(e) => setIntensity(e.target.value)}
              className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700 shadow-sm transition-colors focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
            >
              {INTENSITY_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          {/* Month select */}
          <div>
            <label className="mb-1.5 block text-xs font-medium text-gray-500">
              發生月份
            </label>
            <select
              value={month}
              onChange={(e) => setMonth(Number(e.target.value))}
              className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700 shadow-sm transition-colors focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
            >
              {MONTH_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          {/* Simulate button */}
          <div className="flex items-end">
            <button
              onClick={handleSimulate}
              disabled={loading || !selectedCrop}
              className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-indigo-400"
            >
              {loading ? (
                <>
                  <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  模擬中...
                </>
              ) : (
                <>
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.348a1.125 1.125 0 010 1.971l-11.54 6.347a1.125 1.125 0 01-1.667-.986V5.653z" />
                  </svg>
                  開始模擬
                </>
              )}
            </button>
          </div>
        </div>

        {/* No crop selected hint */}
        {!selectedCrop && (
          <p className="mt-3 text-xs text-gray-400">請先選擇作物再進行颱風模擬</p>
        )}

        {/* Error */}
        {error && (
          <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            <div className="flex items-center gap-2">
              <svg className="h-4 w-4 shrink-0 text-red-500" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z" clipRule="evenodd" />
              </svg>
              模擬失敗: {error}
            </div>
          </div>
        )}

        {/* Result */}
        {result && (
          <div className="mt-6 space-y-4">
            {/* Impact badge */}
            {(() => {
              const impactPct = result.impact_pct ?? result.impactPercent ?? result.impact_percent ?? 0;
              const color = getImpactColor(impactPct);
              return (
                <div className={`flex items-center gap-2 rounded-lg ${color.bg} px-4 py-3`}>
                  <span className={`h-2 w-2 rounded-full ${color.dot}`} />
                  <span className={`text-sm font-semibold ${color.text}`}>
                    影響程度: {color.label} ({impactPct > 0 ? '+' : ''}{impactPct.toFixed(1)}%)
                  </span>
                </div>
              );
            })()}

            {/* Prediction comparison */}
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="rounded-lg border border-gray-100 bg-gray-50/50 p-4">
                <p className="text-xs font-medium text-gray-500">原始預測</p>
                <p className="mt-1 text-xl font-bold tabular-nums text-gray-800">
                  {formatCurrency(result.originalForecast ?? result.original_forecast ?? 0, 1)}
                </p>
                <p className="mt-0.5 text-xs text-gray-400">
                  {selectedCropLabel || selectedCrop} 元/公斤
                </p>
              </div>
              <div className="rounded-lg border border-red-200 bg-gradient-to-br from-red-50 to-orange-50 p-4">
                <p className="text-xs font-medium text-red-500">颱風調整後預測</p>
                <p className="mt-1 text-xl font-bold tabular-nums text-red-700">
                  {formatCurrency(result.adjustedForecast ?? result.adjusted_forecast ?? 0, 1)}
                </p>
                <p className="mt-0.5 text-xs text-red-400">
                  {intensity === 'mild' ? '輕度' : intensity === 'moderate' ? '中度' : '強烈'}颱風 - {month} 月情境
                </p>
              </div>
            </div>

            {/* Additional details */}
            {(result.description || result.details) && (
              <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
                <div className="flex items-start gap-3">
                  <svg className="mt-0.5 h-5 w-5 shrink-0 text-amber-500" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a.75.75 0 000 1.5h.253a.25.25 0 01.244.304l-.459 2.066A1.75 1.75 0 0010.747 15H11a.75.75 0 000-1.5h-.253a.25.25 0 01-.244-.304l.459-2.066A1.75 1.75 0 009.253 9H9z" clipRule="evenodd" />
                  </svg>
                  <p className="text-sm text-amber-800">
                    {result.description || result.details}
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
