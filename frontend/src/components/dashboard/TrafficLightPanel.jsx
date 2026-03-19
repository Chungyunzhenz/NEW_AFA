import useTrafficLight from '../../hooks/useTrafficLight';
import useFilterStore from '../../stores/useFilterStore';
import {
  TRAFFIC_SIGNALS,
  TRAFFIC_SIGNAL_LABELS,
  TRAFFIC_THRESHOLDS,
} from '../../utils/constants';

const DOT_COLORS = {
  [TRAFFIC_SIGNALS.GREEN]: 'bg-emerald-500',
  [TRAFFIC_SIGNALS.YELLOW]: 'bg-amber-500',
  [TRAFFIC_SIGNALS.RED]: 'bg-red-500',
  [TRAFFIC_SIGNALS.UNKNOWN]: 'bg-gray-400',
};

const TEXT_COLORS = {
  [TRAFFIC_SIGNALS.GREEN]: 'text-emerald-700',
  [TRAFFIC_SIGNALS.YELLOW]: 'text-amber-700',
  [TRAFFIC_SIGNALS.RED]: 'text-red-700',
  [TRAFFIC_SIGNALS.UNKNOWN]: 'text-gray-500',
};

const BG_COLORS = {
  [TRAFFIC_SIGNALS.GREEN]: 'bg-emerald-50',
  [TRAFFIC_SIGNALS.YELLOW]: 'bg-amber-50',
  [TRAFFIC_SIGNALS.RED]: 'bg-red-50',
  [TRAFFIC_SIGNALS.UNKNOWN]: 'bg-gray-50',
};

const INDICATOR_CONFIG = [
  { key: 'supply_index', label: '供給指數', unit: '' },
  { key: 'price_drop_pct', label: '價格跌幅', unit: '%' },
  { key: 'area_growth_pct', label: '面積成長率', unit: '%' },
];

