const fs = require("fs");
const path = require("path");
const readline = require("readline");

const ROOT = path.resolve(__dirname, "..");
const SRC = path.join(ROOT, "AFA-other");
const OUT = path.join(SRC, "model_ready");
const REG_OUT = path.join(OUT, "regression");
const FORECAST_OUT = path.join(OUT, "forecast");

const CROPS = [
  { key: "cabbage", label: "cabbage", file: "cabbage_交易資料_with_targets.csv" },
  { key: "bok_choy", label: "bok_choy", file: "bok_choy_交易資料_with_targets.csv" },
  { key: "cauliflower", label: "cauliflower", file: "cauliflower_交易資料_with_targets.csv" },
  { key: "green_onion", label: "green_onion", file: "green_onion_交易資料_with_targets.csv" },
  { key: "lettuce", label: "lettuce", file: "lettuce_交易資料_with_targets.csv" },
];

const NUMERIC_FIELDS = ["上價", "中價", "下價", "平均價", "交易量(公斤)", "target_1d", "target_5d", "target_20d"];
const LAGS = [1, 3, 5, 7];

function ensureDirs() {
  for (const dir of [OUT, REG_OUT, FORECAST_OUT]) {
    fs.mkdirSync(dir, { recursive: true });
  }
}

function parseNumber(value) {
  if (value === undefined || value === null || value === "") return null;
  const n = Number(String(value).trim());
  return Number.isFinite(n) ? n : null;
}

