import { useState } from 'react';
import useDataQuality from '../../hooks/useDataQuality';

const HEALTH_STYLES = {
  green: { bg: 'bg-emerald-50', text: 'text-emerald-700', dot: 'bg-emerald-500', label: '良好' },
  yellow: { bg: 'bg-amber-50', text: 'text-amber-700', dot: 'bg-amber-500', label: '注意' },
  red: { bg: 'bg-red-50', text: 'text-red-700', dot: 'bg-red-500', label: '不足' },
};

function HealthBadge({ health }) {
  const s = HEALTH_STYLES[health] || HEALTH_STYLES.red;
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${s.bg} ${s.text}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${s.dot}`} />
      {s.label}
    </span>
  );
}

function SummaryCard({ title, health, children }) {
  return (
    <div className="rounded-xl border border-gray-100 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-semibold text-gray-800">{title}</h4>
        <HealthBadge health={health} />
      </div>
      <div className="space-y-1.5 text-sm text-gray-600">{children}</div>
    </div>
  );
}

function CropRow({ crop, expanded, onToggle }) {
  return (
    <>
      <tr
        className="cursor-pointer hover:bg-gray-50 transition-colors"
        onClick={onToggle}
      >
        <td className="px-4 py-2.5 text-sm font-medium text-gray-800">
          {crop.display_name_zh || crop.crop_key}
        </td>
        <td className="px-4 py-2.5 text-sm tabular-nums">
          {crop.trading_months_covered}/{crop.trading_months_expected}
        </td>
        <td className="px-4 py-2.5 text-sm tabular-nums">
          {crop.trading_coverage_pct}%
        </td>
        <td className="px-4 py-2.5 text-sm tabular-nums">
          {crop.production_years_covered}
        </td>
        <td className="px-4 py-2.5">
          <HealthBadge health={crop.health} />
        </td>
      </tr>
      {expanded && crop.gaps && crop.gaps.length > 0 && (
        <tr>
          <td colSpan={5} className="px-4 py-2 bg-gray-50">
            <p className="text-xs font-medium text-gray-500 mb-1">缺漏詳情：</p>
            <div className="flex flex-wrap gap-1.5">
              {crop.gaps.map((gap, i) => (
                <span key={i} className="inline-block rounded bg-red-50 px-2 py-0.5 text-xs text-red-600">
                  {gap}
                </span>
              ))}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

export default function DataQualityPanel() {
  const { data, loading, error } = useDataQuality();
  const [expandedCrop, setExpandedCrop] = useState(null);

  if (loading) {
    return (
      <div className="rounded-xl border border-gray-100 bg-white p-8 shadow-sm text-center text-sm text-gray-400">
        載入資料品質中...
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl border border-red-100 bg-red-50 p-5 shadow-sm text-sm text-red-600">
        載入失敗：{error}
      </div>
    );
  }

  if (!data) return null;

  const { trading, weather, production, per_crop } = data;

  return (
    <div className="space-y-6">
      {/* Summary cards */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <SummaryCard title="交易資料" health={trading.health}>
          <p>總筆數：{trading.total_records.toLocaleString()}</p>
          <p>日期範圍：{trading.date_range.start || '—'} ~ {trading.date_range.end || '—'}</p>
          <p>月份覆蓋：{trading.coverage_months}/{trading.expected_months}</p>
          <p>crop_id 缺漏：{trading.null_crop_id_pct}%</p>
          <p>market_id 缺漏：{trading.null_market_id_pct}%</p>
        </SummaryCard>

        <SummaryCard title="天氣資料" health={weather.health}>
          <p>總筆數：{weather.total_records.toLocaleString()}</p>
          <p>縣市覆蓋：{weather.counties_with_data}/{weather.counties_total}</p>
          {weather.missing_counties.length > 0 && (
            <p className="text-red-500">缺漏縣市：{weather.missing_counties.join('、')}</p>
          )}
          <p>溫度缺漏：{weather.null_field_pcts.temp_avg}%</p>
          <p>降雨缺漏：{weather.null_field_pcts.rainfall_mm}%</p>
        </SummaryCard>

        <SummaryCard title="產量資料" health={production.health}>
          <p>總筆數：{production.total_records.toLocaleString()}</p>
          <p>年份範圍：{production.year_range.start || '—'} ~ {production.year_range.end || '—'}</p>
          <p>年份覆蓋：{production.coverage_years}/{production.expected_years}</p>
        </SummaryCard>
      </div>

      {/* Per-crop table */}
      {per_crop && per_crop.length > 0 && (
        <div className="rounded-xl border border-gray-100 bg-white shadow-sm overflow-hidden">
          <div className="px-5 py-4 border-b border-gray-100">
            <h3 className="text-base font-semibold text-gray-800">各作物資料完整度</h3>
            <p className="text-xs text-gray-400 mt-0.5">點擊展開查看缺漏詳情</p>
          </div>
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50/50">
                <th className="px-4 py-2.5 text-left text-xs font-medium text-gray-500">作物</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium text-gray-500">交易月份</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium text-gray-500">覆蓋率</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium text-gray-500">產量年數</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium text-gray-500">狀態</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {per_crop.map((crop) => (
                <CropRow
                  key={crop.crop_key}
                  crop={crop}
                  expanded={expandedCrop === crop.crop_key}
                  onToggle={() =>
                    setExpandedCrop(expandedCrop === crop.crop_key ? null : crop.crop_key)
                  }
                />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
