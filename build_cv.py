#!/usr/bin/env python3
"""Сборка страницы резюме из Markdown-источников в хранилище Obsidian.

Источник правды — заметки проекта «13 Резюме и поиск работы»; здесь только
вёрстка. Запуск:  python3 build_cv.py

На выходе index.html (RU), en.html, az.html в корне репозитория —
самодостаточные файлы со встроенным CSS, чтобы `serve .` работал без сборки.
"""
import html
import json
import re
import unicodedata
from datetime import date
from pathlib import Path

ХРАНИЛИЩЕ = Path.home() / "Projects/LifeTracker/LifeTracker/(P) Проекты/13 Резюме и поиск работы/50-резюме"
КОРЕНЬ = Path(__file__).parent

# Опыт до этого года на страницу не выводится — решение человека 2026-10-22.
# В хранилище полная хронология остаётся: это фильтр показа, а не правка резюме.
ОПЫТ_С = 2010

# Канонический адрес. Нужен и человеку (ссылка в подписи), и машине:
# по нему строятся canonical, hreflang, og:url и @id в JSON-LD.
САЙТ = "https://miniwe.github.io/"
ПРОФИЛИ = ["https://github.com/miniwe", "https://t.me/miniwe", САЙТ]

# Каждый язык живёт по своему подпути: /ru/, /en/, /az/. Русская лежит ещё
# и в корне — это основной адрес, его дают в отклике на вакансию, поэтому
# canonical русской указывает на «/», а /ru/ существует как копия для тех,
# кому уже отправляли такую ссылку (на сайте с августа были /en и /ru).
# код · адрес от корня · исходник · метка переключателя · локаль OG · город
ЯЗЫКИ = [
    ("ru", "", "резюме-2026-09.md", "RU", "ru_RU", "Баку"),
    ("en", "en/", "cv-2026-09-en.md", "EN", "en_US", "Baku"),
    ("az", "az/", "cv-2026-09-az.md", "AZ", "az_AZ", "Bakı"),
]
# Тот же язык по второму адресу. canonical такой страницы смотрит на основной.
АЛИАСЫ = [("ru", "ru/")]


def адрес(путь: str) -> str:
    """Относительный путь от корня → полный URL."""
    return САЙТ + путь


def наверх(путь: str) -> str:
    """Сколько раз подняться, чтобы попасть в корень: '' → '', 'en/' → '../'.
    Картинки и иконки лежат в корне, а страницы — на разной глубине."""
    return "../" * путь.count("/")

# Языки владения — из раздела «Образование и языки». Азербайджанского в списке
# нет намеренно: в резюме он не заявлен, а разметка не место для допущений.
ЯЗЫКИ_ВЛАДЕНИЯ = ["ru", "en", "sr", "tr"]

# Какие разделы уходят в левую колонку. Ключ — первое слово заголовка в нижнем
# регистре, чтобы одинаково ловить «Стек» / «Stack» / «Texnologiyalar».
# Слева остаются только короткие справочные блоки. Контакты и «Кратко»
# ушли вправо, а раздел «Стек» больше не выводится отдельным полотном:
# он разбирается на словарь и раздаётся тегами по кейсам и местам работы
# (решение человека 2026-10-22 — «полотно технологий оттолкнёт»).
В_САЙДБАР = {
    "кратко", "summary", "qisaca",            # о себе
    "образование", "education", "təhsil",      # образование и языки
    "формат", "working", "iş formatı",         # формат работы
}
СТЕК_РАЗДЕЛ = {"стек", "stack", "stek"}

# Контакты собираются не из раздела, а из шапки Markdown, поэтому заголовок
# к ним приходится называть здесь — единственная строка интерфейса в сборщике.
ПОДПИСЬ_КОНТАКТОВ = {"ru": "Контакты", "en": "Contact", "az": "Əlaqə"}


# Буквы, которые NFD не разлагает: у них нет базовой латинской формы с
# диакритикой, это самостоятельные знаки. Снимаем вручную, иначе «Qısaca»
# никогда не совпадёт с ключом «qisaca».
НЕРАЗЛОЖИМЫЕ = str.maketrans({"ı": "i", "ə": "e", "ß": "ss", "ø": "o", "đ": "d"})


