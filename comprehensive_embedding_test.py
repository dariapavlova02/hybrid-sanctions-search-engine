#!/usr/bin/env python3
"""
Комплексный тест близости эмбеддингов для имен Вика/Виктория и Даша/Дарья
"""

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import pandas as pd
from typing import List, Dict, Tuple

# Тестовые имена
VIKTORIA_NAMES = [
    "Вика",
    "Виктория", 
    "Викуля",
    "Viktoriia",
    "Victoriia", 
    "Viktoriya",
    "Вікторія",
    "Віка"
]

DARIA_NAMES = [
    "Даша",
    "Дашенька",
    "Dashenka",
    "Daria",
    "Дарья",
    "Дарʼя",
    "Дарія",
    "Дашуля"
]

ALL_NAMES = VIKTORIA_NAMES + DARIA_NAMES

class ComprehensiveEmbeddingTester:
    """Класс для комплексного тестирования близости эмбеддингов"""
    
    def __init__(self, model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"):
        """
        Инициализация тестера
        
        Args:
            model_name: Название модели для эмбеддингов
        """
        self.model_name = model_name
        self.model = None
        self.embeddings = None
        self.names = ALL_NAMES
        self.viktoria_names = VIKTORIA_NAMES
        self.daria_names = DARIA_NAMES
        
    def load_model(self):
        """Загрузка модели эмбеддингов"""
        print(f"Загружаем модель: {self.model_name}")
        self.model = SentenceTransformer(self.model_name)
        print("Модель загружена успешно")
        
    def compute_embeddings(self):
        """Вычисление эмбеддингов для всех имен"""
        if self.model is None:
            raise ValueError("Модель не загружена")
            
        print("Вычисляем эмбеддинги...")
        self.embeddings = self.model.encode(self.names, normalize_embeddings=True)
        print(f"Эмбеддинги вычислены для {len(self.names)} имен")
        
    def compute_similarity_matrix(self) -> np.ndarray:
        """Вычисление матрицы косинусного сходства"""
        if self.embeddings is None:
            raise ValueError("Эмбеддинги не вычислены")
            
        similarity_matrix = cosine_similarity(self.embeddings)
        return similarity_matrix
        
    def print_full_similarity_matrix(self):
        """Вывод полной матрицы сходства"""
        similarity_matrix = self.compute_similarity_matrix()
        
        # Создаем DataFrame для красивого вывода
        df = pd.DataFrame(
            similarity_matrix,
            index=self.names,
            columns=self.names
        )
        
        print("\n" + "="*120)
        print("ПОЛНАЯ МАТРИЦА КОСИНУСНОГО СХОДСТВА")
        print("="*120)
        print(df.round(4))
        
    def get_similarity_pairs(self, threshold: float = 0.0) -> List[Tuple[str, str, float]]:
        """Получение пар имен с их сходством"""
        similarity_matrix = self.compute_similarity_matrix()
        pairs = []
        
        for i in range(len(self.names)):
            for j in range(i + 1, len(self.names)):
                similarity = similarity_matrix[i][j]
                if similarity >= threshold:
                    pairs.append((self.names[i], self.names[j], similarity))
                    
        # Сортируем по убыванию сходства
        pairs.sort(key=lambda x: x[2], reverse=True)
        return pairs
        
    def print_top_pairs(self, top_n: int = 20):
        """Вывод топ-N пар по сходству"""
        pairs = self.get_similarity_pairs()
        
        print(f"\n" + "="*120)
        print(f"ТОП-{min(top_n, len(pairs))} ПАР ПО СХОДСТВУ")
        print("="*120)
        
        for i, (name1, name2, similarity) in enumerate(pairs[:top_n], 1):
            print(f"{i:2d}. {name1:12s} <-> {name2:12s} = {similarity:.4f}")
            
    def analyze_within_group_similarity(self):
        """Анализ сходства внутри групп имен"""
        similarity_matrix = self.compute_similarity_matrix()
        
        print(f"\n" + "="*120)
        print("АНАЛИЗ СХОДСТВА ВНУТРИ ГРУПП")
        print("="*120)
        
        # Группа Виктории
        viktoria_indices = [i for i, name in enumerate(self.names) if name in self.viktoria_names]
        print("\nГРУППА ВИКТОРИИ:")
        viktoria_similarities = []
        for i in viktoria_indices:
            for j in viktoria_indices:
                if i < j:
                    sim = similarity_matrix[i][j]
                    viktoria_similarities.append(sim)
                    print(f"  {self.names[i]:12s} <-> {self.names[j]:12s} = {sim:.4f}")
        
        if viktoria_similarities:
            print(f"  Среднее внутригрупповое сходство: {np.mean(viktoria_similarities):.4f}")
            print(f"  Стандартное отклонение: {np.std(viktoria_similarities):.4f}")
        
        # Группа Дарьи
        daria_indices = [i for i, name in enumerate(self.names) if name in self.daria_names]
        print("\nГРУППА ДАРЬИ:")
        daria_similarities = []
        for i in daria_indices:
            for j in daria_indices:
                if i < j:
                    sim = similarity_matrix[i][j]
                    daria_similarities.append(sim)
                    print(f"  {self.names[i]:12s} <-> {self.names[j]:12s} = {sim:.4f}")
        
        if daria_similarities:
            print(f"  Среднее внутригрупповое сходство: {np.mean(daria_similarities):.4f}")
            print(f"  Стандартное отклонение: {np.std(daria_similarities):.4f}")
            
    def analyze_cross_group_similarity(self):
        """Анализ сходства между группами имен"""
        similarity_matrix = self.compute_similarity_matrix()
        
        print(f"\n" + "="*120)
        print("АНАЛИЗ СХОДСТВА МЕЖДУ ГРУППАМИ")
        print("="*120)
        
        viktoria_indices = [i for i, name in enumerate(self.names) if name in self.viktoria_names]
        daria_indices = [i for i, name in enumerate(self.names) if name in self.daria_names]
        
        cross_similarities = []
        print("\nВИКТОРИЯ ↔ ДАРЬЯ:")
        for i in viktoria_indices:
            for j in daria_indices:
                sim = similarity_matrix[i][j]
                cross_similarities.append(sim)
                print(f"  {self.names[i]:12s} <-> {self.names[j]:12s} = {sim:.4f}")
        
        if cross_similarities:
            print(f"  Среднее межгрупповое сходство: {np.mean(cross_similarities):.4f}")
            print(f"  Стандартное отклонение: {np.std(cross_similarities):.4f}")
            print(f"  Минимум: {np.min(cross_similarities):.4f}")
            print(f"  Максимум: {np.max(cross_similarities):.4f}")
            
    def analyze_language_groups(self):
        """Анализ по языковым группам"""
        similarity_matrix = self.compute_similarity_matrix()
        
        print(f"\n" + "="*120)
        print("АНАЛИЗ ПО ЯЗЫКОВЫМ ГРУППАМ")
        print("="*120)
        
        language_groups = {
            "Русские": ["Вика", "Виктория", "Викуля", "Даша", "Дашенька", "Дарья", "Дашуля"],
            "Украинские": ["Вікторія", "Віка", "Дарʼя", "Дарія"],
            "Латинские": ["Viktoriia", "Victoriia", "Viktoriya", "Dashenka", "Daria"]
        }
        
        for lang, names in language_groups.items():
            indices = [i for i, name in enumerate(self.names) if name in names]
            
            if len(indices) > 1:
                lang_similarities = []
                print(f"\n{lang} ({len(names)} имен):")
                for i in indices:
                    for j in indices:
                        if i < j:
                            sim = similarity_matrix[i][j]
                            lang_similarities.append(sim)
                            print(f"  {self.names[i]:12s} <-> {self.names[j]:12s} = {sim:.4f}")
                
                if lang_similarities:
                    print(f"  Среднее внутриязыковое сходство: {np.mean(lang_similarities):.4f}")
                    print(f"  Стандартное отклонение: {np.std(lang_similarities):.4f}")
            else:
                print(f"\n{lang} ({names[0]}): одиночное имя")
                
    def analyze_clusters(self, thresholds: List[float] = [0.5, 0.6, 0.7, 0.8, 0.9]):
        """Анализ кластеров имен по сходству"""
        similarity_matrix = self.compute_similarity_matrix()
        
        print(f"\n" + "="*120)
        print("АНАЛИЗ КЛАСТЕРОВ")
        print("="*120)
        
        for threshold in thresholds:
            visited = set()
            clusters = []
            
            for i, name in enumerate(self.names):
                if i in visited:
                    continue
                    
                cluster = [name]
                visited.add(i)
                
                for j, other_name in enumerate(self.names):
                    if j != i and j not in visited and similarity_matrix[i][j] >= threshold:
                        cluster.append(other_name)
                        visited.add(j)
                        
                if len(cluster) > 1:
                    clusters.append(cluster)
            
            print(f"\nПорог {threshold}: {len(clusters)} кластеров")
            for i, cluster in enumerate(clusters, 1):
                print(f"  Кластер {i}: {', '.join(cluster)}")
                
    def get_statistics(self):
        """Получение статистики по сходству"""
        similarity_matrix = self.compute_similarity_matrix()
        
        # Исключаем диагональ (сходство с самим собой = 1.0)
        mask = np.ones_like(similarity_matrix, dtype=bool)
        np.fill_diagonal(mask, False)
        similarities = similarity_matrix[mask]
        
        stats = {
            'mean': np.mean(similarities),
            'median': np.median(similarities),
            'std': np.std(similarities),
            'min': np.min(similarities),
            'max': np.max(similarities),
            'q25': np.percentile(similarities, 25),
            'q75': np.percentile(similarities, 75)
        }
        
        print(f"\n" + "="*120)
        print("ОБЩАЯ СТАТИСТИКА СХОДСТВА")
        print("="*120)
        print(f"Общее количество пар: {len(similarities)}")
        print(f"Среднее:     {stats['mean']:.4f}")
        print(f"Медиана:     {stats['median']:.4f}")
        print(f"Стд. откл.:  {stats['std']:.4f}")
        print(f"Минимум:     {stats['min']:.4f}")
        print(f"Максимум:    {stats['max']:.4f}")
        print(f"25-й перц.:  {stats['q25']:.4f}")
        print(f"75-й перц.:  {stats['q75']:.4f}")
        
        return stats
        
    def find_most_similar_cross_pairs(self, top_n: int = 10):
        """Поиск наиболее похожих пар между группами"""
        similarity_matrix = self.compute_similarity_matrix()
        
        viktoria_indices = [i for i, name in enumerate(self.names) if name in self.viktoria_names]
        daria_indices = [i for i, name in enumerate(self.names) if name in self.daria_names]
        
        cross_pairs = []
        for i in viktoria_indices:
            for j in daria_indices:
                sim = similarity_matrix[i][j]
                cross_pairs.append((self.names[i], self.names[j], sim))
        
        cross_pairs.sort(key=lambda x: x[2], reverse=True)
        
        print(f"\n" + "="*120)
        print(f"ТОП-{min(top_n, len(cross_pairs))} МЕЖГРУППОВЫХ ПАР")
        print("="*120)
        
        for i, (name1, name2, similarity) in enumerate(cross_pairs[:top_n], 1):
            print(f"{i:2d}. {name1:12s} <-> {name2:12s} = {similarity:.4f}")

def main():
    """Основная функция"""
    print("КОМПЛЕКСНЫЙ ТЕСТ БЛИЗОСТИ ЭМБЕДДИНГОВ")
    print("Виктория + Дарья")
    print("="*120)
    
    # Инициализация тестера
    tester = ComprehensiveEmbeddingTester()
    
    try:
        # Загрузка модели
        tester.load_model()
        
        # Вычисление эмбеддингов
        tester.compute_embeddings()
        
        # Вывод полной матрицы сходства
        tester.print_full_similarity_matrix()
        
        # Вывод топ пар
        tester.print_top_pairs(top_n=30)
        
        # Анализ внутри групп
        tester.analyze_within_group_similarity()
        
        # Анализ между группами
        tester.analyze_cross_group_similarity()
        
        # Анализ по языкам
        tester.analyze_language_groups()
        
        # Анализ кластеров
        tester.analyze_clusters()
        
        # Поиск межгрупповых пар
        tester.find_most_similar_cross_pairs()
        
        # Общая статистика
        tester.get_statistics()
        
        print(f"\n" + "="*120)
        print("ТЕСТ ЗАВЕРШЕН")
        print("="*120)
        
    except Exception as e:
        print(f"Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
