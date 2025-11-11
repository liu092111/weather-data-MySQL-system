# GL860氣象數據MySQL管理系統

這是一個完整的GL860氣象記錄器數據管理解決方案，支持Excel檔案自動導入MySQL資料庫，並提供定時維護、備份和報告功能。

## 🎯 功能特色

- ✅ **Excel自動導入**: 支持GL860產生的Excel檔案自動解析和導入
- ✅ **數據完整性**: 防重複導入，hash校驗確保數據完整
- ✅ **自動化維護**: 定時導入、備份、清理和報告
- ✅ **多工作表支持**: 自動識別溫度、濕度、降水量等數據
- ✅ **統計分析**: 自動生成日、月統計數據
- ✅ **郵件通知**: 支持導入結果和異常通知
- ✅ **日誌記錄**: 完整的操作日誌和錯誤追蹤

## 📋 系統需求

### 軟體需求
- **Python 3.7+**
- **MySQL 5.7+ 或 MySQL 8.0+**
- **MySQL Workbench** (推薦用於資料庫管理)

### Python套件依賴
```
pandas>=1.3.0
mysql-connector-python>=8.0.26
schedule>=1.1.0
openpyxl>=3.0.7
```

## 🚀 快速開始

### 1. 環境準備

```bash
# 1. 克隆或下載專案檔案
git clone <repository_url>
cd weather_mysql_system

# 2. 安裝Python依賴
pip install -r requirements.txt

# 3. 確保MySQL服務運行中
# Windows: 檢查服務管理員
# Linux/Mac: sudo systemctl status mysql
```

### 2. 資料庫設置

```bash
# 1. 使用MySQL Workbench或命令行連接MySQL
mysql -u root -p

# 2. 執行資料庫初始化腳本
mysql -u root -p < weather_database_schema.sql
```

### 3. 配置系統

第一次運行時會自動生成配置檔案 `config.ini`：

```bash
python automated_maintenance.py
```

編輯 `config.ini` 設置您的環境：

```ini
[database]
host = localhost
port = 3306
database = weather_data
username = root
password = your_mysql_password

[paths]
watch_directory = ./data
processed_directory = ./processed  
backup_directory = ./backup

[email]
enabled = false
smtp_server = smtp.gmail.com
smtp_port = 587
username = your_email@gmail.com
password = your_app_password
to_emails = admin@example.com,manager@example.com
```

### 4. 目錄結構設置

```bash
# 創建必要的目錄
mkdir data processed backup

# data/       - 放置待導入的Excel檔案
# processed/  - 已處理的Excel檔案存放處
# backup/     - 資料庫備份和報告存放處
```

## 📖 使用指南

### 手動導入Excel檔案

```bash
# 導入單個檔案
python excel_to_mysql_importer.py --file "GL860 RAWDATA_2507.xlsx"

# 批量導入目錄中的所有Excel檔案
python excel_to_mysql_importer.py --directory "./data"

# 指定資料庫連接參數
python excel_to_mysql_importer.py \
  --file "data.xlsx" \
  --host localhost \
  --username root \
  --password your_password
```

### 自動化維護

```bash
# 啟動自動化維護排程器（推薦方式）
python automated_maintenance.py

# 執行特定維護任務
python automated_maintenance.py --action import    # 手動導入檢查
python automated_maintenance.py --action backup   # 手動備份
python automated_maintenance.py --action clean    # 手動清理舊數據
python automated_maintenance.py --action report   # 生成日報告
```

### MySQL Workbench中查看數據

1. **連接資料庫**: 在MySQL Workbench中連接到 `weather_data` 資料庫
2. **查看原始數據**: 
   ```sql
   SELECT * FROM v_weather_summary ORDER BY measurement_time DESC LIMIT 100;
   ```
3. **查看統計數據**:
   ```sql
   SELECT * FROM v_monthly_stats ORDER BY year DESC, month DESC;
   ```
4. **查看導入記錄**:
   ```sql
   SELECT * FROM import_logs ORDER BY import_time DESC;
   ```

## 🗂️ 資料庫架構

### 主要數據表

| 表名 | 說明 | 主要欄位 |
|------|------|----------|
| `devices` | 設備信息 | 設備型號、名稱、位置 |
| `channels` | 通道配置 | 通道號、測量類型、单位 |
| `weather_raw_data` | 原始氣象數據 | 時間、溫度、濕度 |
| `weather_daily_stats` | 日統計數據 | 日期、平均值、極值 |
| `import_logs` | 導入記錄 | 檔案名、導入時間、狀態 |

### 有用的查詢視圖

- `v_weather_summary`: 氣象數據摘要視圖
- `v_monthly_stats`: 月統計數據視圖

## 🔧 常用SQL查詢

### 查詢最近7天的溫濕度數據
```sql
SELECT 
    measurement_time,
    ch1_temp as temperature,
    ch2_humidity as humidity
FROM weather_raw_data 
WHERE measurement_time >= DATE_SUB(NOW(), INTERVAL 7 DAY)
ORDER BY measurement_time ASC;
```

