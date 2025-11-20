-- GL860 天氣資料查詢範例
-- 資料表名稱: gl860_weather_data

-- 選擇資料庫
USE weather_data;

-- ============================================
-- 1. 基本查詢
-- ============================================

-- 查詢特定月份的所有資料
SELECT * FROM gl860_weather_data 
WHERE year = 2025 AND month = 8 
ORDER BY record_time
LIMIT 100;

-- 查詢最新的 10 筆記錄
SELECT * FROM gl860_weather_data 
ORDER BY record_time DESC 
LIMIT 10;

-- 統計總記錄數
SELECT COUNT(*) as total_records FROM gl860_weather_data;

-- 統計各月份的記錄數
SELECT year, month, COUNT(*) as record_count
FROM gl860_weather_data
GROUP BY year, month
ORDER BY year, month;

-- ============================================
-- 2. 統計分析
-- ============================================

-- 查詢每日平均值
SELECT 
    DATE(record_time) as date,
    AVG(channel1_temperature) as avg_temp,
    AVG(channel2_humidity) as avg_humidity,
    AVG(channel3_uv) as avg_uv,
    AVG(channel4_lux) as avg_lux
FROM gl860_weather_data
WHERE year = 2025 AND month = 8
GROUP BY DATE(record_time)
ORDER BY date;

-- 查詢每日最高/最低值
SELECT 
    DATE(record_time) as date,
    MAX(channel1_temperature) as max_temp,
    MIN(channel1_temperature) as min_temp,
    MAX(channel2_humidity) as max_humidity,
    MIN(channel2_humidity) as min_humidity,
    MAX(channel3_uv) as max_uv,
    MAX(channel4_lux) as max_lux
FROM gl860_weather_data
WHERE year = 2025 AND month = 8
GROUP BY DATE(record_time)
ORDER BY date;

-- 查詢整月統計
SELECT 
    year,
    month,
    COUNT(*) as record_count,
    AVG(channel1_temperature) as avg_temp,
    MAX(channel1_temperature) as max_temp,
    MIN(channel1_temperature) as min_temp,
    AVG(channel2_humidity) as avg_humidity,
    MAX(channel2_humidity) as max_humidity,
    MIN(channel2_humidity) as min_humidity
FROM gl860_weather_data
WHERE year = 2025 AND month = 8
GROUP BY year, month;

-- ============================================
-- 3. 時段分析
-- ============================================

-- 查詢特定時段的資料（例如：每天 12:00-14:00）
SELECT * FROM gl860_weather_data
WHERE HOUR(record_time) BETWEEN 12 AND 14
  AND year = 2025 AND month = 8
ORDER BY record_time;

-- 查詢各小時的平均溫度
SELECT 
    HOUR(record_time) as hour,
    AVG(channel1_temperature) as avg_temp,
    COUNT(*) as record_count
FROM gl860_weather_data
WHERE year = 2025 AND month = 8
GROUP BY HOUR(record_time)
ORDER BY hour;

-- 查詢白天（6:00-18:00）vs 夜晚（18:00-6:00）的平均值
SELECT 
    CASE 
        WHEN HOUR(record_time) BETWEEN 6 AND 17 THEN '白天'
        ELSE '夜晚'
    END as time_period,
    AVG(channel1_temperature) as avg_temp,
    AVG(channel2_humidity) as avg_humidity,
    COUNT(*) as record_count
FROM gl860_weather_data
WHERE year = 2025 AND month = 8
GROUP BY 
    CASE 
        WHEN HOUR(record_time) BETWEEN 6 AND 17 THEN '白天'
        ELSE '夜晚'
    END;

-- ============================================
-- 4. 極端值查詢
-- ============================================

-- 查詢最高溫度的記錄
SELECT * FROM gl860_weather_data
WHERE channel1_temperature = (
    SELECT MAX(channel1_temperature) 
    FROM gl860_weather_data 
    WHERE year = 2025 AND month = 8
)
AND year = 2025 AND month = 8;

-- 查詢最低溫度的記錄
SELECT * FROM gl860_weather_data
WHERE channel1_temperature = (
    SELECT MIN(channel1_temperature) 
    FROM gl860_weather_data 
    WHERE year = 2025 AND month = 8
)
AND year = 2025 AND month = 8;

