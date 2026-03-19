import { useState, useMemo, useCallback } from 'react';
import {
  ResponsiveContainer,
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  AreaChart,
  Area,
} from 'recharts';
import useFilterStore from '../stores/useFilterStore';
import useTradingData from '../hooks/useTradingData';
import useCropConfig from '../hooks/useCropConfig';
import TimeSeriesChart from '../components/charts/TimeSeriesChart';
import { METRICS, METRIC_LABELS, GRANULARITY_LABELS } from '../utils/constants';
import { formatCurrency, formatNumber, formatDate, formatPercent } from '../utils/formatters';

/* ------------------------------------------------------------------ */
/*  Price-Volume combined chart                                       */
/* ------------------------------------------------------------------ */
function PriceVolumeChart({ data, loading }) {
  const chartData = useMemo(
    () =>
      (data || [])
        .map((d) => ({
          date: d.date ?? d.period ?? d.month,
          price: d.value ?? d.avgPrice ?? d.avg_price ?? 0,
          volume: d.volume ?? d.trading_volume ?? 0,
        }))
        .sort((a, b) => String(a.date ?? '').localeCompare(String(b.date ?? ''))),
    [data],
  );

  if (loading) {
    return (
      <div className="flex h-80 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-200 border-t-blue-600" />
      </div>
    );
  }

  if (!chartData.length) {
    return (
      <div className="flex h-80 items-center justify-center text-sm text-gray-400">
        暫無資料
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={350}>
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
          tick={{ fontSize: 12, fill: '#6b7280' }}
          tickFormatter={(v) => `$${formatNumber(v)}`}
          tickLine={false}
          axisLine={false}
          label={{ value: '價格', angle: -90, position: 'insideLeft', style: { fontSize: 12, fill: '#9ca3af' } }}
        />
        <YAxis
          yAxisId="volume"
          orientation="right"
          tick={{ fontSize: 12, fill: '#6b7280' }}
          tickFormatter={(v) => formatNumber(v)}
          tickLine={false}
          axisLine={false}
          label={{ value: '交易量', angle: 90, position: 'insideRight', style: { fontSize: 12, fill: '#9ca3af' } }}
        />
        <Tooltip
          content={({ active, payload, label }) => {
            if (!active || !payload?.length) return null;
            return (
              <div className="rounded-lg border border-gray-200 bg-white p-3 text-sm shadow-lg">
                <p className="mb-1 font-medium text-gray-700">{formatDate(label)}</p>
                {payload.map((p) => (
                  <p key={p.dataKey} style={{ color: p.color }}>
                    {p.dataKey === 'price' ? '價格' : '交易量'}:{' '}
                    {p.dataKey === 'price' ? formatCurrency(p.value, 1) : formatNumber(p.value)}
                  </p>
                ))}
              </div>
            );
          }}
        />
        <Legend
          wrapperStyle={{ fontSize: 13 }}
          formatter={(v) => (v === 'price' ? '價格' : '交易量')}
        />
        <Bar yAxisId="volume" dataKey="volume" fill="#93c5fd" opacity={0.6} radius={[2, 2, 0, 0]} />
        <Line
          yAxisId="price"
          type="monotone"
          dataKey="price"
          stroke="#ef4444"
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4 }}
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}

