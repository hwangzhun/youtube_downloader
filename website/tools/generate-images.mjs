// Optional maintainer tool. The PNGs are committed; production builds do not
// require Playwright, Chrome, or the desktop development server.
import { readFile, mkdir } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, '..', '..');
const assets = join(here, '..', 'public', 'assets');
const { chromium } = await import(process.env.PLAYWRIGHT_MODULE || 'playwright');
const browser = await chromium.launch({ ...(process.env.CHROME_PATH ? { executablePath: process.env.CHROME_PATH } : {}), headless: true });
await mkdir(assets, { recursive: true });
try {
  const logo = (await readFile(join(root, 'resources/icons/app_icon_horizontal.png'))).toString('base64');
  const icon = (await readFile(join(root, 'resources/icons/app_icon.png'))).toString('base64');
  const page = await browser.newPage({ viewport: { width: 1200, height: 630 }, deviceScaleFactor: 1 });
  for (const lang of ['zh', 'en']) {
    await page.setContent(`<!doctype html><html lang="${lang}"><meta charset="utf-8"><style>
      *{box-sizing:border-box}body{margin:0;width:1200px;height:630px;background:#faf9f6;color:#242628;font-family:"Noto Sans CJK SC","Segoe UI",sans-serif;overflow:hidden}
      .stripe{height:10px;background:#df343d}.copy{position:absolute;left:72px;top:76px;width:720px}.logo{width:460px;height:auto}
      .tag{margin-top:42px;font-size:16px;color:#df343d;letter-spacing:3px;font-weight:700}h1{font-size:46px;line-height:1.35;letter-spacing:-1.5px;margin:22px 0 24px;max-width:690px}
      .sub{font-size:23px;color:#64696e}.bottom{position:absolute;bottom:54px;left:72px;font-size:16px;color:#8b867f;letter-spacing:1px}.art{position:absolute;width:275px;right:48px;top:184px;transform:rotate(-9deg)}
      .ring{position:absolute;width:350px;height:350px;border:1px solid #e3d9cd;border-radius:50%;right:11px;top:140px;background:radial-gradient(ellipse,#f5e4dc,transparent 72%)}
    </style><div class="stripe"></div><div class="copy"><img class="logo" src="data:image/png;base64,${logo}" alt="YouTube Downloader"><div class="tag">${lang === 'zh' ? '开源 · 完全免费' : 'OPEN SOURCE · COMPLETELY FREE'}</div><h1>${lang === 'zh' ? '把喜欢的视频，<br>留在自己的电脑里。' : 'Keep the videos you love.<br>On your own computer.'}</h1><div class="sub">Powered by yt-dlp + FFmpeg</div></div><div class="ring"></div><img class="art" src="data:image/png;base64,${icon}" alt=""><div class="bottom">WINDOWS 10 / 11 · MIT LICENSE · YouTube Downloader</div></html>`);
    await page.evaluate(() => document.fonts.ready);
    await page.locator('img').evaluateAll(images => Promise.all(images.map(image => image.decode())));
    await page.screenshot({ path: join(assets, `share-${lang}.png`) });
  }
  await page.close();

  const version = JSON.parse(await readFile(join(root, 'src-tauri/tauri.conf.json'), 'utf8')).version;
  const app = await browser.newPage({ viewport: { width: 1440, height: 920 }, deviceScaleFactor: 1 });
  // Only this screenshot context gets fixture data. These mocks are never
  // bundled into the website or the desktop application.
  await app.addInitScript(({ version }) => {
    localStorage.setItem('theme', 'light');
    const video = { id: 'example', url: 'https://www.youtube.com/watch?v=example', title: '示例视频 · Sample video', channel: '演示内容 · Demo content', duration: 185, formats: [{ formatId: '137', label: '1080p · 30fps', height: 1080, fps: 30, videoCodec: 'avc1' }, { formatId: '136', label: '720p · 30fps', height: 720, fps: 30, videoCodec: 'avc1' }], audioFormats: [{ formatId: '140', label: 'AAC · 128 kbps', audioCodec: 'aac' }] };
    sessionStorage.setItem('page.single.url', JSON.stringify(video.url));
    sessionStorage.setItem('page.single.video', JSON.stringify(video));
    sessionStorage.setItem('page.single.videoFormat', JSON.stringify('137'));
    sessionStorage.setItem('page.single.audioFormat', JSON.stringify('140'));
    const tool = { available: true };
    window.__TAURI_INTERNALS__ = {
      metadata: { currentWindow: { label: 'main' }, currentWebview: { label: 'main' } },
      invoke: async (command) => {
        if (command === 'get_runtime_status') return { appVersion: version, ytDlp: tool, ffmpeg: tool, ffprobe: tool, webview2: tool, javascriptRuntime: tool };
        if (command === 'get_settings') return { outputDir: '', proxyUrl: '', proxyEnabled: false, maxConcurrent: 2, firstRunNoticePending: false };
        if (command === 'list_tasks') return [];
        throw new Error(`Unexpected screenshot command: ${command}`);
      },
    };
  }, { version });
  await app.goto(process.env.APP_PREVIEW_URL || 'http://127.0.0.1:5188/', { waitUntil: 'networkidle' });
  await app.getByRole('heading', { name: '示例视频 · Sample video' }).waitFor();
  await app.evaluate(() => document.fonts.ready);
  await app.screenshot({ path: join(assets, 'app-preview.png') });
  await app.close();
  console.log('Generated app-preview.png and 1200×630 share-zh.png / share-en.png');
} finally {
  await browser.close();
}
