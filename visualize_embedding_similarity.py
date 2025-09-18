#!/usr/bin/env python3
"""
Визуализация близости эмбеддингов для различных вариантов имени Вика/Виктория
"""

import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
import pandas as pd

# Тестовые имена
TEST_NAMES = [
    "Вика",
    "Виктория", 
    "Викуля",
    "Viktoriia",
    "Victoriia", 
    "Viktoriya",
    "Вікторія",
    "Віка"
]

def create_visualizations():
    """Создание визуализаций для анализа эмбеддингов"""
    
    # Загрузка модели
    print("Загружаем модель...")
    model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    
    # Вычисление эмбеддингов
    print("Вычисляем эмбеддинги...")
    embeddings = model.encode(TEST_NAMES, normalize_embeddings=True)
    
    # Матрица сходства
    similarity_matrix = cosine_similarity(embeddings)
    
    # Создание фигуры с подграфиками
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle('Анализ близости эмбеддингов для имен Вика/Виктория', fontsize=16, fontweight='bold')
    
    # 1. Тепловая карта матрицы сходства
    ax1 = axes[0, 0]
    sns.heatmap(
        similarity_matrix,
        xticklabels=TEST_NAMES,
        yticklabels=TEST_NAMES,
        annot=True,
        fmt='.3f',
        cmap='YlOrRd',
        ax=ax1,
        cbar_kws={'label': 'Косинусное сходство'}
    )
    ax1.set_title('Матрица косинусного сходства')
    ax1.tick_params(axis='x', rotation=45)
    ax1.tick_params(axis='y', rotation=0)
    
    # 2. График распределения сходства
    ax2 = axes[0, 1]
    # Исключаем диагональ (сходство с самим собой = 1.0)
    mask = np.ones_like(similarity_matrix, dtype=bool)
    np.fill_diagonal(mask, False)
    similarities = similarity_matrix[mask]
    
    ax2.hist(similarities, bins=20, alpha=0.7, color='skyblue', edgecolor='black')
    ax2.axvline(np.mean(similarities), color='red', linestyle='--', 
                label=f'Среднее: {np.mean(similarities):.3f}')
    ax2.axvline(np.median(similarities), color='green', linestyle='--', 
                label=f'Медиана: {np.median(similarities):.3f}')
    ax2.set_xlabel('Косинусное сходство')
    ax2.set_ylabel('Частота')
    ax2.set_title('Распределение значений сходства')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # 3. PCA визуализация в 2D
    ax3 = axes[1, 0]
    pca = PCA(n_components=2)
    embeddings_2d = pca.fit_transform(embeddings)
    
    scatter = ax3.scatter(embeddings_2d[:, 0], embeddings_2d[:, 1], 
                         c=range(len(TEST_NAMES)), cmap='tab10', s=100, alpha=0.7)
    
    # Добавляем подписи к точкам
    for i, name in enumerate(TEST_NAMES):
        ax3.annotate(name, (embeddings_2d[i, 0], embeddings_2d[i, 1]), 
                    xytext=(5, 5), textcoords='offset points', fontsize=8)
    
    ax3.set_xlabel(f'PC1 ({pca.explained_variance_ratio_[0]:.1%} дисперсии)')
    ax3.set_ylabel(f'PC2 ({pca.explained_variance_ratio_[1]:.1%} дисперсии)')
    ax3.set_title('PCA проекция эмбеддингов')
    ax3.grid(True, alpha=0.3)
    
    # 4. t-SNE визуализация
    ax4 = axes[1, 1]
    tsne = TSNE(n_components=2, random_state=42, perplexity=min(5, len(TEST_NAMES)-1))
    embeddings_tsne = tsne.fit_transform(embeddings)
    
    scatter = ax4.scatter(embeddings_tsne[:, 0], embeddings_tsne[:, 1], 
                         c=range(len(TEST_NAMES)), cmap='tab10', s=100, alpha=0.7)
    
    # Добавляем подписи к точкам
    for i, name in enumerate(TEST_NAMES):
        ax4.annotate(name, (embeddings_tsne[i, 0], embeddings_tsne[i, 1]), 
                    xytext=(5, 5), textcoords='offset points', fontsize=8)
    
    ax4.set_xlabel('t-SNE 1')
    ax4.set_ylabel('t-SNE 2')
    ax4.set_title('t-SNE проекция эмбеддингов')
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('embedding_similarity_analysis.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    # Создание дендрограммы
    plt.figure(figsize=(12, 8))
    
    # Вычисляем расстояние как 1 - сходство
    distance_matrix = 1 - similarity_matrix
    
    # Создаем дендрограмму
    from scipy.cluster.hierarchy import dendrogram, linkage
    from scipy.spatial.distance import squareform
    
    # Преобразуем в condensed distance matrix
    condensed_distances = squareform(distance_matrix)
    linkage_matrix = linkage(condensed_distances, method='ward')
    
    plt.subplot(2, 1, 1)
    dendrogram(linkage_matrix, labels=TEST_NAMES, orientation='top')
    plt.title('Дендрограмма кластеризации имен')
    plt.xlabel('Имена')
    plt.ylabel('Расстояние')
    
    # График сходства по парам
    plt.subplot(2, 1, 2)
    pairs = []
    similarities = []
    
    for i in range(len(TEST_NAMES)):
        for j in range(i + 1, len(TEST_NAMES)):
            pairs.append(f"{TEST_NAMES[i]}-{TEST_NAMES[j]}")
            similarities.append(similarity_matrix[i][j])
    
    # Сортируем по сходству
    sorted_data = sorted(zip(pairs, similarities), key=lambda x: x[1], reverse=True)
    pairs_sorted, similarities_sorted = zip(*sorted_data)
    
    bars = plt.bar(range(len(pairs_sorted)), similarities_sorted, color='lightcoral')
    plt.xticks(range(len(pairs_sorted)), pairs_sorted, rotation=45, ha='right')
    plt.ylabel('Косинусное сходство')
    plt.title('Сходство между парами имен')
    plt.grid(True, alpha=0.3)
    
    # Добавляем значения на столбцы
    for i, (bar, sim) in enumerate(zip(bars, similarities_sorted)):
        plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01, 
                f'{sim:.3f}', ha='center', va='bottom', fontsize=8)
    
    plt.tight_layout()
    plt.savefig('embedding_dendrogram_analysis.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    print("Визуализации сохранены:")
    print("- embedding_similarity_analysis.png")
    print("- embedding_dendrogram_analysis.png")

if __name__ == "__main__":
    create_visualizations()
