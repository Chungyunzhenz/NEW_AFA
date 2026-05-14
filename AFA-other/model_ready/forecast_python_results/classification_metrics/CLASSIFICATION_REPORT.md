# Forecast classification metrics

These metrics reinterpret price forecasts as warning/classification tasks.

Tasks:

- `direction_up`: predicted price change >= 0%.
- `rise_ge_5pct`: predicted price change >= 5%.
- `rise_ge_10pct`: predicted price change >= 10%.

The previous actual price is used as the reference price for both actual and predicted change rates.

## Best F1 by crop and task

| crop | task | best model | accuracy | precision | recall | f1_score | positives |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| bok_choy | direction_up | lightgbm | 0.7127 | 0.7677 | 0.6068 | 0.6778 | 768/1542 |
| bok_choy | rise_ge_10pct | lightgbm | 0.8113 | 0.6807 | 0.2425 | 0.3576 | 334/1542 |
| bok_choy | rise_ge_5pct | lightgbm | 0.7497 | 0.7133 | 0.4016 | 0.5139 | 508/1542 |
| cabbage | direction_up | naive_lag1 | 0.4848 | 0.4848 | 1.0000 | 0.6530 | 750/1547 |
| cabbage | rise_ge_10pct | xgboost | 0.8597 | 0.6218 | 0.3008 | 0.4055 | 246/1547 |
| cabbage | rise_ge_5pct | lightgbm | 0.7796 | 0.6667 | 0.3800 | 0.4841 | 421/1547 |
| cauliflower | direction_up | lightgbm | 0.7447 | 0.7748 | 0.7030 | 0.7372 | 788/1547 |
| cauliflower | rise_ge_10pct | lightgbm | 0.8087 | 0.7457 | 0.3386 | 0.4657 | 381/1547 |
| cauliflower | rise_ge_5pct | lightgbm | 0.7576 | 0.7413 | 0.4713 | 0.5763 | 541/1547 |
| green_onion | direction_up | lightgbm | 0.6652 | 0.6507 | 0.7385 | 0.6918 | 807/1586 |
| green_onion | rise_ge_10pct | lightgbm | 0.8216 | 0.4613 | 0.5019 | 0.4807 | 261/1586 |
| green_onion | rise_ge_5pct | lightgbm | 0.7144 | 0.4848 | 0.5479 | 0.5145 | 438/1586 |
| lettuce | direction_up | xgboost | 0.7293 | 0.7933 | 0.6253 | 0.6994 | 798/1585 |
| lettuce | rise_ge_10pct | lightgbm | 0.8221 | 0.6320 | 0.4540 | 0.5284 | 348/1585 |
| lettuce | rise_ge_5pct | lightgbm | 0.7539 | 0.6321 | 0.5151 | 0.5676 | 497/1585 |

## Full Metrics

### direction_up

