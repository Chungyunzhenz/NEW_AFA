import { useState, useMemo } from 'react';
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
  BarChart,
  Bar,
} from 'recharts';
import useFilterStore from '../stores/useFilterStore';
import useMapStore from '../stores/useMapStore';
import usePredictions from '../hooks/usePredictions';
import useTradingData from '../hooks/useTradingData';
import useMapData from '../hooks/useMapData';
import ForecastPanel from '../components/predictions/ForecastPanel';
import ModelInfoPanel from '../components/predictions/ModelInfoPanel';
import { formatCurrency, formatNumber, formatDate } from '../utils/formatters';

/* ------------------------------------------------------------------ */
/*  Forecast chart: historical + prediction + confidence interval     */
/* ------------------------------------------------------------------ */
function ForecastChart({ historicalData, predictions, loading }) {
  const chartData = useMemo(() => {
    const hist = (historicalData || []).map((d) => ({
      date: d.date ?? d.period ?? d.month,
      actual: d.value ?? d.avgPrice ?? d.avg_price ?? null,
      predicted: null,
      ciUpper: null,
      ciLower: null,
    }));

    const pred = (Array.isArray(predictions) ? predictions : []).map((d) => ({
      date: d.date ?? d.forecastDate ?? d.forecast_date,
      actual: null,
      predicted: d.value ?? d.predicted ?? d.forecast_value ?? null,
      ciUpper: d.ciUpper ?? d.ci_upper ?? null,
      ciLower: d.ciLower ?? d.ci_lower ?? null,
    }));

    // Merge: connect the last actual point to the first prediction
    const merged = [...hist];
    if (hist.length > 0 && pred.length > 0) {
      const lastActual = hist[hist.length - 1];
      merged.push({
        ...lastActual,
        predicted: lastActual.actual,
        ciUpper: lastActual.actual,
        ciLower: lastActual.actual,
      });
    }
    merged.push(...pred);
    return merged;
  }, [historicalData, predictions]);

  // Find the boundary between historical and forecast data
  const boundaryDate = useMemo(() => {
    if (!historicalData?.length) return null;
    const last = historicalData[historicalData.length - 1];
    return last?.date ?? last?.period ?? last?.month ?? null;
  }, [historicalData]);

  if (loading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-blue-200 border-t-blue-600" />
          <p className="text-sm text-gray-500">載入預測資料中...</p>
        </div>
      </div>
    );
  }

  if (!chartData.length) {
    return (
      <div className="flex h-96 items-center justify-center text-sm text-gray-400">
        <div className="text-center">
          <svg className="mx-auto h-12 w-12 text-gray-300" fill="none" viewBox="0 0 24 24" strokeWidth={1} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 3v11.25A2.25 2.25 0 006 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0118 16.5h-2.25m-7.5 0h7.5m-7.5 0l-1 3m8.5-3l1 3m0 0l.5 1.5m-.5-1.5h-9.5m0 0l-.5 1.5" />
          </svg>
          <p className="mt-3">請選擇作物以查看預測圖表</p>
        </div>
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={400}>
      <ComposedChart data={chartData} margin={{ top: 12, right: 24, left: 8, bottom: 8 }}>
        <defs>
          <linearGradient id="ciGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#818cf8" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#818cf8" stopOpacity={0.05} />
          </linearGradient>
        </defs>
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
          tick={{ fontSize: 12, fill: '#6b7280' }}
          tickFormatter={(v) => `$${formatNumber(v)}`}
          tickLine={false}
          axisLine={false}
          label={{ value: '價格 (NT$)', angle: -90, position: 'insideLeft', offset: -4, style: { fontSize: 12, fill: '#9ca3af' } }}
        />
        <Tooltip
          content={({ active, payload, label }) => {
            if (!active || !payload?.length) return null;
            const d = payload[0]?.payload;
            return (
              <div className="rounded-lg border border-gray-200 bg-white p-3 text-sm shadow-lg">
                <p className="mb-1.5 font-medium text-gray-700">{formatDate(label)}</p>
                {d?.actual != null && (
                  <p className="text-blue-600">實際值: {formatCurrency(d.actual, 1)}</p>
                )}
                {d?.predicted != null && (
                  <p className="text-indigo-600">預測值: {formatCurrency(d.predicted, 1)}</p>
                )}
                {d?.ciLower != null && d?.ciUpper != null && (
                  <p className="text-gray-400">
                    CI: {formatCurrency(d.ciLower, 1)} ~ {formatCurrency(d.ciUpper, 1)}
                  </p>
                )}
              </div>
            );
          }}
        />
        <Legend
          wrapperStyle={{ fontSize: 13 }}
          formatter={(v) =>
            v === 'actual' ? '實際價格' : v === 'predicted' ? '預測價格' : '信賴區間'
          }
        />

        {/* Confidence interval band */}
        <Area
          type="monotone"
          dataKey="ciUpper"
          stroke="none"
          fill="url(#ciGradient)"
          name="ciUpper"
          legendType="none"
        />
        <Area
          type="monotone"
          dataKey="ciLower"
          stroke="none"
          fill="#ffffff"
          name="ciLower"
          legendType="none"
        />

        {/* Boundary line */}
        {boundaryDate && (
          <ReferenceLine
            x={boundaryDate}
            stroke="#9ca3af"
            strokeDasharray="4 4"
            label={{ value: '預測起點', position: 'top', style: { fontSize: 11, fill: '#9ca3af' } }}
          />
        )}

        {/* Historical line */}
        <Line
          type="monotone"
          dataKey="actual"
          stroke="#3b82f6"
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4, fill: '#3b82f6' }}
          name="actual"
          connectNulls={false}
        />

        {/* Prediction line */}
        <Line
          type="monotone"
          dataKey="predicted"
          stroke="#6366f1"
          strokeWidth={2}
          strokeDasharray="6 3"
          dot={false}
          activeDot={{ r: 4, fill: '#6366f1' }}
          name="predicted"
          connectNulls={false}
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}

