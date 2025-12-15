"""
整合部署腳本 - 同時部署GL860和COAI資料到MySQL
"""
import sys
from gl860_to_mysql import GL860DataImporter
from coai_to_mysql import COAIDataImporter

def main():
    print("=" * 80)
    print("天氣資料整合部署系統 - GL860 & COAI")
    print("=" * 80)
    
    # 資料庫連接參數（請根據實際情況修改）
    db_config = {
        'host': 'localhost',
        'database': 'weather_data',
        'user': 'root',
        'password': ''  # 請輸入您的 MySQL 密碼
    }
    
    print(f"\n資料庫設定:")
    print(f"  主機: {db_config['host']}")
    print(f"  資料庫: {db_config['database']}")
    print(f"  使用者: {db_config['user']}")
    
    # ============= 第一步：部署GL860資料 =============
    print("\n" + "=" * 80)
    print("第一步：部署 GL860 資料（30分鐘採樣+5通道統計）")
    print("Channel 1: 溫度, Channel 2: 濕度, Channel 3: LUX")
    print("Channel 4: UV (USA), Channel 5: UV (Ref)")
    print("=" * 80)
    
    gl860_importer = GL860DataImporter(**db_config)
    
    # 建立連接
    if not gl860_importer.create_connection():
        print("無法連接到資料庫，程式結束")
        return
    
    # 創建GL860資料表
    if not gl860_importer.create_table():
        print("無法創建GL860資料表，程式結束")
        gl860_importer.close()
        return
    
    # 導入GL860資料（已包含統計）
    print("\n開始導入 GL860 資料...")
    gl860_importer.import_all_files('GL860')
    
    # 驗證GL860資料
    gl860_importer.verify_data()
    
    # 關閉GL860連接
    gl860_importer.close()
    
    # ============= 第二步：部署COAI資料 =============
    print("\n" + "=" * 80)
    print("第二步：部署 COAI 資料")
    print("=" * 80)
    
    coai_importer = COAIDataImporter(**db_config)
    
    # 建立連接
    if not coai_importer.create_connection():
        print("無法連接到資料庫，程式結束")
        return
    
    # 創建COAI獨立資料表
    if not coai_importer.create_coai_table():
        print("無法創建COAI資料表，程式結束")
        coai_importer.close()
        return
    
    # 在GL860表中添加COAI欄位
    print("\n更新 GL860 資料表結構...")
    if not coai_importer.add_coai_columns_to_gl860():
        print("警告：無法更新GL860資料表結構")
    
    # 導入COAI資料並整合到GL860
    print("\n開始導入 COAI 資料...")
    coai_importer.import_all_coai_files('COAI')
    
    # 驗證COAI資料
    coai_importer.verify_coai_data()
    
    # 關閉COAI連接
    coai_importer.close()
    
    # ============= 完成 =============
    print("\n" + "=" * 80)
    print("部署完成！")
    print("=" * 80)
    print("\n資料表摘要:")
    print("  1. gl860_weather_data - GL860氣象資料（包含COAI和每日統計）")
    print("     - 每30分鐘採樣一次")
    print("     - 統計數據使用全部原始資料（每分鐘）計算")
    print("     - 每日統計附加在每天第一筆記錄中")
    print("     - 5個Channel: 溫度, 濕度, LUX, UV(USA), UV(Ref)")
    print("  2. coai_weather_data  - COAI每日氣象資料（獨立表）")
    print("\nGL860表中整合的欄位（僅在每日第一筆記錄顯示）:")
    print("  [Channel資料]")
    print("    - channel1_temperature (溫度 degC)")
    print("    - channel2_humidity (濕度 %)")
    print("    - channel3_lux (照度 lux)")
    print("    - channel4_uv_usa (UV USA W/m²)")
    print("    - channel5_uv_ref (UV Ref W/m²)")
    print("  [COAI資料]")
    print("    - coai_temperature, coai_humidity, coai_rainfall")
    print("  [每日統計 - 所有5個Channel]")
    print("    - daily_avg_*, daily_max_*, daily_min_*")
    print("    - daily_temperature_delta, daily_humidity_delta")
    print("    - daily_record_count (原始資料筆數，基於每分鐘數據)")
    print("\n優點：一次查詢即可獲得完整的每日資訊！")
    print("=" * 80)


if __name__ == "__main__":
    main()
