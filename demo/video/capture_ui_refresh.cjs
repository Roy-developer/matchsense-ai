const { chromium } = require('./capture-deps/node_modules/playwright-core');
const fs = require('fs');
const path = require('path');

const outDir = __dirname;
const workDir = path.join(outDir, '.ui-live-capture-refresh');
const dashboardUrl = 'https://matchsense-dashboard.salmonflower-b8e9c650.centralindia.azurecontainerapps.io/';
const ffprobeDir = 'C:/Users/Admin/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0.2-full_build/bin';
const voiceoverPath = path.join(outDir, 'ui-walkthrough-narration-refresh.mp3');
const narrationPath = path.join(outDir, 'ui-walkthrough-narration-refresh.txt');
const captionsPath = path.join(outDir, 'ui-walkthrough-refresh.vtt');
const subtitleCues = [];

function toSeconds(timestamp) {
  const [hours, minutes, rest] = timestamp.split(':');
  const [seconds, milliseconds] = rest.replace(',', '.').split('.');
  return Number(hours) * 3600 + Number(minutes) * 60 + Number(seconds) + Number(`0.${milliseconds || '0'}`);
}

function normalize(text) {
  return text.toLowerCase().replace(/[^a-z0-9 ]/g, ' ').replace(/\s+/g, ' ').trim();
}

function loadCues() {
  const raw = fs.readFileSync(captionsPath, 'utf8');
  const blocks = raw.split(/\r?\n\r?\n/);
  for (const block of blocks) {
    const lines = block.split(/\r?\n/);
    const timingLine = lines.findIndex(line => line.includes(' --> '));
    if (timingLine < 0) continue;
    const [start, end] = lines[timingLine].split(' --> ');
    const text = lines.slice(timingLine + 1).join(' ').trim();
    if (text) subtitleCues.push({ start: toSeconds(start), end: toSeconds(end), text });
  }
  if (!subtitleCues.length) throw new Error(`No subtitle cues found in ${captionsPath}`);

  const paragraphs = fs.readFileSync(narrationPath, 'utf8').split(/\r?\n\r?\n/).map(text => text.trim()).filter(Boolean);
  return paragraphs.map((text, index) => {
    const normalized = normalize(text);
    const matching = subtitleCues.filter(cue => normalized.includes(normalize(cue.text)));
    if (!matching.length) throw new Error(`Could not align narration paragraph ${index + 1} to subtitle cues`);
    return { start: matching[0].start, end: matching[matching.length - 1].end };
  });
}

async function showCaption(page, seconds) {
  const cue = subtitleCues.find(item => seconds >= item.start && seconds <= item.end);
  await page.evaluate(text => {
    let element = document.getElementById('matchsense-caption');
    if (!element) {
      element = document.createElement('div');
      element.id = 'matchsense-caption';
      element.style.cssText = 'position:fixed;bottom:18px;left:50%;transform:translateX(-50%);z-index:2147483000;background:rgba(8,14,24,.88);color:#fff;font:15px/1.25 Segoe UI,sans-serif;padding:5px 11px;border-radius:6px;max-width:70vw;text-align:center;pointer-events:none;box-shadow:0 2px 10px #0007';
      document.body.appendChild(element);
    }
    element.textContent = text || '';
  }, cue ? cue.text : '');
}

const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));

// Streamlit scrolls inside section.stMain, not the window.
async function bring(locator, offset = 70) {
  await locator.evaluate((element, top) => {
    const main = document.querySelector('section.stMain');
    main.scrollTo({ top: main.scrollTop + element.getBoundingClientRect().top - top, behavior: 'smooth' });
  }, offset);
  await sleep(900);
}

async function scrollMainTop(page) {
  await page.evaluate(() => document.querySelector('section.stMain').scrollTo({ top: 0, behavior: 'smooth' }));
}

