import client from './client';

export function getTrafficLight({ crop }) {
  return client.get(`/alerts/traffic-light/${encodeURIComponent(crop)}`);
}
