from flask import Flask
from user_routes import user_bp, mail  # ดึง mail มาจาก user_routes เพื่อ Init
from admin_routes import admin_bp
from technician_routes import technician_bp
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "KU_Super_Secret_Key_2026")

# ==========================================
# 🚀 ตั้งค่า Mail สำหรับส่ง OTP (เปลี่ยนเป็น Port 465 SSL)
# ==========================================
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 465))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'False').lower() in ('true', '1', 't')
app.config['MAIL_USE_SSL'] = os.getenv('MAIL_USE_SSL', 'True').lower() in ('true', '1', 't')
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME')

# สั่งให้ Mail ทำงานกับแอปนี้
mail.init_app(app)
# ==========================================

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