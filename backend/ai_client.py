# -*- coding: utf-8 -*-
"""ตัวเชื่อม AI หลายเจ้า: auto (gemini → claude → ollama) → none (กฎพื้นฐาน)

- API key อยู่ฝั่ง backend เท่านั้น (อ่านจาก .env) ห้ามส่งไป frontend
- ถ้าไม่มี key เลย → โหมด "กฎพื้นฐาน" (none) ใช้ scam_data.match_patterns()
- ทุกคำตอบที่ส่งให้ผู้ใช้เป็นภาษาไทยทั่วไป ผสมศัพท์อังกฤษที่คนคุ้นได้ (AI, Deepfake, OTP)
"""
import json
import os

import httpx

import scam_data

# ---------------------------------------------------------------------------
# system prompt ภาษาไทย — ล็อกขอบเขตให้คุยเฉพาะเรื่องภัยออนไลน์
# ---------------------------------------------------------------------------
SYSTEM_PROMPT_CHAT = """คุณคือ "AI ผู้ช่วย" ของแอป Deepfake Detective ผู้ช่วยที่เป็นมิตรสำหรับคนไทย

หน้าที่ของคุณ:
- ตอบคำถามเรื่องมิจฉาชีพออนไลน์ คลิป Deepfake (วิดีโอ/เสียงที่ AI ปลอมขึ้น) ข้อความหลอกลวง และวิธีป้องกันตัว
- ใช้ภาษาไทยทั่วไปที่อ่านง่าย สั้น กระชับ ผสมศัพท์อังกฤษที่คนทั่วไปคุ้นได้ (เช่น AI, Deepfake, OTP, Link)
- เลี่ยงศัพท์เทคนิคเชิงลึกที่คนทั่วไปไม่รู้จัก ถ้าจำเป็นต้องใช้ให้อธิบายสั้น ๆ
- ถ้าผู้ใช้เล่าว่ากำลังถูกหลอกหรือโอนเงินไปแล้ว ให้บอกทันทีว่า: โทร 1441 (สายด่วนตำรวจไซเบอร์) เพื่ออายัดบัญชีให้เร็วที่สุด หรือ 191 ถ้าเป็นเหตุด่วน
- เน้นย้ำกฎเหล็ก 3 ข้อเมื่อเกี่ยวข้อง: (1) ถูกเร่งให้รีบตัดสินใจ เป็นสัญญาณอันตราย (2) วางสายแล้วโทรกลับไปยังเบอร์จริงด้วยตัวเอง (3) ห้ามโอนเงินและบอกรหัส ไม่ว่ากรณีใด

ขอบเขต:
- ถ้าถูกถามเรื่องอื่นที่ไม่เกี่ยวกับภัยออนไลน์/การหลอกลวง/ความปลอดภัย ให้ตอบสุภาพว่า "ขอโทษค่ะ ฉันตอบได้เฉพาะเรื่องภัยออนไลน์และการป้องกันมิจฉาชีพนะคะ" แล้วชวนกลับมาเรื่องความปลอดภัย
- ห้ามแนะนำวิธีโกงหรือหลอกลวงผู้อื่นเด็ดขาด
- ตอบไม่เกิน 6-8 ประโยคต่อครั้ง อ่านง่าย ใช้บรรทัดใหม่ช่วย
- ตอบเป็นข้อความธรรมดา ห้ามใช้ Markdown (ห้ามใช้ ** หรือ #)
- ห้ามใช้เครื่องหมายขีด (- – —) และเครื่องหมาย = ในคำตอบ ถ้าจะแจกแจงให้ใช้ 1. 2. 3. หรือ • แทน"""

