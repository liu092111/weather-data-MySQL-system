import pandas as pd
import mysql.connector
from mysql.connector import Error
import os
from datetime import datetime
import glob

class GL860DataImporter:
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
            # 如果資料庫不存在，嘗試創建
            try:
                connection = mysql.connector.connect(
                    host=self.host,
                    user=self.user,
                    password=self.password
                )
                cursor = connection.cursor()
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.database}")
                print(f"已創建資料庫: {self.database}")
                connection.close()
                return self.create_connection()
            except Error as e2:
                print(f"創建資料庫錯誤: {e2}")
                return False
    
    def create_table(self):
        """創建天氣資料表"""
        if not self.connection:
            print("請先建立資料庫連接")
            return False
        
        create_table_query = """
        CREATE TABLE IF NOT EXISTS gl860_weather_data (
            id INT AUTO_INCREMENT PRIMARY KEY,
            year INT NOT NULL,
            month INT NOT NULL,
            record_time DATETIME NOT NULL,
            channel1_temperature DECIMAL(10, 2),
            channel2_humidity DECIMAL(10, 2),
            channel3_uv DECIMAL(10, 2),
            channel4_lux DECIMAL(10, 2),
            channel5_device_temp DECIMAL(10, 2),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_year_month (year, month),
            INDEX idx_record_time (record_time)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(create_table_query)
            self.connection.commit()
            print("資料表創建成功或已存在")
            return True
        except Error as e:
            print(f"創建資料表錯誤: {e}")
            return False
    
    def extract_year_month_from_filename(self, filename):
        """從檔名提取年份和月份
        例如: GL860 RAWDATA_2508.xlsx -> year=2025, month=8
        """
        basename = os.path.basename(filename)
        # 提取 YYMM 格式
        parts = basename.split('_')
        if len(parts) >= 2:
            yymm = parts[1].replace('.xlsx', '')
            if len(yymm) == 4:
                year = 2000 + int(yymm[:2])  # 25 -> 2025
                month = int(yymm[2:])         # 08 -> 8
                return year, month
        return None, None
    
    def parse_excel_file(self, filepath):
        """解析 Excel 檔案"""
        year, month = self.extract_year_month_from_filename(filepath)
        if not year or not month:
            print(f"無法從檔名提取年月: {filepath}")
            return None
        
        print(f"\n處理檔案: {os.path.basename(filepath)}")
        print(f"年份: {year}, 月份: {month}")
        
        try:
            # 讀取第一個 sheet（通常是 YYMM 格式的 sheet name）
            df = pd.read_excel(filepath, sheet_name=0, header=None)
            
            # 找到 "Data" 標記的位置
            data_row = None
            for idx, row in df.iterrows():
                if row[0] == 'Data':
                    data_row = idx
                    break
            
            if data_row is None:
                print("找不到資料區域")
                return None
            
            print(f"找到 Data 標記在第 {data_row} 行")
            
            # 讀取資料，跳過標題行
            # Data 標記後的第 1 行是欄位名稱（Number, Date&Time, CH1...）
            # Data 標記後的第 2 行是單位（NO., Time, degC, %, W/m2, lux, degC）
            # 實際資料從第 3 行開始
            # 直接從 Data 行之後讀取，使用第一行作為 header
            df_data = pd.read_excel(
                filepath, 
                sheet_name=0,
                skiprows=data_row + 2  # 跳過 Data 行和欄位名稱行，從單位行開始
            )
            
            print(f"讀取到的欄位: {df_data.columns.tolist()}")
            print(f"前 3 筆資料:\n{df_data.head(3)}")
            
            # 準備資料
            records = []
            
            # 找到日期時間和通道欄位
            # 根據欄位順序和名稱識別各通道
            date_col = None
            ch_cols = {}
            
            # 找出非 NO. 和 Time 的資料欄位
            data_columns = []
            for col in df_data.columns:
                col_str = str(col).strip()
                if 'time' in col_str.lower() or '時間' in col_str:
                    date_col = col
                elif col_str not in ['NO.', 'Number'] and not col_str.startswith('Unnamed'):
                    data_columns.append(col)
            
            # 根據欄位名稱和順序映射到通道
            # 需要智能識別：有些檔案只有3個通道，有些有5個或更多
            # 標準順序應該是：degC(溫度), %(濕度), W/m2(UV), lux(照度), 設備溫度
            
            # 先統計有多少個 degC 欄位
            degc_columns = [col for col in data_columns if 'degc' in str(col).lower()]
            
            for i, col in enumerate(data_columns):
                col_str = str(col)
                col_lower = col_str.lower()
                
                # Channel 1: 第一個溫度欄位
                if 'degc' in col_lower and '.1' not in col_str and 1 not in ch_cols:
                    ch_cols[1] = col
                # Channel 2: 濕度
                elif '%' in col_str or 'rh' in col_lower:
                    ch_cols[2] = col
                # Channel 3: UV
                elif 'w/m2' in col_lower and '.1' not in col_str:
                    ch_cols[3] = col
                # Channel 4: 照度
                elif 'lux' in col_lower:
                    ch_cols[4] = col
                # Channel 5: 設備溫度 - 可能是 degC.1 或者是第二個 degC 欄位
                elif 'degc.1' in col_lower:
                    ch_cols[5] = col
                elif len(degc_columns) >= 2 and 'degc' in col_lower and 1 in ch_cols and col != ch_cols[1]:
                    # 如果有兩個 degC 欄位，第二個就是設備溫度
                    ch_cols[5] = col
            
            print(f"日期欄位: {date_col}")
            print(f"資料欄位: {data_columns}")
            print(f"通道映射: {ch_cols}")
            
            if date_col is None:
                print("警告：找不到日期時間欄位")
                return None
            
            for idx, row in df_data.iterrows():
                try:
                    # 檢查是否有 Date&Time 資料
                    if pd.isna(row.get(date_col)):
                        continue
                    
                    # 解析日期時間
                    date_time = row[date_col]
                    if isinstance(date_time, str):
                        # 如果是字串，嘗試解析
                        date_time = pd.to_datetime(date_time)
                    
                    # 組合完整的 datetime
                    record_time = date_time
                    
                    # 提取各通道資料，處理空值
                    ch1_temp = float(row[ch_cols.get(1)]) if 1 in ch_cols and pd.notna(row.get(ch_cols.get(1))) else None
                    ch2_humidity = float(row[ch_cols.get(2)]) if 2 in ch_cols and pd.notna(row.get(ch_cols.get(2))) else None
                    ch3_uv = float(row[ch_cols.get(3)]) if 3 in ch_cols and pd.notna(row.get(ch_cols.get(3))) else None
                    ch4_lux = float(row[ch_cols.get(4)]) if 4 in ch_cols and pd.notna(row.get(ch_cols.get(4))) else None
                    ch5_device_temp = float(row[ch_cols.get(5)]) if 5 in ch_cols and pd.notna(row.get(ch_cols.get(5))) else None
                    
                    records.append({
                        'year': year,
                        'month': month,
                        'record_time': record_time,
                        'channel1_temperature': ch1_temp,
                        'channel2_humidity': ch2_humidity,
                        'channel3_uv': ch3_uv,
                        'channel4_lux': ch4_lux,
                        'channel5_device_temp': ch5_device_temp
                    })
                    
                except Exception as e:
                    print(f"處理第 {idx} 行時發生錯誤: {e}")
                    continue
            
            print(f"成功解析 {len(records)} 筆記錄")
            return records
            
        except Exception as e:
            print(f"解析 Excel 檔案錯誤: {e}")
            return None
    
    def insert_records(self, records):
        """插入記錄到資料庫"""
        if not self.connection or not records:
            return False
        
        insert_query = """
        INSERT INTO gl860_weather_data 
        (year, month, record_time, channel1_temperature, channel2_humidity, 
         channel3_uv, channel4_lux, channel5_device_temp)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        try:
            cursor = self.connection.cursor()
            
            # 批量插入
            values = [
                (
                    r['year'],
                    r['month'],
                    r['record_time'],
                    r['channel1_temperature'],
                    r['channel2_humidity'],
                    r['channel3_uv'],
                    r['channel4_lux'],
                    r['channel5_device_temp']
                )
                for r in records
            ]
            
            cursor.executemany(insert_query, values)
            self.connection.commit()
            print(f"成功插入 {cursor.rowcount} 筆記錄")
            return True
            
        except Error as e:
            print(f"插入資料錯誤: {e}")
            self.connection.rollback()
            return False
    
    def import_all_files(self, folder_path='GL860'):
        """導入指定資料夾中的所有 Excel 檔案"""
        pattern = os.path.join(folder_path, 'GL860 RAWDATA_*.xlsx')
        files = glob.glob(pattern)
        
        # 排除暫存檔
        files = [f for f in files if not os.path.basename(f).startswith('~$')]
        
        if not files:
            print(f"在 {folder_path} 中找不到符合條件的檔案")
            return
        
        print(f"找到 {len(files)} 個檔案")
        
        # 按檔名排序
        files.sort()
        
        total_records = 0
        for filepath in files:
            records = self.parse_excel_file(filepath)
            if records:
                if self.insert_records(records):
                    total_records += len(records)
        
        print(f"\n總共導入 {total_records} 筆記錄")
    
    def verify_data(self):
        """驗證導入的資料"""
        if not self.connection:
            return
        
        try:
            cursor = self.connection.cursor()
            
            # 統計各月份的記錄數
            query = """
            SELECT year, month, COUNT(*) as record_count,
                   MIN(record_time) as first_record,
                   MAX(record_time) as last_record
            FROM gl860_weather_data
            GROUP BY year, month
            ORDER BY year, month
            """
            
            cursor.execute(query)
            results = cursor.fetchall()
            
            print("\n=== 資料驗證 ===")
            print(f"{'年份':<6} {'月份':<6} {'記錄數':<10} {'第一筆':<20} {'最後一筆':<20}")
            print("-" * 70)
            
            for row in results:
                print(f"{row[0]:<6} {row[1]:<6} {row[2]:<10} {row[3]:<20} {row[4]:<20}")
            
            # 統計各欄位的完整性
            query2 = """
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN channel1_temperature IS NOT NULL THEN 1 ELSE 0 END) as ch1_count,
                SUM(CASE WHEN channel2_humidity IS NOT NULL THEN 1 ELSE 0 END) as ch2_count,
                SUM(CASE WHEN channel3_uv IS NOT NULL THEN 1 ELSE 0 END) as ch3_count,
                SUM(CASE WHEN channel4_lux IS NOT NULL THEN 1 ELSE 0 END) as ch4_count,
                SUM(CASE WHEN channel5_device_temp IS NOT NULL THEN 1 ELSE 0 END) as ch5_count
            FROM gl860_weather_data
            """
            
            cursor.execute(query2)
            result = cursor.fetchone()
            
            print("\n=== 欄位完整性 ===")
            print(f"總記錄數: {result[0]}")
            if result[0] > 0:
                print(f"Channel 1 (溫度):     {result[1]} ({result[1]/result[0]*100:.1f}%)")
                print(f"Channel 2 (濕度):     {result[2]} ({result[2]/result[0]*100:.1f}%)")
                print(f"Channel 3 (UV):       {result[3]} ({result[3]/result[0]*100:.1f}%)")
                print(f"Channel 4 (Lux):      {result[4]} ({result[4]/result[0]*100:.1f}%)")
                print(f"Channel 5 (設備溫度): {result[5]} ({result[5]/result[0]*100:.1f}%)")
            else:
                print("沒有資料可以統計")
            
        except Error as e:
            print(f"驗證資料錯誤: {e}")
    
    def close(self):
        """關閉資料庫連接"""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print("\n資料庫連接已關閉")


def main():
    """主程式"""
    print("=" * 70)
    print("GL860 天氣資料導入 MySQL 系統")
    print("=" * 70)
    
    # 設定資料庫連接參數（請根據實際情況修改）
    importer = GL860DataImporter(
        host='localhost',
        database='weather_data',
        user='root',
        password=''  # 請輸入您的 MySQL 密碼
    )
    
    # 建立連接
    if not importer.create_connection():
        print("無法連接到資料庫，程式結束")
        return
    
    # 創建資料表
    if not importer.create_table():
        print("無法創建資料表，程式結束")
        importer.close()
        return
    
    # 導入所有檔案
    importer.import_all_files('GL860')
    
    # 驗證資料
    importer.verify_data()
    
    # 關閉連接
    importer.close()


if __name__ == "__main__":
    main()
