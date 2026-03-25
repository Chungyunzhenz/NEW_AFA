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
        let tradingByCounty = [];
        let productionByCounty = [];

        if (mapLayer === 'prediction') {
          data = await getPredictionsByCounty({
            crop: selectedCrop,
            date: dateRange.endDate,
          });
        } else if (mapLayer === 'production') {
          const year = dateRange.startDate?.slice(0, 4);
          // Fetch both production (primary) and trading (secondary) in parallel
          const [prodData, tradData] = await Promise.all([
            getProductionByCounty({ crop: selectedCrop, year }),
            getTradingByCounty({ crop: selectedCrop, startDate: dateRange.startDate, endDate: dateRange.endDate }).catch(() => []),
          ]);
          data = prodData;
          productionByCounty = Array.isArray(prodData) ? prodData : [];
          tradingByCounty = Array.isArray(tradData) ? tradData : [];
        } else {
          // Default: trading layer — also fetch production
          const year = dateRange.startDate?.slice(0, 4);
          const [tradData, prodData] = await Promise.all([
            getTradingByCounty({ crop: selectedCrop, startDate: dateRange.startDate, endDate: dateRange.endDate }),
            getProductionByCounty({ crop: selectedCrop, year }).catch(() => []),
          ]);
          data = tradData;
          tradingByCounty = Array.isArray(tradData) ? tradData : [];
          productionByCounty = Array.isArray(prodData) ? prodData : [];
        }

        // Only apply result if this is still the latest request
        if (!cancelled && requestId === abortRef.current) {
          // Build lookup maps for merging
          const toKey = (item) => item.county_code ?? item.countyId ?? item.county_id ?? item.id;
          const tradMap = new Map(tradingByCounty.map((t) => [toKey(t), t]));
          const prodMap = new Map(productionByCounty.map((p) => [toKey(p), p]));

          // Normalise data for map consumption.
          // Each record has { countyId, countyName, value, avgPrice, volume, productionTonnes }.
          const normalised = (Array.isArray(data) ? data : []).map((item) => {
            const id = toKey(item);
            const tradItem = tradMap.get(id);
            const prodItem = prodMap.get(id);
            return {
              countyId: id,
              countyName: item.county_name_zh ?? item.countyName ?? item.county_name ?? item.name,
              value: metric === 'trading_volume'
                ? (item.volume ?? 0)
                : (item.avg_price ?? item.value ?? 0),
              avgPrice: tradItem?.avg_price ?? item.avg_price ?? 0,
              volume: tradItem?.volume ?? item.volume ?? 0,
              productionTonnes: prodItem?.production_tonnes ?? prodItem?.value ?? item.production_tonnes ?? 0,
              tempAvg: tradItem?.temp_avg ?? item.temp_avg ?? null,
              rainfallMm: tradItem?.rainfall_mm ?? item.rainfall_mm ?? null,
              raw: item,
            };
          });
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
