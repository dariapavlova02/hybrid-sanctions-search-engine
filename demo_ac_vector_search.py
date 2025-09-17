#!/usr/bin/env python3
"""
Демонстрация полной работоспособности Aho-Corasick и векторного поиска

Этот скрипт демонстрирует:
1. Aho-Corasick поиск с паттернами
2. Векторный поиск с FAISS
3. Гибридный поиск (AC + Vector)
4. Performance метрики
"""

import os
import time
import json
from typing import List, Dict, Any
from dataclasses import dataclass

# Устанавливаем переменные окружения для включения всех компонентов
os.environ["ENABLE_AHO_CORASICK"] = "true"
os.environ["ENABLE_EMBEDDINGS"] = "true"
os.environ["ENABLE_DECISION_ENGINE"] = "true"
os.environ["ENABLE_FAISS_INDEX"] = "true"

from src.ai_service.layers.smart_filter.smart_filter_service import SmartFilterService
from src.ai_service.layers.embeddings.optimized_embedding_service import OptimizedEmbeddingService
from src.ai_service.layers.embeddings.indexing.vector_index_service import CharTfidfVectorIndex, VectorIndexConfig
from src.ai_service.layers.patterns.unified_pattern_service import UnifiedPatternService
from src.ai_service.config.settings import ServiceConfig


@dataclass
class SearchResult:
    """Результат поиска"""
    method: str
    query: str
    results: List[Dict[str, Any]]
    processing_time_ms: float
    success: bool


