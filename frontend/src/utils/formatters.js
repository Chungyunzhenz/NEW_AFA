import { format as dateFnsFormat, parseISO } from 'date-fns';
import { zhTW } from 'date-fns/locale';

/**
 * Format a number with locale-aware thousand separators.
 * @param {number} value
 * @param {number} [decimals=0]
 * @returns {string}
 */
export function formatNumber(value, decimals = 0) {
  if (value == null || Number.isNaN(value)) return '-';
  return value.toLocaleString('zh-TW', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

/**
 * Format a number as TWD currency.
 * @param {number} value
 * @param {number} [decimals=0]
 * @returns {string}
 */
export function formatCurrency(value, decimals = 0) {
  if (value == null || Number.isNaN(value)) return '-';
  return `NT$ ${formatNumber(value, decimals)}`;
}

/**
 * Format a date string or Date object.
 * @param {string|Date} value - ISO date string or Date.
 * @param {string} [pattern='yyyy/MM/dd'] - date-fns format pattern.
 * @returns {string}
 */
export function formatDate(value, pattern = 'yyyy/MM/dd') {
  if (!value) return '-';
  const date = typeof value === 'string' ? parseISO(value) : value;
  if (isNaN(date.getTime())) return value;
  return dateFnsFormat(date, pattern, { locale: zhTW });
}

/**
 * Format a decimal as a percentage string.
 * @param {number} value - e.g. 0.1234
 * @param {number} [decimals=1]
 * @returns {string}
 */
export function formatPercent(value, decimals = 1) {
  if (value == null || Number.isNaN(value)) return '-';
  return `${(value * 100).toFixed(decimals)}%`;
}
