# Security Scan Test Report
**Project Name:** KU_FixIt (Flask Web Application)
**Date:** 21 March 2026
**Scanner Tool:** OWASP ZAP (Zed Attack Proxy)

---

## 1. Executive Summary
จากการสแกนความปลอดภัยเบื้องต้น พบช่องโหว่และข้อควรระวังทั้งหมด 13 รายการ โดยแบ่งเป็นระดับความเสี่ยงปานกลาง (Medium) และความเสี่ยงต่ำ/ข้อมูลทั่วไป (Low/Informational) ซึ่งจำเป็นต้องได้รับการปรับปรุงเพื่อความปลอดภัยของข้อมูลผู้ใช้งาน

---

## 2. Vulnerability Details

### 🟠 Medium Risk (ความเสี่ยงปานกลาง)

| Vulnerability | Description | Recommended Fix |
| :--- | :--- | :--- |
| **Absence of Anti-CSRF Tokens** | ขาดการใช้ Token ป้องกันการปลอมแปลงคำขอจากฝั่ง Client | ใช้งาน `Flask-WTF` และเพิ่ม `{{ form.csrf_token }}` ในทุกฟอร์ม HTML |
| **Missing Security Headers** | ขาด Header สำคัญ เช่น CSP, Anti-clickjacking | ตั้งค่า `Talisman` ใน Flask หรือกำหนด Header ใน Nginx |
| **Cookie without SameSite Attribute** | คุกกี้ไม่ได้ตั้งค่าขอบเขตการส่งข้อมูล | ตั้งค่า `SESSION_COOKIE_SAMESITE = 'Lax'` ในไฟล์ Config ของ Flask |
| **Insecure JS Source Inclusion** | มีการดึงไฟล์ JavaScript จากโดเมนภายนอกที่อาจไม่ปลอดภัย | ตรวจสอบแหล่งที่มาของ JS หรือใช้ Subresource Integrity (SRI) |

### 🔵 Low / Informational (ความเสี่ยงต่ำและข้อมูลทั่วไป)

| Vulnerability | Description | Recommended Fix |
| :--- | :--- | :--- |
| **Server Leaks Version Info** | เซิร์ฟเวอร์เปิดเผยข้อมูลเวอร์ชันผ่าน HTTP Header | ตั้งค่าปิดการแสดงผล `Server` header ในระดับ Web Server |
| **Sensitive Info in URL** | มีการส่งข้อมูลสำคัญผ่านทาง URL Query String | เปลี่ยนการส่งข้อมูลจากวิธี `GET` เป็น `POST` และส่งผ่าน Request Body |
| **X-Content-Type-Options** | ขาด Header ป้องกันการเดาประเภทไฟล์ (MIME sniffing) | เพิ่ม Header `X-Content-Type-Options: nosniff` |

---

## 3. Screenshots & Evidence
![Security Scan Results](./image_3fb9eb.png)
*รูปภาพแสดงรายการ Alert ที่ตรวจพบจากเครื่องมือสแกน*

---

## 4. Conclusion & Next Steps
1. **Immediate Action:** เร่งแก้ไขเรื่อง Anti-CSRF และ Security Headers เนื่องจากเป็นพื้นฐานสำคัญของ Web Security
2. **Configuration:** ปรับปรุงการตั้งค่า Flask Application ให้รองรับการทำงานแบบ Secure Session
3. **Re-test:** หลังจากแก้ไขแล้ว จะดำเนินการสแกนซ้ำอีกครั้งเพื่อยืนยันว่าช่องโหว่ถูกปิดเรียบร้อยแล้ว