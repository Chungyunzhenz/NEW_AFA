import client from './client';

/**
 * Fetch the list of all available crops.
 * @param {Object} params - { category, search }
 */
export function getCrops(params = {}) {
  return client.get('/crops', { params });
}

/**
 * Fetch detail information for a specific crop.
 * @param {string} cropId - The crop identifier.
 */
export function getCropDetail(cropId) {
  return client.get(`/crops/${cropId}`);
}
