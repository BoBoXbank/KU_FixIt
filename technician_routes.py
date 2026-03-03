from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from database import get_db_connection

technician_bp = Blueprint('technician', __name__, url_prefix='/technician')

# ฟังก์ชันตรวจสอบว่าเป็นช่างจริงไหม
def is_technician():
    return session.get('role') == 'technician'

# ---------------- DASHBOARD TECH ----------------
@technician_bp.route('/dashboard')
def dashboardtech():
    if not is_technician():
        flash('⛔ เฉพาะช่างเท่านั้นที่เข้าถึงหน้านี้ได้', 'danger')
        return redirect(url_for('user.login'))

    conn = get_db_connection()
    reports = []
    stats = {'total': 0, 'pending': 0, 'ongoing': 0, 'finished': 0}

    if conn:
        cursor = conn.cursor()
        # ดึงงานทั้งหมดมาให้ช่างดู
        cursor.execute("SELECT * FROM reports ORDER BY id DESC")
        reports = cursor.fetchall()
        
        # คำนวณสถิติงาน
        stats['total'] = len(reports)
        stats['pending'] = len([r for r in reports if r['status'] == 'รอซ่อม'])
        stats['ongoing'] = len([r for r in reports if r['status'] == 'กำลังซ่อม'])
        stats['finished'] = len([r for r in reports if r['status'] == 'เสร็จสิ้น'])
        
        conn.close()

    # เรนเดอร์ไฟล์ตามโครงสร้างที่คุณวางไว้
    return render_template('technician/dashbordtech.html', reports=reports, stats=stats)

# ---------------- RECORD TECH (ประวัติงานซ่อม) ----------------
@technician_bp.route('/record')
def record_tech():
    if not is_technician():
        return redirect(url_for('user.login'))
    
    conn = get_db_connection()
    reports = []
    if conn:
        cursor = conn.cursor()
        # ดึงงานที่ซ่อมเสร็จแล้วมาแสดงในหน้าประวัติ
        cursor.execute("SELECT * FROM reports WHERE status = 'เสร็จสิ้น' ORDER BY id DESC")
        reports = cursor.fetchall()
        conn.close()
        
    # เรนเดอร์ไฟล์ตามโครงสร้างที่คุณวางไว้
    return render_template('technician/record_tech.html', reports=reports)

# ---------------- UPDATE STATUS (สำหรับช่างกดรับงาน/ปิดงาน) ----------------
@technician_bp.route('/update_status/<int:id>', methods=['POST'])
def update_status(id):
    if not is_technician():
        return redirect(url_for('user.login'))

    new_status = request.form.get('status')
    
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        # อัปเดตสถานะงาน
        cursor.execute(
            "UPDATE reports SET status = %s WHERE id = %s",
            (new_status, id)
        )
        conn.commit()
        conn.close()
        flash(f'✅ อัปเดตสถานะเป็น "{new_status}" เรียบร้อย', 'success')

    return redirect(url_for('technician.dashboardtech'))