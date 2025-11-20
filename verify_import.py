import mysql.connector
from mysql.connector import Error

def verify_import():
    """驗證導入的資料"""
    try:
        connection = mysql.connector.connect(
            host='localhost',
            database='weather_data',
            user='root',
            password=''
        )
        
        if connection.is_connected():
            cursor = connection.cursor()
            
            print("=" * 70)
            print("資料驗證報告")
            print("=" * 70)
            
            # 查詢各月份的資料統計
            query = """
            SELECT 
                year, 
                month,
                COUNT(*) as total,
                MIN(record_time) as first_time,
                MAX(record_time) as last_time,
                ROUND(AVG(channel1_temperature), 2) as avg_temp,
                ROUND(AVG(channel2_humidity), 2) as avg_humidity
            FROM gl860_weather_data
            GROUP BY year, month
            ORDER BY year, month
            """
            
            cursor.execute(query)
            results = cursor.fetchall()
            
            print("\n各月份統計：")
            print(f"{'年':<6} {'月':<6} {'記錄數':<10} {'第一筆時間':<20} {'最後一筆時間':<20} {'平均溫度':<10} {'平均濕度':<10}")
            print("-" * 100)
            
            for row in results:
                print(f"{row[0]:<6} {row[1]:<6} {row[2]:<10} {str(row[3]):<20} {str(row[4]):<20} {row[5]:<10} {row[6]:<10}")
            
            # 查詢最高最低溫度
            query2 = """
            SELECT 
                MIN(channel1_temperature) as min_temp,
                MAX(channel1_temperature) as max_temp,
                MIN(channel2_humidity) as min_humidity,
                MAX(channel2_humidity) as max_humidity
            FROM gl860_weather_data
            WHERE channel1_temperature IS NOT NULL
            """
            
            cursor.execute(query2)
            result = cursor.fetchone()
            
            print(f"\n溫濕度範圍：")
            print(f"  最低溫度: {result[0]}°C")
            print(f"  最高溫度: {result[1]}°C")
            print(f"  最低濕度: {result[2]}%")
            print(f"  最高濕度: {result[3]}%")
            
            # 查詢 UV 和 Lux 資料
            query3 = """
            SELECT 
                MIN(record_time) as first_uv_time,
                COUNT(DISTINCT DATE(record_time)) as days_with_uv
            FROM gl860_weather_data
            WHERE channel3_uv IS NOT NULL
            """
            
            cursor.execute(query3)
            result = cursor.fetchone()
            
            print(f"\nUV 資料統計：")
            print(f"  第一筆 UV 記錄時間: {result[0]}")
            print(f"  有 UV 記錄的天數: {result[1]} 天")
            
            # 查詢設備溫度資料
            query4 = """
            SELECT 
                year,
                month,
                COUNT(*) as count
            FROM gl860_weather_data
            WHERE channel5_device_temp IS NOT NULL
            GROUP BY year, month
            """
            
            cursor.execute(query4)
            results = cursor.fetchall()
            
            print(f"\n設備溫度資料分布：")
            for row in results:
                print(f"  {row[0]}年{row[1]}月: {row[2]} 筆記錄")
            
            connection.close()
            print("\n" + "=" * 70)
            print("驗證完成！")
            
    except Error as e:
        print(f"錯誤: {e}")

if __name__ == "__main__":
    verify_import()