SYSTEM_PROMPT_ANALYZE = """คุณคือผู้เชี่ยวชาญตรวจข้อความหลอกลวงสำหรับคนไทย วิเคราะห์ข้อความที่ผู้ใช้ส่งมาว่าเป็นข้อความมิจฉาชีพหรือไม่

ตอบเป็น JSON เท่านั้น (ไม่มีข้อความอื่น) รูปแบบ:
{"risk_percent": <0-95>, "verdict_th": "<สรุปสั้น 1 ประโยค>", "signals_th": ["<จุดสังเกต 1>", "<จุดสังเกต 2>", ...], "advice_th": "<คำแนะนำ 1-2 ประโยค>"}

กติกา:
- risk_percent: 0-95 เท่านั้น (ห้ามเกิน 95 เพราะไม่มีอะไรแน่นอน 100%)
- ห้ามใช้คำฟันธงเช่น "แน่นอน 100%" "ชัวร์" — ให้ใช้ "มีสัญญาณชัดเจนว่า..." "เข้าข่ายอย่างมาก" เพราะผลตรวจเป็นสัญญาณเตือน ไม่ใช่คำตัดสิน
- ทุกข้อความเป็นภาษาไทยทั่วไปที่อ่านง่าย ผสมศัพท์อังกฤษที่คนคุ้นได้ (เช่น OTP, Link, AI)
- ห้ามใช้เครื่องหมายขีด (- – —) และเครื่องหมาย = ในข้อความภาษาไทย
- signals_th: จุดสังเกตที่เจอในข้อความ 1-4 ข้อ (ถ้าปลอดภัยให้บอกว่าไม่พบสัญญาณอันตราย)
- ถ้าเสี่ยงสูง advice_th ต้องมี "โทร 1441" และเตือนอย่าโอนเงิน/กดลิงก์
- ระวังรูปแบบที่พบบ่อยในไทย: แก๊งคอลเซ็นเตอร์อ้างตำรวจ/บัญชีปลอดภัย, ลิงก์ปลอมดูดเงิน, ชวนลงทุนกำไรสูง, งานออนไลน์ให้เติมเงิน, หลอกให้รักแล้วขอเงิน, เงินกู้เถื่อน, ร้านค้าปลอม, หลอกถูกรางวัล, คลิป/เสียงปลอมขอยืมเงิน"""

SYSTEM_PROMPT_VISION = """คุณคือผู้เชี่ยวชาญแยกแยะว่า "วิดีโอนี้ถ่ายจากของจริง" หรือ "คอมพิวเตอร์สร้างขึ้น"
ภาพที่ให้มาคือภาพนิ่งหลายภาพจากคลิปเดียวกัน เรียงตามเวลาในคลิป

ให้ใช้เหตุผลตรวจ 4 ด้าน:
1. เป็นไปได้จริงในโลกนี้ไหม — สัตว์ทำท่าที่สัตว์จริงทำไม่ได้ (เช่น หมายืนสองขายกเวท แมวขับรถ), คนทำท่าที่ร่างกายมนุษย์ทำไม่ได้, ของลอยผิดแรงโน้มถ่วง, ขนาดหรือสัดส่วนผิดจากความจริงมาก
2. ร่องรอยของภาพที่คอมพิวเตอร์สร้าง — นิ้วมือเกินหรือขาด แขนขาบิดผิดรูป ของสองชิ้นกลืนเป็นชิ้นเดียว ตัวหนังสือมั่วอ่านไม่ออก พื้นผิวลื่นไม่มีรายละเอียด ฟันหรือหูผิดรูป
3. ฉากสมเหตุสมผลไหม — ทิศทางเงาไม่ตรงกับแสง เงาหายไป ภาพสะท้อนในกระจกหรือน้ำไม่ตรงกับของจริง
4. ความต่อเนื่องระหว่างภาพ — สิ่งของเปลี่ยนรูป เปลี่ยนจำนวน หรือหายไปเฉย ๆ ระหว่างภาพ

ตอบเป็น JSON เท่านั้น ไม่มีข้อความอื่น:
{"ai_generated_percent": <0-95>, "impossible_in_real_life": <true|false>, "has_human_face": <true|false>, "findings_th": ["<สิ่งที่เห็น 1>", ...], "summary_th": "<สรุปสั้น 1 ประโยค>"}

has_human_face: มีใบหน้าคนจริง ๆ ปรากฏชัดในภาพหรือไม่ (ถ้าเป็นวิว สัตว์ สิ่งของ หรือคนตัวเล็กมากจนไม่เห็นหน้า ให้ตอบ false)

กติกาการให้คะแนน (สำคัญมาก):
- 80-95 = เจอสิ่งที่เป็นไปไม่ได้ในความจริงอย่างชัดเจน เช่น สัตว์ทำกิจกรรมของคน หรือร่างกายผิดรูปแบบที่ของจริงเป็นไม่ได้
- 45-79 = มีหลายจุดน่าสงสัยแต่ยังพอเป็นไปได้ในความจริง
- 0-20 = คลิปธรรมดาที่ไม่พบความผิดปกติ
- ห้ามให้คะแนนสูงเพียงเพราะภาพเบลอ ภาพมืด ความละเอียดต่ำ หรือถ่ายด้วยมือถือรุ่นเก่า — สิ่งเหล่านี้เป็นเรื่องปกติของคลิปจริง
- ถ้าเป็นคลิปคนธรรมดาที่ดูปกติ ให้ตอบต่ำและ findings_th เป็น []

กติกาภาษา:
- findings_th: บอกเฉพาะสิ่งที่เห็นจริงในภาพ ห้ามเดา 1-4 ข้อ ภาษาไทยทั่วไปที่อ่านง่าย
- ผสมศัพท์อังกฤษที่คนคุ้นได้ (เช่น AI, Deepfake) แต่เลี่ยงศัพท์เทคนิคเชิงลึก
- ห้ามใช้เครื่องหมายขีด (- – —) และเครื่องหมาย = ในข้อความภาษาไทย"""

