#!/usr/bin/env node
// paper_capsule_sweep.mjs — Anthropic Distill 웹논문의 "인터랙티브 생명성"을 로컬
// 재현 캡슐로 회수한다. headless Chrome(CDP 직접, npm 의존 0)으로 논문을 로드+스크롤
// 하며 런타임이 실제로 fetch 하는 자산(bundle.js·parquet·json·css·png…)을 네트워크
// 스윕으로 열거한 뒤, same-origin 자산을 서버 경로 그대로 로컬 docroot에 미러한다.
//
// 설계 근거 (2026-07-07, Opus×GPT 검토):
//   - Playwright 대신 CDP 직접: flake 에 nodejs_24, 호스트에 google-chrome-stable 존재.
//     Node 24 는 전역 WebSocket/fetch/crypto 를 제공하므로 추가 의존 없이 CDP 가능.
//   - "load + full-scroll sweep = complete baseline" 로 명명. jspace 는 모든 데이터를
//     선(先)로딩하여 스크롤 시 새 fetch 0 이지만, scroll+idle 은 저비용이라 항상 넣는다.
//   - URL 열거는 CDP, 실제 바이트 다운로드는 plain fetch (public CDN 자산, 쿠키 불필요).
//   - 원문 저작권 = Anthropic. 산출물은 out/ (gitignore). 도구/로직만 리포 자산.
//
// 사용:
//   node paper_capsule_sweep.mjs <URL> --out <capsule_dir> [--serve-check] [--no-scroll]
//
// 산출:
//   <capsule_dir>/<server-path...>            (미러된 자산, 서버 경로 보존)
//   <capsule_dir>/capsule-manifest.json       (provenance + 자산별 sha256/bytes/content-type)

import { spawn } from "node:child_process";
import { createHash } from "node:crypto";
import { mkdtempSync, existsSync, readFileSync, mkdirSync, writeFileSync } from "node:fs";
import { createServer } from "node:http";
import { tmpdir } from "node:os";
import { dirname, join, extname } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";

// ── 인자 파싱 ──────────────────────────────────────────────────────────
const argv = process.argv.slice(2);
const url = argv.find((a) => !a.startsWith("--"));
const getOpt = (flag) => {
  const i = argv.indexOf(flag);
  return i >= 0 && i + 1 < argv.length ? argv[i + 1] : null;
};
const outDir = getOpt("--out");
const serveCheck = argv.includes("--serve-check");
const noScroll = argv.includes("--no-scroll");

if (!url || !outDir) {
  console.error("사용법: node paper_capsule_sweep.mjs <URL> --out <capsule_dir> [--serve-check] [--no-scroll]");
  process.exit(2);
}

const CHROME_BIN =
  process.env.CHROME_BIN ||
  ["google-chrome-stable", "google-chrome", "chromium", "chromium-browser"].find((b) => which(b)) ||
  "google-chrome-stable";

function which(bin) {
  for (const dir of (process.env.PATH || "").split(":")) {
    if (dir && existsSync(join(dir, bin))) return join(dir, bin);
  }
  return null;
}

const log = (...a) => console.error("[capsule-sweep]", ...a);

// ── 아주 작은 CDP 클라이언트 (browser WS 위 flatten 세션) ────────────────
class CDP {
  constructor(ws) {
    this.ws = ws;
    this.id = 0;
    this.pending = new Map();
    this.listeners = [];
    ws.addEventListener("message", (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.id !== undefined && this.pending.has(msg.id)) {
        const { resolve, reject } = this.pending.get(msg.id);
        this.pending.delete(msg.id);
        msg.error ? reject(new Error(msg.error.message)) : resolve(msg.result);
      } else if (msg.method) {
        for (const fn of this.listeners) fn(msg);
      }
    });
  }
  send(method, params = {}, sessionId) {
    const id = ++this.id;
    const payload = { id, method, params };
    if (sessionId) payload.sessionId = sessionId;
    this.ws.send(JSON.stringify(payload));
    return new Promise((resolve, reject) => this.pending.set(id, { resolve, reject }));
  }
  on(fn) {
    this.listeners.push(fn);
  }
}

// ── Chrome 기동 + DevToolsActivePort 읽기 ────────────────────────────────
async function launchChrome() {
  const udd = mkdtempSync(join(tmpdir(), "capsule-chrome-"));
  const args = [
    "--headless=new",
    "--disable-gpu",
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-dev-shm-usage",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-extensions",
    "--disable-background-networking",
    "--window-size=1400,2200",
    "--remote-debugging-port=0",
    `--user-data-dir=${udd}`,
    "about:blank",
  ];
  log(`chrome: ${CHROME_BIN}`);
  const proc = spawn(CHROME_BIN, args, { stdio: ["ignore", "ignore", "ignore"] });
  const portFile = join(udd, "DevToolsActivePort");
  for (let i = 0; i < 100; i++) {
    if (existsSync(portFile)) {
      const port = readFileSync(portFile, "utf8").split("\n")[0].trim();
      if (port) return { proc, port };
    }
    await sleep(100);
  }
  proc.kill("SIGKILL");
  throw new Error("DevToolsActivePort 를 못 읽음 (Chrome 기동 실패)");
}

