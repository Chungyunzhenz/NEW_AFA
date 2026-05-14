const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const DATA_DIR = path.join(ROOT, "AFA-other", "model_ready", "forecast");
const OUT_DIR = path.join(ROOT, "AFA-other", "model_ready", "forecast_results");

const CROPS = ["cabbage", "bok_choy", "cauliflower", "green_onion", "lettuce"];
const FEATURE_COLS = [
  "ln_volume_total",
  "transaction_count",
  "item_count",
  "market_count",
  "is_observed",
  "year",
  "month",
  "day_of_week",
  "day_of_year",
  "month_sin",
  "month_cos",
  "price_lag_1",
  "price_lag_3",
  "price_lag_7",
  "price_lag_14",
  "price_roll_mean_7",
  "price_roll_std_7",
  "price_roll_mean_14",
  "volume_lag_1",
  "volume_roll_mean_7",
];

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

function parseCsv(filePath) {
  const content = fs.readFileSync(filePath, "utf8").replace(/^\uFEFF/, "");
  const lines = content.trim().split(/\r?\n/);
  const headers = splitCsvLine(lines[0]);
  return lines.slice(1).map((line) => {
    const cells = splitCsvLine(line);
    const row = {};
    headers.forEach((h, i) => {
      const value = cells[i] ?? "";
      const n = Number(value);
      row[h] = value !== "" && Number.isFinite(n) ? n : value;
    });
    return row;
  });
}

