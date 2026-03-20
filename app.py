from flask import Flask
from user_routes import user_bp  # 🚀 เอา mail ออกจากบรรทัดนี้แล้ว
from admin_routes import admin_bp
from technician_routes import technician_bp
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "KU_Super_Secret_Key_2026")

# ==========================================
# 🚀 Custom Filter สำหรับแปลงเวลาเป็น GMT+7
# ==========================================
@app.template_filter('thaitime')
def thaitime_filter(dt):
    if not dt:
        return ""
    if isinstance(dt, str):
        try:
            dt = datetime.strptime(dt, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            return dt
    return dt.strftime('%d/%m/%Y %H:%M')
# ==========================================

# เพิ่มขีดจำกัดขนาดไฟล์อัปโหลดสูงสุดเป็น 16MB
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 

app.register_blueprint(user_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(technician_bp)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)