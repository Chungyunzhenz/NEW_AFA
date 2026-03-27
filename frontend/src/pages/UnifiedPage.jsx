import { useState, useMemo, useCallback, useEffect, useRef } from 'react';
import {
  ResponsiveContainer,
  ComposedChart,
  Bar,
  Line,
  Area,
  AreaChart,
  BarChart,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
  ReferenceArea,
} from 'recharts';
import ExportButton from '../components/common/ExportButton';
import SeasonalCompareChart from '../components/charts/SeasonalChart';
import useFilterStore from '../stores/useFilterStore';
import useMapStore from '../stores/useMapStore';
import usePredictionStore from '../stores/usePredictionStore';
import useMapData from '../hooks/useMapData';
import useTradingData from '../hooks/useTradingData';
import usePredictions from '../hooks/usePredictions';
import useCropConfig from '../hooks/useCropConfig';
import SummaryCards from '../components/dashboard/SummaryCards';
import TopMarketsTable from '../components/dashboard/TopMarketsTable';
import RecentAlerts from '../components/dashboard/RecentAlerts';
import TimeSeriesChart from '../components/charts/TimeSeriesChart';
import TaiwanMap from '../components/map/TaiwanMap';
import ForecastPanel from '../components/predictions/ForecastPanel';
import ForecastSummary from '../components/predictions/ForecastSummary';
import ModelInfoPanel from '../components/predictions/ModelInfoPanel';
import TyphoonSimulator from '../components/predictions/TyphoonSimulator';
import RecentPredictionPanel from '../components/predictions/RecentPredictionPanel';
import FeatureImportanceChart from '../components/charts/FeatureImportanceChart';
import DataQualityPanel from '../components/data/DataQualityPanel';
import useTyphoonData from '../hooks/useTyphoonData';
import UploadWizard from '../components/upload/UploadWizard';
import TrafficLightPanel from '../components/dashboard/TrafficLightPanel';
import { METRICS, METRIC_LABELS, GRANULARITY_LABELS } from '../utils/constants';
import { formatCurrency, formatNumber, formatDate } from '../utils/formatters';
import { fetchSyncStatus, triggerSync } from '../api/sync';

/* ============================================================ */
/*  Section header component                                     */
/* ============================================================ */
function SectionHeader({ id, title, subtitle }) {
  return (
    <div id={id} className="scroll-mt-28 border-t border-gray-200 pt-8 pb-2">
      <h2 className="text-xl font-bold text-gray-900">{title}</h2>
      {subtitle && <p className="mt-1 text-sm text-gray-500">{subtitle}</p>}
    </div>
  );
}

