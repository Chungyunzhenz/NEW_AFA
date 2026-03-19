import { useState, useEffect, useCallback, useRef } from 'react';
import usePredictionStore from '../stores/usePredictionStore';
import { fetchSyncStatus, triggerSync } from '../api/sync';
import { formatDate, formatNumber } from '../utils/formatters';
import UploadWizard from '../components/upload/UploadWizard';

const TABS = [
  { key: 'sync', label: '資料同步' },
  { key: 'import', label: '資料匯入' },
];

/* ------------------------------------------------------------------ */
/*  Sync status badge                                                 */
/* ------------------------------------------------------------------ */
function SyncStatusBadge({ status }) {
  const config = {
    success: { label: '同步成功', dot: 'bg-emerald-500', bg: 'bg-emerald-50 text-emerald-700' },
    failed: { label: '同步失敗', dot: 'bg-red-500', bg: 'bg-red-50 text-red-700' },
    syncing: { label: '同步中...', dot: 'bg-blue-500 animate-pulse', bg: 'bg-blue-50 text-blue-700' },
    idle: { label: '待同步', dot: 'bg-gray-400', bg: 'bg-gray-50 text-gray-600' },
  };
  const c = config[status] || config.idle;

  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold ${c.bg}`}>
      <span className={`h-2 w-2 rounded-full ${c.dot}`} />
      {c.label}
    </span>
  );
}

/* ------------------------------------------------------------------ */
/*  Last sync info card                                               */
/* ------------------------------------------------------------------ */
function SyncStatusCard({ syncInfo, onSync, syncing }) {
  return (
    <div className="rounded-xl border border-gray-100 bg-white p-6 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h3 className="text-base font-semibold text-gray-800">資料同步狀態</h3>
          <p className="mt-1 text-xs text-gray-400">
            農委會公開資料自動同步
          </p>
        </div>
        <SyncStatusBadge status={syncing ? 'syncing' : syncInfo?.status || 'idle'} />
      </div>

      <div className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-lg bg-gray-50 p-4">
          <p className="text-xs font-medium text-gray-500">最後同步時間</p>
          <p className="mt-1 text-sm font-semibold text-gray-800">
            {syncInfo?.lastSync ? formatDate(syncInfo.lastSync, 'yyyy/MM/dd HH:mm') : '-'}
          </p>
        </div>
        <div className="rounded-lg bg-gray-50 p-4">
          <p className="text-xs font-medium text-gray-500">資料更新至</p>
          <p className="mt-1 text-sm font-semibold text-gray-800">
            {syncInfo?.dataUpTo ? formatDate(syncInfo.dataUpTo) : '-'}
          </p>
        </div>
        <div className="rounded-lg bg-gray-50 p-4">
          <p className="text-xs font-medium text-gray-500">總記錄數</p>
          <p className="mt-1 text-sm font-semibold text-gray-800">
            {syncInfo?.totalRecords ? formatNumber(syncInfo.totalRecords) : '-'}
          </p>
        </div>
      </div>

      <div className="mt-5 flex items-center gap-3">
        <button
          onClick={onSync}
          disabled={syncing}
          className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:bg-blue-400"
        >
          {syncing ? (
            <>
              <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              同步中...
            </>
          ) : (
            <>
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182" />
              </svg>
              手動同步
            </>
          )}
        </button>
        {syncInfo?.lastError && (
          <span className="text-xs text-red-500">
            上次錯誤: {syncInfo.lastError}
          </span>
        )}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Data coverage table                                               */
/* ------------------------------------------------------------------ */
function DataCoverageTable({ crops, loading }) {
  if (loading) {
    return (
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100 bg-gray-50/60">
              {['作物', '交易記錄', '產量記錄'].map((h) => (
                <th key={h} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {Array.from({ length: 5 }).map((_, i) => (
              <tr key={i} className="border-b border-gray-50 animate-pulse">
                {Array.from({ length: 3 }).map((__, j) => (
                  <td key={j} className="px-4 py-3">
                    <div className="h-4 w-20 rounded bg-gray-100" />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  if (!crops?.length) {
    return (
      <div className="flex h-40 items-center justify-center text-sm text-gray-400">
        暫無作物資料
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-100 bg-gray-50/60">
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">作物</th>
            <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">交易記錄</th>
            <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500">產量記錄</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-50">
          {crops.map((crop, idx) => (
            <tr
              key={crop.crop_key ?? idx}
              className={`transition-colors hover:bg-blue-50/30 ${idx % 2 === 0 ? '' : 'bg-gray-50/30'}`}
            >
              <td className="px-4 py-2.5 font-medium text-gray-800">
                {crop.display_name_zh ?? crop.crop_key ?? '-'}
              </td>
              <td className="px-4 py-2.5 text-right tabular-nums text-gray-700">
                {formatNumber(crop.trading_records ?? 0)}
              </td>
              <td className="px-4 py-2.5 text-right tabular-nums text-gray-700">
                {formatNumber(crop.production_records ?? 0)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Retrain section                                                   */
/* ------------------------------------------------------------------ */
function RetrainSection({ onRetrain, retrainStatus }) {
  const statusConfig = {
    pending: { text: '訓練排程中...', color: 'text-blue-600' },
    success: { text: '訓練完成', color: 'text-emerald-600' },
    failed: { text: '訓練失敗', color: 'text-red-600' },
  };
  const statusInfo = retrainStatus ? statusConfig[retrainStatus] : null;

  return (
    <div className="rounded-xl border border-gray-100 bg-white p-6 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h3 className="text-base font-semibold text-gray-800">模型重新訓練</h3>
          <p className="mt-1 text-xs text-gray-400">
            手動觸發預測模型重新訓練
          </p>
        </div>
        {statusInfo && (
          <span className={`text-sm font-medium ${statusInfo.color}`}>
            {statusInfo.text}
          </span>
        )}
      </div>

      <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-4">
        <div className="flex items-start gap-3">
          <svg className="mt-0.5 h-5 w-5 shrink-0 text-amber-500" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.168 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
          </svg>
          <div className="text-sm text-amber-800">
            <p className="font-medium">注意事項</p>
            <p className="mt-1 text-amber-700">
              重新訓練模型可能需要數分鐘。訓練期間預測功能將使用上一版本模型。
              建議在同步新資料後再執行重新訓練。
            </p>
          </div>
        </div>
      </div>

      <div className="mt-4">
        <button
          onClick={onRetrain}
          disabled={retrainStatus === 'pending'}
          className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:bg-indigo-400"
        >
          {retrainStatus === 'pending' ? (
            <>
              <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              訓練中...
            </>
          ) : (
            <>
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0112 15a9.065 9.065 0 00-6.23.693L5 14.5m14.8.8l1.402 1.402c1.232 1.232.65 3.318-1.067 3.611A48.309 48.309 0 0112 21c-2.773 0-5.491-.235-8.135-.687-1.718-.293-2.3-2.379-1.067-3.61L5 14.5" />
              </svg>
              開始重新訓練
            </>
          )}
        </button>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Alert history list                                                */
/* ------------------------------------------------------------------ */
function AlertHistory({ alerts }) {
  if (!alerts?.length) {
    return (
      <div className="flex h-32 items-center justify-center text-sm text-gray-400">
        <div className="text-center">
          <svg className="mx-auto h-8 w-8 text-gray-300" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0" />
          </svg>
          <p className="mt-2">暫無系統通知</p>
        </div>
      </div>
    );
  }

  return (
    <div className="divide-y divide-gray-50">
      {alerts.map((alert, idx) => (
        <div key={alert.id ?? idx} className="flex items-start gap-3 px-5 py-3">
          <div className={`mt-1 h-2 w-2 shrink-0 rounded-full ${
            alert.type === 'error'
              ? 'bg-red-500'
              : alert.type === 'warning'
              ? 'bg-amber-500'
              : 'bg-blue-500'
          }`} />
          <div className="min-w-0 flex-1">
            <p className="text-sm text-gray-700">{alert.message}</p>
            <p className="mt-0.5 text-xs text-gray-400">
              {formatDate(alert.date ?? alert.createdAt, 'yyyy/MM/dd HH:mm')}
            </p>
          </div>
        </div>
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Helper: parse /sync/status response into component-friendly shape */
/* ------------------------------------------------------------------ */
function parseSyncStatusResponse(data) {
  const totalTrading = (data.crops ?? []).reduce((s, c) => s + (c.trading_records ?? 0), 0);
  const totalProduction = (data.crops ?? []).reduce((s, c) => s + (c.production_records ?? 0), 0);
  const taskRunning = data.sync_task?.is_running ?? false;
  const taskStatus = data.sync_task?.last_status; // "success" | "failed" | null

  let status = 'idle';
  if (taskRunning) status = 'syncing';
  else if (taskStatus === 'success') status = 'success';
  else if (taskStatus === 'failed') status = 'failed';
  else if (totalTrading > 0) status = 'success';

  return {
    status,
    lastSync: data.sync_task?.last_run_at ?? data.last_sync_time ?? null,
    dataUpTo: data.latest_trade_date ?? null,
    totalRecords: totalTrading + totalProduction,
    lastError: data.sync_task?.last_error ?? null,
    crops: data.crops ?? [],
    unmatched: data.unmatched_records ?? 0,
    scheduler: data.scheduler ?? null,
    isTaskRunning: taskRunning,
  };
}

/* ------------------------------------------------------------------ */
/*  Main Data Management Page                                         */
/* ------------------------------------------------------------------ */
export default function DataManagementPage() {
  const { retrainStatus, requestRetrain } = usePredictionStore();

  const [activeTab, setActiveTab] = useState('sync');
  const [crops, setCrops] = useState([]);
  const [cropsLoading, setCropsLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [syncInfo, setSyncInfo] = useState({
    status: 'idle',
    lastSync: null,
    dataUpTo: null,
    totalRecords: null,
    lastError: null,
  });
  const [systemAlerts, setSystemAlerts] = useState([]);
  const pollRef = useRef(null);

  // Load real sync status from backend
  const loadSyncStatus = useCallback(async () => {
    try {
      const data = await fetchSyncStatus();
      const parsed = parseSyncStatusResponse(data);
      setSyncInfo(parsed);
      setCrops(parsed.crops);
      return parsed;
    } catch (err) {
      setSyncInfo((prev) => ({ ...prev, status: 'failed', lastError: err.message }));
      return null;
    }
  }, []);

  // Initial load
  useEffect(() => {
    let cancelled = false;
    setCropsLoading(true);
    loadSyncStatus().finally(() => {
      if (!cancelled) setCropsLoading(false);
    });
    return () => { cancelled = true; };
  }, [loadSyncStatus]);

  // Polling: poll /sync/status every 3s while sync is running
  const startPolling = useCallback(() => {
    if (pollRef.current) return;
    pollRef.current = setInterval(async () => {
      const parsed = await loadSyncStatus();
      if (parsed && !parsed.isTaskRunning) {
        // Sync finished — stop polling
        clearInterval(pollRef.current);
        pollRef.current = null;
        setSyncing(false);

        if (parsed.status === 'success') {
          setSystemAlerts((prev) => [
            {
              id: `sync-${Date.now()}`,
              type: 'info',
              message: `資料同步完成，抓取 ${formatNumber(parsed.totalRecords)} 筆記錄`,
              date: new Date().toISOString(),
            },
            ...prev,
          ]);
        } else if (parsed.status === 'failed') {
          setSystemAlerts((prev) => [
            {
              id: `err-${Date.now()}`,
              type: 'error',
              message: `同步失敗: ${parsed.lastError ?? '未知錯誤'}`,
              date: new Date().toISOString(),
            },
            ...prev,
          ]);
        }
      }
    }, 3000);
  }, [loadSyncStatus]);

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, []);

  // Manual sync handler — calls real triggerSync API
  const handleSync = useCallback(async () => {
    setSyncing(true);
    setSyncInfo((prev) => ({ ...prev, status: 'syncing', lastError: null }));

    try {
      await triggerSync({ dataType: 'both', daysBack: 7 });
      // Start polling for completion
      startPolling();
    } catch (err) {
      setSyncing(false);
      setSyncInfo((prev) => ({ ...prev, status: 'failed', lastError: err.message }));
      setSystemAlerts((prev) => [
        {
          id: `err-${Date.now()}`,
          type: 'error',
          message: `同步觸發失敗: ${err.message}`,
          date: new Date().toISOString(),
        },
        ...prev,
      ]);
    }
  }, [startPolling]);

  // Retrain handler
  const handleRetrain = useCallback(async () => {
    try {
      await requestRetrain({ forceRetrain: true });
      setSystemAlerts((prev) => [
        {
          id: `retrain-${Date.now()}`,
          type: 'info',
          message: '模型重新訓練已完成',
          date: new Date().toISOString(),
        },
        ...prev,
      ]);
    } catch (err) {
      setSystemAlerts((prev) => [
        {
          id: `err-${Date.now()}`,
          type: 'error',
          message: `重新訓練失敗: ${err.message}`,
          date: new Date().toISOString(),
        },
        ...prev,
      ]);
    }
  }, [requestRetrain]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">資料管理</h1>
        <p className="mt-1 text-sm text-gray-500">
          管理資料同步、匯入與模型訓練
        </p>
      </div>

      {/* Tab bar */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex gap-6">
          {TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`whitespace-nowrap border-b-2 px-1 pb-3 text-sm font-medium transition-colors ${
                activeTab === tab.key
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab content */}
      {activeTab === 'sync' && (
        <>
          {/* Sync status */}
          <SyncStatusCard syncInfo={syncInfo} onSync={handleSync} syncing={syncing} />

          {/* Data coverage table */}
          <div className="rounded-xl border border-gray-100 bg-white shadow-sm">
            <div className="border-b border-gray-100 px-5 py-4">
              <h3 className="text-base font-semibold text-gray-800">資料涵蓋範圍</h3>
              <p className="mt-0.5 text-xs text-gray-400">
                各作物交易與產量記錄數量
              </p>
            </div>
            <DataCoverageTable crops={crops} loading={cropsLoading} />
          </div>

          {/* Retrain section */}
          <RetrainSection onRetrain={handleRetrain} retrainStatus={retrainStatus} />

          {/* System alerts */}
          <div className="rounded-xl border border-gray-100 bg-white shadow-sm">
            <div className="border-b border-gray-100 px-5 py-4">
              <h3 className="text-base font-semibold text-gray-800">系統通知</h3>
              <p className="mt-0.5 text-xs text-gray-400">
                同步與訓練操作紀錄
              </p>
            </div>
            <AlertHistory alerts={systemAlerts} />
          </div>
        </>
      )}

      {activeTab === 'import' && (
        <div className="rounded-xl border border-gray-100 bg-white p-6 shadow-sm">
          <div className="mb-6">
            <h3 className="text-base font-semibold text-gray-800">資料匯入</h3>
            <p className="mt-0.5 text-xs text-gray-400">
              上傳 CSV 或 Excel 檔案匯入交易、產量或氣象資料
            </p>
          </div>
          <UploadWizard />
        </div>
      )}
    </div>
  );
}
