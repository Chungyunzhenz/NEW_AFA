# 台灣農產品產銷量預測系統

Taiwan Agricultural Product Production & Sales Prediction System

## 系統架構

- **後端**: Python 3.10 + FastAPI + SQLAlchemy 2.0 + SQLite
- **前端**: React 19 (Vite) + D3.js + Recharts + TailwindCSS v4 + Zustand
- **預測模型**: Prophet + SARIMA + XGBoost + LightGBM 四模型集成預測
- **排程**: APScheduler (每日資料抓取、每週模型重訓)
- **資料庫**: SQLite (agriculture.db，約 2.2 GB)

## 支援農產品（22 種）

| 分類 | 作物 |
|------|------|
| 葉菜類 | 甘藍(Cabbage)、萵苣(Lettuce)、菠菜(Spinach)、小白菜(Bok Choy) |
| 花果菜類 | 花椰菜(Cauliflower)、苦瓜(Bitter Gourd)、番茄(Tomato)、辣椒(Chili Pepper) |
| 根莖類 | 蘿蔔(Radish)、蒜頭(Garlic)、蔥(Green Onion)、番薯(Sweet Potato)、筍(Bamboo Shoot) |
| 水果類 | 鳳梨(Pineapple)、芒果(Mango)、木瓜(Papaya)、芭樂(Guava)、香蕉(Banana)、柑橘(Citrus)、葡萄(Grape)、西瓜(Watermelon) |
| 穀物類 | 稻米(Rice) |

## 快速開始

### 1. 安裝後端依賴

```bash
pip install -r requirements.txt
```

### 2. 初始化資料庫

```bash
py scripts/seed_database.py
```

### 3. 啟動後端

```bash
cd backend
py -m uvicorn app.main:app --reload --port 8000
```

API 文件: http://localhost:8000/docs

### 4. 安裝前端依賴

```bash
cd frontend
npm install
```

### 5. 啟動前端

```bash
cd frontend
npm run dev
```

前端: http://localhost:5173

## 資料來源

1. **AMIS 批發市場交易資料** - 農糧署 API，每日自動更新（12,976,260+ 筆）
2. **農業生產統計** - 農糧署 MOA API + CSV 匯入（5,951+ 筆）
3. **中央氣象署觀測資料** - CWA Open Data API，每日自動更新（119,080+ 筆）
4. **颱風事件資料** - 中央氣象署颱風資料庫（145 筆）

## 回填歷史資料

```bash
# 回填交易資料
py scripts/backfill_trading.py --start 2023-01-01

# 回填氣象資料
py scripts/backfill_weather.py --api-key YOUR_CWA_KEY

# 回填產量資料（MOA API）
py scripts/backfill_production.py

# 匯入颱風事件
py scripts/seed_typhoon_data.py
```

## 新增農產品

在 `backend/app/data/crop_configs/` 新增 JSON 設定檔，重啟伺服器即可。目前已有 22 個設定檔。

## 主要功能

- **產銷預測** — 1/3/6 個月預測，含信賴區間
- **四模型集成** — Prophet + SARIMA + XGBoost + LightGBM，反向 MAPE 加權
- **互動式地圖** — 台灣 22 縣市交易分佈視覺化
- **颱風情境模擬** — 模擬不同強度颱風對價格的影響
- **資料品質監控** — 三大資料源健康度紅黃綠燈
- **產銷預警燈號** — 價格異常自動警示
- **CSV 上傳匯入** — 多步驟精靈介面，支援欄位映射
- **資料匯出** — 預測結果、歷史交易 CSV 匯出
- **AI 聊天助手** — 農產品 Q&A 即時問答

## API 端點

| 分類 | 路徑 | 說明 |
|------|------|------|
| 作物 | GET /api/v1/crops | 作物清單 |
| 作物 | GET /api/v1/crops/{crop_key} | 單一作物資訊 |
| 地區 | GET /api/v1/regions/counties | 縣市清單 |
| 地區 | GET /api/v1/regions/markets | 市場清單 |
| 地區 | GET /api/v1/regions/geojson | 地圖 GeoJSON |
| 交易 | GET /api/v1/trading/{crop}/daily | 每日交易資料 |
| 交易 | GET /api/v1/trading/{crop}/aggregated | 彙總資料 |
| 交易 | GET /api/v1/trading/{crop}/by-county | 按縣市分組 |
| 產量 | GET /api/v1/production/{crop}/by-county | 按縣市產量 |
| 產量 | GET /api/v1/production/{crop}/timeseries | 產量時間序列 |
| 預測 | GET /api/v1/predictions/{crop}/forecast | 預測結果 |
| 預測 | GET /api/v1/predictions/{crop}/by-county | 縣市預測 |
| 預測 | GET /api/v1/predictions/{crop}/model-info | 模型資訊 |
| 預測 | GET /api/v1/predictions/{crop}/summary | 預測摘要文字 |
| 預測 | GET /api/v1/predictions/{crop}/feature-importance | 特徵重要性 |
| 預測 | POST /api/v1/predictions/{crop}/retrain | 觸發重訓 |
| 颱風 | GET /api/v1/typhoon/events | 颱風事件列表 |
| 颱風 | POST /api/v1/typhoon/simulate | 情境模擬 |
| 品質 | GET /api/v1/data-quality/overview | 資料健康度 |
| 匯出 | GET /api/v1/export/predictions/{crop} | 匯出預測 CSV |
| 匯出 | GET /api/v1/export/historical/{crop} | 匯出歷史 CSV |
| 同步 | POST /api/v1/sync/fetch-latest | 抓取最新資料 |
| 上傳 | POST /api/v1/upload/file | 上傳 CSV 檔案 |
| 警示 | GET /api/v1/alerts/traffic-light/{crop} | 紅綠燈警示 |
