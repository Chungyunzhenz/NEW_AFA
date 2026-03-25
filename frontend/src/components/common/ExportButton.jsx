import { useState } from 'react';

export default function ExportButton({ url, filename, label = '匯出', format = 'CSV' }) {
  const [loading, setLoading] = useState(false);

  async function handleExport() {
    setLoading(true);
    try {
      const response = await fetch(`/api/v1${url}`, { method: 'GET' });
      if (!response.ok) throw new Error('Export failed');
      const blob = await response.blob();
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = filename || 'export.csv';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(a.href);
    } catch (err) {
      console.error('Export error:', err);
    } finally {
      setLoading(false);
    }
  }

  return (
    <button
      onClick={handleExport}
      disabled={loading}
      className="inline-flex items-center gap-1.5 rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 shadow-sm transition hover:bg-gray-50 disabled:opacity-50"
    >
      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
      </svg>
      {loading ? '匯出中...' : `${label} ${format}`}
    </button>
  );
}
