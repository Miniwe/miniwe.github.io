#!/usr/bin/env python3
"""ATS-версия резюме: для машинного разбора, не для глаз.

Отдельный выход от `build_cv.py`. Сайт сделан для людей — две колонки,
фото, теги, кураторский стек. Всё это ломает разбор в Applicant Tracking
System: двухколоночный макет перетекает построчно и даты прилипают не к
тем местам работы, фото и иконки становятся мусором, нестандартные
заголовки парсер не узнаёт. Около 70% отказов на этом уровне —
формат, а не содержание (разбор рынка 2026-10-22 в хранилище).

Поэтому здесь ровно наоборот:
  - одна колонка, никаких таблиц, фото и иконок;
  - стандартные заголовки: Опыт работы, Навыки, Образование;
  - даты ММ/ГГГГ, местоположение отдельной строкой от дат;
  - ПОЛНЫЙ список технологий: частота ключевых слов при скрининге
    по-прежнему весит, а на сайте стек намеренно сокращён;
  - системный шрифт, крупный кегль, текстовый слой в PDF.

Запуск:  python3 build_ats.py   →  ats-ru.html, ats-en.html, ats-az.html
PDF:     node build_ats_pdf.js  (нужен puppeteer)
"""
import html
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from build_cv import ХРАНИЛИЩЕ, КОРЕНЬ, разобрать, без_диакритики, не_старее

# Полный стек — из снимка до сокращения (public/src/ru.md, 2026-10-02).
# На сайте он намеренно сжат, здесь нужен целиком ради ключевых слов.
НАВЫКИ = {
 "ru": [
  ("Языки и платформы", "Node.js, TypeScript, JavaScript, PHP 8.4, Python, Rust, Go"),
  ("Бэкенд", "NestJS, Express, Meteor.js, Laravel 12, Symfony, REST, GraphQL, Apollo, OpenAPI, gRPC"),
  ("Данные и очереди", "PostgreSQL, MySQL, MongoDB, Redis, TypeORM, Sequelize, Prisma, BullMQ, RabbitMQ, транзакции, уровни изоляции, индексы, планы выполнения"),
  ("Фронтенд", "React, Redux Toolkit, Redux Saga, Effector, MobX, Next.js, Vue, Inertia.js, FSD, TanStack, Ant Design, Material UI, Tailwind, Sass, PostCSS, BEM, Highcharts, GSAP, SVG"),
  ("Инфраструктура и DevOps", "Docker, docker-compose, multi-stage сборки, CI/CD, GitHub Actions, Caddy, HAProxy, nginx, Linux, Ubuntu, Oracle Cloud, VPS, S3, MinIO, Tailscale"),
  ("ИИ и машинное обучение", "LLM, RAG, retrieval, векторный поиск, Qdrant, pgvector, BM25, эмбеддинги, multilingual-e5-small, LiteLLM, OpenRouter, Ollama, MCP, агенты, function calling, структурированный вывод, стриминг, prompt engineering, оценка качества, эталонные наборы"),
  ("Качество и эксплуатация", "Jest, Playwright, автотесты, E2E, структурные логи, health-checks, метрики, мониторинг, поэтапные выкатки"),
  ("ГИС и данные", "Leaflet, H3, Google Maps API, Яндекс.Карты API, Sentinel-2, Google Earth Engine, Copernicus"),
  ("Методология", "Agile, Scrum, код-ревью, технические собеседования, архитектурные решения (ADR), Johnny.Decimal, PARA"),
 ],
 "en": [
  ("Languages and platforms", "Node.js, TypeScript, JavaScript, PHP 8.4, Python, Rust, Go"),
  ("Backend", "NestJS, Express, Meteor.js, Laravel 12, Symfony, REST, GraphQL, Apollo, OpenAPI, gRPC"),
  ("Data and queues", "PostgreSQL, MySQL, MongoDB, Redis, TypeORM, Sequelize, Prisma, BullMQ, RabbitMQ, transactions, isolation levels, indexes, query plans"),
  ("Frontend", "React, Redux Toolkit, Redux Saga, Effector, MobX, Next.js, Vue, Inertia.js, FSD, TanStack, Ant Design, Material UI, Tailwind, Sass, PostCSS, BEM, Highcharts, GSAP, SVG"),
  ("Infrastructure and DevOps", "Docker, docker-compose, multi-stage builds, CI/CD, GitHub Actions, Caddy, HAProxy, nginx, Linux, Ubuntu, Oracle Cloud, VPS, S3, MinIO, Tailscale"),
  ("AI and machine learning", "LLM, RAG, retrieval, vector search, Qdrant, pgvector, BM25, embeddings, multilingual-e5-small, LiteLLM, OpenRouter, Ollama, MCP, agents, function calling, structured outputs, streaming, prompt engineering, evaluation, reference sets"),
  ("Quality and operations", "Jest, Playwright, automated tests, E2E, structured logging, health checks, metrics, monitoring, staged rollouts"),
  ("GIS and data", "Leaflet, H3, Google Maps API, Yandex Maps API, Sentinel-2, Google Earth Engine, Copernicus"),
  ("Methodology", "Agile, Scrum, code review, technical interviews, architecture decision records, Johnny.Decimal, PARA"),
 ],
}
НАВЫКИ["az"] = НАВЫКИ["en"]

