#!/usr/bin/env node
/**
 * PDF из ATS-версий. Текстовый слой обязателен — картинку-PDF парсер не читает.
 * Запуск: node build_ats_pdf.js   (puppeteer берётся из ~/Projects/cv2026)
 */
const puppeteer = require(require('path').join(process.env.HOME, 'Projects/cv2026/node_modules/puppeteer'));
const fs = require('fs');
(async () => {
  const b = await puppeteer.launch({headless: 'new'});
  const p = await b.newPage();
  for (const я of ['ru', 'en', 'az']) {
    const файл = `${__dirname}/ats-${я}.html`;
    if (!fs.existsSync(файл)) continue;
    await p.goto('file://' + файл, {waitUntil: 'networkidle0'});
    const buf = await p.pdf({format: 'A4', printBackground: false, preferCSSPageSize: true});
    fs.writeFileSync(`${__dirname}/Dryukov-CV-${я.toUpperCase()}-ATS.pdf`, buf);
    const текст = await p.evaluate(() => document.body.innerText.length);
    console.log(`  Dryukov-CV-${я.toUpperCase()}-ATS.pdf — ${(buf.length/1024).toFixed(0)} КБ, текста ${текст} знаков`);
  }
  await b.close();
})();
