# RottenTomatoes Scraper Pipeline

## Описание
Проект собирает карточки фильмов с RottenTomatoes (динамическая подгрузка), делает очистку данных и сохраняет в SQLite.

## Структура
- `src/scraper.py` — сбор данных (Selenium) -> `data/raw.json`
- `src/cleaner.py` — очистка -> `data/cleaned.json`
- `src/loader.py` — сохраняет в SQLite `data/output.db`
- `airflow_dag.py` — шаблон DAG: scrape -> clean -> load

## Установка
1. Создай виртуальное окружение:
   ```bash
   python -m venv venv
   source venv/bin/activate   # linux / mac
   venv\Scripts\activate      # windows
