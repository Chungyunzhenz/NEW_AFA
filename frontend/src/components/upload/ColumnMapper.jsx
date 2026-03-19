import { useState, useEffect, useCallback } from 'react';
import useUploadStore from '../../stores/useUploadStore';
import { getPresets, savePreset, deletePreset } from '../../api/upload';

export default function ColumnMapper() {
  const headers = useUploadStore((s) => s.headers);
  const sampleRows = useUploadStore((s) => s.sampleRows);
  const targetFields = useUploadStore((s) => s.targetFields);
  const mapping = useUploadStore((s) => s.mapping);
  const setMapping = useUploadStore((s) => s.setMapping);
  const doPreview = useUploadStore((s) => s.doPreview);
  const loading = useUploadStore((s) => s.loading);
  const dataType = useUploadStore((s) => s.dataType);

  const [presets, setPresets] = useState([]);
  const [presetName, setPresetName] = useState('');
  const [showSavePreset, setShowSavePreset] = useState(false);

  // Load presets
  useEffect(() => {
    getPresets(dataType).then(setPresets).catch(() => {});
  }, [dataType]);

  const handleMappingChange = useCallback(
    (sourceCol, targetField) => {
      setMapping({ ...mapping, [sourceCol]: targetField || null });
    },
    [mapping, setMapping],
  );

  const handleLoadPreset = useCallback(
    (preset) => {
      setMapping(preset.mapping);
    },
    [setMapping],
  );

  const handleSavePreset = useCallback(async () => {
    if (!presetName.trim()) return;
    try {
      const saved = await savePreset({
        name: presetName.trim(),
        dataType,
        mapping,
      });
      setPresets((prev) => {
        const exists = prev.findIndex((p) => p.id === saved.id);
        if (exists >= 0) {
          const next = [...prev];
          next[exists] = saved;
          return next;
        }
        return [saved, ...prev];
      });
      setPresetName('');
      setShowSavePreset(false);
    } catch {
      // error handled by global interceptor
    }
  }, [presetName, dataType, mapping]);

  const handleDeletePreset = useCallback(async (id) => {
    try {
      await deletePreset(id);
      setPresets((prev) => prev.filter((p) => p.id !== id));
    } catch {
      // error handled by global interceptor
    }
  }, []);

  // Compute mapped required fields for validation
  const targetFieldEntries = Object.entries(targetFields);
  const requiredFields = targetFieldEntries
    .filter(([, info]) => info.required)
    .map(([key]) => key);
  const mappedTargets = Object.values(mapping).filter(Boolean);
  const missingRequired = requiredFields.filter((f) => !mappedTargets.includes(f));

  return (
    <div className="space-y-5">
      {/* Preset bar */}
      <div className="flex flex-wrap items-center gap-3">
        <span className="text-sm font-medium text-gray-600">預設映射:</span>
        {presets.length === 0 && (
          <span className="text-xs text-gray-400">尚無儲存的預設</span>
        )}
        {presets.map((p) => (
          <div key={p.id} className="group inline-flex items-center gap-1">
            <button
              onClick={() => handleLoadPreset(p)}
              className="rounded border border-gray-200 bg-white px-3 py-1 text-xs font-medium text-gray-600 transition-colors hover:bg-gray-50"
            >
              {p.name}
            </button>
            <button
              onClick={() => handleDeletePreset(p.id)}
              className="hidden text-gray-400 hover:text-red-500 group-hover:inline-block"
              title="刪除預設"
            >
              <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        ))}
        <button
          onClick={() => setShowSavePreset(!showSavePreset)}
          className="rounded border border-dashed border-gray-300 px-3 py-1 text-xs text-gray-500 hover:border-gray-400 hover:text-gray-700"
        >
          + 儲存目前映射
        </button>
      </div>

      {/* Save preset input */}
      {showSavePreset && (
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={presetName}
            onChange={(e) => setPresetName(e.target.value)}
            placeholder="預設名稱"
            className="rounded-lg border border-gray-200 px-3 py-1.5 text-sm focus:border-blue-400 focus:outline-none focus:ring-1 focus:ring-blue-400"
          />
          <button
            onClick={handleSavePreset}
            disabled={!presetName.trim()}
            className="rounded-lg bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:bg-gray-300"
          >
            儲存
          </button>
          <button
            onClick={() => setShowSavePreset(false)}
            className="text-sm text-gray-500 hover:text-gray-700"
          >
            取消
          </button>
        </div>
      )}

      {/* Mapping table */}
      <div className="overflow-x-auto rounded-lg border border-gray-200">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100 bg-gray-50">
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500">來源欄位</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500">範例資料</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500">對應目標欄位</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {headers.map((col) => (
              <tr key={col} className="hover:bg-blue-50/30">
                <td className="px-4 py-2.5 font-medium text-gray-800">{col}</td>
                <td className="max-w-[200px] truncate px-4 py-2.5 text-xs text-gray-500">
                  {sampleRows.slice(0, 2).map((row) => row[col]).filter(Boolean).join(', ')}
                </td>
                <td className="px-4 py-2.5">
                  <select
                    value={mapping[col] || ''}
                    onChange={(e) => handleMappingChange(col, e.target.value)}
                    className={`w-full rounded border px-2 py-1.5 text-sm focus:border-blue-400 focus:outline-none focus:ring-1 focus:ring-blue-400 ${
                      mapping[col] ? 'border-emerald-300 bg-emerald-50' : 'border-gray-200'
                    }`}
                  >
                    <option value="">-- 不匯入 --</option>
                    {targetFieldEntries.map(([key, info]) => (
                      <option key={key} value={key}>
                        {info.label || key}
                        {info.required ? ' *' : ''}
                      </option>
                    ))}
                  </select>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Validation hint */}
      {missingRequired.length > 0 && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-700">
          尚未映射的必填欄位: {missingRequired.map((f) => targetFields[f]?.label || f).join(', ')}
        </div>
      )}

      {/* Actions */}
      <div className="flex justify-end">
        <button
          onClick={doPreview}
          disabled={loading || missingRequired.length > 0}
          className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-medium text-white shadow-sm transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-gray-300"
        >
          {loading ? (
            <>
              <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              驗證中...
            </>
          ) : (
            '預覽與驗證'
          )}
        </button>
      </div>
    </div>
  );
}
