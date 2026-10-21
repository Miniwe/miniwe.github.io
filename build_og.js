#!/usr/bin/env node
/**
 * Картинка для превью ссылки (og:image) и иконка для вкладки.
 * Ссылку на резюме чаще всего открывают из мессенджера или LinkedIn —
 * без og:image там показывают пустой прямоугольник.
 * Запуск: node build_og.js   (puppeteer берётся из ~/Projects/cv2026)
 */
const path = require('path');
const puppeteer = require(path.join(process.env.HOME, 'Projects/cv2026/node_modules/puppeteer'));
const fs = require('fs');

const ИМЯ = 'Vitaly Dryukov';
const РОЛЬ = 'Senior Full-Stack Engineer';
const ПОДПИСЬ = 'Node.js · TypeScript · AI in production';

const страница = (ш, в, крупно) => `<!DOCTYPE html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@600;700;800&family=Inter:wght@400;500&display=swap&subset=latin,latin-ext,cyrillic" rel="stylesheet">
<style>
  *{box-sizing:border-box;margin:0}
  body{width:${ш}px;height:${в}px;display:flex;align-items:center;gap:${крупно?56:0}px;
       padding:${крупно?'0 72px':'0'};background:#2c3a4f;color:#fff;
       font-family:Inter,Arial,sans-serif;overflow:hidden;
       justify-content:center}
  body::after{content:"";display:${крупно?'block':'none'};position:absolute;right:-120px;top:-120px;width:420px;height:420px;
              border-radius:50%;background:rgba(255,255,255,.05)}
  img{width:${крупно?260:0}px;height:${крупно?260:0}px;border-radius:50%;object-fit:cover;
      border:8px solid rgba(255,255,255,.14);flex:none;display:${крупно?'block':'none'}}
  h1{font-family:Montserrat,Arial,sans-serif;font-weight:800;font-size:64px;letter-spacing:-1.5px}
  p.role{font-family:Montserrat,Arial,sans-serif;font-weight:700;font-size:34px;
         color:#b9c6d8;margin-top:14px}
  p.sub{font-size:26px;color:#8fa0b8;margin-top:22px}
  p.url{font-family:Montserrat,Arial,sans-serif;font-weight:600;font-size:22px;
        color:#7d8ea6;margin-top:34px;letter-spacing:.5px}
  .текст{display:${крупно?'block':'none'}}
  .mono{font-family:Montserrat,Arial,sans-serif;font-weight:700;font-size:${Math.round(в*0.44)}px;
        letter-spacing:-2px;display:${крупно?'none':'block'}}
</style></head><body>
  <img src="portret.png" alt="">
  <div class="текст">
    <h1>${ИМЯ}</h1>
    <p class="role">${РОЛЬ}</p>
    <p class="sub">${ПОДПИСЬ}</p>
    <p class="url">miniwe.github.io</p>
  </div>
  <div class="mono">VD</div>
</body></html>`;

(async () => {
  const b = await puppeteer.launch({headless: 'new'});
  const времянка = path.join(__dirname, '__og.tmp.html');
  for (const [файл, ш, в, крупно] of [['og-cover.png', 1200, 630, true],
                                      ['apple-touch-icon.png', 180, 180, false]]) {
    // Пишем во временный файл рядом с portret.png: при setContent относительная
    // ссылка на портрет не разрешается — страницы как таковой на диске нет.
    fs.writeFileSync(времянка, страница(ш, в, крупно));
    const p = await b.newPage();
    await p.setViewport({width: ш, height: в, deviceScaleFactor: 1});
    await p.goto('file://' + времянка, {waitUntil: 'networkidle0'});
    const buf = await p.screenshot({type: 'png'});
    fs.writeFileSync(path.join(__dirname, файл), buf);
    console.log(`  ${файл} — ${ш}×${в}, ${(buf.length / 1024).toFixed(0)} КБ`);
    await p.close();
  }
  fs.unlinkSync(времянка);
  await b.close();
})();
