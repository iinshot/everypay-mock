# EveryPay Mock

Mock-реализация Open Banking API с поддержкой OAuth2 Authorization Code Flow + PKCE. Проект предоставляет REST API для получения информации о счетах, банках и формирования выписок, а также собственный OAuth2-сервер для авторизации сторонних приложений.

## Возможности
- Получение списка счетов
- Получение информации по счёту
- Получение списка банков
- Создание запроса на выписку
- Получение информации по выписке

Поддерживается Authorization Code Flow с PKCE:
1. Получение Third Party Code
2. Авторизация пользователя
3. Выдача Authorization Code
4. Обмен Authorization Code на Access Token
5. Обновление Access Token через Refresh Token

## Технологии
- Python 3.12
- Django 6
- PostgreSQL 16
- Pydantic v2
- Django Modern REST
- OAuth2 + PKCE
- Docker
- Pytest

## Запуск
```bash
git clone https://github.com/iinshot/everypay-mock.git
cd everypay-mock
touch .env
docker compose up --build
docker exec -it everypay_web python manage.py migrate
docker exec -it everypay_web python manage.py createsuperuser
```

## OAuth Flow
### 1. Получение Third Party Code
```http
POST /oauth/third-party-code
```
Пример:
```json
{
  "client_id": "client",
  "client_secret": "secret",
  "user_id": "123"
}
```
### 2. Авторизация
```http
GET /oauth/authorize
```
Параметры:
```text
client_id
redirect_uri
code
third_party
```
### 3. Подтверждение доступа
После выбора банка и компании создаётся Authorization Code.
### 4. Получение токенов
```http
POST /oauth/token
```
Возвращает:
```json
{
  "access_token": "...",
  "refresh_token": "...",
  "expires_in": 3600
}
```
### 5. Обновление токена
```http
POST /oauth/token
```
с использованием refresh_token.
