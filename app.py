from flask import Flask
from user_routes import user_bp
from admin_routes import admin_bp
from technician_routes import technician_bp

app = Flask(__name__)
app.secret_key = "KU_Super_Secret_Key_2026"  # กุญแจลับสำหรับ Session

app.register_blueprint(user_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(technician_bp)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)