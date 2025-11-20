"""
建立統計資料表和視圖
"""
import mysql.connector
from mysql.connector import Error
import configparser

def read_config():
    """讀取配置文件"""
    config = configparser.ConfigParser()
    config.read('config.ini', encoding='utf-8')
    return config['MySQL']

def create_connection():
    """創建資料庫連接"""
    config = read_config()
    try:
        connection = mysql.connector.connect(
            host=config['host'],
            user=config['user'],
            password=config['password'],
            database=config['database']
        )
        return connection
    except Error as e:
        print(f"連接失敗: {e}")
        return None

def create_daily_statistics_table(connection):
    """建立每日統計資料表"""
    cursor = connection.cursor()
    
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS gl860_daily_statistics (
        id INT AUTO_INCREMENT PRIMARY KEY,
        date DATE NOT NULL UNIQUE,
        year INT NOT NULL,
        month INT NOT NULL,
        day INT NOT NULL,
        avg_temperature DECIMAL(5,2),
        avg_humidity DECIMAL(5,2),
        avg_device_temp DECIMAL(5,2),
        max_temperature DECIMAL(5,2),
        max_humidity DECIMAL(5,2),
        min_temperature DECIMAL(5,2),
        min_humidity DECIMAL(5,2),
        temperature_delta DECIMAL(5,2),
        humidity_delta DECIMAL(5,2),
        record_count INT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_date (date),
        INDEX idx_year_month (year, month)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """
    
    try:
        cursor.execute(create_table_sql)
        print("✓ 每日統計資料表創建成功")
    except Error as e:
        print(f"✗ 創建資料表失敗: {e}")
    finally:
        cursor.close()

def create_view_all_data(connection):
    """建立完整資料視圖"""
    cursor = connection.cursor()
    
    # 先刪除舊視圖（如果存在）
    try:
        cursor.execute("DROP VIEW IF EXISTS v_gl860_complete_data")
    except Error:
        pass
    
    create_view_sql = """
    CREATE VIEW v_gl860_complete_data AS
    SELECT 
        id,
        year,
        month,
        DATE(record_time) as date,
        record_time,
        channel1_temperature as temperature,
        channel2_humidity as humidity,
        channel3_uv as uv,
        channel4_lux as lux,
        channel5_device_temp as device_temperature
    FROM gl860_weather_data;
    """
    
    try:
        cursor.execute(create_view_sql)
        print("✓ 完整資料視圖創建成功 (v_gl860_complete_data)")
        print("  使用方式: SELECT * FROM v_gl860_complete_data;")
    except Error as e:
        print(f"✗ 創建視圖失敗: {e}")
    finally:
        cursor.close()

def populate_daily_statistics(connection):
    """填充每日統計資料"""
    cursor = connection.cursor()
    
    insert_sql = """
    INSERT INTO gl860_daily_statistics 
    (date, year, month, day, avg_temperature, avg_humidity, avg_device_temp,
     max_temperature, max_humidity, min_temperature, min_humidity,
     temperature_delta, humidity_delta, record_count)
    SELECT 
        DATE(record_time) as date,
        year,
        month,
        DAY(record_time) as day,
        ROUND(AVG(channel1_temperature), 2) as avg_temperature,
        ROUND(AVG(channel2_humidity), 2) as avg_humidity,
        ROUND(AVG(channel5_device_temp), 2) as avg_device_temp,
        ROUND(MAX(channel1_temperature), 2) as max_temperature,
        ROUND(MAX(channel2_humidity), 2) as max_humidity,
        ROUND(MIN(channel1_temperature), 2) as min_temperature,
        ROUND(MIN(channel2_humidity), 2) as min_humidity,
        ROUND(MAX(channel1_temperature) - MIN(channel1_temperature), 2) as temperature_delta,
        ROUND(MAX(channel2_humidity) - MIN(channel2_humidity), 2) as humidity_delta,
        COUNT(*) as record_count
    FROM gl860_weather_data
    GROUP BY DATE(record_time), year, month, DAY(record_time)
    ON DUPLICATE KEY UPDATE
        avg_temperature = VALUES(avg_temperature),
        avg_humidity = VALUES(avg_humidity),
        avg_device_temp = VALUES(avg_device_temp),
        max_temperature = VALUES(max_temperature),
        max_humidity = VALUES(max_humidity),
        min_temperature = VALUES(min_temperature),
        min_humidity = VALUES(min_humidity),
        temperature_delta = VALUES(temperature_delta),
        humidity_delta = VALUES(humidity_delta),
        record_count = VALUES(record_count);
    """
    
    try:
        cursor.execute(insert_sql)
        connection.commit()
        print(f"✓ 每日統計資料已更新，共 {cursor.rowcount} 天的資料")
    except Error as e:
        print(f"✗ 填充統計資料失敗: {e}")
        connection.rollback()
    finally:
        cursor.close()

def verify_channel5_data(connection):
    """驗證 Channel 5 資料"""
    cursor = connection.cursor()
    
    print("\n" + "="*70)
    print("Channel 5 (設備溫度) 資料驗證")
    print("="*70)
    
    # 檢查每月的 channel 5 數據
    query = """
    SELECT 
        year,
        month,
        COUNT(*) as total_records,
        COUNT(channel5_device_temp) as ch5_records,
        ROUND(COUNT(channel5_device_temp) * 100.0 / COUNT(*), 2) as percentage,
        ROUND(MIN(channel5_device_temp), 2) as min_temp,
        ROUND(MAX(channel5_device_temp), 2) as max_temp,
        ROUND(AVG(channel5_device_temp), 2) as avg_temp
    FROM gl860_weather_data
    GROUP BY year, month
    ORDER BY year, month;
    """
    
    cursor.execute(query)
    results = cursor.fetchall()
    
    print(f"{'年份':<8}{'月份':<8}{'總記錄':<12}{'CH5記錄':<12}{'比例':<10}{'最小值':<10}{'最大值':<10}{'平均值':<10}")
    print("-" * 70)
    
    for row in results:
        year, month, total, ch5, pct, min_t, max_t, avg_t = row
        min_str = f"{min_t:.2f}" if min_t is not None else "N/A"
        max_str = f"{max_t:.2f}" if max_t is not None else "N/A"
        avg_str = f"{avg_t:.2f}" if avg_t is not None else "N/A"
        print(f"{year:<8}{month:<8}{total:<12}{ch5:<12}{pct:<10.1f}%{min_str:<10}{max_str:<10}{avg_str:<10}")
    
    # 顯示一些實際的 channel 5 資料
    print("\n" + "="*70)
    print("Channel 5 資料樣本 (2025年7月，前10筆有值的記錄)")
    print("="*70)
    
    sample_query = """
    SELECT 
        record_time,
        channel1_temperature,
        channel5_device_temp
    FROM gl860_weather_data
    WHERE year = 2025 
    AND month = 7 
    AND channel5_device_temp IS NOT NULL
    ORDER BY record_time
    LIMIT 10;
    """
    
    cursor.execute(sample_query)
    samples = cursor.fetchall()
    
    print(f"{'時間':<25}{'環境溫度(CH1)':<20}{'設備溫度(CH5)':<20}")
    print("-" * 70)
    for record_time, ch1_temp, ch5_temp in samples:
        print(f"{record_time.strftime('%Y-%m-%d %H:%M:%S'):<25}{ch1_temp:<20.2f}{ch5_temp:<20.2f}")
    
    cursor.close()

def show_statistics_sample(connection):
    """顯示統計資料樣本"""
    cursor = connection.cursor()
    
    print("\n" + "="*70)
    print("每日統計資料樣本 (最近10天)")
    print("="*70)
    
    query = """
    SELECT 
        date,
        avg_temperature,
        avg_humidity,
        avg_device_temp,
        max_temperature,
        min_temperature,
        temperature_delta,
        humidity_delta,
        record_count
    FROM gl860_daily_statistics
    ORDER BY date DESC
    LIMIT 10;
    """
    
    cursor.execute(query)
    results = cursor.fetchall()
    
    print(f"{'日期':<12}{'平均溫度':<10}{'平均濕度':<10}{'平均設備溫':<12}{'最高溫':<10}{'最低溫':<10}{'溫差':<8}{'濕差':<8}{'記錄數':<8}")
    print("-" * 100)
    
    for row in results:
        date, avg_t, avg_h, avg_dt, max_t, min_t, t_delta, h_delta, count = row
        avg_dt_str = f"{avg_dt:.2f}" if avg_dt is not None else "N/A"
        print(f"{date.strftime('%Y-%m-%d'):<12}{avg_t:<10.2f}{avg_h:<10.2f}{avg_dt_str:<12}{max_t:<10.2f}{min_t:<10.2f}{t_delta:<8.2f}{h_delta:<8.2f}{count:<8}")
    
    cursor.close()

def main():
    print("="*70)
    print("建立統計資料表和視圖")
    print("="*70)
    
    connection = create_connection()
    if not connection:
        print("無法連接到資料庫")
        return
    
    try:
        # 1. 建立每日統計資料表
        print("\n步驟 1: 建立每日統計資料表")
        create_daily_statistics_table(connection)
        
        # 2. 建立完整資料視圖
        print("\n步驟 2: 建立完整資料視圖")
        create_view_all_data(connection)
        
        # 3. 填充每日統計資料
        print("\n步驟 3: 填充每日統計資料")
        populate_daily_statistics(connection)
        
        # 4. 驗證 Channel 5 資料
        verify_channel5_data(connection)
        
        # 5. 顯示統計資料樣本
        show_statistics_sample(connection)
        
        print("\n" + "="*70)
        print("完成！")
        print("="*70)
        print("\n您現在可以使用：")
        print("1. 查詢完整資料: SELECT * FROM v_gl860_complete_data;")
        print("2. 查詢每日統計: SELECT * FROM gl860_daily_statistics;")
        print("3. 查詢特定月份統計: SELECT * FROM gl860_daily_statistics WHERE year=2025 AND month=7;")
        
    except Exception as e:
        print(f"\n錯誤: {e}")
    finally:
        if connection.is_connected():
            connection.close()
            print("\n資料庫連接已關閉")

if __name__ == "__main__":
    main()
