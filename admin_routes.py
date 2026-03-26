from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from database import get_db_connection
import base64

# ==============================================================================
# การตั้งค่า BLUEPRINT สำหรับ ADMIN
# ใช้งานในไฟล์: app.py (ใช้สำหรับลงทะเบียน Route ทั้งหมดที่ขึ้นต้นด้วย /admin)
# ==============================================================================
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# ==============================================================================
# ฟังก์ชันตรวจสอบสิทธิ์การเข้าถึง (HELPER FUNCTION)
# หน้าที่: ใช้ตรวจสอบว่าผู้ใช้ที่กำลังใช้งานระบบมีสิทธิ์เป็น 'admin' หรือไม่
# ==============================================================================
def is_admin():
    return session.get('role') == 'admin'

# ==============================================================================
# ส่วนที่ 1: หน้าแดชบอร์ดหลักของผู้ดูแลระบบ (ADMIN DASHBOARD)
# หน้าที่: ดึงข้อมูลการแจ้งซ่อมทั้งหมดมาคำนวณสถิติ (รอซ่อม, กำลังซ่อม, เสร็จสิ้น)
# ใช้งานในไฟล์: templates/admin/dashboard.html
# ==============================================================================
@admin_bp.route('/')
def dashboard():
    if 'user_id' not in session: return redirect(url_for('user.login'))
    if not is_admin():
        flash('ไม่มีสิทธิ์เข้าถึงส่วนผู้ดูแลระบบ', 'danger')
        return redirect(url_for('user.home'))

    conn = get_db_connection()
    reports = []
    stats = {'total': 0, 'pending': 0, 'ongoing': 0, 'finished': 0}

    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM reports ORDER BY id DESC")
            reports = cursor.fetchall()
            
            stats['total'] = len(reports)
            stats['pending'] = len([r for r in reports if r['status'] in ['รอซ่อม', 'รอดำเนินการ']])
            stats['ongoing'] = len([r for r in reports if r['status'] == 'กำลังซ่อม'])
            stats['finished'] = len([r for r in reports if r['status'] == 'เสร็จสิ้น'])
        finally:
            conn.close()

    return render_template('admin/dashboard.html', reports=reports, stats=stats)

# ==============================================================================
# ส่วนที่ 2: หน้ารายการแจ้งซ่อมทั้งหมด (ALL REPORTS RECORD)
# หน้าที่: ดึงข้อมูลประวัติการแจ้งซ่อมทั้งหมดจากฐานข้อมูลมาแสดงในรูปแบบตาราง
# ใช้งานในไฟล์: templates/admin/record.html
# ==============================================================================
@admin_bp.route('/record')
def record():
    if not is_admin(): return redirect(url_for('user.home'))
    conn = get_db_connection()
    reports = []
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM reports ORDER BY id DESC")
            reports = cursor.fetchall()
        finally:
            conn.close()
    return render_template('admin/record.html', reports=reports)

# ==============================================================================
# ส่วนที่ 3: ระบบจัดการผู้ใช้งานและตรวจสอบ IP (MANAGE USERS & IP TRACKING)
# หน้าที่: ค้นหาผู้ใช้งาน, ดูประวัติการล็อกอิน (IP Address), และดึงรายชื่อ IP ที่ถูกแบน
# ใช้งานในไฟล์: templates/admin/manage_users.html
# ==============================================================================
@admin_bp.route('/users')
def manage_users():
    if not is_admin(): return redirect(url_for('user.home'))

    s_user = request.args.get('user', '').strip()
    s_name = request.args.get('first_name', '').strip()
    s_lname = request.args.get('last_name', '').strip()

    conn = get_db_connection()
    users = []
    ip_map = {} 
    banned_ips_list = [] 
    
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
            
            try:
                cursor.execute("SELECT username, ip_address, last_login FROM user_ips")
                all_ips = cursor.fetchall()
                for row in all_ips:
                    uname = row['username']
                    if uname not in ip_map:
                        ip_map[uname] = []
                    ip_map[uname].append({'ip': row['ip_address'], 'last_login': row['last_login']})
            except Exception:
                pass 

            try:
                cursor.execute("SELECT ip_address FROM banned_ips")
                banned_ips_list = [row['ip_address'] for row in cursor.fetchall()]
            except Exception:
                pass

        finally:
            conn.close()
        
    return render_template('admin/manage_users.html', users=users, ip_map=ip_map, banned_ips_list=banned_ips_list)

# ==============================================================================
# ส่วนที่ 4: ระบบรักษาความปลอดภัย - แบนและปลดแบน IP (IP BAN MANAGEMENT)
# หน้าที่: บล็อกหรือปลดบล็อก IP Address ไม่ให้เข้าใช้งานเว็บไซต์
# ใช้งานในไฟล์: ปุ่มกดในหน้า templates/admin/manage_users.html
# ==============================================================================
@admin_bp.route('/ban_ip/<ip>', methods=['POST'])
def ban_ip(ip):
    if not is_admin(): return redirect(url_for('user.home'))
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM banned_ips WHERE ip_address = %s", (ip,))
            if not cursor.fetchone():
                cursor.execute("INSERT INTO banned_ips (ip_address) VALUES (%s)", (ip,))
                conn.commit()
                flash(f'แบน IP: {ip} อย่างถาวรเรียบร้อยแล้ว!', 'success')
            else:
                flash(f'IP: {ip} นี้ถูกแบนไปแล้ว', 'warning')
        except Exception as e:
            flash(f'เกิดข้อผิดพลาด: โปรดสร้างตาราง Banned_ips ก่อน', 'danger')
            print(e)
        finally:
            conn.close()
    return redirect(request.referrer or url_for('admin.manage_users'))

