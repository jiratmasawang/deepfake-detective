# Handoff: UI redesign v2 (ทำต่อใน Claude Code)

Branch: `redesign-v2` — **ยังไม่ได้ทดสอบ ยังไม่ merge เข้า main**

## ทำแล้ว
- โลโก้ใหม่ "Shield Guard" (โล่ไล่สีฟ้า-ม่วง + ใบหน้าพิกเซล + แว่นขยาย) → `frontend/logo.svg`
- ไอคอนแอปใหม่: `icon-512.png`, `icon-192.png`, `apple-touch-icon.png`
- เขียน `frontend/index.html` ใหม่ทั้งไฟล์ตาม mockup (ธีม navy + ฟ้า/ม่วง):
  Splash → Login → Home (Hero + ปุ่มสแกนคลิป + เครื่องมือ + กฎเหล็ก) → Scan (คลิป/ลิงก์/ข้อความ)
  → Analyzing (เฟรมพรีวิว + วงหมุน) → Result (โล่สีตามระดับ + "ควรรู้อะไรบ้าง?" + ตรวจอีกครั้ง / บันทึกผล + แชร์)
  → History (เก็บใน localStorage, ค้นหา, ตัวกรอง ปลอดภัย/น่าสงสัย, ลบทั้งหมด) → Tips (3 สไลด์) → Quiz → AI ผู้ช่วย → ตั้งค่า
- แถบล่าง 3 ปุ่ม: หน้าหลัก / ประวัติ / โปรไฟล์ (ฟีเจอร์เดิมย้ายไปอยู่ในการ์ด "เครื่องมือ")
- ภาษา: ไทยทั่วไปแบบแอปทั่วไป ผสมศัพท์เทคนิคภาษาอังกฤษ (AI, Deepfake, Server, Quiz, Tips) — ไม่ต้องเขียนให้ผู้สูงอายุแล้ว
- เปลี่ยน "กฎทอง" → "กฎเหล็ก" ในฝั่ง frontend แล้ว

## ต้องทำต่อ
1. เปลี่ยน "กฎทอง" → "กฎเหล็ก" ใน backend: `scam_data.py`, `ai_client.py` (system prompt + fallback), `video_pipeline.py`, `main.py`
2. ปรับ system prompt ใน `ai_client.py`: เลิกบังคับ "ห้ามศัพท์เทคนิค / พูดกับผู้สูงอายุ" ให้ใช้ภาษาไทยทั่วไป ผสมศัพท์อังกฤษได้
3. อัปเดต `CLAUDE.md` กฎข้อ 2 (ภาษา) และข้อ 6 (ดีไซน์: navy #070b1f + gradient #4cb4ff→#3b82f6→#4f6bff, โลโก้ Shield Guard)
4. เพิ่ม `logo.svg` ใน `APP_FILES` ของ `frontend/sw.js` และเปลี่ยนชื่อ CACHE เป็น v8
5. รันจริงแล้วทดสอบทุกหน้า (มือถือ 390×844): `cd backend && pip install -r requirements.txt && python run.py`
   - เช็กว่าพิมพ์ใน input/textarea แล้วไม่หลุด focus
   - ทดสอบตรวจข้อความ, อัปโหลดคลิป, ลิงก์, ยกเลิกระหว่างตรวจ (ปุ่ม X / ถังขยะ), ประวัติ, บันทึกผล, แชร์
6. เทียบกับ mockup แล้วเกลาระยะ/ขนาดให้ตรง จากนั้น merge เข้า main
7. แอปบน Render ยัง deploy จาก repo เดิม `ronglaabyaso-web/deepfake-detector` — ต้องเชื่อม Render กับ repo นี้ใหม่ถ้าอยากให้เวอร์ชันออนไลน์อัปเดต
