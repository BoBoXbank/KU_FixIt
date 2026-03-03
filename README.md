# 🚀 Utility Issue Reporting System (Flask Web App)

[cite_start]โปรเจกต์เว็บแอปพลิเคชันสำหรับรายงานปัญหาอุปโภคบริโภคในมหาวิทยาลัย พัฒนาด้วย Flask และเชื่อมต่อกับฐานข้อมูล TiDB Cloud (AWS)

## 📋 ฟีเจอร์หลัก
* **ระบบสมาชิก:** สมัครสมาชิก, ล็อกอิน และรีเซ็ตรหัสผ่านด้วยคำถามความปลอดภัย
* **ระบบรายงาน:** ผู้ใช้สามารถแจ้งเรื่อง ระบุสถานที่ และรายละเอียดปัญหาได้
* **ระบบ Admin:** จัดการสถานะรายงาน, แต่งตั้ง/ปลดสิทธิ์แอดมิน และจัดการรายชื่อผู้ใช้งาน
* [cite_start]**ความปลอดภัย:** แฮชรหัสผ่าน (Password Hashing) และเชื่อมต่อฐานข้อมูลผ่าน SSL 

## 🛠 เทคโนโลยีที่ใช้
Python 3.10 ขึ้นไป (แนะนำ 3.11 หรือใหม่กว่า)
Flask
SQLite (ฐานข้อมูลเริ่มต้น)
HTML / CSS / Jinja2

## ✅ ซอฟต์แวร์ขั้นต่ำที่ต้องมี
Python เวอร์ชัน 3.10 ขึ้นไป
Git (สำหรับ clone โปรเจกต์)

ตรวจสอบเวอร์ชันด้วยคำสั่ง:

python3 --version
pip --version


💾 ฐานข้อมูล
ใช้ฐานข้อมูล SQLite เป็นค่าเริ่มต้น
ระบบจะสร้างไฟล์ฐานข้อมูลให้อัตโนมัติ (เช่น database.db)
ไม่จำเป็นต้องติดตั้ง Database Server เพิ่ม
หากต้องการใช้งานจริงในระดับ Production สามารถเปลี่ยนไปใช้:
MySQL
PostgreSQL
🖥 สเปคเครื่องขั้นต่ำ
ระบบปฏิบัติการ: macOS / Windows / Linux
RAM ขั้นต่ำ: 4 GB (แนะนำ 8 GB)
พื้นที่ว่าง: อย่างน้อย 500 MB
เว็บเบราว์เซอร์: Chrome / Edge / Firefox

## 🚀 วิธีติดตั้งและรันโปรเจกต์
1️⃣ Clone โปรเจกต์

git clone https://github.com/YOUR-USERNAME/KU_FixIt.git
cd KU_FixIt

2️⃣ สร้าง Virtual Environment

สำหรับ Mac / Linux:
python3 -m venv .venv
source .venv/bin/activate

สำหรับ Windows:
py -m venv .venv
.venv\Scripts\activate

3️⃣ ติดตั้ง Dependencies
pip install -r requirements.txt
หากไม่มีไฟล์ requirements.txt ให้ติดตั้ง Flask ด้วยคำสั่ง:
pip install flask

4️⃣ รันโปรแกรม
for mac os:
python3 app.py

for window :
python app.py
หากขึ้นข้อความว่า Port 5000 ถูกใช้งานอยู่ ให้แก้ในไฟล์ app.py เป็น:
app.run(debug=True, port=5001)

5️⃣ เปิดเว็บเบราว์เซอร์
เข้าไปที่:
http://127.0.0.1:5000
หรือ (ถ้าเปลี่ยนพอร์ต)
http://127.0.0.1:5001

📁 โครงสร้างโปรเจกต์
KU_FixIt
 ├── app.py
 ├── requirements.txt
 ├── templates/
 ├── static/
 └── database.db (ระบบสร้างให้อัตโนมัติ)
