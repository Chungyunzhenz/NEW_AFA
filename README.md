# 台灣農產品產銷量預測系統

Taiwan Agricultural Product Production & Sales Prediction System

## 系統架構

- **後端**: Python + FastAPI + SQLAlchemy + SQLite
- **前端**: React 18 (Vite) + D3.js + Recharts + TailwindCSS v4
- **預測模型**: Prophet + SARIMA + XGBoost 集成預測
- **排程**: APScheduler (每日資料抓取、每週模型重訓)

## 支援農產品

- 鳳梨 (Pineapple) - 旺季 3-7 月
- 甘藍 (Cabbage) - 旺季 11-3 月

## 快速開始

### 1. 安裝後端依賴

```bash
cd backend
pip install -r requirements.txt
```

### 2. 初始化資料庫

```bash
# 從專案根目錄執行
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

1. **AMIS 批發市場交易資料** - 每日更新
2. **農業生產統計** - 年度 CSV 匯入
3. **中央氣象署觀測資料** - 每日更新 (需 API Key)

## 回填歷史資料

```bash
# 回填交易資料 (預設 3 年)
py scripts/backfill_trading.py --start 2023-01-01

# 回填氣象資料
py scripts/backfill_weather.py --api-key YOUR_CWA_KEY

# 匯入生產統計 CSV
py scripts/load_production_csv.py path/to/data.csv pineapple
```

## 新增農產品

在 `backend/app/data/crop_configs/` 新增 JSON 設定檔，重啟伺服器即可。

## API 端點

| 路徑 | 說明 |
|------|------|
| GET /api/v1/crops | 農產品列表 |
| GET /api/v1/regions/counties | 縣市列表 |
| GET /api/v1/regions/geojson | 台灣地圖 TopoJSON |
| GET /api/v1/trading/{crop}/daily | 每日交易資料 |
| GET /api/v1/trading/{crop}/by-county | 縣市彙總 (地圖用) |
| GET /api/v1/predictions/{crop}/forecast | 預測結果 |
| GET /api/v1/predictions/{crop}/by-county | 縣市預測 (地圖用) |
