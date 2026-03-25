import client from './client';

export function getTyphoonEvents(params = {}) {
  return client.get('/typhoon/events', { params });
}

export function getTyphoonImpact(cropKey) {
  return client.get(`/typhoon/impact/${cropKey}`);
}

export function simulateTyphoon(data) {
  return client.post('/typhoon/simulate', data);
}
