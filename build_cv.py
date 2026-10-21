#!/usr/bin/env python3
"""Сборка страницы резюме из Markdown-источников в хранилище Obsidian.

Источник правды — заметки проекта «13 Резюме и поиск работы»; здесь только
вёрстка. Запуск:  python3 build_cv.py

На выходе index.html (RU), en.html, az.html в корне репозитория —
самодостаточные файлы со встроенным CSS, чтобы `serve .` работал без сборки.
"""
import html
import re
import unicodedata
from pathlib import Path

ХРАНИЛИЩЕ = Path.home() / "Projects/LifeTracker/LifeTracker/(P) Проекты/13 Резюме и поиск работы"
КОРЕНЬ = Path(__file__).parent

# Опыт до этого года на страницу не выводится — решение человека 2026-10-22.
# В хранилище полная хронология остаётся: это фильтр показа, а не правка резюме.
ОПЫТ_С = 2010

ЯЗЫКИ = [
    ("ru", "index.html", "резюме-2026-09.md", "RU"),
    ("en", "en.html", "cv-2026-09-en.md", "EN"),
    ("az", "az.html", "cv-2026-09-az.md", "AZ"),
]

# Какие разделы уходят в левую колонку. Ключ — первое слово заголовка в нижнем
# регистре, чтобы одинаково ловить «Стек» / «Stack» / «Texnologiyalar».
# Слева остаются только короткие справочные блоки. Контакты и «Кратко»
# ушли вправо, а раздел «Стек» больше не выводится отдельным полотном:
# он разбирается на словарь и раздаётся тегами по кейсам и местам работы
# (решение человека 2026-10-22 — «полотно технологий оттолкнёт»).
В_САЙДБАР = {"образование", "education", "təhsil", "формат", "working", "iş formatı"}
СТЕК_РАЗДЕЛ = {"стек", "stack", "stek"}


def без_диакритики(s: str) -> str:
    """İş → is. Турецкая İ в нижнем регистре даёт i + комбинирующую точку,
    из-за чего startswith('iş') не срабатывает. Снимаем комбинирующие знаки."""
    разложено = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in разложено if not unicodedata.combining(c))


def в_сайдбар(заголовок: str) -> bool:
    з = без_диакритики(заголовок).strip()
    return any(з.startswith(без_диакритики(к)) for к in В_САЙДБАР)


def снять_фронтматтер(t: str) -> str:
    return re.sub(r"^---\n.*?\n---\n", "", t, flags=re.S)


def строчный(s: str) -> str:
    """Инлайновый markdown: **жирный**, `код`, [текст](ссылка), *курсив*."""
    s = html.escape(s)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"(?<![\w*])\*([^*]+)\*(?![\w*])", r"<em>\1</em>", s)
    return s


def разобрать(текст: str):
    """→ (имя, роль, контакты[], {заголовок: [блоки]}) в порядке появления."""
    строки = снять_фронтматтер(текст).split("\n")
    имя = роль = ""
    контакты, разделы, текущий = [], {}, None
    буфер = []

    def слить():
        nonlocal буфер
        if буфер and текущий:
            разделы.setdefault(текущий, []).append("\n".join(буфер))
        буфер = []

    for стр in строки:
        s = стр.rstrip()
        if s.startswith("# "):
            имя = s[2:].strip()
            continue
        if s.startswith("## "):
            слить()
            текущий = s[3:].strip()
            разделы.setdefault(текущий, [])
            continue
        if текущий is None:
            if s.startswith("**") and not роль:
                роль = re.sub(r"\*\*", "", s)
            elif s and not s.startswith("---"):
                контакты.append(s)
            continue
        if s.startswith("---"):
            continue
        if not s:
            слить()
        else:
            буфер.append(s)
    слить()
    return имя, роль, контакты, разделы


def не_старее(блок: str, заголовок: str) -> bool:
    """Фильтр по году — только для раздела опыта, где у записей есть даты."""
    if "опыт" not in без_диакритики(заголовок) and \
       "experience" not in без_диакритики(заголовок) and \
       "tecrube" not in без_диакритики(заголовок):
        return True
    годы = [int(г) for г in re.findall(r"\b(19|20)\d{2}\b", блок.split("\n")[0])
            ] if False else [int(г) for г in re.findall(r"\b((?:19|20)\d{2})\b", блок.split("\n")[0])]
    return not годы or max(годы) >= ОПЫТ_С


