# 🚛 Groozy — Платформа грузоперевозок

**Groozy** — современное веб-приложение для организации грузоперевозок, созданное на основе учебного отчёта. Платформа объединяет грузовладельцев и перевозчиков, обеспечивая безопасные сделки, управление заявками и документооборот.

---

## 📑 Содержание

- [Описание проекта](#-описание-проекта)
- [Стек технологий](#-стек-технологий)
- [Структура проекта](#-структура-проекта)
- [Установка и запуск](#-установка-и-запуск)
- [Android-приложение](#-android-приложение)
- [API документация](#-api-документация)
- [Безопасность](#-безопасность)
- [Оптимизация](#-оптимизация)

---

## 📋 Описание проекта

### Зачем это нужно (раздел 1.1)

Сервис решает главную проблему рынка грузоперевозок — **разброс и неудобство**: сегодня поиск транспорта происходит через разрозненные чаты, доски объявлений и звонки диспетчерам. Groozy — единое цифровое пространство для поиска перевозчиков, создания заявок и управления грузами.

### Отличие от аналогов (раздел 1.2)

| Платформа | Groozy | ATI.SU | Деловые Линии | Перевозка 24 |
|-----------|--------|--------|---------------|--------------|
| Целевая аудитория | Малый бизнес + частные лица | Крупные логисты | Только корпоративные | Срочный вывоз |
| Ценообразование | Гибкое (торг) | Рыночные ставки | Фиксированный тариф | Повышенный тариф |
| Интерфейс | Современный, минималистичный | Перегруженный | Стандартный | Мобильный |
| Межгород | ✅ Приоритет | ✅ | ✅ | ⚠️ Ограничено |

### Функциональность (раздел 1.3–1.5)

По IDEF0-модели система включает три основных блока:

- **Управление пользователями** — регистрация, авторизация, профили, роли (клиент / перевозчик / администратор)
- **Управление транспортом и маршрутами** — каталог перевозчиков, маршруты, параметры транспорта
- **Оформление и обработка заявок** — создание, поиск, взятие в работу, завершение, документы

---

## 🛠 Стек технологий

### Backend

| Технология | Версия | Назначение |
|-----------|--------|-----------|
| **Python** | 3.13 | Основной язык |
| **FastAPI** | 0.115+ | Веб-фреймворк, автодокументация OpenAPI |
| **Uvicorn** | 0.34+ | ASGI-сервер (высокая производительность) |
| **SQLAlchemy** | 2.0+ | ORM, асинхронная работа с БД |
| **Pydantic** | 2.11+ | Валидация данных, схемы |
| **python-jose** | 3.3+ | JWT токены |
| **passlib (pbkdf2_sha256)** | — | Хеширование паролей |
| **aiosqlite** | 0.21+ | Асинхронный SQLite (dev) |

**Почему FastAPI?** — автоматическая генерация OpenAPI/Swagger документации, нативная асинхронность, встроенная валидация через Pydantic, высокая производительность (сравнима с NodeJS и Go).

### Frontend

Чистый HTML5 + CSS3 + Vanilla JS (без фреймворков):
- Нет зависимостей сборки — открывается напрямую
- CSS Custom Properties для тематизации
- Intersection Observer API для анимаций
- Fetch API для работы с REST
- Responsive design (mobile-first)
- ARIA-атрибуты для доступности

### Android

- **Kotlin** 1.9+ / Android SDK 35
- `WebView` + `WebViewClient` + `WebChromeClient`
- `SwipeRefreshLayout` (pull-to-refresh)
- `OnBackPressedCallback` (навигация назад)
- Поддержка загрузки файлов через `FileChooserParams`

---

## 📁 Структура проекта

```
groozy/
│
├── backend/                    # Python/FastAPI сервер
│   ├── main.py                 # Точка входа, регистрация middleware и роутеров
│   ├── requirements.txt        # Зависимости Python 3.13
│   ├── .env.example            # Шаблон конфигурации
│   ├── alembic.ini             # Конфиг миграций БД
│   │
│   ├── app/
│   │   ├── core/
│   │   │   ├── config.py       # Настройки через .env (pydantic-settings)
│   │   │   ├── database.py     # Асинхронное подключение SQLAlchemy
│   │   │   └── security.py     # JWT, PBKDF2, Depends-авторизация
│   │   │
│   │   ├── middleware/
│   │   │   ├── security.py     # Заголовки безопасности (CSP, HSTS, X-Frame)
│   │   │   └── rate_limit.py   # Rate limiting (защита от DDoS/брутфорс)
│   │   │
│   │   ├── models/
│   │   │   ├── user.py         # Модель пользователя (роли: client/carrier/admin)
│   │   │   ├── order.py        # Модель заявки на перевозку
│   │   │   └── cargo.py        # Модель документов груза
│   │   │
│   │   └── routers/
│   │       ├── auth.py         # /api/auth — регистрация, вход, me
│   │       ├── users.py        # /api/users — профили, перевозчики
│   │       ├── orders.py       # /api/orders — CRUD заявок + пагинация
│   │       └── cargo.py        # /api/cargo — загрузка/скачивание документов
│   │
│   ├── static/
│   │   └── uploads/            # Загруженные файлы (создаётся автоматически)
│   │
│   └── templates/
│       └── index.html          # SPA — главная страница (Groozy UI)
│
└── android/                    # Android-приложение
    └── app/src/main/
        ├── java/com/groozy/app/
        │   └── MainActivity.kt # WebView + SwipeRefresh + BackButton
        └── res/
            └── layout/
                └── activity_main.xml
```

---

## 🚀 Установка и запуск

### Требования

- Python **3.13**
- pip 24+
- (опционально) Android Studio для сборки APK

---

### 1. Клонирование репозитория

```bash
git clone https://github.com/your-username/groozy.git
cd groozy/backend
```

---

### 2. Создание виртуального окружения

```bash
# Создать окружение
python3.13 -m venv .venv

# Активировать (Linux/macOS)
source .venv/bin/activate

# Активировать (Windows)
.venv\Scripts\activate
```

---

### 3. Установка зависимостей

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

### 4. Настройка окружения

```bash
# Скопировать шаблон
cp .env.example .env

# Открыть и настроить
nano .env  # или любой текстовый редактор
```

**Обязательно измените `SECRET_KEY`!** Сгенерируйте безопасный ключ:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

### 5. Запуск сервера

#### Режим разработки

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Флаги:
- `--reload` — автоперезапуск при изменении файлов
- `--host 0.0.0.0` — доступен с любого IP (в т.ч. с Android-устройства в сети)
- `--port 8000` — порт сервера

#### Режим продакшена

```bash
uvicorn main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4 \
    --log-level info \
    --access-log
```

Или через Python:

```bash
python main.py
```

---

### 6. Проверка работы

Откройте в браузере:

```
http://localhost:8000          → Главная страница Groozy
http://localhost:8000/api/docs → Swagger UI (интерактивная документация)
http://localhost:8000/api/redoc → ReDoc документация
```

---

### 7. Производственный деплой с Nginx (опционально)

```nginx
# /etc/nginx/sites-available/groozy
server {
    listen 80;
    server_name your-domain.com;

    # Gzip-сжатие
    gzip on;
    gzip_types text/plain application/json text/css application/javascript;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_cache_bypass $http_upgrade;
    }

    # Кэширование статики (оптимизация)
    location /static/ {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

---

### 8. Запуск как systemd-сервис (Linux)

```ini
# /etc/systemd/system/groozy.service
[Unit]
Description=Groozy FastAPI Application
After=network.target

[Service]
User=www-data
WorkingDirectory=/var/www/groozy/backend
Environment="PATH=/var/www/groozy/backend/.venv/bin"
ExecStart=/var/www/groozy/backend/.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable groozy
sudo systemctl start groozy
sudo systemctl status groozy
```

---

## 📱 Android-приложение

### Требования

- Android Studio Hedgehog (2023.1.1) или новее
- Android SDK 35
- Kotlin 1.9+
- Устройство/эмулятор с Android 8.0+ (minSdk 26)

### Настройка

1. Откройте папку `groozy/android` в Android Studio
2. В файле `MainActivity.kt` измените `BASE_URL`:

```kotlin
// Для локального сервера (эмулятор):
const val BASE_URL = "http://10.0.2.2:8000"

// Для реального устройства в локальной сети:
const val BASE_URL = "http://192.168.1.100:8000"  // IP вашего ПК

// Для продакшена:
const val BASE_URL = "https://your-domain.com"
```

3. Для работы с HTTP (не HTTPS) добавьте в `res/xml/network_security_config.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<network-security-config>
    <domain-config cleartextTrafficPermitted="true">
        <domain includeSubdomains="true">10.0.2.2</domain>
        <domain includeSubdomains="true">192.168.1.100</domain>
    </domain-config>
</network-security-config>
```

### Сборка и запуск

```bash
# Через Gradle (из папки android/)
./gradlew assembleDebug

# APK будет по пути:
# android/app/build/outputs/apk/debug/app-debug.apk
```

Или запустите через Android Studio: **Run → Run 'app'**

### Функции приложения

| Функция | Реализация |
|---------|-----------|
| Отображение веб-приложения | `WebView` с включённым JS |
| Обновление страницы | `SwipeRefreshLayout` (потянуть вниз) |
| Навигация «Назад» | `OnBackPressedCallback` → `webView.goBack()` |
| Загрузка файлов | `FileChooserParams` |
| Офлайн-страница | `assets/offline.html` при ошибке сети |
| Прогресс загрузки | `ProgressBar` (горизонтальный, вверху) |
| Внешние ссылки | Открываются в системном браузере |

---

## 📖 API документация

### Авторизация

```http
POST /api/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "username": "ivan_ivanov",
  "full_name": "Иван Иванов",
  "password": "SecurePass1",
  "role": "client"
}
```

```http
POST /api/auth/login
Content-Type: application/x-www-form-urlencoded

username=ivan_ivanov&password=SecurePass1
```

### Заявки (с пагинацией)

```http
GET /api/orders?page=1&per_page=12&cargo_type=fragile
Authorization: Bearer <token>
```

```http
POST /api/orders
Authorization: Bearer <token>
Content-Type: application/json

{
  "origin_city": "Москва",
  "origin_address": "ул. Ленина, 1",
  "destination_city": "Санкт-Петербург",
  "destination_address": "пр. Невский, 10",
  "cargo_name": "Офисная мебель",
  "cargo_type": "general",
  "weight_kg": 850,
  "budget": 18000
}
```

---

## 🔒 Безопасность (раздел 5)

Реализованные меры защиты:

### 1. Аутентификация и авторизация
- JWT-токены (access + refresh) на основе `python-jose`
- Хеширование паролей через **PBKDF2-SHA256** (`passlib`)
- Валидация сложности пароля (минимум 8 символов, заглавная буква, цифра)

### 2. Защита от CSRF
- Для SPA с JWT в Authorization header CSRF-атаки невозможны по умолчанию
- Все мутирующие запросы требуют токена

### 3. Защита от XSS
- Заголовок `Content-Security-Policy` (CSP) через `SecurityHeadersMiddleware`
- `X-XSS-Protection: 1; mode=block`
- Экранирование данных на стороне JS через `escHtml()`

### 4. Защита от Clickjacking
- Заголовок `X-Frame-Options: DENY`

### 5. Защита от SQL-инъекций
- SQLAlchemy ORM с параметризованными запросами
- Никакого сырого SQL с пользовательскими данными

### 6. Rate Limiting
- Общий лимит: 100 запросов / 60 сек с одного IP
- Строгий лимит для `/api/auth/`: 10 запросов / 60 сек (защита от брутфорса)

### 7. Безопасность файлов
- Валидация расширений (`jpg, jpeg, png, webp, pdf`)
- Ограничение размера файла (10 МБ по умолчанию)
- Сохранение файлов с UUID-именами (предотвращение path traversal)

### 8. HTTPS и HSTS
- Заголовок `Strict-Transport-Security` для принудительного HTTPS
- Конфигурация `.env` хранит секреты отдельно от кода

---

## ⚡ Оптимизация (раздел 4)

### База данных

- **Нормализация** — данные разбиты на логически связанные таблицы (`users`, `orders`, `cargo_documents`) с внешними ключами
- **Индексы** — на полях поиска: `email`, `username`, `status`, `client_id`, `carrier_id`
- **Lazy loading** через SQLAlchemy 2.0 async
- **Avoid N+1** — использование `selectinload` для связанных данных

### Пагинация

Вместо загрузки всех записей сразу применяется **пагинация** (аналог `paginate()` в Laravel):

```python
# Только нужная страница — не вся БД
query.order_by(Order.created_at.desc()).offset(offset).limit(per_page)
```

Преимущества:
- Сервер отдаёт ≤12 записей вместо тысяч
- Уменьшение нагрузки на БД и сеть
- Быстрее отрисовка страницы

### Сжатие

- **GZip middleware** FastAPI — сжатие ответов от 1000 байт
- Статические файлы кэшируются Nginx (30 дней)

### Сервер

- **Асинхронная архитектура** FastAPI + Uvicorn — обработка тысяч запросов без блокировки
- **Несколько воркеров** (`--workers 4`) для использования всех ядер CPU
- **`.env`-конфигурация** — разные настройки для dev и prod без изменения кода

---

## 🧪 Тестирование

```bash
# Запуск тестов
pytest

# С отчётом покрытия
pytest --cov=app --cov-report=html
```

Реализованные тест-кейсы (раздел 3.4):
1. Регистрация пользователя
2. Авторизация пользователя
3. Создание заявки
4. Изменение заявки
5. Удаление заявки
6. Поиск в каталоге
7. Выход из аккаунта

---

## 📝 Лицензия

MIT License. Проект создан в учебных целях на основе студенческого отчёта.
