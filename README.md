# GL860 & COAI 天氣資料 MySQL 系統

## 📋 系統說明

自動將 GL860 和 COAI Excel 資料導入 MySQL 資料庫，採用智能採樣技術大幅減少資料量，同時保持統計精度。

### 資料來源

1. **GL860 資料**：高頻率氣象資料
   - Channel 1: 溫度 (degC)
   - Channel 2: 濕度 (%)
   - Channel 3: 照度 LUX (lux)
   - Channel 4: UV USA/Apogee (W/m²)
   - Channel 5: UV Ref (W/m²)
   - 原始頻率：每分鐘一筆
   - 採樣輸出：每30分鐘一筆
   - 檔案位置：`GL860/` 資料夾

2. **COAI 資料**：每日氣象觀測
   - 氣溫、濕度、風速、風向、降水量
   - 檔案位置：`COAI/` 資料夾

## 🎯 核心特色

### GL860 智能採樣系統
- ✅ **30分鐘採樣**：每30分鐘擷取一筆數據，大幅減少資料量
- ✅ **統計精度100%**：平均、最大、最小值使用**每分鐘的全部原始資料**計算
- ✅ **5通道完整統計**：所有Channel都計算每日平均值
- ✅ **內建每日統計**：自動計算並附加在每天第一筆記錄
- ✅ **即時驗證**：導入後立即顯示統計摘要

## 📁 主要程式

### 1. gl860_to_mysql.py ⭐ 主要程式
導入 GL860 資料（30分鐘採樣+5通道統計）
```bash
python gl860_to_mysql.py
```

**功能：**
- 讀取所有 GL860 Excel 檔案
- 自動30分鐘採樣
- 計算每日統計（使用全部每分鐘原始資料）
- 驗證導入結果

### 2. coai_to_mysql.py
導入 COAI 資料並整合到 GL860 表
```bash
python coai_to_mysql.py
```

### 3. deploy_all_data.py
一鍵部署 GL860 + COAI 資料
```bash
python deploy_all_data.py
```

### 4. 輔助程式
- **clear_data.py** - 清空 GL860 資料表
- **verify_import.py** - 驗證資料完整性
- **update_database(rebuild).py** - 完整重建資料庫
- **add_new_data.py** - 增量導入新資料

## 🚀 快速開始

### 初次設定

1. **安裝套件**
```bash
pip install -r requirements.txt
```

2. **設定資料庫**（編輯 config.ini）
```ini
[mysql]
host = localhost
user = root
password = 你的密碼
database = weather_data
```

### 使用方式

**完整重建資料庫**
```bash
python update_database(rebuild).py
```
會執行：清空 → 導入 → 驗證

**只導入 GL860**
```bash
python gl860_to_mysql.py
```

**同時部署 GL860 + COAI**
```bash
python deploy_all_data.py
```

**增量導入新月份**
```bash
python add_new_data.py
```

## 📊 資料庫結構

### gl860_weather_data 表

| 欄位 | 說明 | 備註 |
|------|------|------|
| record_time | 記錄時間 | 每30分鐘一筆 (DATETIME) |
| **channel1_temperature** | 溫度 (degC) | 採樣點數值 |
| **channel2_humidity** | 濕度 (%) | 採樣點數值 |
| **channel3_lux** | 照度 (lux) | 採樣點數值 |
| **channel4_uv_usa** | UV USA (W/m²) | 採樣點數值 |
| **channel5_uv_ref** | UV Ref (W/m²) | 採樣點數值 |
| **record_date** | 當天日期 | 只有年/月/日 (DATE)⭐ |
| **daily_avg_temperature** | 每日平均溫度 | 用全部分鐘資料計算⭐ |
| **daily_avg_humidity** | 每日平均濕度 | 用全部分鐘資料計算⭐ |
| **daily_avg_lux** | 每日平均照度 | 用全部分鐘資料計算⭐ |
| **daily_lux_dosage** | 每日照度劑量 | lux·hour（積分計算）⭐🆕 |
| **daily_avg_uv_usa** | 每日平均UV USA | 用全部分鐘資料計算⭐ |
| **daily_uv_usa_dosage** | 每日UV USA劑量 | W·h/m²（積分計算）⭐🆕 |
| **daily_avg_uv_ref** | 每日平均UV Ref | 用全部分鐘資料計算⭐ |
| **daily_uv_ref_dosage** | 每日UV Ref劑量 | W·h/m²（積分計算）⭐🆕 |
| **daily_max_temperature** | 每日最高溫度 | 用全部分鐘資料計算⭐ |
| **daily_min_temperature** | 每日最低溫度 | 用全部分鐘資料計算⭐ |
| **daily_temperature_delta** | 每日溫差 | 用全部分鐘資料計算⭐ |
| **daily_humidity_delta** | 每日濕差 | 用全部分鐘資料計算⭐ |
| **daily_record_count** | 原始記錄數 | 顯示計算統計時的分鐘資料筆數 |
| coai_temperature | COAI 氣溫 | 每日第一筆 |
| coai_humidity | COAI 濕度 | 每日第一筆 |
| coai_rainfall | COAI 降雨 | "1"=有降雨, "/"=無降雨 🆕 |
| coai_rainfall_raw | COAI 原始降雨量 | mm（原始數值）🆕 |

⚠️ **`record_date`、每日統計和 COAI 欄位只在每天第一筆記錄中有值**

### record_date 欄位說明

`record_date` 是新增的日期欄位，格式為 `DATE`（例如：`2025-07-01`），**只包含年/月/日，不包含時間**。

**設計目的：**
- 方便快速查詢每日統計資料
- 與其他一天只有一筆的統計欄位放在一起
- 簡化日期範圍查詢

