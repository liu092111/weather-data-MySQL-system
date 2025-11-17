# 統一氣象數據導入系統

這是一個支援多種氣象數據格式的統一導入系統，能夠自動識別並處理 CIA（氣象局日統計）和 GL860（原始測量數據）兩種 Excel 格式，並部署到 MySQL 資料庫中。

## 🎯 系統特色

- ✅ **自動格式識別**：自動偵測 CIA-XXX 和 GL860XXX 兩種檔案格式
- ✅ **清楚的檔案讀取顯示**：提供 `read_file('檔案名稱')` 格式的明確顯示
- ✅ **統一資料結構**：將不同格式的數據整合到標準化的資料庫架構
- ✅ **防重複導入**：使用檔案 hash 防止重複導入相同檔案
- ✅ **完整統計功能**：自動計算每日平均、最高、最低溫濕度
- ✅ **統一查詢視圖**：提供包含所有要求資訊的整合檢視

## 📋 支援的資訊欄位

系統整合後可查詢的完整資訊包括：

- **基本資訊**：year, month, time
- **Channel 數據**：channel 1 temperature, channel 2 humidity, channel 3 lux, channel 4 UV, channel 5 device degree
- **每日統計**：每日平均溫度濕度、每日最高溫度濕度、每日最低溫度濕度
- **CIA 氣象局數據**：CIA的溫度、CIA濕度、CIA 降雨量

## 🚀 快速開始

### 1. 安裝依賴

```bash
pip install -r requirements.txt
```

`requirements.txt` 內容：
```
pandas>=1.5.0
mysql-connector-python>=8.0.0
openpyxl>=3.0.0
```

### 2. 設置資料庫

在 MySQL Workbench 中執行以下腳本建立資料庫：

```sql
-- 1. 建立基本資料庫架構
SOURCE weather_database_schema.sql;

-- 2. 建立統一查詢視圖
SOURCE unified_weather_views.sql;
```

### 3. 基本使用方法

#### 方法一：Python API 使用

```python
from unified_weather_importer import read_file, read_directory, get_unified_view

# 導入單一檔案 - CIA 格式
read_file('C0AI10-2025-07.xlsx')

# 導入單一檔案 - GL860 格式  
read_file('GL860 RAWDATA_2507.xlsx')

# 批量導入目錄中的所有 Excel 檔案
read_directory('./', pattern='*.xlsx')

# 取得統一的資料檢視
df = get_unified_view('2025-07-01', '2025-10-31')
print(df.head())
```

#### 方法二：命令列使用

```bash
# 導入單一檔案
python unified_weather_importer.py --file "C0AI10-2025-07.xlsx"

# 批量導入目錄
python unified_weather_importer.py --directory "./" --pattern "*.xlsx"

# 指定資料庫連線參數
python unified_weather_importer.py --file "GL860 RAWDATA_2507.xlsx" \
  --host localhost --database weather_data --username root --password ""
```

## 📁 支援的檔案格式

### CIA 格式（氣象局日統計）
- **檔名特徵**：`C0AI10-YYYY-MM.xlsx` 或包含 `CIA` 關鍵字
- **內容特徵**：包含 `ObsTime`、`Temperature`、`RH`、`Precp` 等欄位
- **數據類型**：日統計數據，包含溫度、濕度、降水量等

### GL860 格式（原始測量數據）
- **檔名特徵**：`GL860 RAWDATA_YYMM.xlsx` 或包含 `GL860` 關鍵字
- **內容特徵**：包含 `NO.`、`Time`、`degC`、`%` 等欄位
- **數據類型**：逐時原始測量數據，包含 5 個 channel 的數據

## 🔍 使用範例

### 完整的使用流程

