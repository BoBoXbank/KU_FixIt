import pymysql
from pymysql.cursors import DictCursor
import os
from dotenv import load_dotenv

# ==============================================================================
# ส่วนที่ 1: การโหลดตัวแปรแวดล้อม (ENVIRONMENT VARIABLES)
# หน้าที่: โหลดค่าความลับและการตั้งค่าจากไฟล์ .env เพื่อความปลอดภัย (ไม่นำขึ้น GitHub)
# ==============================================================================
load_dotenv()

# ==============================================================================
# ส่วนที่ 2: การตั้งค่าตัวแปรเชื่อมต่อฐานข้อมูล (DATABASE CONFIGURATION)
# หน้าที่: ดึงค่าการเชื่อมต่อฐานข้อมูลจากตัวแปรแวดล้อมมาเก็บไว้เตรียมใช้งาน
# ==============================================================================
DB_HOST = os.getenv("DB_HOST")
DB_PORT = int(os.getenv("DB_PORT", 4000)) 
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
charset = 'utf8mb4',
DB_NAME = os.getenv("DB_NAME")
DB_CA = os.getenv("DB_CA")

# ==============================================================================
# ส่วนที่ 3: ฟังก์ชันเชื่อมต่อฐานข้อมูล (DATABASE CONNECTION FUNCTION)
# หน้าที่: สร้างและส่งคืนการเชื่อมต่อ (Connection) ไปยังฐานข้อมูล
# การตั้งค่าเพิ่มเติม: ใช้ DictCursor เพื่อให้ข้อมูลที่ดึงออกมาเป็นรูปแบบ Dictionary (อ่านง่ายขึ้น)
# ==============================================================================
def get_db_connection():
    try:
        conn = pymysql.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            charset= 'utf8mb4',
            cursorclass=DictCursor,
            ssl={"ca": DB_CA},
            autocommit=True
        )
        # ไม่ปริ้นท์ข้อความแจ้งเตือนเมื่อเชื่อมต่อสำเร็จ เพื่อความสะอาดของ Log
        return conn
    except Exception as e:
        print("DB Error:", e)
        return None