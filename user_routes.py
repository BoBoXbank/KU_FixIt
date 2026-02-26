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

# ---------------- HOME ----------------
@user_bp.route('/')
def home():
    return render_template('user/home.html')

# ---------------- REGISTER ----------------
@user_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # รับข้อมูลจากฟอร์มให้ครบตามหน้า UI ใหม่
        username = request.form['username'].strip()
        password = request.form['password']
        room_number = request.form['room_number'].strip()
        first_name = request.form['first_name'].strip()
        last_name = request.form['last_name'].strip()
        email = request.form['email'].strip()
        question = request.form['question']
        answer = request.form['answer']

        # 🤖 === ระบบเช็ค Google reCAPTCHA v2 === 🤖
        recaptcha_response = request.form.get('g-recaptcha-response')
        secret_key = os.getenv('RECAPTCHA_SECRET_KEY') # ดึงคีย์ลับจากไฟล์ .env

        # ส่งรหัสไปถาม Google ว่าคนนี้ติ๊กถูกจริงไหม
        verify_response = requests.post(
            url='https://www.google.com/recaptcha/api/siteverify',
            data={'secret': secret_key, 'response': recaptcha_response}
        )
        result = verify_response.json()

        # ถ้า Google บอกว่าไม่ใช่คน หรือไม่ได้ติ๊กกล่อง ให้เด้งกลับทันที
        if not result.get('success'):
            flash("❌ กรุณายืนยันว่าคุณไม่ใช่โปรแกรมอัตโนมัติ (I'm not a robot)", "danger")
            return redirect(url_for('user.register'))
        # 🤖 ================================== 🤖

        # เข้ารหัสผ่านและคำตอบ
        hashed_pw = generate_password_hash(password)
        hashed_ans = generate_password_hash(answer)

        # 🚀 ทริค: กำหนดสิทธิ์ ถ้ากรอก 0000 ให้เป็นช่าง (admin) นอกนั้นเป็น user
        role = 'admin' if room_number == '0000' else 'user'

        conn = get_db_connection()
        if not conn:
            flash("เชื่อมต่อฐานข้อมูลไม่ได้", "danger")
            return redirect(url_for('user.register'))

        try:
            cursor = conn.cursor()

            # เช็ค username ซ้ำก่อน
            cursor.execute("SELECT id FROM users WHERE username=%s", (username,))
            if cursor.fetchone():
                flash("❌ ชื่อผู้ใช้นี้ถูกใช้แล้ว", "danger")
                return redirect(url_for('user.register'))

            # หา ID ว่างตัวแรกให้ User ใหม่
            cursor.execute("""
                SELECT t1.id + 1 AS next_id
                FROM users t1
                LEFT JOIN users t2 ON t1.id + 1 = t2.id
                WHERE t2.id IS NULL
                ORDER BY t1.id
                LIMIT 1
            """)
            result = cursor.fetchone()

            if result and result['next_id']:
                new_id = result['next_id']
            else:
                new_id = 1

            cursor.execute("SELECT COUNT(*) AS c FROM users")
            if cursor.fetchone()['c'] == 0:
                new_id = 1

            # 🚀 เพิ่มคอลัมน์ใหม่ๆ ลงในคำสั่ง INSERT
            sql = """
            INSERT INTO users (id, username, password_hash, role, security_question, security_answer_hash, room_number, first_name, last_name, email)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (new_id, username, hashed_pw, role, question, hashed_ans, room_number, first_name, last_name, email))

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

# ---------------- REPORT ----------------
@user_bp.route('/report', methods=['GET', 'POST'])
def report():
    if request.method == 'POST':
        title = request.form['title']
        location = request.form['location']
        detail = request.form['detail']

        # 📸 จัดการไฟล์รูปภาพ (แปลงเป็น Base64)
        image = request.files.get('image')
        image_base64 = None
        
        if image and image.filename != '':
            # อ่านไฟล์รูปแล้วแปลงเป็นตัวอักษร Base64 ยาวๆ
            image_base64 = base64.b64encode(image.read()).decode('utf-8')

        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()

            # หา id ว่างตัวแรก
            cursor.execute("""
                SELECT t1.id + 1 AS next_id
                FROM reports t1
                LEFT JOIN reports t2 ON t1.id + 1 = t2.id
                WHERE t2.id IS NULL
                ORDER BY t1.id
                LIMIT 1
            """)
            result = cursor.fetchone()

            if result and result['next_id']:
                new_id = result['next_id']
            else:
                new_id = 1

            # กรณีตารางว่าง
            cursor.execute("SELECT COUNT(*) AS c FROM reports")
            if cursor.fetchone()['c'] == 0:
                new_id = 1

            # 🚀 insert ด้วย id ที่หาได้ พร้อมบันทึกข้อมูลรูป (image_data)
            sql = "INSERT INTO reports (id, title, location, detail, image_data) VALUES (%s, %s, %s, %s, %s)"
            cursor.execute(sql, (new_id, title, location, detail, image_base64))

            conn.commit()
            conn.close()

            flash('✅ ส่งเรื่องและแนบรูปภาพเรียบร้อย', 'success')
            return redirect(url_for('user.home'))

    return render_template('user/report_form.html')