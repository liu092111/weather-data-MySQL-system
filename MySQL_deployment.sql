-- GL860 天氣資料查詢範例
-- 資料表名稱: gl860_weather_data
-- 
-- 資料表結構說明：
-- - record_time: 每筆記錄的完整時間戳記 (DATETIME)
-- - record_date: 當天日期，只在每天第一筆記錄有值 (DATE, 格式: 2025-07-01)
-- - 每日統計欄位 (daily_avg_*, daily_max_*, daily_min_* 等) 也只在每天第一筆有值
-- 
-- Channel 定義：
-- - Channel 1: 溫度 (degC)
-- - Channel 2: 濕度 (%)
-- - Channel 3: 照度 LUX (lux)
-- - Channel 4: UV USA/Apogee (W/m²)
-- - Channel 5: UV Ref (W/m²)

-- 選擇資料庫
USE weather_data;

-- ============================================
-- 1. 基本查詢
-- ============================================

-- 查詢特定月份的所有資料
SELECT * FROM gl860_weather_data 
WHERE year = 2025 AND month = 11 
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

-- 查詢每日平均值（所有5個channel）
SELECT 
    DATE(record_time) as date,
    AVG(channel1_temperature) as avg_temp,
    AVG(channel2_humidity) as avg_humidity,
    AVG(channel3_lux) as avg_lux,
    AVG(channel4_uv_usa) as avg_uv_usa,
    AVG(channel5_uv_ref) as avg_uv_ref
FROM gl860_weather_data
WHERE year = 2025 AND month = 11
GROUP BY DATE(record_time)
ORDER BY date;

-- 查詢每日最高/最低值
SELECT 
    DATE(record_time) as date,
    MAX(channel1_temperature) as max_temp,
    MIN(channel1_temperature) as min_temp,
    MAX(channel2_humidity) as max_humidity,
    MIN(channel2_humidity) as min_humidity,
    MAX(channel3_lux) as max_lux,
    MAX(channel4_uv_usa) as max_uv_usa,
    MAX(channel5_uv_ref) as max_uv_ref
FROM gl860_weather_data
WHERE year = 2025 AND month = 11
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
    MIN(channel2_humidity) as min_humidity,
    AVG(channel3_lux) as avg_lux,
    AVG(channel4_uv_usa) as avg_uv_usa,
    AVG(channel5_uv_ref) as avg_uv_ref
FROM gl860_weather_data
WHERE year = 2025 AND month = 11
GROUP BY year, month;

-- ============================================
-- 3. 時段分析
-- ============================================

-- 查詢特定時段的資料（例如：每天 12:00-14:00）
SELECT * FROM gl860_weather_data
WHERE HOUR(record_time) BETWEEN 12 AND 14
  AND year = 2025 AND month = 11
ORDER BY record_time;

-- 查詢各小時的平均溫度
SELECT 
    HOUR(record_time) as hour,
    AVG(channel1_temperature) as avg_temp,
    COUNT(*) as record_count
FROM gl860_weather_data
WHERE year = 2025 AND month = 11
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
    AVG(channel3_lux) as avg_lux,
    AVG(channel4_uv_usa) as avg_uv_usa,
    AVG(channel5_uv_ref) as avg_uv_ref,
    COUNT(*) as record_count
FROM gl860_weather_data
WHERE year = 2025 AND month = 11
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
    WHERE year = 2025 AND month = 11
)
AND year = 2025 AND month = 11;

-- 查詢最低溫度的記錄
SELECT * FROM gl860_weather_data
WHERE channel1_temperature = (
    SELECT MIN(channel1_temperature) 
    FROM gl860_weather_data 
    WHERE year = 2025 AND month = 11
)
AND year = 2025 AND month = 11;

-- 查詢溫度超過 35°C 的記錄
SELECT 
    record_time,
    channel1_temperature,
    channel2_humidity,
    channel3_lux,
    channel4_uv_usa,
    channel5_uv_ref
FROM gl860_weather_data
WHERE channel1_temperature > 35
  AND year = 2025 AND month = 11
ORDER BY channel1_temperature DESC;

-- 查詢濕度超過 95% 的記錄
SELECT 
    record_time,
    channel1_temperature,
    channel2_humidity
FROM gl860_weather_data
WHERE channel2_humidity > 95
  AND year = 2025 AND month = 11
ORDER BY channel2_humidity DESC;

-- ============================================
-- 5. UV 和光照分析
-- ============================================

-- 查詢每日UV和照度統計
SELECT 
    DATE(record_time) as date,
    COUNT(*) as total_records,
    AVG(channel3_lux) as avg_lux,
    MAX(channel3_lux) as max_lux,
    AVG(channel4_uv_usa) as avg_uv_usa,
    MAX(channel4_uv_usa) as max_uv_usa,
    AVG(channel5_uv_ref) as avg_uv_ref,
    MAX(channel5_uv_ref) as max_uv_ref