| crop | model | accuracy | precision | recall | f1_score | tp | fp | fn | tn |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| bok_choy | lightgbm | 0.7127 | 0.7677 | 0.6068 | 0.6778 | 466 | 141 | 302 | 633 |
| bok_choy | naive_lag1 | 0.4981 | 0.4981 | 1.0000 | 0.6649 | 768 | 774 | 0 | 0 |
| bok_choy | xgboost | 0.7010 | 0.7642 | 0.5781 | 0.6583 | 444 | 137 | 324 | 637 |
| bok_choy | random_forest | 0.6368 | 0.6552 | 0.5716 | 0.6106 | 439 | 231 | 329 | 543 |
| bok_choy | seasonal_naive_lag7 | 0.5078 | 0.5059 | 0.5065 | 0.5062 | 389 | 380 | 379 | 394 |
| bok_choy | moving_average_14 | 0.4890 | 0.4879 | 0.5234 | 0.5050 | 402 | 422 | 366 | 352 |
| bok_choy | moving_average_7 | 0.4812 | 0.4800 | 0.5013 | 0.4904 | 385 | 417 | 383 | 357 |
| bok_choy | ridge | 0.6070 | 0.7613 | 0.3073 | 0.4378 | 236 | 74 | 532 | 700 |
| bok_choy | sarima_weekly | 0.5032 | 1.0000 | 0.0026 | 0.0052 | 2 | 0 | 766 | 774 |
| cabbage | naive_lag1 | 0.4848 | 0.4848 | 1.0000 | 0.6530 | 750 | 797 | 0 | 0 |
| cabbage | prophet | 0.5229 | 0.5048 | 0.8387 | 0.6303 | 629 | 617 | 121 | 180 |
| cabbage | xgboost | 0.6813 | 0.7485 | 0.5160 | 0.6109 | 387 | 130 | 363 | 667 |
| cabbage | lightgbm | 0.6800 | 0.7476 | 0.5133 | 0.6087 | 385 | 130 | 365 | 667 |
| cabbage | random_forest | 0.6367 | 0.6546 | 0.5307 | 0.5862 | 398 | 210 | 352 | 587 |
| cabbage | ridge | 0.5669 | 0.5539 | 0.5480 | 0.5509 | 411 | 331 | 339 | 466 |
| cabbage | moving_average_7 | 0.5488 | 0.5328 | 0.5627 | 0.5473 | 422 | 370 | 328 | 427 |
| cabbage | moving_average_14 | 0.5314 | 0.5156 | 0.5493 | 0.5320 | 412 | 387 | 338 | 410 |
| cabbage | seasonal_naive_lag7 | 0.5404 | 0.5256 | 0.5333 | 0.5295 | 400 | 361 | 350 | 436 |
| cabbage | sarima_weekly | 0.5158 | 0.6667 | 0.0027 | 0.0053 | 2 | 1 | 748 | 796 |
| cauliflower | lightgbm | 0.7447 | 0.7748 | 0.7030 | 0.7372 | 554 | 161 | 234 | 598 |
| cauliflower | xgboost | 0.7427 | 0.7686 | 0.7081 | 0.7371 | 558 | 168 | 230 | 591 |
| cauliflower | random_forest | 0.7027 | 0.6966 | 0.7373 | 0.7164 | 581 | 253 | 207 | 506 |
| cauliflower | naive_lag1 | 0.5094 | 0.5094 | 1.0000 | 0.6749 | 788 | 759 | 0 | 0 |
| cauliflower | ridge | 0.6923 | 0.7407 | 0.6091 | 0.6685 | 480 | 168 | 308 | 591 |
| cauliflower | moving_average_7 | 0.5947 | 0.5990 | 0.6180 | 0.6084 | 487 | 326 | 301 | 433 |
| cauliflower | moving_average_14 | 0.5876 | 0.5912 | 0.6168 | 0.6037 | 486 | 336 | 302 | 423 |
| cauliflower | seasonal_naive_lag7 | 0.5908 | 0.5968 | 0.6066 | 0.6016 | 478 | 323 | 310 | 436 |
| cauliflower | sarima_weekly | 0.5701 | 0.5865 | 0.5292 | 0.5564 | 417 | 294 | 371 | 465 |
| green_onion | lightgbm | 0.6652 | 0.6507 | 0.7385 | 0.6918 | 596 | 320 | 211 | 459 |
| green_onion | sarima_weekly | 0.5120 | 0.5105 | 0.9963 | 0.6751 | 804 | 771 | 3 | 8 |
| green_onion | naive_lag1 | 0.5088 | 0.5088 | 1.0000 | 0.6745 | 807 | 779 | 0 | 0 |
| green_onion | xgboost | 0.6381 | 0.6276 | 0.7100 | 0.6663 | 573 | 340 | 234 | 439 |
| green_onion | random_forest | 0.6400 | 0.6408 | 0.6654 | 0.6529 | 537 | 301 | 270 | 478 |
| green_onion | ridge | 0.5927 | 0.5838 | 0.6952 | 0.6346 | 561 | 400 | 246 | 379 |
| green_onion | seasonal_naive_lag7 | 0.5996 | 0.5956 | 0.6642 | 0.6280 | 536 | 364 | 271 | 415 |
| green_onion | moving_average_7 | 0.5908 | 0.5902 | 0.6406 | 0.6144 | 517 | 359 | 290 | 420 |
| green_onion | moving_average_14 | 0.5404 | 0.5438 | 0.5998 | 0.5704 | 484 | 406 | 323 | 373 |
| lettuce | xgboost | 0.7293 | 0.7933 | 0.6253 | 0.6994 | 499 | 130 | 299 | 657 |
| lettuce | lightgbm | 0.7091 | 0.7612 | 0.6153 | 0.6805 | 491 | 154 | 307 | 633 |
| lettuce | naive_lag1 | 0.5035 | 0.5035 | 1.0000 | 0.6697 | 798 | 787 | 0 | 0 |
| lettuce | sarima_weekly | 0.5136 | 0.5090 | 0.9524 | 0.6635 | 760 | 733 | 38 | 54 |
| lettuce | random_forest | 0.6890 | 0.7529 | 0.5689 | 0.6481 | 454 | 149 | 344 | 638 |
| lettuce | ridge | 0.6379 | 0.6609 | 0.5764 | 0.6158 | 460 | 236 | 338 | 551 |
| lettuce | seasonal_naive_lag7 | 0.5924 | 0.5929 | 0.6078 | 0.6002 | 485 | 333 | 313 | 454 |
| lettuce | moving_average_14 | 0.5722 | 0.5701 | 0.6115 | 0.5901 | 488 | 368 | 310 | 419 |
| lettuce | moving_average_7 | 0.5621 | 0.5624 | 0.5877 | 0.5748 | 469 | 365 | 329 | 422 |

