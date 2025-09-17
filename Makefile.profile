# Makefile для профилирования AI Service Normalization Factory

.PHONY: profile profile-cprofile profile-pyinstrument profile-report clean-profile install-profile-deps

# Установка зависимостей для профилирования
install-profile-deps:
	@echo "Установка зависимостей для профилирования..."
	pip install pyinstrument
	@echo "Зависимости установлены"

# Полное профилирование (cProfile + pyinstrument + отчёт)
profile: profile-cprofile profile-pyinstrument profile-report
	@echo "Профилирование завершено. Результаты в artifacts/"

# Профилирование с cProfile
profile-cprofile:
	@echo "Запуск cProfile профилирования..."
	python scripts/profile_normalization.py 100
	@echo "cProfile профилирование завершено"

# Профилирование с pyinstrument
profile-pyinstrument:
	@echo "Запуск pyinstrument профилирования..."
	python scripts/profile_normalization_pyinstrument.py 20
	@echo "pyinstrument профилирование завершено"

# Генерация отчёта
profile-report:
	@echo "Генерация отчёта профилирования..."
	python scripts/generate_profile_report.py
	@echo "Отчёт сгенерирован: artifacts/profile_report.md"

# Быстрое профилирование (меньше итераций)
profile-quick: install-profile-deps
	@echo "Быстрое профилирование..."
	python scripts/profile_normalization.py 10
	python scripts/profile_normalization_pyinstrument.py 5
	python scripts/generate_profile_report.py
	@echo "Быстрое профилирование завершено"

# Профилирование с трассировкой памяти
profile-memory:
	@echo "Профилирование с трассировкой памяти..."
	PYTHONTRACEMALLOC=1 python scripts/profile_normalization.py 50
	@echo "Профилирование с памятью завершено"

# Очистка результатов профилирования
clean-profile:
	@echo "Очистка результатов профилирования..."
	rm -rf artifacts/
	@echo "Результаты профилирования очищены"

# Показать результаты профилирования
show-profile:
	@echo "Результаты профилирования:"
	@if [ -f "artifacts/profile_report.md" ]; then \
		echo "Отчёт: artifacts/profile_report.md"; \
		head -20 artifacts/profile_report.md; \
	else \
		echo "Отчёт не найден. Запустите 'make profile' сначала."; \
	fi
	@if [ -f "artifacts/profile.html" ]; then \
		echo "HTML отчёт: artifacts/profile.html"; \
	else \
		echo "HTML отчёт не найден."; \
	fi

# Помощь
help-profile:
	@echo "Доступные команды профилирования:"
	@echo "  profile              - Полное профилирование (cProfile + pyinstrument + отчёт)"
	@echo "  profile-cprofile     - Только cProfile профилирование"
	@echo "  profile-pyinstrument - Только pyinstrument профилирование"
	@echo "  profile-report       - Генерация отчёта из существующих данных"
	@echo "  profile-quick        - Быстрое профилирование (меньше итераций)"
	@echo "  profile-memory       - Профилирование с трассировкой памяти"
	@echo "  clean-profile        - Очистка результатов профилирования"
	@echo "  show-profile         - Показать результаты профилирования"
	@echo "  install-profile-deps - Установить зависимости для профилирования"
