# Trainable Forecast Weather Training Report

Data source: `AFA-other/model_ready/trainable_forecast_weather`.

Each model predicts future price using information available at `ds` only.

## Best Price Prediction Models

| crop | horizon | best model | MAE | RMSE | MAPE (%) | R2 |
| --- | ---: | --- | ---: | ---: | ---: | ---: |
| bok_choy | 1 | ridge | 2.5291 | 3.8383 | 10.0596 | 0.9306 |
| bok_choy | 5 | ridge | 5.3918 | 8.0920 | 21.1553 | 0.6913 |
| bok_choy | 7 | ridge | 5.9899 | 9.0989 | 23.3113 | 0.6098 |
| bok_choy | 14 | ridge | 7.8830 | 12.4941 | 28.8315 | 0.2642 |
| bok_choy | 20 | random_forest | 9.0430 | 13.5474 | 34.3843 | 0.1349 |
| cabbage | 1 | xgboost | 1.4297 | 2.1964 | 7.6136 | 0.9499 |
| cabbage | 5 | ridge | 2.6794 | 3.7760 | 14.5414 | 0.8518 |
| cabbage | 7 | ridge | 3.0110 | 4.1456 | 17.0540 | 0.8214 |
| cabbage | 14 | ridge | 4.0078 | 5.2628 | 24.1669 | 0.7121 |
| cabbage | 20 | ridge | 4.6475 | 6.0510 | 29.2155 | 0.6194 |
| cauliflower | 1 | ridge | 4.1487 | 6.8431 | 11.2019 | 0.7892 |
| cauliflower | 5 | ridge | 5.4911 | 7.8421 | 15.9445 | 0.7231 |
| cauliflower | 7 | ridge | 5.7965 | 8.0518 | 17.0735 | 0.7081 |
| cauliflower | 14 | ridge | 6.7788 | 9.2636 | 20.2734 | 0.6136 |
| cauliflower | 20 | ridge | 7.1951 | 10.0256 | 21.5004 | 0.5475 |
| green_onion | 1 | ridge | 6.0094 | 10.4275 | 7.8885 | 0.9587 |
| green_onion | 5 | ridge | 9.3857 | 17.0276 | 12.2905 | 0.8900 |
| green_onion | 7 | ridge | 10.3472 | 18.4037 | 13.3761 | 0.8715 |
| green_onion | 14 | ridge | 14.7082 | 24.0792 | 19.2416 | 0.7800 |
| green_onion | 20 | ridge | 17.8373 | 28.9511 | 23.1256 | 0.6820 |
| lettuce | 1 | ridge | 3.8556 | 5.4291 | 11.6027 | 0.9118 |
| lettuce | 5 | ridge | 5.9026 | 7.9906 | 18.1236 | 0.8089 |
| lettuce | 7 | ridge | 6.2944 | 8.6418 | 19.1558 | 0.7765 |
| lettuce | 14 | ridge | 8.5624 | 11.8417 | 25.6696 | 0.5804 |
| lettuce | 20 | xgboost | 8.8814 | 13.0048 | 23.7456 | 0.4939 |

## Best Classification Models by F1

