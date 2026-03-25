import client from './client';

export function getDataQualityOverview() {
  return client.get('/data-quality/overview');
}

export function getCropQuality(cropKey) {
  return client.get(`/data-quality/${cropKey}`);
}
