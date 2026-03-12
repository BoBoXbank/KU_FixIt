import base64
import os
import requests 
import io        
from PIL import Image 
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from database import get_db_connection
from werkzeug.security import generate_password_hash, check_password_hash
import datetime # 🚀 นำเข้าเพื่อใช้วันที่ปัจจุบัน

user_bp = Blueprint('user', __name__)

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
        print(f"❌ Error compressing image: {e}")
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

        recaptcha_response = request.form.get('g-recaptcha-response')
        secret_key = os.getenv('RECAPTCHA_SECRET_KEY')
        if secret_key and recaptcha_response:
            verify_response = requests.post(
                url='https://www.google.com/recaptcha/api/siteverify',
                data={'secret': secret_key, 'response': recaptcha_response}
            )
            result = verify_response.json()
            if not result.get('success'):
                flash("❌ กรุณายืนยันว่าคุณไม่ใช่โปรแกรมอัตโนมัติ (reCAPTCHA)", "danger")
                return redirect(url_for('user.register'))

        hashed_pw = generate_password_hash(password)
        hashed_ans = generate_password_hash(answer)
        role = 'admin' if room_number == '0000' else 'user'

        conn = get_db_connection()
        if not conn:
            flash("❌ เชื่อมต่อฐานข้อมูลไม่ได้", "danger")
            return redirect(url_for('user.register'))

        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users WHERE username=%s", (username,))
            if cursor.fetchone():
                flash("❌ ชื่อผู้ใช้นี้ถูกใช้แล้ว", "danger")
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
            flash('✅ สมัครสมาชิกสำเร็จ! กรุณาเข้าสู่ระบบ', 'success')
            return redirect(url_for('user.login'))
        except Exception as e:
            flash(f'❌ บันทึกข้อมูลไม่ได้: {e}', 'danger')
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
            flash("❌ เชื่อมต่อฐานข้อมูลไม่ได้", "danger")
            return redirect(url_for('user.login'))
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
            user = cursor.fetchone()
            if user and check_password_hash(user['password_hash'], password):
                session['user_id'] = user['id']
                session['role'] = user['role']
                session['username'] = user['username']
                if user['role'] == 'admin': return redirect(url_for('admin.dashboard'))
                elif user['role'].startswith('technician_'): return redirect(url_for('technician.dashboardtech'))
                return redirect(url_for('user.home'))
            else:
                flash('❌ ชื่อผู้ใช้หรือรหัสผ่านผิด', 'danger')
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
                    flash('❌ ไม่พบชื่อผู้ใช้นี้', 'danger')
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
                    cursor.execute("UPDATE users SET password_hash = %s WHERE id = %s", (new_hash, session['reset_id']))
                    conn.commit()
                    session.pop('reset_id', None)
                    flash('✅ เปลี่ยนรหัสผ่านสำเร็จ! ล็อกอินได้เลย', 'success')
                    return redirect(url_for('user.login'))
                else:
                    flash('❌ คำตอบไม่ถูกต้อง', 'danger')
            finally:
                conn.close()
    return render_template('user/reset_password.html', question=session.get('question'))

# ---------------- REPORT (แจ้งซ่อมโฉมใหม่) ----------------
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

        # 🚀 ประมวลผล "เวลาที่สะดวกเข้าซ่อม"
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

        # 🚀 สร้างเวลาแจ้งซ่อมปัจจุบัน (ของจริง)
        created_at = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        image = request.files.get('image')
        image_base64 = None
        if image and image.filename != '':
            image_base64 = process_and_compress_image(image)

        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor()
                sql = """
                    INSERT INTO reports (title, detail, location, building, repair_time, phone, username, image_data, status, created_at) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'รอซ่อม', %s)
                """
                cursor.execute(sql, (
                    title, detail, location, building, repair_time_str, phone, current_username, image_base64, created_at
                ))
                conn.commit()
                flash('✅ ส่งเรื่องแจ้งซ่อมเรียบร้อย', 'success')
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
                    flash('✅ เปลี่ยนรูปโปรไฟล์สำเร็จ!', 'success')
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
        flash('❌ ไม่พบข้อมูลแจ้งซ่อม', 'danger')
        return redirect(url_for('user.record_user'))
    if report['status'] != 'รอซ่อม' and report['status'] != 'รอดำเนินการ':
        flash('⚠️ ไม่สามารถแก้ไขได้เนื่องจากช่างรับงานไปแล้ว', 'warning')
        return redirect(url_for('user.record_user'))

    if request.method == 'POST':
        title = request.form.get('title')
        building = request.form.get('location_building')
        room = request.form.get('location_room')
        detail = request.form.get('detail')
        phone = request.form.get('phone')
        location = f"{building} ห้อง {room}"
        
        # 🚀 ประมวลผล "เวลาที่สะดวกเข้าซ่อม" ใหม่ตอนแก้ไข
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
        flash('✅ แก้ไขข้อมูลแจ้งซ่อมเรียบร้อยแล้ว', 'success')
        return redirect(url_for('user.home'))

    conn.close()
    return render_template('user/edit_report.html', item=report)