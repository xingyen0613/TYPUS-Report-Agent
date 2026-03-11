#!/usr/bin/env node
/**
 * import-to-medium.js
 * Playwright 自動化：在 Medium 建立草稿
 *
 * 使用 playwright-extra + stealth plugin 繞過 Cloudflare bot 偵測
 * 使用 macOS AppKit 設定系統 clipboard HTML，讓 Medium 接收真實 paste 事件
 * 安全性：cookies 儲存於 ~/.config/typus-medium-session.json（repo 外）
 */

const { chromium } = require('playwright-extra');
const StealthPlugin = require('puppeteer-extra-plugin-stealth');
chromium.use(StealthPlugin());
const fs = require('fs');
const path = require('path');
const os = require('os');
const SESSION_FILE = path.join(os.homedir(), '.config', 'typus-medium-session.json');
const OUTPUTS_DIR = path.join(__dirname, '..', '..', '..', 'outputs');
const TEMP_HTML = path.join(os.tmpdir(), 'medium-paste-content.html');

const LAUNCH_OPTS = {
  headless: false,
  channel: 'chrome',
};

// 找最新的 *-medium-version.html
function findLatestHtml() {
  const dirs = [
    path.join(OUTPUTS_DIR, 'weekly', 'final'),
    path.join(OUTPUTS_DIR, 'monthly', 'final'),
  ];
  let latest = null;
  let latestMtime = 0;
  for (const dir of dirs) {
    if (!fs.existsSync(dir)) continue;
    for (const f of fs.readdirSync(dir)) {
      if (!f.endsWith('-medium-version.html')) continue;
      const fp = path.join(dir, f);
      const mtime = fs.statSync(fp).mtimeMs;
      if (mtime > latestMtime) {
        latestMtime = mtime;
        latest = fp;
      }
    }
  }
  return latest;
}

// 從 HTML 提取 H1 標題與 body 內文
function extractContent(htmlPath) {
  const raw = fs.readFileSync(htmlPath, 'utf8');
  const h1Match = raw.match(/<h1>([^<]+)<\/h1>/);
  const title = h1Match ? h1Match[1] : '';
  const bodyMatch = raw.match(/<body>([\s\S]*)<\/body>/);
  const bodyHtml = bodyMatch ? bodyMatch[1].trim() : raw;
  return { title, bodyHtml };
}

async function firstTimeLogin() {
  console.log('🔐 首次登入：開啟 Chrome 到 Medium 登入頁，請手動完成登入...');
  const browser = await chromium.launch(LAUNCH_OPTS);
  const context = await browser.newContext();
  const page = await context.newPage();
  await page.goto('https://medium.com/m/signin');

  console.log('⏳ 等待登入完成（最多 5 分鐘）...');
  await page.waitForFunction(
    () => window.location.hostname.includes('medium.com') &&
          !window.location.href.includes('/m/signin') &&
          !window.location.href.includes('/m/connect'),
    undefined,
    { timeout: 300000 }
  );
  await page.waitForTimeout(3000);
  console.log('✅ 登入成功，儲存 session...');

  const storageState = await context.storageState();
  fs.mkdirSync(path.dirname(SESSION_FILE), { recursive: true });
  fs.writeFileSync(SESSION_FILE, JSON.stringify(storageState, null, 2));
  console.log(`💾 Session 已儲存至 ${SESSION_FILE}`);
  await browser.close();
}