/* ------------------------------------------------------------------ */
/*  Model comparison chart                                            */
/* ------------------------------------------------------------------ */
function ModelComparisonChart({ modelInfo }) {
  const chartData = useMemo(() => {
    if (!modelInfo?.length) return [];
    return modelInfo.map((m) => ({
      name: m.name ?? 'Unknown',
      MSE: m.mse ?? 0,
      RMSE: m.rmse ?? 0,
      MAE: m.mae ?? 0,
      'R²': m.r_squared ?? 0,
    }));
  }, [modelInfo]);

  if (!chartData.length) {
    return (
      <div className="flex h-64 items-center justify-center text-sm text-gray-400">
        暫無模型比較資料
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={chartData} margin={{ top: 8, right: 24, left: 8, bottom: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis
          dataKey="name"
          tick={{ fontSize: 12, fill: '#6b7280' }}
          tickLine={false}
          axisLine={{ stroke: '#d1d5db' }}
        />
        <YAxis
          tick={{ fontSize: 12, fill: '#6b7280' }}
          tickLine={false}
          axisLine={false}
        />
        <Tooltip
          content={({ active, payload, label }) => {
            if (!active || !payload?.length) return null;
            return (
              <div className="rounded-lg border border-gray-200 bg-white p-3 text-sm shadow-lg">
                <p className="mb-1 font-semibold text-gray-700">{label}</p>
                {payload.map((p) => (
                  <p key={p.dataKey} style={{ color: p.color }}>
                    {p.dataKey}: {p.value.toFixed(4)}
                  </p>
                ))}
              </div>
            );
          }}
        />
        <Legend wrapperStyle={{ fontSize: 13 }} />
        <Bar dataKey="MSE" fill="#f97316" radius={[4, 4, 0, 0]} />
        <Bar dataKey="RMSE" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
        <Bar dataKey="MAE" fill="#3b82f6" radius={[4, 4, 0, 0]} />
        <Bar dataKey="R²" fill="#10b981" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

/* ------------------------------------------------------------------ */
/*  Forecast map placeholder                                          */
/* ------------------------------------------------------------------ */
function ForecastMapSection({ mapData, loading }) {
  return (
    <div className="rounded-xl border border-gray-100 bg-white p-5 shadow-sm">
      <h3 className="mb-4 text-base font-semibold text-gray-800">各縣市預測分佈</h3>
      <div className="flex h-64 flex-col items-center justify-center rounded-lg border border-dashed border-gray-300 bg-gradient-to-br from-indigo-50/50 to-purple-50/50">
        {loading ? (
          <div className="flex flex-col items-center gap-3">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-200 border-t-indigo-600" />
            <p className="text-sm text-gray-500">載入預測地圖...</p>
          </div>
        ) : (
          <>
            <svg className="h-12 w-12 text-indigo-300" fill="none" viewBox="0 0 24 24" strokeWidth={1} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 6.75V15m6-6v8.25m.503 3.498l4.875-2.437c.381-.19.622-.58.622-1.006V4.82c0-.836-.88-1.38-1.628-1.006l-3.869 1.934c-.317.159-.69.159-1.006 0L9.503 3.252a1.125 1.125 0 00-1.006 0L3.622 5.689C3.24 5.88 3 6.27 3 6.695V19.18c0 .836.88 1.38 1.628 1.006l3.869-1.934c.317-.159.69-.159 1.006 0l4.994 2.497c.317.158.69.158 1.006 0z" />
            </svg>
            <p className="mt-2 text-sm font-medium text-gray-500">預測分佈地圖</p>
            <p className="mt-1 text-xs text-gray-400">
              {mapData.length > 0 ? `${mapData.length} 筆縣市預測資料` : '請選擇作物以顯示預測地圖'}
            </p>
          </>
        )}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main Forecast Page                                                */
/* ------------------------------------------------------------------ */
export default function ForecastPage() {
  const { selectedCrop } = useFilterStore();
  const setMapLayer = useMapStore((s) => s.setMapLayer);

  const [horizon, setHorizon] = useState('7d');
  const horizonOptions = [
    { value: '7d', label: '7 天' },
    { value: '14d', label: '14 天' },
    { value: '30d', label: '30 天' },
  ];

  const { predictions, forecast, modelInfo, loading: predLoading, error: predError } =
    usePredictions({ horizon });

  const { data: historicalData, loading: histLoading } = useTradingData();

  // Switch map to prediction mode and get prediction map data
  const { mapData, loading: mapLoading } = useMapData();

  // Set map to prediction layer when on this page
  useState(() => {
    setMapLayer('prediction');
    return () => setMapLayer('trading');
  });

  const isLoading = predLoading || histLoading;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">預測結果</h1>
          <p className="mt-1 text-sm text-gray-500">
            AI 模型價格與產量預測
            {selectedCrop && (
              <span className="ml-2 font-medium text-blue-600">{selectedCrop}</span>
            )}
          </p>
        </div>

        {/* Horizon selector */}
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-500">預測期間:</span>
          <div className="flex items-center rounded-lg bg-gray-100 p-0.5">
            {horizonOptions.map((opt) => (
              <button
                key={opt.value}
                onClick={() => setHorizon(opt.value)}
                className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                  horizon === opt.value
                    ? 'bg-white text-indigo-700 shadow-sm'
                    : 'text-gray-600 hover:text-gray-800'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Error */}
      {predError && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          <div className="flex items-center gap-2">
            <svg className="h-5 w-5 shrink-0 text-red-500" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z" clipRule="evenodd" />
            </svg>
            {predError}
          </div>
        </div>
      )}

      {/* Forecast panel */}
      <ForecastPanel forecast={forecast} loading={predLoading} />

      {/* Forecast chart (historical + prediction + CI) */}
      <div className="rounded-xl border border-gray-100 bg-white p-5 shadow-sm">
        <h3 className="mb-4 text-base font-semibold text-gray-800">
          歷史價格與預測走勢
        </h3>
        <ForecastChart
          historicalData={historicalData}
          predictions={predictions}
          loading={isLoading}
        />
      </div>

      {/* Model comparison + model info row */}
      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <div className="rounded-xl border border-gray-100 bg-white p-5 shadow-sm">
          <h3 className="mb-4 text-base font-semibold text-gray-800">模型效能比較</h3>
          <ModelComparisonChart modelInfo={modelInfo} />
        </div>

        <ModelInfoPanel modelInfo={modelInfo} loading={predLoading} />
      </div>

      {/* Prediction map */}
      <ForecastMapSection mapData={mapData} loading={mapLoading} />
    </div>
  );
}
