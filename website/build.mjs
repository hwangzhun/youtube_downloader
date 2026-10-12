import { cp, mkdir, readFile, rm, writeFile } from 'node:fs/promises';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { content } from './content.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const repository = 'https://github.com/hwangzhun/youtube_downloader';
const release = `${repository}/releases/latest`;
export const escape = (value) => String(value).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);

function publicUrl(value, label, originOnly = false) {
  if (!value) return '';
  const url = new URL(value);
  if (!['https:', 'http:'].includes(url.protocol) || url.username || url.password) throw new Error(`${label} must be an HTTP(S) URL without credentials`);
  if (originOnly && (url.pathname !== '/' || url.search || url.hash)) throw new Error(`${label} must be a site origin, without a path, query or fragment`);
  return originOnly ? url.origin : url.href;
}

export function configuration(env) {
  const site = publicUrl(env.SITE_URL?.trim(), 'SITE_URL', true);
  const script = publicUrl(env.UMAMI_SCRIPT_URL?.trim(), 'UMAMI_SCRIPT_URL');
  const id = env.UMAMI_WEBSITE_ID?.trim() || '';
  if (Boolean(script) !== Boolean(id)) throw new Error('Set both UMAMI_SCRIPT_URL and UMAMI_WEBSITE_ID, or leave both empty');
  return { site, script, id };
}

function render(lang, config) {
  const c = content[lang];
  const e = escape;
  const event = (name, position) => `data-umami-event="${name}" data-umami-event-language="${lang}" data-umami-event-position="${position}"`;
  const download = position => `<a class="button primary" href="${release}" ${event('download_click', position)}>${e(c.download)} <span aria-hidden="true">↗</span></a>`;
  const source = position => `<a class="button secondary" href="${repository}" ${event('github_click', position)}>${e(c.github)} <span aria-hidden="true">↗</span></a>`;
  const absolute = path => `${config.site}${path}`;
  const meta = config.site ? `<link rel="canonical" href="${absolute(`/${lang}/`)}">
    <link rel="alternate" hreflang="zh-CN" href="${absolute('/zh/')}">
    <link rel="alternate" hreflang="en" href="${absolute('/en/')}">
    <link rel="alternate" hreflang="x-default" href="${absolute('/zh/')}">
    <meta property="og:url" content="${absolute(`/${lang}/`)}">` : '';
  const picture = absolute(`/assets/share-${lang}.png`);
  return `<!doctype html>
<html lang="${c.htmlLang}">
<head>
  <meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
  <title>${e(c.title)}</title><meta name="description" content="${e(c.description)}">
  <meta name="theme-color" content="#faf9f6">
  <link rel="icon" type="image/png" href="/assets/app_icon.png">
  <link rel="apple-touch-icon" href="/assets/app_icon.png">
  <link rel="stylesheet" href="/assets/style.css">${meta}
  <meta property="og:type" content="website"><meta property="og:site_name" content="YouTube Downloader">
  <meta property="og:locale" content="${c.locale}"><meta property="og:locale:alternate" content="${content[c.other].locale}">
  <meta property="og:title" content="${e(c.title)}"><meta property="og:description" content="${e(c.description)}">
  <meta property="og:image" content="${picture}"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
  <meta property="og:image:alt" content="YouTube Downloader — ${lang === 'zh' ? '开源 · 完全免费' : 'Open source · Completely free'}">
  <meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="${e(c.title)}">
  <meta name="twitter:description" content="${e(c.description)}"><meta name="twitter:image" content="${picture}">
  <script src="/assets/main.js" defer></script>
  ${config.script ? `<script defer src="${e(config.script)}" data-website-id="${e(config.id)}"></script>` : ''}
</head>
<body>
  <a class="skip-link" href="#main">${e(c.skip)}</a>
  <header class="site-header"><div class="container header-inner">
    <a class="brand" href="/${lang}/" aria-label="YouTube Downloader"><img src="/assets/app_icon.png" width="36" height="36" alt=""><span>YouTube <b>Downloader</b></span></a>
    <nav aria-label="${lang === 'zh' ? '主要导航' : 'Main navigation'}">${c.nav.map((label, index) => `<a href="#${['features', 'settings', 'start', 'faq'][index]}">${e(label)}</a>`).join('')}</nav>
    <a class="language" href="/${c.other}/" lang="${content[c.other].htmlLang}" hreflang="${content[c.other].htmlLang}" ${event('language_switch', 'header')}>${e(c.language)} <span aria-hidden="true">↗</span></a>
  </div></header>
  <main id="main">
    <section class="hero container">
      <div class="hero-copy"><p class="badge"><span aria-hidden="true"></span>${e(c.badge)}</p>
        <img class="hero-logo" src="/assets/app_icon_horizontal.png" width="1000" height="164" alt="YouTube Downloader">
        <h1>${c.heading}</h1><p class="intro">${e(c.intro)}</p>
        <div class="actions">${download('hero')}${source('hero')}</div>
        <p class="requirements">${e(c.requirements)}<br><span>${e(c.releaseHint)}</span></p>
      </div>
      <a class="hero-art" href="#preview" aria-label="${e(c.previewLabel)}"><div class="art-orbit"></div><img src="/assets/app_icon.png" width="1000" height="1000" alt=""><div class="art-label"><span aria-hidden="true">↓</span> yt-dlp + FFmpeg</div><span class="art-caption">LOCAL FILES. YOUR CONTROL.</span></a>
    </section>
    <section class="container preview-section" id="preview"><div class="section-line"><h2>${e(c.previewLabel)}</h2><span>${e(c.previewNote)}</span></div>
      <figure class="app-preview"><img src="/assets/app-preview.png" width="1440" height="920" alt="${e(c.previewAlt)}" fetchpriority="high"><figcaption>${e(c.previewNote)}</figcaption></figure>
    </section>
    <section class="container engines"><h2 class="subtle-heading">${e(c.engines)}</h2><div class="engine-grid">${c.engineCards.map(([name, title, text], i) => `<article><a href="${['https://github.com/yt-dlp/yt-dlp', 'https://ffmpeg.org/', 'https://tauri.app/'][i]}">${e(name)} <span aria-hidden="true">↗</span></a><h3>${e(title)}</h3><p>${e(text)}</p></article>`).join('')}</div></section>
    <section class="container section" id="features"><p class="eyebrow">${c.featuresEyebrow}</p><h2>${e(c.featuresTitle)}</h2><p class="section-intro">${e(c.featuresIntro)}</p><div class="feature-grid">${c.features.map(([number, title, text]) => `<article><span class="number">${number}</span><h3>${e(title)}</h3><p>${e(text)}</p></article>`).join('')}</div></section>
    <section class="settings-section" id="settings"><div class="container settings-grid"><div class="settings-heading"><p class="eyebrow">${c.settingsEyebrow}</p><h2>${e(c.settingsTitle)}</h2><p class="section-intro">${e(c.settingsIntro)}</p><div class="settings-stamp"><img src="/assets/app_icon.png" width="58" height="58" alt=""><span>YOUR DESKTOP.<br>YOUR SETTINGS.</span></div></div><div class="settings-list">${c.settings.map(([title, text], i) => `<article><span class="setting-number">0${i + 1}</span><div><h3>${e(title)}</h3><p>${e(text)}</p></div></article>`).join('')}</div></div></section>
    <section class="container section" id="start"><p class="eyebrow">${c.stepsEyebrow}</p><h2>${e(c.stepsTitle)}</h2><div class="steps">${c.steps.map(([title, text], i) => `<article><span class="step-number">${i + 1}</span><h3>${e(title)}</h3><p>${e(text)}</p></article>`).join('')}</div><div class="actions">${download('getting_started')}</div></section>
    <section class="container section faq-section" id="faq"><div><p class="eyebrow">FAQ</p><h2>${e(c.faqTitle)}</h2></div><div class="faq-list">${c.faqs.map(([question, answer]) => `<details><summary>${e(question)}</summary><p>${e(answer)}</p></details>`).join('')}</div></section>
    <section class="container open-section"><div><p class="eyebrow">${c.openEyebrow}</p><h2>${e(c.openTitle)}</h2><p>${e(c.openText)}</p><a class="license" href="${repository}/blob/main/LICENSE" ${event('github_click', 'license')}>${e(c.license)} ↗</a></div>${source('open_source')}</section>
  </main>
  <footer class="container"><div class="footer-main"><a class="brand" href="/${lang}/"><img src="/assets/app_icon.png" width="32" height="32" alt=""><span>YouTube <b>Downloader</b></span></a><p>${e(c.footer)}</p><a href="${repository}" ${event('github_click', 'footer')}>GitHub ↗</a></div><div class="footer-notes"><p>${e(c.legal)}</p><p>${e(c.privacy)}</p></div></footer>
</body></html>`;
}

