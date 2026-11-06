# Обновление клиентского репозитория из шаблона

Клиентский репозиторий хранит собственные данные (`content/days/*.json` и настройки клиента), а `upstream` указывает на общий шаблон `Wwwoper/template-menu`.

## Первоначальная настройка remote

В клиентском репозитории `origin` должен указывать на репозиторий клиента,
а `upstream` — на общий шаблон. Проверьте URL:

```bash
git remote -v
```

Если `upstream` ещё не настроен, добавьте его:

```bash
git remote add upstream https://github.com/Wwwoper/template-menu.git
```

Зафиксируйте безопасное направление push по умолчанию:

```bash
git config --local remote.pushDefault origin
git config --local push.default simple
git config --get remote.pushDefault
```

Последняя команда должна вывести `origin`. Не используйте `git remote rename origin upstream`:
при таком переименовании Git может переключить upstream локальной ветки на шаблон.
Если `origin` указывает не на клиентский репозиторий, исправьте URL до продолжения.

## Получение обновления

Перед началом убедитесь, что рабочее дерево чистое и изменения клиента закоммичены:

```bash
git status --short
git switch main
git pull --ff-only origin main
git fetch upstream
```

Создайте отдельную ветку и объедините изменения шаблона:

```bash
git switch -c update/template
git merge upstream/main
```

Если возникли конфликты, разрешите их вручную. Особенно внимательно проверяйте файлы клиентских настроек и `content/days/*.json`: сохраняйте данные клиента, если изменение этих данных не является частью отдельной осознанной задачи.

После объединения проверьте проект:

```bash
uv sync
uv run tools/validate.py
uv run pytest
node --test tests/js/*.test.mjs
```

Если изменялись файлы интерфейса или Service Worker, проверьте сайт локально и убедитесь, что версия кэша в `service-worker.js` соответствует правилам проекта.

Отправьте ветку и откройте Pull Request в клиентском репозитории:

```bash
git push -u origin update/template
```

В GitHub создайте Pull Request из `update/template` в `main`. После проверки объедините его. GitHub Actions выполнит проверки; публикация произойдёт после попадания изменений в основную ветку.

## Важные правила

- Не выполняйте `git push` в `upstream`: это общий репозиторий шаблона.
- Не заменяйте клиентский `content/days/` файлами из шаблона.
- Не перезаписывайте `CLIENT_TEMPLATE_VERSION`: он фиксирует первоначальную версию шаблона, из которой был создан клиент.
- `TEMPLATE_VERSION` в шаблоне — версия текущего релиза. Она не заменяет `CLIENT_TEMPLATE_VERSION` в клиенте.
- `content/days.json` генерируется при сборке и не должен добавляться в Git.
- Не переносите локальные XLSX из `input/` в коммиты или публичные артефакты.