```python
#!/usr/bin/env python3
from unified_weather_importer import read_file, get_unified_view
import pandas as pd

# 1. 導入不同格式的檔案
print("=== 導入 CIA 氣象局數據 ===")
read_file('C0AI10-2025-07.xlsx')
read_file('C0AI10-2025-08.xlsx')
read_file('C0AI10-2025-09.xlsx')
read_file('C0AI10-2025-10.xlsx')

print("\n=== 導入 GL860 原始數據 ===")
read_file('GL860 RAWDATA_2507.xlsx')
read_file('GL860 RAWDATA_2508.xlsx')
read_file('GL860 RAWDATA_2509.xlsx')
read_file('GL860 RAWDATA_2510.xlsx')

# 2. 查詢統一的資料檢視
print("\n=== 查詢統一數據 ===")
df = get_unified_view('2025-07-01', '2025-10-31')

# 3. 查看數據摘要
print(f"總共 {len(df)} 筆記錄")
print(f"日期範圍：{df['time'].min()} ~ {df['time'].max()}")
print("\n欄位列表：")
for col in df.columns:
    print(f"  - {col}")

# 4. 保存到 Excel 用於分析
df.to_excel('unified_weather_data.xlsx', index=False)
print("\n✅ 數據已保存到 unified_weather_data.xlsx")
```

### 運行結果示例

```
============================================================
🔄 read_file('C0AI10-2025-07.xlsx')
============================================================
🔍 偵測檔案格式: C0AI10-2025-07.xlsx
📋 偵測到 CIA 氣象局日統計格式
📋 解析 CIA 氣象局日統計數據...
✅ CIA 格式解析完成，共 31 筆日統計數據
📋 處理 CIA 氣象局日統計數據...
📈 已插入/更新日統計數據: 31 筆
✅ CIA 數據導入完成: 31 筆日統計數據
🎉 檔案 C0AI10-2025-07.xlsx 導入成功！
✅ 導入完成: 31 筆記錄
📅 日期範圍: 2025-07-01 ~ 2025-07-31
============================================================

============================================================
🔄 read_file('GL860 RAWDATA_2507.xlsx')
============================================================
🔍 偵測檔案格式: GL860 RAWDATA_2507.xlsx
📊 偵測到 GL860 原始測量數據格式
📊 解析 GL860 原始測量數據...
✅ GL860 格式解析完成，原始數據 4464 筆，日統計 31 筆
📊 處理 GL860 原始測量數據...
📊 已插入原始數據: 4464 筆
📈 已插入/更新日統計數據: 31 筆
✅ GL860 數據導入完成: 4464 筆原始數據 + 31 筆日統計數據
🎉 檔案 GL860 RAWDATA_2507.xlsx 導入成功！
✅ 導入完成: 4495 筆記錄
📅 日期範圍: 2025-07-01 ~ 2025-07-31
============================================================
```

## 🗄️ 資料庫查詢

### 使用 SQL 查詢統一檢視

```sql
-- 1. 查看所有統一數據（限制 100 筆）
SELECT * FROM v_weather_main LIMIT 100;

-- 2. 查看特定日期範圍的數據
SELECT * FROM v_weather_main 
WHERE DATE(time) BETWEEN '2025-07-01' AND '2025-10-31'
ORDER BY time;

-- 3. 查看日統計摘要
SELECT * FROM v_daily_summary 
WHERE year = 2025 AND month = 7
ORDER BY date;

-- 4. 查看月統計摘要
SELECT * FROM v_monthly_summary 
WHERE year = 2025
ORDER BY month;

-- 5. 使用存儲程序查詢
CALL GetUnifiedWeatherData('2025-07-01', '2025-10-31', 1);
CALL GetDailySummary('2025-07-01', '2025-10-31');

-- 6. 檢查數據品質
SELECT * FROM v_data_quality_check 
WHERE date >= '2025-07-01'
ORDER BY date DESC;
```

### Python 中的資料庫查詢

