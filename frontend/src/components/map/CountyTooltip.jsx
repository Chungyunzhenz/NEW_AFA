import { useMemo } from 'react';

/**
 * Floating tooltip that follows the mouse cursor over the map.
 *
 * Props:
 *  - show:        boolean  -- whether the tooltip is visible
 *  - x, y:        number   -- position relative to map container
 *  - county:      string   -- county name (Chinese)
 *  - value:       string   -- formatted metric value
 *  - metricLabel: string   -- human-readable label for the active metric
 */
export default function CountyTooltip({ show, x, y, county, value, metricLabel }) {
  const style = useMemo(
    () => ({
      left: x + 16,
      top: y - 12,
      // Prevent the tooltip from overflowing right edge
      maxWidth: 220,
    }),
    [x, y],
  );

  if (!show) return null;

  return (
    <div
      className="county-tooltip pointer-events-none absolute z-50 rounded-lg border border-gray-200 bg-white px-3 py-2 shadow-lg transition-opacity duration-100"
      style={style}
    >
      {/* Arrow */}
      <div className="absolute -left-1.5 top-3 h-3 w-3 rotate-45 border-b border-l border-gray-200 bg-white" />

      <p className="text-sm font-semibold text-gray-800">{county}</p>

      <div className="mt-1 flex items-baseline gap-1.5">
        <span className="text-xs text-gray-500">{metricLabel}</span>
        <span className="text-sm font-medium text-emerald-700">{value}</span>
      </div>
    </div>
  );
}
