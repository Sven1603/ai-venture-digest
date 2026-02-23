import puppeteer from "puppeteer";
import { readdirSync, mkdirSync } from "fs";

const url = process.argv[2];
const label = process.argv[3];
if (!url) {
  console.error("Usage: node screenshot.mjs <url> [label]");
  process.exit(1);
}

const dir = "./temporary screenshots";
mkdirSync(dir, { recursive: true });

const existing = readdirSync(dir).filter((f) => f.startsWith("screenshot-"));
const next =
  existing.reduce((max, f) => {
    const n = parseInt(f.match(/screenshot-(\d+)/)?.[1] || "0");
    return n > max ? n : max;
  }, 0) + 1;

const filename = label
  ? `screenshot-${next}-${label}.png`
  : `screenshot-${next}.png`;

const browser = await puppeteer.launch();
const page = await browser.newPage();
const width = parseInt(process.argv[4]) || 1280;
    await page.setViewport({ width, height: 800 });
await page.goto(url, { waitUntil: "networkidle2" });
await page.screenshot({ path: `${dir}/${filename}`, fullPage: true });
await browser.close();
console.log(`${dir}/${filename}`);
