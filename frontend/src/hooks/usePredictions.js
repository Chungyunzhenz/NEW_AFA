import { useState, useEffect, useRef } from 'react';
import useFilterStore from '../stores/useFilterStore';
import { getForecast, getModelInfo } from '../api/predictions';

/**
 * Custom hook that fetches prediction/forecast data and model info
 * for the currently selected crop and metric.
 *
 * Auto-refetches when selectedCrop or metric changes.
 *
 * @param {Object} [options]
 * @param {string} [options.horizon='7d'] - Forecast horizon ('7d', '14d', '30d').
 * @returns {{
 *   predictions: Array,
 *   forecast: Object|null,
 *   modelInfo: Array,
 *   loading: boolean,
 *   error: string|null
 * }}
 */
export default function usePredictions({ horizon = '1m' } = {}) {
  const { selectedCrop, metric } = useFilterStore();

  const [predictions, setPredictions] = useState([]);
  const [forecast, setForecast] = useState(null);
  const [modelInfo, setModelInfo] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const abortRef = useRef(0);

  useEffect(() => {
    if (!selectedCrop) {
      setPredictions([]);
      setForecast(null);
      setModelInfo([]);
      return;
    }

    const requestId = ++abortRef.current;
    let cancelled = false;

    async function fetchAll() {
      setLoading(true);
      setError(null);

      try {
        // Fetch forecast and model info in parallel
        const [forecastResult, modelResult] = await Promise.all([
          getForecast({ crop: selectedCrop, horizon, metric: metric || 'price_avg', region_type: 'national', limit: 500 }).catch((err) => {
            console.warn('[usePredictions] forecast fetch failed:', err.message);
            return null;
          }),
          getModelInfo({ crop: selectedCrop }).catch((err) => {
            console.warn('[usePredictions] modelInfo fetch failed:', err.message);
            return null;
          }),
        ]);

        if (cancelled || requestId !== abortRef.current) return;

        // Process forecast result
        if (forecastResult) {
          const items = Array.isArray(forecastResult)
            ? forecastResult
            : forecastResult.predictions ?? [];
          setPredictions(items);

          // Find the best forecast: ensemble + national + price_avg
          const currentMetric = metric || 'price_avg';
          const best =
            items.find((d) => d.model_name === 'ensemble' && d.region_type === 'national' && d.target_metric === currentMetric) ||
            items.find((d) => d.model_name === 'ensemble' && d.target_metric === currentMetric) ||
            items.find((d) => d.target_metric === currentMetric) ||
            (items.length > 0 ? items[0] : null);
          setForecast(best);
        } else {
          setPredictions([]);
          setForecast(null);
        }

        // Process model info — map model_type to name for display
        if (modelResult) {
          const raw = Array.isArray(modelResult)
            ? modelResult
            : modelResult.models ?? [];
          const models = raw.map((m) => ({
            ...m,
            name: m.name ?? m.model_type ?? 'Unknown',
          }));
          setModelInfo(models);
        } else {
          setModelInfo([]);
        }
      } catch (err) {
        if (!cancelled && requestId === abortRef.current) {
          setError(err.message);
          setPredictions([]);
          setForecast(null);
          setModelInfo([]);
        }
      } finally {
        if (!cancelled && requestId === abortRef.current) {
          setLoading(false);
        }
      }
    }

    fetchAll();

    return () => {
      cancelled = true;
    };
  }, [selectedCrop, metric, horizon]);

  return { predictions, forecast, modelInfo, loading, error };
}
