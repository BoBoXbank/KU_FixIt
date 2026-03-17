import base64
import os
import requests 
import io        
from PIL import Image 
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from database import get_db_connection
from werkzeug.security import generate_password_hash, check_password_hash
import datetime

user_bp = Blueprint('user', __name__)

# ==========================================
# 🚀 ระบบด่านตรวจ: บล็อค IP ที่ถูกแบนก่อนเข้าเว็บทุกหน้า
# ==========================================
@user_bp.before_app_request
def check_banned_ip():
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM banned_ips WHERE ip_address = %s", (client_ip,))
            if cursor.fetchone():
                return "<h1>🚫 Access Denied</h1><p>เครื่องของคุณถูกระงับการใช้งานอย่างถาวร (IP Banned)</p>", 403
        finally:
            conn.close()

# ==========================================
# 🚀 ฟังก์ชันเสริม: บีบอัดรูปภาพก่อนเซฟลง Database
# ==========================================
def process_and_compress_image(file):
    if not file or file.filename == '':
        return None
    try:
        img = Image.open(file)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        img.thumbnail((1080, 1080))
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='JPEG', optimize=True, quality=85)
        base64_encoded = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')
        return base64_encoded
    except Exception as e:
        print(f"Error compressing image: {e}")
        return None
# ==========================================

@user_bp.app_context_processor
def inject_user_info():
    user_info = None
    if 'user_id' in session:
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT first_name, profile_picture FROM users WHERE id = %s", (session['user_id'],))
                row = cursor.fetchone()
                if row:
                    user_info = dict(row)
                    pic = user_info.get('profile_picture')
                    if pic:
                        if isinstance(pic, bytes):
                            user_info['profile_picture'] = pic.decode('utf-8')
            finally:
                conn.close()
    return dict(current_user_info=user_info)

@user_bp.route('/logout')
def logout():
    session.clear() 
    flash('ออกจากระบบเรียบร้อย', 'info')
    return redirect(url_for('user.login'))

@user_bp.route('/')
def index():
    if 'user_id' not in session: return redirect(url_for('user.login'))
    return redirect(url_for('user.home'))

@user_bp.route('/home')
def home():
    if 'user_id' not in session: return redirect(url_for('user.login'))
    role = session.get('role', '') 
    if role == 'admin': return redirect(url_for('admin.dashboard'))
    elif role.startswith('technician_'): return redirect(url_for('technician.dashboardtech')) 
    
    conn = get_db_connection()
    stats = {'total': 0, 'pending': 0, 'ongoing': 0, 'finished': 0}
    recent_reports = []
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM reports WHERE username = %s ORDER BY id DESC", (session.get('username'),))
            reports = cursor.fetchall()
            stats['total'] = len(reports)
            stats['pending'] = len([r for r in reports if r['status'] == 'รอซ่อม'])
            stats['ongoing'] = len([r for r in reports if r['status'] == 'กำลังซ่อม'])
            stats['finished'] = len([r for r in reports if r['status'] == 'เสร็จสิ้น'])
            recent_reports = reports[:5]
        finally:
            conn.close()
    return render_template('user/home.html', stats=stats, reports=recent_reports)

