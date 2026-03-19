import { create } from 'zustand';
import { DEFAULT_DATE_RANGE, GRANULARITIES, METRICS } from '../utils/constants';

const useFilterStore = create((set) => ({
  // State
  selectedCrop: null,
  selectedCropLabel: null,
  dateRange: { ...DEFAULT_DATE_RANGE },
  granularity: GRANULARITIES.MONTHLY,
  metric: METRICS.AVG_PRICE,

  // Actions
  setSelectedCrop: (crop, label) => set({ selectedCrop: crop, selectedCropLabel: label ?? crop }),

  setDateRange: (dateRange) =>
    set((state) => ({
      dateRange: { ...state.dateRange, ...dateRange },
    })),

  setGranularity: (granularity) => set({ granularity }),

  setMetric: (metric) => set({ metric }),

  resetFilters: () =>
    set({
      selectedCrop: null,
      selectedCropLabel: null,
      dateRange: { ...DEFAULT_DATE_RANGE },
      granularity: GRANULARITIES.MONTHLY,
      metric: METRICS.AVG_PRICE,
    }),
}));

export default useFilterStore;
