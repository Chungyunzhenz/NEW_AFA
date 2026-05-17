# Weather feature comparison report

This report compares the original forecast models with models retrained after adding weather features.

Positive improvement means the weather-enhanced model reduced error.

## Best model comparison

| crop | base best | base RMSE | base MAPE | weather best | weather RMSE | weather MAPE | RMSE improvement | MAPE improvement |
| --- | --- | ---: | ---: | --- | ---: | ---: | ---: | ---: |
| bok_choy | xgboost | 3.9583 | 8.3266% | ridge | 3.8955 | 9.9140% | 1.59% | -19.07% |
| cabbage | xgboost | 2.1090 | 7.5252% | xgboost | 2.1895 | 7.6826% | -3.82% | -2.09% |
| cauliflower | xgboost | 5.7756 | 8.9067% | lightgbm | 6.0503 | 9.2469% | -4.76% | -3.82% |
| green_onion | ridge | 10.7128 | 8.3430% | ridge | 10.6395 | 8.5346% | 0.68% | -2.30% |
| lettuce | ridge | 5.4444 | 11.2568% | ridge | 5.3369 | 11.2801% | 1.97% | -0.21% |

## Notes

- Weather features include national daily temperature, rainfall, humidity, lagged weather values, rolling rainfall, and heavy-rain flags.
- If improvement is negative, the weather-enhanced model performed worse under the current feature set and hyperparameters.
- Weather may still help after crop-specific regional weighting or tuned lag windows.
