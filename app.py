from flask import Flask, session, jsonify, request
from user_routes import user_bp
from admin_routes import admin_bp
from technician_routes import technician_bp
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta


# เพิ่มระบบส่งอีเมล OTP
from flask_mail import Mail, Message
import random

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "KU_Super_Secret_Key_2026")  # กุญแจลับสำหรับ Session

# -------------------------------
# ตั้งค่า Mail สำหรับส่ง OTP
# -------------------------------
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() in ('true', '1', 't')
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')

mail = Mail(app)
# -------------------------------

@app.route('/send_otp', methods=['POST'])
def send_otp():
    try:
        data = request.get_json()
        email = data.get('email')
        if not email:
            return jsonify({'success': False, 'message': 'Email is required'}), 400

        # Server-side validation for @ku.th email
        if not email.endswith('@ku.th'):
            return jsonify({'success': False, 'message': 'ต้องใช้อีเมลของมหาวิทยาลัยเกษตรศาสตร์ (@ku.th) เท่านั้น'}), 400

        otp = f"{random.randint(0, 9999):04d}"
        session['otp'] = otp
        session['otp_gen_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        msg = Message('Your OTP for KU-FixIT', sender=os.getenv('MAIL_USERNAME'), recipients=[email])
        msg.body = f'Your OTP is: {otp}. This OTP will expire in 2 minutes.'
        mail.send(msg)

        return jsonify({'success': True, 'message': 'OTP sent successfully'})
    except Exception as e:
        # For debugging, you might want to log the error
        print(f"Error sending OTP: {e}")
        return jsonify({'success': False, 'message': 'Failed to send OTP'}), 500

@app.route('/verify_otp', methods=['POST'])
def verify_otp():
    try:
        data = request.get_json()
        otp_from_user = data.get('otp')
        
        otp_in_session = session.get('otp')
        otp_gen_time_str = session.get('otp_gen_time')

        if not otp_in_session or not otp_gen_time_str:
            return jsonify({'success': False, 'message': 'OTP not found or expired. Please request a new one.'})

        otp_gen_time = datetime.strptime(otp_gen_time_str, "%Y-%m-%d %H:%M:%S")

        if datetime.now() > otp_gen_time + timedelta(minutes=2):
            # Clear expired OTP
            session.pop('otp', None)
            session.pop('otp_gen_time', None)
            return jsonify({'success': False, 'message': 'OTP has expired. Please request a new one.'})

        if otp_from_user == otp_in_session:
            # Clear OTP after successful verification
            session.pop('otp', None)
            session.pop('otp_gen_time', None)
            return jsonify({'success': True, 'message': 'OTP verified successfully.'})
        else:
            return jsonify({'success': False, 'message': 'Invalid OTP.'})

    except Exception as e:
        # For debugging
        print(f"Error verifying OTP: {e}")
        return jsonify({'success': False, 'message': 'An error occurred during OTP verification.'}), 500

# -------------------------------

# เพิ่มขีดจำกัดขนาดไฟล์อัปโหลดสูงสุดเป็น 16MB เพื่อรองรับรูปภาพความละเอียดสูง
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 

app.register_blueprint(user_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(technician_bp)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)