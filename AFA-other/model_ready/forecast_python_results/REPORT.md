# Python forecast model report

Data source: `AFA-other/model_ready/forecast`.

The report compares simple baselines, classical time-series models, machine-learning regressors, and an ANN model.
ML and ANN models use lag, rolling, calendar, and volume features prepared from past values.

## Best model by crop

| crop | best model | MAE | RMSE | MAPE (%) | R2 |
| --- | --- | ---: | ---: | ---: | ---: |
| bok_choy | xgboost | 2.2629 | 3.9583 | 8.3266 | 0.9261 |
| cabbage | xgboost | 1.4158 | 2.1090 | 7.5252 | 0.9538 |
| cauliflower | xgboost | 3.4573 | 5.7756 | 8.9067 | 0.8498 |
| green_onion | ridge | 6.1748 | 10.7128 | 8.3430 | 0.9565 |
| lettuce | ann | 3.6745 | 5.1790 | 11.1158 | 0.9197 |

## Full metrics

### cabbage

| model | n_test | MAE | RMSE | MAPE (%) | R2 |
| --- | ---: | ---: | ---: | ---: | ---: |
| xgboost | 1548 | 1.4158 | 2.1090 | 7.5252 | 0.9538 |
| lightgbm | 1548 | 1.4260 | 2.1168 | 7.5885 | 0.9534 |
| random_forest | 1548 | 1.4547 | 2.1592 | 7.8413 | 0.9515 |
| ann | 1548 | 1.6177 | 2.2291 | 9.2100 | 0.9483 |
| ridge | 1548 | 1.6123 | 2.3248 | 9.1518 | 0.9438 |
| naive_lag1 | 1548 | 1.6003 | 2.5495 | 8.5061 | 0.9324 |
| moving_average_7 | 1548 | 2.1562 | 3.1423 | 11.0904 | 0.8974 |
| moving_average_14 | 1548 | 2.8454 | 3.9746 | 14.6724 | 0.8358 |
| seasonal_naive_lag7 | 1548 | 3.2420 | 4.6141 | 16.6751 | 0.7787 |
| prophet | 1548 | 7.6951 | 9.3556 | 60.2475 | 0.0902 |
| sarima_weekly | 1548 | 15.0282 | 18.1176 | 69.3270 | -2.4121 |

### bok_choy

| model | n_test | MAE | RMSE | MAPE (%) | R2 |
| --- | ---: | ---: | ---: | ---: | ---: |
| xgboost | 1543 | 2.2629 | 3.9583 | 8.3266 | 0.9261 |
| lightgbm | 1543 | 2.2623 | 3.9996 | 8.1996 | 0.9246 |
| ann | 1543 | 2.5764 | 4.0474 | 10.5282 | 0.9228 |
| ridge | 1543 | 2.6613 | 4.1474 | 10.4267 | 0.9189 |
| naive_lag1 | 1543 | 2.7163 | 4.2798 | 10.0861 | 0.9137 |
| random_forest | 1543 | 2.5805 | 4.4626 | 9.4213 | 0.9061 |
| moving_average_7 | 1543 | 4.9565 | 7.9063 | 17.9453 | 0.7054 |
| moving_average_14 | 1543 | 6.6039 | 10.1895 | 24.8126 | 0.5106 |
| seasonal_naive_lag7 | 1543 | 7.7794 | 12.4739 | 28.3282 | 0.2666 |
| prophet | 1543 | 8.8523 | 13.7558 | 33.1866 | 0.1081 |
| sarima_weekly | 1543 | 17.4030 | 22.9589 | 60.7888 | -1.4846 |

### cauliflower

| model | n_test | MAE | RMSE | MAPE (%) | R2 |
| --- | ---: | ---: | ---: | ---: | ---: |
| xgboost | 1548 | 3.4573 | 5.7756 | 8.9067 | 0.8498 |
| lightgbm | 1548 | 3.4997 | 5.8616 | 9.0389 | 0.8453 |
| ann | 1548 | 3.9553 | 6.0015 | 10.8815 | 0.8378 |
| ridge | 1548 | 4.0128 | 6.6221 | 10.6119 | 0.8026 |
| random_forest | 1548 | 3.9919 | 6.9770 | 10.2470 | 0.7808 |
| moving_average_7 | 1548 | 4.8028 | 7.1213 | 13.7708 | 0.7717 |
| moving_average_14 | 1548 | 5.7120 | 8.1351 | 16.6584 | 0.7020 |
| naive_lag1 | 1548 | 4.9650 | 8.4147 | 13.2625 | 0.6812 |
| prophet | 1548 | 6.1739 | 8.8416 | 19.3687 | 0.6480 |
| seasonal_naive_lag7 | 1548 | 6.6361 | 9.2815 | 19.1331 | 0.6121 |
| sarima_weekly | 1548 | 11.5176 | 15.4219 | 33.5766 | -0.0708 |

### green_onion

| model | n_test | MAE | RMSE | MAPE (%) | R2 |
| --- | ---: | ---: | ---: | ---: | ---: |
| ridge | 1587 | 6.1748 | 10.7128 | 8.3430 | 0.9565 |
| naive_lag1 | 1587 | 6.3874 | 11.1830 | 8.3038 | 0.9526 |
| ann | 1587 | 8.6058 | 12.7135 | 13.8656 | 0.9387 |
| random_forest | 1587 | 6.5391 | 13.6959 | 7.6037 | 0.9288 |
| xgboost | 1587 | 6.5674 | 13.8333 | 7.8031 | 0.9274 |
| moving_average_7 | 1587 | 7.4877 | 13.9543 | 9.3210 | 0.9261 |
| lightgbm | 1587 | 6.6532 | 14.2473 | 7.7606 | 0.9230 |
| moving_average_14 | 1587 | 9.5896 | 17.1453 | 12.0227 | 0.8885 |
| seasonal_naive_lag7 | 1587 | 10.8667 | 20.6152 | 12.9796 | 0.8388 |
| prophet | 1587 | 61.8580 | 78.1738 | 84.3692 | -1.3184 |
| sarima_weekly | 1587 | 312.7941 | 324.0210 | 643.5361 | -38.8305 |

### lettuce

| model | n_test | MAE | RMSE | MAPE (%) | R2 |
| --- | ---: | ---: | ---: | ---: | ---: |
| ann | 1586 | 3.6745 | 5.1790 | 11.1158 | 0.9197 |
| ridge | 1586 | 3.8201 | 5.4444 | 11.2568 | 0.9113 |
| xgboost | 1586 | 3.5316 | 5.5180 | 9.4793 | 0.9089 |
| lightgbm | 1586 | 3.5706 | 5.5428 | 9.5695 | 0.9081 |
| random_forest | 1586 | 3.9922 | 6.0535 | 10.8744 | 0.8904 |
| naive_lag1 | 1586 | 4.0981 | 6.0853 | 12.1114 | 0.8892 |
| moving_average_7 | 1586 | 4.9837 | 7.0678 | 14.5685 | 0.8505 |
| moving_average_14 | 1586 | 6.3331 | 8.9354 | 18.4835 | 0.7611 |
| seasonal_naive_lag7 | 1586 | 6.9727 | 10.3072 | 19.8471 | 0.6821 |
| prophet | 1586 | 9.8585 | 13.2141 | 31.7637 | 0.4775 |
| sarima_weekly | 1586 | 36.0351 | 39.3206 | 157.3485 | -3.6262 |

## Output files

- `metrics.csv`: all metrics.
- `<crop>_predictions.csv`: actual and predicted values by date.
