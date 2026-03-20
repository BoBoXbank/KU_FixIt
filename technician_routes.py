from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from database import get_db_connection

technician_bp = Blueprint('technician', __name__, url_prefix='/technician')

# 1. สร้างตารางจับคู่ Role กับ "ประเภทงาน"
ROLE_MAP = {
    'technician_air': 'แอร์',
    'technician_wood': 'ไม้',     
    'technician_wifi': 'WiFi',  
    'technician_plumb': 'ประปา',
    'technician_elec': 'ไฟ'       
}

def is_technician():
    role = session.get('role', '')
    return role.startswith('technician_') or role == 'admin'

@technician_bp.route('/dashboard')
def dashboardtech():
    if not is_technician():
        flash('⛔ เฉพาะช่างเท่านั้นที่เข้าถึงหน้านี้ได้', 'danger')
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
            # แอดมินยังคงเห็นทั้งหมดเพื่อตรวจสอบ
            cursor.execute("SELECT * FROM reports ORDER BY id DESC")
            reports = cursor.fetchall()
        else:
            # 🚀 Logic ใหม่: แยกงานส่วนกลาง กับ งานส่วนตัว 🚀
            # 1. งานที่ 'รอซ่อม' -> ทุกคนในแผนกเห็น (เพื่อกดรับงาน)
            # 2. งานที่ 'กำลังซ่อม' หรือ 'เสร็จสิ้น' -> จะเห็นเฉพาะงานที่ตัวเอง (user_id) เป็นเจ้าของเท่านั้น
            query = """
                SELECT * FROM reports 
                WHERE (title LIKE %s AND status = 'รอซ่อม')
                OR (technician_id = %s)
                ORDER BY id DESC
            """
            cursor.execute(query, (f"%{category}%", user_id))
            reports = cursor.fetchall()

            # คำนวณสถิติเฉพาะของตัวเอง
            stats['pending'] = len([r for r in reports if r['status'] == 'รอซ่อม'])
            stats['ongoing'] = len([r for r in reports if r['technician_id'] == user_id and r['status'] == 'กำลังซ่อม'])
            stats['finished'] = len([r for r in reports if r['technician_id'] == user_id and r['status'] == 'เสร็จสิ้น'])

        conn.close()

    return render_template('technician/dashbordtech.html', reports=reports, stats=stats)

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
            flash(f'✅ อัปเดตสถานะเป็น "{new_status}" เรียบร้อย', 'success')
        except Exception as e:
            flash(f'❌ เกิดข้อผิดพลาด: {e}', 'danger')
        finally:
            conn.close()

    return redirect(request.referrer or url_for('technician.dashboardtech'))

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
        # 🚀 ปรับ Query: 
        # 1. ดึงงานที่ยังไม่มีเจ้าของ (status = 'รอซ่อม') ในแผนกตัวเอง
        # 2. หรือ งานที่ตัวเองเป็นคนรับผิดชอบ (technician_id = ตัวเอง) ไม่ว่าจะสถานะไหน
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
                flash(f'✅ อัปเดต {len(report_ids)} รายการเป็น "{new_status}" เรียบร้อยแล้ว', 'success')
            except Exception as e:
                flash(f'❌ เกิดข้อผิดพลาด: {str(e)}', 'danger')
            finally:
                conn.close()
    else:
        flash('⚠️ กรุณาเลือกรายการและสถานะที่ต้องการเปลี่ยน', 'warning')
        
    return redirect(request.referrer or url_for('technician.dashboardtech'))