ЗАГОЛОВКИ = {
 "ru": dict(контакты="Контакты", профиль="Профиль", навыки="Навыки",
            опыт="Опыт работы", проекты="Проекты", образование="Образование",
            языки="Языки", формат="Формат работы"),
 "en": dict(контакты="Contact", профиль="Profile", навыки="Skills",
            опыт="Work Experience", проекты="Projects", образование="Education",
            языки="Languages", формат="Work arrangement"),
}
ЗАГОЛОВКИ["az"] = ЗАГОЛОВКИ["en"]

# По чему узнаём абзац про владение языками внутри раздела образования.
ЯЗЫКОВОЙ = re.compile(
    r"родной|native|ana dili|разговорн|conversational|danışıq|B1|B2|C1", re.I)

ЯЗЫКИ = [("ru", "ats-ru.html", "резюме-2026-09.md"),
         ("en", "ats-en.html", "cv-2026-09-en.md"),
         ("az", "ats-az.html", "cv-2026-09-az.md")]

ТЕКУЩЕЕ = {"ru": "настоящее время", "en": "present", "az": "present"}

# Куда указывает canonical: на человеческую версию того же языка.
КАНОН = {"ru": "https://miniwe.github.io/",
         "en": "https://miniwe.github.io/en.html",
         "az": "https://miniwe.github.io/az.html"}

ШАБЛОН = """<!DOCTYPE html>
<html lang="{язык}">
<head>
<meta charset="utf-8">
<title>{имя} — {роль_кратко}</title>
<!-- Машинная версия того же резюме. В выдачу её не пускаем: для поисковика
     это дубль index.html, и дубль без вёрстки вытеснил бы оригинал. Канонический
     адрес указан явно, за парсером вакансий файл остаётся доступен. -->
<meta name="robots" content="noindex,follow">
<link rel="canonical" href="{канон}">
<style>
@page {{ margin: 11mm 13mm; }}
body {{ font-family: Arial, Helvetica, sans-serif; font-size: 10pt; line-height: 1.32;
  color:#000; background:#fff; margin:0 auto; max-width:188mm; padding:14mm 4mm; }}
h1 {{ font-size:18pt; margin:0 0 2px; font-weight:700; letter-spacing:0 }}
.роль {{ font-size:11pt; margin:0 0 10px; font-weight:700 }}
h2 {{ font-size:11pt; margin:11px 0 5px; font-weight:700; text-transform:uppercase;
  border-bottom:1px solid #000; padding-bottom:2px }}
h3 {{ font-size:10.3pt; margin:7px 0 1px; font-weight:700 }}
p {{ margin:0 0 4px }}
.мета {{ margin:0 0 3px }}
.навык {{ margin:0 0 4px }}
ul {{ margin:0 0 6px; padding-left:17px }}
li {{ margin-bottom:2px }}
a {{ color:#000 }}
@media print {{ body{{padding:0;max-width:none}} h2,h3{{break-after:avoid}} .запись{{break-inside:avoid}} }}
</style>
</head>
<body>
<h1>{имя}</h1>
<p class="роль">{роль}</p>
{тело}
</body>
</html>
"""


def чистый(s: str) -> str:
    """Текст без разметки и символов, которые сбивают парсер."""
    s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)
    s = re.sub(r"[*`]", "", s)
    # «·» разделяет пункты, «—» стоит внутри пункта. Если оба станут
    # тире, строка «Русский — родной · Английский — B1» превращается в
    # кашу из дефисов. Разделитель делаем точкой с запятой.
    s = re.sub(r"\s*·\s*", "; ", s).replace("—", "-").replace("→", "->")
    s = re.sub(r"[^\S\n]+", " ", s)
    return html.escape(s.strip())


def контакты_строками(контакты, язык):
    """Иконки и всё в одну строку парсер читает плохо — разносим по строкам."""
    текст = " ".join(контакты)
    поля = []
    for шаблон, метка in [
            (r"(\+\d[\d\s]{8,})", {"ru": "Телефон", "en": "Phone"}),
            (r"([\w.+-]+@[\w-]+\.[\w.]+)", {"ru": "Email", "en": "Email"}),
            (r"Telegram\s*\[?@?([\w]+)", {"ru": "Telegram", "en": "Telegram"}),
            (r"(github\.com/[\w-]+)", {"ru": "GitHub", "en": "GitHub"}),
            (r"(miniwe\.github\.io)", {"ru": "Сайт", "en": "Website"})]:
        м = re.search(шаблон, текст)
        if м:
            поля.append((метка.get(язык, метка["en"]), м.group(1).strip()))
    место = re.search(r"(Баку[^·\n]*|Bak[ıi][^·\n]*)", текст)
    if место:
        поля.insert(0, ({"ru": "Местоположение"}.get(язык, "Location"),
                        чистый(место.group(1))))
    return "".join(f'<p class="мета">{м}: {чистый(з)}</p>' for м, з in поля)


