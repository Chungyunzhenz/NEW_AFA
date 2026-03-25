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
export default function CountyTooltip({ show, x, y, county, avgPrice, volume, productionTonnes, tempAvg, rainfallMm }) {
  const style = useMemo(
    () => ({
      left: x + 16,
      top: y - 12,
      maxWidth: 240,
    }),
    [x, y],
  );

  if (!show) return null;

  const hasData = avgPrice > 0 || volume > 0;

  return (
    <div
      className="county-tooltip pointer-events-none absolute z-50 rounded-lg border border-gray-200 bg-white px-3 py-2 shadow-lg transition-opacity duration-100"
      style={style}
    >
      {/* Arrow */}
      <div className="absolute -left-1.5 top-3 h-3 w-3 rotate-45 border-b border-l border-gray-200 bg-white" />

      <p className="text-sm font-semibold text-gray-800">{county}</p>

      {hasData ? (
        <dl className="mt-1 space-y-0.5">
          <div className="flex items-baseline justify-between gap-3">
            <dt className="text-xs text-gray-500">平均價格</dt>
            <dd className="text-sm font-medium tabular-nums text-emerald-700">{formatCurrency(avgPrice, 1)}</dd>
          </div>
          <div className="flex items-baseline justify-between gap-3">
            <dt className="text-xs text-gray-500">交易量</dt>
            <dd className="text-sm font-medium tabular-nums text-emerald-700">{formatNumber(volume)} 公斤</dd>
          </div>
          {productionTonnes > 0 && (
            <div className="flex items-baseline justify-between gap-3">
              <dt className="text-xs text-gray-500">產量</dt>
              <dd className="text-sm font-medium tabular-nums text-emerald-700">{formatNumber(productionTonnes)} 公噸</dd>
            </div>
          )}
          {tempAvg != null && (
            <div className="flex items-baseline justify-between gap-3 border-t border-gray-100 pt-0.5 mt-0.5">
              <dt className="text-xs text-gray-500">平均氣溫</dt>
              <dd className="text-sm font-medium tabular-nums text-blue-600">{tempAvg}°C</dd>
            </div>
          )}
          {rainfallMm != null && (
            <div className="flex items-baseline justify-between gap-3">
              <dt className="text-xs text-gray-500">近月降雨</dt>
              <dd className="text-sm font-medium tabular-nums text-blue-600">{formatNumber(rainfallMm)} mm</dd>
            </div>
          )}
        </dl>
      ) : (
        <p className="mt-1 text-xs text-gray-400">此縣市暫無交易紀錄</p>
      )}
    </div>
  );
}
