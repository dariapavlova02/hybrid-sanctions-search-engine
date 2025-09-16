#!/usr/bin/env python3
"""
Демонстрационный скрипт для запуска тестов поисковой интеграции.
"""

import subprocess
import sys
import time
from pathlib import Path


def run_command(cmd, description):
    """Запустить команду и показать результат."""
    print(f"\n{'='*60}")
    print(f"🚀 {description}")
    print(f"{'='*60}")
    print(f"Команда: {cmd}")
    print()
    
    start_time = time.time()
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        end_time = time.time()
        
        print(f"⏱️  Время выполнения: {end_time - start_time:.2f}с")
        print(f"📊 Код возврата: {result.returncode}")
        
        if result.stdout:
            print(f"\n📤 STDOUT:")
            print(result.stdout)
        
        if result.stderr:
            print(f"\n❌ STDERR:")
            print(result.stderr)
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ Ошибка выполнения: {e}")
        return False


def main():
    """Главная функция демонстрации."""
    print("🎯 Демонстрация тестов поисковой интеграции")
    print("=" * 60)
    
    # Проверяем, что мы в правильной директории
    if not Path("tests").exists():
        print("❌ Ошибка: Запустите скрипт из корня проекта ai-service")
        sys.exit(1)
    
    # Проверяем наличие pytest
    if not run_command("pytest --version", "Проверка pytest"):
        print("❌ pytest не установлен. Установите: pip install pytest")
        sys.exit(1)
    
    # 1. Unit тесты
    print("\n" + "="*60)
    print("📋 1. UNIT ТЕСТЫ")
    print("="*60)
    
    unit_tests = [
        "tests/unit/test_search_contracts.py",
        "tests/unit/test_search_integration.py", 
        "tests/unit/test_decision_engine_with_search.py"
    ]
    
    for test_file in unit_tests:
        if Path(test_file).exists():
            success = run_command(
                f"pytest {test_file} -v --tb=short",
                f"Запуск {test_file}"
            )
            if not success:
                print(f"❌ Тест {test_file} не прошел")
        else:
            print(f"⚠️  Файл {test_file} не найден")
    
    # 2. Проверка Docker
    print("\n" + "="*60)
    print("🐳 2. ПРОВЕРКА DOCKER")
    print("="*60)
    
    docker_available = run_command("docker --version", "Проверка Docker")
    if not docker_available:
        print("⚠️  Docker не доступен. Integration тесты будут пропущены.")
    else:
        # Проверяем, запущен ли Elasticsearch
        es_running = run_command(
            "curl -f http://localhost:9200/_cluster/health",
            "Проверка Elasticsearch"
        )
        
        if not es_running:
            print("⚠️  Elasticsearch не запущен. Запустите:")
            print("   docker-compose -f docker-compose.test.yml up -d")
        else:
            # 3. Integration тесты
            print("\n" + "="*60)
            print("🔗 3. INTEGRATION ТЕСТЫ")
            print("="*60)
            
            integration_tests = [
                "tests/integration/test_elasticsearch_search.py"
            ]
            
            for test_file in integration_tests:
                if Path(test_file).exists():
                    success = run_command(
                        f"pytest {test_file} -v --tb=short",
                        f"Запуск {test_file}"
                    )
                    if not success:
                        print(f"❌ Тест {test_file} не прошел")
                else:
                    print(f"⚠️  Файл {test_file} не найден")
    
    # 4. Performance тесты (только если Docker доступен)
    if docker_available and es_running:
        print("\n" + "="*60)
        print("⚡ 4. PERFORMANCE ТЕСТЫ")
        print("="*60)
        
        performance_tests = [
            "tests/performance/test_search_performance.py"
        ]
        
        for test_file in performance_tests:
            if Path(test_file).exists():
                success = run_command(
                    f"pytest {test_file} -v --tb=short",
                    f"Запуск {test_file}"
                )
                if not success:
                    print(f"❌ Тест {test_file} не прошел")
            else:
                print(f"⚠️  Файл {test_file} не найден")
    
    # 5. Итоговый отчет
    print("\n" + "="*60)
    print("📊 ИТОГОВЫЙ ОТЧЕТ")
    print("="*60)
    
    print("✅ Unit тесты: Проверены")
    if docker_available:
        print("✅ Docker: Доступен")
        if es_running:
            print("✅ Elasticsearch: Запущен")
            print("✅ Integration тесты: Доступны")
            print("✅ Performance тесты: Доступны")
        else:
            print("⚠️  Elasticsearch: Не запущен")
            print("⚠️  Integration тесты: Недоступны")
            print("⚠️  Performance тесты: Недоступны")
    else:
        print("⚠️  Docker: Не доступен")
        print("⚠️  Integration тесты: Недоступны")
        print("⚠️  Performance тесты: Недоступны")
    
    print("\n🎉 Демонстрация завершена!")
    print("\nДля полного запуска всех тестов используйте:")
    print("  make -f Makefile.test test-with-docker")


if __name__ == "__main__":
    main()
