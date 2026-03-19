import { useCallback, useMemo } from 'react';
import { format, subMonths, subYears, isSameDay, parseISO } from 'date-fns';
import useFilterStore from '../../stores/useFilterStore';

/**
 * Quick-range presets: label + generator returning { startDate, endDate }.
 */
const PRESETS = [
  { label: '近1月', key: '1m', fn: () => makeRange(subMonths, 1) },
  { label: '近3月', key: '3m', fn: () => makeRange(subMonths, 3) },
  { label: '近6月', key: '6m', fn: () => makeRange(subMonths, 6) },
  { label: '近1年', key: '1y', fn: () => makeRange(subYears, 1) },
  { label: '近3年', key: '3y', fn: () => makeRange(subYears, 3) },
];

function makeRange(subtractFn, amount) {
  const today = new Date();
  const start = subtractFn(today, amount);
  return {
    startDate: format(start, 'yyyy-MM-dd'),
    endDate: format(today, 'yyyy-MM-dd'),
  };
}

/**
 * Detect which preset (if any) matches the current dateRange.
 * Returns the preset key or 'custom'.
 */
function detectActivePreset(dateRange) {
  for (const preset of PRESETS) {
    const range = preset.fn();
    try {
      const startMatch = isSameDay(parseISO(dateRange.startDate), parseISO(range.startDate));
      const endMatch = isSameDay(parseISO(dateRange.endDate), parseISO(range.endDate));
      if (startMatch && endMatch) return preset.key;
    } catch {
      // invalid date string — skip
    }
  }
  return 'custom';
}

/**
 * Date range picker with start/end inputs and quick preset buttons.
 */
export default function DateRangePicker({ compact = false }) {
  const dateRange = useFilterStore((s) => s.dateRange);
  const setDateRange = useFilterStore((s) => s.setDateRange);

  const handleStartChange = useCallback(
    (e) => setDateRange({ startDate: e.target.value }),
    [setDateRange],
  );

  const handleEndChange = useCallback(
    (e) => setDateRange({ endDate: e.target.value }),
    [setDateRange],
  );

  const applyPreset = useCallback(
    (fn) => setDateRange(fn()),
    [setDateRange],
  );

  const activePreset = useMemo(() => detectActivePreset(dateRange), [dateRange]);

  const handlePresetSelect = useCallback(
    (e) => {
      const key = e.target.value;
      if (key === 'custom') return;
      const preset = PRESETS.find((p) => p.key === key);
      if (preset) applyPreset(preset.fn);
    },
    [applyPreset],
  );

  if (compact) {
    return (
      <div className="flex items-center gap-2">
        {/* Preset dropdown */}
        <select
          value={activePreset}
          onChange={handlePresetSelect}
          className={[
            'appearance-none rounded-lg border-0 bg-sky-50/60 text-sky-700',
            'font-medium px-2.5 py-1.5 text-sm cursor-pointer transition',
            'hover:bg-sky-100/80 focus:ring-2 focus:ring-sky-500/20 focus:outline-none',
          ].join(' ')}
        >
          {PRESETS.map((p) => (
            <option key={p.key} value={p.key}>{p.label}</option>
          ))}
          <option value="custom">自訂</option>
        </select>

        {/* Date inputs */}
        <div className="flex items-center gap-1 rounded-lg bg-gray-50 px-2">
          <input
            type="date"
            value={dateRange.startDate}
            onChange={handleStartChange}
            max={dateRange.endDate}
            className="w-28 border-0 bg-transparent py-1.5 text-sm text-gray-700 focus:ring-0 focus:outline-none"
          />
          <span className="text-xs text-gray-400">~</span>
          <input
            type="date"
            value={dateRange.endDate}
            onChange={handleEndChange}
            min={dateRange.startDate}
            className="w-28 border-0 bg-transparent py-1.5 text-sm text-gray-700 focus:ring-0 focus:outline-none"
          />
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      <span className="text-xs font-medium text-gray-500 tracking-wide">
        日期範圍
      </span>

      {/* Date inputs */}
      <div className="flex items-center gap-2">
        <input
          type="date"
          value={dateRange.startDate}
          onChange={handleStartChange}
          max={dateRange.endDate}
          className={[
            'w-full rounded-lg border border-gray-300 bg-white',
            'px-3 py-2 text-sm text-gray-700',
            'shadow-sm transition',
            'hover:border-gray-400 focus:border-sky-500 focus:ring-2 focus:ring-sky-500/20 focus:outline-none',
          ].join(' ')}
        />

        <span className="shrink-0 text-xs text-gray-400">至</span>

        <input
          type="date"
          value={dateRange.endDate}
          onChange={handleEndChange}
          min={dateRange.startDate}
          className={[
            'w-full rounded-lg border border-gray-300 bg-white',
            'px-3 py-2 text-sm text-gray-700',
            'shadow-sm transition',
            'hover:border-gray-400 focus:border-sky-500 focus:ring-2 focus:ring-sky-500/20 focus:outline-none',
          ].join(' ')}
        />
      </div>

      {/* Preset buttons */}
      <div className="flex flex-wrap gap-1.5">
        {PRESETS.map((preset) => (
          <button
            key={preset.key}
            type="button"
            onClick={() => applyPreset(preset.fn)}
            className={[
              'rounded-md border border-gray-200 bg-gray-50 px-2.5 py-1 text-xs font-medium text-gray-600',
              'transition hover:bg-sky-50 hover:border-sky-300 hover:text-sky-700',
              'active:scale-95',
              'focus:outline-none focus:ring-2 focus:ring-sky-500/20',
            ].join(' ')}
          >
            {preset.label}
          </button>
        ))}
      </div>
    </div>
  );
}
