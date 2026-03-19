import useFilterStore from '../../stores/useFilterStore';
import { GRANULARITIES } from '../../utils/constants';

/**
 * Options shown in the button group.
 * Using weekly, monthly, yearly as the three primary aggregation levels.
 */
const OPTIONS = [
  { value: GRANULARITIES.WEEKLY, label: '週' },
  { value: GRANULARITIES.MONTHLY, label: '月' },
  { value: GRANULARITIES.YEARLY, label: '年' },
];

/**
 * Button group for selecting temporal granularity.
 */
export default function GranularitySelector({ compact = false }) {
  const granularity = useFilterStore((s) => s.granularity);
  const setGranularity = useFilterStore((s) => s.setGranularity);

  if (compact) {
    return (
      <div className="inline-flex items-center rounded-lg bg-gray-100 p-0.5">
        {OPTIONS.map((opt) => {
          const isActive = granularity === opt.value;
          return (
            <button
              key={opt.value}
              type="button"
              onClick={() => setGranularity(opt.value)}
              className={[
                'px-3 py-1.5 text-sm font-medium transition-all',
                'focus:outline-none focus:z-10',
                'active:scale-[0.97]',
                isActive
                  ? 'rounded-md bg-white text-emerald-700 shadow-sm'
                  : 'text-gray-500 hover:text-gray-700',
              ].join(' ')}
            >
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
        時間粒度
      </span>

      <div className="inline-flex rounded-lg border border-gray-300 bg-white shadow-sm overflow-hidden">
        {OPTIONS.map((opt, idx) => {
          const isActive = granularity === opt.value;

          return (
            <button
              key={opt.value}
              type="button"
              onClick={() => setGranularity(opt.value)}
              className={[
                'relative px-4 py-2 text-sm font-medium transition',
                'focus:outline-none focus:z-10 focus:ring-2 focus:ring-sky-500/20',
                'active:scale-[0.97]',
                idx > 0 ? 'border-l border-gray-300' : '',
                isActive
                  ? 'bg-sky-500 text-white shadow-inner'
                  : 'bg-white text-gray-600 hover:bg-gray-50',
              ].join(' ')}
            >
              {opt.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
