# Marketplace — Платформа услуг с эскроу-системой

## Описание проекта

Маркетплейс для заказа услуг с безопасными расчётами на основе эскроу-механизма. Заказчик (customer) размещает заказ — средства блокируются в изолированном счёте и не переходят исполнителю до тех пор, пока заказчик не подтвердит выполнение. Если возникает спор — средства остаются заморожены до ручного разрешения.

Все платёжные операции фиксируются в **блокчейн-подобном логе** (цепочка SHA-256 хэшей): каждая транзакция содержит хэш предыдущей, что делает историю операций доступной для независимой проверки. Любой участник может запросить `GET /chain/verify` и убедиться, что записи не изменялись.

Система состоит из двух сервисов: **Python FastAPI** — управление пользователями и заказами, **Go** — платёжный микросервис и блокчейн-лог. Оба запускаются через Docker Compose.

---

## Технологический стек

| Компонент        | Технология                                        |
|------------------|---------------------------------------------------|
| API-бэкенд       | Python 3.12, FastAPI, SQLAlchemy, Alembic         |
| Платёжный сервис | Go 1.23, net/http, pgx/v5                        |
| Блокчейн-лог     | Go, crypto/sha256, PostgreSQL 16 (persistence)   |
| База данных      | PostgreSQL 16                                     |
| Фронтенд         | HTML + ES6, nginx:alpine (port 3000)              |
| Контейнеризация  | Docker, Docker Compose                            |
| Тесты Python     | pytest, pytest-asyncio                            |
| Тесты Go         | go test                                           |
| Линтер Python    | ruff                                              |
| Линтер Go        | gofmt, golangci-lint                              |
| SAST             | bandit (Python), gosec (Go)                       |
| SCA              | pip-audit (Python), govulncheck (Go)              |
| CI/CD            | GitHub Actions                                    |

---

## Структура проекта

```
marketplace/
├── backend/                  # Python FastAPI
│   ├── app/
│   │   ├── api/              # роутеры (auth, services, orders, balance)
│   │   ├── models/           # SQLAlchemy ORM модели
│   │   ├── schemas/          # Pydantic v2 схемы
│   │   ├── services/         # бизнес-логика + payment_client
│   │   ├── core/             # JWT, конфиг, зависимости, rate_limit
│   │   └── main.py
│   ├── tests/                # pytest тесты (14 тестов)
│   ├── alembic/              # миграции БД
│   └── Dockerfile
├── payment/                  # Go микросервис
│   ├── cmd/server/main.go
│   ├── internal/
│   │   ├── chain/            # SHA-256 блокчейн-лог
│   │   ├── db/               # PostgreSQL схема и подключение
│   │   ├── escrow/           # эскроу: lock, release, refund
│   │   └── handlers/         # HTTP-обработчики
│   └── docs/swagger.yaml
├── frontend/                 # HTML + ES6, nginx:alpine
├── infra/docker-compose.yml
├── docs/                     # Архитектурная документация
├── .github/workflows/ci.yml
├── Makefile
└── .env.example
```

---

## Быстрый старт

```bash
git clone <repo-url>
cd marketplace
cp .env.example .env
make up
```

| Сервис           | URL                          |
|------------------|------------------------------|
| Фронтенд         | http://localhost:3000        |
| Swagger UI (Python) | http://localhost:8000/docs |
| ReDoc (Python)   | http://localhost:8000/redoc  |
| Swagger UI (Go)  | http://localhost:8001        |
| Блокчейн-лог     | http://localhost:8001/chain  |

---

## Примеры curl-запросов

### Регистрация

```bash
curl -X POST http://localhost:8000/register \
  -H "Content-Type: application/json" \
  -d '{"email":"customer@example.com","password":"secret123","role":"customer"}'

curl -X POST http://localhost:8000/register \
  -H "Content-Type: application/json" \
  -d '{"email":"executor@example.com","password":"secret123","role":"executor"}'
```

### Логин

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/login \
  -H "Content-Type: application/json" \
  -d '{"email":"customer@example.com","password":"secret123"}' | jq -r .access_token)
```

### Пополнение баланса

```bash
curl -X POST http://localhost:8000/balance/topup \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"amount":500}'
```

### Создание услуги (executor)

```bash
EXEC_TOKEN=$(curl -s -X POST http://localhost:8000/login \
  -H "Content-Type: application/json" \
  -d '{"email":"executor@example.com","password":"secret123"}' | jq -r .access_token)