def без_диакритики(s: str) -> str:
    """İş → is, Qısaca → qisaca. Турецкая İ в нижнем регистре даёт i +
    комбинирующую точку, из-за чего startswith('iş') не срабатывает."""
    разложено = unicodedata.normalize("NFD", s.lower().translate(НЕРАЗЛОЖИМЫЕ))
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
                    if not any(c.isalpha() for c in к):
                        continue  # «---» из разделителя таблицы — не технология
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
    "RAG": ["rag:", " rag ", "rag-"],
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
        # Что в хвосте — срок работы или уже текст записи? Сроком считаем
        # короткий хвост с годом, отметкой «по сей день» или длительностью
        # («15+ лет суммарно»). Длинное предложение — текст: «, 2000 —
        # факультет прикладной математики…» уходит в тело записи.
        if остаток and len(остаток) <= 48 and re.search(
                r"\d{4}|н\.\s?в\.|present|hazırda|indiyədək"
                r"|\d+\+?\s*(лет|год\w*|years?|il)\b", остаток, re.I):
            дата, остаток = остаток, ""
        тело = " ".join(([остаток] if остаток else []) + строки[1:]).strip()
        # Хвост после тире — начало предложения, а в Markdown он со строчной:
        # «**Геоаналитика** — исследовательский проект…».
        if остаток and тело[:1].islower():
            тело = тело[0].upper() + тело[1:]
        метка = f'<span class="дата">{строчный(дата)}</span>' if дата else ""
        низ = f"<p>{строчный(тело)}</p>" if тело else ""
        чипы = теги(блок, словарь) if словарь else ""
        return f'<article class="запись"><h3>{титул}{метка}</h3>{низ}{чипы}</article>'
    return f"<p>{строчный(' '.join(строки))}</p>"


# ──────────────────────────────────────────────────────────────────────────
# Метаданные. Отдельный блок, потому что читает их не человек: поисковик,
# превью в мессенджере, парсер вакансий и ИИ-скринер. Всё берётся из того же
# Markdown, что и видимый текст, — второго источника правды не заводим.

КРАТКО = {"кратко", "summary", "qisaca"}


def описание(разделы: dict, предел: int = 185) -> str:
    """Meta description: первый абзац «Кратко», целыми предложениями.

    Обрыв на полуслове в выдаче выглядит хуже, чем короткий текст, поэтому
    набираем предложения, пока помещаются, и останавливаемся."""
    for заголовок, блоки in разделы.items():
        if not any(без_диакритики(заголовок).startswith(к) for к in КРАТКО):
            continue
        if not блоки:
            return ""
        сырой = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", блоки[0])
        сырой = re.sub(r"[*`#]", "", сырой)
        сырой = re.sub(r"\s+", " ", сырой).strip()
        итог = ""
        for предложение in re.split(r"(?<=[.!?])\s+", сырой):
            if итог and len(итог) + 1 + len(предложение) > предел:
                break
            итог = f"{итог} {предложение}".strip()
        return итог or сырой[:предел]
    return ""


def навыки_разметки(словарь: list, текст: str, предел: int = 40) -> list:
    """knowsAbout для JSON-LD. Ядро стека вперёд: список режется по пределу, и
    алфавитный порядок выкинул бы как раз Qdrant, TypeScript и Node.js.
    Канонические написания из СИНОНИМЫ берём только если они есть в тексте —
    разметка не должна заявлять больше, чем сказано в резюме."""
    низ = текст.lower()
    ядро = [к for к, формы in СИНОНИМЫ.items() if any(ф in низ for ф in формы)]
    остальное = sorted((set(словарь) - set(ядро)), key=str.lower)
    return (sorted(ядро, key=str.lower) + остальное)[:предел]


def контактные_данные(контакты: list) -> dict:
    """Почта и телефон из строки контактов — для JSON-LD, где они отдельными
    полями, а не куском текста."""
    строка = " ".join(контакты)
    почта = re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", строка)
    телефон = re.search(r"\+\d[\d\s()\u2011-]{7,}\d", строка)
    return {
        "почта": почта.group(0) if почта else "",
        "телефон": re.sub(r"\s+", " ", телефон.group(0)).strip() if телефон else "",
    }


def цель(текст: str) -> str:
    """Поле target из фронтматтера — чем человек занят на рынке прямо сейчас.
    В разметке это Person.seeks: единственное место, где «ищу работу»
    написано машиночитаемо."""
    m = re.search(r"^target:\s*(.+)$", текст, re.M)
    return m.group(1).strip().strip('"') if m else ""


