import { useEffect, useMemo, useState } from 'react';
import useFilterStore from '../stores/useFilterStore';
import useMapStore from '../stores/useMapStore';
import useMapData from '../hooks/useMapData';
import useTradingData from '../hooks/useTradingData';
import SummaryCards from '../components/dashboard/SummaryCards';
import TopMarketsTable from '../components/dashboard/TopMarketsTable';
import RecentAlerts from '../components/dashboard/RecentAlerts';
import TimeSeriesChart from '../components/charts/TimeSeriesChart';
import TaiwanMap from '../components/map/TaiwanMap';
import { METRICS, METRIC_LABELS } from '../utils/constants';
import { formatDate } from '../utils/formatters';

/* ------------------------------------------------------------------ */
/*  County detail side panel (shown when a county is selected on map) */
/* ------------------------------------------------------------------ */
function CountyDetailPanel({ county, mapData, onClose }) {
  const countyData = useMemo(
    () => mapData.find((d) => {
      const name = (d.countyName || '').replace(/臺/g, '台');
      return d.countyId === county || name === county;
    }),
    [mapData, county],
  );

  if (!countyData) return null;

  return (
    <div className="rounded-xl border border-gray-100 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold text-gray-800">
          {countyData.countyName ?? county}
        </h4>
        <button
          onClick={onClose}
          className="rounded p-1 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600"
          aria-label="關閉"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
      <dl className="mt-3 space-y-2 text-sm">
        <div className="flex justify-between">
          <dt className="text-gray-500">平均價格</dt>
          <dd className="font-medium tabular-nums text-gray-800">
            NT$ {(countyData.avgPrice ?? 0).toLocaleString('zh-TW', { maximumFractionDigits: 1 })}
          </dd>
        </div>
        <div className="flex justify-between">
          <dt className="text-gray-500">交易量</dt>
          <dd className="font-medium tabular-nums text-gray-800">
            {(countyData.volume ?? 0).toLocaleString('zh-TW')} 公斤
          </dd>
        </div>
      </dl>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Alerts mock generator (used until real alert API is integrated)   */
/* ------------------------------------------------------------------ */
function useAlerts(tradingData) {
  return useMemo(() => {
    if (!tradingData || tradingData.length < 2) return [];
    const alerts = [];
    // Generate alerts from significant price changes in trading data
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

/* ------------------------------------------------------------------ */
/*  Main Dashboard Page                                               */
/* ------------------------------------------------------------------ */
export default function DashboardPage() {
  const { selectedCrop, selectedCropLabel, dateRange, metric } = useFilterStore();
  const { selectedCounty, mapLayer } = useMapStore();
  const clearSelection = useMapStore((s) => s.clearSelection);

  const { mapData, loading: mapLoading, error: mapError } = useMapData();
  const { data: tradingData, loading: tradingLoading, error: tradingError } = useTradingData();

  // Derive summary KPI values from trading data
  const summaryData = useMemo(() => {
    if (!tradingData || tradingData.length === 0) return null;

    const latest = tradingData[tradingData.length - 1];
    const previous = tradingData.length > 1 ? tradingData[tradingData.length - 2] : null;

    const latestPrice = latest?.value ?? latest?.avgPrice ?? latest?.avg_price ?? latest?.price_avg ?? 0;
    const prevPrice = previous?.value ?? previous?.avgPrice ?? previous?.avg_price ?? previous?.price_avg ?? 0;
    const priceChange = prevPrice > 0 ? (latestPrice - prevPrice) / prevPrice : 0;

    const monthlyVolume = tradingData
      .slice(-30)
      .reduce((sum, d) => sum + (d.volume ?? d.trading_volume ?? d.volume_total ?? 0), 0);

    const yearlyVolume = tradingData.reduce(
      (sum, d) => sum + (d.volume ?? d.trading_volume ?? d.volume_total ?? 0),
      0,
    );

    const prevMonthVolume = tradingData
      .slice(-60, -30)
      .reduce((sum, d) => sum + (d.volume ?? d.trading_volume ?? d.volume_total ?? 0), 0);

    const volumeChange =
      prevMonthVolume > 0 ? (monthlyVolume - prevMonthVolume) / prevMonthVolume : 0;

    return {
      latestPrice,
      priceChange,
      monthlyVolume,
      yearlyVolume,
      volumeChange,
      yearlyChange: 0,
    };
  }, [tradingData]);

  // Derive market ranking from map data
  const topMarkets = useMemo(() => {
    if (!mapData || mapData.length === 0) return [];
    const totalVolume = mapData.reduce((s, d) => s + (d.volume ?? 0), 0);
    return mapData
      .map((d) => ({
        name: d.countyName ?? d.countyId ?? '-',
        avgPrice: d.avgPrice ?? 0,
        volume: d.volume ?? 0,
        share: totalVolume > 0 ? (d.volume ?? 0) / totalVolume : 0,
      }))
      .sort((a, b) => b.volume - a.volume);
  }, [mapData]);

  const alerts = useAlerts(tradingData);

  // Chart data formatted for TimeSeriesChart
  const chartData = useMemo(
    () =>
      (tradingData || []).map((d) => ({
        date: d.date ?? d.period ?? d.month,
        value: d.value ?? d[metric] ?? d.avgPrice ?? d.avg_price ?? d.price_avg ?? 0,
      })),
    [tradingData, metric],
  );

  const isLoading = mapLoading || tradingLoading;
  const globalError = mapError || tradingError;

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">儀表板總覽</h1>
          <p className="mt-1 text-sm text-gray-500">
            台灣農產品各縣市交易與生產數據視覺化
          </p>
        </div>
        {selectedCrop && (
          <div className="flex items-center gap-2 rounded-lg bg-blue-50 px-3 py-1.5 text-sm text-blue-700">
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v2.25m6.364.386l-1.591 1.591M21 12h-2.25m-.386 6.364l-1.591-1.591M12 18.75V21m-4.773-4.227l-1.591 1.591M5.25 12H3m4.227-4.773L5.636 5.636M15.75 12a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0z" />
            </svg>
            目前作物: <span className="font-semibold">{selectedCropLabel || selectedCrop}</span>
          </div>
        )}
      </div>

      {/* Global error banner */}
      {globalError && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          <div className="flex items-center gap-2">
            <svg className="h-5 w-5 shrink-0 text-red-500" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z" clipRule="evenodd" />
            </svg>
            {globalError}
          </div>
        </div>
      )}

      {/* Row 1: Summary KPI cards */}
      <SummaryCards data={summaryData} loading={isLoading} />

      {/* Row 2: Two-column layout */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        {/* Left column: chart + table + alerts */}
        <div className="space-y-6 lg:col-span-7">
          <div className="rounded-xl border border-gray-100 bg-white p-5 shadow-sm">
            <TimeSeriesChart
              data={chartData}
              metric={metric}
              title={`${selectedCropLabel || selectedCrop || '農產品'}${METRIC_LABELS[metric] ?? ''}趨勢`}
              height={360}
              color="#3b82f6"
            />
          </div>

          <TopMarketsTable markets={topMarkets} loading={isLoading} />

          <RecentAlerts alerts={alerts} loading={isLoading} maxHeight={300} />
        </div>

        {/* Right column: map + county detail (sticky) */}
        <div className="order-first space-y-4 lg:order-none lg:col-span-5 lg:sticky lg:top-24 lg:self-start">
          <div className="rounded-xl border border-gray-100 bg-white p-4 shadow-sm">
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-sm font-semibold text-gray-700">
                各縣市{METRIC_LABELS[metric] ?? '數據'}分佈
              </h3>
              <span className="text-xs text-gray-400">
                {dateRange.startDate} ~ {dateRange.endDate}
              </span>
            </div>
            <TaiwanMap data={mapData} metric={metric} />
          </div>

          {selectedCounty && (
            <CountyDetailPanel
              county={selectedCounty}
              mapData={mapData}
              onClose={clearSelection}
            />
          )}
        </div>
      </div>
    </div>
  );
}
