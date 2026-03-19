import { useState, useEffect } from 'react';
import useFilterStore from '../../stores/useFilterStore';
import { getCrops } from '../../api/crops';

/**
 * Colour dots assigned to each known crop for quick visual identification.
 */
const CROP_COLORS = {
  '鳳梨': '#f59e0b',
  '甘藍': '#22c55e',
  '香蕉': '#facc15',
  '稻米': '#84cc16',
  '芒果': '#fb923c',
  '西瓜': '#ef4444',
  '茶葉': '#16a34a',
  '蓮霧': '#e879f9',
  '番茄': '#dc2626',
  '胡蘿蔔': '#f97316',
  '竹筍': '#a3e635',
  '洋蔥': '#d4a276',
  '蒜頭': '#fde68a',
  '花椰菜': '#4ade80',
  '高麗菜': '#86efac',
};

const FALLBACK_COLOR = '#94a3b8';

/**
 * Dropdown to choose a crop. Fetches crop list from the API on mount.
 */
export default function CropSelector({ compact = false }) {
  const selectedCrop = useFilterStore((s) => s.selectedCrop);
  const setSelectedCrop = useFilterStore((s) => s.setSelectedCrop);

  const [crops, setCrops] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const data = await getCrops();
        if (!cancelled) {
          // Normalise: API may return { items: [...] } or plain array
          const list = Array.isArray(data) ? data : data?.items ?? [];
          setCrops(list);

          // Auto-select first crop when nothing selected
          if (!selectedCrop && list.length > 0) {
            const first = list[0];
            const firstId = first.crop_key ?? first.id ?? first.name ?? first;
            const firstLabel = first.display_name_zh ?? first.name ?? firstId;
            setSelectedCrop(firstId, firstLabel);
          }
        }
      } catch (err) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => { cancelled = true; };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  function handleChange(e) {
    const value = e.target.value;
    if (!value) {
      setSelectedCrop(null, null);
      return;
    }
    const matched = crops.find((c) => (c.crop_key ?? c.id ?? c.name ?? c) === value);
    const label = matched ? (matched.display_name_zh ?? matched.name ?? value) : value;
    setSelectedCrop(value, label);
  }

  const selectedName =
    typeof selectedCrop === 'string'
      ? selectedCrop
      : selectedCrop?.name ?? '';

  const dotColor = CROP_COLORS[selectedName] ?? FALLBACK_COLOR;

  if (compact) {
    return (
      <div className="relative">
        <span
          className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 h-2.5 w-2.5 rounded-full"
          style={{ backgroundColor: dotColor }}
        />
        <select
          id="crop-selector"
          value={selectedCrop ?? ''}
          onChange={handleChange}
          disabled={loading}
          className={[
            'appearance-none rounded-lg border-0 bg-emerald-50/60',
            'py-1.5 pl-7 pr-8 text-sm font-semibold text-gray-800',
            'cursor-pointer transition',
            'hover:bg-emerald-100/80 focus:ring-2 focus:ring-emerald-500/20 focus:outline-none',
            'disabled:cursor-not-allowed disabled:opacity-60',
          ].join(' ')}
        >
          <option value="">選擇作物</option>
          {crops.map((crop) => {
            const id = crop.crop_key ?? crop.id ?? crop.name ?? crop;
            const name = crop.display_name_zh ?? crop.name ?? crop;
            return (
              <option key={id} value={id}>{name}</option>
            );
          })}
        </select>
        <svg
          className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-gray-400"
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 20 20"
          fill="currentColor"
        >
          <path
            fillRule="evenodd"
            d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z"
            clipRule="evenodd"
          />
        </svg>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-1">
      <label
        htmlFor="crop-selector"
        className="text-xs font-medium text-gray-500 tracking-wide"
      >
        農產品
      </label>

      <div className="relative">
        {/* Colour indicator dot */}
        <span
          className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 h-2.5 w-2.5 rounded-full"
          style={{ backgroundColor: dotColor }}
        />

        <select
          id="crop-selector"
          value={selectedCrop ?? ''}
          onChange={handleChange}
          disabled={loading}
          className={[
            'w-full appearance-none rounded-lg border border-gray-300 bg-white',
            'py-2 pl-8 pr-10 text-sm text-gray-700',
            'shadow-sm transition',
            'hover:border-gray-400 focus:border-sky-500 focus:ring-2 focus:ring-sky-500/20 focus:outline-none',
            'disabled:cursor-not-allowed disabled:opacity-60',
          ].join(' ')}
        >
          <option value="">-- 請選擇作物 --</option>

          {crops.map((crop) => {
            const id = crop.crop_key ?? crop.id ?? crop.name ?? crop;
            const name = crop.display_name_zh ?? crop.name ?? crop;
            return (
              <option key={id} value={id}>
                {name}
              </option>
            );
          })}
        </select>

        {/* Dropdown chevron */}
        <svg
          className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400"
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 20 20"
          fill="currentColor"
        >
          <path
            fillRule="evenodd"
            d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z"
            clipRule="evenodd"
          />
        </svg>
      </div>

      {loading && (
        <p className="text-xs text-gray-400">載入作物清單中...</p>
      )}
      {error && (
        <p className="text-xs text-red-500">載入失敗: {error}</p>
      )}
    </div>
  );
}
