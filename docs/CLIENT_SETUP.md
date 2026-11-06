# Создание клиентского репозитория

Эта инструкция описывает полный путь от нового GitHub-репозитория до опубликованного меню.

## 1. Создать пустой репозиторий клиента

На GitHub создайте новый репозиторий без README, `.gitignore` и License. Например, `menu-anna`.

## 2. Клонировать шаблон и подключить репозиторий клиента

```bash
git clone https://github.com/Wwwoper/template-menu.git menu-anna
cd menu-anna
git remote rename origin upstream
git remote add origin https://github.com/OWNER/menu-anna.git
```

Замените `OWNER/menu-anna` на владельца и имя созданного репозитория. `upstream` — основной шаблон, `origin` — репозиторий клиента. Проверьте настройки:

```bash
git remote -v
```

## 3. Подготовить Excel и создать клиента

Установите зависимости (нужны Python 3.11+ и [uv](https://github.com/astral-sh/uv)):

```bash
uv sync
```

Положите исходную книгу `.xlsx` в папку `input/` и запустите:

```bash
uv run tools/create_client.py
```

Следуйте подсказкам: выберите книгу, введите имя клиента точно как в заголовках Excel, проверьте сводку и подтвердите импорт.

Скрипт инициализирует приложение, создаст JSON-дни в `content/days/`, проверит данные и построит локальный индекс. После успешного импорта исходная книга будет перемещена в `input/archive/`.

**Важно:** `input/` целиком исключена из Git. Не переносите исходные таблицы в другие отслеживаемые каталоги и не добавляйте их в коммиты: они могут содержать персональные данные и учётные сведения.

Если требуется, короткое название приложения можно передать параметром:

```bash
uv run tools/create_client.py --short-name "Анна"
```

## 4. Проверить результат

```bash
uv run tools/validate.py
uv run pytest
node --test tests/js/*.test.mjs
git status --short
```

Проверьте название клиента и содержимое `content/days/`. Исходный XLSX и его архив не должны отображаться в `git status`.

`content/days.json` — генерируемый индекс, он исключён из Git. В репозитории хранятся исходные JSON-файлы из `content/days/`.

## 5. Сохранить и отправить клиентский проект

```bash
git add -A
git commit -m "chore: initialize client menu"
git push -u origin main
```

Если основная ветка шаблона называется не `main`, используйте соответствующее имя ветки.

## 6. Включить GitHub Pages

В репозитории клиента откройте **Settings → Pages → Build and deployment** и выберите **GitHub Actions** в поле Source.

После push в основную ветку workflow проверит данные, соберёт индекс, запустит тесты и опубликует сайт. Результат и адрес публикации можно проверить в **Actions** и **Settings → Pages**.

## 7. Получать обновления шаблона

Обновления приложения переносите из `upstream` в отдельной ветке. Не заменяйте клиентские JSON-файлы содержимым шаблона.

Подробная процедура описана в [TEMPLATE_UPDATES.md](TEMPLATE_UPDATES.md).