export async function build(env = process.env, output = join(here, 'dist')) {
  const config = configuration(env);
  await rm(output, { recursive: true, force: true });
  await mkdir(join(output, 'assets'), { recursive: true });
  await cp(join(here, 'public'), output, { recursive: true });
  for (const name of ['app_icon.png', 'app_icon_horizontal.png']) {
    await cp(join(here, '..', 'resources', 'icons', name), join(output, 'assets', name));
  }
  for (const lang of Object.keys(content)) {
    await mkdir(join(output, lang), { recursive: true });
    await writeFile(join(output, lang, 'index.html'), render(lang, config));
  }
  await writeFile(join(output, 'index.html'), `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>YouTube Downloader</title><meta http-equiv="refresh" content="0; url=/zh/">${config.site ? `<link rel="canonical" href="${config.site}/zh/">` : ''}</head><body><a href="/zh/">简体中文</a> · <a href="/en/">English</a></body></html>`);
  await writeFile(join(output, 'robots.txt'), `User-agent: *\nAllow: /\n${config.site ? `Sitemap: ${config.site}/sitemap.xml\n` : ''}`);
  if (config.site) {
    await writeFile(join(output, 'sitemap.xml'), `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">${['zh', 'en'].map(lang => `<url><loc>${config.site}/${lang}/</loc></url>`).join('')}</urlset>\n`);
  }
  // Fail before deployment when a required product or sharing image is missing.
  for (const asset of ['app-preview.png', 'share-zh.png', 'share-en.png']) await readFile(join(output, 'assets', asset));
  console.log(`Built bilingual website: ${output}`);
  if (!config.site) console.log('SITE_URL is unset: absolute sharing URLs, canonical links and sitemap require a production rebuild.');
  if (!config.script) console.log('Umami is disabled until both tracking variables are configured.');
  return output;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) await build();
