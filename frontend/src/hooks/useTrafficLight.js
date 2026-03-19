import { useEffect } from 'react';
import useFilterStore from '../stores/useFilterStore';
import useTrafficLightStore from '../stores/useTrafficLightStore';

export default function useTrafficLight() {
  const selectedCrop = useFilterStore((s) => s.selectedCrop);
  const { metrics, signals, overall, loading, error, fetchTrafficLight } =
    useTrafficLightStore();

  useEffect(() => {
    if (selectedCrop) {
      fetchTrafficLight(selectedCrop);
    }
  }, [selectedCrop, fetchTrafficLight]);

  return { metrics, signals, overall, loading, error };
}
