import { useState, useMemo, useCallback } from 'react';
import { formatCurrency, formatNumber, formatPercent } from '../../utils/formatters';

const SortIcon = ({ direction }) => (
  <svg className="ml-1 inline h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
    {direction === 'asc' ? (
      <path
        fillRule="evenodd"
        d="M5.293 9.707a1 1 0 010-1.414l4-4a1 1 0 011.414 0l4 4a1 1 0 01-1.414 1.414L11 7.414V15a1 1 0 11-2 0V7.414L6.707 9.707a1 1 0 01-1.414 0z"
        clipRule="evenodd"
      />
    ) : (
      <path
        fillRule="evenodd"
        d="M14.707 10.293a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 111.414-1.414L9 12.586V5a1 1 0 012 0v7.586l2.293-2.293a1 1 0 011.414 0z"
        clipRule="evenodd"
      />
    )}
  </svg>
);

const UnsortedIcon = () => (
  <svg className="ml-1 inline h-3.5 w-3.5 text-gray-300" viewBox="0 0 20 20" fill="currentColor">
    <path d="M5 9l5-5 5 5H5zM5 11l5 5 5-5H5z" />
  </svg>
);

const columns = [
  { key: 'rank', label: '排名', sortable: false, width: 'w-14', align: 'text-center' },
  { key: 'name', label: '市場名稱', sortable: true, width: 'flex-1', align: 'text-left' },
  { key: 'avgPrice', label: '平均價', sortable: true, width: 'w-28', align: 'text-right' },
  { key: 'volume', label: '交易量', sortable: true, width: 'w-28', align: 'text-right' },
  { key: 'share', label: '佔比', sortable: true, width: 'w-24', align: 'text-right' },
];

function RankBadge({ rank }) {
  if (rank <= 3) {
    const colors = [
      'bg-yellow-400 text-yellow-900',
      'bg-gray-300 text-gray-700',
      'bg-amber-600 text-amber-50',
    ];
    return (
      <span
        className={`inline-flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold ${colors[rank - 1]}`}
      >
        {rank}
      </span>
    );
  }
  return <span className="text-sm text-gray-500">{rank}</span>;
}

/**
 * Sortable table ranking top markets by trading volume or average price.
 *
 * @param {Object}  props
 * @param {Array}   props.markets  - Array of { name, avgPrice, volume, share }
 * @param {boolean} [props.loading=false]
 */
export default function TopMarketsTable({ markets = [], loading = false }) {
  const [sortKey, setSortKey] = useState('volume');
  const [sortDir, setSortDir] = useState('desc');

  const handleSort = useCallback(
    (key) => {
      if (!columns.find((c) => c.key === key)?.sortable) return;
      if (sortKey === key) {
        setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
      } else {
        setSortKey(key);
        setSortDir('desc');
      }
    },
    [sortKey],
  );

  const sorted = useMemo(() => {
    if (!markets.length) return [];
    const copy = [...markets];
    copy.sort((a, b) => {
      const aVal = a[sortKey] ?? 0;
      const bVal = b[sortKey] ?? 0;
      if (typeof aVal === 'string') {
        return sortDir === 'asc'
          ? aVal.localeCompare(bVal)
          : bVal.localeCompare(aVal);
      }
      return sortDir === 'asc' ? aVal - bVal : bVal - aVal;
    });
    return copy.map((m, i) => ({ ...m, rank: i + 1 }));
  }, [markets, sortKey, sortDir]);

  if (loading) {
    return (
      <div className="rounded-xl border border-gray-100 bg-white shadow-sm">
        <div className="border-b border-gray-100 px-5 py-4">
          <div className="h-5 w-32 animate-pulse rounded bg-gray-200" />
        </div>
        <div className="divide-y divide-gray-50 p-4">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="flex gap-4 py-3 animate-pulse">
              <div className="h-4 w-8 rounded bg-gray-100" />
              <div className="h-4 w-24 rounded bg-gray-100" />
              <div className="ml-auto h-4 w-16 rounded bg-gray-100" />
              <div className="h-4 w-16 rounded bg-gray-100" />
              <div className="h-4 w-12 rounded bg-gray-100" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-gray-100 bg-white shadow-sm">
      <div className="border-b border-gray-100 px-5 py-4">
        <h3 className="text-base font-semibold text-gray-800">市場排行</h3>
        <p className="mt-0.5 text-xs text-gray-400">
          依{sortKey === 'volume' ? '交易量' : sortKey === 'avgPrice' ? '平均價' : sortKey === 'share' ? '佔比' : '名稱'}
          {sortDir === 'desc' ? '降序' : '升序'}排列
        </p>
      </div>

      {sorted.length === 0 ? (
        <div className="flex h-40 items-center justify-center text-sm text-gray-400">
          暫無市場資料
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50/60">
                {columns.map((col) => (
                  <th
                    key={col.key}
                    onClick={() => handleSort(col.key)}
                    className={`px-4 py-3 text-xs font-semibold uppercase tracking-wider text-gray-500 ${col.align} ${col.width} ${
                      col.sortable ? 'cursor-pointer select-none hover:text-gray-700' : ''
                    }`}
                  >
                    {col.label}
                    {col.sortable &&
                      (sortKey === col.key ? (
                        <SortIcon direction={sortDir} />
                      ) : (
                        <UnsortedIcon />
                      ))}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {sorted.map((market) => (
                <tr
                  key={market.name}
                  className={`transition-colors hover:bg-blue-50/40 ${
                    market.rank <= 3 ? 'bg-amber-50/30' : market.rank % 2 === 0 ? 'bg-gray-50/30' : ''
                  }`}
                >
                  <td className="px-4 py-3 text-center">
                    <RankBadge rank={market.rank} />
                  </td>
                  <td className="px-4 py-3 text-left font-medium text-gray-800">
                    {market.name}
                  </td>
                  <td className="px-4 py-3 text-right tabular-nums text-gray-700">
                    {formatCurrency(market.avgPrice, 1)}
                  </td>
                  <td className="px-4 py-3 text-right tabular-nums text-gray-700">
                    {formatNumber(market.volume)}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <div className="h-1.5 w-16 overflow-hidden rounded-full bg-gray-100">
                        <div
                          className="h-full rounded-full bg-blue-500 transition-all"
                          style={{ width: `${Math.min((market.share || 0) * 100, 100)}%` }}
                        />
                      </div>
                      <span className="tabular-nums text-gray-600">
                        {formatPercent(market.share)}
                      </span>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
