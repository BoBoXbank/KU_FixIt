from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from database import get_db_connection
import base64

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def is_admin():
    """ตรวจสอบว่าเป็นแอดมินหรือไม่"""
    return session.get('role') == 'admin'

def get_current_user_data():
    """ดึงข้อมูลผู้ใช้ปัจจุบัน (ชื่อจริง, นามสกุล, รูปโปรไฟล์)"""
    user_id = session.get('user_id')
    if not user_id:
        return None
    
    conn = get_db_connection()
    user_data = None
    if conn:
        try:
            cursor = conn.cursor()
            # ดึงข้อมูลที่จำเป็นสำหรับ Sidebar และ Profile Badge
            cursor.execute("SELECT id, username, first_name, last_name, profile_picture FROM users WHERE id = %s", (user_id,))
            user_data = cursor.fetchone()
            
            if user_data:
                user_data = dict(user_data) # แปลงเป็น dictionary เพื่อให้แก้ไขค่าได้ง่าย
                # ถ้ามีรูปโปรไฟล์ ให้แปลงเป็น Base64
                if user_data['profile_picture']:
                    user_data['profile_picture'] = base64.b64encode(user_data['profile_picture']).decode('utf-8')
        finally:
            conn.close()
    return user_data

# --- หน้า Dashboard (หน้าแรกแอดมิน) ---
@admin_bp.route('/')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('user.login'))

    if not is_admin():
        flash('⛔ ไม่มีสิทธิ์เข้าถึงส่วนผู้ดูแลระบบ', 'danger')
        return redirect(url_for('user.home'))

    # ดึงข้อมูลสำหรับ Sidebar/Header
    current_user_info = get_current_user_data()

    conn = get_db_connection()
    reports = []
    stats = {'total': 0, 'pending': 0, 'ongoing': 0, 'finished': 0}

    if conn:
        try:
            cursor = conn.cursor()
            # ดึงข้อมูลใบแจ้งซ่อม
            cursor.execute("SELECT * FROM reports ORDER BY id DESC")
            reports = cursor.fetchall()
            
            # คำนวณสถิติ
            stats['total'] = len(reports)
            stats['pending'] = len([r for r in reports if r['status'] in ['รอซ่อม', 'รอดำเนินการ']])
            stats['ongoing'] = len([r for r in reports if r['status'] == 'กำลังซ่อม'])
            stats['finished'] = len([r for r in reports if r['status'] == 'เสร็จสิ้น'])
        finally:
            conn.close()

    return render_template('admin/dashboard.html', 
                           reports=reports, 
                           stats=stats, 
                           current_user_info=current_user_info)

# --- หน้าประวัติแจ้งซ่อม (Record) ---
@admin_bp.route('/record')
def record():
    if not is_admin(): return redirect(url_for('user.home'))
    
    current_user_info = get_current_user_data()
    conn = get_db_connection()
    reports = []
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM reports ORDER BY id DESC")
            reports = cursor.fetchall()
        finally:
            conn.close()
            
    return render_template('admin/record.html', 
                           reports=reports, 
                           current_user_info=current_user_info)

# --- หน้าจัดการผู้ใช้งาน (Manage Users) ---
@admin_bp.route('/users')
def manage_users():
    if not is_admin(): return redirect(url_for('user.home'))

    current_user_info = get_current_user_data()
    s_user = request.args.get('user', '').strip()
    s_name = request.args.get('first_name', '').strip()
    s_lname = request.args.get('last_name', '').strip()

    conn = get_db_connection()
    users = []
    if conn:
        try:
            cursor = conn.cursor()
            query = "SELECT id, username, role, first_name, last_name FROM users WHERE 1=1"
            params = []

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
        finally:
            conn.close()
        
    return render_template('admin/manage_users.html', 
                           users=users, 
                           current_user_info=current_user_info)

# --- แก้ไขสถานะใบแจ้งซ่อม ---
@admin_bp.route('/update/<int:id>', methods=['POST'])
def update_status(id):
    if not is_admin(): return redirect(url_for('user.home'))
    
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE reports SET status = %s WHERE id = %s", (request.form['status'], id))
            conn.commit()
        finally:
            conn.close()
    return redirect(url_for('admin.dashboard'))

# --- ลบใบแจ้งซ่อม ---
@admin_bp.route('/delete/<int:id>')
def delete_report(id):
    if not is_admin(): return redirect(url_for('user.home'))
    
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM reports WHERE id = %s", (id,))
            conn.commit()
        finally:
            conn.close()
    return redirect(url_for('admin.dashboard'))

# --- เปลี่ยนสิทธิ์ผู้ใช้งาน ---
@admin_bp.route('/users/change_role/<int:id>')
def change_role(id):
    if not is_admin(): return redirect(url_for('user.home'))
    
    new_role = request.args.get('role')
    if id == session.get('user_id'):
        flash('❌ ไม่สามารถเปลี่ยนสิทธิ์ของตัวเองได้', 'danger')
        return redirect(url_for('admin.manage_users'))

    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET role = %s WHERE id = %s", (new_role, id))
            conn.commit()
            flash(f'✅ เปลี่ยนสถานะเป็น {new_role} เรียบร้อย', 'success')
        finally:
            conn.close()
    return redirect(url_for('admin.manage_users'))

# --- ลบผู้ใช้งาน ---
@admin_bp.route('/users/delete/<int:id>')
def delete_user(id):
    if not is_admin(): return redirect(url_for('user.home'))
    
    if id == session.get('user_id'):
        flash('❌ ไม่สามารถลบบัญชีของตัวเองได้!', 'danger')
        return redirect(url_for('admin.manage_users'))

    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE id = %s", (id,))
            conn.commit()
            flash('🗑️ ลบบัญชีผู้ใช้เรียบร้อย', 'success')
        finally:
            conn.close()
    return redirect(url_for('admin.manage_users'))

# --- ออกจากระบบ ---
@admin_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('user.home'))