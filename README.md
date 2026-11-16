# Job Tracker Bot

Telegram-бот, який трекає вакансії, і вебсторінка до нього.

Кидаєш у бот текст вакансії або посилання. Gemini повертає JSON за схемою (компанія, роль, стек, зарплата, формат, рівень), бот зберігає запис у Supabase і відповідає резюме з inline-кнопками статусу. Сторінка на Next.js показує таблицю вакансій із фільтром за статусом.

## Стек

- **Бот:** Python, python-telegram-bot, Gemini API (structured output), Supabase REST API
- **Веб:** Next.js (App Router, серверні компоненти), TypeScript, supabase-js
- **Деплой:** Render (бот, webhook), Vercel (сторінка)

## Команди бота

| Команда | Що робить |
|---|---|
| текст або посилання | розбирає вакансію і зберігає її |
| `/list` | останні 10 вакансій зі статусами |
| `/stats` | скільки відгуків, співбесід і відмов |
| `/match [id]` | порівнює вакансію з твоїм стеком і пише, чого бракує (без id бере останню) |

## Структура

```
bot/        Telegram-бот (main.py, ai.py, db.py, scrape.py, config.py)
web/        сторінка на Next.js
supabase/   schema.sql — таблиця vacancies
render.yaml конфіг деплою бота
```

## Запуск

### 1. Ключі

1. **Telegram:** створи бота в @BotFather, візьми токен.
2. **Gemini:** ключ на https://aistudio.google.com/apikey
3. **Supabase:** створи проєкт, у SQL Editor виконай `supabase/schema.sql`. У налаштуваннях API візьми Project URL і secret (service_role) ключ.

### 2. Бот локально

```
cd bot
pip install -r requirements.txt
copy .env.example .env      # заповни значення
python main.py
```

Напиши боту `/start`: він покаже твій Telegram ID. Впиши його в `ALLOWED_USER_IDS`, щоб ботом користувався тільки ти.

### 3. Сторінка локально

```
cd web
npm install
copy .env.example .env.local   # SUPABASE_URL і SUPABASE_KEY
npm run dev
```

### 4. Деплой

- **Бот на Render:** New -> Blueprint, вибери репозиторій (Render прочитає `render.yaml`), заповни env-змінні. Бот сам перейде в режим webhook. На безкоштовному плані сервіс засинає, тому перша відповідь після паузи може йти до хвилини.
- **Сторінка на Vercel:** імпортуй репозиторій, Root Directory = `web`, додай `SUPABASE_URL` і `SUPABASE_KEY` в Environment Variables.

## Безпека

- Усі ключі тільки в env-змінних, `.env` у `.gitignore`.
- У таблиці ввімкнено RLS без політик: публічний ключ нічого не читає, доступ має лише серверний ключ.
- Сторінка читає Supabase на сервері, ключ у браузер не потрапляє.
