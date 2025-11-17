-- 氣象數據資料庫架構設計
-- 支援GL860氣象記錄器數據導入和維護

-- 創建資料庫
CREATE DATABASE IF NOT EXISTS weather_data 
DEFAULT CHARACTER SET utf8mb4 
DEFAULT COLLATE utf8mb4_unicode_ci;

USE weather_data;

-- 設備信息表
CREATE TABLE IF NOT EXISTS devices (
    device_id INT PRIMARY KEY AUTO_INCREMENT,
    device_model VARCHAR(50) NOT NULL COMMENT '設備型號',
    device_name VARCHAR(100) COMMENT '設備名稱',
    location VARCHAR(200) COMMENT '設備位置',
    sampling_interval INT COMMENT '採樣間隔(分鐘)',
    max_channels INT COMMENT '最大通道數',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) COMMENT='氣象設備基本信息表';

-- 通道配置表
CREATE TABLE IF NOT EXISTS channels (
    channel_id INT PRIMARY KEY AUTO_INCREMENT,
    device_id INT,
    channel_number VARCHAR(10) NOT NULL COMMENT '通道號 (如 CH1, CH2)',
    signal_name VARCHAR(100) COMMENT '信號名稱',
    measurement_type VARCHAR(50) COMMENT '測量類型 (TEMP, RH, etc.)',
    unit VARCHAR(20) COMMENT '單位',
    input_range VARCHAR(50) COMMENT '輸入範圍',
    amp_setting VARCHAR(50) COMMENT '放大器設置',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (device_id) REFERENCES devices(device_id),
    UNIQUE KEY unique_device_channel (device_id, channel_number)
) COMMENT='設備通道配置信息表';

-- 原始氣象數據表 (主要數據表)
CREATE TABLE IF NOT EXISTS weather_raw_data (
    data_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    device_id INT NOT NULL,
    record_number INT COMMENT '記錄編號',
    measurement_time DATETIME NOT NULL COMMENT '測量時間',
    ch1_temp DECIMAL(5,2) COMMENT 'CH1溫度(°C)',
    ch2_humidity DECIMAL(5,2) COMMENT 'CH2相對濕度(%)',
    ch3_temp DECIMAL(5,2) COMMENT 'CH3溫度(°C)',
    data_source VARCHAR(100) COMMENT '數據來源檔案',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (device_id) REFERENCES devices(device_id),
    INDEX idx_device_time (device_id, measurement_time),
    INDEX idx_measurement_time (measurement_time),
    UNIQUE KEY unique_device_time_record (device_id, measurement_time, record_number)
) COMMENT='原始氣象數據表';

-- 日統計數據表
CREATE TABLE IF NOT EXISTS weather_daily_stats (
    stat_id INT PRIMARY KEY AUTO_INCREMENT,
    device_id INT NOT NULL,
    stat_date DATE NOT NULL,
    temp_avg DECIMAL(5,2) COMMENT '平均溫度',
    temp_max DECIMAL(5,2) COMMENT '最高溫度',
    temp_min DECIMAL(5,2) COMMENT '最低溫度',
    humidity_avg DECIMAL(5,2) COMMENT '平均濕度',
    humidity_max DECIMAL(5,2) COMMENT '最高濕度',
    humidity_min DECIMAL(5,2) COMMENT '最低濕度',
    precipitation DECIMAL(6,1) COMMENT '降水量(mm)',
    data_count INT COMMENT '數據點數量',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (device_id) REFERENCES devices(device_id),
    UNIQUE KEY unique_device_date (device_id, stat_date),
    INDEX idx_stat_date (stat_date)
) COMMENT='日統計數據表';