@admin_bp.route('/unban_ip/<ip>', methods=['POST'])
def unban_ip(ip):
    if not is_admin(): return redirect(url_for('user.home'))
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM banned_ips WHERE ip_address = %s", (ip,))
            conn.commit()
            flash(f'ปลดแบน IP: {ip} เรียบร้อยแล้ว! ผู้ใช้สามารถเข้าเว็บได้ตามปกติ', 'success')
        except Exception as e:
            flash(f'เกิดข้อผิดพลาดในการปลดแบน: {e}', 'danger')
        finally:
            conn.close()
    return redirect(request.referrer or url_for('admin.manage_users'))

# ==============================================================================
# ส่วนที่ 5: การจัดการใบแจ้งซ่อมแบบรายบุคคล (SINGLE REPORT MANAGEMENT)
# หน้าที่: อัปเดตสถานะ (รอซ่อม -> กำลังซ่อม -> เสร็จสิ้น) และการลบใบแจ้งซ่อม
# ใช้งานในไฟล์: ตารางแสดงผลใน templates/admin/record.html
# ==============================================================================
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
    return redirect(request.referrer or url_for('admin.manage_users'))

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
    return redirect(request.referrer or url_for('admin.manage_users'))

# ==============================================================================
# ส่วนที่ 6: การจัดการสิทธิ์และบัญชีผู้ใช้งาน (USER ROLE & ACCOUNT MANAGEMENT)
# หน้าที่: เปลี่ยนตำแหน่งผู้ใช้ (เช่น user -> technician) หรือลบบัญชีผู้ใช้ออกจากระบบ
# ใช้งานในไฟล์: ตารางแสดงผู้ใช้ใน templates/admin/manage_users.html
# ==============================================================================
@admin_bp.route('/users/change_role/<int:id>')
def change_role(id):
    if not is_admin(): return redirect(url_for('user.home'))
    
    new_role = request.args.get('role')
    if id == session.get('user_id'):
        flash('ไม่สามารถเปลี่ยนสิทธิ์ของตัวเองได้', 'danger')
        return redirect(url_for('admin.manage_users'))

    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET role = %s WHERE id = %s", (new_role, id))
            conn.commit()
            flash(f'เปลี่ยนสถานะเป็น {new_role} เรียบร้อย', 'success')
        finally:
            conn.close()
    return redirect(url_for('admin.manage_users'))

@admin_bp.route('/users/delete/<int:id>')
def delete_user(id):
    if not is_admin(): return redirect(url_for('user.home'))
    
    if id == session.get('user_id'):
        flash('ไม่สามารถลบบัญชีของตัวเองได้!', 'danger')
        return redirect(url_for('admin.manage_users'))

    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE id = %s", (id,))
            conn.commit()
            flash('ลบบัญชีผู้ใช้เรียบร้อย', 'success')
        finally:
            conn.close()
    return redirect(url_for('admin.manage_users'))

# ==============================================================================
# ส่วนที่ 7: ระบบออกจากระบบของผู้ดูแล (ADMIN LOGOUT)
# หน้าที่: เคลียร์ค่า Session และส่งกลับไปหน้า Home
# ==============================================================================
@admin_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('user.home'))

# ==============================================================================
# ส่วนที่ 8: การจัดการข้อมูลแบบกลุ่ม (BULK ACTIONS)
# หน้าที่: อัปเดตสถานะทีละหลายๆ รายการพร้อมกัน หรือลบทีละหลายๆ รายการพร้อมกัน
# ใช้งานในไฟล์: Checkbox ในตารางของ templates/admin/record.html
# ==============================================================================
@admin_bp.route('/bulk_update', methods=['POST'])
def bulk_update():
    if not is_admin(): return redirect(url_for('user.home'))
    
    report_ids = request.form.getlist('report_ids')
    new_status = request.form.get('bulk_status')
    
    if report_ids and new_status:
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor()
                format_strings = ','.join(['%s'] * len(report_ids))
                query = f"UPDATE reports SET status = %s WHERE id IN ({format_strings})"
                cursor.execute(query, [new_status] + report_ids)
                conn.commit()
                flash(f'อัปเดต {len(report_ids)} รายการเรียบร้อย', 'success')
            finally:
                conn.close()
    return redirect(request.referrer or url_for('admin.record'))

@admin_bp.route('/delete_multiple', methods=['POST'])
def delete_multiple():
    if not is_admin(): return redirect(url_for('user.home'))
    report_ids = request.form.getlist('report_ids')
    if report_ids:
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor()
                format_strings = ','.join(['%s'] * len(report_ids))
                cursor.execute(f"DELETE FROM reports WHERE id IN ({format_strings})", tuple(report_ids))
                conn.commit()
                flash(f'ลบ {len(report_ids)} รายการเรียบร้อยแล้ว', 'success')
            finally:
                conn.close()
    return redirect(request.referrer or url_for('admin.record'))