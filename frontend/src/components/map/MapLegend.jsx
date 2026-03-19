import { useRef, useEffect } from 'react';
import * as d3 from 'd3';
import { METRIC_LABELS } from '../../utils/constants';

const LEGEND_WIDTH = 200;
const LEGEND_HEIGHT = 12;

/**
 * Gradient color legend for the choropleth map.
 *
 * Props:
 *  - domain:      [min, max] numeric tuple
 *  - metric:      string metric key
 *  - formatValue: function to format a numeric value for display
 */
export default function MapLegend({ domain = [0, 0], metric, formatValue }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const w = canvas.width;
    const h = canvas.height;

    // Draw the gradient
    for (let i = 0; i < w; i++) {
      const t = i / (w - 1);
      ctx.fillStyle = d3.interpolateYlOrRd(t);
      ctx.fillRect(i, 0, 1, h);
    }
  }, []);

  const [min, max] = domain;
  const hasData = min !== max || min !== 0;
  const label = METRIC_LABELS[metric] || metric || '';

  return (
    <div className="mt-4 flex flex-col items-center gap-1.5">
      {label && (
        <span className="text-xs font-medium text-gray-600">{label}</span>
      )}

      <div className="flex items-center gap-2">
        <span className="text-xs tabular-nums text-gray-500">
          {hasData ? formatValue(min) : '-'}
        </span>

        <canvas
          ref={canvasRef}
          width={LEGEND_WIDTH}
          height={LEGEND_HEIGHT}
          className="rounded-sm"
          style={{ width: LEGEND_WIDTH, height: LEGEND_HEIGHT }}
        />

        <span className="text-xs tabular-nums text-gray-500">
          {hasData ? formatValue(max) : '-'}
        </span>
      </div>

      {!hasData && (
        <span className="text-xs text-gray-400">尚無資料</span>
      )}
    </div>
  );
}
