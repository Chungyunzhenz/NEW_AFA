import client from './client';

/**
 * Upload a CSV or Excel file for parsing.
 * @param {File} file - The file object
 * @param {string} dataType - "trading" | "production" | "weather"
 */
export function uploadFile(file, dataType = 'trading') {
  const formData = new FormData();
  formData.append('file', file);
  return client.post('/upload/file', formData, {
    params: { data_type: dataType },
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 60000,
  });
}

/**
 * Apply column mapping and preview validated rows.
 * @param {Object} params
 * @param {string} params.uploadId
 * @param {string} params.dataType
 * @param {Object} params.mapping - { sourceColumn: targetField | null }
 */
export function previewImport({ uploadId, dataType, mapping }) {
  return client.post('/upload/preview', {
    upload_id: uploadId,
    data_type: dataType,
    mapping,
  });
}

/**
 * Confirm and import validated data into the database.
 * @param {Object} params
 * @param {string} params.uploadId
 * @param {string} params.dataType
 * @param {boolean} [params.skipErrors=true]
 */
export function confirmImport({ uploadId, dataType, skipErrors = true }) {
  return client.post('/upload/confirm', {
    upload_id: uploadId,
    data_type: dataType,
    skip_errors: skipErrors,
  });
}

/**
 * List saved column mapping presets.
 * @param {string} [dataType] - Optional filter
 */
export function getPresets(dataType) {
  return client.get('/upload/presets', {
    params: dataType ? { data_type: dataType } : {},
  });
}

/**
 * Save a new column mapping preset.
 * @param {Object} data - { name, dataType, mapping }
 */
export function savePreset({ name, dataType, mapping }) {
  return client.post('/upload/presets', {
    name,
    data_type: dataType,
    mapping,
  });
}

/**
 * Delete a column mapping preset.
 * @param {number} id
 */
export function deletePreset(id) {
  return client.delete(`/upload/presets/${id}`);
}
