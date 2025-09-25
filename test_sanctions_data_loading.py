#!/usr/bin/env python3

"""
Тест загрузки sanctions data для выяснения почему в продакшене
только 26 записей вместо полного датасета.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def test_sanctions_data_loading():
    """Тест загрузки sanctions data."""
    print("🔍 ТЕСТ ЗАГРУЗКИ SANCTIONS DATA")
    print("=" * 60)

    try:
        from ai_service.layers.search.sanctions_data_loader import SanctionsDataLoader

        # Создаем loader
        loader = SanctionsDataLoader()
        print(f"✅ SanctionsDataLoader создан")

        # Проверяем путь
        print(f"📂 Data directory: {loader.data_dir}")
        print(f"📂 Directory exists: {loader.data_dir.exists()}")

        if loader.data_dir.exists():
            files = list(loader.data_dir.glob("*.json"))
            print(f"📄 Files found: {len(files)}")
            for f in files:
                size_mb = f.stat().st_size / 1024 / 1024
                print(f"   - {f.name}: {size_mb:.2f}MB")

        # Очищаем кеш для чистого теста
        print("\n🧹 Clearing cache for fresh test...")
        await loader.clear_cache()

        # Загружаем датасет
        print("\n📊 Loading dataset...")
        dataset = await loader.load_dataset(force_reload=True)

        print(f"✅ Dataset loaded successfully!")
        print(f"   Total entries: {dataset.total_entries}")
        print(f"   Persons: {len(dataset.persons)}")
        print(f"   Organizations: {len(dataset.organizations)}")
        print(f"   Unique names: {len(dataset.all_names)}")
        print(f"   Sources: {dataset.sources}")

        # Проверяем fuzzy candidates
        fuzzy_candidates = await loader.get_fuzzy_candidates()
        print(f"   Fuzzy candidates: {len(fuzzy_candidates)}")

        # Поиск Ковриков в кандидатах
        kovrykov_candidates = [c for c in fuzzy_candidates if "ковриков" in c.lower()]
        print(f"   'Ковриков' entries: {len(kovrykov_candidates)}")
        for candidate in kovrykov_candidates:
            print(f"     - {candidate}")

        # Показываем sample некоторых entries
        print(f"\n📋 Sample entries:")
        for entry in dataset.persons[:5]:
            print(f"   - {entry.name} ({entry.source})")

        return len(fuzzy_candidates) >= 100  # Ожидаем минимум 100 записей

    except Exception as e:
        print(f"❌ Общая ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Главная функция."""
    print("🎯 ДИАГНОСТИКА SANCTIONS DATA LOADING")
    print("=" * 50)

    success = await test_sanctions_data_loading()

    print("\n" + "=" * 50)
    if success:
        print("🎉 SUCCESS: Sanctions data loading работает!")
    else:
        print("❌ FAILURE: Проблемы с загрузкой sanctions data")
        print("\n🔧 ВОЗМОЖНЫЕ ПРИЧИНЫ:")
        print("   1. Отсутствуют файлы sanctions в /data/sanctions")
        print("   2. Поврежденный кеш")
        print("   3. Ошибки при парсинге JSON файлов")
        print("   4. Неправильные права доступа к файлам")

    return success

if __name__ == "__main__":
    import asyncio
    success = asyncio.run(main())
    sys.exit(0 if success else 1)