@user_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password')
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()       
        building = request.form.get('building', '').strip() 
        room_number = request.form.get('room_number', '').strip()
        question = request.form.get('question')
        answer = request.form.get('answer')
        # --- เพิ่มการตรวจสอบโดเมนอีเมลตรงนี้ ---
        allowed_domains = ("@ku.th")
        if not email.lower().endswith(allowed_domains):
            flash("❌ อีเมลต้องลงท้ายด้วย @ku.th เท่านั้น", "danger")
            return redirect(url_for('user.register'))
        # ----------------------------------
        recaptcha_response = request.form.get('g-recaptcha-response')
        secret_key = os.getenv('RECAPTCHA_SECRET_KEY')
        if secret_key and recaptcha_response:
            verify_response = requests.post(
                url='https://www.google.com/recaptcha/api/siteverify',
                data={'secret': secret_key, 'response': recaptcha_response}
            )
            result = verify_response.json()
            if not result.get('success'):
                flash("กรุณายืนยันว่าคุณไม่ใช่โปรแกรมอัตโนมัติ (reCAPTCHA)", "danger")
                return redirect(url_for('user.register'))

        hashed_pw = generate_password_hash(password)
        hashed_ans = generate_password_hash(answer)
        role = 'admin' if room_number == '0000' else 'user'

        conn = get_db_connection()
        if not conn:
            flash("เชื่อมต่อฐานข้อมูลไม่ได้", "danger")
            return redirect(url_for('user.register'))

        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users WHERE username=%s", (username,))
            if cursor.fetchone():
                flash("ชื่อผู้ใช้นี้ถูกใช้แล้ว", "danger")
                return redirect(url_for('user.register'))

            cursor.execute("""
                SELECT t1.id + 1 AS next_id FROM users t1
                LEFT JOIN users t2 ON t1.id + 1 = t2.id
                WHERE t2.id IS NULL ORDER BY t1.id LIMIT 1
            """)
            id_result = cursor.fetchone()
            new_id = id_result['next_id'] if id_result and id_result['next_id'] else 1
            cursor.execute("SELECT COUNT(*) AS c FROM users")
            if cursor.fetchone()['c'] == 0: new_id = 1

            sql = """
            INSERT INTO users (id, username, password_hash, role, security_question, security_answer_hash, 
                             room_number, first_name, last_name, email, phone, building)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (new_id, username, hashed_pw, role, question, hashed_ans, 
                               room_number, first_name, last_name, email, phone, building))
            conn.commit()
            flash('สมัครสมาชิกสำเร็จ! กรุณาเข้าสู่ระบบ', 'success')
            return redirect(url_for('user.login'))
        except Exception as e:
            flash(f'บันทึกข้อมูลไม่ได้: {e}', 'danger')
        finally:
            conn.close()
    return render_template('user/register.html')

@user_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        
        conn = get_db_connection()
        if not conn:
            flash("เชื่อมต่อฐานข้อมูลไม่ได้", "danger")
            return redirect(url_for('user.login'))
            
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
            user = cursor.fetchone()
            
            if user:
                lockout_until = user.get('lockout_until')
                if lockout_until and lockout_until > datetime.datetime.now():
                    time_left = (lockout_until - datetime.datetime.now()).seconds // 60 + 1
                    flash(f'🔒 บัญชีถูกล็อคชั่วคราว กรุณารออีก {time_left} นาที', 'danger')
                    return redirect(url_for('user.login'))

                if check_password_hash(user['password_hash'], password):
                    # 🚀 ดึง IP เข้าสู่ระบบ และเซฟลงตาราง user_ips
                    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()
                    try:
                        cursor.execute("""
                            INSERT INTO user_ips (username, ip_address) 
                            VALUES (%s, %s) 
                            ON DUPLICATE KEY UPDATE last_login = CURRENT_TIMESTAMP
                        """, (user['username'], client_ip))
                        cursor.execute("UPDATE users SET failed_attempts = 0, lockout_until = NULL WHERE id = %s", (user['id'],))
                        conn.commit()
                    except Exception as e:
                        print("Error saving login IP:", e)

                    session['user_id'] = user['id']
                    session['role'] = user['role']
                    session['username'] = user['username']
                    
                    if user['role'] == 'admin': return redirect(url_for('admin.dashboard'))
                    elif user['role'].startswith('technician_'): return redirect(url_for('technician.dashboardtech'))
                    return redirect(url_for('user.home'))
                else:
                    failed_attempts = (user.get('failed_attempts') or 0) + 1
                    try:
                        if failed_attempts >= 10:
                            lockout_time = datetime.datetime.now() + datetime.timedelta(minutes=2)
                            cursor.execute("UPDATE users SET failed_attempts = %s, lockout_until = %s WHERE id = %s", (failed_attempts, lockout_time, user['id']))
                            conn.commit()
                            flash('คุณใส่รหัสผิดครบ 10 ครั้ง บัญชีถูกล็อค 2 นาทีเพื่อความปลอดภัย', 'danger')
                        else:
                            cursor.execute("UPDATE users SET failed_attempts = %s WHERE id = %s", (failed_attempts, user['id']))
                            conn.commit()
                            flash(f'ชื่อผู้ใช้หรือรหัสผ่านผิด (เหลือโอกาสอีก {10 - failed_attempts} ครั้ง)', 'danger')
                    except Exception as e:
                         flash('ชื่อผู้ใช้หรือรหัสผ่านผิด', 'danger')
            else:
                flash('ชื่อผู้ใช้หรือรหัสผ่านผิด', 'danger')
                
        finally:
            conn.close()
            
    return render_template('user/login.html')

@user_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        username = request.form['username'].strip()
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
                user = cursor.fetchone()
                if user:
                    session['reset_id'] = user['id']
                    session['question'] = user['security_question']
                    return redirect(url_for('user.reset_password'))
                else:
                    flash('ไม่พบชื่อผู้ใช้นี้', 'danger')
            finally:
                conn.close()
    return render_template('user/forgot_password.html')

@user_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if 'reset_id' not in session: return redirect(url_for('user.forgot_password'))
    if request.method == 'POST':
        answer = request.form['answer']
        new_pass = request.form['new_password']
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT security_answer_hash FROM users WHERE id = %s", (session['reset_id'],))
                user = cursor.fetchone()
                if user and check_password_hash(user['security_answer_hash'], answer):
                    new_hash = generate_password_hash(new_pass)
                    try:
                        cursor.execute("UPDATE users SET password_hash = %s, failed_attempts = 0, lockout_until = NULL WHERE id = %s", (new_hash, session['reset_id']))
                    except Exception:
                        cursor.execute("UPDATE users SET password_hash = %s WHERE id = %s", (new_hash, session['reset_id']))
                    conn.commit()
                    session.pop('reset_id', None)
                    flash('เปลี่ยนรหัสผ่านสำเร็จ! ล็อกอินได้เลย', 'success')
                    return redirect(url_for('user.login'))
                else:
                    flash('คำตอบไม่ถูกต้อง', 'danger')
            finally:
                conn.close()
    return render_template('user/reset_password.html', question=session.get('question'))

@user_bp.route('/report', methods=['GET', 'POST'])
def report():
    if 'user_id' not in session: return redirect(url_for('user.login'))

    if request.method == 'POST':
        title = request.form.get('title')
        building = request.form.get('location_building')
        room = request.form.get('location_room')
        detail = request.form.get('detail')
        phone = request.form.get('phone')
        location = f"{building} ห้อง {room}"
        current_username = session.get('username')

        # 🚀 ดึง IP ผู้ใช้เพื่อบันทึกไว้
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()

        time_type = request.form.get('time_type')
        if time_type == 'anytime':
            repair_time_str = "สะดวกทุกวัน และทุกช่วงเวลา"
        else:
            days = request.form.getlist('days')
            times = request.form.getlist('times')
            note = request.form.get('time_note', '').strip()
            days_str = ", ".join(days) if days else "ไม่ได้ระบุวัน"
            times_str = ", ".join(times) if times else "ไม่ได้ระบุช่วงเวลา"
            repair_time_str = f"วัน: {days_str} | เวลา: {times_str}"
            if note:
                repair_time_str += f" | หมายเหตุ: {note}"

        created_at = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        image = request.files.get('image')
        image_base64 = None
        if image and image.filename != '':
            image_base64 = process_and_compress_image(image)

        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor()
                try:
                    sql = """
                        INSERT INTO reports (title, detail, location, building, repair_time, phone, username, image_data, status, created_at, ip_address) 
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'รอซ่อม', %s, %s)
                    """
                    cursor.execute(sql, (
                        title, detail, location, building, repair_time_str, phone, current_username, image_base64, created_at, client_ip
                    ))
                except Exception:
                    # กรณีฐานข้อมูลยังไม่ได้เพิ่มคอลัมน์ ip_address
                    sql = """
                        INSERT INTO reports (title, detail, location, building, repair_time, phone, username, image_data, status, created_at) 
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'รอซ่อม', %s)
                    """
                    cursor.execute(sql, (
                        title, detail, location, building, repair_time_str, phone, current_username, image_base64, created_at
                    ))
                conn.commit()
                flash('ส่งเรื่องแจ้งซ่อมเรียบร้อย', 'success')
                return redirect(url_for('user.home'))
            finally:
                conn.close()

    return render_template('user/report_form.html')

@user_bp.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session: return redirect(url_for('user.login'))
    conn = get_db_connection()
    if request.method == 'POST':
        image = request.files.get('profile_picture')
        if image and image.filename != '':
            image_base64 = process_and_compress_image(image)
            if image_base64 and conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute("UPDATE users SET profile_picture = %s WHERE id = %s", (image_base64, session['user_id']))
                    conn.commit()
                    flash('เปลี่ยนรูปโปรไฟล์สำเร็จ!', 'success')
                    return redirect(url_for('user.profile'))
                finally:
                    conn.close()
                    conn = get_db_connection()

    user_data = None
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE id = %s", (session['user_id'],))
            user_data = cursor.fetchone()
        finally:
            conn.close()
    return render_template('user/profile.html', user=user_data)

@user_bp.route('/record_user')
def record_user():
    if 'user_id' not in session: return redirect(url_for('user.login'))
    conn = get_db_connection()
    reports = []
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM reports WHERE username = %s ORDER BY id DESC", (session.get('username'),))
            reports = cursor.fetchall()
        finally:
            conn.close()
    return render_template('user/record_user.html', reports=reports)

@user_bp.route('/edit_report/<int:id>', methods=['GET', 'POST'])
def edit_report(id):
    if 'user_id' not in session: return redirect(url_for('user.login'))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM reports WHERE id = %s AND username = %s", (id, session.get('username')))
    report = cursor.fetchone()
    
    if not report:
        flash('ไม่พบข้อมูลแจ้งซ่อม', 'danger')
        return redirect(url_for('user.record_user'))
    if report['status'] != 'รอซ่อม' and report['status'] != 'รอดำเนินการ':
        flash('ไม่สามารถแก้ไขได้เนื่องจากช่างรับงานไปแล้ว', 'warning')
        return redirect(url_for('user.record_user'))

    if request.method == 'POST':
        title = request.form.get('title')
        building = request.form.get('location_building')
        room = request.form.get('location_room')
        detail = request.form.get('detail')
        phone = request.form.get('phone')
        location = f"{building} ห้อง {room}"
        
        time_type = request.form.get('time_type')
        if time_type == 'anytime':
            repair_time_str = "สะดวกทุกวัน และทุกช่วงเวลา"
        else:
            days = request.form.getlist('days')
            times = request.form.getlist('times')
            note = request.form.get('time_note', '').strip()
            days_str = ", ".join(days) if days else "ไม่ได้ระบุวัน"
            times_str = ", ".join(times) if times else "ไม่ได้ระบุช่วงเวลา"
            repair_time_str = f"วัน: {days_str} | เวลา: {times_str}"
            if note: repair_time_str += f" | หมายเหตุ: {note}"

        image = request.files.get('image')
        if image and image.filename != '':
            image_base64 = process_and_compress_image(image)
            cursor.execute("""
                UPDATE reports SET title=%s, detail=%s, location=%s, building=%s, 
                repair_time=%s, phone=%s, image_data=%s WHERE id=%s
            """, (title, detail, location, building, repair_time_str, phone, image_base64, id))
        else:
            cursor.execute("""
                UPDATE reports SET title=%s, detail=%s, location=%s, building=%s, 
                repair_time=%s, phone=%s WHERE id=%s
            """, (title, detail, location, building, repair_time_str, phone, id))
            
        conn.commit()
        conn.close()
        flash('แก้ไขข้อมูลแจ้งซ่อมเรียบร้อยแล้ว', 'success')
        return redirect(url_for('user.home'))

    conn.close()
    return render_template('user/edit_report.html', item=report)

# =====================================================
# OTP EMAIL SYSTEM 
# =====================================================

from flask import request, jsonify, current_app
from flask_mail import Mail, Message
import random
import time

mail = Mail()

# เก็บ OTP ชั่วคราว
otp_storage = {}
otp_expire_time = {}

@user_bp.record_once
def setup_mail(state):
    app = state.app
    mail.init_app(app)

@user_bp.route('/send_otp', methods=['POST'])
def send_otp():

    data = request.get_json()
    email = data.get("email")

    if not email:
        return jsonify({"status": "error", "message": "Email required"}), 400

    # สร้าง OTP 4 หลัก
    otp = random.randint(1000, 9999)

    # เก็บ OTP
    otp_storage[email] = str(otp)

    # ตั้งเวลา OTP หมดอายุ 2 นาที
    otp_expire_time[email] = time.time() + 120

    try:

        msg = Message(
            subject="KU FixIt OTP Verification",
            sender=current_app.config['MAIL_USERNAME'],
            recipients=[email]
        )

        msg.body = f"""
KU FixIt Email Verification

Your OTP Code: {otp}

This code will expire in 2 minutes.

If you did not request this code please ignore this email.
"""

        mail.send(msg)

        return jsonify({"status": "success"})

    except Exception as e:

        print("OTP MAIL ERROR:", e)

        return jsonify({"status": "error", "message": "Failed to send email"})
    
    