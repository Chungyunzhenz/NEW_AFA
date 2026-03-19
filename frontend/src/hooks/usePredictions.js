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
export default function usePredictions({ horizon = '7d' } = {}) {
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
          getForecast({ crop: selectedCrop, horizon }).catch((err) => {
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
          if (Array.isArray(forecastResult)) {
            setPredictions(forecastResult);
            // Use the last item as the primary forecast point
            setForecast(forecastResult.length > 0 ? forecastResult[forecastResult.length - 1] : null);
          } else if (forecastResult.predictions) {
            setPredictions(forecastResult.predictions);
            setForecast(forecastResult);
          } else {
            setPredictions([]);
            setForecast(forecastResult);
          }
        } else {
          setPredictions([]);
          setForecast(null);
        }

        // Process model info
        if (modelResult) {
          const models = Array.isArray(modelResult)
            ? modelResult
            : modelResult.models ?? [];
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
