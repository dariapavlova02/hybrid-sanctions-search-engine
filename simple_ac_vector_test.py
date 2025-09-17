#!/usr/bin/env python3
"""
Простой тест работоспособности Aho-Corasick и векторного поиска
"""

import os
import time

# Устанавливаем переменные окружения
os.environ["ENABLE_AHO_CORASICK"] = "true"
os.environ["ENABLE_EMBEDDINGS"] = "true"
os.environ["ENABLE_DECISION_ENGINE"] = "true"
os.environ["ENABLE_FAISS_INDEX"] = "true"

def test_aho_corasick():
    """Тест Aho-Corasick"""
    print("=== Тест Aho-Corasick ===")
    try:
        from src.ai_service.layers.smart_filter.smart_filter_service import SmartFilterService
        
        service = SmartFilterService(enable_aho_corasick=True)
        print("✓ SmartFilterService инициализирован")
        
        # Простой тест
        result = service.search_aho_corasick("Иван Петров", max_matches=5)
        print(f"✓ AC поиск работает: найдено {len(result.get('matches', []))} совпадений")
        
        return True
    except Exception as e:
        print(f"✗ Ошибка AC: {e}")
        return False

def test_vector_search():
    """Тест векторного поиска"""
    print("\n=== Тест векторного поиска ===")
    try:
        from src.ai_service.layers.embeddings.indexing.vector_index_service import CharTfidfVectorIndex, VectorIndexConfig
        
        # Создаем тестовые данные
        docs = [
            ("doc1", "Иван Петров"),
            ("doc2", "Петр Иванов"),
            ("doc3", "Мария Сидорова")
        ]
        
        # Создаем индекс
        config = VectorIndexConfig(use_faiss=True)
        index = CharTfidfVectorIndex(config)
        index.rebuild(docs)
        print("✓ Векторный индекс создан")
        
        # Тестируем поиск
        results = index.search("Иван", top_k=3)
        print(f"✓ Vector поиск работает: найдено {len(results)} результатов")
        
        for doc_id, score in results:
            print(f"  - {doc_id}: {score:.4f}")
        
        return True
    except Exception as e:
        print(f"✗ Ошибка Vector: {e}")
        return False

def test_embeddings():
    """Тест эмбеддингов"""
    print("\n=== Тест эмбеддингов ===")
    try:
        from src.ai_service.layers.embeddings.optimized_embedding_service import OptimizedEmbeddingService
        
        service = OptimizedEmbeddingService()
        print("✓ EmbeddingService инициализирован")
        
        # Простой тест
        result = service.get_embeddings_optimized(["тест"])
        if result["success"]:
            print(f"✓ Embeddings работают: получен вектор размером {len(result['embeddings'][0])}")
        else:
            print(f"✗ Ошибка embeddings: {result.get('error', 'Unknown')}")
            return False
        
        return True
    except Exception as e:
        print(f"✗ Ошибка Embeddings: {e}")
        return False

def test_faiss_availability():
    """Тест доступности FAISS"""
    print("\n=== Тест FAISS ===")
    try:
        import faiss
        import numpy as np
        
        # Создаем простой индекс
        dimension = 128
        index = faiss.IndexFlatL2(dimension)
        
        # Добавляем тестовые векторы
        vectors = np.random.random((5, dimension)).astype('float32')
        index.add(vectors)
        
        # Тестируем поиск
        query = np.random.random((1, dimension)).astype('float32')
        scores, indices = index.search(query, 3)
        
        print(f"✓ FAISS работает: найдено {len(indices[0])} результатов")
        return True
    except Exception as e:
        print(f"✗ Ошибка FAISS: {e}")
        return False

def main():
    """Главная функция"""
    print("ПРОВЕРКА РАБОТОСПОСОБНОСТИ AHO-CORASICK И ВЕКТОРНОГО ПОИСКА")
    print("=" * 60)
    
    tests = [
        ("FAISS", test_faiss_availability),
        ("Aho-Corasick", test_aho_corasick),
        ("Vector Search", test_vector_search),
        ("Embeddings", test_embeddings),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"✗ Критическая ошибка в {test_name}: {e}")
            results.append((test_name, False))
    
    # Итоги
    print("\n" + "=" * 60)
    print("ИТОГИ ТЕСТИРОВАНИЯ")
    print("=" * 60)
    
    successful = 0
    for test_name, success in results:
        status = "✓ РАБОТАЕТ" if success else "✗ НЕ РАБОТАЕТ"
        print(f"{test_name}: {status}")
        if success:
            successful += 1
    
    print(f"\nУспешно: {successful}/{len(results)}")
    
    if successful == len(results):
        print("🎉 ВСЕ КОМПОНЕНТЫ РАБОТАЮТ КОРРЕКТНО!")
    else:
        print("⚠️  НЕКОТОРЫЕ КОМПОНЕНТЫ ТРЕБУЮТ ВНИМАНИЯ")

if __name__ == "__main__":
    main()
