import client from './client';

/**
 * Fetch daily trading data with optional filters.
 * @param {Object} params - { crop, market, startDate, endDate, page, pageSize }
 */
export function getTradingDaily({ crop, startDate, endDate, page, pageSize, ...rest } = {}) {
  return client.get(`/trading/${crop}/daily`, {
    params: { start_date: startDate, end_date: endDate, skip: page ? (page - 1) * (pageSize || 100) : undefined, limit: pageSize, ...rest },
  });
}

/**
 * Fetch aggregated trading data (weekly / monthly / yearly).
 * @param {Object} params - { crop, granularity, startDate, endDate }
 */
export function getTradingAggregated({ crop, granularity, startDate, endDate, ...rest } = {}) {
  const granMap = { daily: 'day', weekly: 'week', monthly: 'month', yearly: 'year' };
  return client.get(`/trading/${crop}/aggregated`, {
    params: { granularity: granMap[granularity] || granularity, start_date: startDate, end_date: endDate, ...rest },
  });
}

/**
 * Fetch trading data grouped by county.
 * @param {Object} params - { crop, startDate, endDate }
 */
export function getTradingByCounty({ crop, startDate, endDate, ...rest } = {}) {
  return client.get(`/trading/${crop}/by-county`, {
    params: { start_date: startDate, end_date: endDate, ...rest },
  });
}

/**
 * Fetch market-level time series for a specific crop.
 * @param {Object} params - { crop, market, startDate, endDate, granularity }
 */
export function getMarketTimeSeries({ crop, market, startDate, endDate, ...rest } = {}) {
  return client.get(`/trading/${crop}/markets/${market}`, {
    params: { start_date: startDate, end_date: endDate, ...rest },
  });
}