def словарь_технологий(разделы) -> list:
    """Разбирает таблицу «Стек» в плоский список терминов для тегов.
    Длинные пояснения («транзакции, изоляция, индексы») отбрасываются —
    тегом должно быть название, а не фраза."""
    слова = []
    for заголовок, блоки in разделы.items():
        if not any(без_диакритики(заголовок).startswith(к) for к in СТЕК_РАЗДЕЛ):
            continue
        for блок in блоки:
            for стр in блок.split("\n"):
                ячейки = [c.strip() for c in стр.strip("|").split("|")]
                if len(ячейки) < 2:
                    continue
                for кусок in re.split(r"[,·]", ячейки[1]):
                    к = re.sub(r"[*`]", "", кусок).strip()
                    к = re.sub(r"\s*\(.*?\)\s*", " ", к).strip()
                    if 2 <= len(к) <= 22 and " " not in к.strip() or (
                            2 <= len(к) <= 22 and к.count(" ") == 1 and any(c.isdigit() for c in к)):
                        слова.append(к)
    # длинные вперёд: «PHP 8.4» должен сматчиться раньше, чем «PHP»
    return sorted(set(слова), key=len, reverse=True)


# В тексте записей технологии пишутся свободно: «NodeJS» против «Node.js»,
# «Postgres» против «PostgreSQL». Канон слева, написания справа.
СИНОНИМЫ = {
    "Node.js": ["node.js", "nodejs", "node js"],
    "PostgreSQL": ["postgresql", "postgres"],
    "TypeScript": ["typescript", " ts,", "(ts)"],
    "Redux Toolkit": ["redux toolkit"],
    "Qdrant": ["qdrant"], "BM25": ["bm25"], "LiteLLM": ["litellm"],
    "MCP": ["mcp-", "mcp ", "mcp."], "Ollama": ["ollama"],
    "Docker": ["docker"], "NestJS": ["nestjs", "nest.js"],
    "Laravel 12": ["laravel 12"], "PHP 8.4": ["php 8.4"],
    "React": ["react"], "GraphQL": ["graphql"], "Redis": ["redis"],
    "BullMQ": ["bullmq"], "Next.js": ["next.js"], "MongoDB": ["mongodb"],
    "RabbitMQ": ["rabbitmq"], "OpenAPI": ["openapi"], "CI/CD": ["ci/cd"],
}


def теги(текст: str, словарь: list, предел: int = 7) -> str:
    """Какие технологии из словаря реально упомянуты в этой записи."""
    низ = текст.lower()
    найдено = []
    for канон, формы in СИНОНИМЫ.items():
        if any(ф in низ for ф in формы):
            найдено.append(канон)
    for сл in словарь:
        if сл.lower() in низ and not any(сл.lower() in у.lower() for у in найдено):
            найдено.append(сл)
    if not найдено:
        return ""
    чипы = "".join(f"<span>{html.escape(с)}</span>" for с in найдено[:предел])
    return f'<p class="теги">{чипы}</p>'


def блок_в_html(блок: str, словарь: list = ()) -> str:
    строки = блок.split("\n")
    # таблица стека: | **Backend** | Node.js, ... |
    if строки[0].startswith("|"):
        пункты = []
        for стр in строки:
            ячейки = [c.strip() for c in стр.strip("|").split("|")]
            if len(ячейки) < 2 or set(ячейки[0]) <= set("-: "):
                continue
            if not ячейки[0]:
                continue
            пункты.append(f"<li><b>{строчный(ячейки[0])}</b>"
                          f"<span>{строчный(ячейки[1])}</span></li>")
        return f'<ul class="стек">{"".join(пункты)}</ul>' if пункты else ""
    # Запись опыта или кейса: строка начинается с **Заголовка**.
    # Дальше по строке может идти либо дата («— 04/2022 – 10/2025»), либо
    # сразу текст («— монорепозиторий NestJS…»). Различаем по содержимому:
    # датой считаем только то, где есть четырёхзначный год или «н.в.».
    m = re.match(r"\*\*(.+?)\*\*(.*)$", строки[0])
    if m:
        титул = строчный(f"**{m.group(1)}**")
        остаток = m.group(2).strip().lstrip("—-·,").strip()
        дата = ""
        # Датой считаем только короткий хвост с годом. Длинное предложение —
        # это текст записи («, 2000 — факультет прикладной математики…»).
        if остаток and len(остаток) <= 48 and \
                re.search(r"\d{4}|н\.\s?в\.|present|indiyədək", остаток, re.I):
            дата, остаток = остаток, ""
        тело = " ".join(([остаток] if остаток else []) + строки[1:]).strip()
        метка = f'<span class="дата">{строчный(дата)}</span>' if дата else ""
        низ = f"<p>{строчный(тело)}</p>" if тело else ""
        чипы = теги(блок, словарь) if словарь else ""
        return f'<article class="запись"><h3>{титул}{метка}</h3>{низ}{чипы}</article>'
    return f"<p>{строчный(' '.join(строки))}</p>"


