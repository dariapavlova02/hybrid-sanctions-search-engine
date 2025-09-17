# QA Parity Checklist

Этот документ описывает запуск и анализ инструмента `parity_check`, который сравнивает legacy и factory пайплайны нормализации.

## Локальный запуск

1. Убедитесь, что виртуальное окружение активировано и зависимости установлены.
2. Выполните команду:
   ```bash
   PYTHONPATH=src python tools/parity_check.py --input tests/fixtures/parity_golden.jsonl
   ```
3. Артефакты будут сохранены в каталоге `artifacts/parity/`:
   - `parity_diff.csv` — список кейсов и статус паритета
   - `report.html` — подробный HTML-отчёт с трассами и метриками
   - `metrics.json` — агрегированные метрики (parity%, p50/p95/p99)

Для больших наборов данных используйте параметры `--batch-size` и `--workers`, например:
```bash
PYTHONPATH=src python tools/parity_check.py --input reports/normalization_comparison.json --batch-size 16 --workers 4
```

## Запуск в CI

### GitHub Actions

- Workflow `parity.yml` запускается на каждом push и pull request, поднимает Python 3.11, запускает `tools/parity_check.py` на `tests/fixtures/parity_golden.jsonl`.
- Job завершится с ошибкой, если `parity_percent < 70` или `factory`-p95 превышает 20 мс; основные метрики выводятся в лог.
- HTML/CSV/JSON артефакты публикуются как `parity-report` (retention 7 дней).

### Ручная интеграция или другой CI

- Выполните `python tools/parity_check.py --input <path>`.
- Сохраните `artifacts/parity/` как build-артефакт.
- Для smoke-проверки используйте:
  ```bash
  PYTHONPATH=src pytest tests/parity/test_parity_smoke.py -q
  ```

## Анализ результатов

- Ключевой показатель — `parity_percent` (ожидаемое значение ≥90% для релиза).
- Следите за `delta_p95_ms` в `metrics.json`, чтобы заводить задачи на оптимизацию.
- Топ-5 расхождений доступны в `report.html` (collapsible блоки) и `metrics.json`.
- Для расследования конкретного кейса используйте `diff_tokens` и `trace_deltas` из JSON-метрик.
