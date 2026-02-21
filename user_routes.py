from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from database import get_db_connection
from werkzeug.security import generate_password_hash, check_password_hash

user_bp = Blueprint('user', __name__)

# ---------------- HOME ----------------
@user_bp.route('/')
def home():
    return render_template('user/home.html')

# ---------------- REGISTER ----------------
@user_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        question = request.form['question']
        answer = request.form['answer']

        hashed_pw = generate_password_hash(password)
        hashed_ans = generate_password_hash(answer)

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

            # 🚀 ทริค: หา ID ว่างตัวแรกให้ User ใหม่
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

            # กรณีตารางว่าง
            cursor.execute("SELECT COUNT(*) AS c FROM users")
            if cursor.fetchone()['c'] == 0:
                new_id = 1

            sql = """
            INSERT INTO users (id, username, password_hash, security_question, security_answer_hash)
            VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (new_id, username, hashed_pw, question, hashed_ans))
            # ถ้าไม่ได้ใช้ autocommit=True ต้องใส่ conn.commit() ด้วย

            flash('✅ สมัครสมาชิกสำเร็จ!', 'success')
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
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        if not conn:
            flash("Database error", "danger")
            return redirect(url_for('user.login'))

        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
            user = cursor.fetchone()

        finally:
            cursor.close()
            conn.close()

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['role'] = user['role']
            session['username'] = user['username']

            if user['role'] == 'admin':
                return redirect(url_for('admin.dashboard'))
            return redirect(url_for('user.home'))

        flash('❌ ชื่อผู้ใช้หรือรหัสผ่านผิด', 'danger')

    return render_template('user/login.html')


# ---------------- FORGOT PASSWORD (เพิ่มกลับมา) ----------------
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

# ---------------- RESET PASSWORD (เพิ่มกลับมา) ----------------
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

            # insert ด้วย id ที่หาได้
            sql = "INSERT INTO reports (id, title, location, detail) VALUES (%s, %s, %s, %s)"
            cursor.execute(sql, (new_id, title, location, detail))

            conn.commit()
            conn.close()

            flash('✅ ส่งเรื่องเรียบร้อย', 'success')
            return redirect(url_for('user.home'))

    return render_template('user/report_form.html')