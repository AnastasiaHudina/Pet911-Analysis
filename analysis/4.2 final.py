import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.patches import Patch

# Настройка визуализации
plt.rcParams['font.family'] = 'DejaVu Sans'
sns.set_palette("husl")
pd.set_option('display.max_columns', None)

def load_and_prepare_data(lost_file, found_file):
    """
    Загружает данные из двух файлов, объединяет их и создает целевую переменную is_success.
    """
    print("Загрузка данных...")
    
    # Загрузка данных
    df_lost = pd.read_csv(lost_file)
    df_found = pd.read_csv(found_file)
    
    # Добавляем метку типа объявления
    df_lost['объявление_тип'] = 'lost'
    df_found['объявление_тип'] = 'found'
    
    # Объединяем датасеты
    df_combined = pd.concat([df_lost, df_found], ignore_index=True)
    
    # Создаем целевую переменную is_success
    success_conditions = (
        (df_combined['статус'] == 'питомец найден') | 
        (df_combined['статус'] == 'хозяин найден')
    )
    df_combined['is_success'] = success_conditions
    
    print(f"Всего объявлений: {len(df_combined)}")
    print(f"Успешных случаев: {df_combined['is_success'].sum()}")
    print(f"Неуспешных случаев: {len(df_combined) - df_combined['is_success'].sum()}")
    
    return df_combined

def calculate_completeness_features(df):
    """
    Создает признаки для оценки наполненности объявлений.
    """
    print("\nРасчет признаков наполненности...")
    
    # 1. Количество фото (прямой признак)
    df['фото_количество'] = df['количество_фото'].fillna(0)
    
    # 2. Наличие фото (бинарный признак)
    df['фото_наличие'] = df['есть_фото'].astype(int)
    
    # 3. Длина описания в словах
    df['описание_длина'] = df['Длина_описания_в_словах'].fillna(0)
    
    # 4. Наличие описания
    df['описание_наличие'] = df['наличие_описания'].astype(int)
    
    # 5. Полнота заполнения ключевых полей
    key_columns = ['регион', 'тип_животного', 'окрас', 'порода', 
                   'место события', 'пол', 'возраст']
    
    def calculate_field_completeness(row):
        filled = 0
        for col in key_columns:
            if (col in row and 
                pd.notna(row[col]) and 
                row[col] != 'Неизвестно' and 
                str(row[col]).strip() != ''):
                filled += 1
        return filled / len(key_columns)
    
    df['полнота_полей'] = df.apply(calculate_field_completeness, axis=1)
    
    # 6. Общий балл наполненности (композитный показатель)
    df['общий_балл'] = (
        df['фото_количество'] * 0.3 + 
        df['описание_длина'] * 0.001 +  # нормализуем длину описания
        df['полнота_полей'] * 0.7
    )
    
    print("Статистика признаков наполненности:")
    print(df[['фото_количество', 'описание_длина', 'полнота_полей', 'общий_балл']].describe())
    
    return df

def assign_clusters(df):
    """
    Присваивает кластеры по четко заданным критериям.
    """
    print("\nПрисвоение кластеров...")
    
    conditions = [
        # 1. Идеальные анкеты
        (df['фото_количество'] >= 3) & 
        (df['описание_длина'] >= 30) & 
        (df['полнота_полей'] >= 0.8),
        
        # 2. Полные анкеты
        (df['фото_количество'] >= 2) & 
        (df['описание_длина'] >= 15) & 
        (df['полнота_полей'] >= 0.6),
        
        # 3. Средние анкеты
        (df['фото_количество'] >= 1) & 
        (df['описание_длина'] >= 5) & 
        (df['полнота_полей'] >= 0.4),
        
        # 4. Текстовые анкеты (нет фото или 0 фото, но есть описание)
        (df['фото_количество'] == 0) & 
        (df['описание_длина'] >= 1),
        
        # 5. Визуальные анкеты (есть фото, но практически нет описания)
        (df['фото_количество'] >= 1) & 
        (df['описание_длина'] < 5)
    ]
    
    cluster_names = [
        'Идеальные анкеты',
        'Полные анкеты', 
        'Средние анкеты',
        'Текстовые анкеты',
        'Визуальные анкеты'
    ]
    
    # Присваиваем кластеры
    df['cluster'] = np.select(conditions, cluster_names, default='Неопределенные')
    
    # Статистика по кластерам
    cluster_stats = df['cluster'].value_counts()
    print("\nРаспределение по кластерам:")
    for cluster, count in cluster_stats.items():
        print(f"  {cluster}: {count} объявлений ({count/len(df)*100:.1f}%)")
    
    return df