export default function TrafficLightPanel() {
  const { metrics, signals, overall, loading, error } = useTrafficLight();
  const selectedCrop = useFilterStore((s) => s.selectedCrop);
  const selectedCropLabel = useFilterStore((s) => s.selectedCropLabel);

  if (!selectedCrop) {
    return (
      <div className="rounded-xl border border-gray-100 bg-white p-5 shadow-sm">
        <h2 className="text-base font-semibold text-gray-800">產銷預警燈號</h2>
        <p className="mt-2 text-sm text-gray-400">請先選擇作物以查看燈號預警</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="rounded-xl border border-gray-100 bg-white p-5 shadow-sm">
        <h2 className="text-base font-semibold text-gray-800">產銷預警燈號</h2>
        <div className="mt-4 flex items-center gap-3">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-gray-200 border-t-emerald-600" />
          <span className="text-sm text-gray-500">載入燈號資料中...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl border border-gray-100 bg-white p-5 shadow-sm">
        <h2 className="text-base font-semibold text-gray-800">產銷預警燈號</h2>
        <p className="mt-2 text-sm text-red-500">載入失敗：{error}</p>
      </div>
    );
  }

  const overallSignal = overall || TRAFFIC_SIGNALS.UNKNOWN;

  return (
    <div className="rounded-xl border border-gray-100 bg-white p-5 shadow-sm">
      {/* Header with overall signal */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <h2 className="text-base font-semibold text-gray-800">產銷預警燈號</h2>
          {selectedCropLabel && (
            <span className="rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-medium text-blue-700">
              {selectedCropLabel}
            </span>
          )}
        </div>
        <div className={`flex items-center gap-2 rounded-full px-3 py-1.5 ${BG_COLORS[overallSignal]}`}>
          <span className={`h-3.5 w-3.5 rounded-full ${DOT_COLORS[overallSignal]} shadow-sm`} />
          <span className={`text-sm font-semibold ${TEXT_COLORS[overallSignal]}`}>
            {TRAFFIC_SIGNAL_LABELS[overallSignal]}
          </span>
        </div>
      </div>

      {/* Three indicator cards */}
      <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
        {INDICATOR_CONFIG.map(({ key, label, unit }) => {
          const signal = signals?.[key] || TRAFFIC_SIGNALS.UNKNOWN;
          const value = metrics?.[key];
          return (
            <div
              key={key}
              className={`flex items-center gap-3 rounded-lg border p-3 ${
                signal === TRAFFIC_SIGNALS.RED
                  ? 'border-red-200 bg-red-50/50'
                  : signal === TRAFFIC_SIGNALS.YELLOW
                  ? 'border-amber-200 bg-amber-50/50'
                  : signal === TRAFFIC_SIGNALS.GREEN
                  ? 'border-emerald-200 bg-emerald-50/50'
                  : 'border-gray-100 bg-gray-50/50'
              }`}
            >
              <span className={`h-3 w-3 shrink-0 rounded-full ${DOT_COLORS[signal]}`} />
              <div className="min-w-0 flex-1">
                <p className="text-xs font-medium text-gray-500">{label}</p>
                <p className="mt-0.5 text-sm font-semibold tabular-nums text-gray-800">
                  {value != null ? `${value}${unit}` : '—'}
                </p>
              </div>
              <span className={`shrink-0 text-xs font-medium ${TEXT_COLORS[signal]}`}>
                {TRAFFIC_SIGNAL_LABELS[signal]}
              </span>
            </div>
          );
        })}
      </div>

      {/* Threshold reference table */}
      <details className="mt-4">
        <summary className="cursor-pointer text-xs font-medium text-gray-400 hover:text-gray-600">
          查看門檻值定義
        </summary>
        <div className="mt-2 overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-gray-100">
                <th className="py-1.5 pr-4 text-left font-medium text-gray-500">指標</th>
                <th className="py-1.5 px-3 text-center font-medium text-emerald-600">綠燈</th>
                <th className="py-1.5 px-3 text-center font-medium text-amber-600">黃燈</th>
                <th className="py-1.5 px-3 text-center font-medium text-red-600">紅燈</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              <tr>
                <td className="py-1.5 pr-4 text-gray-700">供給指數</td>
                <td className="py-1.5 px-3 text-center text-gray-600">≤ {TRAFFIC_THRESHOLDS.supply_index.green}</td>
                <td className="py-1.5 px-3 text-center text-gray-600">≤ {TRAFFIC_THRESHOLDS.supply_index.yellow}</td>
                <td className="py-1.5 px-3 text-center text-gray-600">&gt; {TRAFFIC_THRESHOLDS.supply_index.yellow}</td>
              </tr>
              <tr>
                <td className="py-1.5 pr-4 text-gray-700">價格跌幅 %</td>
                <td className="py-1.5 px-3 text-center text-gray-600">≤ {TRAFFIC_THRESHOLDS.price_drop_pct.green}%</td>
                <td className="py-1.5 px-3 text-center text-gray-600">≤ {TRAFFIC_THRESHOLDS.price_drop_pct.yellow}%</td>
                <td className="py-1.5 px-3 text-center text-gray-600">&gt; {TRAFFIC_THRESHOLDS.price_drop_pct.yellow}%</td>
              </tr>
              <tr>
                <td className="py-1.5 pr-4 text-gray-700">面積成長率 %</td>
                <td className="py-1.5 px-3 text-center text-gray-600">≤ {TRAFFIC_THRESHOLDS.area_growth_pct.green}%</td>
                <td className="py-1.5 px-3 text-center text-gray-600">≤ {TRAFFIC_THRESHOLDS.area_growth_pct.yellow}%</td>
                <td className="py-1.5 px-3 text-center text-gray-600">&gt; {TRAFFIC_THRESHOLDS.area_growth_pct.yellow}%</td>
              </tr>
            </tbody>
          </table>
        </div>
      </details>
    </div>
  );
}
