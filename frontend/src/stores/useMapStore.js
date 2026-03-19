import { create } from 'zustand';

const useMapStore = create((set) => ({
  // State
  hoveredCounty: null,
  selectedCounty: null,
  mapLayer: 'trading', // 'trading' | 'production' | 'prediction'

  // Actions
  setHoveredCounty: (county) => set({ hoveredCounty: county }),

  setSelectedCounty: (county) => set({ selectedCounty: county }),

  setMapLayer: (layer) => set({ mapLayer: layer }),

  clearSelection: () =>
    set({
      hoveredCounty: null,
      selectedCounty: null,
    }),
}));

export default useMapStore;
