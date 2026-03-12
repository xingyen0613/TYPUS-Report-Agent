#!/usr/bin/env node
/**
 * intercept-upload.js
 * 攔截 Medium 圖片上傳的 network request，印出 API 細節
 * 用法：
 *   1. node intercept-upload.js
 *   2. 瀏覽器開啟後，手動點 "+" → "Add an image" → 上傳任意圖片
 *   3. 結果自動存到 /tmp/medium-upload-log.json
 *   4. Ctrl+C 結束
 */

const { chromium } = require('playwright-extra');
const StealthPlugin = require('puppeteer-extra-plugin-stealth');
chromium.use(StealthPlugin());
const fs = require('fs');
const path = require('path');
const os = require('os');

const SESSION_FILE = path.join(os.homedir(), '.config', 'typus-medium-session.json');
const LOG_FILE = '/tmp/medium-upload-log.json';
const LAUNCH_OPTS = { headless: false, channel: 'chrome' };

const captured = [];

(async () => {
  if (!fs.existsSync(SESSION_FILE)) {
    console.error('❌ 找不到 session，請先執行 /publish-medium 登入');
    process.exit(1);
  }

  const browser = await chromium.launch(LAUNCH_OPTS);
  const context = await browser.newContext({ storageState: SESSION_FILE });
  const page = await context.newPage();

  // 攔截所有 POST requests
  page.on('request', req => {
    if (req.method() !== 'POST') return;
    const url = req.url();
    const headers = req.headers();
    const contentType = headers['content-type'] || '';
    const entry = {
      type: 'request',
      url,
      method: req.method(),
      contentType,
      headers,
      postDataSize: req.postData()?.length || 0,
    };
    captured.push(entry);
    console.log(`\n📤 POST: ${url}`);
    console.log(`   Content-Type: ${contentType}`);
    if (contentType.includes('multipart') || url.includes('image') || url.includes('upload') || url.includes('media')) {
      console.log('   ⭐ 可能是圖片上傳！');
    }
  });

  // 攔截所有 response
  page.on('response', async res => {
    if (res.request().method() !== 'POST') return;
    const url = res.url();
    const status = res.status();
    let body = '';
    try {
      body = await res.text();
      if (body.length > 1000) body = body.substring(0, 1000) + '...';
    } catch {}

    const entry = {
      type: 'response',
      url,
      status,
      body,
    };
    captured.push(entry);

    if (url.includes('image') || url.includes('upload') || url.includes('media') ||
        body.includes('imageId') || body.includes('url') || body.includes('cdn')) {
      console.log(`\n✅ Response: ${url} [${status}]`);
      console.log(`   Body: ${body.substring(0, 300)}`);
    }

    // 儲存到 log file
    fs.writeFileSync(LOG_FILE, JSON.stringify(captured, null, 2));
  });

  await page.goto('https://medium.com/new-story', { waitUntil: 'domcontentloaded', timeout: 60000 });

  console.log('\n✅ Medium 編輯器已開啟');
  console.log('👉 步驟：');
  console.log('   1. 點擊 "+" 按鈕（空白行左側）');
  console.log('   2. 選 "Add an image"');
  console.log('   3. 上傳任意圖片');
  console.log('   4. 看 terminal 輸出');
  console.log(`\n📝 所有 POST requests 會存到：${LOG_FILE}`);
  console.log('   Ctrl+C 結束\n');

  // 等待直到手動中斷
  await new Promise(() => {});
})();