```python
import mysql.connector
import pandas as pd

# 建立連線
connection = mysql.connector.connect(
    host='localhost',
    database='weather_data',
    user='root',
    password=''
)

# 查詢統一檢視
query = """
SELECT year, month, time,
       channel_1_temperature, channel_2_humidity,
       daily_avg_temperature, daily_avg_humidity,
       cia_precipitation
FROM v_weather_main
WHERE DATE(time) BETWEEN %s AND %s
ORDER BY time
"""

df = pd.read_sql(query, connection, params=['2025-07-01', '2025-10-31'])
print(df.head())

connection.close()
```

## 📊 資料庫架構

### 主要資料表

1. **`weather_raw_data`** - 原始測量數據
   - 存儲 GL860 的逐時測量數據
   - 包含 5 個 channel 的數據

2. **`weather_daily_stats`** - 日統計數據  
   - 存儲每日統計結果和 CIA 數據
   - 包含平均、最高、最低溫濕度及降水量

3. **`import_logs`** - 導入記錄
   - 追蹤檔案導入狀況，防止重複導入

### 主要檢視

1. **`v_weather_main`** - 統一主檢視
   - 包含所有要求的欄位資訊

2. **`v_daily_summary`** - 日統計摘要
   - 按日期匯總的統計資訊

3. **`v_monthly_summary`** - 月統計摘要
   - 按月份匯總的統計資訊

## ⚙️ 設定參數

### 資料庫連線設定

```python
# 預設設定
db_config = {
    'host': 'localhost',
    'port': 3306,
    'database': 'weather_data',
    'username': 'root',
    'password': ''
}

# 自定義設定
read_file('data.xlsx', host='192.168.1.100', password='mypassword')
```

### 設備 ID 設定

```python
# 預設設備 ID = 1
read_file('data.xlsx')

# 指定設備 ID
read_file('data.xlsx', device_id=2)
```

## 🐛 故障排除

### 常見問題

1. **無法連接到資料庫**
   ```
   ❌ 無法連線到資料庫: Access denied for user 'root'@'localhost'
   ```
   - 檢查 MySQL 服務是否運行
   - 確認使用者名稱和密碼正確
   - 檢查資料庫權限設定

2. **檔案格式無法識別**
   ```
   ⚠️ 內容偵測失敗: Excel file format cannot be determined
   ```
   - 確認檔案不是損毀的
   - 檢查檔案是否為有效的 Excel 格式
   - 嘗試手動指定格式

3. **找不到表頭行**
   ```
   ❌ GL860 格式解析失敗: 在工作表 Modify 中找不到表頭行
   ```
   - 檢查 Excel 檔案的工作表結構
   - 確認包含 "NO." 和 "Time" 欄位

### 日誌檢查

系統會產生詳細的日誌檔案：
- `unified_weather_import.log` - 主要日誌檔案
- 包含完整的導入過程和錯誤資訊

### 手動檢查數據

```sql
-- 檢查導入記錄
SELECT * FROM import_logs ORDER BY import_time DESC LIMIT 10;

-- 檢查數據統計
SELECT 
    COUNT(*) as total_records,
    MIN(measurement_time) as earliest_date,
    MAX(measurement_time) as latest_date,
    COUNT(DISTINCT DATE(measurement_time)) as total_days
FROM weather_raw_data;

-- 檢查數據品質
SELECT * FROM v_data_quality_check 
WHERE data_status != '數據完整'
ORDER BY date DESC;
```

## 📞 技術支援

如遇到技術問題，請提供以下資訊：
1. 錯誤訊息的完整內容
2. `unified_weather_import.log` 日誌檔案
3. Excel 檔案的檔名和大概結構
4. MySQL 版本和連線設定

## 📄 授權

本專案採用 MIT 授權條款。

---

🎉 **恭喜！你現在可以開始使用統一氣象數據導入系統了！**

記住關鍵的使用方式：
```python
from unified_weather_importer import read_file

# 就是這麼簡單！
read_file('你的檔案名稱.xlsx')