// ── 한 URL 을 스윕: 로드 + 스크롤 + idle, 요청 열거 반환 ──────────────────
async function sweep(pageUrl, { scroll } = { scroll: true }) {
  const { proc, port } = await launchChrome();
  try {
    const ver = await (await fetch(`http://127.0.0.1:${port}/json/version`)).json();
    const ws = new WebSocket(ver.webSocketDebuggerUrl);
    await new Promise((res, rej) => {
      ws.addEventListener("open", res, { once: true });
      ws.addEventListener("error", rej, { once: true });
    });
    const cdp = new CDP(ws);

    const { targetId } = await cdp.send("Target.createTarget", { url: "about:blank" });
    const { sessionId } = await cdp.send("Target.attachToTarget", { targetId, flatten: true });

    // 네트워크 상태 추적
    const requests = new Map(); // requestId -> {url,type}
    const statuses = new Map(); // url -> status
    const inflight = new Set();
    let lastActivity = Date.now();
    let loaded = false;

    cdp.on((msg) => {
      if (msg.sessionId !== sessionId) return;
      const p = msg.params || {};
      switch (msg.method) {
        case "Network.requestWillBeSent":
          requests.set(p.requestId, { url: p.request.url, type: p.type });
          inflight.add(p.requestId);
          lastActivity = Date.now();
          break;
        case "Network.responseReceived":
          statuses.set(p.response.url, p.response.status);
          lastActivity = Date.now();
          break;
        case "Network.loadingFinished":
        case "Network.loadingFailed":
          inflight.delete(p.requestId);
          lastActivity = Date.now();
          break;
        case "Page.loadEventFired":
          loaded = true;
          lastActivity = Date.now();
          break;
      }
    });

    await cdp.send("Page.enable", {}, sessionId);
    await cdp.send("Network.enable", {}, sessionId);
    await cdp.send("Runtime.enable", {}, sessionId);
    await cdp.send("Page.navigate", { url: pageUrl }, sessionId);

    // load 대기
    for (let i = 0; i < 300 && !loaded; i++) await sleep(100);
    await waitIdle(inflight, () => lastActivity, 1500, 15000);

    if (scroll) {
      const h = await evalNum(cdp, sessionId, "document.body.scrollHeight");
      const vh = await evalNum(cdp, sessionId, "window.innerHeight");
      const step = Math.max(400, Math.floor(vh * 0.8));
      for (let y = 0; y <= h; y += step) {
        await cdp.send("Runtime.evaluate", { expression: `window.scrollTo(0, ${y})` }, sessionId);
        await sleep(250);
      }
      await cdp.send("Runtime.evaluate", { expression: `window.scrollTo(0, document.body.scrollHeight)` }, sessionId);
      await waitIdle(inflight, () => lastActivity, 1500, 20000);
    }

    // 요청 정리 (중복 URL dedupe, 상태 병합)
    const seen = new Map();
    for (const { url: u, type } of requests.values()) {
      if (!seen.has(u)) seen.set(u, { url: u, type, status: statuses.get(u) ?? null });
    }
    await cdp.send("Target.closeTarget", { targetId });
    ws.close();
    return [...seen.values()];
  } finally {
    proc.kill("SIGKILL");
  }
}

async function evalNum(cdp, sessionId, expr) {
  const r = await cdp.send("Runtime.evaluate", { expression: expr, returnByValue: true }, sessionId);
  return Number(r.result?.value) || 0;
}

async function waitIdle(inflight, getLast, idleMs, maxMs) {
  const start = Date.now();
  while (Date.now() - start < maxMs) {
    if (inflight.size === 0 && Date.now() - getLast() > idleMs) return;
    await sleep(200);
  }
}

