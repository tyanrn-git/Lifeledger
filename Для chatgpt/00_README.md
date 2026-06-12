# Пакет для ChatGPT — LifeLedger

**Дата сборки:** 2026-06-11  
**Файлов в пакете:** 6 (лимит ChatGPT Project — 25)  
**Репозиторий:** https://github.com/tyanrn-git/Lifeledger  
**Прод:** Railway webhook, бот @MyLifeledgerbot

---

## Состав папки (только описания)

| Файл | Назначение |
|------|------------|
| `00_README.md` | Инструкция и Instructions для ChatGPT |
| `01_PROJECT_CONTEXT.md` | **Читать первым.** Состояние проекта + **полный функционал бота** (§2) |
| `02_DOCS_DELTA.md` | Расхождения документации v0 и реального кода |
| `03_DECISION_LOG.md` | Принятые решения после первоначальной документации |
| `04_ADMIN_DASHBOARD_SPEC.md` | ТЗ Web Admin Dashboard (живой документ) |
| `05_ADMIN_IMPLEMENTATION_PLAN.md` | **План работ** по фазам A–F, спринты, DoD |

**Не входит в пакет** (смотреть в репозитории на GitHub):

- Исходный код — `app/`
- Документация v0 — `PRD.md`, `architecture.md`, `database_schema.md`, `telegram_ux.md`, `DEPLOY.md`
- Миграции — `app/db/migrations/`

---

## Как обновлять в ChatGPT Project

1. Удалите старые файлы проекта в ChatGPT.
2. Загрузите **все 6 файлов** из этой папки.
3. В **Instructions** вставьте текст ниже.

### Instructions для ChatGPT Project

```
Ты консультант по проекту LifeLedger (Telegram-бот оценки жизненных событий).

Источники (в порядке приоритета):
1. 01_PROJECT_CONTEXT.md — актуальная правда о продукте и коде
2. 04_ADMIN_DASHBOARD_SPEC.md — ТЗ админки (scope)
3. 05_ADMIN_IMPLEMENTATION_PLAN.md — план работ и чеклисты (при реализации)
4. 02_DOCS_DELTA.md — что устарело в документации v0
5. 03_DECISION_LOG.md — принятые решения (не предлагай отклонённое)

Исходный код и полные доки v0 — в GitHub: github.com/tyanrn-git/Lifeledger

При конфликте: 01_PROJECT_CONTEXT > 04_ADMIN_DASHBOARD_SPEC > 03_DECISION_LOG.
Не предлагай фичи из раздела «Сознательно не делали» в PROJECT_CONTEXT.
```

---

## Когда обновлять пакет

После значимого релиза или продуктового решения:

1. `01_PROJECT_CONTEXT.md` — дата, коммит, новые фичи, пути в репо.
2. `04_ADMIN_DASHBOARD_SPEC.md` — при разработке админки + Changelog в конце файла.
3. `02_DOCS_DELTA.md` / `03_DECISION_LOG.md` — новые расхождения и решения.
4. Перезалить 6 файлов в ChatGPT.

Код в эту папку **не копировать** — лимит файлов и дублирование с GitHub.

---

## Покрытие функционала в пакете

| Область | Где описано |
|---------|-------------|
| Команды, сценарии, правила оценки | `01_PROJECT_CONTEXT.md` §2 |
| Лента, AI, scoring, БД | `01_PROJECT_CONTEXT.md` §4–5 |
| Расхождения с PRD v0 | `02_DOCS_DELTA.md` |
| Продуктовые решения | `03_DECISION_LOG.md` |
| Админка (ТЗ + lifecycle) | `04_ADMIN_DASHBOARD_SPEC.md` |
| План реализации админки | `05_ADMIN_IMPLEMENTATION_PLAN.md` |
| Детали промптов AI, SQL-запросы | Репозиторий `app/` |

---

## Чего нет намеренно

- `.env`, секреты, токены
- Снимки `.py` / `.sql`
- Копии `PRD.md` и др. (есть в корне репозитория)
- Тесты, CI, история чатов Cursor
