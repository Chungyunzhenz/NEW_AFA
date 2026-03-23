import { useMemo } from 'react';
import { formatCurrency, formatNumber } from '../../utils/formatters';

/**
 * Floating tooltip that follows the mouse cursor over the map.
 *
 * Props:
 *  - show:             boolean  -- whether the tooltip is visible
 *  - x, y:             number   -- position relative to map container
 *  - county:           string   -- county name (Chinese)
 *  - avgPrice:         number   -- average price
 *  - volume:           number   -- trading volume (kg)
 *  - productionTonnes: number   -- production (tonnes)
 */
export default function CountyTooltip({ show, x, y, county, avgPrice, volume, productionTonnes }) {
  const style = useMemo(
    () => ({
      left: x + 16,
      top: y - 12,
      maxWidth: 240,
    }),
    [x, y],
  );

  if (!show) return null;

  const rows = [
    { label: '平均價格', value: avgPrice ? formatCurrency(avgPrice, 1) : '—' },
    { label: '交易量', value: volume ? `${formatNumber(volume)} 公斤` : '—' },
    { label: '產量', value: productionTonnes ? `${formatNumber(productionTonnes)} 公噸` : '—' },
  ];

  return (
    <div
      className="county-tooltip pointer-events-none absolute z-50 rounded-lg border border-gray-200 bg-white px-3 py-2 shadow-lg transition-opacity duration-100"
      style={style}
    >
      {/* Arrow */}
      <div className="absolute -left-1.5 top-3 h-3 w-3 rotate-45 border-b border-l border-gray-200 bg-white" />

      <p className="text-sm font-semibold text-gray-800">{county}</p>

      <dl className="mt-1 space-y-0.5">
        {rows.map((r) => (
          <div key={r.label} className="flex items-baseline justify-between gap-3">
            <dt className="text-xs text-gray-500">{r.label}</dt>
            <dd className="text-sm font-medium tabular-nums text-emerald-700">{r.value}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
