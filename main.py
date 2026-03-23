import os
from fastapi import FastAPI, Request, Query
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import sqlite3

app = FastAPI(title="游泳比賽成績查詢系統")

# 設定模板資料夾
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
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

# 2. 提供資料查詢的 API 端點
@app.get("/api/results")
async def search_results(
    name: str = Query(None, description="選手姓名"),
    year: int = Query(None, description="賽事年份")
):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 動態組裝 SQL 查詢語句 (這部分維持原樣)
    query = "SELECT * FROM results WHERE 1=1"
    params = []
    
    if name:
        query += " AND student_name LIKE ?"
        params.append(f"%{name}%")
        
    if year:
        query += " AND activity_year = ?"
        params.append(year)
        
    query += " ORDER BY activity_year DESC, activity_name ASC"
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    # --- 重點：後端清洗資料邏輯 ---
    results_list = []
    for row in rows:
        # 將 SQLite Row 轉為 Python 字典
        item = dict(row)
        
        # 取得原始的成績字串，如果為 None 則給空字串
        raw_result = item.get('result_text') or ""
        
        # 1. 執行清洗：用 split 把 " Name:" 後面的東西通通切掉
        # split會回傳一個串列，我們取第一個元素 [0]，並去除頭尾空白
        cleaned_result = raw_result.split(' Name:')[0].strip()
        
        # 2. 將清洗後的乾淨成績存回字典中
        item['result_text'] = cleaned_result
        
        # 3. 再將整理好的字典加入要回傳的串列中
        results_list.append(item)
    # ----------------------------
    
    # 回傳清洗乾淨後的資料
    return results_list
# 若要直接在本地端測試，可加入這段
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
