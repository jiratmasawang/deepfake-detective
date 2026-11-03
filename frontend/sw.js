/* service worker — ให้ติดตั้งเป็นแอปได้ + เปิดหน้าแอปได้แม้เน็ตช้า
   กลยุทธ์: หน้าเว็บ/ไฟล์แอปใช้ network-first (ได้ของใหม่เสมอ ถ้าเน็ตล่มใช้ของเก็บไว้)
   ส่วน /api ไม่เก็บเลย (ผลตรวจต้องสดเสมอ)
   ไฟล์ของแอปโหลดแบบไม่ใช้ของที่เบราว์เซอร์จำไว้ — กันมือถือค้างหน้าเก่าหลัง deploy
   ถ้า Server ตอบช้าเกิน 4 วินาที (เช่น Render กำลังตื่น) เปิดจากของเก็บไว้ก่อน แล้วโหลดของใหม่ไว้ใช้ครั้งหน้า */
const CACHE = "fakeclip-helper-v10";
const SLOW_MS = 4000;
const APP_FILES = ["./", "./index.html", "./manifest.json", "./icon-192.png", "./icon-512.png", "./logo.svg"];

self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open(CACHE)
      .then((c) => c.addAll(APP_FILES.map((u) => new Request(u, { cache: "reload" }))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.pathname.includes("/api/")) return; // API สดเสมอ
  const fresh = url.origin === self.location.origin ? { cache: "no-cache" } : {}; // ฟอนต์ภายนอกใช้แคชปกติ
  const net = fetch(e.request, fresh).then((res) => {
    if (res.ok) { // ไม่เก็บหน้า error ทับของดี (เผื่อ Server ล่มชั่วคราว)
      const copy = res.clone();
      caches.open(CACHE).then((c) => c.put(e.request, copy)).catch(() => {});
    }
    return res;
  });
  e.waitUntil(net.catch(() => {})); // ให้โหลดต่อจนเสร็จแม้ตอบจากของเก็บไว้ไปแล้ว
  const slow = new Promise((r) => setTimeout(r, SLOW_MS)).then(() => caches.match(e.request)).then((hit) => hit || net);
  e.respondWith(
    Promise.race([net, slow])
      .catch(() => caches.match(e.request).then((hit) => hit || caches.match("./index.html")))
  );
});
