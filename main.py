import os
from fastapi import FastAPI, Request, Query
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import sqlite3

app = FastAPI(title="游泳比賽成績查詢系統")

# 1. 取得當前檔案 (main.py) 所在的絕對目錄
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 2. 設定模板與資料庫的絕對路徑
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
DB_PATH = os.path.join(BASE_DIR, "ctsa_shoushan.sqlite")

templates = Jinja2Templates(directory=TEMPLATE_DIR)

# 資料庫連線輔助函式
def get_db_connection():
    conn = sqlite3.connect('ctsa_shoushan.sqlite')
    # 讓資料可以像 Python 字典一樣透過欄位名稱存取
    conn.row_factory = sqlite3.Row 
    return conn

# 1. 提供前端網頁的路由
@app.get("/", response_class=HTMLResponse)
async def read_index(request: Request):
    #return templates.TemplateResponse("index.html", {"request": request})
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/api/activities")
async def get_activities():
    conn = get_db_connection()
    cursor = conn.cursor()

    # 撈取所有不重複的賽事名稱與年份，並依照年份由新到舊排序
    query = """
        SELECT DISTINCT activity_year, activity_name, activity_short_name
        FROM results
        WHERE activity_name IS NOT NULL
        ORDER BY activity_year DESC, activity_name ASC
    """

    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]
# 2.1 請將這段加在 main.py 裡面，原本的 @app.get("/api/results") 之前或之後都可以
@app.get("/api/athletes")
async def get_athletes():
    conn = get_db_connection()
    cursor = conn.cursor()

    # 只要撈取「個人成績」的選手姓名，並過濾掉重複的名字，按筆畫或拼音排序
    query = """
        SELECT DISTINCT student_name
        FROM results
        WHERE event_display = '個人成績'
          AND student_name IS NOT NULL
          AND student_name != ''
        ORDER BY student_name ASC
    """

    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()

    # 將結果轉成一個單純的字串陣列回傳，例如: ["王小明", "張懿婷", "李大華"...]
    athletes = [row['student_name'] for row in rows]
    return athletes

# ==========================================
# 2. 修改：支援「賽事名稱(activity)」過濾的成績查詢 API
# ==========================================
@app.get("/api/results")
async def search_results(
    name: str = Query(None, description="選手姓名"),
    year: int = Query(None, description="賽事年份"),
    activity: str = Query(None, description="賽事名稱") # <-- 新增這個參數
):
    conn = get_db_connection()
    cursor = conn.cursor()

    # 動態組裝 SQL 查詢語句
    query = "SELECT * FROM results WHERE 1=1"
    params = []

    if name:
        query += " AND student_name LIKE ?"
        params.append(f"%{name}%")

    if year:
        query += " AND activity_year = ?"
        params.append(year)

    # <-- 新增：如果前端有傳賽事名稱來，就過濾全名或簡稱
    if activity:
        query += " AND (activity_name = ? OR activity_short_name = ?)"
        params.extend([activity, activity])

    query += " ORDER BY activity_year DESC, activity_name ASC"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    # 後端清洗資料邏輯 (切掉 Pandas 的 Name: 0 小尾巴)
    results_list = []
    for row in rows:
        item = dict(row)
        raw_result = item.get('result_text') or ""
        cleaned_result = raw_result.split('Name:')[0].strip()
        item['result_text'] = cleaned_result
        results_list.append(item)

    return results_list

# 若要直接在本地端測試，可加入這段
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
