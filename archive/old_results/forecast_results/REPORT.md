# Forecast model report

This report uses the daily forecast-ready data in `AFA-other/model_ready/forecast`.

Models evaluated:

- `naive_lag1`: predicts tomorrow from the previous available price.
- `seasonal_naive_lag7`: predicts from the same weekday one week earlier.
- `moving_average_7`: predicts using the previous 7-day average.
- `moving_average_14`: predicts using the previous 14-day average.
- `ridge_ts_regression`: Ridge regression using lag, rolling, volume, and calendar features.

Evaluation is chronological on each crop's held-out test period. The feature columns use past observed values already prepared in the forecast data, so this is a one-step-ahead / walk-forward style evaluation.

## Best model by crop

| crop | best model | MAE | RMSE | MAPE (%) | R2 |
| --- | --- | ---: | ---: | ---: | ---: |
| cabbage | ridge_ts_regression | 1.6123 | 2.3248 | 9.1519 | 0.9438 |
| bok_choy | ridge_ts_regression | 2.6613 | 4.1474 | 10.4267 | 0.9189 |
| cauliflower | ridge_ts_regression | 4.0128 | 6.6221 | 10.6119 | 0.8026 |
| green_onion | ridge_ts_regression | 6.1748 | 10.7128 | 8.343 | 0.9565 |
| lettuce | ridge_ts_regression | 3.8201 | 5.4444 | 11.2568 | 0.9113 |

## Full metrics

### cabbage

| model | n_test | MAE | RMSE | MAPE (%) | R2 |
| --- | ---: | ---: | ---: | ---: | ---: |
| naive_lag1 | 1548 | 1.6003 | 2.5495 | 8.5061 | 0.9324 |
| seasonal_naive_lag7 | 1548 | 3.242 | 4.6141 | 16.6751 | 0.7787 |
| moving_average_7 | 1548 | 2.1562 | 3.1423 | 11.0904 | 0.8974 |
| moving_average_14 | 1548 | 2.8454 | 3.9746 | 14.6724 | 0.8358 |
| ridge_ts_regression | 1548 | 1.6123 | 2.3248 | 9.1519 | 0.9438 |

### bok_choy

| model | n_test | MAE | RMSE | MAPE (%) | R2 |
| --- | ---: | ---: | ---: | ---: | ---: |
| naive_lag1 | 1543 | 2.7163 | 4.2798 | 10.0861 | 0.9137 |
| seasonal_naive_lag7 | 1543 | 7.7794 | 12.4739 | 28.3282 | 0.2666 |
| moving_average_7 | 1543 | 4.9565 | 7.9063 | 17.9453 | 0.7054 |
| moving_average_14 | 1543 | 6.6039 | 10.1895 | 24.8126 | 0.5106 |
| ridge_ts_regression | 1543 | 2.6613 | 4.1474 | 10.4267 | 0.9189 |

### cauliflower

| model | n_test | MAE | RMSE | MAPE (%) | R2 |
| --- | ---: | ---: | ---: | ---: | ---: |
| naive_lag1 | 1548 | 4.965 | 8.4147 | 13.2625 | 0.6812 |
| seasonal_naive_lag7 | 1548 | 6.6361 | 9.2815 | 19.1331 | 0.6121 |
| moving_average_7 | 1548 | 4.8028 | 7.1213 | 13.7708 | 0.7717 |
| moving_average_14 | 1548 | 5.712 | 8.1351 | 16.6584 | 0.702 |
| ridge_ts_regression | 1548 | 4.0128 | 6.6221 | 10.6119 | 0.8026 |

### green_onion

| model | n_test | MAE | RMSE | MAPE (%) | R2 |
| --- | ---: | ---: | ---: | ---: | ---: |
| naive_lag1 | 1587 | 6.3874 | 11.183 | 8.3038 | 0.9526 |
| seasonal_naive_lag7 | 1587 | 10.8667 | 20.6152 | 12.9796 | 0.8388 |
| moving_average_7 | 1587 | 7.4877 | 13.9543 | 9.321 | 0.9261 |
| moving_average_14 | 1587 | 9.5896 | 17.1453 | 12.0227 | 0.8885 |
| ridge_ts_regression | 1587 | 6.1748 | 10.7128 | 8.343 | 0.9565 |

### lettuce

| model | n_test | MAE | RMSE | MAPE (%) | R2 |
| --- | ---: | ---: | ---: | ---: | ---: |
| naive_lag1 | 1586 | 4.0981 | 6.0853 | 12.1114 | 0.8892 |
| seasonal_naive_lag7 | 1586 | 6.9727 | 10.3072 | 19.8471 | 0.6821 |
| moving_average_7 | 1586 | 4.9837 | 7.0678 | 14.5685 | 0.8505 |
| moving_average_14 | 1586 | 6.3331 | 8.9354 | 18.4835 | 0.7611 |
| ridge_ts_regression | 1586 | 3.8201 | 5.4444 | 11.2568 | 0.9113 |

## Interpretation

- Lower MAE/RMSE/MAPE is better.
- `R2` can be negative when a model is worse than predicting the test-period mean.
- If simple lag or moving-average models beat Ridge, the series is mostly short-memory and the current engineered features are not adding enough signal.
- This is the first baseline report. Prophet/SARIMA/XGBoost can be added after Python dependencies are available.

## Output files

- `metrics.csv`: all model metrics.
- `<crop>_predictions.csv`: actual and predicted values for each crop.
