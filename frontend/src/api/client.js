import axios from 'axios';

const client = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' }
});

client.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const detail = error.response?.data?.detail;
    const message =
      Array.isArray(detail)
        ? detail.map((d) => d.msg || JSON.stringify(d)).join('; ')
        : typeof detail === 'string'
          ? detail
          : error.response?.data?.message || error.message || 'An unexpected error occurred';
    console.error('[API Error]', message);
    return Promise.reject(new Error(message));
  }
);

export default client;
