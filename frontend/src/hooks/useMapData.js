import { useState, useEffect, useRef } from 'react';
import useFilterStore from '../stores/useFilterStore';
import useMapStore from '../stores/useMapStore';
import { getTradingByCounty } from '../api/trading';
import { getProductionByCounty } from '../api/production';
import { getPredictionsByCounty } from '../api/predictions';

/**
 * Custom hook that fetches trading, production, or prediction data
 * formatted for the Taiwan map choropleth based on current filters
 * and map layer selection.
 *
 * Auto-refetches when selectedCrop, dateRange, metric, or mapLayer change.
 *
 * @returns {{ mapData: Array, loading: boolean, error: string|null }}
 */
export default function useMapData() {
  const { selectedCrop, dateRange, metric } = useFilterStore();
  const { mapLayer } = useMapStore();

  const [mapData, setMapData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Track in-flight request to avoid race conditions
  const abortRef = useRef(0);

  useEffect(() => {
    // Nothing to fetch without a crop selection
    if (!selectedCrop) {
      setMapData([]);
      return;
    }

    const requestId = ++abortRef.current;
    let cancelled = false;

    async function fetchMapData() {
      setLoading(true);
      setError(null);

      try {
        let data;

        if (mapLayer === 'prediction') {
          data = await getPredictionsByCounty({
            crop: selectedCrop,
            date: dateRange.endDate,
          });
        } else if (mapLayer === 'production') {
          const year = dateRange.startDate?.slice(0, 4);
          data = await getProductionByCounty({
            crop: selectedCrop,
            year,
          });
        } else {
          // Default: trading layer
          data = await getTradingByCounty({
            crop: selectedCrop,
            startDate: dateRange.startDate,
            endDate: dateRange.endDate,
          });
        }

        // Only apply result if this is still the latest request
        if (!cancelled && requestId === abortRef.current) {
          // Normalise data for map consumption.
          // Each record should have at minimum { countyId, countyName, value }.
          const normalised = (Array.isArray(data) ? data : []).map((item) => ({
            countyId: item.countyId ?? item.county_id ?? item.county_code ?? item.id,
            countyName: item.countyName ?? item.county_name ?? item.county_name_zh ?? item.name,
            value: item[metric] ?? 0,
            volume: item.volume ?? item.trading_volume ?? item.volume_total ?? 0,
            avgPrice: item.avgPrice ?? item.avg_price ?? item.price_avg ?? 0,
            raw: item,
          }));
          setMapData(normalised);
        }
      } catch (err) {
        if (!cancelled && requestId === abortRef.current) {
          setError(err.message);
          setMapData([]);
        }
      } finally {
        if (!cancelled && requestId === abortRef.current) {
          setLoading(false);
        }
      }
    }

    fetchMapData();

    return () => {
      cancelled = true;
    };
  }, [selectedCrop, dateRange.startDate, dateRange.endDate, metric, mapLayer]);

  return { mapData, loading, error };
}
