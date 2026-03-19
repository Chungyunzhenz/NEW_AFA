import client from './client';

/**
 * Fetch forecast data for a crop.
 * @param {Object} params - { crop, horizon, startDate }
 */
export function getForecast({ crop, ...params } = {}) {
  return client.get(`/predictions/${crop}/forecast`, { params });
}

/**
 * Fetch predictions grouped by county.
 * @param {Object} params - { crop, date }
 */
export function getPredictionsByCounty({ crop, date, ...params } = {}) {
  return client.get(`/predictions/${crop}/by-county`, {
    params: { forecast_date: date, ...params },
  });
}

/**
 * Fetch model metadata and performance metrics.
 * @param {Object} params - { crop }
 */
export function getModelInfo({ crop, ...params } = {}) {
  return client.get(`/predictions/${crop}/model-info`, { params });
}

/**
 * Trigger a model retrain job.
 * @param {Object} data - { crop, forceRetrain }
 */
export function triggerRetrain({ crop, ...data } = {}) {
  return client.post(`/predictions/${crop}/retrain`, data);
}
