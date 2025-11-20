# GL860 天氣資料 MySQL 導入系統

## 📋 系統說明

這個系統可以自動將 GL860 資料夾中的 Excel 檔案導入到 MySQL 資料庫中。

## 📁 檔案說明

### 主要程式

1. **update_database.py** ⭐ **推薦使用**
   - 一鍵更新資料庫的自動化腳本
   - 會自動執行清除、導入、驗證三個步驟
   - 適合日常使用

2. **gl860_to_mysql.py**
   - 讀取 GL860 資料夾中的所有 Excel 檔案
   - 將資料導入到 MySQL 資料表
   - 智能識別不同檔案的欄位結構

3. **clear_data.py**
   - 清空資料表中的所有資料
   - 保留資料表結構

4. **verify_import.py**
   - 驗證資料導入結果
   - 顯示統計資訊

### 設定檔

- **config.ini** - MySQL 資料庫連線設定
- **requirements.txt** - Python 套件需求清單

## 🚀 使用方式

### 初次設定

1. 安裝 Python 套件：
```bash
pip install -r requirements.txt
```

2. 設定資料庫連線（編輯 config.ini）：
```ini
[mysql]
host = localhost
user = root
password = 你的密碼
database = weather_data
```

### 更新資料庫資料

**方法一：完全更新（清空後重新導入）**
```bash
python update_database.py
```
這個腳本會：
1. 詢問確認
2. 清除舊資料
3. 導入新資料
4. 驗證結果

⚠️ **注意：此方法會清空所有舊資料**

**方法二：增量導入（只加入新資料）⭐ 推薦用於日常更新**
```bash
python add_new_data.py
```
這個腳本會：
1. 自動檢測哪些檔案已經導入過
2. 讓您選擇要導入哪些檔案
3. 只導入新的記錄，跳過重複的資料
4. 驗證結果

✅ **優點：不會清空舊資料，適合定期加入新月份資料**

**方法二：手動執行步驟**
```bash
# 步驟 1: 清除舊資料
python clear_data.py

# 步驟 2: 導入新資料
python gl860_to_mysql.py

# 步驟 3: 驗證結果（可選）
python verify_import.py
```

## 💡 常見使用情境

### 情境 1：新的月份資料（如 2511）到了 ⭐ 最常用
```bash
python add_new_data.py
```
選擇「只導入新檔案」，系統會自動識別並只導入新月份的資料。

**完成後手動更新統計：**
```bash
python create_statistics.py
```

### 情境 2：想重新導入某個月份的資料（如修正了 2510）
```bash
python add_new_data.py
```
選擇「選擇特定檔案導入」，然後輸入該檔案的編號。系統會詢問是否要重新導入。

**完成後手動更新統計：**
```bash
python create_statistics.py
```

### 情境 3：第一次建立資料庫或想完全重建 ⭐ 一鍵完成
```bash
python update_database.py
```
此方法會：
- 清空所有舊資料
- 重新導入所有 GL860 檔案
- 自動更新統計資料表和視圖

✅ **不需要再執行 create_statistics.py**

### 情境 4：只想查看目前資料庫的狀態
```bash
python verify_import.py
```

## 📊 MySQL Workbench 中查看資料

更新資料後，在 MySQL Workbench 中：

1. **重新執行查詢**：
   - 按 F5 鍵
   - 或點擊 ⚡ 執行按鈕

2. **基本查詢範例**：
```sql
-- 查看所有資料
SELECT * FROM gl860_weather_data;

-- 查看最新 10 筆資料
SELECT * FROM gl860_weather_data 
ORDER BY record_time DESC 
LIMIT 10;

-- 查看某月份的資料
SELECT * FROM gl860_weather_data 
WHERE year = 2025 AND month = 10;

-- 查看有設備溫度的資料
SELECT * FROM gl860_weather_data 
WHERE channel_5_device_temp IS NOT NULL;
```

## 📈 資料庫結構

資料表：`gl860_weather_data`

| 欄位名稱 | 類型 | 說明 |
|---------|------|------|
| id | INT | 主鍵（自動遞增）|
| year | INT | 年份 |
| month | INT | 月份 |
| record_time | DATETIME | 記錄時間 |
| channel_1_temp | DECIMAL(5,2) | CH1: 溫度 (°C) |
| channel_2_humidity | DECIMAL(5,2) | CH2: 濕度 (%) |
| channel_3_uv | DECIMAL(10,2) | CH3: UV (W/m²) |
| channel_4_lux | DECIMAL(10,2) | CH4: Lux (照度) |
| channel_5_device_temp | DECIMAL(5,2) | CH5: 設備溫度 (°C) |

