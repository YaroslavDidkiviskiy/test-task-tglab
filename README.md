# Expedition API

Backend сервіс для керування експедиціями на FastAPI + PostgreSQL + WebSocket.

---

## Стек

- **FastAPI** — веб фреймворк
- **SQLAlchemy 2.0 async** — ORM
- **Alembic** — міграції
- **PostgreSQL** — база даних
- **argon2** — хешування паролів
- **JWT** — авторизація (access + refresh token rotation)
- **WebSocket** — real-time події

---

## Запуск через Docker

```bash
git clone <repo>
cd expedition
cp .env.example .env
docker-compose up --build
```

- API: `http://localhost:8000`
- Документація: `http://localhost:8000/docs`

Міграції застосовуються автоматично при старті.

---

## Локальний запуск

```bash
pip install -r requirements.txt
# налаштуй .env
alembic upgrade head
uvicorn app.main:app --reload
```

---

## Змінні середовища

Скопіюй `.env.example` в `.env` і заповни:

| Змінна | Опис | Default |
|--------|------|---------|
| `DATABASE_URL` | рядок підключення до PostgreSQL | — |
| `SECRET_KEY` | секретний ключ для JWT | — |
| `ACCESS_EXPIRE_MIN` | час життя access token (хв) | 30 |
| `REFRESH_EXPIRE_DAYS` | час життя refresh token (дні) | 30 |
| `DEBUG` | SQL логи | false |

---

## Авторизація

JWT авторизація. Access token передається в заголовку:

```
Authorization: Bearer <access_token>
```

Refresh token зберігається в httponly cookie. Реалізована ротація refresh токенів — при кожному `/auth/refresh` старий токен інвалідується і видається новий.

---

## Ендпоінти

### Auth

| Метод | URL | Опис |
|-------|-----|------|
| POST | `/auth/register` | Реєстрація |
| POST | `/auth/login` | Логін, повертає access token |
| POST | `/auth/refresh` | Оновлення токенів |
| POST | `/auth/logout` | Вихід |

### Expeditions

| Метод | URL | Доступ | Опис |
|-------|-----|--------|------|
| POST | `/expeditions` | chief | Створити експедицію |
| GET | `/expeditions` | всі | Список своїх експедицій |
| GET | `/expeditions/{id}` | всі | Деталі експедиції |
| POST | `/expeditions/{id}/status/ready` | chief | Перевести в ready |
| POST | `/expeditions/{id}/status/active` | chief | Запустити |
| POST | `/expeditions/{id}/status/finished` | chief | Завершити |
| POST | `/expeditions/{id}/members` | chief | Запросити учасника |
| POST | `/expeditions/{id}/members/confirm` | member | Підтвердити участь |

### WebSocket

```
ws://localhost:8000/ws/expeditions/{expedition_id}?token=<access_token>
```

Доступно тільки авторизованим користувачам які є chief або учасником експедиції.

**Події:**

| Подія | Коли |
|-------|------|
| `member_invited` | chief запросив учасника |
| `member_confirmed` | учасник підтвердив участь |
| `expedition_status` | змінився статус експедиції |

**Приклад події:**
```json
{"event": "expedition_status", "expedition_id": "uuid", "status": "active"}
```

**Тест в браузері (F12 → Console):**
```javascript
const ws = new WebSocket("ws://localhost:8000/ws/expeditions/EXPEDITION_ID?token=YOUR_TOKEN")
ws.onmessage = (e) => console.log(e.data)
ws.onopen = () => console.log("connected!")
```

---

## Життєвий цикл експедиції

```
draft → ready → active → finished
```

| Статус | Хто переводить | Умови |
|--------|---------------|-------|
| `draft` | автоматично при створенні | — |
| `ready` | chief | експедиція не active/finished |
| `active` | chief | start_at <= now(), confirmed >= 2, confirmed <= capacity, ніхто з confirmed не в іншій active експедиції |
| `finished` | chief | тільки з active |

---

## Правила запрошень

- Запрошувати можна лише користувачів з роллю `member`
- Не можна запросити одного учасника двічі
- Підтвердити може лише сам запрошений
- Перехід тільки `invited → confirmed`

---

## Структура проекту

```
expedition/
├── app/
│   ├── auth/           # авторизація, моделі юзерів
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── security.py
│   │   ├── dependencies.py
│   │   └── router.py
│   ├── expeditions/    # експедиції, бізнес-логіка
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── service.py
│   │   └── router.py
│   ├── ws/             # WebSocket
│   │   ├── manager.py
│   │   └── router.py
│   ├── config.py
│   ├── db.py
│   └── main.py
├── alembic/            # міграції
├── docker-compose.yml
├── Dockerfile
├── entrypoint.sh
├── requirements.txt
└── .env.example
```