import client from './client';

/**
 * Fetch current sync status (scheduler, crop stats, date ranges).
 */
export function fetchSyncStatus() {
  return client.get('/sync/status');
}

/**
 * Trigger a manual data sync.
 * @param {Object} params
 * @param {string} params.dataType - "trading" | "weather" | "both"
 * @param {number} params.daysBack - Number of days to fetch (1–365)
 */
export function triggerSync({ dataType = 'both', daysBack = 1 } = {}) {
  return client.post('/sync/fetch-latest', null, {
    params: { data_type: dataType, days_back: daysBack },
  });
}

/**
 * Re-scan trading records with NULL crop_id and try to match them.
 */
export function backfillCropIds() {
  return client.post('/sync/backfill-crop-ids');
}