FROM gl860_weather_data
WHERE year = 2025 AND month = 11
GROUP BY DATE(record_time)
ORDER BY date;

-- 查詢高 UV 時段（UV USA > 1.0）
SELECT 
    record_time,
    channel4_uv_usa,
    channel5_uv_ref,
    channel1_temperature,
    channel3_lux
FROM gl860_weather_data
WHERE channel4_uv_usa > 1.0
  AND year = 2025 AND month = 11
ORDER BY channel4_uv_usa DESC;

-- 比較 UV USA vs UV Ref 的差異
SELECT 
    DATE(record_time) as date,
    AVG(channel4_uv_usa) as avg_uv_usa,
    AVG(channel5_uv_ref) as avg_uv_ref,
    AVG(channel4_uv_usa) - AVG(channel5_uv_ref) as uv_diff
FROM gl860_weather_data
WHERE year = 2025 AND month = 11
GROUP BY DATE(record_time)
ORDER BY date;

-- 查詢光照度統計（白天時段）
SELECT 
    DATE(record_time) as date,
    AVG(channel3_lux) as avg_lux,
    MAX(channel3_lux) as max_lux,
    MIN(channel3_lux) as min_lux,
    COUNT(*) as record_count
FROM gl860_weather_data
WHERE HOUR(record_time) BETWEEN 6 AND 18
  AND year = 2025 AND month = 11
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
    SUM(CASE WHEN channel3_lux IS NOT NULL THEN 1 ELSE 0 END) as lux_count,
    SUM(CASE WHEN channel4_uv_usa IS NOT NULL THEN 1 ELSE 0 END) as uv_usa_count,
    SUM(CASE WHEN channel5_uv_ref IS NOT NULL THEN 1 ELSE 0 END) as uv_ref_count,
    ROUND(SUM(CASE WHEN channel1_temperature IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*) * 100, 2) as temp_percentage,
    ROUND(SUM(CASE WHEN channel3_lux IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*) * 100, 2) as lux_percentage,
    ROUND(SUM(CASE WHEN channel4_uv_usa IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*) * 100, 2) as uv_usa_percentage
FROM gl860_weather_data
WHERE year = 2025 AND month = 11;

-- 查詢缺失資料的記錄
SELECT 
    record_time,
    CASE WHEN channel1_temperature IS NULL THEN '缺' ELSE '有' END as temp,
    CASE WHEN channel2_humidity IS NULL THEN '缺' ELSE '有' END as humidity,
    CASE WHEN channel3_lux IS NULL THEN '缺' ELSE '有' END as lux,
    CASE WHEN channel4_uv_usa IS NULL THEN '缺' ELSE '有' END as uv_usa,
    CASE WHEN channel5_uv_ref IS NULL THEN '缺' ELSE '有' END as uv_ref
FROM gl860_weather_data
WHERE (channel1_temperature IS NULL 
    OR channel2_humidity IS NULL
    OR channel3_lux IS NULL
    OR channel4_uv_usa IS NULL
    OR channel5_uv_ref IS NULL)
  AND year = 2025 AND month = 11
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
WHERE year = 2025 AND month = 11
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
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM gl860_weather_data WHERE year = 2025 AND month = 11), 2) as percentage
FROM gl860_weather_data
WHERE year = 2025 AND month = 11
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
WHERE year = 2025 AND month = 11
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
    AVG(channel3_lux) as avg_lux,
    AVG(channel4_uv_usa) as avg_uv_usa,
    AVG(channel5_uv_ref) as avg_uv_ref,
    COUNT(*) as record_count
FROM gl860_weather_data
WHERE year = 2025 AND month = 11
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
    channel3_lux as '照度(lux)',
    channel4_uv_usa as 'UV_USA(W/m²)',
    channel5_uv_ref as 'UV_Ref(W/m²)'
FROM gl860_weather_data
WHERE year = 2025 AND month = 11
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
    ROUND(AVG(channel3_lux), 2) as '平均照度',
    ROUND(AVG(channel4_uv_usa), 2) as '平均UV_USA',
    ROUND(AVG(channel5_uv_ref), 2) as '平均UV_Ref'
FROM gl860_weather_data
WHERE year = 2025 AND month = 11
GROUP BY DATE(record_time)
ORDER BY DATE(record_time);

-- ============================================
-- 10. record_date 日期欄位查詢
-- ============================================

-- 說明：record_date 欄位只在每天第一筆記錄中有值
-- 格式為 DATE 類型 (例如: 2025-07-01)，不包含時間
-- 每日統計欄位包含所有5個channel的平均值

