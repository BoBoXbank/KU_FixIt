from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from database import get_db_connection

technician_bp = Blueprint('technician', __name__, url_prefix='/technician')

# 1. สร้างตารางจับคู่ Role กับ "ประเภทงาน" ที่เก็บในคอลัมน์ title
ROLE_MAP = {
    'technician_air': 'แอร์',
    'technician_wood': 'ไม้',     # เปลี่ยนจาก 'ไม้/เฟอร์นิเจอร์' เป็น 'ไม้'
    'technician_wifi': 'WiFi',  # เปลี่ยนจาก 'อินเทอร์เน็ต/WiFi' เป็น 'WiFi'
    'technician_plumb': 'ประปา'
}

def is_technician():
    role = session.get('role', '')
    return role.startswith('technician_') or role == 'admin'

# ---------------- DASHBOARD TECH ----------------
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
    
    if conn:
        cursor = conn.cursor()
        
        if user_role == 'admin':
            # Admin เห็นงานทั้งหมด
            cursor.execute("SELECT * FROM reports ORDER BY id DESC")
        else:
            # ✅ แก้ไขตรงนี้: เปลี่ยนจากการหาคำเป๊ะๆ (=) เป็นการหาบางส่วน (LIKE)
            query = """
                SELECT * FROM reports 
                WHERE (title LIKE %s AND (technician_id IS NULL OR status = 'รอซ่อม'))
                OR (technician_id = %s)
                ORDER BY id DESC
            """
            # ✅ ใส่ % คลุมตัวแปร category เพื่อให้หาคำว่า "แอร์" เจอชัวร์ๆ
            cursor.execute(query, (f"%{category}%", user_id))
            
        reports = cursor.fetchall()
        conn.close()

    # สรุปสถิติเฉพาะงานที่ช่างคนนั้นเห็น
    stats = {
        'pending': len([r for r in reports if r['status'] == 'รอซ่อม']),
        'ongoing': len([r for r in reports if r['status'] == 'กำลังซ่อม']),
        'finished': len([r for r in reports if r['status'] == 'เสร็จสิ้น'])
    }

    return render_template('technician/dashbordtech.html', reports=reports, stats=stats)


# ---------------- UPDATE STATUS ----------------
@technician_bp.route('/update_status/<int:id>', methods=['POST'])
def update_status(id):
    if not is_technician(): return redirect(url_for('user.login'))

    new_status = request.form.get('status')
    user_id = session.get('user_id')
    
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        if new_status == 'กำลังซ่อม':
            # ตอนกดรับงาน ให้บันทึก ID ของช่างที่กดด้วย
            cursor.execute(
                "UPDATE reports SET status = %s, technician_id = %s WHERE id = %s",
                (new_status, user_id, id)
            )
        else:
            # ตอนกดซ่อมเสร็จ เปลี่ยนแค่สถานะ (ID ช่างมีอยู่แล้ว)
            cursor.execute(
                "UPDATE reports SET status = %s WHERE id = %s",
                (new_status, id)
            )
        conn.close()
        flash('✅ อัปเดตสถานะงานเรียบร้อย', 'success')

    return redirect(url_for('technician.dashboardtech'))


# ---------------- RECORD TECH (เพิ่มให้เพื่อให้กดเมนูข้างได้) ----------------
@technician_bp.route('/record_tech')
def record_tech():
    if not is_technician():
        return redirect(url_for('user.login'))
        
    user_id = session.get('user_id')
    conn = get_db_connection()
    reports = []
    if conn:
        cursor = conn.cursor()
        # ดึงเฉพาะงานที่ช่างคนนั้นๆ กดรับไปทำ และซ่อมเสร็จแล้ว
        cursor.execute("SELECT * FROM reports WHERE technician_id = %s AND status = 'เสร็จสิ้น' ORDER BY id DESC", (user_id,))
        reports = cursor.fetchall()
        conn.close()
        
    return render_template('technician/record_tech.html', reports=reports)