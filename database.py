import pymysql
from pymysql.cursors import DictCursor
import os
from dotenv import load_dotenv

# โหลดค่าลับจากไฟล์ .env (ที่ GitHub มองไม่เห็น)
load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_PORT = int(os.getenv("DB_PORT", 4000)) 
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")
DB_CA = os.getenv("DB_CA")

def get_db_connection():
    try:
        conn = pymysql.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            cursorclass=DictCursor,
            ssl={"ca": DB_CA},
            autocommit=True
        )
        # ไม่ปริ้นท์แล้วเพื่อความสะอาดของ Log
        return conn
    except Exception as e:
        print("❌ DB Error:", e)
        return None