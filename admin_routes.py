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

    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM reports ORDER BY id DESC")
        reports = cursor.fetchall()
        conn.close()

    return render_template('admin/dashboard.html', reports=reports)


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


# ---------------- MANAGE USERS (เพิ่มกลับมา) ----------------
@admin_bp.route('/users')
def manage_users():
    if not is_admin(): 
        return redirect(url_for('user.home'))

    conn = get_db_connection()
    users = []
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, role FROM users")
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