import { useEffect, useState, useRef, useMemo } from 'react';
import * as d3 from 'd3';
import useMapStore from '../../stores/useMapStore';
import useFilterStore from '../../stores/useFilterStore';
import { getMarkets } from '../../api/regions';
import { getMarketTimeSeries } from '../../api/trading';
import { METRIC_LABELS } from '../../utils/constants';
import { formatNumber, formatCurrency } from '../../utils/formatters';

/**
 * Tiny sparkline chart rendered with D3 inside a small SVG.
 */
function MiniTrendChart({ data, metric }) {
  const svgRef = useRef(null);
  const width = 260;
  const height = 80;
  const margin = { top: 4, right: 4, bottom: 4, left: 4 };

  useEffect(() => {
    if (!svgRef.current || !Array.isArray(data) || data.length < 2) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const innerW = width - margin.left - margin.right;
    const innerH = height - margin.top - margin.bottom;

    const values = data.map((d) => d[metric] ?? d.value ?? 0);
    const xScale = d3.scaleLinear().domain([0, values.length - 1]).range([0, innerW]);
    const yScale = d3
      .scaleLinear()
      .domain([d3.min(values) * 0.95, d3.max(values) * 1.05])
      .range([innerH, 0]);

    const line = d3
      .line()
      .x((_, i) => xScale(i))
      .y((d) => yScale(d))
      .curve(d3.curveMonotoneX);

    const area = d3
      .area()
      .x((_, i) => xScale(i))
      .y0(innerH)
      .y1((d) => yScale(d))
      .curve(d3.curveMonotoneX);

    const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

    // Gradient fill
    const gradientId = 'mini-trend-grad';
    const defs = svg.append('defs');
    const gradient = defs
      .append('linearGradient')
      .attr('id', gradientId)
      .attr('x1', 0)
      .attr('y1', 0)
      .attr('x2', 0)
      .attr('y2', 1);
    gradient.append('stop').attr('offset', '0%').attr('stop-color', '#059669').attr('stop-opacity', 0.3);
    gradient.append('stop').attr('offset', '100%').attr('stop-color', '#059669').attr('stop-opacity', 0.02);

    g.append('path').datum(values).attr('d', area).attr('fill', `url(#${gradientId})`);

    g.append('path')
      .datum(values)
      .attr('d', line)
      .attr('fill', 'none')
      .attr('stroke', '#059669')
      .attr('stroke-width', 2);

    // End dot
    g.append('circle')
      .attr('cx', xScale(values.length - 1))
      .attr('cy', yScale(values[values.length - 1]))
      .attr('r', 3)
      .attr('fill', '#059669');
  }, [data, metric]);

  if (!Array.isArray(data) || data.length < 2) {
    return (
      <div className="flex h-20 items-center justify-center text-xs text-gray-400">
        暫無趨勢資料
      </div>
    );
  }

  return <svg ref={svgRef} viewBox={`0 0 ${width} ${height}`} className="w-full" />;
}

/**
 * Slide-out detail panel shown when a county is selected on the map.
 */
export default function CountyDetail() {
  const { selectedCounty, setSelectedCounty } = useMapStore();
  const { selectedCrop, dateRange, metric } = useFilterStore();

  const [markets, setMarkets] = useState([]);
  const [trendData, setTrendData] = useState([]);
  const [loading, setLoading] = useState(false);

  /* ---- Fetch markets for the selected county ---- */
  useEffect(() => {
    if (!selectedCounty) return;
    let cancelled = false;

    getMarkets({ county: selectedCounty })
      .then((res) => {
        if (!cancelled) setMarkets(Array.isArray(res) ? res : []);
      })
      .catch(() => {
        if (!cancelled) setMarkets([]);
      });

    return () => { cancelled = true; };
  }, [selectedCounty]);

  /* ---- Fetch trend data ---- */
  useEffect(() => {
    if (!selectedCounty || !selectedCrop) {
      setTrendData([]);
      return;
    }
    let cancelled = false;
    setLoading(true);

    getMarketTimeSeries({
      crop: selectedCrop,
      market: selectedCounty,
      startDate: dateRange.startDate,
      endDate: dateRange.endDate,
      granularity: 'monthly',
    })
      .then((res) => {
        if (!cancelled) setTrendData(Array.isArray(res) ? res : []);
      })
      .catch(() => {
        if (!cancelled) setTrendData([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, [selectedCounty, selectedCrop, dateRange]);

  if (!selectedCounty) return null;

  return (
    <div className="animate-slide-in rounded-xl border border-gray-200 bg-white shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-gray-100 px-5 py-4">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-emerald-100">
            <svg className="h-5 w-5 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
              <path strokeLinecap="round" strokeLinejoin="round" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900">{selectedCounty}</h3>
            <p className="text-xs text-gray-500">
              {METRIC_LABELS[metric] || metric}
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={() => setSelectedCounty(null)}
          className="rounded-lg p-2 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600"
          aria-label="Close panel"
        >
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Content */}
      <div className="grid gap-5 p-5 md:grid-cols-2">
        {/* Trend chart */}
        <div>
          <h4 className="mb-2 text-sm font-medium text-gray-700">歷史趨勢</h4>
          <div className="rounded-lg border border-gray-100 bg-gray-50 p-3">
            {loading ? (
              <div className="flex h-20 items-center justify-center">
                <span className="text-xs text-gray-400">載入中...</span>
              </div>
            ) : (
              <MiniTrendChart data={trendData} metric={metric} />
            )}
          </div>
          {!selectedCrop && (
            <p className="mt-2 text-xs text-amber-600">
              請先選擇農產品以查看趨勢資料
            </p>
          )}
        </div>

        {/* Markets list */}
        <div>
          <h4 className="mb-2 text-sm font-medium text-gray-700">
            相關市場
            <span className="ml-1.5 text-xs font-normal text-gray-400">
              ({markets.length})
            </span>
          </h4>
          <div className="max-h-48 space-y-1 overflow-y-auto rounded-lg border border-gray-100 bg-gray-50 p-2">
            {markets.length === 0 && (
              <p className="py-3 text-center text-xs text-gray-400">暫無市場資料</p>
            )}
            {markets.map((m, i) => {
              const name = m.market_name || m.name || `市場 ${i + 1}`;
              return (
                <div
                  key={m.id || name}
                  className="flex items-center gap-2 rounded-md px-3 py-2 text-sm text-gray-700 transition-colors hover:bg-white"
                >
                  <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-400" />
                  {name}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
