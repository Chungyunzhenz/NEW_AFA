import { useState, useCallback } from 'react';
import Header from './Header';
import FilterBar from './FilterBar';

export default function MainLayout({ children }) {
  const [filterOpen, setFilterOpen] = useState(false);

  const toggleFilter = useCallback(() => setFilterOpen((v) => !v), []);

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900">
      <Header onToggleFilter={toggleFilter} filterOpen={filterOpen} />

      <FilterBar mobileOpen={filterOpen} onToggleMobile={toggleFilter} />

      {/* Main content area - offset by header + filter bar height */}
      <main className="pt-24">
        <div className="mx-auto max-w-screen-2xl px-4 py-6 sm:px-6 lg:px-8">
          {children}
        </div>
      </main>
    </div>
  );
}
