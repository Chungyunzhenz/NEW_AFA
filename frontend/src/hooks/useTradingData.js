import { useState, useEffect, useCallback, useRef } from 'react';
import useFilterStore from '../stores/useFilterStore';
import { getTradingDaily, getTradingAggregated, getMarketTimeSeries } from '../api/trading';

/**
 * Custom hook that fetches trading data based on current filter state.
 *
 * Supports daily, aggregated, and market-level time-series requests
 * depending on the granularity and optional market filter.
 *
 * @param {Object} [options]
 * @param {string} [options.market]       - Optional market filter.
 * @param {number} [options.page=1]       - Page for daily data pagination.
 * @param {number} [options.pageSize=50]  - Page size for daily data.
 * @param {boolean} [options.autoFetch=true] - Whether to auto-fetch on filter change.
 * @returns {{ data: Array, totalCount: number, loading: boolean, error: string|null, refetch: Function }}
 */
export default function useTradingData({
  market,
  page = 1,
  pageSize = 50,
  autoFetch = true,
} = {}) {
  const { selectedCrop, dateRange, granularity } = useFilterStore();

  const [data, setData] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const abortRef = useRef(0);

  const fetchData = useCallback(async () => {
    if (!selectedCrop) {
      setData([]);
      setTotalCount(0);
      return;
    }

    const requestId = ++abortRef.current;
    setLoading(true);
    setError(null);

    try {
      let result;

      if (market) {
        // Market-specific time series
        result = await getMarketTimeSeries({
          crop: selectedCrop,
          market,
          startDate: dateRange.startDate,
          endDate: dateRange.endDate,
          granularity,
        });
      } else if (granularity === 'daily') {
        // Paginated daily data
        result = await getTradingDaily({
          crop: selectedCrop,
          startDate: dateRange.startDate,
          endDate: dateRange.endDate,
          page,
          pageSize,
        });
      } else {
        // Aggregated data (weekly/monthly/yearly)
        result = await getTradingAggregated({
          crop: selectedCrop,
          granularity,
          startDate: dateRange.startDate,
          endDate: dateRange.endDate,
        });
      }

      if (requestId === abortRef.current) {
        // Handle both paginated { items, total } and plain array responses
        if (result && typeof result === 'object' && !Array.isArray(result)) {
          setData(result.items ?? result.data ?? []);
          setTotalCount(result.total ?? result.totalCount ?? 0);
        } else {
          setData(Array.isArray(result) ? result : []);
          setTotalCount(Array.isArray(result) ? result.length : 0);
        }
      }
    } catch (err) {
      if (requestId === abortRef.current) {
        setError(err.message);
        setData([]);
        setTotalCount(0);
      }
    } finally {
      if (requestId === abortRef.current) {
        setLoading(false);
      }
    }
  }, [selectedCrop, dateRange.startDate, dateRange.endDate, granularity, market, page, pageSize]);

  useEffect(() => {
    if (autoFetch) {
      fetchData();
    }
  }, [fetchData, autoFetch]);

  return { data, totalCount, loading, error, refetch: fetchData };
}
