import useFilterStore from '../../stores/useFilterStore';
import { METRICS } from '../../utils/constants';

/**
 * Three primary metric categories, each with a distinct accent colour.
 */
const OPTIONS = [
  {
    value: METRICS.AVG_PRICE,
    label: '價格',
    activeClasses: 'bg-sky-500 text-white shadow-inner',
    dotColor: '#0ea5e9',
  },
  {
    value: METRICS.TRADING_VOLUME,
    label: '交易量',
    activeClasses: 'bg-violet-500 text-white shadow-inner',
    dotColor: '#8b5cf6',
  },
  {
    value: METRICS.PRODUCTION_AMOUNT,
    label: '產量',
    activeClasses: 'bg-emerald-500 text-white shadow-inner',
    dotColor: '#10b981',
  },
];

/**
 * Button group for selecting the primary display metric.
 */
/**
 * Compact active classes for pill-style metric buttons.
 */
const COMPACT_ACTIVE = {
  [METRICS.AVG_PRICE]: 'bg-sky-50 text-sky-700 shadow-sm',
  [METRICS.TRADING_VOLUME]: 'bg-violet-50 text-violet-700 shadow-sm',
  [METRICS.PRODUCTION_AMOUNT]: 'bg-emerald-50 text-emerald-700 shadow-sm',
};

export default function MetricSelector({ compact = false }) {
  const metric = useFilterStore((s) => s.metric);
  const setMetric = useFilterStore((s) => s.setMetric);

  if (compact) {
    return (
      <div className="inline-flex items-center rounded-lg bg-gray-100 p-0.5">
        {OPTIONS.map((opt) => {
          const isActive = metric === opt.value;
          return (
            <button
              key={opt.value}
              type="button"
              onClick={() => setMetric(opt.value)}
              className={[
                'flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium transition-all',
                'focus:outline-none focus:z-10',
                'active:scale-[0.97]',
                isActive
                  ? `rounded-md ${COMPACT_ACTIVE[opt.value]}`
                  : 'text-gray-500 hover:text-gray-700',
              ].join(' ')}
            >
              <span
                className="h-2 w-2 rounded-full shrink-0"
                style={{ backgroundColor: opt.dotColor }}
              />
              {opt.label}
            </button>
          );
        })}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-1">
      <span className="text-xs font-medium text-gray-500 tracking-wide">
        指標
      </span>

      <div className="inline-flex rounded-lg border border-gray-300 bg-white shadow-sm overflow-hidden">
        {OPTIONS.map((opt, idx) => {
          const isActive = metric === opt.value;

          return (
            <button
              key={opt.value}
              type="button"
              onClick={() => setMetric(opt.value)}
              className={[
                'relative flex items-center gap-1.5 px-4 py-2 text-sm font-medium transition',
                'focus:outline-none focus:z-10 focus:ring-2 focus:ring-sky-500/20',
                'active:scale-[0.97]',
                idx > 0 ? 'border-l border-gray-300' : '',
                isActive
                  ? opt.activeClasses
                  : 'bg-white text-gray-600 hover:bg-gray-50',
              ].join(' ')}
            >
              <span
                className="h-2 w-2 rounded-full shrink-0"
                style={{
                  backgroundColor: isActive ? '#ffffff' : opt.dotColor,
                  opacity: isActive ? 0.7 : 1,
                }}
              />
              {opt.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