// Each scene must show these texts inside the 1280x720 viewport (open=true means the parent details is expanded).
const sceneExpectations = [
  [{ text: 'MatchSense AI' }],
  [{ text: 'Momentum timeline' }],
  [{ text: 'Event volume per team', open: true }],
  [{ text: "Harbour Rovers · 55-60'", open: true }],
  [{ text: "Harbour Rovers · 55-60'", open: true }],
  [{ text: 'blocked · Formation claim', open: true }],
  [{ text: 'blocked · Invented statistics', open: true }, { text: 'blocked · Fatigue claim', open: true }],
  [{ text: "Ridgeway Athletic · 40-45'", open: true }, { text: '3 independent signals moving together' }],
  [{ text: 'MatchSense AI' }]
];

async function probeScene(page, expectations) {
  return page.evaluate(wanted => {
    const inView = el => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0 && r.top >= 0 && r.bottom <= window.innerHeight; };
    const results = wanted.map(({ text, open }) => {
      const hits = [...document.querySelectorAll('summary, h1, h3, p, div, span')]
        .filter(el => el.id !== 'matchsense-caption' && !el.closest('#matchsense-caption') && el.textContent.includes(text) && ![...el.children].some(child => child.textContent.includes(text)));
      const visible = hits.filter(inView);
      const details = visible.map(el => el.closest('details')).find(Boolean);
      return { text, found: hits.length > 0, visible: visible.length > 0, open: details ? details.open : null, ok: visible.length > 0 && (open === undefined || (details ? details.open === open : false)) };
    });
    return { caption: document.getElementById('matchsense-caption')?.textContent || '', results, ok: results.every(r => r.ok) };
  }, expectations);
}

async function clickSummary(page, details, label) {
  if (await details.evaluate(element => element.open).catch(() => false)) return;
  const summary = details.locator('summary').first();
  await summary.scrollIntoViewIfNeeded();
  const bounds = await summary.boundingBox();
  if (!bounds) throw new Error(`Could not locate ${label} summary`);
  await page.mouse.click(bounds.x + Math.min(160, bounds.width / 2), bounds.y + Math.min(20, bounds.height / 2));
  await page.waitForTimeout(500);
  if (!(await details.evaluate(element => element.open).catch(() => false))) {
    const retryBounds = await summary.boundingBox();
    if (!retryBounds) throw new Error(`Could not reopen ${label} summary`);
    await page.mouse.click(retryBounds.x + Math.min(160, retryBounds.width / 2), retryBounds.y + Math.min(20, retryBounds.height / 2));
    await page.waitForTimeout(500);
  }
  if (!(await details.evaluate(element => element.open).catch(() => false))) throw new Error(`Failed to expand ${label}`);
}

async function requireDetails(page, text, label) {
  const details = page.locator('details').filter({ hasText: text }).first();
  if (!(await details.count())) throw new Error(`Could not find ${label}`);
  return details;
}

async function waitForTimeline(startedAt, seconds) {
  const remaining = startedAt + seconds * 1000 - Date.now();
  if (remaining > 0) await sleep(remaining);
}