DISCLAIMER_TEXT_TH = (
    "ผลตรวจนี้เป็นเพียงสัญญาณเตือนให้ระวัง ไม่ใช่คำตัดสิน 100% "
    "หากยังไม่แน่ใจ อย่าโอนเงิน อย่ากดลิงก์ "
    "และลองปรึกษาคนใกล้ตัวหรือโทร 1441"
)


class AIClient:
    """เลือกผู้ให้บริการอัตโนมัติ: gemini → claude → ollama → none"""

    def __init__(self):
        self.provider = "none"
        self._gemini = None
        self._init_provider()

    # -- การเลือกผู้ให้บริการ -------------------------------------------------
    def _init_provider(self):
        want = os.environ.get("AI_PROVIDER", "auto").strip().lower()
        order = [want] if want in ("gemini", "claude", "ollama", "none") else ["gemini", "claude", "ollama"]
        for name in order:
            if name == "none":
                break
            try:
                if getattr(self, f"_try_{name}")():
                    self.provider = name
                    return
            except Exception:
                continue
        self.provider = "none"

    def _try_gemini(self) -> bool:
        key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not key:
            return False
        from google import genai  # import เมื่อจำเป็นเท่านั้น
        self._gemini = genai.Client(api_key=key)
        self._gemini_model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
        return True

    def _try_claude(self) -> bool:
        key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
        if not key:
            return False
        self._claude_key = key
        self._claude_model = os.environ.get("CLAUDE_MODEL", "claude-haiku-4-5-20251001")
        return True

    def _try_ollama(self) -> bool:
        url = os.environ.get("OLLAMA_URL", "http://localhost:11434").rstrip("/")
        try:
            r = httpx.get(f"{url}/api/tags", timeout=2)
            r.raise_for_status()
        except Exception:
            return False
        self._ollama_url = url
        self._ollama_model = os.environ.get("OLLAMA_MODEL", "llama3.2")
        return True

    # -- การเรียกโมเดล (ต่อผู้ให้บริการ) --------------------------------------
    def _generate(self, system: str, user: str) -> str:
        """เรียกโมเดลตาม provider ปัจจุบัน คืนข้อความล้วน (raise เมื่อพลาด)"""
        if self.provider == "gemini":
            from google.genai import types
            resp = self._gemini.models.generate_content(
                model=self._gemini_model,
                contents=user,
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    temperature=0.4,
                ),
            )
            return (resp.text or "").strip()
        if self.provider == "claude":
            r = httpx.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self._claude_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": self._claude_model,
                    "max_tokens": 1024,
                    "system": system,
                    "messages": [{"role": "user", "content": user}],
                },
                timeout=60,
            )
            r.raise_for_status()
            return r.json()["content"][0]["text"].strip()
        if self.provider == "ollama":
            r = httpx.post(
                f"{self._ollama_url}/api/chat",
                json={
                    "model": self._ollama_model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "stream": False,
                },
                timeout=120,
            )
            r.raise_for_status()
            return r.json()["message"]["content"].strip()
        raise RuntimeError("no provider")

    # -- ฟีเจอร์: ใช้เหตุผลกับภาพจากคลิป -------------------------------------
    def supports_vision(self) -> bool:
        """ตอนนี้รองรับการมองภาพเฉพาะ gemini และ claude"""
        return self.provider in ("gemini", "claude")

    def analyze_frames(self, frames_jpeg: list) -> dict | None:
        """ดูภาพนิ่งจากคลิปแล้วใช้เหตุผลว่าเป็นของจริงหรือคอมพิวเตอร์สร้าง

        คืน dict {ai_generated_percent, impossible_in_real_life, findings_th, summary_th}
        หรือ None เมื่อทำไม่ได้ (ผู้ให้บริการไม่รองรับ / เรียกพลาด)
        """
        if not frames_jpeg or not self.supports_vision():
            return None
        user_text = (
            f"ภาพต่อไปนี้คือ {len(frames_jpeg)} ภาพจากคลิปเดียวกัน เรียงตามเวลา "
            "ช่วยวิเคราะห์ตามกติกาแล้วตอบ JSON"
        )
        try:
            if self.provider == "gemini":
                from google.genai import types
                parts = [types.Part.from_bytes(data=b, mime_type="image/jpeg") for b in frames_jpeg]
                parts.append(types.Part.from_text(text=user_text))
                resp = self._gemini.models.generate_content(
                    model=self._gemini_model,
                    contents=parts,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT_VISION,
                        temperature=0.2,
                    ),
                )
                raw = (resp.text or "").strip()
            else:  # claude
                import base64
                content = [
                    {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                                 "data": base64.b64encode(b).decode()}}
                    for b in frames_jpeg
                ]
                content.append({"type": "text", "text": user_text})
                r = httpx.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={"x-api-key": self._claude_key, "anthropic-version": "2023-06-01",
                             "content-type": "application/json"},
                    json={"model": self._claude_model, "max_tokens": 1024,
                          "system": SYSTEM_PROMPT_VISION,
                          "messages": [{"role": "user", "content": content}]},
                    timeout=90,
                )
                r.raise_for_status()
                raw = r.json()["content"][0]["text"].strip()
            return self._parse_vision_json(raw)
        except Exception:
            return None

    @staticmethod
    def _parse_vision_json(raw: str):
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start == -1 or end == -1:
            return None
        data = json.loads(cleaned[start:end + 1])
        pct = max(0, min(95, int(float(data.get("ai_generated_percent", 0)))))
        findings = [str(f).strip() for f in data.get("findings_th", []) if str(f).strip()][:4]
        return {
            "ai_generated_percent": pct,
            "impossible_in_real_life": bool(data.get("impossible_in_real_life", False)),
            "has_human_face": bool(data.get("has_human_face", True)),
            "findings_th": findings,
            "summary_th": str(data.get("summary_th", "")).strip(),
        }

    # -- ฟีเจอร์: วิเคราะห์ข้อความ --------------------------------------------
    def analyze_text(self, text: str) -> dict:
        """วิเคราะห์ข้อความ/SMS คืน dict พร้อม disclaimer เสมอ

        ถ้า AI ใช้ไม่ได้ (ไม่มี key / เรียกพลาด) → ตกลงมาใช้กฎพื้นฐานเสมอ
        """
        matches = scam_data.match_patterns(text)
        result = None
        if self.provider != "none":
            try:
                raw = self._generate(SYSTEM_PROMPT_ANALYZE, f"ข้อความที่ต้องวิเคราะห์:\n{text}")
                result = self._parse_analysis_json(raw)
            except Exception:
                result = None
        if result is None:
            result = self._rule_based_analysis(text, matches)
            result["mode"] = "rules"
        else:
            result["mode"] = "ai"
            # เสริมจุดสังเกตจากกฎพื้นฐานที่ AI อาจไม่ได้พูดถึง
            for m in matches[:2]:
                note = f"เข้าข่าย: {m['name_th']}"
                if note not in result["signals_th"]:
                    result["signals_th"].append(note)
        result["matched_patterns"] = matches
        result["disclaimer_th"] = DISCLAIMER_TEXT_TH
        return result

    @staticmethod
    def _parse_analysis_json(raw: str):
        """ดึง JSON จากคำตอบโมเดล (ตัด markdown fence ถ้ามี)"""
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start == -1 or end == -1:
            return None
        data = json.loads(cleaned[start:end + 1])
        risk = max(0, min(95, int(data.get("risk_percent", 0))))
        signals = [str(s) for s in data.get("signals_th", [])][:5]
        return {
            "risk_percent": risk,
            "verdict_th": str(data.get("verdict_th", "")).strip() or "วิเคราะห์เรียบร้อยแล้ว",
            "signals_th": signals,
            "advice_th": str(data.get("advice_th", "")).strip(),
        }

    @staticmethod
    def _rule_based_analysis(text: str, matches) -> dict:
        """โหมดกฎพื้นฐาน — ไม่ต้องมี key ใด ๆ"""
        risk = scam_data.risk_from_matches(matches)
        if matches:
            top = matches[0]
            signals = []
            for m in matches[:3]:
                words = "“" + "”, “".join(m["matched_words"][:3]) + "”"
                signals.append(f"พบคำที่มิจฉาชีพมักใช้บ่อย: {words} (เข้าข่าย: {m['name_th']})")
            return {
                "risk_percent": risk,
                "verdict_th": f"ข้อความนี้มีลักษณะคล้าย “{top['name_th']}” ควรระวังเป็นพิเศษ",
                "signals_th": signals,
                "advice_th": top["warning_th"] + " หากเผลอโอนเงินไปแล้ว ให้รีบโทร 1441 ทันที",
            }
        return {
            "risk_percent": risk,
            "verdict_th": "ไม่พบข้อความที่เข้าข่ายมิจฉาชีพ",
            "signals_th": ["ไม่พบรูปแบบกลโกงที่ระบบรู้จัก แต่ควรใช้กฎเหล็ก 3 ข้อประกอบการตัดสินใจเสมอ"],
            "advice_th": "แม้จะไม่พบสัญญาณอันตราย ก็อย่าโอนเงินหรือบอกรหัสให้คนที่ติดต่อเข้ามาเอง",
        }

    # -- ฟีเจอร์: แชท -----------------------------------------------------------
    def chat(self, message: str, history: list | None = None) -> dict:
        """แชทกับผู้ช่วย คืน {'reply_th': ..., 'mode': 'ai'|'rules'}"""
        if self.provider != "none":
            try:
                convo = ""
                for turn in (history or [])[-6:]:
                    who = "ผู้ใช้" if turn.get("role") == "user" else "ผู้ช่วย"
                    convo += f"{who}: {turn.get('text', '')}\n"
                convo += f"ผู้ใช้: {message}\nผู้ช่วย:"
                reply = self._generate(SYSTEM_PROMPT_CHAT, convo)
                if reply:
                    return {"reply_th": reply, "mode": "ai"}
            except Exception:
                pass
        return {"reply_th": self._rule_based_chat(message), "mode": "rules"}

    @staticmethod
    def _rule_based_chat(message: str) -> str:
        """แชทโหมดกฎพื้นฐาน — ตอบจากฐานข้อมูลในเครื่อง"""
        msg = message.lower()
        # กำลังถูกหลอก/โอนเงินแล้ว → สายด่วนก่อนเลย
        urgent_words = ["โอนไปแล้ว", "โอนเงินไปแล้ว", "โดนหลอก", "ถูกหลอก", "เสียเงิน", "โดนโกง", "ถูกโกง"]
        if any(w in msg for w in urgent_words):
            return (
                "ใจเย็น ๆ นะคะ แล้วทำตามขั้นตอนนี้ทันทีค่ะ:\n"
                "1. โทร 1441 (สายด่วนตำรวจไซเบอร์) เพื่อขออายัดบัญชีปลายทาง "
                "ยิ่งโทรเร็วก็ยิ่งมีโอกาสได้เงินคืนค่ะ\n"
                "2. เก็บหลักฐานทุกอย่างไว้ เช่น สลิปโอนเงิน ข้อความ เบอร์โทร "
                "และชื่อบัญชี\n"
                "3. แจ้งความออนไลน์ได้ที่ thaipoliceonline.go.th\n"
                "\n"
                "คุณไม่ได้ทำอะไรผิดนะคะ มิจฉาชีพมีวิธีหลอกลวงที่แนบเนียนมาก "
                "ขอเป็นกำลังใจให้ค่ะ"
            )
        matches = scam_data.match_patterns(message)
        if matches:
            top = matches[0]
            return (
                f"จากที่เล่ามา มีลักษณะคล้าย “{top['name_th']}” ค่ะ\n\n"
                f"{top['warning_th']}\n\n"
                "และอย่าลืมกฎเหล็ก 3 ข้อไว้เสมอนะคะ ได้แก่ ถูกเร่งให้รีบตัดสินใจถือเป็นสัญญาณอันตราย "
                "วางสายแล้วโทรกลับไปยังเบอร์จริงด้วยตัวเอง และไม่โอนเงินหรือบอกรหัสไม่ว่ากรณีใดค่ะ"
            )
        rule_words = ["กฎเหล็ก", "กฎทอง", "ป้องกัน", "ทำยังไง", "ทำอย่างไร", "ระวัง"]
        if any(w in msg for w in rule_words):
            lines = ["กฎเหล็ก 3 ข้อที่ช่วยป้องกันมิจฉาชีพมีดังนี้ค่ะ:"]
            for r in scam_data.GOLDEN_RULES:
                lines.append(f"{r['icon']} {r['title_th']}")
            lines.append("\nหากมีข้อสงสัยเพิ่มเติม ถามได้เลยนะคะ หรือลองเปิด “Tips” ที่หน้าหลักเพื่อดูรายละเอียดเพิ่มเติมค่ะ")
            return "\n".join(lines)
        return (
            "สวัสดีค่ะ ฉันเป็น AI ผู้ช่วยเรื่องภัยออนไลน์นะคะ "
            "มีอะไรถามได้เลยค่ะ เช่น\n"
            "• “คลิปดาราชวนลงทุน เป็นเรื่องจริงไหม”\n"
            "• “มีคนโทรมาอ้างว่าเป็นตำรวจ ควรทำอย่างไรดี”\n"
            "• “โอนเงินไปแล้ว ต้องทำอย่างไรดี”\n"
            "หากเป็นเรื่องด่วน โทร 1441 (ตำรวจไซเบอร์) ได้ตลอด 24 "
            "ชั่วโมงค่ะ"
        )


# instance เดียวใช้ทั้งแอป (สร้างตอน import — อ่าน .env แล้วโดย main.py)
_client = None


def get_client() -> AIClient:
    global _client
    if _client is None:
        _client = AIClient()
    return _client
