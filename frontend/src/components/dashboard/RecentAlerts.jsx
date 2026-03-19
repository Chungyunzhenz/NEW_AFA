import { useMemo } from 'react';
import { formatDate } from '../../utils/formatters';

const WarningIcon = () => (
  <svg className="h-5 w-5 shrink-0" viewBox="0 0 20 20" fill="currentColor">
    <path
      fillRule="evenodd"
      d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.168 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z"
      clipRule="evenodd"
    />
  </svg>
);

const DangerIcon = () => (
  <svg className="h-5 w-5 shrink-0" viewBox="0 0 20 20" fill="currentColor">
    <path
      fillRule="evenodd"
      d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z"
      clipRule="evenodd"
    />
  </svg>
);

const InfoIcon = () => (
  <svg className="h-5 w-5 shrink-0" viewBox="0 0 20 20" fill="currentColor">
    <path
      fillRule="evenodd"
      d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a.75.75 0 000 1.5h.253a.25.25 0 01.244.304l-.459 2.066A1.75 1.75 0 0010.747 15H11a.75.75 0 000-1.5h-.253a.25.25 0 01-.244-.304l.459-2.066A1.75 1.75 0 009.253 9H9z"
      clipRule="evenodd"
    />
  </svg>
);

const severityConfig = {
  danger: {
    icon: <DangerIcon />,
    bgClass: 'bg-red-50 border-red-100',
    iconClass: 'text-red-500',
    textClass: 'text-red-800',
    dateClass: 'text-red-400',
    dotClass: 'bg-red-500',
  },
  warning: {
    icon: <WarningIcon />,
    bgClass: 'bg-amber-50 border-amber-100',
    iconClass: 'text-amber-500',
    textClass: 'text-amber-800',
    dateClass: 'text-amber-400',
    dotClass: 'bg-amber-500',
  },
  info: {
    icon: <InfoIcon />,
    bgClass: 'bg-blue-50 border-blue-100',
    iconClass: 'text-blue-500',
    textClass: 'text-blue-800',
    dateClass: 'text-blue-400',
    dotClass: 'bg-blue-500',
  },
};

function AlertItem({ alert }) {
  const config = severityConfig[alert.severity] || severityConfig.info;

  return (
    <div
      className={`flex items-start gap-3 rounded-lg border p-3 transition-colors hover:brightness-95 ${config.bgClass}`}
    >
      <div className={`mt-0.5 ${config.iconClass}`}>{config.icon}</div>
      <div className="min-w-0 flex-1">
        <p className={`text-sm font-medium leading-snug ${config.textClass}`}>
          {alert.message}
        </p>
        <div className="mt-1.5 flex items-center gap-2">
          <span className={`h-1.5 w-1.5 rounded-full ${config.dotClass}`} />
          <span className={`text-xs ${config.dateClass}`}>
            {formatDate(alert.date, 'yyyy/MM/dd HH:mm')}
          </span>
          {alert.crop && (
            <span className="rounded bg-white/60 px-1.5 py-0.5 text-xs font-medium text-gray-600">
              {alert.crop}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

/**
 * Scrollable list of recent abnormal price/volume alerts.
 *
 * @param {Object}  props
 * @param {Array}   props.alerts  - Array of { id, severity ('danger'|'warning'|'info'), message, date, crop? }
 * @param {boolean} [props.loading=false]
 * @param {number}  [props.maxHeight=420] - Max container height in pixels.
 */
export default function RecentAlerts({ alerts = [], loading = false, maxHeight = 420 }) {
  const sorted = useMemo(() => {
    const severityOrder = { danger: 0, warning: 1, info: 2 };
    return [...alerts].sort((a, b) => {
      const sDiff = (severityOrder[a.severity] ?? 9) - (severityOrder[b.severity] ?? 9);
      if (sDiff !== 0) return sDiff;
      return new Date(b.date) - new Date(a.date);
    });
  }, [alerts]);

  const dangerCount = useMemo(
    () => alerts.filter((a) => a.severity === 'danger').length,
    [alerts],
  );
  const warningCount = useMemo(
    () => alerts.filter((a) => a.severity === 'warning').length,
    [alerts],
  );

  if (loading) {
    return (
      <div className="rounded-xl border border-gray-100 bg-white shadow-sm">
        <div className="border-b border-gray-100 px-5 py-4">
          <div className="h-5 w-24 animate-pulse rounded bg-gray-200" />
        </div>
        <div className="space-y-3 p-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-16 animate-pulse rounded-lg bg-gray-100" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-gray-100 bg-white shadow-sm">
      <div className="flex items-center justify-between border-b border-gray-100 px-5 py-4">
        <div>
          <h3 className="text-base font-semibold text-gray-800">異常警示</h3>
          <p className="mt-0.5 text-xs text-gray-400">
            價格或交易量異常變動通知
          </p>
        </div>
        <div className="flex items-center gap-2">
          {dangerCount > 0 && (
            <span className="inline-flex items-center rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-semibold text-red-700">
              {dangerCount} 嚴重
            </span>
          )}
          {warningCount > 0 && (
            <span className="inline-flex items-center rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-semibold text-amber-700">
              {warningCount} 警告
            </span>
          )}
        </div>
      </div>

      {sorted.length === 0 ? (
        <div className="flex h-32 items-center justify-center text-sm text-gray-400">
          <div className="text-center">
            <svg className="mx-auto h-8 w-8 text-gray-300" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p className="mt-2">目前無異常警示</p>
          </div>
        </div>
      ) : (
        <div
          className="space-y-2 overflow-y-auto p-4"
          style={{ maxHeight }}
        >
          {sorted.map((alert) => (
            <AlertItem key={alert.id ?? `${alert.date}-${alert.message}`} alert={alert} />
          ))}
        </div>
      )}
    </div>
  );
}
