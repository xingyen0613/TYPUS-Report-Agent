#!/usr/bin/env node
/**
 * import-to-medium.js
 * Playwright 自動化：在 Medium 建立草稿
 *
 * 使用 playwright-extra + stealth plugin 繞過 Cloudflare bot 偵測
 * 安全性：cookies 儲存於 ~/.config/typus-medium-session.json（repo 外）
 *
 * 圖片策略：
 *   - 在 Medium 編輯器 tab 上呼叫 fetch() 上傳 PNG 至 Medium CDN
 *   - 取得 fileId 後組出 miro.medium.com CDN URL
 *   - 用 CDN URL 替換佔位符寫入 temp HTML
 *   - copy-paste 時 Medium 不會 strip 自家 CDN 的 img src
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

// 找對應的 30D performance PNG
function findMatchingPng(htmlPath) {
  const dir = path.dirname(htmlPath);
  const base = path.basename(htmlPath).replace('-medium-version.html', '');
  const pngPath = path.join(dir, `${base}-30d-performance.png`);
  return fs.existsSync(pngPath) ? pngPath : null;
}

// 上傳 PNG 至 Medium CDN，回傳 CDN URL（失敗則回傳 null）
// 使用獨立 tab + Medium 編輯器原生 UI 上傳（最可靠）
async function uploadImageToMedium(context, pngPath) {
  console.log(`🌐 上傳圖片至 Medium CDN：${path.basename(pngPath)}`);

  const uploadPage = await context.newPage();
  await uploadPage.goto('https://medium.com/new-story', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await uploadPage.waitForTimeout(3000);

  // 攔截 /_/upload 回應取得 fileId
  let uploadedFileId = null;
  uploadPage.on('response', async resp => {
    if (!resp.url().includes('/_/upload')) return;
    try {
      const text = await resp.text();
      const start = text.search(/\{/);
      if (start < 0) return;
      const parsed = JSON.parse(text.substring(start));
      if (parsed?.success) {
        uploadedFileId = parsed.payload?.value?.fileId || null;
      }
    } catch {}
  });

  // 點 paragraph 讓 cursor 在 body
  await uploadPage.waitForSelector('[data-testid="editorParagraphText"]', { timeout: 15000 });
  await uploadPage.click('[data-testid="editorParagraphText"]');
  await uploadPage.waitForTimeout(500);

  // 點 "+" 按鈕
  const addBtn = uploadPage.locator('[data-testid="editorAddButton"]');
  await addBtn.scrollIntoViewIfNeeded();
  await addBtn.click();
  await uploadPage.waitForTimeout(500);

  // 點 "Add an image" 並攔截 file chooser
  const [fileChooser] = await Promise.all([
    uploadPage.waitForEvent('filechooser', { timeout: 10000 }),
    uploadPage.click('button[aria-label="Add an image"]'),
  ]);
  await fileChooser.setFiles(pngPath);
  console.log(`   已選擇檔案，等待上傳完成...`);

  // 等待 uploadedFileId 被設置（最多 30 秒）
  const deadline = Date.now() + 30000;
  while (!uploadedFileId && Date.now() < deadline) {
    await uploadPage.waitForTimeout(500);
  }

  await uploadPage.close();

  if (uploadedFileId) {
    const cdnUrl = `https://miro.medium.com/v2/resize:fit:1400/${uploadedFileId}`;
    console.log(`✅ 圖片上傳成功 → ${cdnUrl}`);
    return cdnUrl;
  } else {
    console.warn(`⚠️  圖片上傳失敗：未收到 fileId`);
    return null;
  }
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

  let bodyWithoutTitle = bodyHtml.replace(/<h1>[^<]*<\/h1>\s*/, '');
  const pngPath = findMatchingPng(htmlPath);

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

  // 先確認 editor 已載入並填入標題
  await mediumPage.waitForSelector('[data-testid="editorTitleParagraph"]', { timeout: 30000 });
  await mediumPage.click('[data-testid="editorTitleParagraph"]');
  await mediumPage.keyboard.type(title);
  console.log('✏️  標題已輸入');

  // 上傳 PNG 至 Medium CDN（editor 確認後再上傳，走瀏覽器網路堆疊）
  if (pngPath) {
    const cdnUrl = await uploadImageToMedium(context, pngPath);
    if (cdnUrl) {
      bodyWithoutTitle = bodyWithoutTitle.replace(
        '<p>[Image: 30-Day Comparison Chart]</p>',
        `<figure><img src="${cdnUrl}" alt="30-Day Comparison Chart"></figure>`
      );
    }
  }

  // 包一層 body 讓瀏覽器正確渲染
  fs.writeFileSync(TEMP_HTML, `<!DOCTYPE html><html><body>${bodyWithoutTitle}</body></html>`);

  // Tab 2：開臨時 HTML，全選複製
  console.log('📋 開臨時 tab 複製內文...');
  const copyPage = await context.newPage();
  await copyPage.goto(`file://${TEMP_HTML}`, { waitUntil: 'networkidle' });
  // 等圖片完全載入
  await copyPage.evaluate(() => {
    return Promise.all(
      Array.from(document.images).map(img =>
        img.complete ? Promise.resolve() : new Promise(r => { img.onload = r; img.onerror = r; })
      )
    );
  });
  await copyPage.waitForTimeout(500);
  await copyPage.evaluate(() => {
    document.execCommand('selectAll');
    document.execCommand('copy');
  });
  await copyPage.waitForTimeout(500);
  await copyPage.close();

  // 切回 Medium tab，focus body，貼上
  await mediumPage.bringToFront();
  await mediumPage.waitForSelector('[data-testid="editorParagraphText"]', { timeout: 10000 });
  await mediumPage.click('[data-testid="editorParagraphText"]');
  await mediumPage.waitForTimeout(500);

  await mediumPage.keyboard.press('Meta+V');
  console.log('📌 內文已貼上，等待 Medium 儲存...');
  await mediumPage.waitForTimeout(5000);

  // 清理臨時檔案
  try { fs.unlinkSync(TEMP_HTML); } catch {}

  // 等待 URL 變為 /p/xxx/edit（Medium 自動儲存後）
  await mediumPage.waitForFunction(
    () => window.location.href.includes('/p/') && window.location.href.includes('/edit'),
    undefined,
    { timeout: 60000 }
  );

  const draftUrl = mediumPage.url();
  console.log(`\n✅ 草稿已建立！`);
  console.log(`🔗 草稿 URL：${draftUrl}`);

  // 掃描剩餘未替換的圖片佔位符
  const remainingImages = [...bodyWithoutTitle.matchAll(/\[Image: ([^\]]+)\]/g)].map(m => m[0]);
  if (remainingImages.length > 0) {
    console.log(`\n⚠️  以下圖片需手動加入草稿：`);
    for (const img of remainingImages) {
      console.log(`  - ${img}`);
    }
  }

  console.log(`\n📋 下一步：`);
  console.log(`  1. 開啟草稿確認內容`);
  console.log(`  2. 加 tags、選封面圖`);
  console.log(`  3. 點 Publish`);

  // 儲存最新 cookies，保持瀏覽器開啟讓用戶確認內容
  const storageState = await context.storageState();
  fs.writeFileSync(SESSION_FILE, JSON.stringify(storageState, null, 2));

  // 給用戶 5 秒確認畫面後再關閉
  await mediumPage.waitForTimeout(5000);
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