-- 查詢所有有 record_date 的記錄（即每天的第一筆）
SELECT 
    record_date as '日期',
    record_time as '記錄時間',
    channel1_temperature as '溫度',
    channel2_humidity as '濕度',
    daily_avg_temperature as '日均溫',
    daily_avg_humidity as '日均濕度',
    daily_avg_lux as '日均照度',
    daily_avg_uv_usa as '日均UV_USA',
    daily_avg_uv_ref as '日均UV_Ref',
    daily_max_temperature as '日最高溫',
    daily_min_temperature as '日最低溫',
    daily_record_count as '當日原始筆數'
FROM gl860_weather_data
WHERE record_date IS NOT NULL
ORDER BY record_date DESC
LIMIT 10;

-- 使用 record_date 查詢特定日期的統計資料
SELECT 
    record_date,
    daily_avg_temperature,
    daily_avg_humidity,
    daily_avg_lux,
    daily_avg_uv_usa,
    daily_avg_uv_ref,
    daily_max_temperature,
    daily_min_temperature,
    daily_temperature_delta,
    daily_record_count
FROM gl860_weather_data
WHERE record_date BETWEEN '2025-11-01' AND '2025-11-30'
ORDER BY record_date;

-- 統計每月有多少天有資料
SELECT 
    year,
    month,
    COUNT(record_date) as '天數'
FROM gl860_weather_data
WHERE record_date IS NOT NULL
GROUP BY year, month
ORDER BY year, month;

-- 查詢特定日期範圍的每日統計（使用 record_date）
SELECT 
    record_date as '日期',
    daily_avg_temperature as '均溫(°C)',
    daily_avg_humidity as '均濕(%)',
    daily_avg_lux as '均照度(lux)',
    daily_avg_uv_usa as '均UV_USA(W/m²)',
    daily_avg_uv_ref as '均UV_Ref(W/m²)',
    daily_max_temperature as '最高溫(°C)',
    daily_min_temperature as '最低溫(°C)',
    daily_temperature_delta as '溫差(°C)',
    daily_record_count as '原始記錄數'
FROM gl860_weather_data
WHERE record_date IS NOT NULL
  AND year = 2025
ORDER BY record_date;

-- ============================================
-- 11. 五個Channel的完整統計比較
-- ============================================

-- 各Channel的整體統計
SELECT 
    'Channel 1 (溫度)' as channel_name,
    COUNT(channel1_temperature) as data_count,
    ROUND(AVG(channel1_temperature), 2) as avg_value,
    ROUND(MAX(channel1_temperature), 2) as max_value,
    ROUND(MIN(channel1_temperature), 2) as min_value,
    'degC' as unit
FROM gl860_weather_data WHERE year = 2025
UNION ALL
SELECT 
    'Channel 2 (濕度)' as channel_name,
    COUNT(channel2_humidity),
    ROUND(AVG(channel2_humidity), 2),
    ROUND(MAX(channel2_humidity), 2),
    ROUND(MIN(channel2_humidity), 2),
    '%'
FROM gl860_weather_data WHERE year = 2025
UNION ALL
SELECT 
    'Channel 3 (照度)' as channel_name,
    COUNT(channel3_lux),
    ROUND(AVG(channel3_lux), 2),
    ROUND(MAX(channel3_lux), 2),
    ROUND(MIN(channel3_lux), 2),
    'lux'
FROM gl860_weather_data WHERE year = 2025
UNION ALL
SELECT 
    'Channel 4 (UV USA)' as channel_name,
    COUNT(channel4_uv_usa),
    ROUND(AVG(channel4_uv_usa), 2),
    ROUND(MAX(channel4_uv_usa), 2),
    ROUND(MIN(channel4_uv_usa), 2),
    'W/m²'
FROM gl860_weather_data WHERE year = 2025
UNION ALL
SELECT 
    'Channel 5 (UV Ref)' as channel_name,
    COUNT(channel5_uv_ref),
    ROUND(AVG(channel5_uv_ref), 2),
    ROUND(MAX(channel5_uv_ref), 2),
    ROUND(MIN(channel5_uv_ref), 2),
    'W/m²'
FROM gl860_weather_data WHERE year = 2025;

-- 每日五個Channel的平均值比較（使用預先計算的統計）
SELECT 
    record_date as '日期',
    daily_avg_temperature as '溫度(°C)',
    daily_avg_humidity as '濕度(%)',
    daily_avg_lux as '照度(lux)',
    daily_avg_uv_usa as 'UV_USA(W/m²)',
    daily_avg_uv_ref as 'UV_Ref(W/m²)',
    daily_record_count as '原始記錄數(分鐘)'
FROM gl860_weather_data
WHERE record_date IS NOT NULL
  AND year = 2025 AND month = 11
ORDER BY record_date;