class AhoCorasickVectorDemo:
    """Демонстрация Aho-Corasick и векторного поиска"""
    
    def __init__(self):
        self.config = ServiceConfig()
        print("=== Инициализация компонентов ===")
        
        # Инициализируем сервисы
        self.smart_filter = SmartFilterService(enable_aho_corasick=True)
        self.embedding_service = OptimizedEmbeddingService()
        self.pattern_service = UnifiedPatternService()
        
        # Создаем векторный индекс
        vector_config = VectorIndexConfig(use_faiss=True)
        self.vector_index = CharTfidfVectorIndex(vector_config)
        
        print("✓ Все компоненты инициализированы")
    
    def prepare_test_data(self) -> List[tuple]:
        """Подготавливаем тестовые данные"""
        test_docs = [
            ("person_001", "Иван Петров"),
            ("person_002", "Петр Иванов"),
            ("person_003", "Мария Сидорова"),
            ("person_004", "Александр Козлов"),
            ("person_005", "Елена Морозова"),
            ("person_006", "Дмитрий Волков"),
            ("person_007", "Анна Соколова"),
            ("person_008", "Сергей Лебедев"),
            ("person_009", "Ольга Новикова"),
            ("person_010", "Михаил Федоров"),
            ("org_001", "ООО Рога и Копыта"),
            ("org_002", "ИП Петров И.И."),
            ("org_003", "ЗАО Стройкомпания"),
            ("org_004", "ОАО Нефтегаз"),
            ("org_005", "ПАО Сбербанк"),
        ]
        
        print(f"✓ Подготовлено {len(test_docs)} тестовых документов")
        return test_docs
    
    def test_aho_corasick_search(self, text: str) -> SearchResult:
        """Тестируем Aho-Corasick поиск"""
        print(f"\n--- Aho-Corasick поиск: '{text}' ---")
        
        start_time = time.time()
        
        try:
            # Генерируем паттерны
            patterns = self.pattern_service.generate_patterns(text, language="ru")
            ac_patterns = self.pattern_service.export_for_aho_corasick(patterns)
            
            # Выполняем AC поиск
            ac_result = self.smart_filter.search_aho_corasick(text, max_matches=10)
            
            processing_time = (time.time() - start_time) * 1000
            
            print(f"Найдено паттернов: {len(patterns)}")
            print(f"AC паттерны по тирам: {len(ac_patterns)}")
            print(f"Найдено совпадений: {len(ac_result.get('matches', []))}")
            print(f"Время обработки: {processing_time:.2f}ms")
            
            return SearchResult(
                method="Aho-Corasick",
                query=text,
                results=ac_result.get('matches', []),
                processing_time_ms=processing_time,
                success=True
            )
            
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            print(f"✗ Ошибка AC поиска: {e}")
            return SearchResult(
                method="Aho-Corasick",
                query=text,
                results=[],
                processing_time_ms=processing_time,
                success=False
            )
    
    def test_vector_search(self, query: str, docs: List[tuple]) -> SearchResult:
        """Тестируем векторный поиск"""
        print(f"\n--- Векторный поиск: '{query}' ---")
        
        start_time = time.time()
        
        try:
            # Перестраиваем индекс с тестовыми данными
            self.vector_index.rebuild(docs)
            
            # Выполняем поиск
            results = self.vector_index.search(query, top_k=5)
            
            processing_time = (time.time() - start_time) * 1000
            
            print(f"Найдено результатов: {len(results)}")
            for i, (doc_id, score) in enumerate(results[:3], 1):
                doc_text = next((text for doc_id_found, text in docs if doc_id_found == doc_id), "Unknown")
                print(f"  {i}. {doc_id}: {doc_text} (score: {score:.4f})")
            
            print(f"Время обработки: {processing_time:.2f}ms")
            
            return SearchResult(
                method="Vector Search",
                query=query,
                results=[{"doc_id": doc_id, "score": score, "text": next((text for d_id, text in docs if d_id == doc_id), "Unknown")} 
                        for doc_id, score in results],
                processing_time_ms=processing_time,
                success=True
            )
            
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            print(f"✗ Ошибка векторного поиска: {e}")
            return SearchResult(
                method="Vector Search",
                query=query,
                results=[],
                processing_time_ms=processing_time,
                success=False
            )
    
    def test_embedding_search(self, query: str, candidates: List[str]) -> SearchResult:
        """Тестируем поиск по эмбеддингам"""
        print(f"\n--- Поиск по эмбеддингам: '{query}' ---")
        
        start_time = time.time()
        
        try:
            # Выполняем поиск похожих текстов
            result = self.embedding_service.find_similar_texts_optimized(
                query=query,
                candidates=candidates,
                threshold=0.7,
                top_k=5,
                use_faiss=True
            )
            
            processing_time = (time.time() - start_time) * 1000
            
            if result["success"]:
                print(f"Найдено результатов: {len(result['results'])}")
                for i, item in enumerate(result['results'][:3], 1):
                    print(f"  {i}. {item['text']} (similarity: {item['similarity_score']:.4f})")
            else:
                print(f"✗ Ошибка поиска: {result.get('error', 'Unknown error')}")
            
            print(f"Время обработки: {processing_time:.2f}ms")
            
            return SearchResult(
                method="Embedding Search",
                query=query,
                results=result.get('results', []),
                processing_time_ms=processing_time,
                success=result["success"]
            )
            
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            print(f"✗ Ошибка поиска по эмбеддингам: {e}")
            return SearchResult(
                method="Embedding Search",
                query=query,
                results=[],
                processing_time_ms=processing_time,
                success=False
            )
    
    def test_hybrid_search(self, query: str, docs: List[tuple]) -> Dict[str, Any]:
        """Тестируем гибридный поиск (AC + Vector)"""
        print(f"\n--- Гибридный поиск: '{query}' ---")
        
        start_time = time.time()
        
        # AC поиск
        ac_result = self.test_aho_corasick_search(query)
        
        # Vector поиск
        vector_result = self.test_vector_search(query, docs)
        
        # Embedding поиск
        candidates = [text for _, text in docs]
        embedding_result = self.test_embedding_search(query, candidates)
        
        total_time = (time.time() - start_time) * 1000
        
        # Анализируем результаты
        hybrid_analysis = {
            "query": query,
            "total_processing_time_ms": total_time,
            "ac_matches": len(ac_result.results),
            "vector_matches": len(vector_result.results),
            "embedding_matches": len(embedding_result.results),
            "ac_success": ac_result.success,
            "vector_success": vector_result.success,
            "embedding_success": embedding_result.success,
            "all_success": all([ac_result.success, vector_result.success, embedding_result.success])
        }
        
        print(f"\n=== Анализ гибридного поиска ===")
        print(f"AC совпадений: {hybrid_analysis['ac_matches']}")
        print(f"Vector совпадений: {hybrid_analysis['vector_matches']}")
        print(f"Embedding совпадений: {hybrid_analysis['embedding_matches']}")
        print(f"Общее время: {hybrid_analysis['total_processing_time_ms']:.2f}ms")
        print(f"Все методы успешны: {hybrid_analysis['all_success']}")
        
        return hybrid_analysis
    
    def run_comprehensive_demo(self):
        """Запускаем комплексную демонстрацию"""
        print("=" * 60)
        print("ДЕМОНСТРАЦИЯ AHO-CORASICK И ВЕКТОРНОГО ПОИСКА")
        print("=" * 60)
        
        # Подготавливаем данные
        test_docs = self.prepare_test_data()
        
        # Тестовые запросы
        test_queries = [
            "Иван Петров",
            "Петр",
            "Мария Сидорова",
            "ООО Рога",
            "Сбербанк",
            "Анна"
        ]
        
        all_results = []
        
        for query in test_queries:
            print(f"\n{'='*50}")
            print(f"ТЕСТИРОВАНИЕ ЗАПРОСА: '{query}'")
            print(f"{'='*50}")
            
            # Гибридный поиск
            hybrid_result = self.test_hybrid_search(query, test_docs)
            all_results.append(hybrid_result)
        
        # Итоговая статистика
        print(f"\n{'='*60}")
        print("ИТОГОВАЯ СТАТИСТИКА")
        print(f"{'='*60}")
        
        successful_queries = sum(1 for r in all_results if r['all_success'])
        avg_processing_time = sum(r['total_processing_time_ms'] for r in all_results) / len(all_results)
        
        print(f"Успешных запросов: {successful_queries}/{len(all_results)}")
        print(f"Среднее время обработки: {avg_processing_time:.2f}ms")
        print(f"AC успешных: {sum(1 for r in all_results if r['ac_success'])}/{len(all_results)}")
        print(f"Vector успешных: {sum(1 for r in all_results if r['vector_success'])}/{len(all_results)}")
        print(f"Embedding успешных: {sum(1 for r in all_results if r['embedding_success'])}/{len(all_results)}")
        
        # Сохраняем результаты
        with open('demo_results.json', 'w', encoding='utf-8') as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)
        
        print(f"\n✓ Результаты сохранены в demo_results.json")
        print("✓ Демонстрация завершена успешно!")


if __name__ == "__main__":
    demo = AhoCorasickVectorDemo()
    demo.run_comprehensive_demo()
