// Optional browser verification. The application itself needs no Node runtime.
import { chromium } from "playwright";
import { spawn } from "node:child_process";
import { mkdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const base = "http://127.0.0.1:18777";
const server = spawn(process.env.OPSPILOT_PYTHON || "python", ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "18777", "--no-access-log"], {
  cwd: root, env: { ...process.env, OPSPILOT_MODE: "demo", OPSPILOT_API_TOKEN: "" }, stdio: ["ignore", "ignore", "pipe"]
});
let processError;
server.on("error", error => { processError = error; });
let browser;
try {
  let ready = false;
  for (let attempt = 0; attempt < 100; attempt++) {
    if (processError) throw processError;
    try { const response = await fetch(`${base}/readyz`); if (response.ok) { ready = true; break; } } catch {}
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  if (!ready) throw new Error("Demo server did not become ready; verify Python dependencies and port 18777.");
  const executablePath = process.env.OPSPILOT_BROWSER || undefined;
  browser = await chromium.launch({headless: true, executablePath, args: ["--no-sandbox"]});
  const page = await browser.newPage({viewport: {width: 1440, height: 1080}});
  const errors = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.goto(base);
  await page.waitForFunction(() => document.querySelector("#example").options.length > 1);
  await page.selectOption("#example", "0");
  await page.click("#submit");
  await page.waitForSelector("#results:not([hidden])");
  const summary = await page.locator("#summary").innerText();
  if (!summary.includes("memory")) throw new Error("Memory incident diagnosis was not displayed.");
  if (await page.locator("#sources details").count() !== 5) throw new Error("Missing source cards.");
  const assets = path.join(root, "docs/assets"); await mkdir(assets, {recursive: true});
  await page.screenshot({path: path.join(assets, "workspace.png"), fullPage: true});
  await page.selectOption("#example", "10");
  await page.click("#submit");
  await page.waitForSelector("#insufficient:not([hidden])");
  await page.setViewportSize({width: 390, height: 844});
  if (await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)) throw new Error("Mobile horizontal overflow.");
  await page.screenshot({path: path.join(assets, "mobile.png"), fullPage: true});
  if (errors.length) throw new Error(errors.join("; "));
  console.log(JSON.stringify({diagnosis_flow: "passed", insufficient_evidence_flow: "passed", javascript_errors: 0, mobile_horizontal_overflow: false}));
} finally {
  if (browser) await browser.close();
  server.kill();
}
