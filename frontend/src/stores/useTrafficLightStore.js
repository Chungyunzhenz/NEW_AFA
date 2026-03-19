import { create } from 'zustand';
import { getTrafficLight } from '../api/trafficLight';
import { TRAFFIC_THRESHOLDS, TRAFFIC_SIGNALS } from '../utils/constants';

function computeSignal(value, thresholds) {
  if (value == null) return TRAFFIC_SIGNALS.UNKNOWN;
  if (value <= thresholds.green) return TRAFFIC_SIGNALS.GREEN;
  if (value <= thresholds.yellow) return TRAFFIC_SIGNALS.YELLOW;
  return TRAFFIC_SIGNALS.RED;
}

const SEVERITY = {
  [TRAFFIC_SIGNALS.UNKNOWN]: 0,
  [TRAFFIC_SIGNALS.GREEN]: 1,
  [TRAFFIC_SIGNALS.YELLOW]: 2,
  [TRAFFIC_SIGNALS.RED]: 3,
};

function overallSignal(signals) {
  const vals = Object.values(signals);
  if (vals.includes(TRAFFIC_SIGNALS.RED)) return TRAFFIC_SIGNALS.RED;
  let max = TRAFFIC_SIGNALS.UNKNOWN;
  for (const s of vals) {
    if (SEVERITY[s] > SEVERITY[max]) max = s;
  }
  return max;
}

const useTrafficLightStore = create((set) => ({
  metrics: null,
  signals: null,
  overall: null,
  loading: false,
  error: null,

  fetchTrafficLight: async (cropKey) => {
    if (!cropKey) return;
    set({ loading: true, error: null });
    try {
      const data = await getTrafficLight({ crop: cropKey });
      const signals = {
        supply_index: computeSignal(data.supply_index, TRAFFIC_THRESHOLDS.supply_index),
        price_drop_pct: computeSignal(data.price_drop_pct, TRAFFIC_THRESHOLDS.price_drop_pct),
        area_growth_pct: computeSignal(data.area_growth_pct, TRAFFIC_THRESHOLDS.area_growth_pct),
      };
      set({
        metrics: data,
        signals,
        overall: overallSignal(signals),
        loading: false,
      });
    } catch (err) {
      set({ error: err.message, loading: false });
    }
  },
}));

export default useTrafficLightStore;