def разметка(язык, путь, имя, роль, опис, город, контакты, навыки, цель_, изменено):
    """JSON-LD: ProfilePage + Person. Ровно то, что читают Google, LinkedIn
    и парсеры вакансий; дублирует видимое на странице, ничего не добавляя."""
    страница = адрес(путь)
    человек = {
        "@type": "Person",
        "@id": САЙТ + "#person",
        "name": имя,
        "jobTitle": роль.split("·")[0].strip(),
        "description": опис,
        "url": САЙТ,
        "image": САЙТ + "portret.png",
        "sameAs": ПРОФИЛИ,
        "address": {"@type": "PostalAddress",
                    "addressLocality": город, "addressCountry": "AZ"},
        "alumniOf": {"@type": "CollegeOrUniversity",
                     "name": "Baku State University", "sameAs": "https://bsu.edu.az/"},
        "knowsLanguage": ЯЗЫКИ_ВЛАДЕНИЯ,
        "knowsAbout": навыки,
    }
    if контакты["почта"]:
        человек["email"] = "mailto:" + контакты["почта"]
    if контакты["телефон"]:
        человек["telephone"] = контакты["телефон"]
    if цель_:
        человек["seeks"] = {"@type": "Demand", "name": цель_}
    граф = {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "ProfilePage", "@id": страница + "#page", "url": страница,
             "name": f"{имя} — {роль.split('·')[0].strip()}",
             "inLanguage": язык, "dateModified": изменено,
             "mainEntity": {"@id": САЙТ + "#person"}},
            человек,
        ],
    }
    текст = json.dumps(граф, ensure_ascii=False, indent=1)
    # </script> внутри строки закрыл бы тег раньше времени
    return текст.replace("</", "<\\/")


def мета(язык, путь, канон, имя, роль, опис, локаль) -> str:
    """`путь` — где файл лежит (для относительных ссылок на иконки),
    `канон` — какой адрес объявлен основным. У копии /ru/ они расходятся."""
    вверх = наверх(путь)
    альтернативы = "\n".join(
        f'<link rel="alternate" hreflang="{л}" href="{адрес(ф)}">'
        for л, ф, *_ in ЯЗЫКИ)
    э = html.escape
    return f"""<meta name="description" content="{э(опис)}">
<meta name="author" content="{э(имя)}">
<meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large">
<link rel="canonical" href="{канон}">
{альтернативы}
<link rel="alternate" hreflang="x-default" href="{САЙТ}">
<meta property="og:type" content="profile">
<meta property="og:site_name" content="{э(имя)}">
<meta property="og:title" content="{э(имя)} — {э(роль.split('·')[0].strip())}">
<meta property="og:description" content="{э(опис)}">
<meta property="og:url" content="{канон}">
<meta property="og:image" content="{САЙТ}og-cover.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{э(имя)} — {э(роль.split('·')[0].strip())}">
<meta property="og:locale" content="{локаль}">
{chr(10).join(f'<meta property="og:locale:alternate" content="{л}">' for _, _, _, _, л, _ in ЯЗЫКИ if л != локаль)}
<meta property="profile:first_name" content="{э(имя.split()[0])}">
<meta property="profile:last_name" content="{э(имя.split()[-1])}">
<meta property="profile:username" content="miniwe">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{э(имя)} — {э(роль.split('·')[0].strip())}">
<meta name="twitter:description" content="{э(опис)}">
<meta name="twitter:image" content="{САЙТ}og-cover.png">
<meta name="theme-color" content="#2c3a4f">
<link rel="icon" href="{вверх}favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="{вверх}apple-touch-icon.png">"""


