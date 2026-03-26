from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from database import get_db_connection

# ==============================================================================
# ส่วนที่ 1: การตั้งค่า BLUEPRINT สำหรับช่างซ่อม (TECHNICIAN)
# หน้าที่: ใช้สำหรับลงทะเบียน Route ทั้งหมดที่ขึ้นต้นด้วย /technician
# ==============================================================================
technician_bp = Blueprint('technician', __name__, url_prefix='/technician')

# ==============================================================================
# ส่วนที่ 2: การตั้งค่าหมวดหมู่งาน (ROLE MAPPING)
# หน้าที่: สร้างตารางจับคู่สิทธิ์ของผู้ใช้งาน (Role) กับประเภทของงานซ่อมที่ต้องรับผิดชอบ
# ==============================================================================
ROLE_MAP = {
    'technician_air': 'แอร์',
    'technician_wood': 'ไม้',     
    'technician_wifi': 'WiFi',  
    'technician_plumb': 'ประปา',
    'technician_elec': 'ไฟ'       
}

# ==============================================================================
# ส่วนที่ 3: ฟังก์ชันตรวจสอบสิทธิ์ (AUTHORIZATION HELPER)
# หน้าที่: ตรวจสอบว่าผู้ใช้ที่ล็อกอินอยู่เป็น "ช่าง" (technician) หรือ "แอดมิน" หรือไม่
# ==============================================================================
def is_technician():
    role = session.get('role', '')
    return role.startswith('technician_') or role == 'admin'

# ==============================================================================
# ส่วนที่ 4: หน้าแดชบอร์ดของช่าง (TECHNICIAN DASHBOARD)
# หน้าที่: แสดงภาพรวมงานซ่อม แยกตามประเภทช่าง คำนวณสถิติ และแสดงตารางงาน
# ==============================================================================
@technician_bp.route('/dashboard')
def dashboardtech():
    if not is_technician():
        flash('เฉพาะช่างเท่านั้นที่เข้าถึงหน้านี้ได้', 'danger')
        return redirect(url_for('user.login'))

    user_role = session.get('role')
    user_id = session.get('user_id')
    category = ROLE_MAP.get(user_role)

    conn = get_db_connection()
    reports = []
    stats = {'pending': 0, 'ongoing': 0, 'finished': 0}

    if conn:
        cursor = conn.cursor()
        if user_role == 'admin':
            # แอดมินยังคงเห็นทั้งหมดเพื่อตรวจสอบภาพรวมได้
            cursor.execute("SELECT * FROM reports ORDER BY id DESC")
            reports = cursor.fetchall()
        else:
            # การแยกงานส่วนกลาง กับ งานส่วนตัว
            # 1. งานที่ 'รอซ่อม' จะแสดงให้ทุกคนในแผนกเห็น (เพื่อให้สามารถกดรับงานได้)
            # 2. งานที่ 'กำลังซ่อม' หรือ 'เสร็จสิ้น' จะแสดงเฉพาะงานที่ตัวเอง (user_id) เป็นผู้รับผิดชอบเท่านั้น
            query = """
                SELECT * FROM reports 
                WHERE (title LIKE %s AND status = 'รอซ่อม')
                OR (technician_id = %s)
                ORDER BY id DESC
            """
            cursor.execute(query, (f"%{category}%", user_id))
            reports = cursor.fetchall()

            # คำนวณสถิติสถานะงานซ่อมเฉพาะของตัวเอง
            stats['pending'] = len([r for r in reports if r['status'] == 'รอซ่อม'])
            stats['ongoing'] = len([r for r in reports if r['technician_id'] == user_id and r['status'] == 'กำลังซ่อม'])
            stats['finished'] = len([r for r in reports if r['technician_id'] == user_id and r['status'] == 'เสร็จสิ้น'])

        conn.close()

    return render_template('technician/dashbordtech.html', reports=reports, stats=stats)

