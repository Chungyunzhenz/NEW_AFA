import { useState, useEffect, useRef } from 'react';
import useFilterStore from '../stores/useFilterStore';
import { getTyphoonEvents, getTyphoonImpact } from '../api/typhoon';

/**
 * Custom hook that fetches typhoon events and crop-specific impact data.
 * Auto-refetches when selectedCrop changes.
 *
 * @returns {{
 *   events: Array,
 *   impact: Object|null,
 *   loading: boolean,
 *   error: string|null
 * }}
 */
export default function useTyphoonData() {
  const { selectedCrop } = useFilterStore();

  const [events, setEvents] = useState([]);
  const [impact, setImpact] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const abortRef = useRef(0);

  useEffect(() => {
    const requestId = ++abortRef.current;
    let cancelled = false;

    async function fetchAll() {
      setLoading(true);
      setError(null);

      try {
        const fetches = [
          getTyphoonEvents().catch((err) => {
            console.warn('[useTyphoonData] events fetch failed:', err.message);
            return [];
          }),
        ];

        if (selectedCrop) {
          fetches.push(
            getTyphoonImpact(selectedCrop).catch((err) => {
              console.warn('[useTyphoonData] impact fetch failed:', err.message);
              return null;
            }),
          );
        }

        const [eventsResult, impactResult] = await Promise.all(fetches);

        if (cancelled || requestId !== abortRef.current) return;

        setEvents(Array.isArray(eventsResult) ? eventsResult : []);
        setImpact(selectedCrop ? impactResult : null);
      } catch (err) {
        if (!cancelled && requestId === abortRef.current) {
          setError(err.message);
          setEvents([]);
          setImpact(null);
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
  }, [selectedCrop]);

  return { events, impact, loading, error };
}
