import base64
import os
import requests  # 🚀 เพิ่มไลบรารีนี้สำหรับคุยกับ API ของ Google
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from database import get_db_connection
from werkzeug.security import generate_password_hash, check_password_hash

user_bp = Blueprint('user', __name__)

# ---------------- LOGOUT (เพิ่มอันนี้เพื่อแก้ปัญหาเอ๋อเวลาเปลี่ยนคนใช้) ----------------
@user_bp.route('/logout')
def logout():
    session.clear() # ล้างค่าทั้งหมด
    flash('ออกจากระบบเรียบร้อย', 'info')
    return redirect(url_for('user.login'))

# ---------------- INDEX & HOME (บังคับเข้า Login หรือ Report) ----------------
@user_bp.route('/')
def index():
    # ถ้ายังไม่ล็อกอิน ให้ไปหน้า Login ทันที
    if 'user_id' not in session:
        return redirect(url_for('user.login'))
    return redirect(url_for('user.home'))

@user_bp.route('/home')
def home():
    if 'user_id' not in session:
        return redirect(url_for('user.login'))
    
    # ดึง role มาเช็ค
    role = session.get('role', '') # ใส่ '' กันเหนียวกรณีไม่มีค่า
    
    # 1. ถ้าเป็นแอดมิน ไปหน้าแอดมิน
    if role == 'admin':
        return redirect(url_for('admin.dashboard'))
        
    # 2. ✅ ถ้า role ขึ้นต้นด้วยคำว่า 'technician_' ให้ไปหน้าช่าง ✅
    elif role.startswith('technician_'): 
        return redirect(url_for('technician.dashboardtech')) 
    
    # 3. นอกนั้น (User ทั่วไป) ค่อยดึงข้อมูลของ User มาแสดง
    conn = get_db_connection()
    stats = {'total': 0, 'pending': 0, 'ongoing': 0, 'finished': 0}
    recent_reports = []
    
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM reports WHERE username = %s ORDER BY id DESC", (session.get('username'),))
        reports = cursor.fetchall()
        
        stats['total'] = len(reports)
        stats['pending'] = len([r for r in reports if r['status'] == 'รอซ่อม'])
        stats['ongoing'] = len([r for r in reports if r['status'] == 'กำลังซ่อม'])
        stats['finished'] = len([r for r in reports if r['status'] == 'เสร็จสิ้น'])
        recent_reports = reports[:5]
        conn.close()

    return render_template('user/home.html', stats=stats, reports=recent_reports)

