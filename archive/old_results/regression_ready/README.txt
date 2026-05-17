=== 回歸資料說明 (regression_ready) ===

資料來源: AFA-other/<crop>_交易資料_with_targets.csv
整理腳本: prepare_regression_data.py

【格式】
  - 純數值矩陣，類別變數已預先編碼成 0/1 啞變數
  - 連續變數: 上價/中價/下價/平均價/交易量(公斤)/ln_volume
  - 啞變數: variety_* (品名), market_* (市場)
  - y: target_5d (最後一欄，未來 5 日均價)
  - 交易日期: 僅供對照，不要放進回歸

【切分】
  - 70/30 依日期時序切（前 70% 訓練、後 30% 測試）
  - 用 unique 日期切以避免同日資料被切兩半

【各作物統計】
  cabbage      (甘藍): train=118000, test= 60209, cut=2021-10-06, variety_dummy=15, market_dummy=14, 總欄位=37
  bok_choy     (小白菜): train= 76492, test= 42990, cut=2021-10-11, variety_dummy=4, market_dummy=14, 總欄位=26
  cauliflower  (花椰菜): train= 49531, test= 20274, cut=2021-10-06, variety_dummy=3, market_dummy=14, 總欄位=25
  green_onion  (青蔥): train= 95322, test= 42871, cut=2021-08-28, variety_dummy=6, market_dummy=14, 總欄位=28
  lettuce      (萵苣): train=178348, test= 89799, cut=2021-08-29, variety_dummy=17, market_dummy=14, 總欄位=39

【使用注意】
  1. 詳細的啞變數對照請看各作物的 <crop>_codebook.txt
  2. 上價/中價/下價/平均價之間相關性很高，做 OLS 時建議：
     - 只留 平均價 一個，或
     - 改用 Ridge / Lasso，或
     - 跑 VIF 檢驗篩選變數
  3. 同時放入 交易量(公斤) 與 ln_volume 會有完全共線性，
     請挑一個（建議用 ln_volume）
  4. 啞變數有「參照組」(被省略的那個類別)，係數要相對於它解讀
  5. CSV 為 UTF-8 BOM 編碼，Excel 直接開不會亂碼