function CollapsibleSection({ title, subtitle, children, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between px-6 py-4 text-left hover:bg-gray-50 transition-colors"
      >
        <div>
          <h3 className="text-base font-semibold text-gray-800">{title}</h3>
          {subtitle && <p className="mt-0.5 text-xs text-gray-400">{subtitle}</p>}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-400">{open ? '收起' : '展開'}</span>
          <svg className={`h-5 w-5 text-gray-400 transition-transform ${open ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
          </svg>
        </div>
      </button>
      {open && (
        <div className="border-t border-gray-100 p-6 space-y-6">
          {children}
        </div>
      )}
    </div>
  );
}

/* ============================================================ */
/*  Dashboard: County detail panel                               */
/* ============================================================ */
function CountyDetailPanel({ county, mapData, onClose }) {
  const countyData = useMemo(
    () =>
      mapData.find((d) => {
        const name = (d.countyName || '').replace(/臺/g, '台');
        return d.countyId === county || name === county;
      }),
    [mapData, county],
  );
  if (!countyData) return null;

  const hasData = countyData.avgPrice > 0 || countyData.volume > 0;

  return (
    <div className="rounded-xl border border-gray-100 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold text-gray-800">{countyData.countyName ?? county}</h4>
        <button onClick={onClose} className="rounded p-1 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600" aria-label="關閉">
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
        </button>
      </div>
      {hasData ? (
        <dl className="mt-3 space-y-2 text-sm">
          <div className="flex justify-between"><dt className="text-gray-500">平均價格</dt><dd className="font-medium tabular-nums text-gray-800">NT$ {(countyData.avgPrice ?? 0).toLocaleString('zh-TW', { maximumFractionDigits: 1 })}</dd></div>
          <div className="flex justify-between"><dt className="text-gray-500">交易量</dt><dd className="font-medium tabular-nums text-gray-800">{(countyData.volume ?? 0).toLocaleString('zh-TW')} 公斤</dd></div>
          {countyData.productionTonnes > 0 && (
            <div className="flex justify-between"><dt className="text-gray-500">產量</dt><dd className="font-medium tabular-nums text-gray-800">{countyData.productionTonnes.toLocaleString('zh-TW')} 公噸</dd></div>
          )}
          {countyData.tempAvg != null && (
            <div className="flex justify-between border-t border-gray-100 pt-2 mt-2"><dt className="text-gray-500">平均氣溫</dt><dd className="font-medium tabular-nums text-blue-600">{countyData.tempAvg}°C</dd></div>
          )}
          {countyData.rainfallMm != null && (
            <div className="flex justify-between"><dt className="text-gray-500">近月降雨</dt><dd className="font-medium tabular-nums text-blue-600">{countyData.rainfallMm.toLocaleString('zh-TW')} mm</dd></div>
          )}
        </dl>
      ) : (
        <p className="mt-3 text-sm text-gray-400">此縣市暫無交易紀錄</p>
      )}
    </div>
  );
}

/* ============================================================ */
/*  Dashboard: Alerts from trading data                          */
/* ============================================================ */
function useAlerts(tradingData) {
  return useMemo(() => {
    if (!tradingData || tradingData.length < 2) return [];
    const alerts = [];
    for (let i = 1; i < tradingData.length; i++) {
      const prev = tradingData[i - 1];
      const curr = tradingData[i];
      const prevVal = prev.value ?? prev.avgPrice ?? prev.avg_price ?? prev.price_avg;
      const currVal = curr.value ?? curr.avgPrice ?? curr.avg_price ?? curr.price_avg;
      if (!prevVal || !currVal) continue;
      const change = (currVal - prevVal) / prevVal;
      if (Math.abs(change) > 0.15) {
        alerts.push({
          id: `alert-${i}`,
          severity: Math.abs(change) > 0.3 ? 'danger' : 'warning',
          message: `${change > 0 ? '價格急漲' : '價格急跌'} ${(Math.abs(change) * 100).toFixed(1)}%`,
          date: curr.date,
        });
      }
    }
    return alerts.slice(-10);
  }, [tradingData]);
}

/* ============================================================ */
/*  Trading: Price-Volume chart                                  */
/* ============================================================ */
function PriceVolumeChart({ data, loading }) {
  const chartData = useMemo(
    () => (data || []).map((d) => ({ date: d.period, price: d.price_avg ?? 0, volume: d.volume_total ?? 0 })).sort((a, b) => String(a.date ?? '').localeCompare(String(b.date ?? ''))),
    [data],
  );
  if (loading) return <div className="flex h-80 items-center justify-center"><div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-200 border-t-blue-600" /></div>;
  if (!chartData.length) return <div className="flex h-80 items-center justify-center text-sm text-gray-400">暫無資料</div>;
  return (
    <ResponsiveContainer width="100%" height={350}>
      <ComposedChart data={chartData} margin={{ top: 8, right: 24, left: 8, bottom: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis dataKey="date" tickFormatter={(v) => formatDate(v, 'MM/dd')} tick={{ fontSize: 12, fill: '#6b7280' }} tickLine={false} axisLine={{ stroke: '#d1d5db' }} minTickGap={40} />
        <YAxis yAxisId="price" orientation="left" tick={{ fontSize: 12, fill: '#6b7280' }} tickFormatter={(v) => `$${formatNumber(v)}`} tickLine={false} axisLine={false} label={{ value: '價格', angle: -90, position: 'insideLeft', style: { fontSize: 12, fill: '#9ca3af' } }} />
        <YAxis yAxisId="volume" orientation="right" tick={{ fontSize: 12, fill: '#6b7280' }} tickFormatter={(v) => formatNumber(v)} tickLine={false} axisLine={false} label={{ value: '交易量', angle: 90, position: 'insideRight', style: { fontSize: 12, fill: '#9ca3af' } }} />
        <Tooltip content={({ active, payload, label }) => { if (!active || !payload?.length) return null; return (<div className="rounded-lg border border-gray-200 bg-white p-3 text-sm shadow-lg"><p className="mb-1 font-medium text-gray-700">{formatDate(label)}</p>{payload.map((p) => (<p key={p.dataKey} style={{ color: p.color }}>{p.dataKey === 'price' ? '價格' : '交易量'}: {p.dataKey === 'price' ? formatCurrency(p.value, 1) : formatNumber(p.value)}</p>))}</div>); }} />
        <Legend wrapperStyle={{ fontSize: 13 }} formatter={(v) => (v === 'price' ? '價格' : '交易量')} />
        <Bar yAxisId="volume" dataKey="volume" fill="#93c5fd" opacity={0.6} radius={[2, 2, 0, 0]} />
        <Line yAxisId="price" type="monotone" dataKey="price" stroke="#ef4444" strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
      </ComposedChart>
    </ResponsiveContainer>
  );
}

/* ============================================================ */
/*  Trading: Seasonal chart                                      */
/* ============================================================ */
function SeasonalChart({ data, cropConfig }) {
  const monthlyData = useMemo(() => {
    if (!data || data.length === 0) return [];
    const byMonth = {};
    for (const d of data) {
      const dateStr = d.period;
      if (!dateStr) continue;
      const month = new Date(dateStr).getMonth() + 1;
      if (!byMonth[month]) byMonth[month] = { prices: [], volumes: [] };
      const price = d.price_avg ?? 0;
      const volume = d.volume_total ?? 0;
      if (price > 0) byMonth[month].prices.push(price);
      if (volume > 0) byMonth[month].volumes.push(volume);
    }
    return Array.from({ length: 12 }, (_, i) => {
      const m = i + 1;
      const entry = byMonth[m] || { prices: [], volumes: [] };
      const avgPrice = entry.prices.length > 0 ? entry.prices.reduce((s, v) => s + v, 0) / entry.prices.length : 0;
      const avgVolume = entry.volumes.length > 0 ? entry.volumes.reduce((s, v) => s + v, 0) / entry.volumes.length : 0;
      const isPeak = cropConfig?.seasonality?.peakMonths?.includes(m);
      const isOff = cropConfig?.seasonality?.offMonths?.includes(m);
      return { month: `${m}月`, avgPrice, avgVolume, isPeak, isOff };
    });
  }, [data, cropConfig]);

  if (!monthlyData.length || monthlyData.every((d) => d.avgPrice === 0)) return <div className="flex h-64 items-center justify-center text-sm text-gray-400">暫無季節性資料</div>;

  return (
    <ResponsiveContainer width="100%" height={300}>
      <AreaChart data={monthlyData} margin={{ top: 8, right: 24, left: 8, bottom: 8 }}>
        <defs><linearGradient id="seasonGradient" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#10b981" stopOpacity={0.3} /><stop offset="95%" stopColor="#10b981" stopOpacity={0} /></linearGradient></defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis dataKey="month" tick={{ fontSize: 12, fill: '#6b7280' }} tickLine={false} axisLine={{ stroke: '#d1d5db' }} />
        <YAxis tick={{ fontSize: 12, fill: '#6b7280' }} tickFormatter={(v) => `$${formatNumber(v)}`} tickLine={false} axisLine={false} />
        <Tooltip content={({ active, payload, label }) => { if (!active || !payload?.length) return null; const d = payload[0]?.payload; return (<div className="rounded-lg border border-gray-200 bg-white p-3 text-sm shadow-lg"><p className="mb-1 font-medium text-gray-700">{label}</p><p className="text-emerald-600">均價: {formatCurrency(d?.avgPrice, 1)}</p><p className="text-blue-600">均量: {formatNumber(d?.avgVolume)}</p>{d?.isPeak && <p className="mt-1 text-xs font-semibold text-orange-500">旺季</p>}{d?.isOff && <p className="mt-1 text-xs font-semibold text-gray-400">淡季</p>}</div>); }} />
        <Area type="monotone" dataKey="avgPrice" stroke="#10b981" strokeWidth={2} fill="url(#seasonGradient)" />
      </AreaChart>
    </ResponsiveContainer>
  );
}

/* ============================================================ */
/*  Trading: Market comparison                                   */
/* ============================================================ */
function MarketComparison({ data }) {
  const markets = useMemo(() => {
    if (!data || data.length === 0) return [];
    const byMarket = {};
    for (const d of data) {
      const market = d.market ?? d.marketName ?? d.market_name;
      if (!market) continue;
      if (!byMarket[market]) byMarket[market] = { prices: [], volumes: [] };
      const price = d.price_avg ?? 0;
      const vol = d.volume_total ?? 0;
      if (price > 0) byMarket[market].prices.push(price);
      if (vol > 0) byMarket[market].volumes.push(vol);
    }
    return Object.entries(byMarket).map(([name, info]) => ({ name, avgPrice: info.prices.length > 0 ? info.prices.reduce((s, v) => s + v, 0) / info.prices.length : 0, totalVolume: info.volumes.reduce((s, v) => s + v, 0), count: info.prices.length })).sort((a, b) => b.totalVolume - a.totalVolume).slice(0, 8);
  }, [data]);

  if (!markets.length) return <div className="flex h-40 items-center justify-center text-sm text-gray-400">暫無市場比較資料</div>;
  const maxVolume = Math.max(...markets.map((m) => m.totalVolume), 1);

  return (
    <div className="space-y-3">
      {markets.map((m) => (
        <div key={m.name} className="flex items-center gap-4">
          <span className="w-24 shrink-0 truncate text-sm font-medium text-gray-700">{m.name}</span>
          <div className="flex-1"><div className="h-6 w-full overflow-hidden rounded-full bg-gray-100"><div className="flex h-full items-center rounded-full bg-gradient-to-r from-blue-400 to-blue-600 transition-all duration-500" style={{ width: `${(m.totalVolume / maxVolume) * 100}%` }}>{m.totalVolume / maxVolume > 0.2 && <span className="pl-2 text-xs font-medium text-white">{formatNumber(m.totalVolume)}</span>}</div></div></div>
          <div className="w-24 text-right"><span className="text-sm tabular-nums text-gray-600">{formatCurrency(m.avgPrice, 1)}</span></div>
        </div>
      ))}
    </div>
  );
}

/* ============================================================ */
/*  Trading: Data table                                          */
/* ============================================================ */
function TradingDataTable({ data, loading, page, pageSize, totalCount, onPageChange }) {
  if (loading) {
    return (
      <div className="overflow-x-auto">
        <table className="w-full text-sm"><thead><tr className="border-b border-gray-100 bg-gray-50/60">{['日期', '市場', '作物', '平均價', '最高價', '最低價', '交易量'].map((h) => (<th key={h} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">{h}</th>))}</tr></thead>
          <tbody>{Array.from({ length: 5 }).map((_, i) => (<tr key={i} className="border-b border-gray-50 animate-pulse">{Array.from({ length: 7 }).map((__, j) => (<td key={j} className="px-4 py-3"><div className="h-4 w-20 rounded bg-gray-100" /></td>))}</tr>))}</tbody>
        </table>
      </div>
    );
  }
  if (!data.length) return <div className="flex h-40 items-center justify-center text-sm text-gray-400">暫無交易資料，請選擇作物</div>;
  const totalPages = Math.ceil(totalCount / pageSize) || 1;

  return (
    <div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead><tr className="border-b border-gray-100 bg-gray-50/60">
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">日期</th>
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">市場</th>
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">作物</th>
            <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">平均價</th>
            <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">最高價</th>
            <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">最低價</th>
            <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">交易量</th>
          </tr></thead>
          <tbody className="divide-y divide-gray-50">
            {data.map((row, idx) => (
              <tr key={row.id ?? idx} className={`transition-colors hover:bg-blue-50/30 ${idx % 2 === 0 ? '' : 'bg-gray-50/30'}`}>
                <td className="px-4 py-2.5 text-gray-700">{formatDate(row.date ?? row.period)}</td>
                <td className="px-4 py-2.5 text-gray-700">{row.market ?? row.marketName ?? row.market_name ?? '-'}</td>
                <td className="px-4 py-2.5 text-gray-700">{row.crop ?? row.cropName ?? row.crop_name ?? '-'}</td>
                <td className="px-4 py-2.5 text-right tabular-nums text-gray-700">{formatCurrency(row.avgPrice ?? row.avg_price, 1)}</td>
                <td className="px-4 py-2.5 text-right tabular-nums text-gray-700">{formatCurrency(row.maxPrice ?? row.max_price, 1)}</td>
                <td className="px-4 py-2.5 text-right tabular-nums text-gray-700">{formatCurrency(row.minPrice ?? row.min_price, 1)}</td>
                <td className="px-4 py-2.5 text-right tabular-nums text-gray-700">{formatNumber(row.volume ?? row.trading_volume)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="flex items-center justify-between border-t border-gray-100 px-4 py-3">
        <p className="text-xs text-gray-500">共 {formatNumber(totalCount)} 筆，第 {page} / {totalPages} 頁</p>
        <div className="flex items-center gap-1">
          <button onClick={() => onPageChange(page - 1)} disabled={page <= 1} className="rounded-lg px-3 py-1.5 text-sm text-gray-600 transition-colors hover:bg-gray-100 disabled:cursor-not-allowed disabled:text-gray-300">上一頁</button>
          {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => { let p; if (totalPages <= 5) { p = i + 1; } else if (page <= 3) { p = i + 1; } else if (page >= totalPages - 2) { p = totalPages - 4 + i; } else { p = page - 2 + i; } return (<button key={p} onClick={() => onPageChange(p)} className={`h-8 w-8 rounded-lg text-sm font-medium transition-colors ${p === page ? 'bg-blue-600 text-white' : 'text-gray-600 hover:bg-gray-100'}`}>{p}</button>); })}
          <button onClick={() => onPageChange(page + 1)} disabled={page >= totalPages} className="rounded-lg px-3 py-1.5 text-sm text-gray-600 transition-colors hover:bg-gray-100 disabled:cursor-not-allowed disabled:text-gray-300">下一頁</button>
        </div>
      </div>
    </div>
  );
}

/* ============================================================ */
/*  Forecast: Combined chart                                     */
/* ============================================================ */
function ForecastChart({ historicalData, predictions, loading, typhoonEvents = [] }) {
  const MODEL_COLORS = { prophet: '#3b82f6', sarima: '#f59e0b', xgboost: '#10b981', lightgbm: '#8b5cf6', ensemble: '#111827' };
  const MODEL_LABELS = { prophet: 'Prophet', sarima: 'SARIMA', xgboost: 'XGBoost', lightgbm: 'LightGBM', ensemble: '集成預測' };

  const chartData = useMemo(() => {
    const hist = (historicalData || []).map((d) => ({ date: d.period, actual: d.price_avg ?? null }));

    // Group predictions by date, with each model as a separate field
    const predItems = Array.isArray(predictions) ? predictions : [];
    const predMap = {};
    for (const d of predItems) {
      const date = d.forecast_date ?? d.date ?? d.forecastDate;
      const model = d.model_name ?? d.modelName ?? 'ensemble';
      const value = d.forecast_value ?? d.value ?? d.predicted;
      if (!date || value == null) continue;
      if (!predMap[date]) predMap[date] = { date };
      predMap[date][model] = value;
      if (model === 'ensemble') {
        predMap[date].ciUpper = d.upper_bound ?? d.ciUpper ?? null;
        predMap[date].ciLower = d.lower_bound ?? d.ciLower ?? null;
      }
    }
    const predRows = Object.values(predMap).sort((a, b) => (a.date > b.date ? 1 : -1));

    // Merge
    const merged = [...hist];
    if (hist.length > 0 && predRows.length > 0) {
      const last = hist[hist.length - 1];
      const bridge = { date: last.date, actual: last.actual };
      for (const m of Object.keys(MODEL_COLORS)) bridge[m] = last.actual;
      merged.push(bridge);
    }
    merged.push(...predRows);
    return merged;
  }, [historicalData, predictions]);

  const boundaryDate = useMemo(() => { if (!historicalData?.length) return null; const last = historicalData[historicalData.length - 1]; return last?.period ?? null; }, [historicalData]);

  if (loading) return <div className="flex h-96 items-center justify-center"><div className="flex flex-col items-center gap-3"><div className="h-10 w-10 animate-spin rounded-full border-4 border-blue-200 border-t-blue-600" /><p className="text-sm text-gray-500">載入預測資料中...</p></div></div>;
  if (!chartData.length) return <div className="flex h-96 items-center justify-center text-sm text-gray-400">請選擇作物以查看預測圖表</div>;

  return (
    <ResponsiveContainer width="100%" height={420}>
      <ComposedChart data={chartData} margin={{ top: 12, right: 24, left: 8, bottom: 8 }}>
        <defs><linearGradient id="ciGradient" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#818cf8" stopOpacity={0.2} /><stop offset="95%" stopColor="#818cf8" stopOpacity={0.02} /></linearGradient></defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis dataKey="date" tickFormatter={(v) => formatDate(v, 'MM/dd')} tick={{ fontSize: 12, fill: '#6b7280' }} tickLine={false} axisLine={{ stroke: '#d1d5db' }} minTickGap={40} />
        <YAxis tick={{ fontSize: 12, fill: '#6b7280' }} tickFormatter={(v) => `$${formatNumber(v)}`} tickLine={false} axisLine={false} label={{ value: '價格 (NT$)', angle: -90, position: 'insideLeft', offset: -4, style: { fontSize: 12, fill: '#9ca3af' } }} />
        <Tooltip content={({ active, payload, label }) => {
          if (!active || !payload?.length) return null;
          const d = payload[0]?.payload;
          return (
            <div className="rounded-lg border border-gray-200 bg-white p-3 text-sm shadow-lg min-w-[180px]">
              <p className="mb-2 font-medium text-gray-700">{formatDate(label)}</p>
              {d?.actual != null && <p className="text-blue-600 font-medium">實際價格: {formatCurrency(d.actual, 1)}</p>}
              {d?.ensemble != null && <p className="font-bold text-gray-900 mt-1">集成預測: {formatCurrency(d.ensemble, 1)}</p>}
              <div className="mt-1 pt-1 border-t border-gray-100 space-y-0.5">
                {d?.prophet != null && <p style={{color: MODEL_COLORS.prophet}}>Prophet: {formatCurrency(d.prophet, 1)}</p>}
                {d?.sarima != null && <p style={{color: MODEL_COLORS.sarima}}>SARIMA: {formatCurrency(d.sarima, 1)}</p>}
                {d?.xgboost != null && <p style={{color: MODEL_COLORS.xgboost}}>XGBoost: {formatCurrency(d.xgboost, 1)}</p>}
                {d?.lightgbm != null && <p style={{color: MODEL_COLORS.lightgbm}}>LightGBM: {formatCurrency(d.lightgbm, 1)}</p>}
              </div>
            </div>
          );
        }} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Area type="monotone" dataKey="ciUpper" stroke="none" fill="url(#ciGradient)" name="ciUpper" legendType="none" />
        <Area type="monotone" dataKey="ciLower" stroke="none" fill="#ffffff" name="ciLower" legendType="none" />
        {boundaryDate && <ReferenceLine x={boundaryDate} stroke="#9ca3af" strokeDasharray="4 4" label={{ value: '預測起點', position: 'top', style: { fontSize: 11, fill: '#9ca3af' } }} />}
        <Line type="monotone" dataKey="actual" stroke="#3b82f6" strokeWidth={2.5} dot={false} activeDot={{ r: 4 }} name="實際價格" connectNulls={false} />
        <Line type="monotone" dataKey="ensemble" stroke={MODEL_COLORS.ensemble} strokeWidth={3} strokeDasharray="0" dot={{ r: 3, fill: MODEL_COLORS.ensemble }} name="集成預測" connectNulls={false} />
        <Line type="monotone" dataKey="prophet" stroke={MODEL_COLORS.prophet} strokeWidth={1.5} strokeDasharray="6 3" dot={false} name="Prophet" connectNulls={false} opacity={0.7} />
        <Line type="monotone" dataKey="sarima" stroke={MODEL_COLORS.sarima} strokeWidth={1.5} strokeDasharray="6 3" dot={false} name="SARIMA" connectNulls={false} opacity={0.7} />
        <Line type="monotone" dataKey="xgboost" stroke={MODEL_COLORS.xgboost} strokeWidth={1.5} strokeDasharray="6 3" dot={false} name="XGBoost" connectNulls={false} opacity={0.7} />
        <Line type="monotone" dataKey="lightgbm" stroke={MODEL_COLORS.lightgbm} strokeWidth={1.5} strokeDasharray="6 3" dot={false} name="LightGBM" connectNulls={false} opacity={0.7} />
        {typhoonEvents.map((evt, idx) => (
          <ReferenceArea key={`typhoon-${idx}`} x1={evt.startDate ?? evt.start_date} x2={evt.endDate ?? evt.end_date} fill="#ef444420" stroke="#ef444440" strokeDasharray="3 3" label={{ value: evt.name ?? evt.typhoonName ?? '', position: 'top', style: { fontSize: 10, fill: '#ef4444' } }} />
        ))}
      </ComposedChart>
    </ResponsiveContainer>
  );
}

/* ============================================================ */
/*  Forecast: Price-Volume dual-axis compare chart               */
/* ============================================================ */
function PriceVolumeCompare({ data }) {
  const chartData = useMemo(() => {
    if (!data || data.length === 0) return [];
    return data
      .map((d) => ({
        date: d.period,
        price_avg: d.price_avg ?? 0,
        volume: d.volume_total ?? 0,
      }))
      .sort((a, b) => String(a.date ?? '').localeCompare(String(b.date ?? '')));
  }, [data]);

  if (!chartData.length) {
    return (
      <div className="flex h-[300px] items-center justify-center text-sm text-gray-400">
        暫無價量資料
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <ComposedChart data={chartData} margin={{ top: 8, right: 24, left: 8, bottom: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis
          dataKey="date"
          tickFormatter={(v) => formatDate(v, 'MM/dd')}
          tick={{ fontSize: 12, fill: '#6b7280' }}
          tickLine={false}
          axisLine={{ stroke: '#d1d5db' }}
          minTickGap={40}
        />
        <YAxis
          yAxisId="price"
          orientation="left"
          tick={{ fontSize: 12, fill: '#3b82f6' }}
          tickFormatter={(v) => `$${formatNumber(v)}`}
          tickLine={false}
          axisLine={false}
          label={{ value: '平均價格', angle: -90, position: 'insideLeft', style: { fontSize: 12, fill: '#3b82f6' } }}
        />
        <YAxis
          yAxisId="volume"
          orientation="right"
          tick={{ fontSize: 12, fill: '#8b5cf6' }}
          tickFormatter={(v) => formatNumber(v)}
          tickLine={false}
          axisLine={false}
          label={{ value: '交易量', angle: 90, position: 'insideRight', style: { fontSize: 12, fill: '#8b5cf6' } }}
        />
        <Tooltip
          content={({ active, payload, label }) => {
            if (!active || !payload?.length) return null;
            return (
              <div className="rounded-lg border border-gray-200 bg-white p-3 text-sm shadow-lg">
                <p className="mb-1 font-medium text-gray-700">{formatDate(label)}</p>
                {payload.map((p) => (
                  <p key={p.dataKey} style={{ color: p.color }}>
                    {p.dataKey === 'price_avg' ? '平均價格' : '交易量'}:{' '}
                    {p.dataKey === 'price_avg' ? formatCurrency(p.value, 1) : formatNumber(p.value)}
                  </p>
                ))}
              </div>
            );
          }}
        />
        <Legend
          wrapperStyle={{ fontSize: 13 }}
          formatter={(v) => (v === 'price_avg' ? '平均價格' : '交易量')}
        />
        <Bar
          yAxisId="volume"
          dataKey="volume"
          fill="#8b5cf6"
          opacity={0.35}
          radius={[2, 2, 0, 0]}
          name="volume"
        />
        <Line
          yAxisId="price"
          type="monotone"
          dataKey="price_avg"
          stroke="#3b82f6"
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4 }}
          name="price_avg"
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}

/* ============================================================ */
/*  Forecast: Model comparison chart                             */
/* ============================================================ */
function ModelComparisonChart({ modelInfo }) {
  const chartData = useMemo(() => { if (!modelInfo?.length) return []; return modelInfo.map((m) => ({ name: m.name ?? 'Unknown', MSE: m.mse ?? 0, RMSE: m.rmse ?? 0, MAE: m.mae ?? 0, 'R²': m.r_squared ?? 0 })); }, [modelInfo]);
  if (!chartData.length) return <div className="flex h-64 items-center justify-center text-sm text-gray-400">暫無模型比較資料</div>;
  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={chartData} margin={{ top: 8, right: 24, left: 8, bottom: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis dataKey="name" tick={{ fontSize: 12, fill: '#6b7280' }} tickLine={false} axisLine={{ stroke: '#d1d5db' }} />
        <YAxis tick={{ fontSize: 12, fill: '#6b7280' }} tickLine={false} axisLine={false} />
        <Tooltip content={({ active, payload, label }) => { if (!active || !payload?.length) return null; return (<div className="rounded-lg border border-gray-200 bg-white p-3 text-sm shadow-lg"><p className="mb-1 font-semibold text-gray-700">{label}</p>{payload.map((p) => (<p key={p.dataKey} style={{ color: p.color }}>{p.dataKey}: {p.value.toFixed(4)}</p>))}</div>); }} />
        <Legend wrapperStyle={{ fontSize: 13 }} />
        <Bar dataKey="MSE" fill="#f97316" radius={[4, 4, 0, 0]} />
        <Bar dataKey="RMSE" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
        <Bar dataKey="MAE" fill="#3b82f6" radius={[4, 4, 0, 0]} />
        <Bar dataKey="R²" fill="#10b981" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

/* ============================================================ */
/*  Data management: helpers (same as DataManagementPage)         */
/* ============================================================ */
function SyncStatusBadge({ status }) {
  const config = { success: { label: '同步成功', dot: 'bg-emerald-500', bg: 'bg-emerald-50 text-emerald-700' }, failed: { label: '同步失敗', dot: 'bg-red-500', bg: 'bg-red-50 text-red-700' }, syncing: { label: '同步中...', dot: 'bg-blue-500 animate-pulse', bg: 'bg-blue-50 text-blue-700' }, idle: { label: '待同步', dot: 'bg-gray-400', bg: 'bg-gray-50 text-gray-600' } };
  const c = config[status] || config.idle;
  return <span className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold ${c.bg}`}><span className={`h-2 w-2 rounded-full ${c.dot}`} />{c.label}</span>;
}

function SyncStatusCard({ syncInfo, onSync, syncing }) {
  return (
    <div className="rounded-xl border border-gray-100 bg-white p-6 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div><h3 className="text-base font-semibold text-gray-800">資料同步狀態</h3><p className="mt-1 text-xs text-gray-400">農委會公開資料自動同步</p></div>
        <SyncStatusBadge status={syncing ? 'syncing' : syncInfo?.status || 'idle'} />
      </div>
      <div className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-lg bg-gray-50 p-4"><p className="text-xs font-medium text-gray-500">最後同步時間</p><p className="mt-1 text-sm font-semibold text-gray-800">{syncInfo?.lastSync ? formatDate(syncInfo.lastSync, 'yyyy/MM/dd HH:mm') : '-'}</p></div>
        <div className="rounded-lg bg-gray-50 p-4"><p className="text-xs font-medium text-gray-500">資料更新至</p><p className="mt-1 text-sm font-semibold text-gray-800">{syncInfo?.dataUpTo ? formatDate(syncInfo.dataUpTo) : '-'}</p></div>
        <div className="rounded-lg bg-gray-50 p-4"><p className="text-xs font-medium text-gray-500">總記錄數</p><p className="mt-1 text-sm font-semibold text-gray-800">{syncInfo?.totalRecords ? formatNumber(syncInfo.totalRecords) : '-'}</p></div>
      </div>
      <div className="mt-5 flex items-center gap-3">
        <button onClick={onSync} disabled={syncing} className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-blue-400">
          {syncing ? (<><svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>同步中...</>) : (<><svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182" /></svg>手動同步</>)}
        </button>
        {syncInfo?.lastError && <span className="text-xs text-red-500">上次錯誤: {syncInfo.lastError}</span>}
      </div>
    </div>
  );
}

function DataCoverageTable({ crops, loading }) {
  if (loading) return <div className="overflow-x-auto"><table className="w-full text-sm"><thead><tr className="border-b border-gray-100 bg-gray-50/60">{['作物', '交易記錄', '產量記錄'].map((h) => (<th key={h} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">{h}</th>))}</tr></thead><tbody>{Array.from({ length: 5 }).map((_, i) => (<tr key={i} className="border-b border-gray-50 animate-pulse">{Array.from({ length: 3 }).map((__, j) => (<td key={j} className="px-4 py-3"><div className="h-4 w-20 rounded bg-gray-100" /></td>))}</tr>))}</tbody></table></div>;
  if (!crops?.length) return <div className="flex h-40 items-center justify-center text-sm text-gray-400">暫無作物資料</div>;
  return (
    <div className="overflow-x-auto"><table className="w-full text-sm"><thead><tr className="border-b border-gray-100 bg-gray-50/60"><th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">作物</th><th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">交易記錄</th><th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">產量記錄</th></tr></thead>
      <tbody className="divide-y divide-gray-50">{crops.map((crop, idx) => (<tr key={crop.crop_key ?? idx} className={`transition-colors hover:bg-blue-50/30 ${idx % 2 === 0 ? '' : 'bg-gray-50/30'}`}><td className="px-4 py-2.5 font-medium text-gray-800">{crop.display_name_zh ?? crop.crop_key ?? '-'}</td><td className="px-4 py-2.5 text-right tabular-nums text-gray-700">{formatNumber(crop.trading_records ?? 0)}</td><td className="px-4 py-2.5 text-right tabular-nums text-gray-700">{formatNumber(crop.production_records ?? 0)}</td></tr>))}</tbody></table></div>
  );
}

function RetrainSection({ onRetrain, retrainStatus }) {
  const statusConfig = { pending: { text: '訓練排程中...', color: 'text-blue-600' }, success: { text: '訓練完成', color: 'text-emerald-600' }, failed: { text: '訓練失敗', color: 'text-red-600' } };
  const statusInfo = retrainStatus ? statusConfig[retrainStatus] : null;
  return (
    <div className="rounded-xl border border-gray-100 bg-white p-6 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-4"><div><h3 className="text-base font-semibold text-gray-800">模型重新訓練</h3><p className="mt-1 text-xs text-gray-400">手動觸發預測模型重新訓練</p></div>{statusInfo && <span className={`text-sm font-medium ${statusInfo.color}`}>{statusInfo.text}</span>}</div>
      <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-4"><div className="flex items-start gap-3"><svg className="mt-0.5 h-5 w-5 shrink-0 text-amber-500" viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.168 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" /></svg><div className="text-sm text-amber-800"><p className="font-medium">注意事項</p><p className="mt-1 text-amber-700">重新訓練模型可能需要數分鐘。訓練期間預測功能將使用上一版本模型。建議在同步新資料後再執行重新訓練。</p></div></div></div>
      <div className="mt-4"><button onClick={onRetrain} disabled={retrainStatus === 'pending'} className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-indigo-400">{retrainStatus === 'pending' ? (<><svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>訓練中...</>) : (<><svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0112 15a9.065 9.065 0 00-6.23.693L5 14.5m14.8.8l1.402 1.402c1.232 1.232.65 3.318-1.067 3.611A48.309 48.309 0 0112 21c-2.773 0-5.491-.235-8.135-.687-1.718-.293-2.3-2.379-1.067-3.61L5 14.5" /></svg>開始重新訓練</>)}</button></div>
    </div>
  );
}

function AlertHistory({ alerts }) {
  if (!alerts?.length) return <div className="flex h-32 items-center justify-center text-sm text-gray-400">暫無系統通知</div>;
  return (
    <div className="divide-y divide-gray-50">{alerts.map((alert, idx) => (<div key={alert.id ?? idx} className="flex items-start gap-3 px-5 py-3"><div className={`mt-1 h-2 w-2 shrink-0 rounded-full ${alert.type === 'error' ? 'bg-red-500' : alert.type === 'warning' ? 'bg-amber-500' : 'bg-blue-500'}`} /><div className="min-w-0 flex-1"><p className="text-sm text-gray-700">{alert.message}</p><p className="mt-0.5 text-xs text-gray-400">{formatDate(alert.date ?? alert.createdAt, 'yyyy/MM/dd HH:mm')}</p></div></div>))}</div>
  );
}

function parseSyncStatusResponse(data) {
  const totalTrading = (data.crops ?? []).reduce((s, c) => s + (c.trading_records ?? 0), 0);
  const totalProduction = (data.crops ?? []).reduce((s, c) => s + (c.production_records ?? 0), 0);
  const taskRunning = data.sync_task?.is_running ?? false;
  const taskStatus = data.sync_task?.last_status;
  let status = 'idle';
  if (taskRunning) status = 'syncing';
  else if (taskStatus === 'success') status = 'success';
  else if (taskStatus === 'failed') status = 'failed';
  else if (totalTrading > 0) status = 'success';
  return { status, lastSync: data.sync_task?.last_run_at ?? data.last_sync_time ?? null, dataUpTo: data.latest_trade_date ?? null, totalRecords: totalTrading + totalProduction, lastError: data.sync_task?.last_error ?? null, crops: data.crops ?? [], unmatched: data.unmatched_records ?? 0, scheduler: data.scheduler ?? null, isTaskRunning: taskRunning };
}

/* ============================================================ */
/*  UNIFIED PAGE                                                 */
/* ============================================================ */
export default function UnifiedPage() {
  const { selectedCrop, selectedCropLabel, dateRange, metric, granularity } = useFilterStore();
  const setMetric = useFilterStore((s) => s.setMetric);
  const { selectedCounty, mapLayer } = useMapStore();
  const clearSelection = useMapStore((s) => s.clearSelection);
  const setGranularity = useFilterStore((s) => s.setGranularity);
  const setMapLayer = useMapStore((s) => s.setMapLayer);

  /* --- Dashboard data --- */
  const { mapData, loading: mapLoading, error: mapError } = useMapData();
  const { data: tradingData, totalCount, loading: tradingLoading, error: tradingError } = useTradingData();
  const alerts = useAlerts(tradingData);

  const summaryData = useMemo(() => {
    if (!tradingData || tradingData.length === 0) return null;
    const latest = tradingData[tradingData.length - 1];
    const previous = tradingData.length > 1 ? tradingData[tradingData.length - 2] : null;
    const latestPrice = latest?.price_avg ?? 0;
    const prevPrice = previous?.price_avg ?? 0;
    const priceChange = prevPrice > 0 ? (latestPrice - prevPrice) / prevPrice : 0;
    const monthlyVolume = tradingData.slice(-30).reduce((sum, d) => sum + (d.volume_total ?? 0), 0);
    const prevMonthVolume = tradingData.slice(-60, -30).reduce((sum, d) => sum + (d.volume_total ?? 0), 0);
    const volumeChange = prevMonthVolume > 0 ? (monthlyVolume - prevMonthVolume) / prevMonthVolume : 0;
    return { latestPrice, priceChange, monthlyVolume, yearlyVolume: tradingData.reduce((s, d) => s + (d.volume_total ?? 0), 0), volumeChange, yearlyChange: 0 };
  }, [tradingData]);

  const topMarkets = useMemo(() => {
    if (!mapData || mapData.length === 0) return [];
    const totalVolume = mapData.reduce((s, d) => s + (d.volume ?? 0), 0);
    return mapData.map((d) => ({ name: d.countyName ?? d.countyId ?? '-', avgPrice: d.avgPrice ?? 0, volume: d.volume ?? 0, share: totalVolume > 0 ? (d.volume ?? 0) / totalVolume : 0 })).sort((a, b) => b.volume - a.volume);
  }, [mapData]);

  const chartData = useMemo(() => (tradingData || []).map((d) => ({ date: d.period, value: d[metric] ?? d.price_avg ?? 0 })), [tradingData, metric]);

  /* --- Trading page data --- */
  const [tradingPage, setTradingPage] = useState(1);
  const tradingPageSize = 50;
  const { data: tableData, totalCount: tableTotalCount, loading: tableLoading } = useTradingData({ page: tradingPage, pageSize: tradingPageSize });
  const { config: cropConfig } = useCropConfig();
  const handleTradingPageChange = useCallback((p) => setTradingPage(Math.max(1, p)), []);

  /* --- Forecast data --- */
  const [horizon, setHorizon] = useState('7d');
  const horizonOptions = [{ value: '1m', label: '1 個月' }, { value: '3m', label: '3 個月' }, { value: '6m', label: '6 個月' }];
  const { predictions, forecast, modelInfo, loading: predLoading, error: predError } = usePredictions({ horizon });
  const { data: historicalData, loading: histLoading } = useTradingData();
  const { events: typhoonEvents } = useTyphoonData();

  /* --- Data management state --- */
  const { retrainStatus, requestRetrain } = usePredictionStore();
  const [crops, setCrops] = useState([]);
  const [cropsLoading, setCropsLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [syncInfo, setSyncInfo] = useState({ status: 'idle', lastSync: null, dataUpTo: null, totalRecords: null, lastError: null });
  const [systemAlerts, setSystemAlerts] = useState([]);
  const [uploadOpen, setUploadOpen] = useState(false);
  const pollRef = useRef(null);

  const loadSyncStatus = useCallback(async () => {
    try {
      const data = await fetchSyncStatus();
      const parsed = parseSyncStatusResponse(data);
      setSyncInfo(parsed); setCrops(parsed.crops);
      return parsed;
    } catch (err) {
      setSyncInfo((prev) => ({ ...prev, status: 'failed', lastError: err.message }));
      return null;
    }
  }, []);

  useEffect(() => { let cancelled = false; setCropsLoading(true); loadSyncStatus().finally(() => { if (!cancelled) setCropsLoading(false); }); return () => { cancelled = true; }; }, [loadSyncStatus]);

  const startPolling = useCallback(() => {
    if (pollRef.current) return;
    pollRef.current = setInterval(async () => {
      const parsed = await loadSyncStatus();
      if (parsed && !parsed.isTaskRunning) { clearInterval(pollRef.current); pollRef.current = null; setSyncing(false);
        if (parsed.status === 'success') setSystemAlerts((prev) => [{ id: `sync-${Date.now()}`, type: 'info', message: `資料同步完成，抓取 ${formatNumber(parsed.totalRecords)} 筆記錄`, date: new Date().toISOString() }, ...prev]);
        else if (parsed.status === 'failed') setSystemAlerts((prev) => [{ id: `err-${Date.now()}`, type: 'error', message: `同步失敗: ${parsed.lastError ?? '未知錯誤'}`, date: new Date().toISOString() }, ...prev]);
      }
    }, 3000);
  }, [loadSyncStatus]);

  useEffect(() => () => { if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; } }, []);

  const handleSync = useCallback(async () => {
    setSyncing(true); setSyncInfo((prev) => ({ ...prev, status: 'syncing', lastError: null }));
    try { await triggerSync({ dataType: 'both', daysBack: 7 }); startPolling(); }
    catch (err) { setSyncing(false); setSyncInfo((prev) => ({ ...prev, status: 'failed', lastError: err.message })); setSystemAlerts((prev) => [{ id: `err-${Date.now()}`, type: 'error', message: `同步觸發失敗: ${err.message}`, date: new Date().toISOString() }, ...prev]); }
  }, [startPolling]);

  const handleRetrain = useCallback(async () => {
    try { await requestRetrain({ forceRetrain: true }); setSystemAlerts((prev) => [{ id: `retrain-${Date.now()}`, type: 'info', message: '模型重新訓練已完成', date: new Date().toISOString() }, ...prev]); }
    catch (err) { setSystemAlerts((prev) => [{ id: `err-${Date.now()}`, type: 'error', message: `重新訓練失敗: ${err.message}`, date: new Date().toISOString() }, ...prev]); }
  }, [requestRetrain]);

  const isLoading = mapLoading || tradingLoading;
  const globalError = mapError || tradingError;

  return (
    <div className="space-y-6">
      {/* ★ Traffic Light Panel */}
      <TrafficLightPanel />

      {/* ============================================ */}
      {/*  § 總覽                                      */}
      {/* ============================================ */}
      <SummaryCards data={summaryData} loading={isLoading} />
      <p className="text-xs text-gray-400 mt-1 px-1">數據根據您選擇的日期範圍計算。綠色箭頭表示較上期上漲，紅色箭頭表示下跌。</p>

      {globalError && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          <div className="flex items-center gap-2">
            <svg className="h-5 w-5 shrink-0 text-red-500" viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z" clipRule="evenodd" /></svg>
            {globalError}
          </div>
        </div>
      )}

      {/* ============================================ */}
      {/*  § AI 預測核心（直接顯示）                     */}
      {/* ============================================ */}
      <div className="rounded-2xl border-2 border-blue-100 bg-gradient-to-r from-blue-50 to-indigo-50 p-6 shadow-sm">
        <div className="flex items-center gap-2 mb-4">
          <div className="h-8 w-8 rounded-lg bg-blue-600 flex items-center justify-center">
            <svg className="h-5 w-5 text-white" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 3v11.25A2.25 2.25 0 006 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0118 16.5h-2.25m-7.5 0h7.5m-7.5 0l-1 3m8.5-3l1 3m0 0l.5 1.5m-.5-1.5h-9.5m0 0l-.5 1.5" />
            </svg>
          </div>
          <h2 className="text-lg font-bold text-gray-900">AI 預測分析</h2>
          <div className="ml-auto flex items-center gap-2">
            <span className="text-sm text-gray-500">預測期間:</span>
            <div className="flex items-center rounded-lg bg-white/70 p-0.5">
              {horizonOptions.map((opt) => (
                <button key={opt.value} onClick={() => setHorizon(opt.value)} className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${horizon === opt.value ? 'bg-white text-indigo-700 shadow-sm' : 'text-gray-600 hover:text-gray-800'}`}>{opt.label}</button>
              ))}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          {/* Left: Forecast value */}
          <div className="rounded-xl bg-white p-5 shadow-sm">
            <p className="text-xs font-medium text-gray-500 mb-1">預測均價</p>
            <p className="text-3xl font-bold text-blue-700 tabular-nums">
              {forecast?.forecast_value != null ? formatCurrency(forecast.forecast_value, 1) : '--'}
            </p>
            <p className="text-xs text-gray-400 mt-1">元/公斤</p>
            {forecast?.forecast_value != null && forecast?.lower_bound != null && (() => {
              const mid = (forecast.lower_bound + forecast.upper_bound) / 2;
              const diff = forecast.forecast_value - mid;
              const isUp = diff > 0;
              return (
                <span className={`mt-2 inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${isUp ? 'bg-red-50 text-red-600' : 'bg-emerald-50 text-emerald-600'}`}>
                  {isUp ? '↑' : '↓'} 趨勢{isUp ? '偏高' : '偏低'}
                </span>
              );
            })()}
          </div>

          {/* Center: Confidence interval */}
          <div className="rounded-xl bg-white p-5 shadow-sm">
            <p className="text-xs font-medium text-gray-500 mb-1">預測區間</p>
            <p className="text-xl font-bold text-gray-800 tabular-nums">
              {forecast?.lower_bound != null && forecast?.upper_bound != null
                ? `${formatCurrency(forecast.lower_bound, 1)} ~ ${formatCurrency(forecast.upper_bound, 1)}`
                : '--'}
            </p>
            <p className="text-xs text-gray-400 mt-1">95% 信賴區間</p>
            {forecast?.lower_bound != null && forecast?.upper_bound != null && (() => {
              const spread = forecast.upper_bound - forecast.lower_bound;
              const mid = (forecast.upper_bound + forecast.lower_bound) / 2;
              const spreadPct = mid > 0 ? (spread / mid) * 100 : 0;
              const isNarrow = spreadPct < 10;
              return (
                <span className={`mt-2 inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${isNarrow ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'}`}>
                  {isNarrow ? '區間較窄，信心高' : '區間較寬，波動大'}
                </span>
              );
            })()}
          </div>

          {/* Right: Model accuracy */}
          <div className="rounded-xl bg-white p-5 shadow-sm">
            <p className="text-xs font-medium text-gray-500 mb-1">模型準確度 (R²)</p>
            {(() => {
              const bestModel = (modelInfo || [])
                .filter((m) => m.is_active && m.target_metric === 'price_avg' && m.region_type === 'national')
                .sort((a, b) => (b.r_squared ?? -Infinity) - (a.r_squared ?? -Infinity))[0]
                || (modelInfo || []).filter((m) => m.r_squared != null).sort((a, b) => (b.r_squared ?? -Infinity) - (a.r_squared ?? -Infinity))[0];
              const r2 = bestModel?.r_squared;
              const modelName = bestModel?.name ?? bestModel?.model_name ?? 'AI';
              return (
                <>
                  <p className="text-3xl font-bold text-emerald-600 tabular-nums">
                    {r2 != null ? r2.toFixed(4) : '--'}
                  </p>
                  <p className="text-xs text-gray-400 mt-1">
                    {r2 != null ? `MAE ${(bestModel?.mae ?? 0).toFixed(2)}` : '尚無模型數據'}
                  </p>
                  {modelName && r2 != null && (
                    <span className="mt-2 inline-block rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-700">
                      {modelName} 主導
                    </span>
                  )}
                </>
              );
            })()}
          </div>
        </div>

        {/* Summary text */}
        <div className="mt-4">
          <ForecastSummary horizon={horizon} />
        </div>
        <p className="text-xs text-gray-400 mt-2 px-1">預測基於歷史交易資料、天氣資料及颱風事件，使用 Prophet、SARIMA、XGBoost 三模型集成預測。</p>
      </div>

      {/* ============================================ */}
      {/*  § 預測圖表詳情（可摺疊）                     */}
      {/* ============================================ */}
      <CollapsibleSection title="預測圖表詳情" subtitle="AI 模型價格預測圖表。圖表中藍線為歷史實際價格，虛線為模型預測。">
        <div className="flex items-center justify-end gap-2">
          <ExportButton url={`/export/predictions/${selectedCrop}`} filename={`${selectedCrop}_predictions.csv`} label="匯出預測" />
        </div>

        <ForecastPanel forecast={forecast ? {
          value: forecast.forecast_value ?? forecast.value,
          ciLower: forecast.lower_bound ?? forecast.ciLower,
          ciUpper: forecast.upper_bound ?? forecast.ciUpper,
          forecastDate: forecast.forecast_date ?? forecast.forecastDate,
          generatedAt: forecast.generated_at ?? forecast.generatedAt,
          modelName: forecast.model_name ?? forecast.modelName,
          horizon: forecast.horizon_label ?? forecast.horizon,
          cropName: forecast.crop_key ?? forecast.cropName,
        } : null} loading={predLoading} />

        <div className="rounded-xl border border-gray-100 bg-white p-5 shadow-sm">
          <h3 className="mb-4 text-base font-semibold text-gray-800">歷史價格與預測走勢</h3>
          <ForecastChart historicalData={historicalData} predictions={predictions} loading={predLoading || histLoading} typhoonEvents={typhoonEvents} />
        </div>

        <div className="rounded-xl border border-gray-100 bg-white p-5 shadow-sm">
          <h3 className="mb-4 text-base font-semibold text-gray-800">價量雙軸比較</h3>
          <PriceVolumeCompare data={historicalData} />
        </div>

        <div className="rounded-xl border border-gray-100 bg-white p-5 shadow-sm">
          <h3 className="mb-4 text-base font-semibold text-gray-800">季節性年度比較</h3>
          <SeasonalCompareChart data={(historicalData || []).map((d) => ({ date: d.period, value: d.price_avg ?? 0 }))} />
        </div>
      </CollapsibleSection>

      <CollapsibleSection title="颱風情境模擬" subtitle="根據歷史颱風對農產品價格的影響，模擬不同強度颱風來襲時的價格預測調整。">
        <TyphoonSimulator />
      </CollapsibleSection>

      <CollapsibleSection title="近期資料快速預測" subtitle="將最近的實際交易均價與模型預測做比對，評估預測準確度。">
        <RecentPredictionPanel />
      </CollapsibleSection>

      {/* ============================================ */}
      {/*  § 進階分析（可摺疊）                         */}
      {/* ============================================ */}
      <CollapsibleSection title="模型成效分析" subtitle="四個預測模型（Prophet / SARIMA / XGBoost / LightGBM）的準確度比較、集成權重和影響因素排名。" defaultOpen={false}>
        {/* Model accuracy comparison */}
        <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
          <div className="rounded-xl border border-gray-100 bg-white p-5 shadow-sm">
            <h3 className="mb-2 text-base font-semibold text-gray-800">模型預測準確度</h3>
            <p className="mb-4 text-xs text-gray-400">R² 越接近 1 代表預測越準確。MSE/RMSE/MAE 越低越好。</p>
            <ModelComparisonChart modelInfo={modelInfo} />
          </div>
          <ModelInfoPanel modelInfo={modelInfo} loading={predLoading} />
        </div>

        {/* Ensemble weights visualization */}
        {forecast && (
          <div className="rounded-xl border border-gray-100 bg-white p-5 shadow-sm">
            <h3 className="mb-2 text-base font-semibold text-gray-800">模型集成權重</h3>
            <p className="mb-4 text-xs text-gray-400">系統自動計算各模型的預測誤差，準確度越高的模型獲得越大的投票權重。</p>
            {(() => {
              const weights = forecast.ensemble_weights ? (typeof forecast.ensemble_weights === 'string' ? JSON.parse(forecast.ensemble_weights) : forecast.ensemble_weights) : null;
              if (!weights) return <p className="text-sm text-gray-400">尚無集成權重資料</p>;
              const total = Object.values(weights).reduce((a, b) => a + b, 0) || 1;
              const modelColors = { prophet: '#3b82f6', sarima: '#f59e0b', xgboost: '#10b981' };
              const modelLabels = { prophet: 'Prophet', sarima: 'SARIMA', xgboost: 'XGBoost' };
              return (
                <div>
                  {/* Stacked bar */}
                  <div className="flex h-10 overflow-hidden rounded-lg">
                    {Object.entries(weights).map(([name, w]) => {
                      const pct = (w / total) * 100;
                      if (pct < 0.1) return null;
                      return (
                        <div key={name} style={{ width: `${pct}%`, backgroundColor: modelColors[name] || '#6b7280' }} className="flex items-center justify-center text-white text-xs font-bold transition-all">
                          {pct > 10 ? `${modelLabels[name] || name} ${pct.toFixed(1)}%` : ''}
                        </div>
                      );
                    })}
                  </div>
                  {/* Legend */}
                  <div className="mt-3 flex flex-wrap gap-4">
                    {Object.entries(weights).map(([name, w]) => (
                      <div key={name} className="flex items-center gap-2">
                        <span className="h-3 w-3 rounded-full" style={{ backgroundColor: modelColors[name] || '#6b7280' }} />
                        <span className="text-sm text-gray-600">{modelLabels[name] || name}</span>
                        <span className="text-sm font-bold text-gray-800">{((w / total) * 100).toFixed(1)}%</span>
                      </div>
                    ))}
                  </div>
                  <p className="mt-2 text-xs text-gray-400">權重越高代表該模型在此作物的預測越準確，系統會更信任它的預測結果。</p>
                </div>
              );
            })()}
          </div>
        )}

        {/* Feature importance */}
        <div className="rounded-xl border border-gray-100 bg-white p-5 shadow-sm">
          <h3 className="mb-2 text-base font-semibold text-gray-800">影響預測的關鍵因素</h3>
          <p className="mb-3 text-xs text-gray-400">XGBoost 模型自動判斷哪些因素對價格預測影響最大。紅色=颱風因素、藍色=天氣因素、黃色=季節因素。</p>
          <FeatureImportanceChart />
        </div>
      </CollapsibleSection>

      {/* ============================================ */}
      {/*  § 儀表板總覽（可摺疊）                       */}
      {/* ============================================ */}
      <CollapsibleSection title="儀表板總覽" subtitle="各縣市交易與天氣數據視覺化。地圖顏色越深代表價格越高，灰色表示無交易紀錄。點擊縣市查看詳情。">
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
          <div className="space-y-6 lg:col-span-7">
            <div className="rounded-xl border border-gray-100 bg-white p-5 shadow-sm">
              <TimeSeriesChart data={chartData} metric={metric} title={`${selectedCropLabel || selectedCrop || '農產品'}${METRIC_LABELS[metric] ?? ''}趨勢`} height={360} color="#3b82f6" />
            </div>
            <TopMarketsTable markets={topMarkets} loading={isLoading} />
            <RecentAlerts alerts={alerts} loading={isLoading} maxHeight={300} />
          </div>
          <div className="order-first space-y-4 lg:order-none lg:col-span-5 lg:sticky lg:top-28 lg:self-start">
            <div className="rounded-xl border border-gray-100 bg-white p-4 shadow-sm">
              <div className="mb-3 flex items-center justify-between flex-wrap gap-2">
                <h3 className="text-sm font-semibold text-gray-700">各縣市數據分佈</h3>
                <div className="flex items-center gap-2">
                  <div className="flex items-center rounded-lg bg-gray-100 p-0.5">
                    {[
                      { key: 'avg_price', label: '價格' },
                      { key: 'trading_volume', label: '交易量' },
                    ].map((opt) => (
                      <button key={opt.key} onClick={() => setMetric(opt.key)} className={`rounded-md px-2 py-1 text-xs font-medium transition-colors ${metric === opt.key ? 'bg-white text-blue-700 shadow-sm' : 'text-gray-600 hover:text-gray-800'}`}>{opt.label}</button>
                    ))}
                  </div>
                  <span className="text-xs text-gray-400">{dateRange.startDate} ~ {dateRange.endDate}</span>
                </div>
              </div>
              <TaiwanMap data={mapData} metric={metric} />
              <p className="mt-2 text-xs text-gray-400 text-center">點擊縣市查看詳細資訊 | 顏色越深代表數值越高 | 灰色為無資料地區</p>
            </div>
            {selectedCounty && <CountyDetailPanel county={selectedCounty} mapData={mapData} onClose={clearSelection} />}
          </div>
        </div>
      </CollapsibleSection>

      {/* ============================================ */}
      {/*  § 交易分析（可摺疊）                         */}
      {/* ============================================ */}
      <CollapsibleSection title="交易分析" subtitle="農產品市場交易數據分析與趨勢（點擊展開查看詳情）">
        <div className="flex items-center justify-end">
          <div className="flex items-center rounded-lg bg-gray-100 p-0.5">
            {Object.entries(GRANULARITY_LABELS).map(([key, label]) => (
              <button key={key} onClick={() => setGranularity(key)} className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${granularity === key ? 'bg-white text-blue-700 shadow-sm' : 'text-gray-600 hover:text-gray-800'}`}>{label}</button>
            ))}
          </div>
        </div>

        <div className="rounded-xl border border-gray-100 bg-white p-5 shadow-sm">
          <h3 className="mb-4 text-base font-semibold text-gray-800">價量走勢</h3>
          <PriceVolumeChart data={tradingData} loading={tradingLoading} />
        </div>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <div className="rounded-xl border border-gray-100 bg-white p-5 shadow-sm">
            <h3 className="mb-4 text-base font-semibold text-gray-800">季節性分析{cropConfig?.seasonality?.harvestSeason && <span className="ml-2 text-sm font-normal text-gray-400">採收期: {cropConfig.seasonality.harvestSeason}</span>}</h3>
            <SeasonalChart data={tradingData} cropConfig={cropConfig} />
          </div>
          <div className="rounded-xl border border-gray-100 bg-white p-5 shadow-sm">
            <h3 className="mb-4 text-base font-semibold text-gray-800">市場比較</h3>
            <MarketComparison data={tradingData} />
          </div>
        </div>

        <div className="rounded-xl border border-gray-100 bg-white shadow-sm">
          <div className="border-b border-gray-100 px-5 py-4">
            <h3 className="text-base font-semibold text-gray-800">交易資料明細</h3>
            <p className="mt-0.5 text-xs text-gray-400">{selectedCrop ?? '全部作物'}的交易紀錄</p>
          </div>
          <TradingDataTable data={tableData} loading={tableLoading} page={tradingPage} pageSize={tradingPageSize} totalCount={tableTotalCount} onPageChange={handleTradingPageChange} />
        </div>
      </CollapsibleSection>

      {/* ============================================ */}
      {/*  § 資料管理（可摺疊）                         */}
      {/* ============================================ */}
      <CollapsibleSection title="資料管理" subtitle="檢視資料覆蓋率、同步狀態，匯出 CSV 或下載 SQLite 資料庫供政府單位使用。">
        <DataQualityPanel />
        <SyncStatusCard syncInfo={syncInfo} onSync={handleSync} syncing={syncing} />
        <div className="flex flex-wrap items-center gap-2">
          <ExportButton url={`/export/historical/${selectedCrop}`} filename={`${selectedCrop}_historical.csv`} label="匯出歷史" />
          <ExportButton url="/export/database" filename="agriculture.db" label="下載資料庫" format="SQLite" />
        </div>
        <div className="rounded-xl border border-gray-100 bg-white shadow-sm">
          <div className="border-b border-gray-100 px-5 py-4">
            <h3 className="text-base font-semibold text-gray-800">資料涵蓋範圍</h3>
            <p className="mt-0.5 text-xs text-gray-400">各作物交易與產量記錄數量</p>
          </div>
          <DataCoverageTable crops={crops} loading={cropsLoading} />
        </div>
        <RetrainSection onRetrain={handleRetrain} retrainStatus={retrainStatus} />

      </CollapsibleSection>

      {/* Upload wizard - collapsible */}
      <div className="rounded-xl border border-gray-100 bg-white shadow-sm">
        <button
          onClick={() => setUploadOpen((v) => !v)}
          className="flex w-full items-center justify-between px-5 py-4 text-left"
        >
          <div>
            <h3 className="text-base font-semibold text-gray-800">資料匯入</h3>
            <p className="mt-0.5 text-xs text-gray-400">上傳 CSV 或 Excel 檔案匯入交易、產量或氣象資料</p>
          </div>
          <svg className={`h-5 w-5 text-gray-400 transition-transform ${uploadOpen ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
          </svg>
        </button>
        {uploadOpen && (
          <div className="border-t border-gray-100 p-6">
            <UploadWizard />
          </div>
        )}
      </div>

      {/* System alerts */}
      <div className="rounded-xl border border-gray-100 bg-white shadow-sm">
        <div className="border-b border-gray-100 px-5 py-4">
          <h3 className="text-base font-semibold text-gray-800">系統通知</h3>
          <p className="mt-0.5 text-xs text-gray-400">同步與訓練操作紀錄</p>
        </div>
        <AlertHistory alerts={systemAlerts} />
      </div>
    </div>
  );
}
