import client from './client';

/**
 * Fetch production data grouped by county.
 * @param {Object} params - { crop, year, season }
 */
export function getProductionByCounty({ crop, ...params } = {}) {
  return client.get(`/production/${crop}/by-county`, { params });
}

/**
 * Fetch production time series for a specific crop.
 * @param {Object} params - { crop, county, startYear, endYear }
 */
export function getProductionTimeSeries({ crop, ...params } = {}) {
  return client.get(`/production/${crop}/timeseries`, { params });
}
