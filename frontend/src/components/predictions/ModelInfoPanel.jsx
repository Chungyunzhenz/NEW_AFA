import { useMemo } from 'react';
import { formatNumber, formatPercent, formatDate } from '../../utils/formatters';

function MetricBar({ value, max, color }) {
  const pct = max > 0 ? Math.min((value / max) * 100, 100) : 0;
  return (
    <div className="h-2 w-full overflow-hidden rounded-full bg-gray-100">
      <div
        className={`h-full rounded-full transition-all duration-500 ${color}`}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

function ActiveIndicator({ active }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium ${
        active
          ? 'bg-emerald-50 text-emerald-700'
          : 'bg-gray-50 text-gray-500'
      }`}
    >
      <span
        className={`h-1.5 w-1.5 rounded-full ${
          active ? 'bg-emerald-500 animate-pulse' : 'bg-gray-300'
        }`}
      />
      {active ? '使用中' : '停用'}
    </span>
  );
}

/**
 * Model performance information panel showing metrics and ensemble weights.
 *
 * @param {Object}   props
 * @param {Array}    props.modelInfo  - Array of {
 *   name, mae, rmse, mape, weight, active, trainingDate, dataSize
 * }
 * @param {boolean}  [props.loading=false]
 */
export default function ModelInfoPanel({ modelInfo = [], loading = false }) {
  // Compute maxima for relative bar charts
  const maxValues = useMemo(() => {
    if (!modelInfo.length) return { mae: 1, rmse: 1, mape: 1 };
    return {
      mae: Math.max(...modelInfo.map((m) => m.mae || 0), 0.01),
      rmse: Math.max(...modelInfo.map((m) => m.rmse || 0), 0.01),
      mape: Math.max(...modelInfo.map((m) => m.mape || 0), 0.01),
    };
  }, [modelInfo]);

  const totalWeight = useMemo(
    () => modelInfo.reduce((sum, m) => sum + (m.weight || 0), 0),
    [modelInfo],
  );

  const latestTraining = useMemo(() => {
    const dates = modelInfo
      .filter((m) => m.trainingDate)
      .map((m) => new Date(m.trainingDate));
    if (!dates.length) return null;
    return new Date(Math.max(...dates));
  }, [modelInfo]);

  const totalData = useMemo(
    () => modelInfo.reduce((sum, m) => sum + (m.dataSize || 0), 0),
    [modelInfo],
  );

  if (loading) {
    return (
      <div className="rounded-xl border border-gray-100 bg-white shadow-sm">
        <div className="border-b border-gray-100 px-6 py-4">
          <div className="h-5 w-36 animate-pulse rounded bg-gray-200" />
        </div>
        <div className="p-6">
          <div className="space-y-4">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="h-16 animate-pulse rounded-lg bg-gray-100" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (!modelInfo.length) {
    return (
      <div className="rounded-xl border border-gray-100 bg-white p-6 shadow-sm">
        <div className="flex h-32 items-center justify-center text-sm text-gray-400">
          <div className="text-center">
            <svg className="mx-auto h-10 w-10 text-gray-300" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0112 15a9.065 9.065 0 00-6.23.693L5 14.5m14.8.8l1.402 1.402c1.232 1.232.65 3.318-1.067 3.611A48.309 48.309 0 0112 21c-2.773 0-5.491-.235-8.135-.687-1.718-.293-2.3-2.379-1.067-3.61L5 14.5" />
            </svg>
            <p className="mt-2">暫無模型資訊</p>
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
          <h3 className="text-base font-semibold text-gray-800">模型資訊</h3>
          <p className="mt-0.5 text-xs text-gray-400">
            各模型效能指標與集成權重
          </p>
        </div>
        <div className="flex items-center gap-4 text-xs text-gray-500">
          {latestTraining && (
            <span>最後訓練: {formatDate(latestTraining)}</span>
          )}
          {totalData > 0 && (
            <span>總資料量: {formatNumber(totalData)} 筆</span>
          )}
        </div>
      </div>

      {/* Metrics table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100 bg-gray-50/60">
              <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                模型
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                狀態
              </th>
              <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">
                MAE
              </th>
              <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">
                RMSE
              </th>
              <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">
                MAPE
              </th>
              <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">
                權重
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {modelInfo.map((model) => (
              <tr
                key={model.name}
                className={`transition-colors hover:bg-blue-50/30 ${
                  model.active ? 'bg-emerald-50/20' : ''
                }`}
              >
                <td className="px-6 py-3.5">
                  <div className="font-medium text-gray-800">{model.name}</div>
                  {model.trainingDate && (
                    <div className="mt-0.5 text-xs text-gray-400">
                      訓練於 {formatDate(model.trainingDate)}
                    </div>
                  )}
                </td>
                <td className="px-4 py-3.5">
                  <ActiveIndicator active={model.active} />
                </td>
                <td className="px-4 py-3.5 text-right">
                  <div className="space-y-1">
                    <span className="tabular-nums text-gray-700">
                      {formatNumber(model.mae, 2)}
                    </span>
                    <MetricBar value={model.mae} max={maxValues.mae} color="bg-blue-400" />
                  </div>
                </td>
                <td className="px-4 py-3.5 text-right">
                  <div className="space-y-1">
                    <span className="tabular-nums text-gray-700">
                      {formatNumber(model.rmse, 2)}
                    </span>
                    <MetricBar value={model.rmse} max={maxValues.rmse} color="bg-purple-400" />
                  </div>
                </td>
                <td className="px-4 py-3.5 text-right">
                  <div className="space-y-1">
                    <span className="tabular-nums text-gray-700">
                      {(model.mape ?? 0).toFixed(1)}%
                    </span>
                    <MetricBar value={model.mape} max={maxValues.mape} color="bg-amber-400" />
                  </div>
                </td>
                <td className="px-4 py-3.5 text-right">
                  <span className="tabular-nums font-semibold text-gray-800">
                    {totalWeight > 0
                      ? formatPercent(model.weight / totalWeight)
                      : '-'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Ensemble weights visualization */}
      <div className="border-t border-gray-100 px-6 py-5">
        <h4 className="mb-3 text-sm font-semibold text-gray-700">集成權重分佈</h4>
        <div className="space-y-3">
          {modelInfo
            .filter((m) => m.weight > 0)
            .sort((a, b) => (b.weight || 0) - (a.weight || 0))
            .map((model) => {
              const pct = totalWeight > 0 ? (model.weight / totalWeight) * 100 : 0;
              return (
                <div key={model.name} className="flex items-center gap-3">
                  <span className="w-28 shrink-0 truncate text-sm text-gray-600">
                    {model.name}
                  </span>
                  <div className="flex-1">
                    <div className="h-5 w-full overflow-hidden rounded-full bg-gray-100">
                      <div
                        className="flex h-full items-center rounded-full bg-gradient-to-r from-blue-500 to-indigo-500 transition-all duration-700"
                        style={{ width: `${pct}%` }}
                      >
                        {pct > 15 && (
                          <span className="pl-2 text-xs font-semibold text-white">
                            {pct.toFixed(1)}%
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                  {pct <= 15 && (
                    <span className="w-14 text-right text-xs tabular-nums text-gray-500">
                      {pct.toFixed(1)}%
                    </span>
                  )}
                </div>
              );
            })}
        </div>
      </div>
    </div>
  );
}
