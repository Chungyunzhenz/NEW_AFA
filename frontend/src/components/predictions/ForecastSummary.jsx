import { useState, useEffect } from 'react';
import useFilterStore from '../../stores/useFilterStore';
import { getForecastSummary } from '../../api/predictions';

const TREND_ICONS = {
  up: { icon: '↑', color: 'text-red-600', bg: 'bg-red-50', label: '上漲' },
  down: { icon: '↓', color: 'text-emerald-600', bg: 'bg-emerald-50', label: '下跌' },
  flat: { icon: '→', color: 'text-gray-600', bg: 'bg-gray-50', label: '穩定' },
};

const CONFIDENCE_STYLES = {
  high: { color: 'text-emerald-700', bg: 'bg-emerald-50', label: '高' },
  medium: { color: 'text-amber-700', bg: 'bg-amber-50', label: '中等' },
  low: { color: 'text-red-700', bg: 'bg-red-50', label: '低' },
};

export default function ForecastSummary({ horizon = '1m' }) {
  const selectedCrop = useFilterStore((s) => s.selectedCrop);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!selectedCrop) {
      setSummary(null);
      return;
    }

    let cancelled = false;
    async function fetch() {
      setLoading(true);
      try {
        const result = await getForecastSummary({ crop: selectedCrop, horizon });
        if (!cancelled) setSummary(result);
      } catch {
        if (!cancelled) setSummary(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    fetch();
    return () => { cancelled = true; };
  }, [selectedCrop, horizon]);

  if (loading) {
    return (
      <div className="rounded-xl border border-gray-100 bg-white p-5 shadow-sm animate-pulse">
        <div className="h-4 bg-gray-200 rounded w-3/4 mb-2" />
        <div className="h-4 bg-gray-200 rounded w-1/2" />
      </div>
    );
  }

  if (!summary || !summary.summary_text || summary.summary_text === '尚無預測資料。') {
    return null;
  }

  const trend = TREND_ICONS[summary.trend] || TREND_ICONS.flat;
  const conf = CONFIDENCE_STYLES[summary.confidence] || CONFIDENCE_STYLES.medium;

  return (
    <div className="rounded-xl border border-gray-100 bg-white p-5 shadow-sm">
      <h3 className="text-base font-semibold text-gray-800 mb-3">預測摘要</h3>

      {/* Badges row */}
      <div className="flex flex-wrap gap-2 mb-3">
        <span className={`inline-flex items-center gap-1 rounded-full px-3 py-1 text-sm font-medium ${trend.bg} ${trend.color}`}>
          {trend.icon} {trend.label}
          {summary.trend_pct != null && ` ${Math.abs(summary.trend_pct)}%`}
        </span>

        <span className={`inline-flex items-center gap-1 rounded-full px-3 py-1 text-sm font-medium ${conf.bg} ${conf.color}`}>
          信心度：{conf.label}
        </span>

        {summary.yoy_pct != null && (
          <span className={`inline-flex items-center gap-1 rounded-full px-3 py-1 text-sm font-medium ${summary.yoy_pct >= 0 ? 'bg-red-50 text-red-600' : 'bg-emerald-50 text-emerald-600'}`}>
            YoY {summary.yoy_pct >= 0 ? '+' : ''}{summary.yoy_pct}%
          </span>
        )}

        {summary.typhoon_risk && (
          <span className="inline-flex items-center gap-1 rounded-full px-3 py-1 text-sm font-medium bg-orange-50 text-orange-700">
            颱風風險
          </span>
        )}
      </div>

      {/* Summary text */}
      <p className="text-sm text-gray-600 leading-relaxed">{summary.summary_text}</p>
    </div>
  );
}
