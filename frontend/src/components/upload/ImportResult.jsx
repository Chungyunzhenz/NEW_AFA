import useUploadStore from '../../stores/useUploadStore';
import { formatNumber } from '../../utils/formatters';

export default function ImportResult() {
  const result = useUploadStore((s) => s.result);
  const loading = useUploadStore((s) => s.loading);
  const reset = useUploadStore((s) => s.reset);

  if (loading || !result) {
    return (
      <div className="flex h-40 items-center justify-center">
        <div className="text-center">
          <svg className="mx-auto h-8 w-8 animate-spin text-blue-500" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          <p className="mt-3 text-sm text-gray-500">正在匯入資料...</p>
        </div>
      </div>
    );
  }

  const { inserted, skipped_duplicate, skipped_error, total_processed } = result;
  const allGood = skipped_error === 0;

  return (
    <div className="space-y-6">
      {/* Success / partial success banner */}
      <div
        className={`rounded-xl border p-6 ${
          allGood
            ? 'border-emerald-200 bg-emerald-50'
            : 'border-amber-200 bg-amber-50'
        }`}
      >
        <div className="flex items-center gap-3">
          {allGood ? (
            <svg className="h-8 w-8 text-emerald-500" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          ) : (
            <svg className="h-8 w-8 text-amber-500" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.168 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
            </svg>
          )}
          <div>
            <h3
              className={`text-lg font-semibold ${
                allGood ? 'text-emerald-800' : 'text-amber-800'
              }`}
            >
              {allGood ? '匯入完成' : '匯入完成（部分跳過）'}
            </h3>
            <p className={`mt-1 text-sm ${allGood ? 'text-emerald-600' : 'text-amber-600'}`}>
              共處理 {formatNumber(total_processed)} 筆資料
            </p>
          </div>
        </div>
      </div>

      {/* Result stats */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-lg bg-emerald-50 p-4">
          <p className="text-xs font-medium text-emerald-600">成功匯入</p>
          <p className="mt-1 text-2xl font-bold tabular-nums text-emerald-700">
            {formatNumber(inserted)}
          </p>
        </div>
        <div className="rounded-lg bg-gray-50 p-4">
          <p className="text-xs font-medium text-gray-500">跳過（重複）</p>
          <p className="mt-1 text-2xl font-bold tabular-nums text-gray-700">
            {formatNumber(skipped_duplicate)}
          </p>
        </div>
        <div className="rounded-lg bg-red-50 p-4">
          <p className="text-xs font-medium text-red-500">跳過（錯誤）</p>
          <p className="mt-1 text-2xl font-bold tabular-nums text-red-700">
            {formatNumber(skipped_error)}
          </p>
        </div>
      </div>

      {/* Action buttons */}
      <div className="flex justify-end gap-3">
        <button
          onClick={reset}
          className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-medium text-white shadow-sm transition-colors hover:bg-blue-700"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
          </svg>
          繼續匯入其他檔案
        </button>
      </div>
    </div>
  );
}