function parseDateKey(value) {
  if (!value) return null;
  const s = String(value).trim().replace(/\//g, "-");
  const d = new Date(`${s}T00:00:00Z`);
  if (Number.isNaN(d.getTime())) return null;
  return d.toISOString().slice(0, 10);
}

function dateParts(dateKey) {
  const d = new Date(`${dateKey}T00:00:00Z`);
  const start = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
  return {
    year: d.getUTCFullYear(),
    month: d.getUTCMonth() + 1,
    day_of_week: d.getUTCDay(),
    day_of_year: Math.floor((d - start) / 86400000) + 1,
  };
}

function csvEscape(value) {
  if (value === null || value === undefined) return "";
  const s = String(value);
  if (/[",\r\n]/.test(s)) return `"${s.replace(/"/g, '""')}"`;
  return s;
}

function splitCsvLine(line) {
  const out = [];
  let cur = "";
  let quoted = false;
  for (let i = 0; i < line.length; i += 1) {
    const ch = line[i];
    if (ch === '"') {
      if (quoted && line[i + 1] === '"') {
        cur += '"';
        i += 1;
      } else {
        quoted = !quoted;
      }
    } else if (ch === "," && !quoted) {
      out.push(cur);
      cur = "";
    } else {
      cur += ch;
    }
  }
  out.push(cur);
  return out;
}

async function readRows(filePath) {
  const rows = [];
  const rejected = {
    bad_date: 0,
    missing_target_5d: 0,
    non_positive_target_5d: 0,
    non_positive_avg_price: 0,
    non_positive_volume: 0,
  };
  let headers = null;

  const rl = readline.createInterface({
    input: fs.createReadStream(filePath, { encoding: "utf8" }),
    crlfDelay: Infinity,
  });

  for await (const rawLine of rl) {
    const line = rawLine.replace(/^\uFEFF/, "");
    if (!line.trim()) continue;
    const cells = splitCsvLine(line);
    if (!headers) {
      headers = cells;
      continue;
    }

    const row = {};
    headers.forEach((h, i) => {
      row[h] = cells[i] ?? "";
    });

    const date = parseDateKey(row["交易日期"]);
    if (!date) {
      rejected.bad_date += 1;
      continue;
    }

    for (const field of NUMERIC_FIELDS) row[field] = parseNumber(row[field]);

    if (row["target_5d"] === null) {
      rejected.missing_target_5d += 1;
      continue;
    }
    if (row["target_5d"] <= 0) {
      rejected.non_positive_target_5d += 1;
      continue;
    }
    if (row["平均價"] === null || row["平均價"] <= 0) {
      rejected.non_positive_avg_price += 1;
      continue;
    }
    if (row["交易量(公斤)"] === null || row["交易量(公斤)"] <= 0) {
      rejected.non_positive_volume += 1;
      continue;
    }

    rows.push({
      date,
      item: row["品名"] || "unknown",
      market_name: row["市場名稱"] || "unknown",
      market_code: row["市場代碼"] || "unknown",
      high_price: row["上價"],
      mid_price: row["中價"],
      low_price: row["下價"],
      avg_price: row["平均價"],
      volume_kg: row["交易量(公斤)"],
      target_5d: row["target_5d"],
    });
  }

  rows.sort((a, b) => {
    if (a.date !== b.date) return a.date < b.date ? -1 : 1;
    if (a.item !== b.item) return a.item < b.item ? -1 : 1;
    return String(a.market_code).localeCompare(String(b.market_code));
  });

  return { rows, rejected };
}

function uniqueSorted(values) {
  return [...new Set(values)].sort((a, b) => String(a).localeCompare(String(b), "zh-Hant"));
}

function splitCutDate(rows, ratio = 0.7) {
  const dates = uniqueSorted(rows.map((r) => r.date));
  const idx = Math.max(1, Math.min(dates.length - 1, Math.floor(dates.length * ratio)));
  return dates[idx];
}

function addRegressionHistory(rows) {
  const states = new Map();
  const enriched = [];

  for (const row of rows) {
    const key = `${row.item}||${row.market_code}`;
    const history = states.get(key) || [];
    const parts = dateParts(row.date);
    const prevPrices = history.map((h) => h.avg_price);
    const prevVolumes = history.map((h) => h.volume_kg);

    const out = {
      ...row,
      ...parts,
      month_sin: Math.sin((2 * Math.PI * parts.month) / 12),
      month_cos: Math.cos((2 * Math.PI * parts.month) / 12),
      ln_volume: Math.log1p(row.volume_kg),
    };

    for (const lag of LAGS) {
      const idx = history.length - lag;
      out[`avg_price_lag_${lag}`] = idx >= 0 ? history[idx].avg_price : null;
    }

    out.volume_lag_1 = prevVolumes.length >= 1 ? prevVolumes[prevVolumes.length - 1] : null;
    out.price_roll_mean_3 = rollingMean(prevPrices, 3);
    out.price_roll_mean_7 = rollingMean(prevPrices, 7);
    out.price_roll_std_7 = rollingStd(prevPrices, 7);

    enriched.push(out);
    history.push(row);
    states.set(key, history);
  }

  return enriched.filter((r) =>
    LAGS.every((lag) => r[`avg_price_lag_${lag}`] !== null) &&
    r.volume_lag_1 !== null &&
    r.price_roll_std_7 !== null
  );
}

function rollingMean(values, window) {
  if (values.length === 0) return null;
  const slice = values.slice(-window);
  return slice.reduce((sum, v) => sum + v, 0) / slice.length;
}

function rollingStd(values, window) {
  if (values.length < 2) return null;
  const slice = values.slice(-window);
  const mean = slice.reduce((sum, v) => sum + v, 0) / slice.length;
  const variance = slice.reduce((sum, v) => sum + (v - mean) ** 2, 0) / (slice.length - 1);
  return Math.sqrt(variance);
}

function buildRegressionOutputs(rows, cutDate, cropKey) {
  const trainBase = rows.filter((r) => r.date < cutDate);
  const itemRefAndOthers = uniqueSorted(trainBase.map((r) => r.item));
  const marketRefAndOthers = uniqueSorted(trainBase.map((r) => r.market_code));
  const [itemRef, ...itemOthers] = itemRefAndOthers;
  const [marketRef, ...marketOthers] = marketRefAndOthers;

  const itemCols = itemOthers.map((_, i) => `item_${i + 1}`);
  const marketCols = marketOthers.map((_, i) => `market_${i + 1}`);
  const itemMap = new Map(itemOthers.map((v, i) => [v, itemCols[i]]));
  const marketMap = new Map(marketOthers.map((v, i) => [v, marketCols[i]]));

  const featureRows = addRegressionHistory(rows);
  const numericCols = [
    "high_price", "mid_price", "low_price", "avg_price", "volume_kg", "ln_volume",
    "year", "month", "day_of_week", "day_of_year", "month_sin", "month_cos",
    "avg_price_lag_1", "avg_price_lag_3", "avg_price_lag_5", "avg_price_lag_7",
    "volume_lag_1", "price_roll_mean_3", "price_roll_mean_7", "price_roll_std_7",
  ];
  const columns = ["date", ...numericCols, ...itemCols, ...marketCols, "target_5d"];

  const encoded = featureRows.map((r) => {
    const out = {};
    out.date = r.date;
    for (const col of numericCols) out[col] = r[col];
    for (const col of itemCols) out[col] = 0;
    for (const col of marketCols) out[col] = 0;
    if (itemMap.has(r.item)) out[itemMap.get(r.item)] = 1;
    if (marketMap.has(r.market_code)) out[marketMap.get(r.market_code)] = 1;
    out.target_5d = r.target_5d;
    return out;
  });

  const train = encoded.filter((r) => r.date < cutDate);
  const test = encoded.filter((r) => r.date >= cutDate);

  writeCsv(path.join(REG_OUT, `${cropKey}_train.csv`), columns, train);
  writeCsv(path.join(REG_OUT, `${cropKey}_test.csv`), columns, test);

  const unseenTestItems = uniqueSorted(featureRows.filter((r) => r.date >= cutDate && !itemRefAndOthers.includes(r.item)).map((r) => r.item));
  const unseenTestMarkets = uniqueSorted(featureRows.filter((r) => r.date >= cutDate && !marketRefAndOthers.includes(r.market_code)).map((r) => r.market_code));

  writeCodebook(path.join(REG_OUT, `${cropKey}_codebook.txt`), [
    `Regression data for ${cropKey}`,
    "",
    `Target: target_5d`,
    `Split: train date < ${cutDate}; test date >= ${cutDate}`,
    `Rows: train=${train.length}, test=${test.length}`,
    "",
    "Numeric features:",
    ...numericCols.map((c) => `  - ${c}`),
    "",
    `Item reference: ${itemRef}`,
    ...itemOthers.map((v, i) => `  ${itemCols[i]} = 1 if item == ${v}`),
    "",
    `Market reference: ${marketRef}`,
    ...marketOthers.map((v, i) => `  ${marketCols[i]} = 1 if market_code == ${v}`),
    "",
    `Unseen test items encoded as all-zero item dummies: ${unseenTestItems.length ? unseenTestItems.join(", ") : "none"}`,
    `Unseen test markets encoded as all-zero market dummies: ${unseenTestMarkets.length ? unseenTestMarkets.join(", ") : "none"}`,
  ]);

  return { train: train.length, test: test.length, columns: columns.length };
}

function buildForecastOutputs(rows, cutDate, cropKey) {
  const byDate = new Map();
  for (const r of rows) {
    const agg = byDate.get(r.date) || {
      date: r.date,
      weighted_price_sum: 0,
      weighted_high_sum: 0,
      weighted_mid_sum: 0,
      weighted_low_sum: 0,
      volume_total: 0,
      price_sum: 0,
      transaction_count: 0,
      items: new Set(),
      markets: new Set(),
    };
    agg.weighted_price_sum += r.avg_price * r.volume_kg;
    agg.weighted_high_sum += (r.high_price ?? r.avg_price) * r.volume_kg;
    agg.weighted_mid_sum += (r.mid_price ?? r.avg_price) * r.volume_kg;
    agg.weighted_low_sum += (r.low_price ?? r.avg_price) * r.volume_kg;
    agg.volume_total += r.volume_kg;
    agg.price_sum += r.avg_price;
    agg.transaction_count += 1;
    agg.items.add(r.item);
    agg.markets.add(r.market_code);
    byDate.set(r.date, agg);
  }

  const dates = uniqueSorted(rows.map((r) => r.date));
  const start = new Date(`${dates[0]}T00:00:00Z`);
  const end = new Date(`${dates[dates.length - 1]}T00:00:00Z`);
  const daily = [];
  let lastPrice = null;

  for (let d = new Date(start); d <= end; d = new Date(d.getTime() + 86400000)) {
    const date = d.toISOString().slice(0, 10);
    const agg = byDate.get(date);
    if (agg) {
      const price = agg.weighted_price_sum / agg.volume_total;
      lastPrice = price;
      daily.push({
        ds: date,
        y: price,
        price_avg_weighted: price,
        price_mean: agg.price_sum / agg.transaction_count,
        high_price_weighted: agg.weighted_high_sum / agg.volume_total,
        mid_price_weighted: agg.weighted_mid_sum / agg.volume_total,
        low_price_weighted: agg.weighted_low_sum / agg.volume_total,
        volume_total: agg.volume_total,
        ln_volume_total: Math.log1p(agg.volume_total),
        transaction_count: agg.transaction_count,
        item_count: agg.items.size,
        market_count: agg.markets.size,
        is_observed: 1,
      });
    } else {
      daily.push({
        ds: date,
        y: lastPrice,
        price_avg_weighted: lastPrice,
        price_mean: lastPrice,
        high_price_weighted: lastPrice,
        mid_price_weighted: lastPrice,
        low_price_weighted: lastPrice,
        volume_total: 0,
        ln_volume_total: 0,
        transaction_count: 0,
        item_count: 0,
        market_count: 0,
        is_observed: 0,
      });
    }
  }

  const firstObserved = daily.find((r) => r.y !== null);
  for (const r of daily) {
    if (r.y === null && firstObserved) {
      r.y = firstObserved.y;
      r.price_avg_weighted = firstObserved.y;
      r.price_mean = firstObserved.y;
      r.high_price_weighted = firstObserved.y;
      r.mid_price_weighted = firstObserved.y;
      r.low_price_weighted = firstObserved.y;
    }
  }

  addForecastHistory(daily);

  const columns = [
    "ds", "y", "price_avg_weighted", "price_mean", "high_price_weighted",
    "mid_price_weighted", "low_price_weighted", "volume_total", "ln_volume_total",
    "transaction_count", "item_count", "market_count", "is_observed",
    "year", "month", "day_of_week", "day_of_year", "month_sin", "month_cos",
    "price_lag_1", "price_lag_3", "price_lag_7", "price_lag_14",
    "price_roll_mean_7", "price_roll_std_7", "price_roll_mean_14",
    "volume_lag_1", "volume_roll_mean_7",
  ];

  const ready = daily.filter((r) => r.price_lag_14 !== null && r.price_roll_std_7 !== null);
  const train = ready.filter((r) => r.ds < cutDate);
  const test = ready.filter((r) => r.ds >= cutDate);

  writeCsv(path.join(FORECAST_OUT, `${cropKey}_daily.csv`), columns, ready);
  writeCsv(path.join(FORECAST_OUT, `${cropKey}_daily_train.csv`), columns, train);
  writeCsv(path.join(FORECAST_OUT, `${cropKey}_daily_test.csv`), columns, test);

  return { rows: ready.length, train: train.length, test: test.length, columns: columns.length };
}

function addForecastHistory(rows) {
  const prices = [];
  const volumes = [];
  for (const r of rows) {
    const parts = dateParts(r.ds);
    Object.assign(r, parts);
    r.month_sin = Math.sin((2 * Math.PI * parts.month) / 12);
    r.month_cos = Math.cos((2 * Math.PI * parts.month) / 12);
    for (const lag of [1, 3, 7, 14]) {
      const idx = prices.length - lag;
      r[`price_lag_${lag}`] = idx >= 0 ? prices[idx] : null;
    }
    r.price_roll_mean_7 = rollingMean(prices, 7);
    r.price_roll_std_7 = rollingStd(prices, 7);
    r.price_roll_mean_14 = rollingMean(prices, 14);
    r.volume_lag_1 = volumes.length >= 1 ? volumes[volumes.length - 1] : null;
    r.volume_roll_mean_7 = rollingMean(volumes, 7);
    prices.push(r.y);
    volumes.push(r.volume_total);
  }
}

function writeCsv(filePath, columns, rows) {
  const lines = [columns.join(",")];
  for (const row of rows) {
    lines.push(columns.map((c) => csvEscape(row[c])).join(","));
  }
  fs.writeFileSync(filePath, `\uFEFF${lines.join("\n")}\n`, "utf8");
}

function writeCodebook(filePath, lines) {
  fs.writeFileSync(filePath, `${lines.join("\n")}\n`, "utf8");
}

async function main() {
  ensureDirs();
  const summary = [];

  for (const crop of CROPS) {
    const filePath = path.join(SRC, crop.file);
    console.log(`Processing ${crop.key}...`);
    const { rows, rejected } = await readRows(filePath);
    const cutDate = splitCutDate(rows);
    const regression = buildRegressionOutputs(rows, cutDate, crop.key);
    const forecast = buildForecastOutputs(rows, cutDate, crop.key);
    summary.push({ crop: crop.key, input: rows.length, cutDate, rejected, regression, forecast });
    console.log(`  clean=${rows.length}, cut=${cutDate}, regression train/test=${regression.train}/${regression.test}, forecast train/test=${forecast.train}/${forecast.test}`);
  }

  writeReadme(summary);
  console.log(`Done. Output: ${OUT}`);
}

function writeReadme(summary) {
  const lines = [
    "# Model-ready data",
    "",
    "Generated by `node scripts/prepare_model_data.js`.",
    "",
    "## Folders",
    "",
    "- `regression/`: transaction-level supervised learning data. Use this for OLS, Ridge, Lasso, Random Forest, XGBoost, LightGBM.",
    "- `forecast/`: daily national time-series data. Use this for Prophet, SARIMA, and time-series ML baselines.",
    "",
    "## Regression target",
    "",
    "- `target_5d`: average price 5 days ahead.",
    "- Split is chronological: train dates are before `cutDate`; test dates are on/after `cutDate`.",
    "- Category encoders are fit from train rows only. Unseen test categories become all-zero dummy columns.",
    "- Lag and rolling features use only previous observations within the same item and market.",
    "",
    "## Forecast target",
    "",
    "- `ds`: date.",
    "- `y`: daily national weighted average price.",
    "- `price_avg_weighted = sum(avg_price * volume_kg) / sum(volume_kg)`.",
    "- Missing calendar dates are kept so Prophet/SARIMA receive a fixed daily frequency; price is forward/back filled and `is_observed=0`.",
    "",
    "## Summary",
    "",
    "| crop | clean rows | cutDate | regression train | regression test | forecast train | forecast test | removed rows |",
    "| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |",
  ];

  for (const s of summary) {
    const removed = Object.values(s.rejected).reduce((sum, n) => sum + n, 0);
    lines.push(`| ${s.crop} | ${s.input} | ${s.cutDate} | ${s.regression.train} | ${s.regression.test} | ${s.forecast.train} | ${s.forecast.test} | ${removed} |`);
  }

  lines.push("", "## Removed row reasons", "");
  for (const s of summary) {
    lines.push(`### ${s.crop}`);
    for (const [reason, count] of Object.entries(s.rejected)) {
      lines.push(`- ${reason}: ${count}`);
    }
    lines.push("");
  }

  fs.writeFileSync(path.join(OUT, "README.md"), `${lines.join("\n")}\n`, "utf8");
}

main().catch((err) => {
  console.error(err);
  process.exitCode = 1;
});
