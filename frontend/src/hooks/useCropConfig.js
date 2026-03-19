import { useState, useEffect, useRef } from 'react';
import useFilterStore from '../stores/useFilterStore';
import { getCropDetail } from '../api/crops';

/**
 * Custom hook that fetches the detailed crop configuration including
 * seasonality information for the currently selected crop.
 *
 * @param {string} [overrideCropId] - Optional crop ID to use instead of the store value.
 * @returns {{
 *   config: Object|null,
 *   loading: boolean,
 *   error: string|null
 * }}
 *
 * Expected config shape:
 * {
 *   id, name, category, unit,
 *   seasonality: { peakMonths: number[], offMonths: number[], harvestSeason: string },
 *   priceRange: { min, max, typical },
 *   description, imageUrl
 * }
 */
export default function useCropConfig(overrideCropId) {
  const selectedCrop = useFilterStore((s) => s.selectedCrop);
  const cropId = overrideCropId ?? selectedCrop;

  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const abortRef = useRef(0);
  // Cache to avoid refetching the same crop config
  const cacheRef = useRef(new Map());

  useEffect(() => {
    if (!cropId) {
      setConfig(null);
      return;
    }

    // Return cached result if available
    if (cacheRef.current.has(cropId)) {
      setConfig(cacheRef.current.get(cropId));
      return;
    }

    const requestId = ++abortRef.current;
    let cancelled = false;

    async function fetchConfig() {
      setLoading(true);
      setError(null);

      try {
        const data = await getCropDetail(cropId);

        if (cancelled || requestId !== abortRef.current) return;

        // Normalise seasonality data
        const normalised = {
          id: data.id ?? cropId,
          name: data.name ?? data.cropName ?? cropId,
          category: data.category ?? null,
          unit: data.unit ?? '元/公斤',
          seasonality: data.seasonality ?? {
            peakMonths: [],
            offMonths: [],
            harvestSeason: null,
          },
          priceRange: data.priceRange ?? data.price_range ?? {
            min: null,
            max: null,
            typical: null,
          },
          description: data.description ?? null,
          imageUrl: data.imageUrl ?? data.image_url ?? null,
          ...data,
        };

        cacheRef.current.set(cropId, normalised);
        setConfig(normalised);
      } catch (err) {
        if (!cancelled && requestId === abortRef.current) {
          setError(err.message);
          setConfig(null);
        }
      } finally {
        if (!cancelled && requestId === abortRef.current) {
          setLoading(false);
        }
      }
    }

    fetchConfig();

    return () => {
      cancelled = true;
    };
  }, [cropId]);

  return { config, loading, error };
}