| crop | horizon | task | best model | accuracy | precision | recall | f1_score | positives |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| bok_choy | 1 | target_rise_ge_10pct_h1 | ridge | 0.7660 | 0.4226 | 0.2119 | 0.2823 | 335/1543 |
| bok_choy | 1 | target_rise_ge_5pct_h1 | lightgbm | 0.6967 | 0.5623 | 0.3635 | 0.4415 | 509/1543 |
| bok_choy | 1 | target_up_h1 | xgboost | 0.6753 | 0.6914 | 0.6294 | 0.6590 | 769/1543 |
| bok_choy | 5 | target_rise_ge_10pct_h5 | ridge | 0.7187 | 0.6397 | 0.4991 | 0.5607 | 555/1543 |
| bok_choy | 5 | target_rise_ge_5pct_h5 | ridge | 0.7103 | 0.6926 | 0.5615 | 0.6202 | 650/1543 |
| bok_choy | 5 | target_up_h5 | xgboost | 0.6915 | 0.6977 | 0.6905 | 0.6941 | 782/1543 |
| bok_choy | 7 | target_rise_ge_10pct_h7 | xgboost | 0.6909 | 0.5915 | 0.5783 | 0.5849 | 581/1543 |
| bok_choy | 7 | target_rise_ge_5pct_h7 | random_forest | 0.6572 | 0.5825 | 0.6880 | 0.6308 | 657/1543 |
| bok_choy | 7 | target_up_h7 | xgboost | 0.6909 | 0.6796 | 0.7090 | 0.6940 | 763/1543 |
| bok_choy | 14 | target_rise_ge_10pct_h14 | ridge | 0.7362 | 0.6963 | 0.6074 | 0.6488 | 619/1543 |
| bok_choy | 14 | target_rise_ge_5pct_h14 | ridge | 0.7233 | 0.7174 | 0.6199 | 0.6651 | 684/1543 |
| bok_choy | 14 | target_up_h14 | ridge | 0.7220 | 0.7554 | 0.6474 | 0.6972 | 763/1543 |
| bok_choy | 20 | target_rise_ge_10pct_h20 | ridge | 0.7297 | 0.7271 | 0.6119 | 0.6645 | 675/1543 |
| bok_choy | 20 | target_rise_ge_5pct_h20 | ridge | 0.7285 | 0.7427 | 0.6360 | 0.6852 | 717/1543 |
| bok_choy | 20 | target_up_h20 | ridge | 0.7285 | 0.7669 | 0.6679 | 0.7140 | 783/1543 |
| cabbage | 1 | target_rise_ge_10pct_h1 | xgboost | 0.8592 | 0.5921 | 0.3659 | 0.4523 | 246/1548 |
| cabbage | 1 | target_rise_ge_5pct_h1 | lightgbm | 0.7545 | 0.5647 | 0.4252 | 0.4851 | 421/1548 |
| cabbage | 1 | target_up_h1 | xgboost | 0.6615 | 0.6652 | 0.6067 | 0.6346 | 750/1548 |
| cabbage | 5 | target_rise_ge_10pct_h5 | ann | 0.6079 | 0.3760 | 0.5022 | 0.4300 | 456/1548 |
| cabbage | 5 | target_rise_ge_5pct_h5 | xgboost | 0.6195 | 0.5150 | 0.5632 | 0.5380 | 609/1548 |
| cabbage | 5 | target_up_h5 | ridge | 0.6499 | 0.6473 | 0.7010 | 0.6731 | 796/1548 |
| cabbage | 7 | target_rise_ge_10pct_h7 | ridge | 0.6673 | 0.4541 | 0.3828 | 0.4154 | 478/1548 |
| cabbage | 7 | target_rise_ge_5pct_h7 | ridge | 0.6363 | 0.5531 | 0.5240 | 0.5381 | 626/1548 |
| cabbage | 7 | target_up_h7 | ridge | 0.6512 | 0.6323 | 0.7096 | 0.6687 | 768/1548 |
| cabbage | 14 | target_rise_ge_10pct_h14 | ridge | 0.6932 | 0.5690 | 0.6507 | 0.6071 | 564/1548 |
| cabbage | 14 | target_rise_ge_5pct_h14 | ridge | 0.6925 | 0.6119 | 0.7412 | 0.6704 | 653/1548 |
| cabbage | 14 | target_up_h14 | ridge | 0.6880 | 0.6448 | 0.8058 | 0.7164 | 757/1548 |
| cabbage | 20 | target_rise_ge_10pct_h20 | ridge | 0.7442 | 0.6404 | 0.7828 | 0.7045 | 603/1548 |
| cabbage | 20 | target_rise_ge_5pct_h20 | ridge | 0.7255 | 0.6485 | 0.8107 | 0.7206 | 676/1548 |
| cabbage | 20 | target_up_h20 | ridge | 0.7093 | 0.6518 | 0.8466 | 0.7365 | 743/1548 |
| cauliflower | 1 | target_rise_ge_10pct_h1 | xgboost | 0.7920 | 0.6234 | 0.3911 | 0.4806 | 381/1548 |
| cauliflower | 1 | target_rise_ge_5pct_h1 | xgboost | 0.7235 | 0.6184 | 0.5453 | 0.5796 | 541/1548 |
| cauliflower | 1 | target_up_h1 | xgboost | 0.6641 | 0.6463 | 0.7513 | 0.6948 | 788/1548 |
| cauliflower | 5 | target_rise_ge_10pct_h5 | xgboost | 0.7203 | 0.5625 | 0.5316 | 0.5466 | 491/1548 |
| cauliflower | 5 | target_rise_ge_5pct_h5 | ridge | 0.6835 | 0.6263 | 0.5570 | 0.5896 | 632/1548 |
| cauliflower | 5 | target_up_h5 | ridge | 0.6609 | 0.6633 | 0.6641 | 0.6637 | 780/1548 |
| cauliflower | 7 | target_rise_ge_10pct_h7 | lightgbm | 0.7016 | 0.5496 | 0.5410 | 0.5453 | 512/1548 |
| cauliflower | 7 | target_rise_ge_5pct_h7 | lightgbm | 0.6809 | 0.6018 | 0.6268 | 0.6141 | 627/1548 |
| cauliflower | 7 | target_up_h7 | ridge | 0.6647 | 0.6628 | 0.6654 | 0.6641 | 771/1548 |
| cauliflower | 14 | target_rise_ge_10pct_h14 | ridge | 0.7597 | 0.6647 | 0.6227 | 0.6430 | 538/1548 |
| cauliflower | 14 | target_rise_ge_5pct_h14 | ridge | 0.7390 | 0.6775 | 0.6904 | 0.6839 | 633/1548 |
| cauliflower | 14 | target_up_h14 | ridge | 0.7222 | 0.6943 | 0.7470 | 0.7197 | 739/1548 |
| cauliflower | 20 | target_rise_ge_10pct_h20 | ridge | 0.7894 | 0.6922 | 0.7373 | 0.7140 | 552/1548 |
| cauliflower | 20 | target_rise_ge_5pct_h20 | ridge | 0.7758 | 0.7100 | 0.7795 | 0.7432 | 644/1548 |
| cauliflower | 20 | target_up_h20 | ridge | 0.7578 | 0.7204 | 0.8016 | 0.7588 | 736/1548 |
| green_onion | 1 | target_rise_ge_10pct_h1 | ridge | 0.8500 | 0.5673 | 0.3716 | 0.4491 | 261/1587 |
| green_onion | 1 | target_rise_ge_5pct_h1 | ridge | 0.7505 | 0.5574 | 0.4658 | 0.5075 | 438/1587 |
| green_onion | 1 | target_up_h1 | lightgbm | 0.6371 | 0.6336 | 0.6807 | 0.6563 | 808/1587 |
| green_onion | 5 | target_rise_ge_10pct_h5 | xgboost | 0.7750 | 0.5049 | 0.4278 | 0.4632 | 360/1587 |
| green_onion | 5 | target_rise_ge_5pct_h5 | xgboost | 0.7089 | 0.5350 | 0.5242 | 0.5295 | 496/1587 |
| green_onion | 5 | target_up_h5 | lightgbm | 0.6641 | 0.6528 | 0.6688 | 0.6607 | 776/1587 |
| green_onion | 7 | target_rise_ge_10pct_h7 | lightgbm | 0.7480 | 0.4051 | 0.4294 | 0.4169 | 333/1587 |
| green_onion | 7 | target_rise_ge_5pct_h7 | lightgbm | 0.6849 | 0.4723 | 0.5064 | 0.4888 | 472/1587 |
| green_onion | 7 | target_up_h7 | random_forest | 0.6345 | 0.6075 | 0.5775 | 0.5921 | 729/1587 |
| green_onion | 14 | target_rise_ge_10pct_h14 | lightgbm | 0.7643 | 0.5414 | 0.4851 | 0.5117 | 404/1587 |
| green_onion | 14 | target_rise_ge_5pct_h14 | lightgbm | 0.7265 | 0.5901 | 0.5097 | 0.5470 | 514/1587 |
| green_onion | 14 | target_up_h14 | ridge | 0.6547 | 0.6183 | 0.5616 | 0.5886 | 698/1587 |
| green_onion | 20 | target_rise_ge_10pct_h20 | lightgbm | 0.7725 | 0.6462 | 0.4979 | 0.5624 | 466/1587 |
| green_onion | 20 | target_rise_ge_5pct_h20 | lightgbm | 0.7549 | 0.6842 | 0.5267 | 0.5952 | 543/1587 |
| green_onion | 20 | target_up_h20 | ridge | 0.7038 | 0.6862 | 0.6037 | 0.6423 | 699/1587 |
| lettuce | 1 | target_rise_ge_10pct_h1 | xgboost | 0.7863 | 0.5207 | 0.3247 | 0.4000 | 348/1586 |
| lettuce | 1 | target_rise_ge_5pct_h1 | ridge | 0.6854 | 0.4980 | 0.4930 | 0.4954 | 497/1586 |
| lettuce | 1 | target_up_h1 | lightgbm | 0.6633 | 0.6849 | 0.6128 | 0.6468 | 798/1586 |
| lettuce | 5 | target_rise_ge_10pct_h5 | xgboost | 0.7371 | 0.6400 | 0.4598 | 0.5351 | 522/1586 |
| lettuce | 5 | target_rise_ge_5pct_h5 | lightgbm | 0.6929 | 0.6352 | 0.5503 | 0.5897 | 636/1586 |
| lettuce | 5 | target_up_h5 | ridge | 0.6835 | 0.7014 | 0.6844 | 0.6928 | 827/1586 |
| lettuce | 7 | target_rise_ge_10pct_h7 | xgboost | 0.7182 | 0.5732 | 0.4635 | 0.5125 | 507/1586 |
| lettuce | 7 | target_rise_ge_5pct_h7 | xgboost | 0.6942 | 0.6160 | 0.5443 | 0.5779 | 610/1586 |
| lettuce | 7 | target_up_h7 | ridge | 0.6835 | 0.6938 | 0.6766 | 0.6851 | 807/1586 |
| lettuce | 14 | target_rise_ge_10pct_h14 | ridge | 0.6753 | 0.5556 | 0.5527 | 0.5541 | 579/1586 |
| lettuce | 14 | target_rise_ge_5pct_h14 | ridge | 0.6696 | 0.5930 | 0.6022 | 0.5975 | 646/1586 |
| lettuce | 14 | target_up_h14 | ridge | 0.7011 | 0.7005 | 0.6825 | 0.6914 | 778/1586 |
| lettuce | 20 | target_rise_ge_10pct_h20 | ridge | 0.7289 | 0.6514 | 0.6146 | 0.6325 | 602/1586 |
| lettuce | 20 | target_rise_ge_5pct_h20 | lightgbm | 0.7427 | 0.7458 | 0.5973 | 0.6634 | 673/1586 |
| lettuce | 20 | target_up_h20 | ridge | 0.7106 | 0.7108 | 0.6822 | 0.6962 | 771/1586 |

## Output Files

- `regression_metrics.csv`: MAE/RMSE/MAPE/R2 for all models.
- `classification_metrics.csv`: Accuracy/Precision/Recall/F1 for all warning targets.
- `<crop>_h<horizon>_predictions.csv`: date-level actual and predicted prices.
