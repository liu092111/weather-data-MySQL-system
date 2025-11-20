import mysql.connector
from mysql.connector import Error

def clear_table():
    """清空資料表"""
    try:
        connection = mysql.connector.connect(
            host='localhost',
            database='weather_data',
            user='root',
            password=''
        )
        
        if connection.is_connected():
            cursor = connection.cursor()
            cursor.execute("TRUNCATE TABLE gl860_weather_data")
            connection.commit()
            print("已清空 gl860_weather_data 資料表")
            connection.close()
            
    except Error as e:
        print(f"錯誤: {e}")

if __name__ == "__main__":
    clear_table()
