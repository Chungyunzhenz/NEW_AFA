import client from './client';

/**
 * Fetch the list of counties.
 */
export function getCounties() {
  return client.get('/regions/counties');
}

/**
 * Fetch the list of markets, optionally filtered by county.
 * @param {Object} params - { county }
 */
export function getMarkets(params = {}) {
  return client.get('/regions/markets', { params });
}

/**
 * Fetch the Taiwan GeoJSON data for map rendering.
 */
export function getGeoJSON() {
  return client.get('/regions/geojson');
}
