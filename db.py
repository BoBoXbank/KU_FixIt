import pymysql
from pymysql.cursors import DictCursor

# 🔹 ใส่ข้อมูล Cloud DB ของคุณตรงนี้
DB_HOST = "your-host"
DB_USER = "appuser"
DB_PASSWORD = "12345678"
DB_NAME = "test"

def get_connection():
    try:
        connection = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            cursorclass=DictCursor,
            autocommit=True
        )
        print("✅ เชื่อมต่อฐานข้อมูลสำเร็จ")
        return connection
    except Exception as e:
        print("❌ เชื่อมต่อฐานข้อมูลไม่สำเร็จ:", e)
        return None