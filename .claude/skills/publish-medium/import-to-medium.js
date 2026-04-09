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

// 找對應的 PNG（依後綴名）
function findMatchingPng(htmlPath, suffix) {
  const dir = path.dirname(htmlPath);
  const base = path.basename(htmlPath).replace('-medium-version.html', '');
  // Try full base name first, then strip trailing '-report' (e.g. week-5-march-2026-report → week-5-march-2026)
  const candidates = [
    path.join(dir, `${base}-${suffix}.png`),
    path.join(dir, `${base.replace(/-report$/, '')}-${suffix}.png`),
  ];
  for (const p of candidates) {
    if (fs.existsSync(p)) return p;
  }
  return null;
}

// 上傳 PNG 至 Medium CDN，回傳 CDN URL（失敗則回傳 null）
// 在 uploadPage（throwaway 頁面）上傳，不影響 main editor 狀態
// 每次上傳後圖片留在 uploadPage（不 undo），下次用 .last() 找最後的空段落
async function uploadImageToMedium(uploadPage, pngPath) {
  console.log(`🌐 上傳圖片至 Medium CDN：${path.basename(pngPath)}`);

  let uploadedFileId = null;
  const responseHandler = async resp => {
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
  };
  uploadPage.on('response', responseHandler);

  // 用 .last() 找最後一個空段落（前幾張圖已插入後，每次都在最後面新增）
  const para = uploadPage.locator('[data-testid="editorParagraphText"]').last();
  await para.waitFor({ timeout: 10000 });
  await para.click();
  await uploadPage.waitForTimeout(500);

  // 點 "+" 按鈕
  const addBtn = uploadPage.locator('[data-testid="editorAddButton"]');
  await addBtn.scrollIntoViewIfNeeded();
  await addBtn.click();
  await uploadPage.waitForTimeout(500);

  // 點 "Add an image" 並上傳檔案
  const [fileChooser] = await Promise.all([
    uploadPage.waitForEvent('filechooser', { timeout: 10000 }),
    uploadPage.click('button[aria-label="Add an image"]'),
  ]);
  await fileChooser.setFiles(pngPath);
  console.log(`   已選擇檔案，等待上傳完成...`);

  // 等待 fileId（最多 30 秒）
  const deadline = Date.now() + 30000;
  while (!uploadedFileId && Date.now() < deadline) {
    await uploadPage.waitForTimeout(500);
  }

  uploadPage.off('response', responseHandler);

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
  const pngCover       = findMatchingPng(htmlPath, 'cover');
  const png30d         = findMatchingPng(htmlPath, '30d-performance');
  const pngOiDist      = findMatchingPng(htmlPath, 'oi-distribution');
  const pngDailyPnl    = findMatchingPng(htmlPath, 'daily-pnl');
  const pngLiquidation = findMatchingPng(htmlPath, 'daily-liquidation');
  const pngDau         = findMatchingPng(htmlPath, 'daily-dau');
  const pngVolume      = findMatchingPng(htmlPath, 'daily-volume');
  const pngOiHistory   = findMatchingPng(htmlPath, 'oi-history');
  const pngTlpPrice    = findMatchingPng(htmlPath, 'tlp-price');
  const pngFeeBreak    = findMatchingPng(htmlPath, 'fee-breakdown');

  if (pngCover) {
    bodyWithoutTitle = '<p>[Image: Cover]</p>\n' + bodyWithoutTitle;
    console.log(`🖼️  偵測到封面圖：${path.basename(pngCover)}`);
  }

  const browser = await chromium.launch(LAUNCH_OPTS);
  const context = await browser.newContext({ storageState: SESSION_FILE });

  // 圖片定義：placeholder 文字對應的 PNG 路徑（含舊格式 altPlaceholder 相容）
  const uploads = [
    { pngPath: pngCover,       placeholder: '[Image: Cover]'                                                                        },
    { pngPath: png30d,         placeholder: '[Image: 30-Day Comparison Chart]'                                                      },
    { pngPath: pngVolume,      placeholder: '[Image: Daily Volume Chart]',      altPlaceholder: '[Image: Weekly Volume Chart]'      },
    { pngPath: pngDau,         placeholder: '[Image: DAU Chart]'                                                                    },
    { pngPath: pngTlpPrice,    placeholder: '[Image: TLP Price Chart]'                                                              },
    { pngPath: pngFeeBreak,    placeholder: '[Image: Fee Breakdown]'                                                                },
    { pngPath: pngDailyPnl,    placeholder: '[Image: Daily PnL Chart]'                                                              },
    { pngPath: pngLiquidation, placeholder: '[Image: Liquidation Chart]'                                                            },
    { pngPath: pngOiHistory,   placeholder: '[Image: OI History Chart]'                                                             },
    { pngPath: pngOiDist,      placeholder: '[Image: OI Distribution Chart]',   altPlaceholder: '[Image: OI Distribution]'         },
  ];

  // 包一層 body 讓瀏覽器正確渲染（圖片 placeholder 保留為文字，不替換）
  fs.writeFileSync(TEMP_HTML, `<!DOCTYPE html><html><body>${bodyWithoutTitle}</body></html>`);

  // ── Phase 1：建立 draft（乾淨的 mediumPage）──
  console.log('📝 Phase 1：建立 Medium 草稿...');
  const mediumPage = await context.newPage();
  let editorReady = false;
  for (let attempt = 1; attempt <= 3; attempt++) {
    await mediumPage.goto('https://medium.com/new-story', { waitUntil: 'domcontentloaded', timeout: 60000 });
    await mediumPage.waitForTimeout(8000);
    const hasEditor = await mediumPage.locator('[data-testid="editorTitleParagraph"]').isVisible().catch(() => false);
    if (hasEditor) { editorReady = true; break; }
    console.log(`⚠️  Editor 未初始化（attempt ${attempt}/3），重試...`);
    await mediumPage.waitForTimeout(5000);
  }
  if (!editorReady) {
    await mediumPage.screenshot({ path: '/tmp/medium-debug.png' });
    console.error(`⚠️  截圖已儲存至 /tmp/medium-debug.png（URL: ${mediumPage.url()}）`);
    await browser.close();
    process.exit(1);
  }

  // 檢查是否被導向登入頁
  const currentUrl = mediumPage.url();
  if (currentUrl.includes('/m/signin') || currentUrl.includes('/m/connect') || currentUrl.includes('accounts.google.com')) {
    console.error('⚠️  Session 已失效，刪除舊 session，請重新執行以登入。');
    fs.unlinkSync(SESSION_FILE);
    await browser.close();
    process.exit(1);
  }

  // 填入標題
  await mediumPage.click('[data-testid="editorTitleParagraph"]');
  await mediumPage.keyboard.type(title);
  console.log('✏️  標題已輸入');

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

  // ── Phase 2：用 editor UI 將各 placeholder 替換為真實圖片 ──
  console.log('🖼️  Phase 2：插入圖片...');
  const uploadedTexts = new Set(); // 記錄成功上傳的 foundTxt，用於後續 warning 過濾
  for (const { pngPath, placeholder, altPlaceholder } of uploads) {
    if (!pngPath) continue;

    // 找 placeholder 文字（試主名稱與舊格式別名），記錄實際找到的文字
    let foundTxt = null;
    for (const txt of [placeholder, altPlaceholder].filter(Boolean)) {
      const el = mediumPage.getByText(txt, { exact: false }).first();
      if (await el.isVisible().catch(() => false)) { foundTxt = txt; break; }
    }
    if (!foundTxt) { console.log(`ℹ️  未找到佔位符，跳過：${placeholder}`); continue; }

    const targetEl = mediumPage.getByText(foundTxt, { exact: false }).first();
    console.log(`🌐 插入：${placeholder}`);
    await targetEl.scrollIntoViewIfNeeded();
    // 取得 placeholder 位置（Enter 後新空段落在其正下方）
    const targetBox = await targetEl.boundingBox();
    await targetEl.click();
    await mediumPage.waitForTimeout(300);

    // 在佔位符段落末尾按 Enter，建立全新空段落（空段落才能觸發 "+" 按鈕）
    await mediumPage.keyboard.press('End');
    await mediumPage.keyboard.press('Enter');
    await mediumPage.waitForTimeout(500);

    // 取得新空段落的 name 屬性，再用 Playwright native click 確保 "+" 按鈕出現在正確位置
    const newParaName = await mediumPage.evaluate(() => {
      const sel = window.getSelection();
      if (!sel || !sel.rangeCount) return null;
      const node = sel.getRangeAt(0).startContainer;
      const el = node.nodeType === 3 ? node.parentElement : node;
      return el?.getAttribute('name') ?? null;
    });
    if (newParaName) {
      await mediumPage.locator(`[name="${newParaName}"]`).click();
    } else {
      // fallback：點 placeholder 下方的下一個 paragraph
      const allParas = mediumPage.locator('[data-testid="editorParagraphText"]');
      const count = await allParas.count();
      for (let i = 0; i < count; i++) {
        const txt = await allParas.nth(i).textContent().catch(() => '');
        if (txt?.includes(foundTxt.replace('[Image: ', '').replace(']', ''))) {
          const nextTxt = await allParas.nth(i + 1).textContent().catch(() => 'x');
          if (!nextTxt.trim()) await allParas.nth(i + 1).click();
          break;
        }
      }
    }
    await mediumPage.waitForTimeout(500);

    // 等待 "+" 按鈕並上傳圖片
    let uploadedFileId = null;
    const responseHandler = async resp => {
      if (!resp.url().includes('/_/upload')) return;
      try {
        const text = await resp.text();
        const start = text.search(/\{/);
        if (start < 0) return;
        const parsed = JSON.parse(text.substring(start));
        if (parsed?.success) uploadedFileId = parsed.payload?.value?.fileId || null;
      } catch {}
    };
    mediumPage.on('response', responseHandler);

    const addBtn = mediumPage.locator('[data-testid="editorAddButton"]');
    await addBtn.scrollIntoViewIfNeeded();
    await addBtn.click();
    await mediumPage.waitForTimeout(500);

    const [fileChooser] = await Promise.all([
      mediumPage.waitForEvent('filechooser', { timeout: 10000 }),
      mediumPage.click('button[aria-label="Add an image"]'),
    ]);
    await fileChooser.setFiles(pngPath);
    console.log(`   已選擇檔案，等待上傳...`);

    const deadline = Date.now() + 30000;
    while (!uploadedFileId && Date.now() < deadline) {
      await mediumPage.waitForTimeout(500);
    }
    mediumPage.off('response', responseHandler);

    if (uploadedFileId) {
      uploadedTexts.add(foundTxt);
      console.log(`✅ 圖片插入成功`);
      // 直接用文字重新找佔位符段落並刪除（不依賴 ArrowUp 定位，避免游標位置不確定的問題）
      await mediumPage.waitForTimeout(300);
      // 按 ArrowDown 移離圖片，讓 image toolbar（highlightMenu）消失
      await mediumPage.keyboard.press('ArrowDown');
      await mediumPage.waitForTimeout(300);
      const placeholderEl = mediumPage.getByText(foundTxt, { exact: false }).first();
      if (await placeholderEl.isVisible().catch(() => false)) {
        await placeholderEl.scrollIntoViewIfNeeded();
        await placeholderEl.click({ clickCount: 3 }); // 三連擊選取整段文字
        await mediumPage.waitForTimeout(200);
        await mediumPage.keyboard.press('Backspace'); // 刪除佔位符文字（留空段落）
        await mediumPage.waitForTimeout(300);
      }
    } else {
      // 上傳失敗：移除剛建立的空段落，恢復原狀
      await mediumPage.keyboard.press('Backspace');
      console.warn(`⚠️  圖片插入失敗：${placeholder}`);
    }
    await mediumPage.waitForTimeout(500);
  }
  await mediumPage.waitForTimeout(3000); // 等 editor 自動儲存

  // 等待 URL 變為 /p/xxx/edit（Medium 自動儲存後）
  await mediumPage.waitForFunction(
    () => window.location.href.includes('/p/') && window.location.href.includes('/edit'),
    undefined,
    { timeout: 60000 }
  );

  const draftUrl = mediumPage.url();
  console.log(`\n✅ 草稿已建立！`);
  console.log(`🔗 草稿 URL：${draftUrl}`);

  // 掃描剩餘未替換的圖片佔位符（排除已成功上傳的）
  const remainingImages = [...bodyWithoutTitle.matchAll(/\[Image: ([^\]]+)\]/g)]
    .map(m => m[0])
    .filter(imgTxt => !uploadedTexts.has(imgTxt));
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

  const fileArg = process.argv[2];
  const htmlPath = fileArg ? path.resolve(fileArg) : findLatestHtml();
  if (!htmlPath) {
    console.error('❌ 找不到 *-medium-version.html，請先執行 /convert-report-format');
    process.exit(1);
  }
  if (fileArg && !fs.existsSync(htmlPath)) {
    console.error(`❌ 指定檔案不存在：${htmlPath}`);
    process.exit(1);
  }

  await createDraft(htmlPath);
})();