### rise_ge_5pct

| crop | model | accuracy | precision | recall | f1_score | tp | fp | fn | tn |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| bok_choy | lightgbm | 0.7497 | 0.7133 | 0.4016 | 0.5139 | 204 | 82 | 304 | 952 |
| bok_choy | xgboost | 0.7451 | 0.7220 | 0.3681 | 0.4876 | 187 | 72 | 321 | 962 |
| bok_choy | seasonal_naive_lag7 | 0.5298 | 0.3349 | 0.4331 | 0.3777 | 220 | 437 | 288 | 597 |
| bok_choy | random_forest | 0.6926 | 0.5708 | 0.2697 | 0.3663 | 137 | 103 | 371 | 931 |
| bok_choy | moving_average_14 | 0.5058 | 0.3170 | 0.4331 | 0.3661 | 220 | 474 | 288 | 560 |
| bok_choy | moving_average_7 | 0.5246 | 0.3122 | 0.3681 | 0.3379 | 187 | 412 | 321 | 622 |
| bok_choy | ridge | 0.6835 | 0.5980 | 0.1201 | 0.2000 | 61 | 41 | 447 | 993 |
| bok_choy | sarima_weekly | 0.6712 | 1.0000 | 0.0020 | 0.0039 | 1 | 0 | 507 | 1034 |
| bok_choy | naive_lag1 | 0.6706 | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 508 | 1034 |
| cabbage | lightgbm | 0.7796 | 0.6667 | 0.3800 | 0.4841 | 160 | 80 | 261 | 1046 |
| cabbage | xgboost | 0.7750 | 0.6637 | 0.3515 | 0.4596 | 148 | 75 | 273 | 1051 |
| cabbage | prophet | 0.4137 | 0.2968 | 0.8432 | 0.4391 | 355 | 841 | 66 | 285 |
| cabbage | random_forest | 0.7602 | 0.6087 | 0.3325 | 0.4301 | 140 | 90 | 281 | 1036 |
| cabbage | seasonal_naive_lag7 | 0.5966 | 0.3317 | 0.4751 | 0.3906 | 200 | 403 | 221 | 723 |
| cabbage | moving_average_14 | 0.5850 | 0.3215 | 0.4727 | 0.3827 | 199 | 420 | 222 | 706 |
| cabbage | moving_average_7 | 0.6270 | 0.3471 | 0.4204 | 0.3802 | 177 | 333 | 244 | 793 |
| cabbage | ridge | 0.7143 | 0.4610 | 0.2945 | 0.3594 | 124 | 145 | 297 | 981 |
| cabbage | naive_lag1 | 0.7279 | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 421 | 1126 |
| cabbage | sarima_weekly | 0.7272 | 0.0000 | 0.0000 | 0.0000 | 0 | 1 | 421 | 1125 |
| cauliflower | lightgbm | 0.7576 | 0.7413 | 0.4713 | 0.5763 | 255 | 89 | 286 | 917 |
| cauliflower | xgboost | 0.7466 | 0.7411 | 0.4233 | 0.5388 | 229 | 80 | 312 | 926 |
| cauliflower | ridge | 0.7350 | 0.7120 | 0.4067 | 0.5176 | 220 | 89 | 321 | 917 |
| cauliflower | seasonal_naive_lag7 | 0.6193 | 0.4631 | 0.5564 | 0.5055 | 301 | 349 | 240 | 657 |
| cauliflower | moving_average_7 | 0.6438 | 0.4912 | 0.5176 | 0.5041 | 280 | 290 | 261 | 716 |
| cauliflower | moving_average_14 | 0.6115 | 0.4531 | 0.5360 | 0.4911 | 290 | 350 | 251 | 656 |
| cauliflower | sarima_weekly | 0.5856 | 0.4219 | 0.4991 | 0.4572 | 270 | 370 | 271 | 636 |
| cauliflower | random_forest | 0.7111 | 0.6715 | 0.3401 | 0.4515 | 184 | 90 | 357 | 916 |
| cauliflower | naive_lag1 | 0.6503 | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 541 | 1006 |
| green_onion | lightgbm | 0.7144 | 0.4848 | 0.5479 | 0.5145 | 240 | 255 | 198 | 893 |
| green_onion | xgboost | 0.7144 | 0.4841 | 0.5205 | 0.5017 | 228 | 243 | 210 | 905 |
| green_onion | moving_average_7 | 0.6828 | 0.4376 | 0.5205 | 0.4755 | 228 | 293 | 210 | 855 |
| green_onion | seasonal_naive_lag7 | 0.6362 | 0.3919 | 0.5753 | 0.4662 | 252 | 391 | 186 | 757 |
| green_onion | ridge | 0.7087 | 0.4712 | 0.4475 | 0.4590 | 196 | 220 | 242 | 928 |
| green_onion | random_forest | 0.7264 | 0.5056 | 0.4087 | 0.4520 | 179 | 175 | 259 | 973 |
| green_onion | moving_average_14 | 0.6261 | 0.3780 | 0.5479 | 0.4473 | 240 | 395 | 198 | 753 |
| green_onion | sarima_weekly | 0.2806 | 0.2763 | 0.9909 | 0.4321 | 434 | 1137 | 4 | 11 |
| green_onion | naive_lag1 | 0.7238 | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 438 | 1148 |
| lettuce | lightgbm | 0.7539 | 0.6321 | 0.5151 | 0.5676 | 256 | 149 | 241 | 939 |
| lettuce | xgboost | 0.7533 | 0.6338 | 0.5050 | 0.5622 | 251 | 145 | 246 | 943 |
| lettuce | seasonal_naive_lag7 | 0.6309 | 0.4308 | 0.5513 | 0.4837 | 274 | 362 | 223 | 726 |
| lettuce | sarima_weekly | 0.3546 | 0.3216 | 0.9537 | 0.4810 | 474 | 1000 | 23 | 88 |
| lettuce | ridge | 0.7085 | 0.5490 | 0.3944 | 0.4590 | 196 | 161 | 301 | 927 |
| lettuce | random_forest | 0.7180 | 0.5806 | 0.3622 | 0.4461 | 180 | 130 | 317 | 958 |
| lettuce | moving_average_14 | 0.5842 | 0.3805 | 0.5191 | 0.4391 | 258 | 420 | 239 | 668 |
| lettuce | moving_average_7 | 0.6038 | 0.3935 | 0.4869 | 0.4353 | 242 | 373 | 255 | 715 |
| lettuce | naive_lag1 | 0.6864 | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 497 | 1088 |