### 查詢月平均統計
```sql
SELECT 
    year, month,
    ROUND(avg_temperature, 2) as avg_temp,
    ROUND(avg_humidity, 2) as avg_humidity,
    total_precipitation as total_rain
FROM v_monthly_stats
ORDER BY year DESC, month DESC;
```

### 查詢每日極值
```sql
SELECT 
    stat_date,
    temp_max as max_temp,
    temp_min as min_temp,
    humidity_max as max_humidity,
    precipitation
FROM weather_daily_stats 
WHERE stat_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
ORDER BY stat_date DESC;
```

## 🤖 生產環境部署

### 1. Windows服務部署

創建Windows服務腳本 `weather_service.py`:

```python
import win32serviceutil
import win32service
import win32event
import servicemanager
import subprocess
import os

class WeatherService(win32serviceutil.ServiceFramework):
    _svc_name_ = "WeatherDataService"
    _svc_display_name_ = "GL860 Weather Data Service"
    _svc_description_ = "GL860氣象數據自動化維護服務"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)

    def SvcDoRun(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        subprocess.call([
            'python', 
            os.path.join(script_dir, 'automated_maintenance.py')
        ])

if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(WeatherService)
```

### 2. Linux Systemd服務部署

創建服務檔案 `/etc/systemd/system/weather-service.service`:

```ini
[Unit]
Description=GL860 Weather Data Service
After=network.target mysql.service

[Service]
Type=simple
User=weather
WorkingDirectory=/opt/weather_system
ExecStart=/usr/bin/python3 /opt/weather_system/automated_maintenance.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

啟動服務:
```bash
sudo systemctl enable weather-service
sudo systemctl start weather-service
sudo systemctl status weather-service
```

### 3. Docker部署

創建 `Dockerfile`:

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "automated_maintenance.py"]
```

創建 `docker-compose.yml`:

```yaml
version: '3.8'
services:
  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: your_password
      MYSQL_DATABASE: weather_data
    volumes:
      - mysql_data:/var/lib/mysql
      - ./weather_database_schema.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "3306:3306"

  weather-service:
    build: .
    depends_on:
      - mysql
    volumes:
      - ./data:/app/data
      - ./processed:/app/processed
      - ./backup:/app/backup
      - ./config.ini:/app/config.ini

volumes:
  mysql_data:
```

## 📊 監控和維護

### 1. 日誌監控

```bash
# 查看導入日誌
tail -f weather_import.log

# 查看維護日誌  
tail -f weather_maintenance.log

# 查看錯誤日誌
grep ERROR weather_*.log
```

### 2. 資料庫性能監控

```sql
-- 查看表大小
SELECT 
    table_name,
    ROUND(((data_length + index_length) / 1024 / 1024), 2) AS size_mb
FROM information_schema.tables 
WHERE table_schema = 'weather_data'
ORDER BY size_mb DESC;

-- 查看數據量統計
SELECT 
    COUNT(*) as total_records,
    MIN(measurement_time) as earliest_data,
    MAX(measurement_time) as latest_data
FROM weather_raw_data;
```

### 3. 定期維護檢查清單

- [ ] 檢查磁碟空間是否充足
- [ ] 確認備份檔案正常生成
- [ ] 查看錯誤日誌是否有異常
- [ ] 確認Excel檔案正常處理
- [ ] 檢查郵件通知是否正常

## 🚨 故障排除

### 常見問題

**Q: Excel檔案導入失敗**
```
A: 檢查檔案格式是否正確，確認工作表名稱符合預期
   檢查日誌: tail -f weather_import.log
```

**Q: 資料庫連接失敗**
```
A: 確認MySQL服務運行中，檢查config.ini中的連接參數
   測試連接: mysql -h localhost -u root -p weather_data
```

**Q: 自動導入不工作**
```
A: 檢查data目錄權限，確認排程器正在運行
   手動測試: python automated_maintenance.py --action import
```

**Q: 郵件通知不工作**
```
A: 檢查SMTP設置，確認用戶名密碼正確
   Gmail需要使用應用程式密碼，不是登錄密碼
```

## 📈 最佳實踐

1. **定期備份**: 建議每日備份資料庫
2. **監控磁碟空間**: 確保有足夠空間存放數據和備份
3. **日誌輪轉**: 定期清理或壓縮舊日誌檔案
4. **數據驗證**: 定期檢查導入數據的完整性
5. **性能優化**: 根據數據量增長適時添加索引

## 📞 支援

如遇到問題，請檢查：
1. 日誌檔案中的錯誤信息
2. MySQL錯誤日誌
3. Python套件版本兼容性
4. 系統資源使用情況

## 📝 版本歷史

- **v1.0.0**: 初版發布，支持基本導入和維護功能
- 支持GL860 Excel檔案解析
- 自動化導入和備份
- 郵件通知功能
- 統計報告生成

---

© 2024 GL860氣象數據管理系統。本系統專為GRAPHTEC GL860氣象記錄器設計。