/* ------------------------------------------------------------------ */
/*  Seasonal pattern chart                                            */
/* ------------------------------------------------------------------ */
function SeasonalChart({ data, cropConfig }) {
  const monthlyData = useMemo(() => {
    if (!data || data.length === 0) return [];
    // Aggregate data by month
    const byMonth = {};
    for (const d of data) {
      const dateStr = d.date ?? d.period ?? d.month;
      if (!dateStr) continue;
      const month = new Date(dateStr).getMonth() + 1;
      if (!byMonth[month]) byMonth[month] = { prices: [], volumes: [] };
      const price = d.value ?? d.avgPrice ?? d.avg_price ?? 0;
      const volume = d.volume ?? d.trading_volume ?? 0;
      if (price > 0) byMonth[month].prices.push(price);
      if (volume > 0) byMonth[month].volumes.push(volume);
    }
    return Array.from({ length: 12 }, (_, i) => {
      const m = i + 1;
      const entry = byMonth[m] || { prices: [], volumes: [] };
      const avgPrice =
        entry.prices.length > 0
          ? entry.prices.reduce((s, v) => s + v, 0) / entry.prices.length
          : 0;
      const avgVolume =
        entry.volumes.length > 0
          ? entry.volumes.reduce((s, v) => s + v, 0) / entry.volumes.length
          : 0;
      const isPeak = cropConfig?.seasonality?.peakMonths?.includes(m);
      const isOff = cropConfig?.seasonality?.offMonths?.includes(m);
      return { month: `${m}月`, avgPrice, avgVolume, isPeak, isOff };
    });
  }, [data, cropConfig]);

  if (!monthlyData.length || monthlyData.every((d) => d.avgPrice === 0)) {
    return (
      <div className="flex h-64 items-center justify-center text-sm text-gray-400">
        暫無季節性資料
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <AreaChart data={monthlyData} margin={{ top: 8, right: 24, left: 8, bottom: 8 }}>
        <defs>
          <linearGradient id="seasonGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis
          dataKey="month"
          tick={{ fontSize: 12, fill: '#6b7280' }}
          tickLine={false}
          axisLine={{ stroke: '#d1d5db' }}
        />
        <YAxis
          tick={{ fontSize: 12, fill: '#6b7280' }}
          tickFormatter={(v) => `$${formatNumber(v)}`}
          tickLine={false}
          axisLine={false}
        />
        <Tooltip
          content={({ active, payload, label }) => {
            if (!active || !payload?.length) return null;
            const d = payload[0]?.payload;
            return (
              <div className="rounded-lg border border-gray-200 bg-white p-3 text-sm shadow-lg">
                <p className="mb-1 font-medium text-gray-700">{label}</p>
                <p className="text-emerald-600">均價: {formatCurrency(d?.avgPrice, 1)}</p>
                <p className="text-blue-600">均量: {formatNumber(d?.avgVolume)}</p>
                {d?.isPeak && <p className="mt-1 text-xs font-semibold text-orange-500">旺季</p>}
                {d?.isOff && <p className="mt-1 text-xs font-semibold text-gray-400">淡季</p>}
              </div>
            );
          }}
        />
        <Area
          type="monotone"
          dataKey="avgPrice"
          stroke="#10b981"
          strokeWidth={2}
          fill="url(#seasonGradient)"
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

/* ------------------------------------------------------------------ */
/*  Data table with pagination                                        */
/* ------------------------------------------------------------------ */
function TradingDataTable({ data, loading, page, pageSize, totalCount, onPageChange }) {
  if (loading) {
    return (
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100 bg-gray-50/60">
              {['日期', '市場', '作物', '平均價', '最高價', '最低價', '交易量'].map((h) => (
                <th key={h} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {Array.from({ length: 5 }).map((_, i) => (
              <tr key={i} className="border-b border-gray-50 animate-pulse">
                {Array.from({ length: 7 }).map((__, j) => (
                  <td key={j} className="px-4 py-3">
                    <div className="h-4 w-20 rounded bg-gray-100" />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  if (!data.length) {
    return (
      <div className="flex h-40 items-center justify-center text-sm text-gray-400">
        暫無交易資料，請選擇作物
      </div>
    );
  }

  const totalPages = Math.ceil(totalCount / pageSize) || 1;

  return (
    <div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100 bg-gray-50/60">
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">日期</th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">市場</th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">作物</th>
              <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">平均價</th>
              <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">最高價</th>
              <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">最低價</th>
              <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">交易量</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {data.map((row, idx) => (
              <tr
                key={row.id ?? idx}
                className={`transition-colors hover:bg-blue-50/30 ${idx % 2 === 0 ? '' : 'bg-gray-50/30'}`}
              >
                <td className="px-4 py-2.5 text-gray-700">
                  {formatDate(row.date ?? row.period)}
                </td>
                <td className="px-4 py-2.5 text-gray-700">
                  {row.market ?? row.marketName ?? row.market_name ?? '-'}
                </td>
                <td className="px-4 py-2.5 text-gray-700">
                  {row.crop ?? row.cropName ?? row.crop_name ?? '-'}
                </td>
                <td className="px-4 py-2.5 text-right tabular-nums text-gray-700">
                  {formatCurrency(row.avgPrice ?? row.avg_price, 1)}
                </td>
                <td className="px-4 py-2.5 text-right tabular-nums text-gray-700">
                  {formatCurrency(row.maxPrice ?? row.max_price, 1)}
                </td>
                <td className="px-4 py-2.5 text-right tabular-nums text-gray-700">
                  {formatCurrency(row.minPrice ?? row.min_price, 1)}
                </td>
                <td className="px-4 py-2.5 text-right tabular-nums text-gray-700">
                  {formatNumber(row.volume ?? row.trading_volume)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between border-t border-gray-100 px-4 py-3">
        <p className="text-xs text-gray-500">
          共 {formatNumber(totalCount)} 筆，第 {page} / {totalPages} 頁
        </p>
        <div className="flex items-center gap-1">
          <button
            onClick={() => onPageChange(page - 1)}
            disabled={page <= 1}
            className="rounded-lg px-3 py-1.5 text-sm text-gray-600 transition-colors hover:bg-gray-100 disabled:cursor-not-allowed disabled:text-gray-300"
          >
            上一頁
          </button>
          {/* Page numbers */}
          {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => {
            let p;
            if (totalPages <= 5) {
              p = i + 1;
            } else if (page <= 3) {
              p = i + 1;
            } else if (page >= totalPages - 2) {
              p = totalPages - 4 + i;
            } else {
              p = page - 2 + i;
            }
            return (
              <button
                key={p}
                onClick={() => onPageChange(p)}
                className={`h-8 w-8 rounded-lg text-sm font-medium transition-colors ${
                  p === page
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-600 hover:bg-gray-100'
                }`}
              >
                {p}
              </button>
            );
          })}
          <button
            onClick={() => onPageChange(page + 1)}
            disabled={page >= totalPages}
            className="rounded-lg px-3 py-1.5 text-sm text-gray-600 transition-colors hover:bg-gray-100 disabled:cursor-not-allowed disabled:text-gray-300"
          >
            下一頁
          </button>
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Market comparison                                                 */
/* ------------------------------------------------------------------ */
function MarketComparison({ data }) {
  const markets = useMemo(() => {
    if (!data || data.length === 0) return [];
    const byMarket = {};
    for (const d of data) {
      const market = d.market ?? d.marketName ?? d.market_name;
      if (!market) continue;
      if (!byMarket[market]) byMarket[market] = { prices: [], volumes: [] };
      const price = d.avgPrice ?? d.avg_price ?? d.value ?? 0;
      const vol = d.volume ?? d.trading_volume ?? 0;
      if (price > 0) byMarket[market].prices.push(price);
      if (vol > 0) byMarket[market].volumes.push(vol);
    }
    return Object.entries(byMarket)
      .map(([name, info]) => ({
        name,
        avgPrice:
          info.prices.length > 0
            ? info.prices.reduce((s, v) => s + v, 0) / info.prices.length
            : 0,
        totalVolume: info.volumes.reduce((s, v) => s + v, 0),
        count: info.prices.length,
      }))
      .sort((a, b) => b.totalVolume - a.totalVolume)
      .slice(0, 8);
  }, [data]);

  if (!markets.length) {
    return (
      <div className="flex h-40 items-center justify-center text-sm text-gray-400">
        暫無市場比較資料
      </div>
    );
  }

  const maxVolume = Math.max(...markets.map((m) => m.totalVolume), 1);

  return (
    <div className="space-y-3">
      {markets.map((m) => (
        <div key={m.name} className="flex items-center gap-4">
          <span className="w-24 shrink-0 truncate text-sm font-medium text-gray-700">
            {m.name}
          </span>
          <div className="flex-1">
            <div className="h-6 w-full overflow-hidden rounded-full bg-gray-100">
              <div
                className="flex h-full items-center rounded-full bg-gradient-to-r from-blue-400 to-blue-600 transition-all duration-500"
                style={{ width: `${(m.totalVolume / maxVolume) * 100}%` }}
              >
                {m.totalVolume / maxVolume > 0.2 && (
                  <span className="pl-2 text-xs font-medium text-white">
                    {formatNumber(m.totalVolume)}
                  </span>
                )}
              </div>
            </div>
          </div>
          <div className="w-24 text-right">
            <span className="text-sm tabular-nums text-gray-600">
              {formatCurrency(m.avgPrice, 1)}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main Trading Analysis Page                                        */
/* ------------------------------------------------------------------ */
export default function TradingAnalysisPage() {
  const { selectedCrop, granularity, metric } = useFilterStore();
  const setGranularity = useFilterStore((s) => s.setGranularity);

  const [page, setPage] = useState(1);
  const pageSize = 50;

  const { data, totalCount, loading, error } = useTradingData({ page, pageSize });
  const { config: cropConfig } = useCropConfig();

  // Also fetch daily data for the table separately
  const {
    data: tableData,
    totalCount: tableTotalCount,
    loading: tableLoading,
  } = useTradingData({ page, pageSize, autoFetch: true });

  const handlePageChange = useCallback((newPage) => {
    setPage(Math.max(1, newPage));
  }, []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">交易分析</h1>
          <p className="mt-1 text-sm text-gray-500">
            農產品市場交易數據分析與趨勢
            {selectedCrop && (
              <span className="ml-2 font-medium text-blue-600">{selectedCrop}</span>
            )}
          </p>
        </div>

        {/* Granularity toggle */}
        <div className="flex items-center rounded-lg bg-gray-100 p-0.5">
          {Object.entries(GRANULARITY_LABELS).map(([key, label]) => (
            <button
              key={key}
              onClick={() => setGranularity(key)}
              className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                granularity === key
                  ? 'bg-white text-blue-700 shadow-sm'
                  : 'text-gray-600 hover:text-gray-800'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Price-Volume combined chart */}
      <div className="rounded-xl border border-gray-100 bg-white p-5 shadow-sm">
        <h3 className="mb-4 text-base font-semibold text-gray-800">價量走勢</h3>
        <PriceVolumeChart data={data} loading={loading} />
      </div>

      {/* Seasonal + Market comparison row */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded-xl border border-gray-100 bg-white p-5 shadow-sm">
          <h3 className="mb-4 text-base font-semibold text-gray-800">
            季節性分析
            {cropConfig?.seasonality?.harvestSeason && (
              <span className="ml-2 text-sm font-normal text-gray-400">
                採收期: {cropConfig.seasonality.harvestSeason}
              </span>
            )}
          </h3>
          <SeasonalChart data={data} cropConfig={cropConfig} />
        </div>

        <div className="rounded-xl border border-gray-100 bg-white p-5 shadow-sm">
          <h3 className="mb-4 text-base font-semibold text-gray-800">市場比較</h3>
          <MarketComparison data={data} />
        </div>
      </div>

      {/* Full data table */}
      <div className="rounded-xl border border-gray-100 bg-white shadow-sm">
        <div className="border-b border-gray-100 px-5 py-4">
          <h3 className="text-base font-semibold text-gray-800">交易資料明細</h3>
          <p className="mt-0.5 text-xs text-gray-400">
            {selectedCrop ?? '全部作物'}的交易紀錄
          </p>
        </div>
        <TradingDataTable
          data={tableData}
          loading={tableLoading}
          page={page}
          pageSize={pageSize}
          totalCount={tableTotalCount}
          onPageChange={handlePageChange}
        />
      </div>
    </div>
  );
}