def plot_cluster_distribution(df):
    """
    Строит график распределения объявлений по кластерам.
    """
    print("\nПостроение графиков...")
    
    # Распределение по кластерам
    cluster_counts = df['cluster'].value_counts()
    
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Цвета для кластеров
    colors = ['#2E8B57', '#3CB371', '#FFD700', '#FF8C00', '#DC143C', '#808080']
    
    bars = ax.bar(cluster_counts.index, cluster_counts.values, color=colors[:len(cluster_counts)])
    
    # Добавляем подписи с количеством
    for bar, count in zip(bars, cluster_counts.values):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 5,
                f'{count}\n({count/len(df)*100:.1f}%)',
                ha='center', va='bottom', fontweight='bold')
    
    ax.set_title('РАСПРЕДЕЛЕНИЕ ОБЪЯВЛЕНИЙ ПО КЛАСТЕРАМ', fontsize=16, fontweight='bold', pad=20)
    ax.set_ylabel('Количество объявлений', fontsize=12)
    ax.tick_params(axis='x', rotation=45)
    ax.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('cluster_distribution.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    return cluster_counts

def plot_success_rate_by_cluster(df):
    """
    Строит график успешности поиска по кластерам.
    """
    # Успешность по кластерам
    success_by_cluster = df.groupby('cluster')['is_success'].agg(['mean', 'count']).round(3)
    success_by_cluster.columns = ['доля_успеха', 'количество']
    success_by_cluster = success_by_cluster.sort_values('доля_успеха', ascending=False)
    
    fig, ax = plt.subplots(figsize=(12, 8))
    
    colors = ['#2E8B57', '#3CB371', '#FFD700', '#FF8C00', '#DC143C', '#808080']
    cluster_order = success_by_cluster.index
    
    bars = ax.bar(cluster_order, success_by_cluster['доля_успеха'] * 100, 
                 color=colors[:len(cluster_order)], alpha=0.8)
    
    # Добавляем значения на столбцы
    for bar, success_rate in zip(bars, success_by_cluster['доля_успеха'] * 100):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 1,
                f'{success_rate:.1f}%',
                ha='center', va='bottom', fontweight='bold', fontsize=11)
    
    ax.set_title('УСПЕШНОСТЬ ПОИСКА ПО КЛАСТЕРАМ', fontsize=16, fontweight='bold', pad=20)
    ax.set_ylabel('Процент успешных случаев (%)', fontsize=12)
    ax.set_ylim(0, max(success_by_cluster['доля_успеха'] * 100) + 15)
    ax.tick_params(axis='x', rotation=45)
    ax.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('success_rate_by_cluster.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    return success_by_cluster

def plot_cluster_comparison(df):
    """
    Строит сравнительные графики наполненности анкет по кластерам.
    """
    # Группируем по кластерам и вычисляем средние значения
    cluster_means = df.groupby('cluster').agg({
        'фото_количество': 'mean',
        'описание_длина': 'mean', 
        'полнота_полей': 'mean',
        'общий_балл': 'mean',
        'is_success': 'mean'
    }).round(3)
    
    # Нормализуем для радиальной диаграммы
    normalized = cluster_means.copy()
    for col in ['фото_количество', 'описание_длина', 'полнота_полей']:
        normalized[col] = normalized[col] / normalized[col].max()
    
    # Создаем фигуру с несколькими субплогами
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    
    # 1. Среднее количество фото по кластерам
    cluster_means_sorted = cluster_means.sort_values('фото_количество', ascending=False)
    axes[0, 0].bar(cluster_means_sorted.index, cluster_means_sorted['фото_количество'], 
                   color='lightblue', edgecolor='navy', alpha=0.7)
    axes[0, 0].set_title('СРЕДНЕЕ КОЛИЧЕСТВО ФОТО', fontweight='bold')
    axes[0, 0].set_ylabel('Количество фото')
    axes[0, 0].tick_params(axis='x', rotation=45)
    axes[0, 0].grid(axis='y', alpha=0.3)
    
    # Добавляем значения на столбцы
    for i, v in enumerate(cluster_means_sorted['фото_количество']):
        axes[0, 0].text(i, v + 0.1, f'{v:.1f}', ha='center', va='bottom', fontweight='bold')
    
    # 2. Средняя длина описания по кластерам
    cluster_means_sorted = cluster_means.sort_values('описание_длина', ascending=False)
    axes[0, 1].bar(cluster_means_sorted.index, cluster_means_sorted['описание_длина'], 
                   color='lightgreen', edgecolor='darkgreen', alpha=0.7)
    axes[0, 1].set_title('СРЕДНЯЯ ДЛИНА ОПИСАНИЯ', fontweight='bold')
    axes[0, 1].set_ylabel('Длина в словах')
    axes[0, 1].tick_params(axis='x', rotation=45)
    axes[0, 1].grid(axis='y', alpha=0.3)
    
    # Добавляем значения на столбцы
    for i, v in enumerate(cluster_means_sorted['описание_длина']):
        axes[0, 1].text(i, v + 1, f'{v:.0f}', ha='center', va='bottom', fontweight='bold')
    
    # 3. Средняя полнота полей по кластерам
    cluster_means_sorted = cluster_means.sort_values('полнота_полей', ascending=False)
    axes[1, 0].bar(cluster_means_sorted.index, cluster_means_sorted['полнота_полей'] * 100, 
                   color='gold', edgecolor='orange', alpha=0.7)
    axes[1, 0].set_title('СРЕДНЯЯ ПОЛНОТА ЗАПОЛНЕНИЯ ПОЛЕЙ', fontweight='bold')
    axes[1, 0].set_ylabel('Процент заполнения (%)')
    axes[1, 0].tick_params(axis='x', rotation=45)
    axes[1, 0].grid(axis='y', alpha=0.3)
    
    # Добавляем значения на столбцы
    for i, v in enumerate(cluster_means_sorted['полнота_полей'] * 100):
        axes[1, 0].text(i, v + 2, f'{v:.0f}%', ha='center', va='bottom', fontweight='bold')
    
    # 4. Радарная диаграмма характеристик кластеров
    clusters = normalized.index
    features = ['фото_количество', 'описание_длина', 'полнота_полей']
    
    # Углы для радарной диаграммы
    angles = np.linspace(0, 2*np.pi, len(features), endpoint=False).tolist()
    angles += angles[:1]  # Замыкаем круг
    
    # Создаем радарную диаграмму
    ax_radar = fig.add_subplot(2, 2, 4, polar=True)
    
    colors = ['#2E8B57', '#3CB371', '#FFD700', '#FF8C00', '#DC143C', '#808080']
    
    for i, cluster in enumerate(clusters):
        values = normalized.loc[cluster, features].tolist()
        values += values[:1]  # Замыкаем круг
        ax_radar.plot(angles, values, 'o-', linewidth=2, label=cluster, color=colors[i])
        ax_radar.fill(angles, values, alpha=0.1, color=colors[i])
    
    ax_radar.set_xticks(angles[:-1])
    ax_radar.set_xticklabels(['Фото', 'Описание', 'Полнота\nполей'])
    ax_radar.set_ylim(0, 1)
    ax_radar.set_title('СРАВНЕНИЕ КЛАСТЕРОВ\n(нормализованные значения)', fontweight='bold', pad=20)
    ax_radar.legend(bbox_to_anchor=(1.3, 1.0), loc='upper right')
    
    plt.tight_layout()
    plt.savefig('cluster_comparison.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    return cluster_means

def print_cluster_insights(df, cluster_means, success_by_cluster):
    """
    Выводит ключевые инсайты по кластерам.
    """
    print("\n" + "="*80)
    print("КЛЮЧЕВЫЕ ИНСАЙТЫ КЛАСТЕРИЗАЦИИ")
    print("="*80)
    
    print(f"\n📊 ОБЩАЯ СТАТИСТИКА:")
    print(f"Всего объявлений: {len(df)}")
    print(f"Общая успешность: {df['is_success'].mean():.1%}")
    
    print(f"\n🏆 РЕЙТИНГ КЛАСТЕРОВ ПО УСПЕШНОСТИ:")
    for i, (cluster, row) in enumerate(success_by_cluster.iterrows(), 1):
        print(f"  {i}. {cluster:20} - {row['доля_успеха']:.1%} успеха ({row['количество']} объяв.)")
    
    print(f"\n🔍 ХАРАКТЕРИСТИКИ КЛАСТЕРОВ:")
    for cluster in cluster_means.index:
        stats = cluster_means.loc[cluster]
        print(f"\n  {cluster}:")
        print(f"    • Фото: {stats['фото_количество']:.1f} шт.")
        print(f"    • Описание: {stats['описание_длина']:.0f} слов") 
        print(f"    • Полнота полей: {stats['полнота_полей']:.0%}")
        print(f"    • Успешность: {stats['is_success']:.1%}")
    
    # Анализ эффективности
    print(f"\n💡 ВЫВОДЫ И РЕКОМЕНДАЦИИ:")
    
    best_cluster = success_by_cluster.index[0]
    worst_cluster = success_by_cluster.index[-1]
    
    print(f"  1. Самый успешный кластер: '{best_cluster}'")
    print(f"  2. Наименее успешный кластер: '{worst_cluster}'")
    
    # Анализ влияния фото
    photo_corr = df[['фото_количество', 'is_success']].corr().iloc[0,1]
    print(f"  3. Корреляция количества фото с успехом: {photo_corr:.3f}")
    
    # Анализ влияния описания
    desc_corr = df[['описание_длина', 'is_success']].corr().iloc[0,1]
    print(f"  4. Корреляция длины описания с успехом: {desc_corr:.3f}")

def main():
    """
    Основная функция для кластеризации.
    """
    # Укажите пути к вашим файлам
    LOST_FILE = 'Dataset_final_Pet911_lost.csv'
    FOUND_FILE = 'dataset_final_Pet911_found.csv'
    
    try:
        print("=== КЛАСТЕРИЗАЦИЯ ПО НАПОЛНЕННОСТИ ОБЪЯВЛЕНИЙ ===")
        
        # Загрузка данных
        df = load_and_prepare_data(LOST_FILE, FOUND_FILE)
        
        # Расчет признаков наполненности
        df = calculate_completeness_features(df)
        
        # Присвоение кластеров
        df = assign_clusters(df)
        
        # Визуализация
        cluster_distribution = plot_cluster_distribution(df)
        success_by_cluster = plot_success_rate_by_cluster(df)
        cluster_means = plot_cluster_comparison(df)
        
        # Вывод инсайтов
        print_cluster_insights(df, cluster_means, success_by_cluster)
        
        # Сохранение результатов
        df.to_csv('объявления_с_кластерами.csv', index=False, encoding='utf-8-sig')
        
        # Сохранение статистики по кластерам
        cluster_stats = df.groupby('cluster').agg({
            'фото_количество': ['mean', 'std'],
            'описание_длина': ['mean', 'std'],
            'полнота_полей': ['mean', 'std'],
            'is_success': 'mean',
            'id': 'count'
        }).round(3)
        
        cluster_stats.to_csv('статистика_кластеров.csv', encoding='utf-8-sig')
        
        print(f"\nРезультаты сохранены в файлы:")
        print("- объявления_с_кластерами.csv")
        print("- статистика_кластеров.csv")
        print("- cluster_distribution.png")
        print("- success_rate_by_cluster.png") 
        print("- cluster_comparison.png")
        
    except Exception as e:
        print(f"Произошла ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()