-- 查詢溫度超過 35°C 的記錄
SELECT 
    record_time,
    channel1_temperature,
    channel2_humidity,
    channel5_device_temp
FROM gl860_weather_data
WHERE channel1_temperature > 35
  AND year = 2025 AND month = 8
ORDER BY channel1_temperature DESC;

-- 查詢濕度超過 95% 的記錄
SELECT 
    record_time,
    channel1_temperature,
    channel2_humidity
FROM gl860_weather_data
WHERE channel2_humidity > 95
  AND year = 2025 AND month = 8
ORDER BY channel2_humidity DESC;

-- ============================================
-- 5. UV 和光照分析
-- ============================================

-- 查詢有 UV 資料的記錄統計
SELECT 
    DATE(record_time) as date,
    COUNT(*) as total_records,
    SUM(CASE WHEN channel3_uv IS NOT NULL THEN 1 ELSE 0 END) as uv_records,
    AVG(channel3_uv) as avg_uv,
    MAX(channel3_uv) as max_uv
FROM gl860_weather_data
WHERE year = 2025 AND month = 8
GROUP BY DATE(record_time)
ORDER BY date;

-- 查詢高 UV 時段（UV > 0.8）
SELECT 
    record_time,
    channel3_uv,
    channel1_temperature,
    channel4_lux
FROM gl860_weather_data
WHERE channel3_uv > 0.8
  AND year = 2025 AND month = 8
ORDER BY channel3_uv DESC;

-- 查詢光照度統計（有資料的記錄）
SELECT 
    DATE(record_time) as date,
    AVG(channel4_lux) as avg_lux,
    MAX(channel4_lux) as max_lux,
    COUNT(channel4_lux) as lux_record_count
FROM gl860_weather_data
WHERE channel4_lux IS NOT NULL
  AND year = 2025 AND month = 8
GROUP BY DATE(record_time)
ORDER BY date;

-- ============================================
-- 6. 資料完整性檢查
-- ============================================

-- 檢查各欄位的資料完整性
SELECT 
    COUNT(*) as total_records,
    SUM(CASE WHEN channel1_temperature IS NOT NULL THEN 1 ELSE 0 END) as temp_count,
    SUM(CASE WHEN channel2_humidity IS NOT NULL THEN 1 ELSE 0 END) as humidity_count,
    SUM(CASE WHEN channel3_uv IS NOT NULL THEN 1 ELSE 0 END) as uv_count,
    SUM(CASE WHEN channel4_lux IS NOT NULL THEN 1 ELSE 0 END) as lux_count,
    SUM(CASE WHEN channel5_device_temp IS NOT NULL THEN 1 ELSE 0 END) as device_temp_count,
    ROUND(SUM(CASE WHEN channel1_temperature IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*) * 100, 2) as temp_percentage,
    ROUND(SUM(CASE WHEN channel3_uv IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*) * 100, 2) as uv_percentage,
    ROUND(SUM(CASE WHEN channel4_lux IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*) * 100, 2) as lux_percentage
FROM gl860_weather_data
WHERE year = 2025 AND month = 8;

-- 查詢缺失資料的記錄
SELECT 
    record_time,
    CASE WHEN channel1_temperature IS NULL THEN '缺' ELSE '有' END as temp,
    CASE WHEN channel2_humidity IS NULL THEN '缺' ELSE '有' END as humidity,
    CASE WHEN channel3_uv IS NULL THEN '缺' ELSE '有' END as uv,
    CASE WHEN channel4_lux IS NULL THEN '缺' ELSE '有' END as lux,
    CASE WHEN channel5_device_temp IS NULL THEN '缺' ELSE '有' END as device_temp
FROM gl860_weather_data
WHERE (channel1_temperature IS NULL 
    OR channel2_humidity IS NULL
    OR channel3_uv IS NULL
    OR channel4_lux IS NULL
    OR channel5_device_temp IS NULL)
  AND year = 2025 AND month = 8
ORDER BY record_time
LIMIT 50;

-- ============================================
-- 7. 溫濕度關聯分析
-- ============================================

-- 查詢溫度和濕度的分布
SELECT 
    FLOOR(channel1_temperature / 5) * 5 as temp_range,
    FLOOR(channel2_humidity / 10) * 10 as humidity_range,
    COUNT(*) as count