// ── 미러: same-origin 자산을 서버 경로 그대로 다운로드 ────────────────────
function urlToLocal(u, origin, root) {
  const { pathname } = new URL(u);
  let rel = pathname.replace(/^\//, "");
  if (rel === "" || rel.endsWith("/")) rel += "index.html";
  return join(root, rel);
}

async function mirror(requests, origin, root) {
  const assets = [];
  const external = [];
  const failed = [];
  for (const req of requests) {
    if (req.url.startsWith("data:")) continue;
    let reqOrigin;
    try {
      reqOrigin = new URL(req.url).origin;
    } catch {
      continue;
    }
    if (reqOrigin !== origin) {
      external.push(req.url);
      continue;
    }
    const dest = urlToLocal(req.url, origin, root);
    try {
      const res = await fetch(req.url, { headers: { "User-Agent": "Mozilla/5.0 (capsule-sweep)" } });
      if (!res.ok) {
        failed.push({ url: req.url, status: res.status });
        continue;
      }
      const buf = Buffer.from(await res.arrayBuffer());
      mkdirSync(dirname(dest), { recursive: true });
      writeFileSync(dest, buf);
      assets.push({
        url: req.url,
        local_path: dest.slice(root.length + 1),
        status: res.status,
        content_type: res.headers.get("content-type") || "",
        bytes: buf.length,
        sha256: createHash("sha256").update(buf).digest("hex"),
      });
    } catch (e) {
      failed.push({ url: req.url, status: String(e.message || e) });
    }
  }
  return { assets, external, failed };
}

// ── 오프라인 검증: docroot 를 로컬 서버로 띄우고 재스윕, 외부요청 0 단언 ──
async function serveAndVerify(root, pagePath) {
  const server = createServer((rq, rs) => {
    const p = decodeURIComponent(new URL(rq.url, "http://x").pathname).replace(/^\//, "");
    const f = join(root, p || "index.html");
    if (!f.startsWith(root) || !existsSync(f)) {
      rs.statusCode = 404;
      return rs.end("not found");
    }
    rs.setHeader("Content-Type", mimeOf(f));
    rs.end(readFileSync(f));
  });
  await new Promise((r) => server.listen(0, "127.0.0.1", r));
  const port = server.address().port;
  try {
    const reqs = await sweep(`http://127.0.0.1:${port}/${pagePath}`, { scroll: !noScroll });
    const origin = `http://127.0.0.1:${port}`;
    const ext = reqs.filter((r) => !r.url.startsWith("data:") && safeOrigin(r.url) !== origin);
    const bad = reqs.filter((r) => r.status && r.status >= 400 && !r.url.endsWith("/favicon.ico"));
    return { total: reqs.length, external: ext.map((r) => r.url), bad };
  } finally {
    server.close();
  }
}

function safeOrigin(u) {
  try {
    return new URL(u).origin;
  } catch {
    return null;
  }
}

function mimeOf(f) {
  const e = extname(f).toLowerCase();
  return (
    {
      ".html": "text/html; charset=utf-8",
      ".js": "application/javascript; charset=utf-8",
      ".mjs": "application/javascript; charset=utf-8",
      ".css": "text/css; charset=utf-8",
      ".json": "application/json; charset=utf-8",
      ".png": "image/png",
      ".svg": "image/svg+xml",
      ".woff2": "font/woff2",
      ".parquet": "application/octet-stream",
      ".npy": "application/octet-stream",
      ".bib": "text/plain; charset=utf-8",
      ".csv": "text/csv",
    }[e] || "application/octet-stream"
  );
}

// ── main ──────────────────────────────────────────────────────────────
(async () => {
  const origin = new URL(url).origin;
  const pagePath = new URL(url).pathname.replace(/^\//, "");
  log(`sweep 시작: ${url}`);
  const requests = await sweep(url, { scroll: !noScroll });
  log(`요청 ${requests.length}개 열거. same-origin 미러 시작 → ${outDir}`);

  mkdirSync(outDir, { recursive: true });
  const { assets, external, failed } = await mirror(requests, origin, outDir);
  const totalBytes = assets.reduce((s, a) => s + a.bytes, 0);

  const manifest = {
    source_url: url,
    origin,
    captured_at: new Date().toISOString(),
    browser: CHROME_BIN,
    sweep: { mode: noScroll ? "load-only" : "load+scroll", request_count: requests.length },
    asset_count: assets.length,
    total_bytes: totalBytes,
    external_requests: external,
    failed_requests: failed,
    assets,
  };
  writeFileSync(join(outDir, "capsule-manifest.json"), JSON.stringify(manifest, null, 2));

  log(`미러 완료: ${assets.length} 파일 / ${(totalBytes / 1024 / 1024).toFixed(1)} MB`);
  log(`external(비-미러) 요청: ${external.length}, 실패: ${failed.length}`);
  if (external.length) external.forEach((u) => log("  external:", u));
  if (failed.length) failed.forEach((f) => log("  실패:", f.url, f.status));

  if (serveCheck) {
    log("오프라인 검증: docroot 재스윕 중…");
    const v = await serveAndVerify(outDir, pagePath);
    const pass = v.external.length === 0 && v.bad.length === 0;
    log(`재스윕 요청 ${v.total}개, 외부요청 ${v.external.length}, 4xx/5xx ${v.bad.length}`);
    if (v.external.length) v.external.forEach((u) => log("  누출:", u));
    if (v.bad.length) v.bad.forEach((r) => log("  bad:", r.status, r.url));
    log(pass ? "✅ 오프라인 캡슐 검증 PASS (외부요청 0)" : "❌ 캡슐 불완전");
    if (!pass) process.exit(1);
  }

  console.log(join(outDir, "capsule-manifest.json"));
})().catch((e) => {
  console.error("[capsule-sweep] 오류:", e);
  process.exit(1);
});
