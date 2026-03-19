import { create } from 'zustand';
import {
  getForecast,
  getPredictionsByCounty,
  getModelInfo,
  triggerRetrain,
} from '../api/predictions';

const usePredictionStore = create((set) => ({
  // State
  predictions: [],
  predictionsByCounty: [],
  modelInfo: null,
  loading: false,
  error: null,
  retrainStatus: null,

  // Actions
  fetchForecast: async (params) => {
    set({ loading: true, error: null });
    try {
      const data = await getForecast(params);
      set({ predictions: data, loading: false });
    } catch (error) {
      set({ error: error.message, loading: false });
    }
  },

  fetchPredictionsByCounty: async (params) => {
    set({ loading: true, error: null });
    try {
      const data = await getPredictionsByCounty(params);
      set({ predictionsByCounty: data, loading: false });
    } catch (error) {
      set({ error: error.message, loading: false });
    }
  },

  fetchModelInfo: async (params) => {
    set({ loading: true, error: null });
    try {
      const data = await getModelInfo(params);
      set({ modelInfo: data, loading: false });
    } catch (error) {
      set({ error: error.message, loading: false });
    }
  },

  requestRetrain: async (data) => {
    set({ retrainStatus: 'pending', error: null });
    try {
      const result = await triggerRetrain(data);
      set({ retrainStatus: 'success' });
      return result;
    } catch (error) {
      set({ retrainStatus: 'failed', error: error.message });
      throw error;
    }
  },

  clearPredictions: () =>
    set({
      predictions: [],
      predictionsByCounty: [],
      error: null,
      retrainStatus: null,
    }),
}));

export default usePredictionStore;
