import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile, rm, stat } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { build, configuration } from '../build.mjs';

test('production output has localized metadata, assets and one Umami tracker per page', async () => {
  const dir = await mkdtemp(join(tmpdir(), 'ytd-site-test-'));
  try {
    await build({ SITE_URL: 'https://download.example/', UMAMI_SCRIPT_URL: 'https://analytics.example/script.js?one=1&two=2', UMAMI_WEBSITE_ID: 'example-id' }, dir);
    for (const lang of ['zh', 'en']) {
      const html = await readFile(join(dir, lang, 'index.html'), 'utf8');
      assert.match(html, new RegExp(`rel="canonical" href="https://download.example/${lang}/"`));
      assert.match(html, new RegExp(`property="og:image" content="https://download.example/assets/share-${lang}.png"`));
      assert.match(html, /hreflang="zh-CN"/);
      assert.match(html, /hreflang="en"/);
      assert.match(html, /name="twitter:card" content="summary_large_image"/);
      assert.equal((html.match(/data-website-id=/g) || []).length, 1);
      assert.match(html, /script\.js\?one=1&amp;two=2/);
      for (const event of ['download_click', 'github_click', 'language_switch']) assert.ok(html.includes(`data-umami-event="${event}"`));
      assert.match(html, /https:\/\/github.com\/hwangzhun\/youtube_downloader\/releases\/latest/);
      assert.doesNotMatch(html, /Core|Lite|__TAURI|@tauri/);
      const paths = [...html.matchAll(/(?:src|href)="(\/assets\/[^"#]+)"/g)].map(match => match[1]);
      for (const path of paths) assert.ok((await stat(join(dir, path))).isFile(), path);
      for (const target of [...html.matchAll(/href="#([^"]+)"/g)]) assert.ok(html.includes(`id="${target[1]}"`));
      const png = await readFile(join(dir, 'assets', `share-${lang}.png`));
      assert.equal(png.readUInt32BE(16), 1200);
      assert.equal(png.readUInt32BE(20), 630);
    }
    assert.match(await readFile(join(dir, 'sitemap.xml'), 'utf8'), /https:\/\/download.example\/en\//);
    assert.match(await readFile(join(dir, 'robots.txt'), 'utf8'), /Sitemap: https:\/\/download.example\/sitemap.xml/);
    assert.match(await readFile(join(dir, 'index.html'), 'utf8'), /http-equiv="refresh" content="0; url=\/zh\/"/);
  } finally { await rm(dir, { recursive: true, force: true }); }
});

test('unconfigured local builds omit analytics and production-only metadata', async () => {
  const dir = await mkdtemp(join(tmpdir(), 'ytd-site-local-'));
  try {
    await build({}, dir);
    const html = await readFile(join(dir, 'zh', 'index.html'), 'utf8');
    assert.doesNotMatch(html, /data-website-id=|rel="canonical"/);
    assert.doesNotMatch(await readFile(join(dir, 'robots.txt'), 'utf8'), /Sitemap:/);
    await assert.rejects(stat(join(dir, 'sitemap.xml')));
  } finally { await rm(dir, { recursive: true, force: true }); }
});

test('configuration rejects partial tracking settings and unsafe URLs', () => {
  assert.throws(() => configuration({ UMAMI_WEBSITE_ID: 'id' }), /both/);
  assert.throws(() => configuration({ UMAMI_SCRIPT_URL: 'https://example.com/script.js' }), /both/);
  assert.throws(() => configuration({ SITE_URL: 'https://example.com/path/' }), /origin/);
  assert.throws(() => configuration({ SITE_URL: 'https://user:password@example.com' }), /credentials/);
  assert.throws(() => configuration({ UMAMI_SCRIPT_URL: 'javascript:alert(1)', UMAMI_WEBSITE_ID: 'id' }), /HTTP/);
});