## ⚠️ 注意事項

1. **每次執行 update_database.py 會清空並重新導入所有資料**
   - 不是累加，而是完全更新
   - 確保 GL860 資料夾中的檔案是最新的

2. **檔案命名格式**
   - 檔案名需包含年月資訊：如 `GL860 RAWDATA_2507.xlsx`
   - 系統會自動從檔名擷取年份和月份

3. **資料完整性**
   - 某些月份可能沒有所有通道的資料（例如 CH3、CH5）
   - 缺失的資料會以 NULL 儲存

## 🔧 疑難排解

### 問題：連線失敗
- 檢查 config.ini 中的資料庫設定
- 確認 MySQL 服務是否啟動
- 檢查帳號密碼是否正確

### 問題：找不到檔案
- 確認 GL860 資料夾與程式在同一目錄下
- 檢查檔案名稱格式是否正確

### 問題：資料重複
- 執行 `python clear_data.py` 清除舊資料
- 再執行 `python gl860_to_mysql.py` 重新導入

## 📊 進階功能：統計資料表和視圖

### create_statistics.py - 建立統計資料

執行此腳本可以：
1. 建立每日統計資料表 (`gl860_daily_statistics`)
2. 建立方便查詢的視圖 (`v_gl860_complete_data`)
3. 自動填充統計資料
4. 驗證 Channel 5 資料完整性

```bash
python create_statistics.py
```

### 統計資料表結構

**gl860_daily_statistics** - 每日統計資料表

| 欄位名稱 | 類型 | 說明 |
|---------|------|------|
| id | INT | 主鍵 |
| date | DATE | 日期 |
| year | INT | 年份 |
| month | INT | 月份 |
| day | INT | 日 |
| avg_temperature | DECIMAL(5,2) | 平均溫度 |
| avg_humidity | DECIMAL(5,2) | 平均濕度 |
| avg_device_temp | DECIMAL(5,2) | 平均設備溫度 |
| max_temperature | DECIMAL(5,2) | 最高溫度 |
| max_humidity | DECIMAL(5,2) | 最高濕度 |
| min_temperature | DECIMAL(5,2) | 最低溫度 |
| min_humidity | DECIMAL(5,2) | 最低濕度 |
| temperature_delta | DECIMAL(5,2) | 溫度日較差 |
| humidity_delta | DECIMAL(5,2) | 濕度日較差 |
| record_count | INT | 記錄筆數 |

### 視圖說明

**v_gl860_complete_data** - 完整資料視圖

此視圖簡化了欄位名稱，方便查詢：

```sql
-- 使用視圖查詢資料
SELECT * FROM v_gl860_complete_data 
WHERE year = 2025 AND month = 10
ORDER BY record_time DESC
LIMIT 100;
```

視圖欄位：
- `temperature` - 溫度 (原 channel1_temperature)
- `humidity` - 濕度 (原 channel2_humidity)
- `uv` - UV值 (原 channel3_uv)
- `lux` - 照度 (原 channel4_lux)
- `device_temperature` - 設備溫度 (原 channel5_device_temp)

### 實用查詢範例

```sql
-- 查詢每日統計
SELECT * FROM gl860_daily_statistics 
WHERE year = 2025 AND month = 10
ORDER BY date DESC;

-- 查詢某月的平均溫度趨勢
SELECT date, avg_temperature, max_temperature, min_temperature
FROM gl860_daily_statistics
WHERE year = 2025 AND month = 10
ORDER BY date;

-- 使用簡化視圖查詢
SELECT date, temperature, humidity, device_temperature
FROM v_gl860_complete_data
WHERE year = 2025 AND month = 9
ORDER BY record_time;
```

### Channel 5 數據說明

執行 `create_statistics.py` 時會顯示各月份的 Channel 5 (設備溫度) 數據完整度：

- 2025年7月：67.1% 有 CH5 數據
- 2025年8月：99.3% 有 CH5 數據  
- 2025年9月：100.0% 有 CH5 數據
- 2025年10月：0.0% 無 CH5 數據

## 📞 技術支援

如有問題，請檢查：
1. Python 版本（建議 3.7+）
2. MySQL 版本（建議 5.7+）
3. 所有套件是否正確安裝