### rise_ge_10pct

| crop | model | accuracy | precision | recall | f1_score | tp | fp | fn | tn |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| bok_choy | lightgbm | 0.8113 | 0.6807 | 0.2425 | 0.3576 | 81 | 38 | 253 | 1170 |
| bok_choy | seasonal_naive_lag7 | 0.5895 | 0.2287 | 0.3772 | 0.2847 | 126 | 425 | 208 | 783 |
| bok_choy | xgboost | 0.8029 | 0.6667 | 0.1796 | 0.2830 | 60 | 30 | 274 | 1178 |
| bok_choy | moving_average_14 | 0.5746 | 0.2195 | 0.3772 | 0.2775 | 126 | 448 | 208 | 760 |
| bok_choy | moving_average_7 | 0.6161 | 0.2159 | 0.2934 | 0.2487 | 98 | 356 | 236 | 852 |
| bok_choy | random_forest | 0.7834 | 0.5000 | 0.1018 | 0.1692 | 34 | 34 | 300 | 1174 |
| bok_choy | ridge | 0.7853 | 0.5366 | 0.0659 | 0.1173 | 22 | 19 | 312 | 1189 |
| bok_choy | naive_lag1 | 0.7834 | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 334 | 1208 |
| bok_choy | sarima_weekly | 0.7834 | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 334 | 1208 |
| cabbage | xgboost | 0.8597 | 0.6218 | 0.3008 | 0.4055 | 74 | 45 | 172 | 1256 |
| cabbage | lightgbm | 0.8520 | 0.5639 | 0.3049 | 0.3958 | 75 | 58 | 171 | 1243 |
| cabbage | seasonal_naive_lag7 | 0.6910 | 0.2593 | 0.5081 | 0.3434 | 125 | 357 | 121 | 944 |
| cabbage | random_forest | 0.8546 | 0.6296 | 0.2073 | 0.3119 | 51 | 30 | 195 | 1271 |
| cabbage | prophet | 0.3975 | 0.1899 | 0.8537 | 0.3107 | 210 | 896 | 36 | 405 |
| cabbage | moving_average_7 | 0.7479 | 0.2707 | 0.3455 | 0.3036 | 85 | 229 | 161 | 1072 |
| cabbage | moving_average_14 | 0.6858 | 0.2333 | 0.4268 | 0.3017 | 105 | 345 | 141 | 956 |
| cabbage | ridge | 0.8268 | 0.4000 | 0.1789 | 0.2472 | 44 | 66 | 202 | 1235 |
| cabbage | naive_lag1 | 0.8410 | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 246 | 1301 |
| cabbage | sarima_weekly | 0.8410 | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 246 | 1301 |
| cauliflower | lightgbm | 0.8087 | 0.7457 | 0.3386 | 0.4657 | 129 | 44 | 252 | 1122 |
| cauliflower | xgboost | 0.8125 | 0.7826 | 0.3307 | 0.4649 | 126 | 35 | 255 | 1131 |
| cauliflower | seasonal_naive_lag7 | 0.6768 | 0.3904 | 0.5564 | 0.4589 | 212 | 331 | 169 | 835 |
| cauliflower | moving_average_7 | 0.7201 | 0.4337 | 0.4462 | 0.4398 | 170 | 222 | 211 | 944 |
| cauliflower | moving_average_14 | 0.6800 | 0.3841 | 0.4961 | 0.4330 | 189 | 303 | 192 | 863 |
| cauliflower | ridge | 0.7880 | 0.6906 | 0.2520 | 0.3692 | 96 | 43 | 285 | 1123 |
| cauliflower | sarima_weekly | 0.6037 | 0.3020 | 0.4646 | 0.3661 | 177 | 409 | 204 | 757 |
| cauliflower | random_forest | 0.7854 | 0.7207 | 0.2100 | 0.3252 | 80 | 31 | 301 | 1135 |
| cauliflower | naive_lag1 | 0.7537 | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 381 | 1166 |
| green_onion | lightgbm | 0.8216 | 0.4613 | 0.5019 | 0.4807 | 131 | 153 | 130 | 1172 |
| green_onion | xgboost | 0.8272 | 0.4751 | 0.4751 | 0.4751 | 124 | 137 | 137 | 1188 |
| green_onion | ridge | 0.8398 | 0.5174 | 0.3985 | 0.4502 | 104 | 97 | 157 | 1228 |
| green_onion | random_forest | 0.8323 | 0.4876 | 0.3755 | 0.4242 | 98 | 103 | 163 | 1222 |
| green_onion | moving_average_7 | 0.8026 | 0.4037 | 0.4176 | 0.4105 | 109 | 161 | 152 | 1164 |
| green_onion | seasonal_naive_lag7 | 0.7163 | 0.2950 | 0.5211 | 0.3767 | 136 | 325 | 125 | 1000 |
| green_onion | moving_average_14 | 0.7295 | 0.2910 | 0.4483 | 0.3529 | 117 | 285 | 144 | 1040 |
| green_onion | sarima_weekly | 0.1740 | 0.1649 | 0.9885 | 0.2826 | 258 | 1307 | 3 | 18 |
| green_onion | naive_lag1 | 0.8354 | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 261 | 1325 |
| lettuce | lightgbm | 0.8221 | 0.6320 | 0.4540 | 0.5284 | 158 | 92 | 190 | 1145 |
| lettuce | xgboost | 0.8278 | 0.6667 | 0.4310 | 0.5236 | 150 | 75 | 198 | 1162 |
| lettuce | seasonal_naive_lag7 | 0.6744 | 0.3456 | 0.5402 | 0.4215 | 188 | 356 | 160 | 881 |
| lettuce | ridge | 0.8088 | 0.6286 | 0.3161 | 0.4207 | 110 | 65 | 238 | 1172 |
| lettuce | random_forest | 0.7868 | 0.5227 | 0.3305 | 0.4049 | 115 | 105 | 233 | 1132 |
| lettuce | moving_average_7 | 0.6877 | 0.3392 | 0.4454 | 0.3851 | 155 | 302 | 193 | 935 |
| lettuce | sarima_weekly | 0.2795 | 0.2277 | 0.9540 | 0.3677 | 332 | 1126 | 16 | 111 |
| lettuce | moving_average_14 | 0.6353 | 0.2917 | 0.4626 | 0.3578 | 161 | 391 | 187 | 846 |
| lettuce | naive_lag1 | 0.7804 | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 348 | 1237 |

## Notes

- Recall answers: among actual warning days, how many did the model catch?
- Precision answers: among predicted warning days, how many were truly warning days?
- F1 balances precision and recall.
- For rare events such as >=10% price jumps, accuracy can look high even when recall is poor; use F1 and recall for warning quality.
