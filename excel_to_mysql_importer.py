#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GL860氣象數據Excel導入MySQL工具
支持批量導入多個Excel檔案到MySQL資料庫
"""

import pandas as pd
import mysql.connector
from mysql.connector import Error
import os
import hashlib
import logging
from datetime import datetime, timedelta
import argparse
import glob
import sys
import traceback

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('weather_import.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class WeatherDataImporter:
    def __init__(self, host='localhost', port=3306, database='weather_data', 
                 username='root', password=''):
        """
        初始化資料庫連接參數
        """
        self.host = host
        self.port = port
        self.database = database
        self.username = username
        self.password = password
        self.connection = None
        self.cursor = None

    def connect_database(self):
        """建立資料庫連接"""
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.username,
                password=self.password,
                charset='utf8mb4',
                autocommit=False
            )
            self.cursor = self.connection.cursor()
            logger.info("資料庫連接成功")
            return True
        except Error as e:
            logger.error(f"資料庫連接失敗: {e}")
            return False

    def close_connection(self):
        """關閉資料庫連接"""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
        logger.info("資料庫連接已關閉")

    def calculate_file_hash(self, filepath):
        """計算檔案hash值，用於防止重複導入"""
        hasher = hashlib.sha256()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def check_file_imported(self, file_hash):
        """檢查檔案是否已經導入過"""
        query = "SELECT COUNT(*) FROM import_logs WHERE file_hash = %s"
        self.cursor.execute(query, (file_hash,))
        count = self.cursor.fetchone()[0]
        return count > 0

    def parse_excel_file(self, filepath):
        """
        解析Excel檔案，提取氣象數據
        返回: (原始數據DataFrame, 日統計數據DataFrame, 降水數據DataFrame)
        """
        try:
            # 讀取不同的工作表
            excel_file = pd.ExcelFile(filepath)
            
            # 讀取主要數據表 (2507_Modify工作表或第一個工作表)
            main_sheet = None
            for sheet_name in excel_file.sheet_names:
                if 'Modify' in sheet_name or sheet_name.startswith('25'):
                    main_sheet = sheet_name
                    break
            
            if not main_sheet:
                main_sheet = excel_file.sheet_names[0]
            
            logger.info(f"讀取工作表: {main_sheet}")
            
            # 嘗試不同的skiprows值來找到正確的表頭
            df_raw = None
            for skiprows in [14, 15, 16]:
                try:
                    df_temp = pd.read_excel(filepath, sheet_name=main_sheet, skiprows=skiprows)
                    if 'NO.' in df_temp.columns and 'Time' in df_temp.columns:
                        df_raw = df_temp
                        logger.info(f"使用skiprows={skiprows}成功讀取數據")
                        break
                except:
                    continue
            
            if df_raw is None:
                raise Exception("無法找到正確的表頭格式")
            
            # 清理數據
            df_raw = df_raw.dropna(subset=['NO.', 'Time'])
            
            # 處理時間欄位
            if 'Date&Time' in df_raw.columns:
                df_raw['measurement_time'] = pd.to_datetime(df_raw['Date&Time'])
            else:
                df_raw['measurement_time'] = pd.to_datetime(df_raw['Time'])
            
            # 重命名欄位
            column_mapping = {
                'NO.': 'record_number',
                'degC': 'ch1_temp',
                '%': 'ch2_humidity', 
                'degC.1': 'ch3_temp'
            }
            df_raw = df_raw.rename(columns=column_mapping)
            
            # 選擇需要的欄位
            required_columns = ['record_number', 'measurement_time', 'ch1_temp', 'ch2_humidity']
            if 'ch3_temp' in df_raw.columns:
                required_columns.append('ch3_temp')
            
            df_clean = df_raw[required_columns].copy()
            
            # 讀取降水數據（如果存在）
            df_precip = None
            try:
                if 'Precp(mm)' in excel_file.sheet_names:
                    df_precip = pd.read_excel(filepath, sheet_name='Precp(mm)')
                    df_precip['stat_date'] = pd.to_datetime(df_precip['Time'])
                    df_precip = df_precip.rename(columns={'Precp(mm)': 'precipitation'})
            except Exception as e:
                logger.warning(f"無法讀取降水數據: {e}")
            
            # 讀取統計數據（如果存在）
            df_stats = None
            try:
                if 'Temp+RH' in excel_file.sheet_names:
                    df_stats = pd.read_excel(filepath, sheet_name='Temp+RH')
                elif 'Temp.' in excel_file.sheet_names:
                    df_temp = pd.read_excel(filepath, sheet_name='Temp.')
                    df_rh = pd.read_excel(filepath, sheet_name='RH') if 'RH' in excel_file.sheet_names else None
                    
                    if df_rh is not None:
                        # 合併溫度和濕度統計
                        df_stats = pd.merge(df_temp, df_rh, on='Time', suffixes=('_temp', '_rh'))
            except Exception as e:
                logger.warning(f"無法讀取統計數據: {e}")
            
            logger.info(f"成功解析Excel檔案，原始數據: {len(df_clean)} 筆")
            return df_clean, df_stats, df_precip
            
        except Exception as e:
            logger.error(f"解析Excel檔案失敗 {filepath}: {e}")
            traceback.print_exc()
            return None, None, None

    def insert_raw_data(self, df_raw, device_id, data_source):
        """插入原始氣象數據"""
        if df_raw is None or df_raw.empty:
            return 0
        
        insert_query = """
        INSERT IGNORE INTO weather_raw_data 
        (device_id, record_number, measurement_time, ch1_temp, ch2_humidity, ch3_temp, data_source)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        
        inserted_count = 0
        for _, row in df_raw.iterrows():
            try:
                values = (
                    device_id,
                    int(row['record_number']) if pd.notna(row['record_number']) else None,
                    row['measurement_time'],
                    float(row['ch1_temp']) if pd.notna(row['ch1_temp']) else None,
                    float(row['ch2_humidity']) if pd.notna(row['ch2_humidity']) else None,
                    float(row['ch3_temp']) if pd.notna(row.get('ch3_temp')) else None,
                    data_source
                )
                
                self.cursor.execute(insert_query, values)
                if self.cursor.rowcount > 0:
                    inserted_count += 1
                    
            except Exception as e:
                logger.warning(f"插入數據失敗 (記錄號: {row.get('record_number')}): {e}")
                continue
        
        return inserted_count

    def insert_precipitation_data(self, df_precip, device_id):
        """插入降水數據到日統計表"""
        if df_precip is None or df_precip.empty:
            return
        
        update_query = """
        UPDATE weather_daily_stats 
        SET precipitation = %s, updated_at = CURRENT_TIMESTAMP
        WHERE device_id = %s AND stat_date = %s
        """
        
        for _, row in df_precip.iterrows():
            try:
                stat_date = row['stat_date'].date()
                precipitation = float(row['precipitation']) if pd.notna(row['precipitation']) else 0
                
                self.cursor.execute(update_query, (precipitation, device_id, stat_date))
                
            except Exception as e:
                logger.warning(f"更新降水數據失敗: {e}")
                continue

    def log_import_result(self, filename, file_hash, device_id, records_imported, 
                         status='SUCCESS', error_message=None, date_range=None):
        """記錄導入結果"""
        insert_query = """
        INSERT INTO import_logs 
        (filename, file_hash, records_imported, status, error_message, device_id, 
         date_range_start, date_range_end)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        date_start, date_end = date_range if date_range else (None, None)
        
        values = (
            filename, file_hash, records_imported, status, 
            error_message, device_id, date_start, date_end
        )
        
        self.cursor.execute(insert_query, values)

    def import_excel_file(self, filepath, device_id=1):
        """導入單個Excel檔案"""
        filename = os.path.basename(filepath)
        logger.info(f"開始導入檔案: {filename}")
        
        try:
            # 計算檔案hash
            file_hash = self.calculate_file_hash(filepath)
            
            # 檢查是否已導入
            if self.check_file_imported(file_hash):
                logger.info(f"檔案 {filename} 已經導入過，跳過")
                return True
            
            # 解析Excel檔案
            df_raw, df_stats, df_precip = self.parse_excel_file(filepath)
            
            if df_raw is None:
                raise Exception("無法解析Excel檔案")
            
            # 獲取日期範圍
            date_range = None
            if not df_raw.empty:
                min_date = df_raw['measurement_time'].min().date()
                max_date = df_raw['measurement_time'].max().date()
                date_range = (min_date, max_date)
            
            # 插入原始數據
            records_imported = self.insert_raw_data(df_raw, device_id, filename)
            
            # 插入降水數據
            if df_precip is not None:
                self.insert_precipitation_data(df_precip, device_id)
            
            # 記錄導入日誌
            self.log_import_result(filename, file_hash, device_id, records_imported, 
                                 'SUCCESS', None, date_range)
            
            # 提交事務
            self.connection.commit()
            
            logger.info(f"成功導入 {filename}，插入 {records_imported} 筆記錄")
            return True
            
        except Exception as e:
            # 回滾事務
            if self.connection:
                self.connection.rollback()
            
            error_msg = str(e)
            logger.error(f"導入檔案 {filename} 失敗: {error_msg}")
            
            # 記錄失敗日誌
            try:
                file_hash = self.calculate_file_hash(filepath)
                self.log_import_result(filename, file_hash, device_id, 0, 
                                     'FAILED', error_msg, None)
                self.connection.commit()
            except:
                pass
            
            return False

    def import_directory(self, directory_path, pattern="*.xlsx", device_id=1):
        """批量導入目錄中的Excel檔案"""
        search_pattern = os.path.join(directory_path, pattern)
        excel_files = glob.glob(search_pattern)
        
        if not excel_files:
            logger.warning(f"在目錄 {directory_path} 中未找到符合模式 {pattern} 的檔案")
            return
        
        logger.info(f"找到 {len(excel_files)} 個Excel檔案")
        
        success_count = 0
        for filepath in sorted(excel_files):
            if self.import_excel_file(filepath, device_id):
                success_count += 1
        
        logger.info(f"批量導入完成，成功導入 {success_count}/{len(excel_files)} 個檔案")

def main():
    parser = argparse.ArgumentParser(description='GL860氣象數據Excel導入工具')
    parser.add_argument('--host', default='localhost', help='MySQL主機地址')
    parser.add_argument('--port', type=int, default=3306, help='MySQL端口')
    parser.add_argument('--database', default='weather_data', help='資料庫名稱')
    parser.add_argument('--username', default='root', help='MySQL用戶名')
    parser.add_argument('--password', default='', help='MySQL密碼')
    parser.add_argument('--device-id', type=int, default=1, help='設備ID')
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--file', help='單個Excel檔案路徑')
    group.add_argument('--directory', help='包含Excel檔案的目錄路徑')
    
    parser.add_argument('--pattern', default='*.xlsx', help='檔案匹配模式 (僅用於目錄模式)')
    
    args = parser.parse_args()
    
    # 創建導入器
    importer = WeatherDataImporter(
        host=args.host,
        port=args.port,
        database=args.database,
        username=args.username,
        password=args.password
    )
    
    try:
        # 連接資料庫
        if not importer.connect_database():
            sys.exit(1)
        
        # 執行導入
        if args.file:
            if not os.path.exists(args.file):
                logger.error(f"檔案不存在: {args.file}")
                sys.exit(1)
            importer.import_excel_file(args.file, args.device_id)
        else:
            if not os.path.exists(args.directory):
                logger.error(f"目錄不存在: {args.directory}")
                sys.exit(1)
            importer.import_directory(args.directory, args.pattern, args.device_id)
    
    finally:
        importer.close_connection()

if __name__ == "__main__":
    main()