SERVICE_ID=$(curl -s -X POST http://localhost:8000/services \
  -H "Authorization: Bearer $EXEC_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"Web Development","description":"I build websites","price":200}' | jq -r .id)
```

### Создание заказа (средства блокируются в эскроу)

```bash
ORDER_ID=$(curl -s -X POST http://localhost:8000/orders \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"service_id\":\"$SERVICE_ID\"}" | jq -r .id)
```

### Принятие и завершение заказа

```bash
# Executor принимает
curl -X POST http://localhost:8000/orders/$ORDER_ID/accept \
  -H "Authorization: Bearer $EXEC_TOKEN"

# Customer подтверждает выполнение → средства переходят executor
curl -X POST http://localhost:8000/orders/$ORDER_ID/complete \
  -H "Authorization: Bearer $TOKEN"
```

### Просмотр блокчейн-лога

```bash
curl http://localhost:8001/chain
```

Пример вывода:

```json
[
  {
    "id": "a1b2c3d4-...",
    "timestamp": "2026-06-05T10:00:00Z",
    "from": "cust-uuid",
    "to": "escrow:esc-uuid",
    "amount": 200,
    "prev_hash": "0000000000000000",
    "hash": "7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069",
    "description": "lock"
  },
  {
    "id": "e5f6a7b8-...",
    "timestamp": "2026-06-05T10:05:12Z",
    "from": "escrow:esc-uuid",
    "to": "exec-uuid",
    "amount": 200,
    "prev_hash": "7f83b1657ff1fc53...",
    "hash": "c0535e4be2b79ffd93291305436bf889314e4a3faec05ecffcbb7df31ad9e51a",
    "description": "release"
  }
]
```

**Как проверить свою транзакцию:** найдите запись с вашим `order_id` в блокчейн-логе. Пересчитайте хэш самостоятельно: `SHA256(id + timestamp + from + to + amount + prev_hash)` и сравните с полем `hash`. Запустите `GET /chain/verify` для проверки всей цепочки.

---

## Тестирование

```bash
make test
```

**Python (pytest) — 14 тестов:**
- Регистрация пользователя / дубликат email (409)
- Логин с верными / неверными данными
- GET /me с токеном
- Обновление access-токена через refresh
- Executor создаёт услугу / Customer получает 403
- Полный флоу: create order → accept → complete
- Создание заказа с нулевым балансом → 402
- Открытие спора
- Отмена pending-заказа
- История заказов

**Go (go test) — 10 тестов:**
- Детерминированность ComputeHash (SHA-256)
- Проверка целостности валидной цепочки
- Обнаружение повреждённой записи в цепочке
- Проверка genesis-хэша первой транзакции
- Проверка связки PrevHash → Hash
- Lock: успешная блокировка средств
- Lock: недостаточно средств → ErrInsufficientFunds
- Release: перевод средств executor
- Refund: возврат средств customer
- Release несуществующего escrow → ErrNotFound

---

## CI/CD

GitHub Actions (`.github/workflows/ci.yml`) запускается при push в `main` и `develop`:

| Job               | Инструмент       | Описание                          |
|-------------------|------------------|-----------------------------------|
| python-lint       | ruff             | Стиль кода PEP8                   |
| python-sast       | bandit           | Статический анализ безопасности   |
| python-sca        | pip-audit        | Проверка зависимостей на CVE      |
| python-tests      | pytest           | Функциональные тесты              |
| go-lint           | gofmt            | Форматирование Go-кода            |
| go-sast           | gosec            | Анализ безопасности Go            |
| go-sca            | govulncheck      | Проверка Go-зависимостей на CVE   |
| go-tests          | go test          | Юнит-тесты Go                     |

---

## Безопасность

- Пароли хранятся только в виде bcrypt-хэша
- Секреты передаются через переменные окружения (`.env` в `.gitignore`)
- JWT-токены хранятся только в памяти клиента (Bearer header)
- Все входные данные валидируются Pydantic (Python) и явной проверкой (Go)
- Rate limiting: 20 запросов / 60 секунд на IP для эндпоинтов `/register` и `/login`
- SAST и SCA запускаются в каждом CI-пайплайне
- Эндпоинт `POST /chain/tamper` доступен только при `DEMO_MODE=true`
