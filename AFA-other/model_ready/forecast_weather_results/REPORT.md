# Python forecast model report

Data source: `AFA-other/model_ready/forecast`.

The report compares simple baselines, classical time-series models, and machine-learning regressors.
ML models use lag, rolling, calendar, and volume features prepared from past values.

## Best model by crop

| crop | best model | MAE | RMSE | MAPE (%) | R2 |
| --- | --- | ---: | ---: | ---: | ---: |
| bok_choy | ridge | 2.4785 | 3.8955 | 9.9140 | 0.9285 |
| cabbage | xgboost | 1.4512 | 2.1895 | 7.6826 | 0.9502 |
| cauliflower | lightgbm | 3.5780 | 6.0503 | 9.2469 | 0.8352 |
| green_onion | ridge | 6.2300 | 10.6395 | 8.5346 | 0.9571 |
| lettuce | ridge | 3.8005 | 5.3369 | 11.2801 | 0.9148 |

## Full metrics

### cabbage

| model | n_test | MAE | RMSE | MAPE (%) | R2 |
| --- | ---: | ---: | ---: | ---: | ---: |
| xgboost | 1548 | 1.4512 | 2.1895 | 7.6826 | 0.9502 |
| lightgbm | 1548 | 1.4704 | 2.2333 | 7.7125 | 0.9482 |
| random_forest | 1548 | 1.5015 | 2.2527 | 8.0115 | 0.9472 |
| ridge | 1548 | 1.6158 | 2.3266 | 9.2733 | 0.9437 |
| naive_lag1 | 1548 | 1.6003 | 2.5495 | 8.5061 | 0.9324 |
| moving_average_7 | 1548 | 2.1562 | 3.1423 | 11.0904 | 0.8974 |
| moving_average_14 | 1548 | 2.8454 | 3.9746 | 14.6724 | 0.8358 |
| seasonal_naive_lag7 | 1548 | 3.2420 | 4.6141 | 16.6751 | 0.7787 |
| prophet | 1548 | 7.5755 | 9.1880 | 59.0463 | 0.1225 |
| sarima_weekly | 1548 | 15.0282 | 18.1176 | 69.3270 | -2.4121 |

### bok_choy

| model | n_test | MAE | RMSE | MAPE (%) | R2 |
| --- | ---: | ---: | ---: | ---: | ---: |
| ridge | 1543 | 2.4785 | 3.8955 | 9.9140 | 0.9285 |
| xgboost | 1543 | 2.3034 | 4.1503 | 8.3701 | 0.9188 |
| lightgbm | 1543 | 2.3339 | 4.1791 | 8.4455 | 0.9177 |
| naive_lag1 | 1543 | 2.7163 | 4.2798 | 10.0861 | 0.9137 |
| random_forest | 1543 | 2.6426 | 4.6326 | 9.6275 | 0.8988 |
| moving_average_7 | 1543 | 4.9565 | 7.9063 | 17.9453 | 0.7054 |
| moving_average_14 | 1543 | 6.6039 | 10.1895 | 24.8126 | 0.5106 |
| seasonal_naive_lag7 | 1543 | 7.7794 | 12.4739 | 28.3282 | 0.2666 |
| sarima_weekly | 1543 | 17.4026 | 22.9586 | 60.7871 | -1.4846 |

### cauliflower

| model | n_test | MAE | RMSE | MAPE (%) | R2 |
| --- | ---: | ---: | ---: | ---: | ---: |
| lightgbm | 1548 | 3.5780 | 6.0503 | 9.2469 | 0.8352 |
| xgboost | 1548 | 3.5880 | 6.0559 | 9.2134 | 0.8349 |
| ridge | 1548 | 3.9279 | 6.4938 | 10.5866 | 0.8101 |
| moving_average_7 | 1548 | 4.8028 | 7.1213 | 13.7708 | 0.7717 |
| random_forest | 1548 | 4.0817 | 7.1992 | 10.4064 | 0.7667 |
| moving_average_14 | 1548 | 5.7120 | 8.1351 | 16.6584 | 0.7020 |
| naive_lag1 | 1548 | 4.9650 | 8.4147 | 13.2625 | 0.6812 |
| seasonal_naive_lag7 | 1548 | 6.6361 | 9.2815 | 19.1331 | 0.6121 |
| sarima_weekly | 1548 | 11.5176 | 15.4219 | 33.5766 | -0.0708 |

### green_onion

| model | n_test | MAE | RMSE | MAPE (%) | R2 |
| --- | ---: | ---: | ---: | ---: | ---: |
| ridge | 1587 | 6.2300 | 10.6395 | 8.5346 | 0.9571 |
| naive_lag1 | 1587 | 6.3874 | 11.1830 | 8.3038 | 0.9526 |
| moving_average_7 | 1587 | 7.4877 | 13.9543 | 9.3210 | 0.9261 |
| random_forest | 1587 | 6.5093 | 14.2905 | 7.3743 | 0.9225 |
| lightgbm | 1587 | 6.7928 | 14.7547 | 7.8395 | 0.9174 |
| xgboost | 1587 | 7.0465 | 15.1249 | 8.2332 | 0.9132 |
| moving_average_14 | 1587 | 9.5896 | 17.1453 | 12.0227 | 0.8885 |
| seasonal_naive_lag7 | 1587 | 10.8667 | 20.6152 | 12.9796 | 0.8388 |
| sarima_weekly | 1587 | 312.7941 | 324.0210 | 643.5361 | -38.8305 |

### lettuce

| model | n_test | MAE | RMSE | MAPE (%) | R2 |
| --- | ---: | ---: | ---: | ---: | ---: |
| ridge | 1586 | 3.8005 | 5.3369 | 11.2801 | 0.9148 |
| xgboost | 1586 | 3.5165 | 5.5133 | 9.4276 | 0.9090 |
| lightgbm | 1586 | 3.6027 | 5.5432 | 9.7299 | 0.9081 |
| random_forest | 1586 | 3.9661 | 6.0185 | 10.8050 | 0.8916 |
| naive_lag1 | 1586 | 4.0981 | 6.0853 | 12.1114 | 0.8892 |
| moving_average_7 | 1586 | 4.9837 | 7.0678 | 14.5685 | 0.8505 |
| moving_average_14 | 1586 | 6.3331 | 8.9354 | 18.4835 | 0.7611 |
| seasonal_naive_lag7 | 1586 | 6.9727 | 10.3072 | 19.8471 | 0.6821 |
| sarima_weekly | 1586 | 36.0351 | 39.3206 | 157.3485 | -3.6262 |

## Model failures

- bok_choy / prophet: AttributeError("'Prophet' object has no attribute 'stan_backend'")
- cauliflower / prophet: AttributeError("'Prophet' object has no attribute 'stan_backend'")
- green_onion / prophet: AttributeError("'Prophet' object has no attribute 'stan_backend'")
- lettuce / prophet: AttributeError("'Prophet' object has no attribute 'stan_backend'")

## Output files

- `metrics.csv`: all metrics.
- `<crop>_predictions.csv`: actual and predicted values by date.
