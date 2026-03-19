import useUploadStore from '../../stores/useUploadStore';
import { formatNumber } from '../../utils/formatters';

export default function ImportPreview() {
  const preview = useUploadStore((s) => s.preview);
  const doConfirm = useUploadStore((s) => s.doConfirm);
  const loading = useUploadStore((s) => s.loading);

  if (!preview) {
    return (
      <div className="flex h-40 items-center justify-center">
        <svg className="h-8 w-8 animate-spin text-blue-500" viewBox="0 0 24 24" fill="none">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      </div>
    );
  }

  const { total_rows, valid_rows, error_rows, duplicate_rows, errors, preview_data } = preview;
  const hasErrors = error_rows > 0;

  return (
    <div className="space-y-5">
      {/* Summary cards */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard label="總筆數" value={total_rows} />
        <StatCard label="有效筆數" value={valid_rows} color="emerald" />
        <StatCard label="錯誤筆數" value={error_rows} color={hasErrors ? 'red' : 'gray'} />
        <StatCard label="重複筆數" value={duplicate_rows} color={duplicate_rows > 0 ? 'amber' : 'gray'} />
      </div>

      {/* Error list */}
      {errors.length > 0 && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4">
          <h4 className="text-sm font-semibold text-red-700">驗證錯誤 (前 {Math.min(errors.length, 20)} 筆)</h4>
          <ul className="mt-2 max-h-40 space-y-1 overflow-y-auto text-xs text-red-600">
            {errors.slice(0, 20).map((err, idx) => (
              <li key={idx}>
                第 {err.row ?? idx + 1} 行: {err.message ?? err.error ?? JSON.stringify(err)}
              </li>
            ))}
          </ul>
          {errors.length > 20 && (
            <p className="mt-2 text-xs text-red-500">...還有 {errors.length - 20} 筆錯誤</p>
          )}
        </div>
      )}

      {/* Preview table */}
      {preview_data.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-gray-200">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50">
                {Object.keys(preview_data[0]).map((key) => (
                  <th key={key} className="px-3 py-2 text-left text-xs font-semibold text-gray-500">
                    {key}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {preview_data.slice(0, 10).map((row, idx) => (
                <tr key={idx} className="hover:bg-blue-50/30">
                  {Object.values(row).map((val, ci) => (
                    <td key={ci} className="max-w-[160px] truncate px-3 py-2 text-xs text-gray-700">
                      {val ?? '-'}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          {preview_data.length > 10 && (
            <p className="border-t border-gray-100 px-4 py-2 text-xs text-gray-400">
              顯示前 10 筆，共 {preview_data.length} 筆有效資料
            </p>
          )}
        </div>
      )}

      {/* Confirm button */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-500">
          {valid_rows > 0
            ? `確認後將匯入 ${formatNumber(valid_rows)} 筆資料${hasErrors ? '（錯誤筆數將跳過）' : ''}`
            : '沒有可匯入的有效資料'}
        </p>
        <button
          onClick={() => doConfirm(true)}
          disabled={loading || valid_rows === 0}
          className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-5 py-2.5 text-sm font-medium text-white shadow-sm transition-colors hover:bg-emerald-700 disabled:cursor-not-allowed disabled:bg-gray-300"
        >
          {loading ? (
            <>
              <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              匯入中...
            </>
          ) : (
            '確認匯入'
          )}
        </button>
      </div>
    </div>
  );
}

function StatCard({ label, value, color = 'gray' }) {
  const colorMap = {
    gray: 'bg-gray-50 text-gray-800',
    emerald: 'bg-emerald-50 text-emerald-700',
    red: 'bg-red-50 text-red-700',
    amber: 'bg-amber-50 text-amber-700',
  };

  return (
    <div className={`rounded-lg p-4 ${colorMap[color]}`}>
      <p className="text-xs font-medium opacity-70">{label}</p>
      <p className="mt-1 text-xl font-bold tabular-nums">{formatNumber(value)}</p>
    </div>
  );
}