async function createDraft(htmlPath) {
  const { title, bodyHtml } = extractContent(htmlPath);
  console.log(`📄 HTML：${htmlPath}`);
  console.log(`📝 標題：${title}`);

  // 把 body HTML 寫入臨時檔案（去掉 h1，title 已分開填）
  const bodyWithoutTitle = bodyHtml.replace(/<h1>[^<]*<\/h1>\s*/, '');
  // 包一層 body 讓瀏覽器正確渲染，選取時不含 html/head 標籤
  fs.writeFileSync(TEMP_HTML, `<!DOCTYPE html><html><body>${bodyWithoutTitle}</body></html>`);

  const browser = await chromium.launch(LAUNCH_OPTS);
  const context = await browser.newContext({ storageState: SESSION_FILE });

  // Tab 1：Medium 編輯器
  const mediumPage = await context.newPage();
  await mediumPage.goto('https://medium.com/new-story', { waitUntil: 'domcontentloaded', timeout: 60000 });

  // 等 editor 初始化
  await mediumPage.waitForTimeout(3000);
  await mediumPage.mouse.click(640, 400);
  await mediumPage.waitForTimeout(3000);

  // 檢查是否被導向登入頁
  const currentUrl = mediumPage.url();
  if (currentUrl.includes('/m/signin') || currentUrl.includes('/m/connect') || currentUrl.includes('accounts.google.com')) {
    console.error('⚠️  Session 已失效，刪除舊 session，請重新執行以登入。');
    fs.unlinkSync(SESSION_FILE);
    await browser.close();
    process.exit(1);
  }

  // 填入標題
  await mediumPage.waitForSelector('[data-testid="editorTitleParagraph"]', { timeout: 15000 });
  await mediumPage.click('[data-testid="editorTitleParagraph"]');
  await mediumPage.keyboard.type(title);
  console.log('✏️  標題已輸入');

  // Tab 2：開臨時 HTML，全選複製（讓 Chrome 設定系統 clipboard）
  console.log('📋 開臨時 tab 複製內文...');
  const copyPage = await context.newPage();
  await copyPage.goto(`file://${TEMP_HTML}`, { waitUntil: 'domcontentloaded' });
  await copyPage.waitForTimeout(500);
  await copyPage.keyboard.press('Meta+A');
  await copyPage.waitForTimeout(300);
  await copyPage.keyboard.press('Meta+C');
  await copyPage.waitForTimeout(500);
  await copyPage.close();

  // 切回 Medium tab，focus body，貼上
  await mediumPage.bringToFront();
  await mediumPage.waitForSelector('[data-testid="editorParagraphText"]', { timeout: 10000 });
  await mediumPage.click('[data-testid="editorParagraphText"]');
  await mediumPage.waitForTimeout(500);

  await mediumPage.keyboard.press('Meta+V');
  console.log('📌 內文已貼上，等待 Medium 儲存...');
  await mediumPage.waitForTimeout(3000);

  // 清理臨時檔案
  try { fs.unlinkSync(TEMP_HTML); } catch {}

  const page = mediumPage;

  // 等待 URL 變為 /p/xxx/edit（Medium 自動儲存後）
  await page.waitForFunction(
    () => window.location.href.includes('/p/') && window.location.href.includes('/edit'),
    undefined,
    { timeout: 60000 }
  );

  const draftUrl = page.url();
  console.log(`\n✅ 草稿已建立！`);
  console.log(`🔗 草稿 URL：${draftUrl}`);
  console.log(`\n📋 下一步：`);
  console.log(`  1. 開啟草稿確認內容`);
  console.log(`  2. 加 tags、選封面圖`);
  console.log(`  3. 點 Publish`);

  // 儲存最新 cookies，保持瀏覽器開啟讓用戶確認內容
  const storageState = await context.storageState();
  fs.writeFileSync(SESSION_FILE, JSON.stringify(storageState, null, 2));

  // 給用戶 5 秒確認畫面後再關閉
  await page.waitForTimeout(5000);
  await browser.close();
}

(async () => {
  if (!fs.existsSync(SESSION_FILE)) {
    try {
      await firstTimeLogin();
    } catch (err) {
      if (err.message.includes('chrome') || err.message.includes('not found')) {
        console.error('❌ 找不到系統 Chrome，請確認已安裝 Google Chrome。');
        process.exit(1);
      }
      throw err;
    }
    console.log('\n🔄 登入完成，請重新執行 /publish-medium 建立草稿。');
    process.exit(0);
  }

  const htmlPath = findLatestHtml();
  if (!htmlPath) {
    console.error('❌ 找不到 *-medium-version.html，請先執行 /convert-report-format');
    process.exit(1);
  }

  await createDraft(htmlPath);
})();