def собрать(язык, путь, исходник, метка, локаль, город, канон=None):
    """`путь` — адрес страницы от корня ('' = корень, 'en/' = /en/).
    `канон` задают только для копии: у /ru/ он указывает на корень."""
    канон = адрес(канон if канон is not None else путь)
    файл = (путь + "index.html") if путь else "index.html"
    источник = ХРАНИЛИЩЕ / исходник
    текст = источник.read_text(encoding="utf-8")
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

    вверх = наверх(путь)
    переключатель = " ".join(
        f'<a href="{вверх + f or "./"}" class="{"тек" if l == язык else ""}" '
        f'hreflang="{l}">{m}</a>'
        for l, f, _, m, _loc, _г in ЯЗЫКИ)
    контакт_html = "".join(f"<p>{строчный(c)}</p>" for c in контакты if c.strip())
    подпись = html.escape(ПОДПИСЬ_КОНТАКТОВ.get(язык, "Контакты"))
    сайдбар.insert(0, f'<section class="контакты"><h2>{подпись}</h2>{контакт_html}</section>')

    опис = описание(разделы)
    изменено = date.fromtimestamp(источник.stat().st_mtime).isoformat()
    навыки = навыки_разметки(словарь, текст)

    куда = КОРЕНЬ / файл
    куда.parent.mkdir(parents=True, exist_ok=True)
    куда.write_text(ШАБЛОН.format(
        язык=язык, имя=html.escape(имя), роль=html.escape(роль),
        титул=html.escape(f"{имя} — {роль.split('·')[0].strip()}"),
        вверх=вверх,
        мета=мета(язык, путь, канон, имя, роль, опис, локаль),
        разметка=разметка(язык, канон.removeprefix(САЙТ), имя, роль, опис, город,
                          контактные_данные(контакты), навыки,
                          цель(текст), изменено),
        контакты=контакт_html, сайдбар="".join(сайдбар),
        основное="".join(основное), переключатель=переключатель,
    ), encoding="utf-8")
    print(f"  /{путь}  → {файл}  ({len(сайдбар)} слева, {len(основное)} справа, "
          f"description {len(опис)} знаков, knowsAbout {len(навыки)})")


