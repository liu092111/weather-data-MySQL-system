"""
自動化更新資料庫腳本
這個腳本會清除舊資料並重新導入所有 GL860 資料
"""
import subprocess
import sys

def run_script(script_name):
    """執行指定的 Python 腳本"""
    print(f"\n{'='*70}")
    print(f"執行: {script_name}")
    print('='*70)
    
    try:
        result = subprocess.run(
            [sys.executable, script_name],
            check=True,
            capture_output=False,
            text=True
        )
        print(f"\n✓ {script_name} 執行成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n✗ {script_name} 執行失敗")
        return False

def main():
    print("="*70)
    print("GL860 資料庫更新程式")
    print("="*70)
    print("\n此程式會執行以下步驟：")
    print("1. 清除資料表中的舊資料")
    print("2. 重新導入所有 GL860 檔案的資料")
    print("3. 驗證導入結果")
    print("4. 更新統計資料表和視圖")
    print("\n" + "="*70)
    
    # 詢問用戶確認
    response = input("\n是否繼續？(y/n): ").strip().lower()
    if response != 'y':
        print("\n已取消操作")
        return
    
    # 步驟 1: 清除舊資料
    if not run_script('clear_data.py'):
        print("\n錯誤：清除資料失敗，停止執行")
        return
    
    # 步驟 2: 導入新資料
    if not run_script('gl860_to_mysql.py'):
        print("\n錯誤：資料導入失敗，停止執行")
        return
    
    # 步驟 3: 驗證資料
    if not run_script('verify_import.py'):
        print("\n警告：資料驗證失敗")
    
    # 步驟 4: 更新統計資料表和視圖
    if not run_script('create_statistics.py'):
        print("\n警告：統計資料表更新失敗")
    
    print("\n" + "="*70)
    print("✓ 資料庫更新完成！")
    print("="*70)
    print("\n您現在可以在 MySQL Workbench 中查看更新後的資料")
    print("可用的資料表和視圖：")
    print("  - gl860_weather_data (原始資料)")
    print("  - v_gl860_complete_data (簡化視圖)")
    print("  - gl860_daily_statistics (每日統計)")

if __name__ == "__main__":
    main()
