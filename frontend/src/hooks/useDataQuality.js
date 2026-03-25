import { useState, useEffect } from 'react';
import { getDataQualityOverview } from '../api/dataQuality';

export default function useDataQuality() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function fetch() {
      setLoading(true);
      setError(null);
      try {
        const result = await getDataQualityOverview();
        if (!cancelled) setData(result);
      } catch (err) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetch();
    return () => { cancelled = true; };
  }, []);

  return { data, loading, error };
}
