import { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import useFilterStore from '../../stores/useFilterStore';

// API 呼叫可以直接 fetch
export default function FeatureImportanceChart() {
  const selectedCrop = useFilterStore((s) => s.selectedCrop);
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!selectedCrop) return;
    let cancelled = false;
    async function load() {
      setLoading(true);
      try {
        const res = await fetch(`/api/v1/predictions/${selectedCrop}/feature-importance`);
        const json = await res.json();
        if (!cancelled && json.features) {
          // 取前 15 個，反轉顯示（最重要的在上面）
          setData(json.features.slice(0, 15).reverse());
        }
      } catch {}
      if (!cancelled) setLoading(false);
    }
    load();
    return () => { cancelled = true; };
  }, [selectedCrop]);

  // 特徵名稱中文對照
  const FEATURE_LABELS = {
    'is_typhoon_month': '颱風月',
    'typhoon_count': '颱風次數',
    'typhoon_intensity_max': '颱風最大強度',
    'days_since_typhoon': '距颱風天數',
    'post_typhoon_1m': '颱風後1月',
    'post_typhoon_2m': '颱風後2月',
    'extreme_rainfall_flag': '極端降雨',
    'temp_avg': '平均溫度',
    'rainfall_mm': '降雨量',
    'temp_anomaly': '溫度異常',
    'month': '月份',
    'quarter': '季度',
    'is_peak_season': '產季',
    'month_sin': '月份(sin)',
    'month_cos': '月份(cos)',
  };

  function getLabel(name) {
    if (FEATURE_LABELS[name]) return FEATURE_LABELS[name];
    if (name.startsWith('lag_')) return `滯後${name.split('_')[1]}期`;
    if (name.startsWith('roll_mean_')) return `${name.split('_')[2]}期均值`;
    if (name.startsWith('roll_std_')) return `${name.split('_')[2]}期標準差`;
    if (name.startsWith('yoy_')) return '年對比';
    return name;
  }

  // 顏色：颱風相關用紅色系，天氣用藍色系，其他用灰色系
  function getColor(name) {
    if (name.includes('typhoon') || name === 'post_typhoon_1m' || name === 'post_typhoon_2m' || name === 'extreme_rainfall_flag') return '#ef4444';
    if (name.includes('temp') || name.includes('rain') || name.includes('humidity')) return '#3b82f6';
    if (name.includes('month') || name.includes('quarter') || name.includes('season')) return '#f59e0b';
    return '#6b7280';
  }

  if (loading) return <div className="p-4 text-sm text-gray-400">載入特徵重要性...</div>;
  if (!data.length) return null;

  const chartData = data.map(d => ({ name: getLabel(d.name), value: d.importance, rawName: d.name }));

  return (
    <div>
      <ResponsiveContainer width="100%" height={Math.max(250, data.length * 28)}>
        <BarChart data={chartData} layout="vertical" margin={{ left: 100, right: 20, top: 5, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" horizontal={false} />
          <XAxis type="number" tick={{ fontSize: 11 }} />
          <YAxis dataKey="name" type="category" tick={{ fontSize: 11 }} width={95} />
          <Tooltip formatter={(v) => v.toFixed(4)} />
          <Bar dataKey="value" radius={[0, 4, 4, 0]}>
            {chartData.map((entry, i) => (
              <Cell key={i} fill={getColor(data[i]?.rawName || entry.rawName || '')} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <div className="mt-3 flex flex-wrap gap-3 text-xs text-gray-500">
        <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-red-500" />颱風因素</span>
        <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-blue-500" />天氣因素</span>
        <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-amber-500" />季節因素</span>
        <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-gray-500" />其他</span>
      </div>
    </div>
  );
}