**使用範例：**
```sql
-- 查詢有 record_date 的記錄（即每天第一筆）
SELECT record_date, daily_avg_temperature, daily_avg_lux, daily_avg_uv_usa
FROM gl860_weather_data
WHERE record_date IS NOT NULL
ORDER BY record_date DESC;

-- 查詢特定日期範圍
SELECT record_date, daily_avg_temperature, daily_avg_uv_usa, daily_avg_uv_ref, coai_temperature
FROM gl860_weather_data
WHERE record_date BETWEEN '2025-11-01' AND '2025-11-30';
```

## 📈 常用查詢

### 查看每日統計（所有5個Channel）
```sql
SELECT 
    record_date as 日期,
    daily_avg_temperature as 平均溫度,
    daily_avg_humidity as 平均濕度,
    daily_avg_lux as 平均照度,
    daily_avg_uv_usa as 平均UV_USA,
    daily_avg_uv_ref as 平均UV_Ref,
    daily_record_count as 原始筆數,
    coai_rainfall as 降雨量
FROM gl860_weather_data
WHERE record_date IS NOT NULL
ORDER BY record_date DESC
LIMIT 10;
```

### 查看某日的30分鐘採樣點
```sql
SELECT 
    record_time,
    channel1_temperature as 溫度,
    channel2_humidity as 濕度,
    channel3_lux as 照度,
    channel4_uv_usa as UV_USA,
    channel5_uv_ref as UV_Ref
FROM gl860_weather_data
WHERE DATE(record_time) = '2025-11-30'
ORDER BY record_time;
```

### 溫差最大的日子
```sql
SELECT 
    record_date as 日期,
    daily_max_temperature as 最高溫,
    daily_min_temperature as 最低溫,
    daily_temperature_delta as 溫差
FROM gl860_weather_data
WHERE record_date IS NOT NULL
ORDER BY daily_temperature_delta DESC
LIMIT 10;
```

### 比較 UV USA vs UV Ref
```sql
SELECT 
    record_date as 日期,
    daily_avg_uv_usa as 平均UV_USA,
    daily_avg_uv_ref as 平均UV_Ref,
    daily_avg_uv_usa - daily_avg_uv_ref as UV差異
FROM gl860_weather_data
WHERE record_date IS NOT NULL
ORDER BY record_date;
```

## 💡 資料特性說明

### 採樣策略
- **原始資料**：每分鐘一筆
- **儲存資料**：每30分鐘採樣一筆
- **統計資料**：使用每分鐘的全部原始資料計算
- **資料減少**：約 96.7%

### 統計精度
- ✅ 所有統計數據使用**每分鐘的全部原始資料**計算
- ✅ `daily_record_count` 顯示實際使用多少筆分鐘級資料
- ✅ 例如：1440 表示該天有完整的每分鐘資料

### 5通道統計
所有5個Channel都計算以下統計：
- **daily_avg_***: 每日平均值
- **daily_max_***: 每日最大值
- **daily_min_***: 每日最小值

### 每日劑量計算 (Dosage) 🆕
使用**梯形積分法**計算每日累積劑量：

**計算公式：**
```
Dosage = ∫ value(t) dt ≈ Σ[(v_i + v_{i+1}) / 2 × Δt]
```

**單位說明：**
- **daily_lux_dosage**: lux·hour（照度累積）
- **daily_uv_usa_dosage**: W·h/m²（UV能量累積）
- **daily_uv_ref_dosage**: W·h/m²（UV能量累積）

**應用場景：**
- 材料曝曬總量評估
- 累積紫外線劑量分析
- 光照能量累計計算

### COAI 降雨欄位說明 🆕
- **coai_rainfall**: 顯示是否有降雨
  - `"1"` = 當天有降雨（原始值 > 0）
  - `NULL`（空白）= 當天無降雨（原始值 = 0 或 NULL）
- **coai_rainfall_raw**: 保存原始降雨量數值（mm）

### 資料量比較

| 項目 | 原始筆數 | 採樣後筆數 | 減少比例 |
|------|----------|-----------|----------|
| 每月 | ~43,200 | ~1,440 | 96.7% |
| 統計精度 | 100% | 100% | 不變 |
| 查詢速度 | 慢 | 快 30倍 | - |

## ⚠️ 注意事項

1. **檔案命名**
   - GL860：`GL860 RAWDATA_YYMM.xlsx`
   - COAI：`C0AI10-YYYY-MM.xlsx`

2. **記憶體需求**
   - 需要處理整月資料到記憶體中計算統計
   - 一般電腦 8GB RAM 足夠

3. **Channel對應**
   - Channel 1: 溫度 (degC)
   - Channel 2: 濕度 (%)
   - Channel 3: 照度 LUX (lux)
   - Channel 4: UV USA/Apogee (W/m²)
   - Channel 5: UV Ref (W/m²)

## 🔧 疑難排解

### 看不到更新後的資料
1. 在 MySQL Workbench 中按 F5 重新整理
2. 或右鍵資料庫 → Refresh All

### 記憶體不足
- 分批處理（一次處理一個月）
- 或增加系統記憶體

### 需要每分鐘的完整資料
- 保留 Excel 原始檔案
- 系統主要用於趨勢分析和統計

## 📞 系統需求

- Python 3.7+
- MySQL 5.7+
- 8GB+ RAM（推薦）
- pandas, mysql-connector-python, openpyxl

---

**版本**: 3.0 (5通道版)  
**更新日期**: 2025-12-15  
**特色**: 5通道完整統計 + 30分鐘採樣 + UV USA/Ref 雙通道
