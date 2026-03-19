import useUploadStore from '../../stores/useUploadStore';
import FileUploader from './FileUploader';
import ColumnMapper from './ColumnMapper';
import ImportPreview from './ImportPreview';
import ImportResult from './ImportResult';

const STEPS = [
  { key: 'upload', label: '上傳檔案' },
  { key: 'mapping', label: '欄位映射' },
  { key: 'preview', label: '預覽驗證' },
  { key: 'result', label: '匯入結果' },
];

function stepIndex(step) {
  if (step === 'idle') return 0;
  if (step === 'uploaded') return 1;
  if (step === 'previewing' || step === 'mapped') return 2;
  if (step === 'importing' || step === 'done') return 3;
  return 0;
}

export default function UploadWizard() {
  const step = useUploadStore((s) => s.step);
  const reset = useUploadStore((s) => s.reset);
  const current = stepIndex(step);

  return (
    <div className="space-y-6">
      {/* Step indicator */}
      <nav className="flex items-center justify-between">
        <ol className="flex w-full items-center gap-2">
          {STEPS.map((s, idx) => {
            const isActive = idx === current;
            const isDone = idx < current;
            return (
              <li key={s.key} className="flex flex-1 items-center">
                <div className="flex w-full flex-col items-center gap-1">
                  <div
                    className={`flex h-8 w-8 items-center justify-center rounded-full text-sm font-semibold transition-colors ${
                      isDone
                        ? 'bg-emerald-500 text-white'
                        : isActive
                          ? 'bg-blue-600 text-white'
                          : 'bg-gray-100 text-gray-400'
                    }`}
                  >
                    {isDone ? (
                      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                      </svg>
                    ) : (
                      idx + 1
                    )}
                  </div>
                  <span
                    className={`text-xs font-medium ${
                      isActive ? 'text-blue-600' : isDone ? 'text-emerald-600' : 'text-gray-400'
                    }`}
                  >
                    {s.label}
                  </span>
                </div>
                {idx < STEPS.length - 1 && (
                  <div
                    className={`mx-2 h-0.5 w-full rounded ${
                      idx < current ? 'bg-emerald-500' : 'bg-gray-200'
                    }`}
                  />
                )}
              </li>
            );
          })}
        </ol>
      </nav>

      {/* Step content */}
      {(step === 'idle') && <FileUploader />}
      {(step === 'uploaded') && <ColumnMapper />}
      {(step === 'previewing' || step === 'mapped') && <ImportPreview />}
      {(step === 'importing' || step === 'done') && <ImportResult />}

      {/* Error display */}
      <ErrorBanner />

      {/* Reset button (visible when not idle) */}
      {step !== 'idle' && (
        <div className="flex justify-end">
          <button
            onClick={reset}
            className="text-sm text-gray-500 underline hover:text-gray-700"
          >
            重新開始
          </button>
        </div>
      )}
    </div>
  );
}

function ErrorBanner() {
  const error = useUploadStore((s) => s.error);
  if (!error) return null;

  return (
    <div className="rounded-lg border border-red-200 bg-red-50 p-4">
      <div className="flex items-start gap-3">
        <svg className="mt-0.5 h-5 w-5 shrink-0 text-red-500" viewBox="0 0 20 20" fill="currentColor">
          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z" clipRule="evenodd" />
        </svg>
        <p className="text-sm text-red-700">{error}</p>
      </div>
    </div>
  );
}
