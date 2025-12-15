import pandas as pd
import mysql.connector
from mysql.connector import Error
import os
from datetime import datetime
import glob

class COAIDataImporter:
    def __init__(self, host='localhost', database='weather_data', user='root', password=''):
        """初始化資料庫連接參數"""
        self.host = host
        self.database = database
        self.user = user
        self.password = password
        self.connection = None
    
    def create_connection(self):
        """建立 MySQL 連接"""
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                database=self.database,
                user=self.user,
                password=self.password
            )
            if self.connection.is_connected():
                print(f"成功連接到 MySQL 資料庫: {self.database}")
                return True
        except Error as e:
            print(f"連接錯誤: {e}")
            return False
    
    def create_coai_table(self):
        """創建COAI獨立資料表"""
        if not self.connection:
            print("請先建立資料庫連接")
            return False
        
        create_table_query = """
        CREATE TABLE IF NOT EXISTS coai_weather_data (
            id INT AUTO_INCREMENT PRIMARY KEY,
            year INT NOT NULL,
            month INT NOT NULL,
            obs_date DATE NOT NULL,
            temperature DECIMAL(10, 2),
            humidity DECIMAL(10, 2),
            wind_speed DECIMAL(10, 2),
            wind_direction DECIMAL(10, 2),
            wind_gust DECIMAL(10, 2),
            rainfall DECIMAL(10, 2),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY idx_obs_date (obs_date),
            INDEX idx_year_month (year, month)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(create_table_query)
            self.connection.commit()
            print("COAI資料表創建成功或已存在")
            return True
        except Error as e:
            print(f"創建COAI資料表錯誤: {e}")
            return False
    
    def add_coai_columns_to_gl860(self):
        """在GL860資料表中增加COAI欄位和record_date欄位"""
        if not self.connection:
            print("請先建立資料庫連接")
            return False
        
        try:
            cursor = self.connection.cursor()
            
            # 檢查欄位是否已存在
            cursor.execute("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = %s 
                AND TABLE_NAME = 'gl860_weather_data'
            """, (self.database,))
            
            existing_columns = [row[0] for row in cursor.fetchall()]
            
            # 添加date、record_date欄位和COAI欄位（如果不存在）
            columns_to_add = [
                ('date', 'INT AFTER month'),
                ('record_date', 'DATE AFTER date'),
                ('coai_temperature', 'DECIMAL(10, 2)'),
                ('coai_humidity', 'DECIMAL(10, 2)'),
                ('coai_rainfall', 'VARCHAR(20)')  # 使用 VARCHAR 以便存儲 "/" 表示無降雨
            ]
            
            for col_name, col_type in columns_to_add:
                if col_name not in existing_columns:
                    alter_query = f"""
                    ALTER TABLE gl860_weather_data 
                    ADD COLUMN {col_name} {col_type}
                    """
                    cursor.execute(alter_query)
                    print(f"已添加欄位: {col_name}")
                else:
                    print(f"欄位已存在: {col_name}")
            
            self.connection.commit()
            
            # 更新 date 欄位數據（從 record_time 提取日期）
            print("正在更新 date 欄位數據...")
            cursor.execute("""
                UPDATE gl860_weather_data 
                SET date = DAY(record_time)
                WHERE date IS NULL
            """)
            self.connection.commit()
            updated_rows = cursor.rowcount
            if updated_rows > 0:
                print(f"已更新 {updated_rows} 筆記錄的 date 欄位")
            
            print("GL860資料表欄位更新完成")
            return True
            
        except Error as e:
            print(f"更新GL860資料表錯誤: {e}")
            return False
    
    def extract_year_month_from_filename(self, filename):
        """從檔名提取年份和月份
        例如: C0AI10-2025-07.xlsx -> year=2025, month=7
        """
        basename = os.path.basename(filename)
        parts = basename.replace('.xlsx', '').split('-')
        if len(parts) >= 3:
            try:
                year = int(parts[1])
                month = int(parts[2])
                return year, month
            except ValueError:
                pass
        return None, None
    
    def parse_coai_excel_file(self, filepath):
        """解析 COAI Excel 檔案"""
        year, month = self.extract_year_month_from_filename(filepath)
        if not year or not month:
            print(f"無法從檔名提取年月: {filepath}")
            return None
        
        print(f"\n處理檔案: {os.path.basename(filepath)}")
        print(f"年份: {year}, 月份: {month}")
        
        try:
            # 讀取Excel檔案，跳過第一行中文標題，使用第二行英文標題作為列名
            df = pd.read_excel(filepath, sheet_name=0, skiprows=1)
            
            print(f"讀取到 {len(df)} 筆記錄")
            print(f"欄位名稱: {df.columns.tolist()}")
            
            # 智能識別欄位位置
            col_mapping = {}
            for i, col in enumerate(df.columns):
                col_str = str(col).strip().lower()
                if i == 0:
                    col_mapping['date'] = i
                elif 'temperature' in col_str and 'max' not in col_str:
                    col_mapping['temperature'] = i
                elif 'rh' in col_str and 'min' not in col_str:
                    col_mapping['humidity'] = i
                elif 'ws' in col_str and 'gust' not in col_str:
                    col_mapping['wind_speed'] = i
                elif 'wd' in col_str:
                    col_mapping['wind_direction'] = i
                elif 'gust' in col_str:
                    col_mapping['wind_gust'] = i
                elif 'precp' in col_str:
                    col_mapping['rainfall'] = i
            
            print(f"欄位映射: {col_mapping}")
            
            records = []
            
            for idx, row in df.iterrows():
                try:
                    # 解析日期
                    obs_date = row.iloc[col_mapping['date']]
                    if pd.isna(obs_date):
                        continue
                    
                    # 處理日期格式
                    if isinstance(obs_date, (int, float)):
                        # 如果是數字，補齊為完整日期
                        day = int(obs_date)
                        obs_date = pd.Timestamp(year=year, month=month, day=day)
                    elif isinstance(obs_date, str):
                        obs_date = pd.to_datetime(obs_date)
                    
                    # 提取各項數據，處理 '/', 'X' 和空值
                    def safe_float(val):
                        if pd.isna(val) or val == '/' or val == 'X' or val == '':
                            return None
                        try:
                            return float(val)
                        except (ValueError, TypeError):
                            return None
                    
                    temperature = safe_float(row.iloc[col_mapping.get('temperature')]) if 'temperature' in col_mapping else None
                    humidity = safe_float(row.iloc[col_mapping.get('humidity')]) if 'humidity' in col_mapping else None
                    wind_speed = safe_float(row.iloc[col_mapping.get('wind_speed')]) if 'wind_speed' in col_mapping else None
                    wind_direction = safe_float(row.iloc[col_mapping.get('wind_direction')]) if 'wind_direction' in col_mapping else None
                    wind_gust = safe_float(row.iloc[col_mapping.get('wind_gust')]) if 'wind_gust' in col_mapping else None
                    rainfall = safe_float(row.iloc[col_mapping.get('rainfall')]) if 'rainfall' in col_mapping else None
                    
                    # rainfall 為 0 時設為 "/" 表示無降雨
                    # 注意：這裡 rainfall 保持為數字，在 GL860 更新時才轉換為 "/"
                    
                    records.append({
                        'year': year,
                        'month': month,
                        'obs_date': obs_date.date(),
                        'temperature': temperature,
                        'humidity': humidity,
                        'wind_speed': wind_speed,
                        'wind_direction': wind_direction,
                        'wind_gust': wind_gust,
                        'rainfall': rainfall
                    })
                    
                except Exception as e:
                    print(f"處理第 {idx} 行時發生錯誤: {e}")
                    continue
            
            print(f"成功解析 {len(records)} 筆記錄")
            return records
            
        except Exception as e:
            print(f"解析 COAI Excel 檔案錯誤: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def insert_coai_records(self, records):
        """插入COAI記錄到獨立資料表"""
        if not self.connection or not records:
            return False
        
        insert_query = """
        INSERT INTO coai_weather_data 
        (year, month, obs_date, temperature, humidity, wind_speed, 
         wind_direction, wind_gust, rainfall)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
        temperature = VALUES(temperature),
        humidity = VALUES(humidity),
        wind_speed = VALUES(wind_speed),
        wind_direction = VALUES(wind_direction),
        wind_gust = VALUES(wind_gust),
        rainfall = VALUES(rainfall)
        """
        
        try:
            cursor = self.connection.cursor()
            
            values = [
                (
                    r['year'],
                    r['month'],
                    r['obs_date'],
                    r['temperature'],
                    r['humidity'],
                    r['wind_speed'],
                    r['wind_direction'],
                    r['wind_gust'],
                    r['rainfall']
                )
                for r in records
            ]
            
            cursor.executemany(insert_query, values)
            self.connection.commit()
            print(f"成功插入/更新 {cursor.rowcount} 筆COAI記錄")
            return True
            
        except Error as e:
            print(f"插入COAI資料錯誤: {e}")
            self.connection.rollback()
            return False
    
    def update_gl860_with_coai_data(self):
        """將COAI的溫度、濕度、降雨量更新到GL860資料表的每日第一筆記錄"""
        if not self.connection:
            return False
        
        try:
            cursor = self.connection.cursor()
            
            # 找出GL860每天的第一筆記錄ID
            print("\n開始更新GL860資料表的COAI欄位...")
            
            # 首先確保 coai_rainfall 欄位是 VARCHAR 類型
            try:
                cursor.execute("""
                    ALTER TABLE gl860_weather_data 
                    MODIFY COLUMN coai_rainfall VARCHAR(20)
                """)
                self.connection.commit()
                print("已將 coai_rainfall 欄位改為 VARCHAR 類型")
            except:
                pass  # 如果已經是 VARCHAR 則忽略
            
            # rainfall = 0 或 NULL 時設為 "/"，其他正常更新
            update_query = """
            UPDATE gl860_weather_data g
            INNER JOIN (
                SELECT 
                    DATE(record_time) as record_date,
                    MIN(id) as first_id
                FROM gl860_weather_data
                GROUP BY DATE(record_time)
            ) first_records ON g.id = first_records.first_id
            INNER JOIN coai_weather_data c ON DATE(g.record_time) = c.obs_date
            SET 
                g.coai_temperature = c.temperature,
                g.coai_humidity = c.humidity,
                g.coai_rainfall = CASE 
                    WHEN c.rainfall IS NULL OR c.rainfall = 0 THEN '/' 
                    ELSE CAST(c.rainfall AS CHAR) 
                END
            """
            
            cursor.execute(update_query)
            self.connection.commit()
            
            affected_rows = cursor.rowcount
            print(f"成功更新 {affected_rows} 筆GL860記錄的COAI數據")
            
            # 將現有的 coai_rainfall = 0 或 '0' 或 '0.00' 或 NULL 更新為 "/"
            cursor.execute("""
                UPDATE gl860_weather_data 
                SET coai_rainfall = '/' 
                WHERE (coai_rainfall = '0' OR coai_rainfall = '0.00' 
                       OR coai_rainfall IS NULL OR coai_rainfall = '')
                AND coai_temperature IS NOT NULL
            """)
            self.connection.commit()
            zero_to_slash = cursor.rowcount
            if zero_to_slash > 0:
                print(f"已將 {zero_to_slash} 筆 coai_rainfall = 0/NULL 的記錄更新為 '/'")
            
            # 清除非第一筆記錄的COAI數據（確保只有每天第一筆有數據）
            clear_query = """
            UPDATE gl860_weather_data g
            LEFT JOIN (
                SELECT 
                    DATE(record_time) as record_date,
                    MIN(id) as first_id
                FROM gl860_weather_data
                GROUP BY DATE(record_time)
            ) first_records ON g.id = first_records.first_id
            SET 
                g.coai_temperature = NULL,
                g.coai_humidity = NULL,
                g.coai_rainfall = NULL
            WHERE first_records.first_id IS NULL
            AND (g.coai_temperature IS NOT NULL 
                 OR g.coai_humidity IS NOT NULL 
                 OR g.coai_rainfall IS NOT NULL)
            """
            
            cursor.execute(clear_query)
            self.connection.commit()
            print(f"已清除非第一筆記錄的COAI數據")
            
            return True
            
        except Error as e:
            print(f"更新GL860表的COAI數據時發生錯誤: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def import_all_coai_files(self, folder_path='COAI'):
        """導入指定資料夾中的所有COAI Excel 檔案"""
        pattern = os.path.join(folder_path, 'C0AI10-*.xlsx')
        files = glob.glob(pattern)
        
        # 排除暫存檔
        files = [f for f in files if not os.path.basename(f).startswith('~$')]
        
        if not files:
            print(f"在 {folder_path} 中找不到符合條件的檔案")
            return
        
        print(f"找到 {len(files)} 個COAI檔案")
        
        # 按檔名排序
        files.sort()
        
        total_records = 0
        for filepath in files:
            records = self.parse_coai_excel_file(filepath)
            if records:
                if self.insert_coai_records(records):
                    total_records += len(records)
        
        print(f"\n總共導入 {total_records} 筆COAI記錄")
        
        # 更新GL860資料表
        self.update_gl860_with_coai_data()
    
    def verify_coai_data(self):
        """驗證COAI資料"""
        if not self.connection:
            return
        
        try:
            cursor = self.connection.cursor()
            
            # 統計COAI資料
            query = """
            SELECT year, month, COUNT(*) as record_count,
                   MIN(obs_date) as first_date,
                   MAX(obs_date) as last_date
            FROM coai_weather_data
            GROUP BY year, month
            ORDER BY year, month
            """
            
            cursor.execute(query)
            results = cursor.fetchall()
            
            print("\n=== COAI資料驗證 ===")
            print(f"{'年份':<6} {'月份':<6} {'記錄數':<10} {'第一天':<15} {'最後一天':<15}")
            print("-" * 60)
            
            for row in results:
                print(f"{row[0]:<6} {row[1]:<6} {row[2]:<10} {str(row[3]):<15} {str(row[4]):<15}")
            
            # 驗證GL860中的COAI數據
            query2 = """
            SELECT 
                COUNT(DISTINCT DATE(record_time)) as days_with_data,
                COUNT(*) as total_records_with_coai
            FROM gl860_weather_data
            WHERE coai_temperature IS NOT NULL
            """
            
            cursor.execute(query2)
            result = cursor.fetchone()
            
            print("\n=== GL860表中的COAI數據 ===")
            print(f"有COAI數據的天數: {result[0]}")
            print(f"包含COAI數據的記錄數: {result[1]}")
            
            # 顯示範例
            query3 = """
            SELECT 
                DATE(record_time) as date,
                COUNT(*) as total_records,
                SUM(CASE WHEN coai_temperature IS NOT NULL THEN 1 ELSE 0 END) as records_with_coai
            FROM gl860_weather_data
            GROUP BY DATE(record_time)
            HAVING records_with_coai > 0
            ORDER BY date
            LIMIT 5
            """
            
            cursor.execute(query3)
            results = cursor.fetchall()
            
            print("\n=== 前5天的COAI整合狀況 ===")
            print(f"{'日期':<15} {'GL860總記錄':<15} {'含COAI記錄':<15}")
            print("-" * 45)
            for row in results:
                print(f"{str(row[0]):<15} {row[1]:<15} {row[2]:<15}")
            
        except Error as e:
            print(f"驗證COAI資料錯誤: {e}")
    
    def close(self):
        """關閉資料庫連接"""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print("\n資料庫連接已關閉")


def main():
    """主程式"""
    print("=" * 70)
    print("COAI 天氣資料導入 MySQL 系統")
    print("=" * 70)
    
    # 設定資料庫連接參數（請根據實際情況修改）
    importer = COAIDataImporter(
        host='localhost',
        database='weather_data',
        user='root',
        password=''  # 請輸入您的 MySQL 密碼
    )
    
    # 建立連接
    if not importer.create_connection():
        print("無法連接到資料庫，程式結束")
        return
    
    # 創建COAI獨立資料表
    if not importer.create_coai_table():
        print("無法創建COAI資料表，程式結束")
        importer.close()
        return
    
    # 在GL860表中添加COAI欄位
    if not importer.add_coai_columns_to_gl860():
        print("警告：無法更新GL860資料表結構")
    
    # 導入所有COAI檔案
    importer.import_all_coai_files('COAI')
    
    # 驗證資料
    importer.verify_coai_data()
    
    # 關閉連接
    importer.close()


if __name__ == "__main__":
    main()