def собрать(язык, файл, исходник, метка):
    текст = (ХРАНИЛИЩЕ / исходник).read_text(encoding="utf-8")
    имя, роль, контакты, разделы = разобрать(текст)

    словарь = словарь_технологий(разделы)
    сайдбар, основное = [], []
    for заголовок, блоки in разделы.items():
        if any(без_диакритики(заголовок).startswith(к) for к in СТЕК_РАЗДЕЛ):
            continue  # стек раздан тегами, отдельным блоком не выводится
        блоки = [b for b in блоки if b.strip() and не_старее(b, заголовок)]
        тело = "".join(блок_в_html(b, словарь) for b in блоки)
        кусок = f'<section><h2>{html.escape(заголовок)}</h2>{тело}</section>'
        (сайдбар if в_сайдбар(заголовок) else основное).append(кусок)

    переключатель = " ".join(
        f'<a href="{f}" class="{"тек" if l == язык else ""}">{m}</a>'
        for l, f, _, m in ЯЗЫКИ)
    контакт_html = "".join(f"<p>{строчный(c)}</p>" for c in контакты if c.strip())
    основное.insert(0, f'<section class="контакты"><h2>Контакты</h2>{контакт_html}</section>')

    (КОРЕНЬ / файл).write_text(ШАБЛОН.format(
        язык=язык, имя=html.escape(имя), роль=html.escape(роль),
        титул=html.escape(f"{имя} — {роль.split('·')[0].strip()}"),
        контакты=контакт_html, сайдбар="".join(сайдбар),
        основное="".join(основное), переключатель=переключатель,
    ), encoding="utf-8")
    print(f"  {файл}  ({len(сайдбар)} разделов слева, {len(основное)} справа)")