FROM gl860_weather_data
WHERE year = 2025 AND month = 8
GROUP BY 
    FLOOR(channel1_temperature / 5),
    FLOOR(channel2_humidity / 10)
ORDER BY temp_range, humidity_range;

-- 查詢舒適度分析（溫度 20-28°C, 濕度 40-70%）
SELECT 
    CASE 
        WHEN channel1_temperature BETWEEN 20 AND 28 
         AND channel2_humidity BETWEEN 40 AND 70 THEN '舒適'
        WHEN channel1_temperature > 28 THEN '炎熱'
        WHEN channel1_temperature < 20 THEN '寒冷'
        WHEN channel2_humidity > 70 THEN '潮濕'
        WHEN channel2_humidity < 40 THEN '乾燥'
        ELSE '其他'
    END as comfort_level,
    COUNT(*) as record_count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM gl860_weather_data WHERE year = 2025 AND month = 8), 2) as percentage
FROM gl860_weather_data
WHERE year = 2025 AND month = 8
GROUP BY 
    CASE 
        WHEN channel1_temperature BETWEEN 20 AND 28 
         AND channel2_humidity BETWEEN 40 AND 70 THEN '舒適'
        WHEN channel1_temperature > 28 THEN '炎熱'
        WHEN channel1_temperature < 20 THEN '寒冷'
        WHEN channel2_humidity > 70 THEN '潮濕'
        WHEN channel2_humidity < 40 THEN '乾燥'
        ELSE '其他'
    END;

-- ============================================
-- 8. 趨勢分析
-- ============================================

-- 查詢每日溫度變化趨勢
SELECT 
    DATE(record_time) as date,
    MIN(channel1_temperature) as min_temp,
    AVG(channel1_temperature) as avg_temp,
    MAX(channel1_temperature) as max_temp,
    MAX(channel1_temperature) - MIN(channel1_temperature) as temp_range
FROM gl860_weather_data
WHERE year = 2025 AND month = 8
GROUP BY DATE(record_time)
ORDER BY date;

-- 查詢週間 vs 週末的比較
SELECT 
    CASE 
        WHEN DAYOFWEEK(record_time) IN (1, 7) THEN '週末'
        ELSE '週間'
    END as day_type,
    AVG(channel1_temperature) as avg_temp,
    AVG(channel2_humidity) as avg_humidity,
    COUNT(*) as record_count
FROM gl860_weather_data
WHERE year = 2025 AND month = 8
GROUP BY 
    CASE 
        WHEN DAYOFWEEK(record_time) IN (1, 7) THEN '週末'
        ELSE '週間'
    END;

-- ============================================
-- 9. 匯出查詢
-- ============================================

-- 匯出特定月份完整資料（適合匯出到 CSV）
SELECT 
    year as '年份',
    month as '月份',
    DATE_FORMAT(record_time, '%Y-%m-%d %H:%i:%s') as '記錄時間',
    channel1_temperature as '溫度(°C)',
    channel2_humidity as '濕度(%)',
    channel3_uv as 'UV(W/m²)',
    channel4_lux as '照度(lux)',
    channel5_device_temp as '設備溫度(°C)'
FROM gl860_weather_data
WHERE year = 2025 AND month = 8
ORDER BY record_time;

-- 匯出每日統計摘要
SELECT 
    DATE(record_time) as '日期',
    COUNT(*) as '記錄數',
    ROUND(AVG(channel1_temperature), 2) as '平均溫度',
    ROUND(MAX(channel1_temperature), 2) as '最高溫度',
    ROUND(MIN(channel1_temperature), 2) as '最低溫度',
    ROUND(AVG(channel2_humidity), 2) as '平均濕度',
    ROUND(MAX(channel2_humidity), 2) as '最高濕度',
    ROUND(MIN(channel2_humidity), 2) as '最低濕度',
    ROUND(AVG(channel3_uv), 2) as '平均UV',
    ROUND(MAX(channel4_lux), 2) as '最高照度'
FROM gl860_weather_data
WHERE year = 2025 AND month = 8
GROUP BY DATE(record_time)
ORDER BY DATE(record_time);