ШАБЛОН = """<!DOCTYPE html>
<html lang="{язык}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{титул}</title>
{мета}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<!-- Montserrat — заголовки, теги и мелкие надписи; Inter — текст.
     Подсеты latin, latin-ext и cyrillic: latin-ext нужен азербайджанскому
     (ə, ğ, ı, İ, ö, ş, ü, ç), cyrillic — русскому. -->
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Montserrat:wght@600;700;800&display=swap&subset=latin,latin-ext,cyrillic" rel="stylesheet">
<style>
:root {{
  --тёмный:#2c3a4f; --поле:#eef1f5; --линия:#cfd6e0;
  --текст:#1b2430; --текст-2:#2d3747; --серый:#4e5a6b; --акцент:#1f4e79;
  --шрифт-текст:"Inter",-apple-system,BlinkMacSystemFont,"Segoe UI","Helvetica Neue",Arial,sans-serif;
  --шрифт-заголовки:"Montserrat","Inter",-apple-system,"Segoe UI",Arial,sans-serif;
}}
*{{box-sizing:border-box}}
html{{-webkit-text-size-adjust:100%}}
body{{
  margin:0;background:#8d96a5;color:var(--текст);
  font:400 16.5px/1.62 var(--шрифт-текст);
  -webkit-font-smoothing:antialiased;overflow-x:hidden;
}}
.лист{{max-width:1120px;margin:28px auto;background:#fff;box-shadow:0 2px 24px rgba(0,0,0,.22)}}
/* ── шапка ── */
.шапка{{background:var(--тёмный);color:#fff;padding:40px 48px 36px 300px;position:relative;min-height:176px}}
.фото{{position:absolute;left:44px;top:34px;width:216px;height:216px;border-radius:50%;
  object-fit:cover;object-position:50% 22%;border:9px solid #fff;background:#fff}}
.шапка h1{{font-family:var(--шрифт-заголовки);margin:0;font-size:35px;line-height:1.1;letter-spacing:.045em;font-weight:800;text-transform:uppercase}}
.шапка .роль{{font-family:var(--шрифт-заголовки);margin:12px 0 0;font-size:14.5px;line-height:1.55;letter-spacing:.1em;
  text-transform:uppercase;color:#e3e8f0;font-weight:600;max-width:48em}}
/* Строка роли двуязычная: английское название должности плюс фраза на
   языке страницы. Браузер под lang="az" поднимает регистр по турецким
   правилам и «Senior / TypeScript» становятся «SENİOR / TYPESCRİPT».
   Правила для английского сломали бы азербайджанское «texniki» → «TEXNIKI».
   Единственный честный выход — не трогать регистр на этой странице;
   заголовки разделов остаются прописными, они целиком азербайджанские. */
html[lang="az"] .шапка .роль{{text-transform:none;letter-spacing:.04em}}
.языки{{position:absolute;right:30px;top:24px;display:flex;gap:5px}}
.языки a{{font-family:var(--шрифт-заголовки);color:#c8d0dd;text-decoration:none;font-size:12.5px;font-weight:600;letter-spacing:.1em;
  padding:5px 10px;border:1px solid #55617a;border-radius:3px}}
.языки a.тек{{color:#fff;border-color:#fff;background:rgba(255,255,255,.12)}}
/* ── колонки ── */
.тело{{display:grid;grid-template-columns:360px 1fr}}
.слева{{background:var(--поле);padding:112px 34px 48px}}
.справа{{padding:40px 52px 56px}}
/* ── заголовки ── */
h2{{font-family:var(--шрифт-заголовки);font-size:15px;letter-spacing:.16em;text-transform:uppercase;margin:0 0 15px;
  padding-bottom:9px;border-bottom:2px solid var(--текст);font-weight:800}}
.слева section{{margin-bottom:32px}}
.слева h2{{font-size:13.5px;border-bottom-width:1.5px}}
.слева p{{margin:0 0 11px;font-size:14.8px;line-height:1.58;color:var(--текст-2);overflow-wrap:anywhere}}
.справа section{{margin-bottom:34px;padding-left:40px;position:relative}}
.справа section::before{{content:"";position:absolute;left:11px;top:4px;width:17px;height:17px;
  border-radius:50%;background:var(--тёмный)}}
.справа section::after{{content:"";position:absolute;left:19px;top:22px;bottom:6px;width:1px;background:var(--линия)}}
.справа section:last-child::after{{display:none}}
.справа p{{margin:0 0 12px;color:var(--текст-2)}}
/* ── записи ── */
.запись{{margin:0 0 20px}}
.запись h3{{font-family:var(--шрифт-заголовки);margin:0 0 5px;font-size:16.5px;font-weight:700;line-height:1.35;
  display:flex;flex-wrap:wrap;justify-content:space-between;gap:4px 18px;align-items:baseline}}
.запись h3>strong{{flex:1 1 60%}}
.запись .дата{{font-family:var(--шрифт-заголовки);flex:0 0 auto;font-size:13.5px;color:var(--серый);font-weight:500;letter-spacing:.02em}}
.запись p{{margin:0;color:var(--текст-2)}}
/* ── стек ── */
ul.стек{{list-style:none;margin:0;padding:0}}
ul.стек li{{margin-bottom:14px;font-size:14px;line-height:1.55}}
ul.стек li b{{font-family:var(--шрифт-заголовки);display:block;font-size:12px;letter-spacing:.09em;text-transform:uppercase;
  color:var(--тёмный);margin-bottom:3px;font-weight:800}}
ul.стек li span{{color:var(--текст-2);overflow-wrap:anywhere}}
p.теги{{margin:9px 0 0;display:flex;flex-wrap:wrap;gap:6px}}
p.теги span{{font-family:var(--шрифт-заголовки);font-size:12px;font-weight:600;letter-spacing:.05em;background:var(--тёмный);
  color:#fff;border-radius:3px;padding:4px 10px;white-space:nowrap;
  -webkit-print-color-adjust:exact;print-color-adjust:exact}}
section.контакты p{{margin:0 0 7px;font-size:15px;color:var(--текст-2)}}
section.контакты{{margin-bottom:30px}}
a{{color:var(--акцент)}}
code{{background:#e7ebf1;padding:1px 5px;border-radius:3px;font-size:13.5px;
  font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}}
em{{color:var(--серый);font-size:13.5px}}
/* ── планшет ── */
@media (max-width:1000px){{
  .тело{{grid-template-columns:300px 1fr}}
  .слева{{padding:104px 24px 40px}}
  .справа{{padding:34px 32px 44px}}
  .шапка{{padding:34px 36px 30px 268px}} .шапка h1{{font-size:31px}}
}}
/* ── мобильный ── */
@media (max-width:760px){{
  body{{font-size:16px;background:#fff}}
  .лист{{margin:0;box-shadow:none}}
  .тело{{display:flex;flex-direction:column}}
  .слева{{order:1}} .справа{{order:2}}
  .шапка{{display:flex;flex-direction:column;align-items:center;
    padding:26px 20px 24px;text-align:center;min-height:0}}
  .шапка>div:last-of-type{{order:2}}
  .фото{{position:static;display:block;margin:0 auto 18px;width:148px;height:148px;border-width:6px}}
  .шапка h1{{font-size:24px;letter-spacing:.03em}}
  .шапка .роль{{font-size:13px;letter-spacing:.07em;margin:10px auto 0}}
  .языки{{position:static;order:3;justify-content:center;margin:20px 0 0}}
  .слева{{padding:26px 20px 30px}}
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
@page {{ margin: 9mm 9mm 8mm; }}
@media print {{
  html,body{{background:#fff}}
  body{{font-size:9.4pt;line-height:1.4;color:#000}}
  .лист{{margin:0;box-shadow:none;max-width:none}}
  .языки{{display:none}}
  .шапка,p.теги span,.слева{{-webkit-print-color-adjust:exact;print-color-adjust:exact}}
  /* Шапка выше фото целиком, иначе круг налезает на первый заголовок. */
  .шапка{{padding:13px 16px 12px 142px;min-height:132px}}
  .фото{{width:104px;height:104px;left:18px;top:12px;border-width:4px}}
  .шапка h1{{font-size:19pt;letter-spacing:.04em}}
  .шапка .роль{{font-size:7.6pt;letter-spacing:.06em;margin-top:6px}}

  /* Две колонки в печати не нужны: серый блок кончается на первой
     странице, а колонка тянется пустой до конца документа. Распускаем
     сетку — серый блок идёт полосой сверху в три колонки текста,
     остальное ниже во всю ширину. */
  .тело{{display:block}}
  .слева{{background:#f2f4f8;padding:11px 16px 9px;
    column-count:3;column-gap:16px;column-fill:balance}}
  .слева section{{margin:0 0 9px;break-inside:avoid}}
  .слева h2{{font-size:7.8pt;margin-bottom:6px;padding-bottom:4px}}
  .слева p{{font-size:8.3pt;line-height:1.38;margin-bottom:5px}}
  .слева .запись h3{{font-size:8.6pt}}
  .слева p.теги{{display:none}}  /* теги в «Кратко» дублируют кейсы */

  .справа{{padding:14px 2px 0}}
  h2{{font-size:8.8pt;margin-bottom:8px;padding-bottom:5px;border-bottom-width:1.3pt}}
  .справа section{{margin-bottom:14px;padding-left:22px}}
  .справа section::before{{width:9px;height:9px;left:4px;top:3px}}
  .справа section::after{{left:8px;top:13px}}
  .запись{{margin-bottom:9px}}
  .запись h3{{font-size:9.6pt;margin-bottom:2px}}
  .запись .дата{{font-size:8pt}}
  .справа p,.запись p{{margin-bottom:5px}}
  p.теги{{margin-top:4px;gap:3px}}
  p.теги span{{font-size:7.2pt;padding:1.5px 5px;border-radius:2px}}
  code{{background:#eceff3;font-size:8.4pt}}
  a{{color:#000;text-decoration:none}}
  /* Целую секцию «не рвать» нельзя: «Опыт работы» длиннее страницы и
     улетает целиком, оставляя пустоту. Не рвутся только записи и их
     заголовки, а заголовок секции не отрывается от первой записи. */
  .запись,.запись h3{{break-inside:avoid;page-break-inside:avoid}}
  .справа section{{break-inside:auto;page-break-inside:auto}}
  h2{{break-after:avoid;page-break-after:avoid}}
  .справа section>h2+.запись{{break-before:avoid;page-break-before:avoid}}
}}
</style>
<script type="application/ld+json">
{разметка}
</script>
</head>
<body>
<div class="лист">
  <header class="шапка">
    <img class="фото" src="{вверх}portret.png" alt="">
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

def карта_сайта():
    """sitemap.xml с перекрёстными hreflang: иначе поисковик считает три языка
    тремя разными страницами и выбирает из них одну на свой вкус."""
    ссылки = "".join(
        f'\n    <xhtml:link rel="alternate" hreflang="{л}" href="{адрес(ф)}"/>'
        for л, ф, *_ in ЯЗЫКИ)
    ссылки += f'\n    <xhtml:link rel="alternate" hreflang="x-default" href="{САЙТ}"/>'
    записи = []
    for _, путь, исходник, *_ in ЯЗЫКИ:
        изменено = date.fromtimestamp((ХРАНИЛИЩЕ / исходник).stat().st_mtime)
        записи.append(f"""  <url>
    <loc>{адрес(путь)}</loc>
    <lastmod>{изменено.isoformat()}</lastmod>{ссылки}
  </url>""")
    (КОРЕНЬ / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"\n'
        '        xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
        + "\n".join(записи) + "\n</urlset>\n", encoding="utf-8")
    print(f"  sitemap.xml ({len(записи)} адреса)")


if __name__ == "__main__":
    print("Сборка резюме из хранилища:")
    for я in ЯЗЫКИ:
        собрать(*я)
    for язык, путь in АЛИАСЫ:
        основной = next(я for я in ЯЗЫКИ if я[0] == язык)
        собрать(язык, путь, *основной[2:], канон=основной[1])
    карта_сайта()
    print("Готово. Проверить:  serve .   →  http://localhost:3000/")
