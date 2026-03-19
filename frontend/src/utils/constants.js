/**
 * Supported metric types for the dashboard visualizations.
 */
export const METRICS = Object.freeze({
  AVG_PRICE: 'avg_price',
  MAX_PRICE: 'max_price',
  MIN_PRICE: 'min_price',
  TRADING_VOLUME: 'trading_volume',
  TRANSACTION_COUNT: 'transaction_count',
  PRODUCTION_AREA: 'production_area',
  PRODUCTION_YIELD: 'production_yield',
  PRODUCTION_AMOUNT: 'production_amount',
});

/**
 * Supported temporal granularities for data aggregation.
 */
export const GRANULARITIES = Object.freeze({
  DAILY: 'daily',
  WEEKLY: 'weekly',
  MONTHLY: 'monthly',
  YEARLY: 'yearly',
});

/**
 * Human-readable labels for metrics (Chinese).
 */
export const METRIC_LABELS = Object.freeze({
  [METRICS.AVG_PRICE]: '平均價格',
  [METRICS.MAX_PRICE]: '最高價格',
  [METRICS.MIN_PRICE]: '最低價格',
  [METRICS.TRADING_VOLUME]: '交易量',
  [METRICS.TRANSACTION_COUNT]: '交易筆數',
  [METRICS.PRODUCTION_AREA]: '種植面積',
  [METRICS.PRODUCTION_YIELD]: '單位產量',
  [METRICS.PRODUCTION_AMOUNT]: '總產量',
});

/**
 * Human-readable labels for granularities (Chinese).
 */
export const GRANULARITY_LABELS = Object.freeze({
  [GRANULARITIES.DAILY]: '日',
  [GRANULARITIES.WEEKLY]: '週',
  [GRANULARITIES.MONTHLY]: '月',
  [GRANULARITIES.YEARLY]: '年',
});

/**
 * Default date range for initial data loading.
 * Covers the most recent full year.
 */
export const DEFAULT_DATE_RANGE = Object.freeze({
  startDate: '2025-01-01',
  endDate: '2025-12-31',
});

/**
 * Traffic light signal levels.
 */
export const TRAFFIC_SIGNALS = Object.freeze({
  GREEN: 'GREEN',
  YELLOW: 'YELLOW',
  RED: 'RED',
  UNKNOWN: 'UNKNOWN',
});

/**
 * Human-readable labels for traffic signals (Chinese).
 */
export const TRAFFIC_SIGNAL_LABELS = Object.freeze({
  [TRAFFIC_SIGNALS.GREEN]: '正常',
  [TRAFFIC_SIGNALS.YELLOW]: '注意',
  [TRAFFIC_SIGNALS.RED]: '警戒',
  [TRAFFIC_SIGNALS.UNKNOWN]: '資料不足',
});

/**
 * Thresholds for determining traffic signal levels.
 * { green: max for GREEN, yellow: max for YELLOW, above yellow = RED }
 */
export const TRAFFIC_THRESHOLDS = Object.freeze({
  supply_index: { green: 1.1, yellow: 1.2 },
  price_drop_pct: { green: 10, yellow: 20 },
  area_growth_pct: { green: 10, yellow: 20 },
});
