import { useState, useEffect } from 'react';

export default function Header({ onToggleFilter, filterOpen }) {
  const [backendUp, setBackendUp] = useState(null);

  useEffect(() => {
    let cancelled = false;
    const check = () =>
      fetch('/api/v1/crops')
        .then((r) => { if (!cancelled) setBackendUp(r.ok); })
        .catch(() => { if (!cancelled) setBackendUp(false); });
    check();
    const id = setInterval(check, 30000);
    return () => { cancelled = true; clearInterval(id); };
  }, []);

  return (
    <header className="fixed top-0 right-0 left-0 z-40 border-b border-gray-800 bg-gray-900 shadow-lg">
      <div className="flex h-16 items-center justify-between px-4 lg:px-6">
        {/* Left section: logo */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-600">
              <svg className="h-5 w-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <h1 className="hidden text-lg font-semibold tracking-tight text-white sm:block">
              台灣農產品產銷量預測系統
            </h1>
            <h1 className="text-lg font-semibold tracking-tight text-white sm:hidden">
              農產預測
            </h1>
          </div>
        </div>

        {/* Right section: filter toggle (mobile) + status indicator */}
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={onToggleFilter}
            className="rounded-lg p-2 text-gray-400 hover:bg-gray-800 hover:text-white md:hidden"
            aria-label="Toggle filters"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
            </svg>
          </button>
          <div className="flex items-center gap-2 rounded-lg bg-gray-800 px-3 py-1.5">
            <span className={`h-2 w-2 rounded-full ${backendUp === null ? 'bg-gray-400' : backendUp ? 'bg-emerald-400' : 'bg-red-400'}`} />
            <span className="hidden text-xs text-gray-400 sm:inline">
              {backendUp === null ? '檢查中...' : backendUp ? '系統運行中' : '系統離線'}
            </span>
          </div>
        </div>
      </div>
    </header>
  );
}
