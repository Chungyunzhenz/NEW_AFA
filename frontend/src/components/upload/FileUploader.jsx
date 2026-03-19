import { useState, useCallback, useRef } from 'react';
import useUploadStore from '../../stores/useUploadStore';

const DATA_TYPE_OPTIONS = [
  { value: 'trading', label: '交易資料' },
  { value: 'production', label: '產量資料' },
  { value: 'weather', label: '氣象資料' },
];

export default function FileUploader() {
  const doUpload = useUploadStore((s) => s.doUpload);
  const loading = useUploadStore((s) => s.loading);

  const [dataType, setDataType] = useState('trading');
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const inputRef = useRef(null);

  const handleFile = useCallback((file) => {
    if (!file) return;
    const ext = file.name.split('.').pop()?.toLowerCase();
    if (!['csv', 'xlsx', 'xls'].includes(ext)) {
      alert('僅支援 CSV 或 Excel (.xlsx/.xls) 檔案');
      return;
    }
    if (file.size > 50 * 1024 * 1024) {
      alert('檔案大小不可超過 50 MB');
      return;
    }
    setSelectedFile(file);
  }, []);

  const handleDrop = useCallback(
    (e) => {
      e.preventDefault();
      setDragActive(false);
      const file = e.dataTransfer.files?.[0];
      handleFile(file);
    },
    [handleFile],
  );

  const handleSubmit = useCallback(() => {
    if (selectedFile) {
      doUpload(selectedFile, dataType);
    }
  }, [selectedFile, dataType, doUpload]);

  return (
    <div className="space-y-5">
      {/* Data type selector */}
      <div>
        <label className="block text-sm font-medium text-gray-700">資料類型</label>
        <div className="mt-2 flex gap-3">
          {DATA_TYPE_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => setDataType(opt.value)}
              className={`rounded-lg border px-4 py-2 text-sm font-medium transition-colors ${
                dataType === opt.value
                  ? 'border-blue-500 bg-blue-50 text-blue-700'
                  : 'border-gray-200 bg-white text-gray-600 hover:bg-gray-50'
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Drop zone */}
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragActive(true);
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        className={`flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed p-10 transition-colors ${
          dragActive
            ? 'border-blue-400 bg-blue-50'
            : selectedFile
              ? 'border-emerald-300 bg-emerald-50'
              : 'border-gray-200 bg-gray-50 hover:border-gray-300 hover:bg-gray-100'
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".csv,.xlsx,.xls"
          className="hidden"
          onChange={(e) => handleFile(e.target.files?.[0])}
        />

        {selectedFile ? (
          <>
            <svg className="h-10 w-10 text-emerald-500" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
            </svg>
            <p className="mt-3 text-sm font-medium text-gray-800">{selectedFile.name}</p>
            <p className="mt-1 text-xs text-gray-500">
              {(selectedFile.size / 1024).toFixed(1)} KB
            </p>
            <p className="mt-2 text-xs text-gray-400">點擊可重新選擇檔案</p>
          </>
        ) : (
          <>
            <svg className="h-10 w-10 text-gray-400" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
            </svg>
            <p className="mt-3 text-sm font-medium text-gray-600">
              拖放檔案到此處，或點擊選擇檔案
            </p>
            <p className="mt-1 text-xs text-gray-400">
              支援 CSV, Excel (.xlsx, .xls)，上限 50 MB
            </p>
          </>
        )}
      </div>

      {/* Upload button */}
      {selectedFile && (
        <div className="flex justify-end">
          <button
            onClick={handleSubmit}
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-medium text-white shadow-sm transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-blue-400"
          >
            {loading ? (
              <>
                <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                上傳中...
              </>
            ) : (
              '上傳並解析'
            )}
          </button>
        </div>
      )}
    </div>
  );
}