# ==============================================================================
# ส่วนที่ 5: การอัปเดตสถานะแบบรายบุคคล (SINGLE STATUS UPDATE)
# หน้าที่: เปลี่ยนสถานะงานซ่อม และหากรับงาน (กำลังซ่อม) จะบันทึกว่าช่างคนไหนเป็นคนรับผิดชอบ
# ==============================================================================
@technician_bp.route('/update_status/<int:id>', methods=['POST'])
def update_status(id):
    if not is_technician(): return redirect(url_for('user.login'))

    new_status = request.form.get('status')
    user_id = session.get('user_id')
    
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            if new_status == 'กำลังซ่อม':
                cursor.execute("UPDATE reports SET status = %s, technician_id = %s WHERE id = %s", (new_status, user_id, id))
            else:
                cursor.execute("UPDATE reports SET status = %s WHERE id = %s", (new_status, id))
            conn.commit() 
            flash(f'อัปเดตสถานะเป็น "{new_status}" เรียบร้อย', 'success')
        except Exception as e:
            flash(f'เกิดข้อผิดพลาด: {e}', 'danger')
        finally:
            conn.close()

    return redirect(request.referrer or url_for('technician.dashboardtech'))

# ==============================================================================
# ส่วนที่ 6: หน้ารายการประวัติงานซ่อมของช่าง (TECHNICIAN RECORD)
# หน้าที่: ดึงข้อมูลประวัติการทำงานทั้งหมดที่เกี่ยวข้องกับช่างคนนั้นๆ มาแสดงผล
# ==============================================================================
@technician_bp.route('/record_tech')
def record_tech():
    if not is_technician():
        return redirect(url_for('user.login'))
        
    user_role = session.get('role')
    user_id = session.get('user_id') # ดึง ID ของช่างที่ล็อกอินอยู่
    category = ROLE_MAP.get(user_role)
    if not category: category = "ไม่มีหมวดหมู่นี้"

    conn = get_db_connection()
    reports = []
    if conn:
        cursor = conn.cursor()
        # 1. ดึงงานที่ยังไม่มีเจ้าของ (status = 'รอซ่อม') ในแผนกของตัวเอง
        # 2. หรือ งานที่ตัวเองเป็นคนรับผิดชอบ (technician_id = ตัวเอง) ไม่ว่าจะอยู่ในสถานะไหน
        query = """
            SELECT * FROM reports 
            WHERE (title LIKE %s AND status = 'รอซ่อม')
            OR (technician_id = %s)
            ORDER BY id DESC
        """
        cursor.execute(query, (f"%{category}%", user_id))
        reports = cursor.fetchall()
        conn.close()
        
    return render_template('technician/record_tech.html', reports=reports)

# ==============================================================================
# ส่วนที่ 7: การอัปเดตสถานะแบบกลุ่ม (BULK UPDATE)
# หน้าที่: รับรายการ ID ที่เลือกจาก Checkbox เพื่อเปลี่ยนสถานะทีละหลายๆ งานพร้อมกัน
# ==============================================================================
@technician_bp.route('/bulk_update', methods=['POST'])
def bulk_update():
    # ดึงรายการ ID ที่ถูกเลือกมาจาก Checkbox
    report_ids = request.form.getlist('report_ids')
    # ดึงสถานะใหม่ที่เลือกจาก Dropdown
    new_status = request.form.get('bulk_status')
    
    if report_ids and new_status:
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor()
                # สร้างเครื่องหมาย %s ตามจำนวน ID เพื่อใช้ในคำสั่ง SQL IN (...)
                format_strings = ','.join(['%s'] * len(report_ids))
                query = f"UPDATE reports SET status = %s WHERE id IN ({format_strings})"
                
                # ส่งค่า status และ tuple ของ IDs เข้าไปประมวลผล
                cursor.execute(query, [new_status] + report_ids)
                conn.commit()
                flash(f'อัปเดต {len(report_ids)} รายการเป็น "{new_status}" เรียบร้อยแล้ว', 'success')
            except Exception as e:
                flash(f'เกิดข้อผิดพลาด: {str(e)}', 'danger')
            finally:
                conn.close()
    else:
        flash('กรุณาเลือกรายการและสถานะที่ต้องการเปลี่ยน', 'warning')
        
    return redirect(request.referrer or url_for('technician.dashboardtech'))