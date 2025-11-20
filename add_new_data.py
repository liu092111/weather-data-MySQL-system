"""
增量導入新的 GL860 資料
只導入資料庫中不存在的記錄
"""
import pandas as pd
import mysql.connector
from mysql.connector import Error
import os
from datetime import datetime
import glob
import configparser

class GL860IncrementalImporter:
    def __init__(self):
        """初始化資料庫連接參數"""
        self.config = self.read_config()
        self.connection = None
    
    def read_config(self):
        """讀取配置文件"""
        config = configparser.ConfigParser()
        config.read('config.ini', encoding='utf-8')
        return config['MySQL']
    
    def create_connection(self):
        """建立 MySQL 連接"""
        try:
            self.connection = mysql.connector.connect(
                host=self.config['host'],
                database=self.config['database'],
                user=self.config['user'],
                password=self.config['password']
            )
            if self.connection.is_connected():
                print(f"✓ 成功連接到 MySQL 資料庫: {self.config['database']}")
                return True
        except Error as e:
            print(f"✗ 連接錯誤: {e}")
            return False
    
    def extract_year_month_from_filename(self, filename):
        """從檔名提取年份和月份"""
        basename = os.path.basename(filename)
        parts = basename.split('_')
        if len(parts) >= 2:
            yymm = parts[1].replace('.xlsx', '')
            if len(yymm) == 4:
                year = 2000 + int(yymm[:2])
                month = int(yymm[2:])
                return year, month
        return None, None
    
    def check_month_exists(self, year, month):
        """檢查特定年月的資料是否已存在"""
        cursor = self.connection.cursor()
        query = """
        SELECT COUNT(*) 
        FROM gl860_weather_data 
        WHERE year = %s AND month = %s
        """
        cursor.execute(query, (year, month))
        count = cursor.fetchone()[0]
        cursor.close()
        return count > 0
    
    def parse_excel_file(self, filepath):
        """解析 Excel 檔案"""
        year, month = self.extract_year_month_from_filename(filepath)
        if not year or not month:
            print(f"✗ 無法從檔名提取年月: {filepath}")
            return None
        
        print(f"\n處理檔案: {os.path.basename(filepath)}")
        print(f"年份: {year}, 月份: {month}")
        
        try:
            # 讀取第一個 sheet
            df = pd.read_excel(filepath, sheet_name=0, header=None)
            
            # 找到 "Data" 標記的位置
            data_row = None
            for idx, row in df.iterrows():
                if row[0] == 'Data':
                    data_row = idx
                    break
            
            if data_row is None:
                print("✗ 找不到資料區域")
                return None
            
            # 讀取資料
            df_data = pd.read_excel(
                filepath, 
                sheet_name=0,
                skiprows=data_row + 2
            )
            
            print(f"讀取到的欄位: {df_data.columns.tolist()}")
            
            # 準備資料
            records = []
            
            # 找出日期時間和通道欄位
            date_col = None
            ch_cols = {}
            data_columns = []
            
            for col in df_data.columns:
                col_str = str(col).strip()
                if 'time' in col_str.lower() or '時間' in col_str:
                    date_col = col
                elif col_str not in ['NO.', 'Number'] and not col_str.startswith('Unnamed'):
                    data_columns.append(col)
            
            # 統計有多少個 degC 欄位
            degc_columns = [col for col in data_columns if 'degc' in str(col).lower()]
            
            # 映射通道
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
                # Channel 5: 設備溫度
                elif 'degc.1' in col_lower:
                    ch_cols[5] = col
                elif len(degc_columns) >= 2 and 'degc' in col_lower and 1 in ch_cols and col != ch_cols[1]:
                    ch_cols[5] = col
            
            print(f"日期欄位: {date_col}")
            print(f"通道映射: {ch_cols}")
            
            if date_col is None:
                print("✗ 找不到日期時間欄位")
                return None
            
            # 處理每一行資料
            for idx, row in df_data.iterrows():
                try:
                    if pd.isna(row.get(date_col)):
                        continue
                    
                    date_time = row[date_col]
                    if isinstance(date_time, str):
                        date_time = pd.to_datetime(date_time)
                    
                    record_time = date_time
                    
                    # 提取各通道資料
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
                    print(f"✗ 處理第 {idx} 行時發生錯誤: {e}")
                    continue
            
            print(f"✓ 成功解析 {len(records)} 筆記錄")
            return records
            
        except Exception as e:
            print(f"✗ 解析 Excel 檔案錯誤: {e}")
            return None
    
    def insert_records_ignore_duplicates(self, records):
        """插入記錄，忽略重複的資料"""
        if not self.connection or not records:
            return False
        
        # 使用 INSERT IGNORE 來跳過重複的記錄
        insert_query = """
        INSERT IGNORE INTO gl860_weather_data 
        (year, month, record_time, channel1_temperature, channel2_humidity, 
         channel3_uv, channel4_lux, channel5_device_temp)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        try:
            cursor = self.connection.cursor()
            
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
            
            inserted_count = cursor.rowcount
            print(f"✓ 成功插入 {inserted_count} 筆新記錄")
            
            skipped = len(records) - inserted_count
            if skipped > 0:
                print(f"  (跳過 {skipped} 筆已存在的記錄)")
            
            cursor.close()
            return True
            
        except Error as e:
            print(f"✗ 插入資料錯誤: {e}")
            self.connection.rollback()
            return False
    
    def import_file(self, filepath):
        """導入單個檔案"""
        year, month = self.extract_year_month_from_filename(filepath)
        
        if not year or not month:
            return False
        
        # 檢查是否已存在
        if self.check_month_exists(year, month):
            print(f"⚠ {year}年{month}月的資料已存在")
            response = input(f"  是否要重新導入這個月的資料？(y/n): ").strip().lower()
            if response != 'y':
                print("  跳過此檔案")
                return True
        
        records = self.parse_excel_file(filepath)
        if records:
            return self.insert_records_ignore_duplicates(records)
        return False
    
    def import_all_new_files(self, folder_path='GL860'):
        """導入指定資料夾中的所有新檔案"""
        pattern = os.path.join(folder_path, 'GL860 RAWDATA_*.xlsx')
        files = glob.glob(pattern)
        
        # 排除暫存檔
        files = [f for f in files if not os.path.basename(f).startswith('~$')]
        
        if not files:
            print(f"✗ 在 {folder_path} 中找不到符合條件的檔案")
            return
        
        print(f"✓ 找到 {len(files)} 個檔案")
        files.sort()
        
        # 顯示檔案列表
        print("\n檔案列表：")
        for i, filepath in enumerate(files, 1):
            year, month = self.extract_year_month_from_filename(filepath)
            exists = "✓ 已存在" if self.check_month_exists(year, month) else "○ 新檔案"
            print(f"{i}. {os.path.basename(filepath)} - {year}年{month}月 [{exists}]")
        
        print("\n選項：")
        print("1. 全部導入（跳過已存在的月份）")
        print("2. 只導入新檔案")
        print("3. 選擇特定檔案導入")
        print("4. 取消")
        
        choice = input("\n請選擇 (1-4): ").strip()
        
        if choice == '1':
            # 全部導入，但跳過已存在的
            for filepath in files:
                year, month = self.extract_year_month_from_filename(filepath)
                if self.check_month_exists(year, month):
                    print(f"\n⊘ 跳過 {year}年{month}月 (已存在)")
                    continue
                self.import_file(filepath)
        
        elif choice == '2':
            # 只導入新檔案
            new_files = [f for f in files 
                        if not self.check_month_exists(*self.extract_year_month_from_filename(f))]
            if not new_files:
                print("\n沒有新檔案需要導入")
            else:
                for filepath in new_files:
                    self.import_file(filepath)
        
        elif choice == '3':
            # 選擇特定檔案
            file_nums = input("\n請輸入要導入的檔案編號（用逗號分隔，例如：1,3,5）: ").strip()
            try:
                nums = [int(n.strip()) for n in file_nums.split(',')]
                for num in nums:
                    if 1 <= num <= len(files):
                        self.import_file(files[num-1])
                    else:
                        print(f"✗ 編號 {num} 無效")
            except ValueError:
                print("✗ 輸入格式錯誤")
        
        else:
            print("\n取消導入")
    
    def verify_data(self):
        """驗證導入的資料"""
        if not self.connection:
            return
        
        try:
            cursor = self.connection.cursor()
            
            query = """
            SELECT year, month, COUNT(*) as record_count,
                   MIN(record_time) as first_record,
                   MAX(record_time) as last_record,
                   COUNT(channel5_device_temp) as ch5_count
            FROM gl860_weather_data
            GROUP BY year, month
            ORDER BY year, month
            """
            
            cursor.execute(query)
            results = cursor.fetchall()
            
            print("\n" + "="*80)
            print("資料驗證")
            print("="*80)
            print(f"{'年份':<6} {'月份':<6} {'記錄數':<10} {'CH5記錄':<10} {'第一筆':<20} {'最後一筆':<20}")
            print("-" * 80)
            
            for row in results:
                year, month, count, first, last, ch5_count = row
                print(f"{year:<6} {month:<6} {count:<10} {ch5_count:<10} {first.strftime('%Y-%m-%d %H:%M'):<20} {last.strftime('%Y-%m-%d %H:%M'):<20}")
            
            cursor.close()
            
        except Error as e:
            print(f"✗ 驗證資料錯誤: {e}")
    
    def close(self):
        """關閉資料庫連接"""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print("\n✓ 資料庫連接已關閉")


def main():
    """主程式"""
    print("=" * 80)
    print("GL860 天氣資料增量導入系統")
    print("=" * 80)
    print("\n此工具會檢查現有資料，只導入新的記錄\n")
    
    importer = GL860IncrementalImporter()
    
    if not importer.create_connection():
        print("✗ 無法連接到資料庫，程式結束")
        return
    
    try:
        importer.import_all_new_files('GL860')
        importer.verify_data()
    finally:
        importer.close()


if __name__ == "__main__":
    main()
