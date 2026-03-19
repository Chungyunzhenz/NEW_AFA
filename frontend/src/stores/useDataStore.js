import { create } from 'zustand';
import { getTradingAggregated, getTradingByCounty } from '../api/trading';
import { getProductionByCounty, getProductionTimeSeries } from '../api/production';

const useDataStore = create((set, get) => ({
  // Trading state
  tradingData: [],
  tradingByCounty: [],
  tradingLoading: false,
  tradingError: null,

  // Production state
  productionData: [],
  productionByCounty: [],
  productionLoading: false,
  productionError: null,

  // Trading actions
  fetchTradingData: async (params) => {
    set({ tradingLoading: true, tradingError: null });
    try {
      const data = await getTradingAggregated(params);
      set({ tradingData: data, tradingLoading: false });
    } catch (error) {
      set({ tradingError: error.message, tradingLoading: false });
    }
  },

  fetchTradingByCounty: async (params) => {
    set({ tradingLoading: true, tradingError: null });
    try {
      const data = await getTradingByCounty(params);
      set({ tradingByCounty: data, tradingLoading: false });
    } catch (error) {
      set({ tradingError: error.message, tradingLoading: false });
    }
  },

  // Production actions
  fetchProductionData: async (params) => {
    set({ productionLoading: true, productionError: null });
    try {
      const data = await getProductionTimeSeries(params);
      set({ productionData: data, productionLoading: false });
    } catch (error) {
      set({ productionError: error.message, productionLoading: false });
    }
  },

  fetchProductionByCounty: async (params) => {
    set({ productionLoading: true, productionError: null });
    try {
      const data = await getProductionByCounty(params);
      set({ productionByCounty: data, productionLoading: false });
    } catch (error) {
      set({ productionError: error.message, productionLoading: false });
    }
  },

  // Clear
  clearTradingData: () =>
    set({ tradingData: [], tradingByCounty: [], tradingError: null }),

  clearProductionData: () =>
    set({ productionData: [], productionByCounty: [], productionError: null }),
}));

export default useDataStore;
