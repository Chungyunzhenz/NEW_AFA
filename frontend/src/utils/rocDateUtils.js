/**
 * Utilities for converting between the Western (Gregorian) calendar and
 * the Republic of China (ROC / Minguo) calendar used in Taiwanese
 * agricultural datasets.
 *
 * ROC Year = Gregorian Year - 1911
 */

const ROC_OFFSET = 1911;

/**
 * Convert a JS Date or ISO string to an ROC date string (YYY/MM/DD).
 * @param {Date|string} date
 * @returns {string} e.g. "113/03/19"
 */
export function toRocDate(date) {
  const d = typeof date === 'string' ? new Date(date) : date;
  const rocYear = d.getFullYear() - ROC_OFFSET;
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${rocYear}/${month}/${day}`;
}

/**
 * Parse an ROC date string (YYY/MM/DD) into a JS Date.
 * @param {string} rocDateStr - e.g. "113/03/19"
 * @returns {Date}
 */
export function fromRocDate(rocDateStr) {
  const [yearStr, monthStr, dayStr] = rocDateStr.split('/');
  const year = parseInt(yearStr, 10) + ROC_OFFSET;
  const month = parseInt(monthStr, 10) - 1;
  const day = parseInt(dayStr, 10);
  return new Date(year, month, day);
}

/**
 * Convert a Gregorian year to an ROC year.
 * @param {number} gregorianYear
 * @returns {number}
 */
export function toRocYear(gregorianYear) {
  return gregorianYear - ROC_OFFSET;
}

/**
 * Convert an ROC year to a Gregorian year.
 * @param {number} rocYear
 * @returns {number}
 */
export function fromRocYear(rocYear) {
  return rocYear + ROC_OFFSET;
}