# ---------------- REGISTER (ฉบับแก้ไขสมบูรณ์สำหรับก๊อปวาง) ----------------
@user_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password')
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        email = request.form.get('email', '').strip()
        
        # ใช้ .get เพื่อป้องกัน KeyError หากหน้า HTML ส่งค่ามาไม่ครบ
        phone = request.form.get('phone', '').strip()       
        building = request.form.get('building', '').strip() 
        room_number = request.form.get('room_number', '').strip()
        
        question = request.form.get('question')
        answer = request.form.get('answer')

        # 🤖 === ระบบเช็ค Google reCAPTCHA v2 === 🤖
        recaptcha_response = request.form.get('g-recaptcha-response')
        secret_key = os.getenv('RECAPTCHA_SECRET_KEY')

        verify_response = requests.post(
            url='https://www.google.com/recaptcha/api/siteverify',
            data={'secret': secret_key, 'response': recaptcha_response}
        )
        result = verify_response.json()

        if not result.get('success'):
            flash("❌ กรุณายืนยันว่าคุณไม่ใช่โปรแกรมอัตโนมัติ (reCAPTCHA)", "danger")
            return redirect(url_for('user.register'))
        # 🤖 ================================== 🤖

        # 2. เข้ารหัสข้อมูลความปลอดภัย
        hashed_pw = generate_password_hash(password)
        hashed_ans = generate_password_hash(answer)

        # 🚀 ทริค: กำหนดสิทธิ์แอดมิน (ถ้ากรอก 0000)
        role = 'admin' if room_number == '0000' else 'user'

        conn = get_db_connection()
        if not conn:
            flash("❌ เชื่อมต่อฐานข้อมูลไม่ได้", "danger")
            return redirect(url_for('user.register'))

        try:
            cursor = conn.cursor()

            # 3. ตรวจสอบ Username ซ้ำ
            cursor.execute("SELECT id FROM users WHERE username=%s", (username,))
            if cursor.fetchone():
                flash("❌ ชื่อผู้ใช้นี้ถูกใช้แล้ว", "danger")
                return redirect(url_for('user.register'))

            # 4. ค้นหา ID ว่างตัวแรกสำหรับ User ใหม่
            cursor.execute("""
                SELECT t1.id + 1 AS next_id
                FROM users t1
                LEFT JOIN users t2 ON t1.id + 1 = t2.id
                WHERE t2.id IS NULL
                ORDER BY t1.id
                LIMIT 1
            """)
            id_result = cursor.fetchone()
            new_id = id_result['next_id'] if id_result and id_result['next_id'] else 1

            # กรณีฐานข้อมูลยังว่างเปล่า
            cursor.execute("SELECT COUNT(*) AS c FROM users")
            if cursor.fetchone()['c'] == 0:
                new_id = 1

            # 5. บันทึกข้อมูลลงฐานข้อมูล (รวม 12 คอลัมน์ตามโครงสร้างล่าสุด)
            sql = """
            INSERT INTO users (id, username, password_hash, role, security_question, security_answer_hash, 
                             room_number, first_name, last_name, email, phone, building)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (new_id, username, hashed_pw, role, question, hashed_ans, 
                               room_number, first_name, last_name, email, phone, building))
            
            conn.commit() # มั่นใจว่ามีการบันทึกข้อมูล
            flash('✅ สมัครสมาชิกสำเร็จ! กรุณาเข้าสู่ระบบ', 'success')
            return redirect(url_for('user.login'))

        except Exception as e:
            flash(f'❌ บันทึกข้อมูลไม่ได้: {e}', 'danger')
        finally:
            cursor.close()
            conn.close()

    return render_template('user/register.html')

# ---------------- LOGIN ----------------
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

                # ถ้าเป็นแอดมินให้ไปหน้าแอดมิน ถ้าทั่วไปให้ไปหน้าแจ้งซ่อม
                if user['role'] == 'admin':
                    return redirect(url_for('admin.dashboard'))
                elif user['role'].startswith('technician_'): # ใช้ startswith เพื่อครอบคลุมทุกแผนกช่าง
                    return redirect(url_for('technician.dashboardtech'))
                return redirect(url_for('user.home'))
            else:
                flash('❌ ชื่อผู้ใช้หรือรหัสผ่านผิด', 'danger')
        finally:
            conn.close()

    return render_template('user/login.html')

# ---------------- FORGOT PASSWORD ----------------
@user_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        username = request.form['username'].strip()
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            user = cursor.fetchone()
            conn.close()
            
            if user:
                session['reset_id'] = user['id']
                session['question'] = user['security_question']
                return redirect(url_for('user.reset_password'))
            else:
                flash('❌ ไม่พบชื่อผู้ใช้นี้', 'danger')
    return render_template('user/forgot_password.html')

# ---------------- RESET PASSWORD ----------------
@user_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if 'reset_id' not in session: return redirect(url_for('user.forgot_password'))
    
    if request.method == 'POST':
        answer = request.form['answer']
        new_pass = request.form['new_password']
        
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT security_answer_hash FROM users WHERE id = %s", (session['reset_id'],))
            user = cursor.fetchone()
            
            if user and check_password_hash(user['security_answer_hash'], answer):
                new_hash = generate_password_hash(new_pass)
                cursor.execute("UPDATE users SET password_hash = %s WHERE id = %s", (new_hash, session['reset_id']))
                conn.commit()
                conn.close()
                session.pop('reset_id', None)
                flash('✅ เปลี่ยนรหัสผ่านสำเร็จ! ล็อกอินได้เลย', 'success')
                return redirect(url_for('user.login'))
            else:
                conn.close()
                flash('❌ คำตอบไม่ถูกต้อง', 'danger')
                
    return render_template('user/reset_password.html', question=session.get('question'))


##----------report-----------------
@user_bp.route('/report', methods=['GET', 'POST'])
def report():
    if 'user_id' not in session:
        return redirect(url_for('user.login'))

    if request.method == 'POST':
        title = request.form.get('title')
        building = request.form.get('location_building')
        room = request.form.get('location_room')
        detail = request.form.get('detail')
        repair_time = request.form.get('repair_time')
        phone = request.form.get('phone')
        
        # รวมสถานที่เพื่อเก็บลงคอลัมน์ location เดิม
        location = f"{building} ห้อง {room}"
        
        # ดึง username จาก session มาบันทึกลงตาราง reports
        current_username = session.get('username')

        image = request.files.get('image')
        image_base64 = None
        if image and image.filename != '':
            image_base64 = base64.b64encode(image.read()).decode('utf-8')

        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            
            # ✅ แก้ไขตรงนี้: เพิ่ม status เข้าไป และบังคับให้เป็น 'รอซ่อม'
            sql = """
                INSERT INTO reports (title, detail, location, building, repair_time, phone, username, image_data, status) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'รอซ่อม')
            """
            
            # ส่งค่าให้ตรงกับจำนวน %s (8 ตัว)
            cursor.execute(sql, (
                title,          # ประเภทปัญหา
                detail,         # รายละเอียด
                location,       # สถานที่ (อาคาร + ห้อง)
                building,       # อาคาร
                repair_time,    # วันเวลาที่สะดวก
                phone,          # เบอร์โทร
                current_username, # ชื่อผู้ใช้จาก session
                image_base64    # รูปภาพ
            ))
            
            conn.commit()
            conn.close()
            flash('✅ ส่งเรื่องแจ้งซ่อมเรียบร้อย', 'success')
            return redirect(url_for('user.home'))

    return render_template('user/report_form.html')

# ---------------- PROFILE ----------------
@user_bp.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('user.login'))
        
    conn = get_db_connection()
    user_data = None
    if conn:
        cursor = conn.cursor()
        # ดึงข้อมูลตาม user_id ที่เก็บไว้ใน session
        cursor.execute("SELECT * FROM users WHERE id = %s", (session['user_id'],))
        user_data = cursor.fetchone()
        conn.close()
        
    return render_template('user/profile.html', user=user_data)


##---------------- RECORD (ประวัติแจ้งซ่อมของ User คนนั้นๆ) ----------------
@user_bp.route('/record_user')
def record_user():
    if 'user_id' not in session:
        return redirect(url_for('user.login'))
        
    conn = get_db_connection()
    reports = []
    if conn:
        cursor = conn.cursor()
        # ดึงประวัติเฉพาะของ User คนนั้นๆ
        cursor.execute("SELECT * FROM reports WHERE username = %s ORDER BY id DESC", (session.get('username'),))
        reports = cursor.fetchall()
        conn.close()
    return render_template('user/record_user.html', reports=reports)