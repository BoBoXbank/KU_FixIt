# 🚀 Utility Issue Reporting System (Flask Web App)

โปรเจกต์เว็บแอปพลิเคชันสำหรับรายงานปัญหาอุปโภคบริโภคในมหาวิทยาลัย พัฒนาด้วย Flask และเชื่อมต่อกับฐานข้อมูล TiDB Cloud (AWS)

**Live Demo:** [https://ku-fixit.onrender.com/](https://ku-fixit.onrender.com/)

## ฟีเจอร์หลัก
* [cite_start]**ระบบสมาชิก (User):** * สมัครสมาชิกด้วยอีเมล `@ku.th` เท่านั้น พร้อมระบบยืนยันตัวตนผ่าน **OTP Email** 
    * [cite_start]ระบบคำถามความปลอดภัยสำหรับรีเซ็ตรหัสผ่าน 
    * [cite_start]ระบบป้องกันการ Login ผิด (Lockout 2 นาที เมื่อผิดครบ 10 ครั้ง) 
* [cite_start]**ระบบรายงาน (Reporting):** * แจ้งซ่อมพร้อมระบุสถานที่ ประเภทงาน และรายละเอียด 
    * [cite_start]อัปโหลดรูปภาพประกอบ (มีระบบบีบอัดไฟล์อัตโนมัติเพื่อประหยัดพื้นที่ฐานข้อมูล) 
* [cite_start]**ระบบช่าง (Technician):** * แยกหน้า Dashboard ตามแผนก (แอร์, ไม้, WiFi, ประปา, ไฟฟ้า) 
    * [cite_start]ระบบกดรับงาน (Claim) และอัปเดตสถานะการดำเนินงาน 
* [cite_start]**ระบบผู้ดูแลระบบ (Admin):** * จัดการสถานะรายงานและรายชื่อผู้ใช้งาน 
    * [cite_start]**Security Control:** ระบบแบน/ปลดแบน IP Address ของผู้ใช้งานที่ทำผิดกฎ 
* [cite_start]**ความปลอดภัย (Security):** * Password Hashing และเชื่อมต่อฐานข้อมูลผ่าน SSL 
    * [cite_start]ป้องกัน Bot ด้วย Google reCAPTCHA

## 🛠 เทคโนโลยีที่ใช้
    Backend: Python 3.10+ / Flask 
    Database: TiDB Cloud (MySQL Compatible) 
    Libraries: PyMySQL, Flask-Mail, Pillow (Image Processing), python-dotenv 
    Frontend: HTML5, CSS3, Jinja2, JavaScript

## ซอฟต์แวร์ขั้นต่ำที่ต้องมี
    Python เวอร์ชัน 3.10 ขึ้นไป
    Git (สำหรับ clone โปรเจกต์)

    ตรวจสอบเวอร์ชันด้วยคำสั่ง:

    python3 --version
    pip --version


### 🖥 สเปคเครื่องขั้นต่ำ
    ระบบปฏิบัติการ: macOS / Windows / Linux
    RAM ขั้นต่ำ: 4 GB (แนะนำ 8 GB)
    พื้นที่ว่าง: อย่างน้อย 500 MB
    เว็บเบราว์เซอร์: Chrome / Edge / Firefox

### 🚀 วิธีติดตั้งและรันโปรเจกต์
    1️⃣ Clone โปรเจกต์
    ```
    git clone https://github.com/YOUR-USERNAME/KU_FixIt.git
    cd KU_FixIt
    ```
    2️⃣ สร้าง Virtual Environment

    สำหรับ Mac / Linux:
    ```
    python3 -m venv .venv
    source .venv/bin/activate
    ```
    สำหรับ Windows:
    ```
    py -m venv .venv
    set-executionpolicy RemoteSigned -Scope CurrentUser
    .venv\Scripts\activate
    ```
    3️⃣ ติดตั้ง Dependencies
    ````
    pip install -r requirements.txt
    ````

    4️⃣ รันโปรแกรม
    for mac os:
    ```
    python3 app.py
    ```

    for window :
    ```
    python app.py
    ```


    5️⃣ เปิดเว็บเบราว์เซอร์
    เข้าไปที่: http://127.0.0.1:5000
    

