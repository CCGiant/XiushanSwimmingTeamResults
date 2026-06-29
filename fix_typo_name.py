import sqlite3

def fix_typo():
    conn = sqlite3.connect("ctsa_shoushan.sqlite")
    cur = conn.cursor()

    # 👉 請在這裡設定錯誤與正確的名字
    WRONG_NAME = "洪少義"   # 例如："朱品成"
    CORRECT_NAME = "洪少羲" # 例如："朱品丞"

    # 1. 把錯的名字全部更新為正確的名字
    cur.execute("""
        UPDATE OR IGNORE results 
        SET student_name = ? 
        WHERE student_name = ?
    """, (CORRECT_NAME, WRONG_NAME))
    
    update_count = cur.rowcount

    # 2. 如果遇到極端情況 (剛好正確名字已經有一模一樣的成績)，
    # OR IGNORE 會略過更新，這時我們就把殘留的錯誤紀錄直接刪除
    cur.execute("DELETE FROM results WHERE student_name = ?", (WRONG_NAME,))
    delete_count = cur.rowcount

    conn.commit()
    conn.close()

    print(f"✅ 選手「{WRONG_NAME}」正名手術成功！")
    print(f"  - 成功將 {update_count} 筆成績轉移給「{CORRECT_NAME}」。")
    if delete_count > 0:
        print(f"  - 移除了 {delete_count} 筆多餘的重複紀錄。")

if __name__ == "__main__":
    fix_typo()