ШАБЛОН = """<!DOCTYPE html>
<html lang="{язык}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{титул}</title>
<style>
:root {{
  --тёмный:#2c3a4f; --поле:#eef1f5; --линия:#cfd6e0;
  --текст:#1b2430; --текст-2:#2d3747; --серый:#4e5a6b; --акцент:#1f4e79;
}}
*{{box-sizing:border-box}}
html{{-webkit-text-size-adjust:100%}}
body{{
  margin:0;background:#8d96a5;color:var(--текст);
  font:400 16.5px/1.62 -apple-system,BlinkMacSystemFont,"Segoe UI","Inter",
       "Helvetica Neue",Arial,sans-serif;
  -webkit-font-smoothing:antialiased;overflow-x:hidden;
}}
.лист{{max-width:1120px;margin:28px auto;background:#fff;box-shadow:0 2px 24px rgba(0,0,0,.22)}}
/* ── шапка ── */
.шапка{{background:var(--тёмный);color:#fff;padding:40px 48px 36px 300px;position:relative;min-height:176px}}
.фото{{position:absolute;left:44px;top:34px;width:216px;height:216px;border-radius:50%;
  object-fit:cover;object-position:50% 22%;border:9px solid #fff;background:#fff}}
.шапка h1{{margin:0;font-size:43px;line-height:1.06;letter-spacing:.05em;font-weight:800;text-transform:uppercase}}
.шапка .роль{{margin:12px 0 0;font-size:15.5px;line-height:1.5;letter-spacing:.11em;
  text-transform:uppercase;color:#cfd7e3;font-weight:400;max-width:48em}}
.языки{{position:absolute;right:30px;top:24px;display:flex;gap:5px}}
.языки a{{color:#b9c2d0;text-decoration:none;font-size:12.5px;letter-spacing:.1em;
  padding:5px 10px;border:1px solid #55617a;border-radius:3px}}
.языки a.тек{{color:#fff;border-color:#fff;background:rgba(255,255,255,.12)}}
/* ── колонки ── */
.тело{{display:grid;grid-template-columns:292px 1fr}}
.слева{{background:var(--поле);padding:40px 28px 48px}}
.справа{{padding:40px 52px 56px}}
/* ── заголовки ── */
h2{{font-size:15px;letter-spacing:.16em;text-transform:uppercase;margin:0 0 15px;
  padding-bottom:9px;border-bottom:2px solid var(--текст);font-weight:800}}
.слева section{{margin-bottom:32px}}
.слева h2{{font-size:13.5px;border-bottom-width:1.5px}}
.слева p{{margin:0 0 10px;font-size:14.5px;line-height:1.55;color:var(--текст-2);overflow-wrap:anywhere}}
.справа section{{margin-bottom:34px;padding-left:40px;position:relative}}
.справа section::before{{content:"";position:absolute;left:11px;top:4px;width:17px;height:17px;
  border-radius:50%;background:var(--тёмный)}}
.справа section::after{{content:"";position:absolute;left:19px;top:22px;bottom:6px;width:1px;background:var(--линия)}}
.справа section:last-child::after{{display:none}}
.справа p{{margin:0 0 12px;color:var(--текст-2)}}
/* ── записи ── */
.запись{{margin:0 0 20px}}
.запись h3{{margin:0 0 5px;font-size:16.5px;font-weight:700;line-height:1.35;
  display:flex;flex-wrap:wrap;justify-content:space-between;gap:4px 18px;align-items:baseline}}
.запись h3>strong{{flex:1 1 60%}}
.запись .дата{{flex:0 0 auto;font-size:13.5px;color:var(--серый);font-weight:500;letter-spacing:.02em}}
.запись p{{margin:0;color:var(--текст-2)}}
/* ── стек ── */
ul.стек{{list-style:none;margin:0;padding:0}}
ul.стек li{{margin-bottom:14px;font-size:14px;line-height:1.55}}
ul.стек li b{{display:block;font-size:12px;letter-spacing:.09em;text-transform:uppercase;
  color:var(--тёмный);margin-bottom:3px;font-weight:800}}
ul.стек li span{{color:var(--текст-2);overflow-wrap:anywhere}}
p.теги{{margin:9px 0 0;display:flex;flex-wrap:wrap;gap:6px}}
p.теги span{{font-size:12px;letter-spacing:.04em;background:#eef1f6;color:#33405a;
  border:1px solid #dde3ec;border-radius:3px;padding:3px 9px;white-space:nowrap}}
section.контакты p{{margin:0 0 7px;font-size:15px;color:var(--текст-2)}}
section.контакты{{margin-bottom:30px}}
a{{color:var(--акцент)}}
code{{background:#e7ebf1;padding:1px 5px;border-radius:3px;font-size:13.5px;
  font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}}
em{{color:var(--серый);font-size:13.5px}}
/* ── планшет ── */
@media (max-width:1000px){{
  .тело{{grid-template-columns:250px 1fr}}
  .справа{{padding:34px 32px 44px}}
  .шапка{{padding:34px 36px 30px 268px}} .шапка h1{{font-size:36px}}
}}
/* ── мобильный ── */
@media (max-width:760px){{
  body{{font-size:16px;background:#fff}}
  .лист{{margin:0;box-shadow:none}}
  .тело{{display:flex;flex-direction:column}}
  .справа{{order:1}} .слева{{order:2}}
  .шапка{{display:flex;flex-direction:column;align-items:center;
    padding:26px 20px 24px;text-align:center;min-height:0}}
  .шапка>div:last-of-type{{order:2}}
  .фото{{position:static;display:block;margin:0 auto 18px;width:148px;height:148px;border-width:6px}}
  .шапка h1{{font-size:27px;letter-spacing:.03em}}
  .шапка .роль{{font-size:13px;letter-spacing:.07em;margin:10px auto 0}}
  .языки{{position:static;order:3;justify-content:center;margin:20px 0 0}}
  .слева{{padding:28px 20px 30px}}
  .справа{{padding:28px 20px 40px}}
  .справа section{{padding-left:26px}}
  .справа section::before{{left:0;width:13px;height:13px;top:5px}}
  .справа section::after{{left:6px;top:20px}}
  .запись h3{{display:block;font-size:16px}}
  p.теги span{{font-size:11.5px;padding:3px 7px}}
  .запись .дата{{display:block;margin-top:2px;font-size:13px}}
  h2{{font-size:14px}}
}}
/* ── печать ── */
@media print{{
  body{{background:#fff;font-size:11pt;line-height:1.45}}
  .лист{{margin:0;box-shadow:none;max-width:none}}
  .языки{{display:none}}
  .шапка{{padding:22px 24px 20px 190px;min-height:0}}
  .фото{{width:140px;height:140px;left:26px;top:20px;border-width:5px}}
  .шапка h1{{font-size:27pt}} .шапка .роль{{font-size:9.5pt}}
  .слева,.справа{{padding:22px 20px}}
  section,.запись{{break-inside:avoid}}
}}
</style>
</head>
<body>
<div class="лист">
  <header class="шапка">
    <img class="фото" src="portret.png" alt="">
    <div class="языки">{переключатель}</div>
    <div>
      <h1>{имя}</h1>
      <p class="роль">{роль}</p>
    </div>
  </header>
  <div class="тело">
    <aside class="слева">{сайдбар}</aside>
    <main class="справа">{основное}</main>
  </div>
</div>
</body>
</html>
"""

if __name__ == "__main__":
    print("Сборка резюме из хранилища:")
    for я in ЯЗЫКИ:
        собрать(*я)
    print("Готово. Проверить:  serve .   →  http://localhost:3000/")
