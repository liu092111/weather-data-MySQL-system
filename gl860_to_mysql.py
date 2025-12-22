import pandas as pd
import mysql.connector
from mysql.connector import Error
import os
from datetime import datetime
import glob
import numpy as np

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
        """創建天氣資料表（包含GL860 + COAI + Daily統計）"""
        if not self.connection:
            print("請先建立資料庫連接")
            return False
        
        # 先刪除舊表和舊View
        drop_statements = [
            "DROP VIEW IF EXISTS v_gl860_complete_data",
            "DROP TABLE IF EXISTS gl860_weather_data",
            "DROP TABLE IF EXISTS coai_weather_data"
        ]
        
        # 欄位順序：基本資訊 → Channel 1-5 → COAI → Daily統計（dosage 放在對應的 avg 旁邊）
        create_table_query = """
        CREATE TABLE IF NOT EXISTS gl860_weather_data (
            id INT AUTO_INCREMENT PRIMARY KEY,
            year INT NOT NULL,
            month INT NOT NULL,
            date INT,
            record_date DATE,
            record_time DATETIME NOT NULL,
            channel1_temperature DECIMAL(10, 2),
            channel2_humidity DECIMAL(10, 2),
            channel3_lux DECIMAL(10, 2),
            channel4_uv_usa DECIMAL(10, 2),
            channel5_uv_ref DECIMAL(10, 2),
            coai_temperature DECIMAL(10, 2),
            coai_humidity DECIMAL(10, 2),
            coai_rainfall VARCHAR(20),
            coai_rainfall_raw DECIMAL(10, 2),
            daily_avg_temperature DECIMAL(10, 2),
            daily_avg_humidity DECIMAL(10, 2),
            daily_avg_lux DECIMAL(10, 2),
            daily_lux_dosage DECIMAL(15, 2),
            daily_avg_uv_usa DECIMAL(10, 2),
            daily_uv_usa_dosage DECIMAL(15, 2),
            daily_avg_uv_ref DECIMAL(10, 2),
            daily_uv_ref_dosage DECIMAL(15, 2),
            daily_max_temperature DECIMAL(10, 2),
            daily_max_humidity DECIMAL(10, 2),
            daily_max_lux DECIMAL(10, 2),
            daily_max_uv_usa DECIMAL(10, 2),
            daily_max_uv_ref DECIMAL(10, 2),
            daily_min_temperature DECIMAL(10, 2),
            daily_min_humidity DECIMAL(10, 2),
            daily_min_lux DECIMAL(10, 2),
            daily_min_uv_usa DECIMAL(10, 2),
            daily_min_uv_ref DECIMAL(10, 2),
            daily_temperature_delta DECIMAL(10, 2),
            daily_humidity_delta DECIMAL(10, 2),
            daily_record_count INT,
            INDEX idx_year_month (year, month),
            INDEX idx_record_time (record_time),
            INDEX idx_record_date (record_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        
        create_coai_table_query = """
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
        
        create_view_query = """
        CREATE VIEW v_gl860_complete_data AS
        SELECT id, year, month, CAST(record_time AS DATE) AS date, record_time,
            channel1_temperature AS temperature, channel2_humidity AS humidity,
            channel3_lux AS lux, channel4_uv_usa AS uv_usa, channel5_uv_ref AS uv_ref,
            coai_temperature, coai_humidity, coai_rainfall,
            daily_avg_temperature, daily_avg_humidity, daily_avg_lux,
            daily_avg_uv_usa, daily_avg_uv_ref, daily_record_count
        FROM gl860_weather_data
        """
        
        try:
            cursor = self.connection.cursor()
            for stmt in drop_statements:
                cursor.execute(stmt)
            cursor.execute(create_table_query)
            print("GL860資料表創建成功")
            cursor.execute(create_coai_table_query)
            print("COAI資料表創建成功")
            cursor.execute(create_view_query)
            print("View創建成功")
            self.connection.commit()
            return True
        except Error as e:
            print(f"創建資料表錯誤: {e}")
            return False
    
    def extract_year_month_from_filename(self, filename):
        basename = os.path.basename(filename)
        parts = basename.split('_')
        if len(parts) >= 2:
            yymm = parts[1].replace('.xlsx', '')
            if len(yymm) == 4:
                return 2000 + int(yymm[:2]), int(yymm[2:])
        return None, None
    
    def convert_to_python_type(self, value):
        if value is None or pd.isna(value):
            return None
        if isinstance(value, (np.integer, np.int64)):
            return int(value)
        if isinstance(value, (np.floating, np.float64)):
            return float(value)
        return value
    
    def calculate_daily_statistics(self, all_records_df):
        daily_stats = {}
        all_records_df['date'] = pd.to_datetime(all_records_df['record_time']).dt.date
        
        for date, group in all_records_df.groupby('date'):
            # 排序以進行積分計算
            group = group.sort_values('record_time')
            
            stats = {
                'daily_avg_temperature': group['channel1_temperature'].mean() if group['channel1_temperature'].notna().any() else None,
                'daily_max_temperature': group['channel1_temperature'].max() if group['channel1_temperature'].notna().any() else None,
                'daily_min_temperature': group['channel1_temperature'].min() if group['channel1_temperature'].notna().any() else None,
                'daily_avg_humidity': group['channel2_humidity'].mean() if group['channel2_humidity'].notna().any() else None,
                'daily_max_humidity': group['channel2_humidity'].max() if group['channel2_humidity'].notna().any() else None,
                'daily_min_humidity': group['channel2_humidity'].min() if group['channel2_humidity'].notna().any() else None,
                'daily_avg_lux': group['channel3_lux'].mean() if group['channel3_lux'].notna().any() else None,
                'daily_max_lux': group['channel3_lux'].max() if group['channel3_lux'].notna().any() else None,
                'daily_min_lux': group['channel3_lux'].min() if group['channel3_lux'].notna().any() else None,
                'daily_avg_uv_usa': group['channel4_uv_usa'].mean() if group['channel4_uv_usa'].notna().any() else None,
                'daily_max_uv_usa': group['channel4_uv_usa'].max() if group['channel4_uv_usa'].notna().any() else None,
                'daily_min_uv_usa': group['channel4_uv_usa'].min() if group['channel4_uv_usa'].notna().any() else None,
                'daily_avg_uv_ref': group['channel5_uv_ref'].mean() if group['channel5_uv_ref'].notna().any() else None,
                'daily_max_uv_ref': group['channel5_uv_ref'].max() if group['channel5_uv_ref'].notna().any() else None,
                'daily_min_uv_ref': group['channel5_uv_ref'].min() if group['channel5_uv_ref'].notna().any() else None,
                'daily_record_count': len(group)
            }
            
            if stats['daily_max_temperature'] is not None and stats['daily_min_temperature'] is not None:
                stats['daily_temperature_delta'] = stats['daily_max_temperature'] - stats['daily_min_temperature']
            else:
                stats['daily_temperature_delta'] = None
            
            if stats['daily_max_humidity'] is not None and stats['daily_min_humidity'] is not None:
                stats['daily_humidity_delta'] = stats['daily_max_humidity'] - stats['daily_min_humidity']
            else:
                stats['daily_humidity_delta'] = None
            
            # 計算每日 dosage (積分)
            # 使用梯形積分法：∫f(t)dt ≈ Σ[(f(t_i) + f(t_{i+1})) / 2 * Δt]
            # Δt 以小時為單位
            stats['daily_lux_dosage'] = self.calculate_dosage(group, 'channel3_lux')
            stats['daily_uv_usa_dosage'] = self.calculate_dosage(group, 'channel4_uv_usa')
            stats['daily_uv_ref_dosage'] = self.calculate_dosage(group, 'channel5_uv_ref')
            
            for key in stats:
                if stats[key] is not None and key != 'daily_record_count':
                    stats[key] = round(float(stats[key]), 2)
            
            daily_stats[date] = stats
        
        return daily_stats
    
    def calculate_dosage(self, group, column_name):
        """
        使用梯形積分法計算每日劑量 (dosage)
        Dosage = ∫ value(t) dt
        結果單位: 
        - lux: lux·hour (照度·小時)
        - UV (W/m²): J/m² (焦耳/平方米) = W·s/m² = W/m² * 3600s/hour
        """
        if column_name not in group.columns:
            return None
        
        # 過濾有效數據
        valid_data = group[['record_time', column_name]].dropna()
        
        if len(valid_data) < 2:
            # 如果只有一筆數據，無法進行積分
            if len(valid_data) == 1:
                return None
            return None
        
        valid_data = valid_data.sort_values('record_time')
        
        total_dosage = 0.0
        times = valid_data['record_time'].values
        values = valid_data[column_name].values
        
        for i in range(len(values) - 1):
            # 計算時間差（小時）
            t1 = pd.Timestamp(times[i])
            t2 = pd.Timestamp(times[i + 1])
            delta_hours = (t2 - t1).total_seconds() / 3600.0
            
            # 梯形法：(v1 + v2) / 2 * dt
            avg_value = (values[i] + values[i + 1]) / 2.0
            total_dosage += avg_value * delta_hours
        
        return total_dosage
    
    def sample_records_30min(self, all_records_df, daily_stats):
        sampled_records = []
        all_records_df['record_time'] = pd.to_datetime(all_records_df['record_time'])
        all_records_df['date'] = all_records_df['record_time'].dt.date
        
        for date, group in all_records_df.groupby('date'):
            group = group.sort_values('record_time')
            stats = daily_stats.get(date, {})
            group['time_30min'] = group['record_time'].dt.floor('30min')
            
            for time_slot, slot_group in group.groupby('time_30min'):
                first_record = slot_group.iloc[0]
                
                record = {
                    'year': self.convert_to_python_type(first_record['year']),
                    'month': self.convert_to_python_type(first_record['month']),
                    'date': date.day,
                    'record_time': first_record['record_time'].to_pydatetime(),
                    'channel1_temperature': self.convert_to_python_type(first_record['channel1_temperature']),
                    'channel2_humidity': self.convert_to_python_type(first_record['channel2_humidity']),
                    'channel3_lux': self.convert_to_python_type(first_record['channel3_lux']),
                    'channel4_uv_usa': self.convert_to_python_type(first_record['channel4_uv_usa']),
                    'channel5_uv_ref': self.convert_to_python_type(first_record['channel5_uv_ref'])
                }
                
                if first_record['record_time'] == group['record_time'].min():
                    record['record_date'] = date
                    for key, value in stats.items():
                        record[key] = self.convert_to_python_type(value)
                else:
                    record['record_date'] = None
                    for key in ['daily_avg_temperature', 'daily_avg_humidity', 'daily_avg_lux', 
                               'daily_avg_uv_usa', 'daily_avg_uv_ref', 'daily_max_temperature',
                               'daily_max_humidity', 'daily_max_lux', 'daily_max_uv_usa', 'daily_max_uv_ref',
                               'daily_min_temperature', 'daily_min_humidity', 'daily_min_lux',
                               'daily_min_uv_usa', 'daily_min_uv_ref', 'daily_temperature_delta',
                               'daily_humidity_delta', 'daily_lux_dosage', 'daily_uv_usa_dosage',
                               'daily_uv_ref_dosage', 'daily_record_count']:
                        record[key] = None
                
                sampled_records.append(record)
        
        return sampled_records
    
    def parse_excel_file(self, filepath):
        year, month = self.extract_year_month_from_filename(filepath)
        if not year or not month:
            print(f"無法從檔名提取年月: {filepath}")
            return None
        
        print(f"\n處理檔案: {os.path.basename(filepath)}")
        print(f"年份: {year}, 月份: {month}")
        
        try:
            df = pd.read_excel(filepath, sheet_name=0, header=None)
            data_row = None
            for idx, row in df.iterrows():
                if row[0] == 'Data':
                    data_row = idx
                    break
            
            if data_row is None:
                print("找不到資料區域")
                return None
            
            df_data = pd.read_excel(filepath, sheet_name=0, skiprows=data_row + 2)
            date_col = None
            ch_cols = {}
            data_columns = []
            
            for col in df_data.columns:
                col_str = str(col).strip()
                if 'time' in col_str.lower():
                    date_col = col
                elif col_str not in ['NO.', 'Number'] and not col_str.startswith('Unnamed'):
                    data_columns.append(col)
            
            for col in data_columns:
                col_str = str(col)
                col_lower = col_str.lower()
                if 'degc' in col_lower and '.1' not in col_str:
                    ch_cols[1] = col
                elif '%' in col_str or 'rh' in col_lower:
                    ch_cols[2] = col
                elif 'lux' in col_lower:
                    ch_cols[3] = col
                elif 'usa' in col_lower:
                    ch_cols[4] = col
                elif 'ref' in col_lower:
                    ch_cols[5] = col
            
            wm2_columns = [col for col in data_columns if 'w/m2' in str(col).lower()]
            if len(wm2_columns) >= 2:
                if 4 not in ch_cols:
                    ch_cols[4] = wm2_columns[0]
                if 5 not in ch_cols:
                    ch_cols[5] = wm2_columns[1]
            
            if date_col is None:
                print("警告：找不到日期時間欄位")
                return None
            
            print(f"識別的欄位: CH1={ch_cols.get(1)}, CH2={ch_cols.get(2)}, CH3={ch_cols.get(3)}, CH4={ch_cols.get(4)}, CH5={ch_cols.get(5)}")
            
            all_records = []
            skipped_empty = 0
            for idx, row in df_data.iterrows():
                try:
                    if pd.isna(row.get(date_col)):
                        continue
                    date_time = row[date_col]
                    if isinstance(date_time, str):
                        date_time = pd.to_datetime(date_time)
                    
                    # 讀取所有 channel 數據
                    temp_val = float(row[ch_cols.get(1)]) if 1 in ch_cols and pd.notna(row.get(ch_cols.get(1))) else None
                    hum_val = float(row[ch_cols.get(2)]) if 2 in ch_cols and pd.notna(row.get(ch_cols.get(2))) else None
                    lux_val = float(row[ch_cols.get(3)]) if 3 in ch_cols and pd.notna(row.get(ch_cols.get(3))) else None
                    
                    # UV值（CH4/CH5）：負值設為0
                    uv_usa_val = float(row[ch_cols.get(4)]) if 4 in ch_cols and pd.notna(row.get(ch_cols.get(4))) else None
                    uv_ref_val = float(row[ch_cols.get(5)]) if 5 in ch_cols and pd.notna(row.get(ch_cols.get(5))) else None
                    if uv_usa_val is not None and uv_usa_val < 0:
                        uv_usa_val = 0
                    if uv_ref_val is not None and uv_ref_val < 0:
                        uv_ref_val = 0
                    
                    # 跳過所有數據欄位都是空的記錄
                    if temp_val is None and hum_val is None and lux_val is None and uv_usa_val is None and uv_ref_val is None:
                        skipped_empty += 1
                        continue
                    
                    all_records.append({
                        'year': year, 'month': month, 'record_time': date_time,
                        'channel1_temperature': temp_val,
                        'channel2_humidity': hum_val,
                        'channel3_lux': lux_val,
                        'channel4_uv_usa': uv_usa_val,
                        'channel5_uv_ref': uv_ref_val
                    })
                except:
                    continue
            
            if skipped_empty > 0:
                print(f"跳過 {skipped_empty} 筆空白記錄")
            
            if not all_records:
                print("沒有解析到任何記錄")
                return None
            
            print(f"成功解析 {len(all_records)} 筆記錄")
            all_records_df = pd.DataFrame(all_records)
            print("計算每日統計...")
            daily_stats = self.calculate_daily_statistics(all_records_df)
            print("進行 30 分鐘採樣...")
            sampled_records = self.sample_records_30min(all_records_df, daily_stats)
            print(f"採樣後: {len(sampled_records)} 筆（減少 {(1-len(sampled_records)/len(all_records))*100:.1f}%）")
            return sampled_records
            
        except Exception as e:
            print(f"解析錯誤: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def insert_records(self, records):
        if not self.connection or not records:
            return False
        
        # 欄位順序配合資料表：dosage 放在對應的 avg 旁邊
        insert_query = """
        INSERT INTO gl860_weather_data 
        (year, month, date, record_date, record_time, 
         channel1_temperature, channel2_humidity, channel3_lux, channel4_uv_usa, channel5_uv_ref,
         daily_avg_temperature, daily_avg_humidity, 
         daily_avg_lux, daily_lux_dosage,
         daily_avg_uv_usa, daily_uv_usa_dosage,
         daily_avg_uv_ref, daily_uv_ref_dosage,
         daily_max_temperature, daily_max_humidity, daily_max_lux, daily_max_uv_usa, daily_max_uv_ref,
         daily_min_temperature, daily_min_humidity, daily_min_lux, daily_min_uv_usa, daily_min_uv_ref,
         daily_temperature_delta, daily_humidity_delta,
         daily_record_count)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        try:
            cursor = self.connection.cursor()
            values = [(r['year'], r['month'], r['date'], r.get('record_date'), r['record_time'],
                      r['channel1_temperature'], r['channel2_humidity'], r['channel3_lux'], r['channel4_uv_usa'], r['channel5_uv_ref'],
                      r.get('daily_avg_temperature'), r.get('daily_avg_humidity'), 
                      r.get('daily_avg_lux'), r.get('daily_lux_dosage'),
                      r.get('daily_avg_uv_usa'), r.get('daily_uv_usa_dosage'),
                      r.get('daily_avg_uv_ref'), r.get('daily_uv_ref_dosage'),
                      r.get('daily_max_temperature'), r.get('daily_max_humidity'), r.get('daily_max_lux'), r.get('daily_max_uv_usa'), r.get('daily_max_uv_ref'),
                      r.get('daily_min_temperature'), r.get('daily_min_humidity'), r.get('daily_min_lux'), r.get('daily_min_uv_usa'), r.get('daily_min_uv_ref'),
                      r.get('daily_temperature_delta'), r.get('daily_humidity_delta'),
                      r.get('daily_record_count')) for r in records]
            cursor.executemany(insert_query, values)
            self.connection.commit()
            print(f"成功插入 {cursor.rowcount} 筆記錄")
            return True
        except Error as e:
            print(f"插入錯誤: {e}")
            self.connection.rollback()
            return False
    
    def import_all_gl860_files(self, folder_path='GL860'):
        pattern = os.path.join(folder_path, 'GL860 RAWDATA_*.xlsx')
        files = [f for f in glob.glob(pattern) if not os.path.basename(f).startswith('~$')]
        if not files:
            print("找不到GL860檔案")
            return
        print(f"找到 {len(files)} 個GL860檔案")
        files.sort()
        total = 0
        for filepath in files:
            records = self.parse_excel_file(filepath)
            if records and self.insert_records(records):
                total += len(records)
        print(f"\n總共導入 {total} 筆GL860記錄")
    
    def import_all_coai_files(self, folder_path='COAI'):
        pattern = os.path.join(folder_path, 'C0AI10-*.xlsx')
        files = [f for f in glob.glob(pattern) if not os.path.basename(f).startswith('~$')]
        if not files:
            print("找不到COAI檔案")
            return
        print(f"\n找到 {len(files)} 個COAI檔案")
        files.sort()
        total = 0
        for filepath in files:
            records = self.parse_coai_file(filepath)
            if records and self.insert_coai_records(records):
                total += len(records)
        print(f"總共導入 {total} 筆COAI記錄")
        self.update_gl860_with_coai()
    
    def parse_coai_file(self, filepath):
        basename = os.path.basename(filepath)
        parts = basename.replace('.xlsx', '').split('-')
        if len(parts) < 3:
            return None
        try:
            year, month = int(parts[1]), int(parts[2])
        except:
            return None
        
        # 獲取該月的實際天數
        import calendar
        max_days = calendar.monthrange(year, month)[1]
        
        print(f"\n處理COAI: {basename} ({year}/{month}), 該月有 {max_days} 天")
        try:
            df = pd.read_excel(filepath, sheet_name=0, skiprows=1)
            col_map = {}
            for i, col in enumerate(df.columns):
                c = str(col).lower()
                if i == 0:
                    col_map['date'] = i
                elif 'temperature' in c and 'max' not in c:
                    col_map['temp'] = i
                elif 'rh' in c and 'min' not in c:
                    col_map['hum'] = i
                elif 'precp' in c:
                    col_map['rain'] = i
            
            records = []
            skipped = 0
            for idx, row in df.iterrows():
                try:
                    d = row.iloc[col_map['date']]
                    if pd.isna(d):
                        continue
                    
                    # 解析日期
                    day_num = None
                    if isinstance(d, (int, float)):
                        day_num = int(d)
                    elif isinstance(d, str):
                        try:
                            parsed = pd.to_datetime(d)
                            day_num = parsed.day
                        except:
                            continue
                    elif hasattr(d, 'day'):
                        day_num = d.day
                    
                    # 跳過超出該月天數的日期（例如11月沒有31日）
                    if day_num is None or day_num > max_days:
                        skipped += 1
                        continue
                    
                    # 創建有效日期
                    try:
                        obs_date = pd.Timestamp(year=year, month=month, day=day_num).date()
                    except:
                        skipped += 1
                        continue
                    
                    def sf(v):
                        if pd.isna(v) or v in ['/', 'X', '']:
                            return None
                        try:
                            return float(v)
                        except:
                            return None
                    
                    temp = sf(row.iloc[col_map.get('temp')]) if 'temp' in col_map else None
                    hum = sf(row.iloc[col_map.get('hum')]) if 'hum' in col_map else None
                    rain = sf(row.iloc[col_map.get('rain')]) if 'rain' in col_map else None
                    
                    # 只有當至少有一個有效數據時才加入記錄
                    if temp is not None or hum is not None or rain is not None:
                        records.append({
                            'year': year, 'month': month, 'obs_date': obs_date,
                            'temperature': temp,
                            'humidity': hum,
                            'rainfall': rain
                        })
                    else:
                        skipped += 1
                except:
                    continue
            
            print(f"解析 {len(records)} 筆有效記錄" + (f"，跳過 {skipped} 筆無效記錄" if skipped > 0 else ""))
            return records
        except Exception as e:
            print(f"錯誤: {e}")
            return None
    
    def insert_coai_records(self, records):
        if not self.connection or not records:
            return False
        try:
            cursor = self.connection.cursor()
            for r in records:
                cursor.execute("""
                    INSERT INTO coai_weather_data (year, month, obs_date, temperature, humidity, rainfall)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE temperature=VALUES(temperature), humidity=VALUES(humidity), rainfall=VALUES(rainfall)
                """, (r['year'], r['month'], r['obs_date'], r['temperature'], r['humidity'], r['rainfall']))
            self.connection.commit()
            return True
        except Error as e:
            print(f"插入COAI錯誤: {e}")
            return False
    
    def update_gl860_with_coai(self):
        if not self.connection:
            return
        try:
            cursor = self.connection.cursor()
            # coai_rainfall: 有數值(>0)時設為 "1"，無數值(NULL 或 0)時設為 NULL（不顯示）
            cursor.execute("""
                UPDATE gl860_weather_data g
                INNER JOIN (SELECT DATE(record_time) as rd, MIN(id) as fid FROM gl860_weather_data GROUP BY DATE(record_time)) fr ON g.id = fr.fid
                INNER JOIN coai_weather_data c ON DATE(g.record_time) = c.obs_date
                SET g.coai_temperature = c.temperature, 
                    g.coai_humidity = c.humidity,
                    g.coai_rainfall = CASE 
                        WHEN c.rainfall > 0 THEN '1' 
                        ELSE NULL 
                    END,
                    g.coai_rainfall_raw = c.rainfall
            """)
            self.connection.commit()
            print(f"已更新 {cursor.rowcount} 筆GL860記錄的COAI數據")
        except Error as e:
            print(f"更新COAI錯誤: {e}")
    
    def verify_data(self):
        if not self.connection:
            return
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT year, month, COUNT(*) as cnt, MIN(record_time), MAX(record_time) FROM gl860_weather_data GROUP BY year, month ORDER BY year, month")
            print("\n=== GL860 資料驗證 ===")
            for row in cursor.fetchall():
                print(f"{row[0]}/{row[1]:02d}: {row[2]} 筆, {row[3]} ~ {row[4]}")
            
            cursor.execute("""
                SELECT record_date, daily_avg_temperature, daily_avg_humidity, daily_avg_lux, 
                       daily_avg_uv_usa, daily_avg_uv_ref, coai_temperature, coai_humidity, coai_rainfall, 
                       coai_rainfall_raw, daily_lux_dosage, daily_uv_usa_dosage, daily_uv_ref_dosage, daily_record_count
                FROM gl860_weather_data WHERE record_date IS NOT NULL ORDER BY record_date DESC LIMIT 5
            """)
            print("\n=== 最近5天統計 ===")
            for row in cursor.fetchall():
                date, avg_temp, avg_hum, avg_lux, avg_uv_usa, avg_uv_ref = row[0:6]
                coai_temp, coai_hum, coai_rain, coai_rain_raw = row[6:10]
                lux_dose, uv_usa_dose, uv_ref_dose, rec_count = row[10:14]
                print(f"{date}: 均溫{avg_temp}°C, 均濕{avg_hum}%, 均LUX{avg_lux}, UV_USA{avg_uv_usa}, UV_Ref{avg_uv_ref}")
                print(f"        COAI({coai_temp}°C,{coai_hum}%,雨:{coai_rain},原始:{coai_rain_raw}mm)")
                print(f"        Dosage: LUX={lux_dose} lux·h, UV_USA={uv_usa_dose} W·h/m², UV_Ref={uv_ref_dose} W·h/m², 原始{rec_count}筆")
            
            # 顯示 coai_rainfall 統計
            cursor.execute("""
                SELECT coai_rainfall, COUNT(*) as cnt 
                FROM gl860_weather_data 
                WHERE record_date IS NOT NULL AND coai_rainfall IS NOT NULL
                GROUP BY coai_rainfall
            """)
            print("\n=== COAI Rainfall 統計 ===")
            print("'1' = 有降雨, '/' = 無降雨")
            for row in cursor.fetchall():
                label = "有降雨" if row[0] == '1' else "無降雨"
                print(f"  {row[0]} ({label}): {row[1]} 天")
                
        except Error as e:
            print(f"驗證錯誤: {e}")
    
    def close(self):
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print("\n資料庫連接已關閉")


def main():
    print("=" * 70)
    print("GL860 & COAI 一次部署系統")
    print("Channel 1: 溫度, Channel 2: 濕度, Channel 3: LUX")
    print("Channel 4: UV (USA), Channel 5: UV (Ref)")
    print("=" * 70)
    
    importer = GL860DataImporter(host='localhost', database='weather_data', user='root', password='')
    
    if not importer.create_connection():
        print("無法連接資料庫")
        return
    
    if not importer.create_table():
        print("無法創建資料表")
        importer.close()
        return
    
    # 步驟1: 導入GL860資料
    print("\n" + "=" * 50)
    print("步驟1: 導入GL860資料")
    print("=" * 50)
    importer.import_all_gl860_files('GL860')
    
    # 步驟2: 導入COAI資料並更新到GL860
    print("\n" + "=" * 50)
    print("步驟2: 導入COAI資料")
    print("=" * 50)
    importer.import_all_coai_files('COAI')
    
    # 步驟3: 驗證
    importer.verify_data()
    importer.close()
    
    print("\n" + "=" * 70)
    print("部署完成！欄位順序: CH1-5 → COAI → Daily統計")
    print("=" * 70)


if __name__ == "__main__":
    main()