def абзацы(блок: str) -> str:
    """Профиль — обычный текст, без заголовков и мета-строк."""
    return "".join(f"<p>{чистый(с)}</p>" for с in блок.split("\n") if с.strip())


def запись_в_html(блок: str, язык: str) -> str:
    строки = блок.split("\n")
    m = re.match(r"\*\*(.+?)\*\*(.*)$", строки[0])
    if not m:
        return f"<p>{чистый(' '.join(строки))}</p>"
    титул = чистый(m.group(1))
    хвост = m.group(2).strip().lstrip("-—·,").strip()
    дата = место = ""
    if хвост:
        # «Баку, Азербайджан · 06/2026 - н.в.» → место и даты раздельно
        д = re.search(r"((?:\d{2}/)?\d{4}\s*[–—-]\s*"
                      r"(?:(?:\d{2}/)?\d{4}|н\.\s?в\.|present|hazırda|indiyədək))", хвост)
        if д:
            дата = д.group(1)
            место = хвост[:д.start()].strip(" ·-,")
            дата = re.sub(r"н\.\s?в\.|hazırda|indiyədək", ТЕКУЩЕЕ[язык], дата)
        elif len(хвост) <= 48 and re.search(
                r"\d+\+?\s*(лет|год\w*|years?|il)\b", хвост, re.I):
            # «15+ лет суммарно, параллельно основным местам» — тоже срок.
            дата = хвост
        else:
            # Ни года, ни длительности — значит это не место и не дата,
            # а начало текста. Иначе проза проектов уезжает в мета-строку.
            строки = [строки[0]] + [хвост] + строки[1:]
    тело = чистый(" ".join(строки[1:]))
    # Хвост после тире в Markdown начинается со строчной буквы, а в ATS это
    # первое предложение абзаца.
    if тело[:1].islower():
        тело = тело[0].upper() + тело[1:]
    куски = [f"<h3>{титул}</h3>"]
    мета = " | ".join(x for x in (дата, чистый(место)) if x)
    if мета:
        куски.append(f'<p class="мета">{мета}</p>')
    if тело:
        куски.append(f"<p>{тело}</p>")
    return f'<div class="запись">{"".join(куски)}</div>'


def собрать(язык, файл, исходник):
    имя, роль, контакты, разделы = разобрать((ХРАНИЛИЩЕ / исходник).read_text(encoding="utf-8"))
    З = ЗАГОЛОВКИ[язык]
    части = [f"<h2>{З['контакты']}</h2>", контакты_строками(контакты, язык)]

    def раздел(ключ, заголовок, фильтр, как_текст=False):
        блоки = [(к, b) for к, бс in разделы.items() if фильтр(к)
                 for b in бс if b.strip() and не_старее(b, к)]
        if not блоки:
            return
        части.append(f"<h2>{заголовок}</h2>")
        части.extend(абзацы(b) if как_текст else запись_в_html(b, язык) for _, b in блоки)

    раздел("профиль", З["профиль"],
           lambda к: без_диакритики(к).startswith(("кратко", "summary", "qisaca")),
           как_текст=True)
    части.append(f"<h2>{З['навыки']}</h2>")
    части.extend(f'<p class="навык"><b>{г}:</b> {с}</p>' for г, с in НАВЫКИ[язык])
    раздел("опыт", З["опыт"], lambda к: без_диакритики(к).startswith(("опыт", "experience", "is tecrubesi")))
    раздел("кейсы", З["проекты"],
           lambda к: без_диакритики(к).startswith(("ключевые", "selected", "esas", "собственные", "own", "oz")))
    # Языки парсер ждёт отдельным разделом, а в источнике они живут вместе
    # с образованием одним абзацем без заголовка — разводим здесь.
    обр = [b for к, бс in разделы.items()
           if без_диакритики(к).startswith(("образование", "education", "tehsil"))
           for b in бс if b.strip()]
    языковые = [b for b in обр if not b.startswith("**") and ЯЗЫКОВОЙ.search(b)]
    учебные = [b for b in обр if b not in языковые]
    if учебные:
        части.append(f"<h2>{З['образование']}</h2>")
        части.extend(запись_в_html(b, язык) for b in учебные)
    if языковые:
        части.append(f"<h2>{З['языки']}</h2>")
        части.extend(абзацы(b) for b in языковые)
    раздел("формат", З["формат"],
           lambda к: без_диакритики(к).startswith(("формат", "working", "is formati")))

    (КОРЕНЬ / файл).write_text(ШАБЛОН.format(
        канон=КАНОН[язык],
        язык=язык, имя=html.escape(имя), роль=чистый(роль),
        роль_кратко=html.escape(роль.split("·")[0].strip()),
        тело="\n".join(части)), encoding="utf-8")
    print(f"  {файл}")


if __name__ == "__main__":
    print("ATS-версия (одна колонка, без фото и таблиц):")
    for я in ЯЗЫКИ:
        собрать(*я)
    print("PDF:  node build_ats_pdf.js")
