from flask import Flask
from user_routes import user_bp
from admin_routes import admin_bp
from technician_routes import technician_bp

app = Flask(__name__)
app.secret_key = "KU_Super_Secret_Key_2026"  # กุญแจลับสำหรับ Session

# เพิ่มขีดจำกัดขนาดไฟล์อัปโหลดสูงสุดเป็น 16MB เพื่อรองรับรูปภาพความละเอียดสูง
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 

app.register_blueprint(user_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(technician_bp)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)