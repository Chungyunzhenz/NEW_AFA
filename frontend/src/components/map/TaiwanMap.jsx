import { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import * as d3 from 'd3';
import * as topojson from 'topojson-client';
import { getGeoJSON } from '../../api/regions';
import useMapStore from '../../stores/useMapStore';
import { formatNumber, formatCurrency } from '../../utils/formatters';
import CountyTooltip from './CountyTooltip';
import MapLegend from './MapLegend';

const MAP_WIDTH = 500;
const MAP_HEIGHT = 700;
const NO_DATA_COLOR = '#e5e7eb'; // gray-200
const STROKE_COLOR = '#ffffff';
const STROKE_HOVER_COLOR = '#059669'; // emerald-600
const STROKE_SELECTED_COLOR = '#047857'; // emerald-700

// 正規化：臺→台 (統一用 GeoJSON 的寫法)
function normalizeName(name) {
  return name ? name.replace(/臺/g, '台') : '';
}

/**
 * Resolve the metric value from a county data record.
 * The API may return values under different key names depending on the metric.
 */
function resolveValue(record, metric) {
  if (!record) return null;
  // Direct key match
  if (record[metric] != null) return record[metric];
  // Common fallback fields
  if (record.value != null) return record.value;
  return null;
}

/**
 * Determine whether a metric represents a price (to format as currency).
 */
function isPriceMetric(metric) {
  return metric && metric.toLowerCase().includes('price');
}

/**
 * Format a value based on the metric type.
 */
function formatMetricValue(value, metric) {
  if (value == null) return '-';
  if (isPriceMetric(metric)) return formatCurrency(value, 1);
  return formatNumber(value);
}

/**
 * Core Taiwan choropleth map component.
 *
 * Props:
 *  - data: Array of county data records, each with at least `county_name_zh` and a metric field
 *  - metric: The active metric key (from METRICS constants)
 */
export default function TaiwanMap({ data = [], metric }) {
  const svgRef = useRef(null);
  const containerRef = useRef(null);
  const [geoData, setGeoData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [tooltip, setTooltip] = useState({ show: false, x: 0, y: 0, county: '', avgPrice: 0, volume: 0, productionTonnes: 0 });

  const { hoveredCounty, selectedCounty, setHoveredCounty, setSelectedCounty } = useMapStore();

  /* ---------------------------------------------------------------- */
  /*  1. Load TopoJSON on mount                                        */
  /* ---------------------------------------------------------------- */
  useEffect(() => {
    let cancelled = false;

    setLoading(true);
    setError(null);

    getGeoJSON()
      .then((topo) => {
        if (cancelled) return;

        let features;
        if (topo.type === 'Topology') {
          // Standard TopoJSON -> convert first object to GeoJSON
          const objectKey = Object.keys(topo.objects)[0];
          features = topojson.feature(topo, topo.objects[objectKey]);
        } else {
          // Already GeoJSON FeatureCollection
          features = topo;
        }
        setGeoData(features);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || 'Failed to load map data');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, []);

  /* ---------------------------------------------------------------- */
  /*  2. Build a lookup map: county_name_zh -> record                  */
  /* ---------------------------------------------------------------- */
  const dataMap = useMemo(() => {
    const map = new Map();
    if (!Array.isArray(data)) return map;
    data.forEach((d) => {
      const key = d.countyName || d.county_name_zh || d.county_name || d.county || d.name;
      if (key) map.set(normalizeName(key), d);
    });
    return map;
  }, [data]);

  /* ---------------------------------------------------------------- */
  /*  3. Build quantile color scale                                    */
  /* ---------------------------------------------------------------- */
  const colorScale = useMemo(() => {
    const values = [];
    if (Array.isArray(data)) {
      data.forEach((d) => {
        const v = resolveValue(d, metric);
        if (v != null && !Number.isNaN(v)) values.push(v);
      });
    }
    if (values.length === 0) {
      return () => NO_DATA_COLOR;
    }
    return d3
      .scaleQuantile()
      .domain(values)
      .range(d3.quantize(d3.interpolateYlOrRd, Math.min(values.length, 7)));
  }, [data, metric]);

  /* ---------------------------------------------------------------- */
  /*  4. Render / update the D3 map                                    */
  /* ---------------------------------------------------------------- */
  useEffect(() => {
    if (!geoData || !svgRef.current) return;

    const svg = d3.select(svgRef.current);

    // ---- Projection ----
    const projection = d3
      .geoMercator()
      .center([121, 23.5])
      .scale(8000)
      .translate([MAP_WIDTH / 2, MAP_HEIGHT / 2]);

    const path = d3.geoPath().projection(projection);

    // ---- Resolve feature name ----
    function featureName(d) {
      const raw = d.properties.COUNTYNAME || d.properties.name || d.properties.NAME || d.properties.county_name_zh || '';
      return normalizeName(raw);
    }

    // ---- Data join ----
    const features = geoData.features || [];

    const counties = svg
      .select('.counties-group')
      .selectAll('path.county')
      .data(features, (d) => featureName(d));

    // Enter + Update
    counties
      .join(
        (enter) =>
          enter
            .append('path')
            .attr('class', 'county')
            .attr('d', path)
            .attr('fill', NO_DATA_COLOR)
            .attr('stroke', STROKE_COLOR)
            .attr('stroke-width', 1),
        (update) => update,
        (exit) => exit.remove(),
      )
      .transition()
      .duration(400)
      .attr('d', path)
      .attr('fill', (d) => {
        const name = featureName(d);
        const record = dataMap.get(name);
        const value = resolveValue(record, metric);
        return value != null ? colorScale(value) : NO_DATA_COLOR;
      })
      .attr('stroke', (d) => {
        const name = featureName(d);
        if (name === selectedCounty) return STROKE_SELECTED_COLOR;
        if (name === hoveredCounty) return STROKE_HOVER_COLOR;
        return STROKE_COLOR;
      })
      .attr('stroke-width', (d) => {
        const name = featureName(d);
        if (name === selectedCounty || name === hoveredCounty) return 2.5;
        return 1;
      });

    // ---- Interaction handlers (re-bindable) ----
    svg
      .select('.counties-group')
      .selectAll('path.county')
      .on('mouseenter', function (event, d) {
        const name = featureName(d);
        const record = dataMap.get(name);
        const value = resolveValue(record, metric);

        setHoveredCounty(name);

        // Raise to top and highlight
        d3.select(this)
          .raise()
          .transition()
          .duration(150)
          .attr('stroke', STROKE_HOVER_COLOR)
          .attr('stroke-width', 2.5);

        // Tooltip position relative to container
        const container = containerRef.current;
        if (container) {
          const rect = container.getBoundingClientRect();
          setTooltip({
            show: true,
            x: event.clientX - rect.left,
            y: event.clientY - rect.top,
            county: name,
            avgPrice: record?.avgPrice ?? 0,
            volume: record?.volume ?? 0,
            productionTonnes: record?.productionTonnes ?? 0,
          });
        }
      })
      .on('mousemove', function (event) {
        const container = containerRef.current;
        if (container) {
          const rect = container.getBoundingClientRect();
          setTooltip((prev) => ({
            ...prev,
            x: event.clientX - rect.left,
            y: event.clientY - rect.top,
          }));
        }
      })
      .on('mouseleave', function (event, d) {
        const name = featureName(d);
        setHoveredCounty(null);

        d3.select(this)
          .transition()
          .duration(150)
          .attr('stroke', name === selectedCounty ? STROKE_SELECTED_COLOR : STROKE_COLOR)
          .attr('stroke-width', name === selectedCounty ? 2.5 : 1);

        setTooltip((prev) => ({ ...prev, show: false }));
      })
      .on('click', function (event, d) {
        const name = featureName(d);
        setSelectedCounty(name === selectedCounty ? null : name);
      })
      .style('cursor', 'pointer');
  }, [geoData, data, dataMap, metric, colorScale, hoveredCounty, selectedCounty, setHoveredCounty, setSelectedCounty]);

  /* ---------------------------------------------------------------- */
  /*  5. Compute domain for legend                                     */
  /* ---------------------------------------------------------------- */
  const domain = useMemo(() => {
    if (!Array.isArray(data) || data.length === 0) return [0, 0];
    const values = data
      .map((d) => resolveValue(d, metric))
      .filter((v) => v != null && !Number.isNaN(v));
    if (values.length === 0) return [0, 0];
    return [d3.min(values), d3.max(values)];
  }, [data, metric]);

  /* ---------------------------------------------------------------- */
  /*  Render                                                           */
  /* ---------------------------------------------------------------- */
  if (loading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <svg className="h-8 w-8 animate-spin text-emerald-500" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          <span className="text-sm text-gray-500">載入地圖資料中...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-96 items-center justify-center">
        <div className="flex flex-col items-center gap-2 text-center">
          <svg className="h-10 w-10 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
          </svg>
          <p className="text-sm font-medium text-gray-700">無法載入地圖</p>
          <p className="text-xs text-gray-500">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div ref={containerRef} className="taiwan-map-container relative">
      {/* SVG map */}
      <svg
        ref={svgRef}
        viewBox={`0 0 ${MAP_WIDTH} ${MAP_HEIGHT}`}
        className="taiwan-map-svg mx-auto block w-full"
        preserveAspectRatio="xMidYMid meet"
      >
        <g className="counties-group" />
      </svg>

      {/* Floating tooltip */}
      <CountyTooltip
        show={tooltip.show}
        x={tooltip.x}
        y={tooltip.y}
        county={tooltip.county}
        avgPrice={tooltip.avgPrice}
        volume={tooltip.volume}
        productionTonnes={tooltip.productionTonnes}
      />

      {/* Legend */}
      <MapLegend
        domain={domain}
        metric={metric}
        formatValue={(v) => formatMetricValue(v, metric)}
      />
    </div>
  );
}