async function main() {
  if (!fs.existsSync(voiceoverPath)) throw new Error(`Missing voiceover: ${voiceoverPath}`);
  const paragraphCues = loadCues();
  fs.rmSync(workDir, { recursive: true, force: true });
  fs.mkdirSync(workDir, { recursive: true });

  const browser = await chromium.launch({
    headless: true,
    executablePath: 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
    args: ['--no-sandbox']
  });
  const context = await browser.newContext({
    viewport: { width: 1280, height: 720 },
    deviceScaleFactor: 1,
    recordVideo: { dir: workDir, size: { width: 1280, height: 720 } }
  });
  const page = await context.newPage();
  const recordingStartedAt = Date.now();
  try {
    await page.goto(dashboardUrl, { waitUntil: 'domcontentloaded', timeout: 120000 });
    await page.waitForFunction(() => document.querySelector('h1')?.innerText.includes('MatchSense AI'), null, { timeout: 120000 });
    await page.waitForTimeout(5000);
    const timelineStartedAt = Date.now();
    const totalDuration = paragraphCues[paragraphCues.length - 1].end;
    fs.writeFileSync(path.join(workDir, 'recording-meta.json'), JSON.stringify({
      initialOffsetSeconds: (timelineStartedAt - recordingStartedAt) / 1000,
      durationSeconds: totalDuration,
      paragraphCues
    }, null, 2));

    const actions = [
      async () => scrollMainTop(page),
      async () => {
        const heading = page.getByRole('heading', { name: 'Momentum timeline' });
        await bring(heading, 20);
      },
      async () => {
        const eventVolume = page.locator('summary').filter({ hasText: 'Event volume per team' }).first();
        if (!(await eventVolume.count())) throw new Error('Could not find event-volume chart');
        await clickSummary(page, eventVolume.locator('xpath=..'), 'event-volume chart');
      },
      async () => {
        const insight = await requireDetails(page, "Harbour Rovers · 55-60'", 'control-shift insight');
        await clickSummary(page, insight, 'control-shift insight');
        await bring(insight);
      },
      async () => {
        const insight = await requireDetails(page, "Harbour Rovers · 55-60'", 'control-shift insight');
        await bring(insight);
        for (const mode of ['fan', 'analyst', 'broadcast']) {
          const label = insight.locator('label').filter({ hasText: new RegExp(`^${mode}$`) }).first();
          if (!(await label.count())) throw new Error(`Could not find ${mode} audience mode`);
          await label.scrollIntoViewIfNeeded();
          const bounds = await label.boundingBox();
          if (!bounds) throw new Error(`Could not locate ${mode} audience mode`);
          await page.mouse.click(bounds.x + bounds.width / 2, bounds.y + bounds.height / 2);
          await sleep(1200);
        }
      },
      async () => {
        await bring(page.getByRole('heading', { name: /Critic check/ }), 20);
        const formation = await requireDetails(page, 'blocked · Formation claim', 'formation rejection');
        await clickSummary(page, formation, 'formation rejection');
      },
      async () => {
        const statistics = await requireDetails(page, 'blocked · Invented statistics', 'invented-statistics rejection');
        await clickSummary(page, statistics, 'invented-statistics rejection');
        const fatigue = await requireDetails(page, 'blocked · Fatigue claim', 'fatigue rejection');
        await clickSummary(page, fatigue, 'fatigue rejection');
        await bring(statistics, 200);
      },
      async () => {
        const approved = await requireDetails(page, "Ridgeway Athletic · 40-45'", 'INS-002 card');
        await clickSummary(page, approved, 'INS-002 card');
        const cardText = await approved.innerText();
        if (!cardText.includes('✅') || !cardText.includes('3 independent signals moving together')) {
          throw new Error(`INS-002 is not approved on the live dashboard: ${cardText.slice(0, 200)}`);
        }
        await bring(approved);
      },
      async () => scrollMainTop(page)
    ];

    let actionIndex = 0;
    const captionTimer = setInterval(() => {
      showCaption(page, (Date.now() - timelineStartedAt) / 1000).catch(error => console.error('Caption update failed:', error));
    }, 100);
    try {
      for (let i = 0; i < paragraphCues.length; i++) {
        await waitForTimeline(timelineStartedAt, paragraphCues[i].start);
        await actions[actionIndex++]();
        await sleep(1800);
        const state = await probeScene(page, sceneExpectations[i]);
        fs.appendFileSync(path.join(workDir, 'scene-state.jsonl'), `${JSON.stringify({ scene: i + 1, atSeconds: +((Date.now() - timelineStartedAt) / 1000).toFixed(1), ...state })}\n`);
        console.log(`scene ${i + 1} ${state.ok ? 'OK' : 'MISMATCH'} | caption: ${state.caption}`);
        fs.appendFileSync(path.join(workDir, 'scene-log.jsonl'), `${JSON.stringify({ scene: i + 1, ...paragraphCues[i] })}\n`);
      }
      await waitForTimeline(timelineStartedAt, totalDuration);
    } finally {
      clearInterval(captionTimer);
    }
    await showCaption(page, totalDuration + 1);
    console.log(`Capture timeline complete: ${totalDuration.toFixed(1)} seconds`);
  } finally {
    await context.close();
    await browser.close();
  }
}

main().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
