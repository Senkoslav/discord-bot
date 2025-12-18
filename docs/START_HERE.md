# 🎵 Начни здесь!

## 👋 Привет!

Это полнофункциональный музыкальный бот для Discord. Вот что тебе нужно знать:

---

## ⚡ Быстрый старт (выбери свой путь)

### 🚀 Хочу запустить ПРЯМО СЕЙЧАС (5 минут)
👉 Читай: **[QUICK_START.ru.md](QUICK_START.ru.md)**

### 📖 Хочу подробную инструкцию
👉 Читай: **[SETUP_GUIDE.ru.md](SETUP_GUIDE.ru.md)**

### 📋 Нужна шпаргалка по командам
👉 Читай: **[CHEATSHEET.ru.md](CHEATSHEET.ru.md)**

### 📖 Хочу примеры использования
👉 Читай: **[EXAMPLES.ru.md](EXAMPLES.ru.md)**

### ❓ У меня вопросы
👉 Читай: **[FAQ.ru.md](FAQ.ru.md)**

### 📚 Хочу всю документацию
👉 Читай: **[README_RU.md](README_RU.md)**

---

## 🎯 Что нужно для запуска?

### Обязательно:
1. ✅ **Docker** (скачай с docker.com)
2. ✅ **Discord Bot Token** (получи на discord.com/developers)
3. ✅ **Твой Discord ID** (включи режим разработчика в Discord)

### Опционально:
- Redis (для больших ботов)
- VPS/VDS (для 24/7 работы)

---

## 📝 Минимальная настройка

### 1. Создай файл .env
```bash
cp .env.example .env
```

### 2. Заполни .env
```env
DISCORD_TOKEN=твой_токен_здесь
BOT_OWNER_ID=твой_id_здесь
USE_REDIS=false
```

### 3. Запусти
```bash
docker compose up --build
```

**Готово!** Бот запущен.

---

## 🎵 Первые команды

После запуска попробуй в Discord:

```
/ping                              # Проверить бота
/help                              # Список команд
/play never gonna give you up      # Включить музыку
/queue                             # Посмотреть очередь
```

---

## ❓ Где найти токены?

### DISCORD_TOKEN
1. Открой: https://discord.com/developers/applications
2. New Application → Bot → Reset Token → Copy

### BOT_OWNER_ID
1. Discord → Настройки → Расширенные → Режим разработчика ВКЛ
2. Правой кнопкой на себя → Копировать ID

**Подробнее**: [FAQ.ru.md](FAQ.ru.md)

---

## 🔧 Что такое Redis и нужен ли он?

**Redis** — быстрая база данных.

- ❌ **НЕ нужен** для 1-10 серверов (используй SQLite)
- ✅ **Нужен** для 50+ серверов

**По умолчанию используется SQLite** — ничего настраивать не нужно!

---

## 📊 Структура проекта

```
music-bot/
├── 📄 START_HERE.md          ← ТЫ ЗДЕСЬ
├── 📄 QUICK_START.ru.md      ← Быстрый старт
├── 📄 SETUP_GUIDE.ru.md      ← Подробная инструкция
├── 📄 CHEATSHEET.ru.md       ← Шпаргалка
├── 📄 EXAMPLES.ru.md         ← Примеры
├── 📄 FAQ.ru.md              ← Вопросы и ответы
├── 📄 README_RU.md           ← Полная документация
├── 📄 .env.example           ← Шаблон конфигурации
├── 📄 docker-compose.yml     ← Docker настройки
└── 📁 bot/                   ← Код бота
```

---

## 🎓 Рекомендуемый порядок чтения

### Для новичков:
1. **START_HERE.md** (ты здесь) ✅
2. **QUICK_START.ru.md** — запусти бота
3. **EXAMPLES.ru.md** — научись пользоваться
4. **FAQ.ru.md** — если что-то не работает

### Для опытных:
1. **SETUP_GUIDE.ru.md** — детальная настройка
2. **README_RU.md** — полная документация
3. **CHEATSHEET.ru.md** — держи под рукой

---

## 🆘 Что-то не работает?

### Бот не запускается
```bash
docker --version          # Проверь Docker
cat .env                  # Проверь конфигурацию
docker compose logs bot   # Посмотри ошибки
```

### Бот не отвечает
- Подожди 1-2 минуты после запуска
- Используй `/sync` для синхронизации команд
- Перезапусти: `docker compose restart`

### Нужна помощь
👉 Читай: **[FAQ.ru.md](FAQ.ru.md)**

---

## 💡 Полезные команды Docker

```bash
# Запустить
docker compose up --build

# Запустить в фоне
docker compose up -d

# Остановить
docker compose down

# Перезапустить
docker compose restart

# Посмотреть логи
docker compose logs -f bot
```

---

## 🎉 Готов начать?

### Выбери свой путь:

**🚀 Быстро (5 минут)**
```bash
cd music-bot
cp .env.example .env
nano .env  # Добавь DISCORD_TOKEN и BOT_OWNER_ID
docker compose up --build
```

**📖 Подробно (10 минут)**
Читай: [SETUP_GUIDE.ru.md](SETUP_GUIDE.ru.md)

---

## 📞 Поддержка

- 📖 [Примеры использования](EXAMPLES.ru.md)
- ❓ [Часто задаваемые вопросы](FAQ.ru.md)
- 📋 [Шпаргалка по командам](CHEATSHEET.ru.md)
- 📚 [Полная документация](README_RU.md)

---

**Удачи! 🎵**

**Следующий шаг** → [QUICK_START.ru.md](QUICK_START.ru.md)