function csvEscape(value) {
  if (value === null || value === undefined) return "";
  const s = String(value);
  if (/[",\r\n]/.test(s)) return `"${s.replace(/"/g, '""')}"`;
  return s;
}

function writeCsv(filePath, columns, rows) {
  const lines = [columns.join(",")];
  for (const row of rows) lines.push(columns.map((c) => csvEscape(row[c])).join(","));
  fs.writeFileSync(filePath, `\uFEFF${lines.join("\n")}\n`, "utf8");
}

function metrics(yTrue, yPred) {
  const pairs = yTrue.map((y, i) => [Number(y), Number(yPred[i])])
    .filter(([y, p]) => Number.isFinite(y) && Number.isFinite(p));
  const n = pairs.length;
  const mae = pairs.reduce((s, [y, p]) => s + Math.abs(y - p), 0) / n;
  const rmse = Math.sqrt(pairs.reduce((s, [y, p]) => s + (y - p) ** 2, 0) / n);
  const mape = pairs.reduce((s, [y, p]) => s + Math.abs((y - p) / y), 0) / n * 100;
  const meanY = pairs.reduce((s, [y]) => s + y, 0) / n;
  const ssRes = pairs.reduce((s, [y, p]) => s + (y - p) ** 2, 0);
  const ssTot = pairs.reduce((s, [y]) => s + (y - meanY) ** 2, 0);
  const r2 = ssTot === 0 ? 0 : 1 - ssRes / ssTot;
  return { n, mae, rmse, mape, r2 };
}

function standardize(trainRows, testRows, featureCols) {
  const stats = {};
  for (const col of featureCols) {
    const values = trainRows.map((r) => Number(r[col])).filter(Number.isFinite);
    const mean = values.reduce((s, v) => s + v, 0) / values.length;
    const variance = values.reduce((s, v) => s + (v - mean) ** 2, 0) / Math.max(1, values.length - 1);
    const sd = Math.sqrt(variance) || 1;
    stats[col] = { mean, sd };
  }
  const transform = (row) => [1, ...featureCols.map((col) => {
    const v = Number(row[col]);
    if (!Number.isFinite(v)) return 0;
    return (v - stats[col].mean) / stats[col].sd;
  })];
  return {
    xTrain: trainRows.map(transform),
    xTest: testRows.map(transform),
  };
}

function ridgeFit(x, y, lambda = 1) {
  const p = x[0].length;
  const a = Array.from({ length: p }, () => Array(p).fill(0));
  const b = Array(p).fill(0);

  for (let i = 0; i < x.length; i += 1) {
    for (let j = 0; j < p; j += 1) {
      b[j] += x[i][j] * y[i];
      for (let k = 0; k < p; k += 1) a[j][k] += x[i][j] * x[i][k];
    }
  }
  for (let j = 1; j < p; j += 1) a[j][j] += lambda;
  return solveLinearSystem(a, b);
}

function solveLinearSystem(a, b) {
  const n = b.length;
  const m = a.map((row, i) => [...row, b[i]]);

  for (let col = 0; col < n; col += 1) {
    let pivot = col;
    for (let r = col + 1; r < n; r += 1) {
      if (Math.abs(m[r][col]) > Math.abs(m[pivot][col])) pivot = r;
    }
    if (Math.abs(m[pivot][col]) < 1e-12) continue;
    [m[col], m[pivot]] = [m[pivot], m[col]];

    const div = m[col][col];
    for (let c = col; c <= n; c += 1) m[col][c] /= div;

    for (let r = 0; r < n; r += 1) {
      if (r === col) continue;
      const factor = m[r][col];
      for (let c = col; c <= n; c += 1) m[r][c] -= factor * m[col][c];
    }
  }

  return m.map((row) => row[n] || 0);
}

function dot(a, b) {
  let s = 0;
  for (let i = 0; i < a.length; i += 1) s += a[i] * b[i];
  return s;
}

function fitPredictRidge(trainRows, testRows) {
  const cleanTrain = trainRows.filter((r) => FEATURE_COLS.every((c) => Number.isFinite(Number(r[c]))) && Number.isFinite(Number(r.y)));
  const { xTrain, xTest } = standardize(cleanTrain, testRows, FEATURE_COLS);
  const yTrain = cleanTrain.map((r) => Number(r.y));
  const beta = ridgeFit(xTrain, yTrain, 10);
  return xTest.map((x) => Math.max(0, dot(x, beta)));
}

function forecastModels(trainRows, testRows) {
  const trainY = trainRows.map((r) => Number(r.y));
  const trainMean14 = trainY.slice(-14).reduce((s, v) => s + v, 0) / 14;
  const fallback = trainY[trainY.length - 1] ?? trainMean14;

  const preds = {
    naive_lag1: testRows.map((r) => Number(r.price_lag_1) || fallback),
    seasonal_naive_lag7: testRows.map((r) => Number(r.price_lag_7) || fallback),
    moving_average_7: testRows.map((r) => Number(r.price_roll_mean_7) || fallback),
    moving_average_14: testRows.map((r) => Number(r.price_roll_mean_14) || fallback),
    ridge_ts_regression: fitPredictRidge(trainRows, testRows),
  };
  return preds;
}

function round(value, digits = 4) {
  return Number.isFinite(value) ? Number(value.toFixed(digits)) : "";
}

function main() {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  const metricRows = [];
  const bestRows = [];

  for (const crop of CROPS) {
    console.log(`Training forecast baselines for ${crop}...`);
    const trainRows = parseCsv(path.join(DATA_DIR, `${crop}_daily_train.csv`));
    const testRows = parseCsv(path.join(DATA_DIR, `${crop}_daily_test.csv`));
    const preds = forecastModels(trainRows, testRows);
    const yTrue = testRows.map((r) => Number(r.y));

    const predictionRows = testRows.map((r, i) => {
      const out = { crop, ds: r.ds, actual: r.y };
      for (const model of Object.keys(preds)) out[model] = round(preds[model][i], 6);
      return out;
    });
    writeCsv(
      path.join(OUT_DIR, `${crop}_predictions.csv`),
      ["crop", "ds", "actual", ...Object.keys(preds)],
      predictionRows,
    );

    let best = null;
    for (const [model, pred] of Object.entries(preds)) {
      const m = metrics(yTrue, pred);
      const row = {
        crop,
        model,
        n_test: m.n,
        MAE: round(m.mae),
        RMSE: round(m.rmse),
        MAPE_percent: round(m.mape),
        R2: round(m.r2),
      };
      metricRows.push(row);
      if (!best || m.rmse < best.RMSE_raw) best = { ...row, RMSE_raw: m.rmse };
    }
    bestRows.push(best);
    console.log(`  best=${best.model}, RMSE=${best.RMSE}`);
  }

  writeCsv(path.join(OUT_DIR, "metrics.csv"), ["crop", "model", "n_test", "MAE", "RMSE", "MAPE_percent", "R2"], metricRows);
  writeReport(metricRows, bestRows);
  console.log(`Done. Output: ${OUT_DIR}`);
}

function writeReport(metricRows, bestRows) {
  const lines = [
    "# Forecast model report",
    "",
    "This report uses the daily forecast-ready data in `AFA-other/model_ready/forecast`.",
    "",
    "Models evaluated:",
    "",
    "- `naive_lag1`: predicts tomorrow from the previous available price.",
    "- `seasonal_naive_lag7`: predicts from the same weekday one week earlier.",
    "- `moving_average_7`: predicts using the previous 7-day average.",
    "- `moving_average_14`: predicts using the previous 14-day average.",
    "- `ridge_ts_regression`: Ridge regression using lag, rolling, volume, and calendar features.",
    "",
    "Evaluation is chronological on each crop's held-out test period. The feature columns use past observed values already prepared in the forecast data, so this is a one-step-ahead / walk-forward style evaluation.",
    "",
    "## Best model by crop",
    "",
    "| crop | best model | MAE | RMSE | MAPE (%) | R2 |",
    "| --- | --- | ---: | ---: | ---: | ---: |",
  ];

  for (const row of bestRows) {
    lines.push(`| ${row.crop} | ${row.model} | ${row.MAE} | ${row.RMSE} | ${row.MAPE_percent} | ${row.R2} |`);
  }

  lines.push("", "## Full metrics", "");
  for (const crop of CROPS) {
    lines.push(`### ${crop}`, "");
    lines.push("| model | n_test | MAE | RMSE | MAPE (%) | R2 |");
    lines.push("| --- | ---: | ---: | ---: | ---: | ---: |");
    for (const row of metricRows.filter((r) => r.crop === crop)) {
      lines.push(`| ${row.model} | ${row.n_test} | ${row.MAE} | ${row.RMSE} | ${row.MAPE_percent} | ${row.R2} |`);
    }
    lines.push("");
  }

  lines.push(
    "## Interpretation",
    "",
    "- Lower MAE/RMSE/MAPE is better.",
    "- `R2` can be negative when a model is worse than predicting the test-period mean.",
    "- If simple lag or moving-average models beat Ridge, the series is mostly short-memory and the current engineered features are not adding enough signal.",
    "- This is the first baseline report. Prophet/SARIMA/XGBoost can be added after Python dependencies are available.",
    "",
    "## Output files",
    "",
    "- `metrics.csv`: all model metrics.",
    "- `<crop>_predictions.csv`: actual and predicted values for each crop.",
  );

  fs.writeFileSync(path.join(OUT_DIR, "REPORT.md"), `${lines.join("\n")}\n`, "utf8");
}

main();
