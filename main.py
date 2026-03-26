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

# 修改後的 main.py
@app.get("/api/athletes")
async def get_athletes():
    conn = get_db_connection()
    cursor = conn.cursor()

    # 第一道防線：資料庫 SQL 初步過濾
    query = """
        SELECT DISTINCT student_name 
        FROM results 
        WHERE event_display != '總成績' 
          AND student_name IS NOT NULL 
          AND student_name != ''
    """
    
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()

    # 第二道防線：Python 端終極清洗
    cleaned_athletes = set()
    for row in rows:
        name = row['student_name']
        if name:
            name = name.strip()
            # 【關鍵防護】只要名字裡面有半形或全形空白，就判定為「接力隊伍字串」，直接跳過！
            # 也可以順便加上長度限制，一般姓名通常不會太長。
            if ' ' not in name and '　' not in name and len(name) > 0:
                cleaned_athletes.add(name)
                
    # 轉回列表並按照筆畫/拼音進行排序
    sorted_athletes = sorted(list(cleaned_athletes))
    
    return sorted_athletes

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
