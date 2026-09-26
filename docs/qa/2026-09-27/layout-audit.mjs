// Local synthetic inspection only. Set PLAYWRIGHT_MODULE and CHROMIUM_EXECUTABLE.
// Run from the repository root with the Vite server on 127.0.0.1:3015.
import { writeFile } from 'node:fs/promises';
const { chromium } = await import(process.env.PLAYWRIGHT_MODULE || 'playwright');
const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_EXECUTABLE, headless: true });
try {
  const page = await browser.newPage({ viewport: { width: 414, height: 896 }, deviceScaleFactor: 1, reducedMotion: 'reduce' });
  await page.route('**/*', route => new URL(route.request().url()).hostname === '127.0.0.1' ? route.continue() : route.abort());
  const directory = 'docs/qa/2026-09-27';
  const results = [];
  for (const path of ['/?demo=1', '/plan?demo=1', '/add?demo=1', '/ledger?demo=1', '/report?demo=1', '/settings?demo=1']) {
    await page.goto('http://127.0.0.1:3015' + path);
    await page.locator('h1').first().waitFor();
    if (path.startsWith('/plan')) await page.getByRole('button', { name: '계획 수정' }).click();
    await page.evaluate(() => document.fonts.ready);
    const name = path.split('?')[0].replaceAll('/', '') || 'home';
    await page.screenshot({ path: directory + '/' + name + '-before-414.png', fullPage: true, animations: 'disabled' });
    results.push(await page.evaluate(name => ({
      screen: name, viewport: innerWidth, documentWidth: document.documentElement.scrollWidth,
      overflow: [...document.querySelectorAll('body *')].filter(el => el.getBoundingClientRect().right > innerWidth + 1 && el.getBoundingClientRect().width > 0).slice(0, 15).map(el => ({ tag: el.tagName, class: typeof el.className === 'string' ? el.className : el.tagName, right: el.getBoundingClientRect().right })),
      planGrid: (() => { const element = document.querySelector('.plan-setup'); return element ? { alignContent: getComputedStyle(element).alignContent, gridRows: getComputedStyle(element).gridTemplateRows, children: [...element.children].map(child => ({ class: child.className, top: child.getBoundingClientRect().top, height: child.getBoundingClientRect().height })) } : null; })(),
    }), name));
  }
  await writeFile(directory + '/layout-observations.json', JSON.stringify({ environment: 'Local Chromium at 414x896, synthetic demo state; not iOS/WebKit evidence', results }, null, 2) + '\n');
  console.log(JSON.stringify(results));
} finally { await browser.close(); }