-- 數據導入記錄表
CREATE TABLE IF NOT EXISTS import_logs (
    log_id INT PRIMARY KEY AUTO_INCREMENT,
    filename VARCHAR(255) NOT NULL COMMENT '導入檔案名',
    file_hash VARCHAR(64) COMMENT '檔案hash值，防止重複導入',
    import_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    records_imported INT COMMENT '導入記錄數',
    status ENUM('SUCCESS', 'FAILED', 'PARTIAL') DEFAULT 'SUCCESS',
    error_message TEXT,
    device_id INT,
    date_range_start DATE,
    date_range_end DATE,
    FOREIGN KEY (device_id) REFERENCES devices(device_id),
    UNIQUE KEY unique_file_hash (file_hash)
) COMMENT='數據導入日誌表';

-- 創建觸發器：自動更新日統計數據
DELIMITER $$

CREATE TRIGGER update_daily_stats_after_insert
AFTER INSERT ON weather_raw_data
FOR EACH ROW
BEGIN
    INSERT INTO weather_daily_stats (
        device_id, stat_date, temp_avg, temp_max, temp_min,
        humidity_avg, humidity_max, humidity_min, data_count
    )
    SELECT 
        NEW.device_id,
        DATE(NEW.measurement_time),
        AVG(ch1_temp),
        MAX(ch1_temp),
        MIN(ch1_temp),
        AVG(ch2_humidity),
        MAX(ch2_humidity),
        MIN(ch2_humidity),
        COUNT(*)
    FROM weather_raw_data 
    WHERE device_id = NEW.device_id 
      AND DATE(measurement_time) = DATE(NEW.measurement_time)
    ON DUPLICATE KEY UPDATE
        temp_avg = VALUES(temp_avg),
        temp_max = VALUES(temp_max),
        temp_min = VALUES(temp_min),
        humidity_avg = VALUES(humidity_avg),
        humidity_max = VALUES(humidity_max),
        humidity_min = VALUES(humidity_min),
        data_count = VALUES(data_count),
        updated_at = CURRENT_TIMESTAMP;
END$$

DELIMITER ;

-- 初始化設備數據
INSERT INTO devices (device_model, device_name, location, sampling_interval, max_channels) 
VALUES ('GRAPHTEC GL860', 'GL860氣象站', '測試地點', 10, 20)
ON DUPLICATE KEY UPDATE updated_at = CURRENT_TIMESTAMP;

-- 初始化通道配置
INSERT INTO channels (device_id, channel_number, signal_name, measurement_type, unit, amp_setting) 
VALUES 
(1, 'CH1', 'CH1', 'TEMP', 'degC', 'TC_K'),
(1, 'CH2', 'CH2', 'RH', '%', 'RH'),
(1, 'CH3', 'CH3', 'TEMP', 'degC', 'TC_K')
ON DUPLICATE KEY UPDATE signal_name = VALUES(signal_name);

-- 創建用於數據查詢的視圖
CREATE OR REPLACE VIEW v_weather_summary AS
SELECT 
    d.device_name,
    w.measurement_time,
    w.ch1_temp as temperature,
    w.ch2_humidity as humidity,
    w.ch3_temp as temperature_ch3,
    DATE(w.measurement_time) as measurement_date,
    HOUR(w.measurement_time) as measurement_hour
FROM weather_raw_data w
JOIN devices d ON w.device_id = d.device_id
ORDER BY w.measurement_time DESC;

-- 創建月統計視圖
CREATE OR REPLACE VIEW v_monthly_stats AS
SELECT 
    d.device_name,
    YEAR(stat_date) as year,
    MONTH(stat_date) as month,
    AVG(temp_avg) as avg_temperature,
    MAX(temp_max) as max_temperature,
    MIN(temp_min) as min_temperature,
    AVG(humidity_avg) as avg_humidity,
    SUM(precipitation) as total_precipitation,
    COUNT(*) as days_count
FROM weather_daily_stats ds
JOIN devices d ON ds.device_id = d.device_id
GROUP BY d.device_id, YEAR(stat_date), MONTH(stat_date)
ORDER BY year DESC, month DESC;