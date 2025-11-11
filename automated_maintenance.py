#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GL860氣象數據自動化維護工具
包含定時數據導入、數據清理、備份等功能
"""

import os
import sys
import time
import schedule
import logging
from datetime import datetime, timedelta
import mysql.connector
from mysql.connector import Error
import shutil
import subprocess
from pathlib import Path
import configparser
import smtplib
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart

# 導入自定義模組
from excel_to_mysql_importer import WeatherDataImporter

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('weather_maintenance.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class WeatherMaintenanceManager:
    def __init__(self, config_file='config.ini'):
        """初始化維護管理器"""
        self.config = configparser.ConfigParser()
        self.config_file = config_file
        self.load_config()
        
    def load_config(self):
        """載入配置檔案"""
        if not os.path.exists(self.config_file):
            self.create_default_config()
        
        self.config.read(self.config_file, encoding='utf-8')
        
        # 資料庫配置
        self.db_config = {
            'host': self.config.get('database', 'host', fallback='localhost'),
            'port': self.config.getint('database', 'port', fallback=3306),
            'database': self.config.get('database', 'database', fallback='weather_data'),
            'username': self.config.get('database', 'username', fallback='root'),
            'password': self.config.get('database', 'password', fallback='')
        }
        
        # 檔案路徑配置
        self.watch_directory = self.config.get('paths', 'watch_directory', fallback='./data')
        self.processed_directory = self.config.get('paths', 'processed_directory', fallback='./processed')
        self.backup_directory = self.config.get('paths', 'backup_directory', fallback='./backup')
        
        # 郵件配置
        self.email_enabled = self.config.getboolean('email', 'enabled', fallback=False)
        if self.email_enabled:
            self.email_config = {
                'smtp_server': self.config.get('email', 'smtp_server'),
                'smtp_port': self.config.getint('email', 'smtp_port'),
                'username': self.config.get('email', 'username'),
                'password': self.config.get('email', 'password'),
                'to_emails': self.config.get('email', 'to_emails').split(',')
            }
    
    def create_default_config(self):
        """創建預設配置檔案"""
        config = configparser.ConfigParser()
        
        config['database'] = {
            'host': 'localhost',
            'port': '3306',
            'database': 'weather_data',
            'username': 'root',
            'password': ''
        }
        
        config['paths'] = {
            'watch_directory': './data',
            'processed_directory': './processed',
            'backup_directory': './backup'
        }
        
        config['maintenance'] = {
            'auto_import_enabled': 'true',
            'import_schedule': '*/10 * * * *',  # 每10分鐘檢查一次
            'data_retention_days': '365',
            'backup_enabled': 'true',
            'backup_schedule': '0 2 * * 0'  # 每週日凌晨2點備份
        }
        
        config['email'] = {
            'enabled': 'false',
            'smtp_server': 'smtp.gmail.com',
            'smtp_port': '587',
            'username': 'your_email@gmail.com',
            'password': 'your_password',
            'to_emails': 'admin@example.com'
        }
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            config.write(f)
        
        logger.info(f"已創建預設配置檔案: {self.config_file}")
    
    def ensure_directories(self):
        """確保必要的目錄存在"""
        directories = [self.watch_directory, self.processed_directory, self.backup_directory]
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
    
    def send_notification(self, subject, message):
        """發送郵件通知"""
        if not self.email_enabled:
            return
        
        try:
            msg = MimeMultipart()
            msg['From'] = self.email_config['username']
            msg['To'] = ', '.join(self.email_config['to_emails'])
            msg['Subject'] = subject
            
            msg.attach(MimeText(message, 'plain', 'utf-8'))
            
            server = smtplib.SMTP(self.email_config['smtp_server'], self.email_config['smtp_port'])
            server.starttls()
            server.login(self.email_config['username'], self.email_config['password'])
            
            for to_email in self.email_config['to_emails']:
                server.sendmail(self.email_config['username'], to_email, msg.as_string())
            
            server.quit()
            logger.info(f"已發送郵件通知: {subject}")
            
        except Exception as e:
            logger.error(f"發送郵件失敗: {e}")
    
    def auto_import_new_files(self):
        """自動導入新的Excel檔案"""
        logger.info("開始自動導入檢查...")
        
        try:
            # 確保目錄存在
            self.ensure_directories()
            
            # 搜索新的Excel檔案
            watch_path = Path(self.watch_directory)
            excel_files = list(watch_path.glob('*.xlsx')) + list(watch_path.glob('*.xls'))
            
            if not excel_files:
                logger.info("未找到新的Excel檔案")
                return
            
            # 創建導入器
            importer = WeatherDataImporter(**self.db_config)
            
            if not importer.connect_database():
                logger.error("無法連接資料庫")
                return
            
            success_count = 0
            total_files = len(excel_files)
            
            for excel_file in excel_files:
                try:
                    if importer.import_excel_file(str(excel_file)):
                        success_count += 1
                        
                        # 移動已處理的檔案
                        processed_file = Path(self.processed_directory) / excel_file.name
                        shutil.move(str(excel_file), str(processed_file))
                        logger.info(f"已移動檔案到已處理目錄: {excel_file.name}")
                    
                except Exception as e:
                    logger.error(f"處理檔案 {excel_file.name} 時發生錯誤: {e}")
            
            importer.close_connection()
            
            # 發送通知
            if success_count > 0:
                message = f"自動導入完成\n成功處理: {success_count}/{total_files} 個檔案"
                logger.info(message)
                self.send_notification("氣象數據自動導入完成", message)
            
        except Exception as e:
            error_msg = f"自動導入過程中發生錯誤: {e}"
            logger.error(error_msg)
            self.send_notification("氣象數據自動導入失敗", error_msg)
    
    def clean_old_data(self):
        """清理舊數據"""
        logger.info("開始清理舊數據...")
        
        try:
            retention_days = self.config.getint('maintenance', 'data_retention_days', fallback=365)
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            
            connection = mysql.connector.connect(**self.db_config)
            cursor = connection.cursor()
            
            # 刪除舊的原始數據
            delete_query = """
            DELETE FROM weather_raw_data 
            WHERE measurement_time < %s
            """
            cursor.execute(delete_query, (cutoff_date,))
            deleted_count = cursor.rowcount
            
            # 刪除舊的日統計數據
            delete_stats_query = """
            DELETE FROM weather_daily_stats 
            WHERE stat_date < %s
            """
            cursor.execute(delete_stats_query, (cutoff_date.date(),))
            deleted_stats_count = cursor.rowcount
            
            connection.commit()
            cursor.close()
            connection.close()
            
            message = f"數據清理完成\n刪除原始數據: {deleted_count} 筆\n刪除統計數據: {deleted_stats_count} 筆"
            logger.info(message)
            
        except Exception as e:
            error_msg = f"數據清理失敗: {e}"
            logger.error(error_msg)
            self.send_notification("數據清理失敗", error_msg)
    
    def backup_database(self):
        """備份資料庫"""
        logger.info("開始資料庫備份...")
        
        try:
            # 確保備份目錄存在
            backup_path = Path(self.backup_directory)
            backup_path.mkdir(parents=True, exist_ok=True)
            
            # 生成備份檔案名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = backup_path / f"weather_data_backup_{timestamp}.sql"
            
            # 執行mysqldump
            mysqldump_cmd = [
                'mysqldump',
                '-h', self.db_config['host'],
                '-P', str(self.db_config['port']),
                '-u', self.db_config['username'],
                f'-p{self.db_config["password"]}' if self.db_config['password'] else '--password=',
                '--single-transaction',
                '--routines',
                '--triggers',
                self.db_config['database']
            ]
            
            with open(backup_file, 'w', encoding='utf-8') as f:
                result = subprocess.run(mysqldump_cmd, stdout=f, stderr=subprocess.PIPE, text=True)
            
            if result.returncode == 0:
                file_size = backup_file.stat().st_size / (1024 * 1024)  # MB
                message = f"資料庫備份成功\n備份檔案: {backup_file.name}\n檔案大小: {file_size:.2f} MB"
                logger.info(message)
                self.send_notification("資料庫備份完成", message)
                
                # 清理舊備份檔案 (保留最近30個)
                backup_files = sorted(backup_path.glob("weather_data_backup_*.sql"))
                if len(backup_files) > 30:
                    for old_backup in backup_files[:-30]:
                        old_backup.unlink()
                        logger.info(f"已刪除舊備份檔案: {old_backup.name}")
            else:
                error_msg = f"資料庫備份失敗: {result.stderr}"
                logger.error(error_msg)
                self.send_notification("資料庫備份失敗", error_msg)
                
        except Exception as e:
            error_msg = f"資料庫備份過程中發生錯誤: {e}"
            logger.error(error_msg)
            self.send_notification("資料庫備份失敗", error_msg)
    
    def generate_daily_report(self):
        """生成日報告"""
        logger.info("開始生成日報告...")
        
        try:
            connection = mysql.connector.connect(**self.db_config)
            cursor = connection.cursor(dictionary=True)
            
            yesterday = datetime.now().date() - timedelta(days=1)
            
            # 查詢昨日統計數據
            stats_query = """
            SELECT d.device_name, ds.stat_date, ds.temp_avg, ds.temp_max, ds.temp_min,
                   ds.humidity_avg, ds.humidity_max, ds.humidity_min, ds.precipitation, ds.data_count
            FROM weather_daily_stats ds
            JOIN devices d ON ds.device_id = d.device_id
            WHERE ds.stat_date = %s
            """
            cursor.execute(stats_query, (yesterday,))
            daily_stats = cursor.fetchall()
            
            # 查詢導入記錄
            import_query = """
            SELECT COUNT(*) as import_count, SUM(records_imported) as total_records
            FROM import_logs
            WHERE DATE(import_time) = %s AND status = 'SUCCESS'
            """
            cursor.execute(import_query, (yesterday,))
            import_stats = cursor.fetchone()
            
            cursor.close()
            connection.close()
            
            # 生成報告
            report_lines = [
                f"氣象數據日報告 - {yesterday}",
                "=" * 40,
                "",
                "數據導入統計:",
                f"  成功導入檔案: {import_stats['import_count'] or 0} 個",
                f"  導入記錄數: {import_stats['total_records'] or 0} 筆",
                "",
                "氣象數據統計:"
            ]
            
            if daily_stats:
                for stat in daily_stats:
                    report_lines.extend([
                        f"  設備: {stat['device_name']}",
                        f"    平均溫度: {stat['temp_avg']:.2f}°C" if stat['temp_avg'] else "    平均溫度: N/A",
                        f"    溫度範圍: {stat['temp_min']:.2f}°C ~ {stat['temp_max']:.2f}°C" if stat['temp_min'] and stat['temp_max'] else "    溫度範圍: N/A",
                        f"    平均濕度: {stat['humidity_avg']:.2f}%" if stat['humidity_avg'] else "    平均濕度: N/A",
                        f"    降水量: {stat['precipitation'] or 0:.1f} mm",
                        f"    數據點數: {stat['data_count'] or 0} 個",
                        ""
                    ])
            else:
                report_lines.append("  無數據")
            
            report_content = "\n".join(report_lines)
            logger.info("日報告生成完成")
            
            # 保存報告到檔案
            report_file = Path(self.backup_directory) / f"daily_report_{yesterday.strftime('%Y%m%d')}.txt"
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report_content)
            
            # 發送郵件報告
            self.send_notification(f"氣象數據日報告 - {yesterday}", report_content)
            
        except Exception as e:
            error_msg = f"生成日報告失敗: {e}"
            logger.error(error_msg)
            self.send_notification("日報告生成失敗", error_msg)
    
    def run_scheduler(self):
        """運行排程器"""
        logger.info("氣象數據維護排程器啟動")
        
        # 設置排程任務
        if self.config.getboolean('maintenance', 'auto_import_enabled', fallback=True):
            schedule.every(10).minutes.do(self.auto_import_new_files)
            logger.info("已設置自動導入任務: 每10分鐘執行一次")
        
        if self.config.getboolean('maintenance', 'backup_enabled', fallback=True):
            schedule.every().sunday.at("02:00").do(self.backup_database)
            schedule.every().sunday.at("02:30").do(self.clean_old_data)
            logger.info("已設置備份和清理任務: 每週日執行")
        
        schedule.every().day.at("08:00").do(self.generate_daily_report)
        logger.info("已設置日報告任務: 每日08:00執行")
        
        # 運行排程器
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # 每分鐘檢查一次
        except KeyboardInterrupt:
            logger.info("排程器已停止")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='GL860氣象數據自動化維護工具')
    parser.add_argument('--config', default='config.ini', help='配置檔案路徑')
    parser.add_argument('--action', choices=['scheduler', 'import', 'backup', 'clean', 'report'], 
                       help='執行特定動作')
    
    args = parser.parse_args()
    
    manager = WeatherMaintenanceManager(args.config)
    
    if args.action == 'scheduler':
        manager.run_scheduler()
    elif args.action == 'import':
        manager.auto_import_new_files()
    elif args.action == 'backup':
        manager.backup_database()
    elif args.action == 'clean':
        manager.clean_old_data()
    elif args.action == 'report':
        manager.generate_daily_report()
    else:
        # 預設運行排程器
        manager.run_scheduler()

if __name__ == "__main__":
    main()
