#!/usr/bin/env python3

"""
Детальная трассировка для поиска источника metrics ошибки.
"""

import sys
import traceback
import linecache
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

class MetricsErrorTracer:
    """Класс для детальной трассировки metrics ошибки."""

    def __init__(self):
        self.original_getattr = object.__getattribute__
        self.metrics_accesses = []

    def trace_metrics_access(self, obj, name):
        """Перехватывает все обращения к metrics."""
        if name == 'metrics':
            import inspect
            frame = inspect.currentframe()
            if frame and frame.f_back:
                caller_frame = frame.f_back
                filename = caller_frame.f_filename
                line_number = caller_frame.f_lineno
                function_name = caller_frame.f_code.co_name
                line_content = linecache.getline(filename, line_number).strip()

                self.metrics_accesses.append({
                    'file': filename,
                    'line': line_number,
                    'function': function_name,
                    'code': line_content,
                    'locals': dict(caller_frame.f_locals.keys()) if caller_frame.f_locals else {}
                })

                print(f"🔍 METRICS ACCESS: {filename}:{line_number} in {function_name}")
                print(f"   Code: {line_content}")

                # Проверяем, есть ли metrics в локальных переменных
                if 'metrics' not in caller_frame.f_locals:
                    print(f"❌ METRICS NOT IN LOCALS: {list(caller_frame.f_locals.keys())}")
                else:
                    print(f"✅ METRICS FOUND: {type(caller_frame.f_locals['metrics'])}")

        return self.original_getattr(obj, name)

def test_with_tracing():
    """Тест с детальной трассировкой."""
    print("🔍 ДЕТАЛЬНАЯ ТРАССИРОВКА METRICS ERROR")
    print("=" * 60)

    tracer = MetricsErrorTracer()

    try:
        # Импортируем и тестируем нормализацию
        from ai_service.layers.normalization.normalization_service import NormalizationService

        print("✅ NormalizationService импортирован")

        service = NormalizationService()
        print("✅ NormalizationService создан")

        # Тестируем простую нормализацию
        test_text = "Іванов Іван Іванович"
        print(f"🧪 Тестируем нормализацию: '{test_text}'")

        # Перехватываем ошибку с детальной информацией
        try:
            result = service.normalize(
                text=test_text,
                language="uk",
                remove_stop_words=True,
                preserve_names=True,
                enable_advanced_features=False
            )

            print("📋 Нормализация завершена:")
            print(f"   Success: {result.success}")
            print(f"   Errors: {result.errors}")

            # Проверяем на metrics ошибки
            if result.errors:
                for error in result.errors:
                    if "metrics" in str(error).lower() and "not defined" in str(error).lower():
                        print(f"❌ НАЙДЕНА METRICS ОШИБКА: {error}")
                        return False

            print("✅ Нет metrics ошибок!")
            return True

        except NameError as e:
            if "metrics" in str(e):
                print(f"❌ ПОЙМАНА METRICS NAMEERROR: {e}")

                # Детальная трассировка
                tb = traceback.extract_tb(sys.exc_info()[2])
                print("\n📍 ДЕТАЛЬНАЯ ТРАССИРОВКА:")
                print("-" * 50)

                for i, frame in enumerate(tb):
                    print(f"  {i+1}. {frame.filename}:{frame.lineno}")
                    print(f"     Функция: {frame.name}")
                    print(f"     Код: {frame.line}")

                    # Если это строка с metrics
                    if frame.line and "metrics" in frame.line:
                        print(f"     ⚠️ ПРОБЛЕМНАЯ СТРОКА!")

                        # Читаем контекст вокруг проблемной строки
                        print(f"     📄 КОНТЕКСТ (строки {frame.lineno-3} - {frame.lineno+3}):")
                        for line_num in range(max(1, frame.lineno-3), frame.lineno+4):
                            line_content = linecache.getline(frame.filename, line_num).rstrip()
                            marker = " >>> " if line_num == frame.lineno else "     "
                            print(f"     {marker}{line_num:4d}: {line_content}")
                    print()

                print("-" * 50)
                return False
            else:
                print(f"ℹ️ Другая ошибка: {e}")
                return True

        except Exception as e:
            print(f"❌ Общая ошибка: {e}")

            if "metrics" in str(e).lower():
                print("🎯 Это metrics-связанная ошибка!")
                traceback.print_exc()
                return False
            return True

    except Exception as setup_error:
        print(f"❌ Ошибка настройки: {setup_error}")
        return False

def analyze_all_metrics_files():
    """Анализирует все файлы, которые используют metrics."""
    print("\n🔍 АНАЛИЗ ВСЕХ METRICS-ФАЙЛОВ")
    print("=" * 50)

    metrics_files = [
        "/Users/dariapavlova/Desktop/ai-service/src/ai_service/core/unified_orchestrator.py",
        "/Users/dariapavlova/Desktop/ai-service/src/ai_service/layers/signals/signals_service.py",
        "/Users/dariapavlova/Desktop/ai-service/src/ai_service/layers/normalization/processors/result_builder.py"
    ]

    for file_path in metrics_files:
        print(f"\n📄 АНАЛИЗ: {file_path.split('/')[-1]}")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            for i, line in enumerate(lines, 1):
                if 'metrics.' in line and 'if metrics' not in line and 'def ' not in line:
                    # Проверяем контекст - есть ли проверка на None рядом
                    context_start = max(0, i-5)
                    context_end = min(len(lines), i+2)
                    context = lines[context_start:context_end]

                    has_null_check = any('if metrics' in ctx_line for ctx_line in context)

                    status = "✅" if has_null_check else "❌"
                    print(f"   {status} Строка {i:4d}: {line.strip()}")

                    if not has_null_check:
                        print(f"        ⚠️ НЕТ ПРОВЕРКИ НА None!")
                        print(f"        📄 КОНТЕКСТ:")
                        for j, ctx_line in enumerate(context):
                            line_num = context_start + j + 1
                            marker = " >>> " if line_num == i else "     "
                            print(f"        {marker}{line_num:4d}: {ctx_line.rstrip()}")

        except Exception as e:
            print(f"   ❌ Ошибка чтения файла: {e}")

def main():
    """Главная функция."""
    print("🎯 КОМПЛЕКСНАЯ ДИАГНОСТИКА METRICS ERROR")
    print("=" * 70)

    # Тест 1: Трассировка выполнения
    success = test_with_tracing()

    # Тест 2: Статический анализ файлов
    analyze_all_metrics_files()

    print("\n" + "=" * 70)
    if success:
        print("🎉 РЕЗУЛЬТАТ: Нет metrics ошибок в тестах")
        print("   Возможные причины продолжающейся ошибки:")
        print("   - Сервис не перезапущен")
        print("   - Используется кэшированный код")
        print("   - Ошибка в другом месте")
    else:
        print("❌ РЕЗУЛЬТАТ: Найдена metrics ошибка")
        print("   Проверьте детальную трассировку выше")

    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)