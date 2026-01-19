"""
整合部署腳本 - 同時部署GL860和COAI資料到MySQL
"""
import sys
from gl860_to_mysql import GL860DataImporter

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
    
    # ============= 部署GL860和COAI資料 =============
    print("\n" + "=" * 80)
    print("部署 GL860 資料（30分鐘採樣+17通道支援）")
    print("Channel 1: 溫度, Channel 2: 濕度, Channel 3: LUX")
    print("Channel 4: UV (USA), Channel 5: UV (Ref)")
    print("Channel 6-17: 魚缸溫度感測器 (2512月份起)")
    print("=" * 80)
    
    importer = GL860DataImporter(**db_config)
    
    # 建立連接
    if not importer.create_connection():
        print("無法連接到資料庫，程式結束")
        return
    
    # 創建資料表
    if not importer.create_table():
        print("無法創建資料表，程式結束")
        importer.close()
        return
    
    # 導入GL860資料
    print("\n開始導入 GL860 資料...")
    importer.import_all_gl860_files('GL860')
    
    # 導入COAI資料
    print("\n開始導入 COAI 資料...")
    importer.import_all_coai_files('COAI')
    
    # 驗證資料
    importer.verify_data()
    
    # 關閉連接
    importer.close()
    
    # ============= 完成 =============
    print("\n" + "=" * 80)
    print("部署完成！")
    print("=" * 80)
    print("\n資料表摘要:")
    print("  1. gl860_weather_data - GL860氣象資料（包含COAI和每日統計）")
    print("     - 每30分鐘採樣一次")
    print("     - 統計數據使用全部原始資料（每分鐘）計算")
    print("     - 每日統計附加在每天第一筆記錄中")
    print("  2. coai_weather_data  - COAI每日氣象資料（獨立表）")
    print("\nGL860表中整合的欄位：")
    print("  [Channel 1-5 資料]")
    print("    - channel1_temperature (溫度 degC)")
    print("    - channel2_humidity (濕度 %)")
    print("    - channel3_lux (照度 lux)")
    print("    - channel4_uv_usa (UV USA W/m²)")
    print("    - channel5_uv_ref (UV Ref W/m²)")
    print("  [Channel 6-17 魚缸溫度 (2512月份起)]")
    print("    - channel6_goldfish_camera_white ~ channel17_marlin_lamp_black")
    print("  [COAI資料 - 僅每日第一筆]")
    print("    - coai_temperature, coai_humidity")
    print("    - coai_rainfall_raw (實際降雨量)")
    print("    - coai_rainfall (有降雨=1)")
    print("  [每日統計 - 僅每日第一筆]")
    print("    - daily_avg_temperature, daily_avg_humidity")
    print("    - daily_avg_lux, daily_lux_dosage")
    print("    - daily_avg_uv_usa, daily_uv_usa_dosage")
    print("    - daily_avg_uv_ref, daily_uv_ref_dosage")
    print("    - daily_record_count")
    print("=" * 80)


if __name__ == "__main__":
    main()
