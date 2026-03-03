from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from database import get_db_connection

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def is_admin():
    return session.get('role') == 'admin'


@admin_bp.route('/')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('user.login'))

    if not is_admin():
        flash('⛔ ไม่มีสิทธิ์', 'danger')
        return redirect(url_for('user.home'))

    conn = get_db_connection()
    reports = []
    stats = {'total': 0, 'pending': 0, 'ongoing': 0, 'finished': 0}

    if conn:
        cursor = conn.cursor()
        # ดึงข้อมูลงานทั้งหมด
        cursor.execute("SELECT * FROM reports ORDER BY id DESC")
        reports = cursor.fetchall()
        
        # คำนวณสถิติ
        stats['total'] = len(reports)
        stats['pending'] = len([r for r in reports if r['status'] == 'รอซ่อม'])
        stats['ongoing'] = len([r for r in reports if r['status'] == 'กำลังซ่อม'])
        stats['finished'] = len([r for r in reports if r['status'] == 'เสร็จสิ้น'])
        
        conn.close()

    return render_template('admin/dashboard.html', reports=reports, stats=stats)

# เพิ่ม Route สำหรับหน้าประวัติแจ้งซ่อม (Record) ตามที่คุณต้องการ
@admin_bp.route('/record')
def record():
    if not is_admin(): return redirect(url_for('user.home'))
    
    conn = get_db_connection()
    reports = []
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM reports ORDER BY id DESC")
        reports = cursor.fetchall()
        conn.close()
    return render_template('admin/record.html', reports=reports)


@admin_bp.route('/update/<int:id>', methods=['POST'])
def update_status(id):
    if not is_admin():
        return redirect(url_for('user.home'))

    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE reports SET status = %s WHERE id = %s",
            (request.form['status'], id)
        )
        conn.close()

    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/delete/<int:id>')
def delete_report(id):
    if not is_admin():
        return redirect(url_for('user.home'))

    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM reports WHERE id = %s", (id,))
        conn.close()

    return redirect(url_for('admin.dashboard'))


# ---------------- MANAGE USERS (ฉบับอัปเกรดระบบค้นหา) ----------------
@admin_bp.route('/users')
def manage_users():
    if not is_admin(): 
        return redirect(url_for('user.home'))

    # รับค่าจากฟอร์มค้นหา
    s_user = request.args.get('user', '').strip()
    s_name = request.args.get('first_name', '').strip()
    s_lname = request.args.get('last_name', '').strip()

    conn = get_db_connection()
    users = []
    if conn:
        cursor = conn.cursor()
        # คำสั่ง SQL พื้นฐาน
        query = "SELECT id, username, role, first_name, last_name FROM users WHERE 1=1"
        params = []

        # ถ้ามีการกรอกช่องไหน ให้เพิ่มเงื่อนไขค้นหา (ใช้ LIKE เพื่อให้หาบางส่วนของคำได้)
        if s_user:
            query += " AND username LIKE %s"
            params.append(f"%{s_user}%")
        if s_name:
            query += " AND first_name LIKE %s"
            params.append(f"%{s_name}%")
        if s_lname:
            query += " AND last_name LIKE %s"
            params.append(f"%{s_lname}%")

        cursor.execute(query, tuple(params))
        users = cursor.fetchall()
        conn.close()
        
    return render_template('admin/manage_users.html', users=users)

@admin_bp.route('/users/promote/<int:id>')
def promote(id):
    if not is_admin(): return redirect(url_for('user.home'))
    
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET role = 'admin' WHERE id = %s", (id,))
        conn.close()
        flash('✅ แต่งตั้ง Admin เรียบร้อย', 'success')
    return redirect(url_for('admin.manage_users'))

@admin_bp.route('/users/demote/<int:id>')
def demote(id):
    if not is_admin(): return redirect(url_for('user.home'))
    
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET role = 'user' WHERE id = %s", (id,))
        conn.close()
        flash('⬇ ปลดสิทธิ์ Admin เรียบร้อย', 'warning')
    return redirect(url_for('admin.manage_users'))

# ---------------- ลบผู้ใช้งาน (DELETE USER) ----------------
@admin_bp.route('/users/delete/<int:id>')
def delete_user(id):
    if not is_admin(): return redirect(url_for('user.home'))
    
    # ป้องกันไม่ให้เผลอกดลบตัวเอง (เดี๋ยวจะเข้าแอดมินไม่ได้)
    if id == session.get('user_id'):
        flash('❌ ไม่สามารถลบบัญชีของตัวเองได้!', 'danger')
        return redirect(url_for('admin.manage_users'))

    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE id = %s", (id,))
        # conn.commit() # ใส่ไว้เผื่อลืมตั้ง autocommit
        conn.close()
        flash('🗑️ ลบบัญชีผู้ใช้เรียบร้อย', 'success')
        
    return redirect(url_for('admin.manage_users'))

# ---------------- LOGOUT (เพิ่มกลับมา) ----------------
@admin_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('user.home'))