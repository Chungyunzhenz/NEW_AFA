import { useState, useCallback } from 'react';
import useFilterStore from '../../stores/useFilterStore';
import CropSelector from '../filters/CropSelector';
import DateRangePicker from '../filters/DateRangePicker';
import GranularitySelector from '../filters/GranularitySelector';
import MetricSelector from '../filters/MetricSelector';

/**
 * Thin vertical divider between filter controls (desktop only).
 */
function Divider() {
  return <div className="h-5 w-px bg-gray-200 shrink-0" />;
}

/**
 * Horizontal filter bar that sits below the Header.
 * Desktop: all controls in a compact single row.
 * Mobile: summary row with toggle to expand a vertical panel.
 */
export default function FilterBar({ mobileOpen, onToggleMobile }) {
  const resetFilters = useFilterStore((s) => s.resetFilters);

  return (
    <div className="sticky top-16 z-30 border-b border-gray-100 bg-white/95 backdrop-blur-sm">
      {/* Desktop: compact horizontal row */}
      <div className="mx-auto hidden max-w-screen-2xl items-center gap-3 px-4 py-2 md:flex lg:px-6">
        <CropSelector compact />
        <Divider />
        <DateRangePicker compact />
        <Divider />
        <GranularitySelector compact />
        <Divider />
        <MetricSelector compact />
        <button
          type="button"
          onClick={resetFilters}
          className="ml-auto shrink-0 rounded-full px-3 py-1.5 text-xs text-gray-400 transition hover:text-red-500 hover:bg-red-50 active:scale-95"
          title="重置所有篩選"
        >
          <span className="flex items-center gap-1">
            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182" />
            </svg>
            重置
          </span>
        </button>
      </div>

      {/* Mobile: expandable panel */}
      {mobileOpen && (
        <div className="space-y-4 border-t border-gray-100 px-4 py-4 md:hidden">
          <CropSelector />
          <DateRangePicker />
          <div className="flex items-end gap-4">
            <GranularitySelector />
            <MetricSelector />
          </div>
          <button
            type="button"
            onClick={resetFilters}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm font-medium text-gray-500 transition hover:bg-gray-50 hover:text-gray-700"
          >
            重置篩選
          </button>
        </div>
      )}
    </div>
  );
}
