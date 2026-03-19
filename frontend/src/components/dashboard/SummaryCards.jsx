import { useMemo } from 'react';
import { formatCurrency, formatNumber, formatPercent } from '../../utils/formatters';

const ArrowUp = () => (
  <svg className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
    <path
      fillRule="evenodd"
      d="M5.293 9.707a1 1 0 010-1.414l4-4a1 1 0 011.414 0l4 4a1 1 0 01-1.414 1.414L11 7.414V15a1 1 0 11-2 0V7.414L6.707 9.707a1 1 0 01-1.414 0z"
      clipRule="evenodd"
    />
  </svg>
);

const ArrowDown = () => (
  <svg className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
    <path
      fillRule="evenodd"
      d="M14.707 10.293a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 111.414-1.414L9 12.586V5a1 1 0 012 0v7.586l2.293-2.293a1 1 0 011.414 0z"
      clipRule="evenodd"
    />
  </svg>
);

const icons = {
  price: (
    <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v12m-3-2.818.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  trend: (
    <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 18L9 11.25l4.306 4.307a11.95 11.95 0 015.814-5.519l2.74-1.22m0 0l-5.94-2.28m5.94 2.28l-2.28 5.941" />
    </svg>
  ),
  volume: (
    <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" />
    </svg>
  ),
  yearly: (
    <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 012.25-2.25h13.5A2.25 2.25 0 0121 7.5v11.25m-18 0A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75m-18 0v-7.5A2.25 2.25 0 015.25 9h13.5A2.25 2.25 0 0121 11.25v7.5" />
    </svg>
  ),
};

const getCardConfigs = (data) => [
  {
    key: 'latestPrice',
    label: '最新均價',
    icon: 'price',
    format: (v) => formatCurrency(v, 1),
    colorClass: 'bg-blue-50 text-blue-600',
    trendKey: 'priceChange',
    unit: data?.priceUnit || '元/公斤',
  },
  {
    key: 'priceChange',
    label: '月增率',
    icon: 'trend',
    format: (v) => formatPercent(v),
    colorClass: 'bg-amber-50 text-amber-600',
    trendKey: 'priceChange',
    unit: '',
  },
  {
    key: 'monthlyVolume',
    label: '本月交易量',
    icon: 'volume',
    format: (v) => formatNumber(v),
    colorClass: 'bg-emerald-50 text-emerald-600',
    trendKey: 'volumeChange',
    unit: data?.volumeUnit || '公斤',
  },
  {
    key: 'yearlyVolume',
    label: '年交易總量',
    icon: 'yearly',
    format: (v) => formatNumber(v),
    colorClass: 'bg-purple-50 text-purple-600',
    trendKey: 'yearlyChange',
    unit: data?.volumeUnit || '公斤',
  },
];

function SkeletonCard() {
  return (
    <div className="rounded-xl border border-gray-100 bg-white p-5 shadow-sm animate-pulse">
      <div className="flex items-center gap-3">
        <div className="h-10 w-10 rounded-lg bg-gray-200" />
        <div className="h-4 w-20 rounded bg-gray-200" />
      </div>
      <div className="mt-4 h-7 w-28 rounded bg-gray-200" />
      <div className="mt-2 h-4 w-16 rounded bg-gray-100" />
    </div>
  );
}

/**
 * KPI summary cards displayed at the top of the dashboard.
 *
 * @param {Object}  props
 * @param {Object}  props.data - { latestPrice, priceChange, monthlyVolume, yearlyVolume, volumeChange, yearlyChange }
 * @param {boolean} [props.loading=false]
 */
export default function SummaryCards({ data, loading = false }) {
  const cards = useMemo(
    () =>
      getCardConfigs(data).map((cfg) => {
        const rawValue = data?.[cfg.key];
        const trendValue = data?.[cfg.trendKey];
        const isPositive = trendValue != null && trendValue > 0;
        const isNegative = trendValue != null && trendValue < 0;
        const isNeutral = trendValue == null || trendValue === 0;

        return {
          ...cfg,
          displayValue: rawValue != null ? cfg.format(rawValue) : '-',
          isPositive,
          isNegative,
          isNeutral,
          trendLabel:
            trendValue != null
              ? `${isPositive ? '+' : ''}${formatPercent(trendValue)}`
              : null,
        };
      }),
    [data],
  );

  if (loading) {
    return (
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {cards.map((card) => (
        <div
          key={card.key}
          className="group relative overflow-hidden rounded-xl border border-gray-100 bg-white p-5 shadow-sm transition-shadow hover:shadow-md"
        >
          {/* Decorative gradient bar at top */}
          <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-blue-500 to-cyan-400 opacity-0 transition-opacity group-hover:opacity-100" />

          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${card.colorClass}`}>
                {icons[card.icon]}
              </div>
              <span className="text-sm font-medium text-gray-500">{card.label}</span>
            </div>
          </div>

          <div className="mt-4 flex items-end justify-between">
            <div>
              <p className="text-2xl font-bold tracking-tight text-gray-900">
                {card.displayValue}
              </p>
              {card.unit && (
                <p className="mt-0.5 text-xs text-gray-400">{card.unit}</p>
              )}
            </div>

            {card.trendLabel && (
              <div
                className={`flex items-center gap-0.5 rounded-full px-2 py-1 text-xs font-semibold ${
                  card.isPositive
                    ? 'bg-emerald-50 text-emerald-600'
                    : card.isNegative
                    ? 'bg-red-50 text-red-600'
                    : 'bg-gray-50 text-gray-500'
                }`}
              >
                {card.isPositive && <ArrowUp />}
                {card.isNegative && <ArrowDown />}
                {card.trendLabel}
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
