import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

# Настройка отображения
plt.style.use('default')
sns.set_palette("husl")


def load_and_prepare_data(file_path):
    """Загрузка и подготовка данных"""
    df = pd.read_csv(file_path)

    # Преобразование даты
    df['дата_публикации'] = pd.to_datetime(df['дата_публикации'], format='%a, %d.%m.%Y', errors='coerce')

    # Создание флага "найдено"
    df['найдено'] = df['статус_поиска'].isin(['найден', 'хозяин найден'])

    return df


def group_regions(df):
    """Группировка регионов: оставляем Москву и Санкт-Петербург, остальное - Другое"""
    # Создаем копию столбца с регионами
    df['регион_группированный'] = df['регион']

    # Определяем, что оставляем как есть (Москва и Санкт-Петербург)
    main_cities = ['Москва', 'Санкт-Петербург']

    # Все остальное помечаем как "Другое"
    df.loc[~df['регион'].isin(main_cities), 'регион_группированный'] = 'Другое'

    return df


def analyze_regions(df):
    """Анализ региональной статистики"""

    # Группируем регионы
    df = group_regions(df)

    # Группировка по сгруппированным регионам
    region_stats = df.groupby('регион_группированный').agg({
        'id': 'count',  # общее количество заявок
        'найдено': 'sum'  # количество найденных
    }).rename(columns={'id': 'общее_количество', 'найдено': 'найдено_количество'})

    # Расчет процента найденных
    region_stats['процент_найденных'] = (
            region_stats['найдено_количество'] / region_stats['общее_количество'] * 100).round(2)

    # Сортировка по общему количеству заявок
    region_stats_sorted = region_stats.sort_values('общее_количество', ascending=True)

    return region_stats_sorted


def create_regions_table(df, output_prefix=''):
    """Создание таблицы с топ-10 регионов по проценту найденных"""

    # Анализируем исходные регионы (без группировки)
    original_region_stats = df.groupby('регион').agg({
        'id': 'count',
        'найдено': 'sum'
    }).rename(columns={'id': 'общее_количество', 'найдено': 'найдено_количество'})

    # Расчет процента найденных
    original_region_stats['процент_найденных'] = (
            original_region_stats['найдено_количество'] / original_region_stats['общее_количество'] * 100
    ).round(2)

    # Сортировка по проценту найденных (по убыванию)
    top_regions = original_region_stats.sort_values('процент_найденных', ascending=False).head(10)

    # Создаем таблицу
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.axis('tight')
    ax.axis('off')

    # Подготовка данных для таблицы
    table_data = []
    for region, row in top_regions.iterrows():
        table_data.append([region, f"{row['процент_найденных']}%"])

    # Создание таблицы
    table = ax.table(cellText=table_data,
                     colLabels=['Регион', 'Процент найденных'],
                     cellLoc='center',
                     loc='center',
                     bbox=[0.1, 0.1, 0.8, 0.8])

    # Стилизация таблицы
    table.auto_set_font_size(False)
    table.set_fontsize(12)
    table.scale(1.2, 2)

    # Заголовок строк
    for i in range(len(table_data) + 1):
        for j in range(2):
            if i == 0:  # Заголовок
                table[(i, j)].set_facecolor('#4CAF50')
                table[(i, j)].set_text_props(weight='bold', color='white')
            else:  # Данные
                table[(i, j)].set_facecolor('#f0f0f0')

    plt.title('Топ-10 регионов по проценту найденных животных',
              fontsize=16, fontweight='bold', pad=20)

    # Добавляем информацию о количестве регионов
    total_regions = len(original_region_stats)
    plt.figtext(0.5, 0.02, f'Всего уникальных регионов в данных: {total_regions}',
                ha='center', fontsize=12, style='italic')

    plt.tight_layout()
    plt.savefig(f'{output_prefix}top_regions_table.png', dpi=300, bbox_inches='tight')
    plt.show()

    return top_regions


def create_visualizations(region_stats, output_prefix=''):
    """Создание визуализаций"""

    # 1. Горизонтальная гистограмма - регионы по общему количеству заявок
    plt.figure(figsize=(12, 6))
    bars = plt.barh(region_stats.index, region_stats['общее_количество'])
    plt.xlabel('Количество заявок')
    plt.title('Распределение заявок по основным регионам')
    plt.grid(axis='x', alpha=0.3)

    # Добавление значений на столбцы
    for bar, value in zip(bars, region_stats['общее_количество']):
        plt.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height() / 2,
                 f'{value}', va='center', ha='left')

    plt.tight_layout()
    plt.savefig(f'{output_prefix}regions_by_requests.png', dpi=300, bbox_inches='tight')
    plt.show()

    # 2. Круговая диаграмма - распределение найденных по регионам
    plt.figure(figsize=(10, 8))

    # Рассчитываем проценты для круговой диаграммы
    found_by_region = region_stats['найдено_количество']
    total_found = found_by_region.sum()

    # Для круговой диаграммы используем все категории (их всего 3)
    percentages = (found_by_region / total_found * 100).round(1)

    colors = plt.cm.Set3(np.linspace(0, 1, len(percentages)))
    wedges, texts, autotexts = plt.pie(percentages.values,
                                       labels=percentages.index,
                                       autopct='%1.1f%%',
                                       colors=colors,
                                       startangle=90)

    # Улучшаем отображение текста
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontweight('bold')

    plt.title('Распределение найденных животных по регионам')
    plt.tight_layout()
    plt.savefig(f'{output_prefix}found_animals_by_region_pie.png', dpi=300, bbox_inches='tight')
    plt.show()

    # 3. График эффективности регионов (процент найденных)
    plt.figure(figsize=(12, 6))
    region_stats_sorted_eff = region_stats.sort_values('процент_найденных', ascending=True)

    bars = plt.barh(region_stats_sorted_eff.index, region_stats_sorted_eff['процент_найденных'])
    plt.xlabel('Процент найденных животных (%)')
    plt.title('Эффективность поиска по регионам')
    plt.grid(axis='x', alpha=0.3)

    # Добавление значений на столбцы
    for bar, value in zip(bars, region_stats_sorted_eff['процент_найденных']):
        plt.text(bar.get_width() + 1, bar.get_y() + bar.get_height() / 2,
                 f'{value}%', va='center', ha='left', fontsize=9)

    plt.tight_layout()
    plt.savefig(f'{output_prefix}regions_efficiency.png', dpi=300, bbox_inches='tight')
    plt.show()

    # 4. Дополнительная столбчатая диаграмма - сравнение абсолютных чисел
    # УБИРАЕМ ЛИШНИЙ plt.figure() - используем только fig, ax
    fig, ax = plt.subplots(figsize=(10, 6))

    x = np.arange(len(region_stats))
    width = 0.35

    bars1 = ax.bar(x - width / 2, region_stats['общее_количество'], width, label='Все заявки')
    bars2 = ax.bar(x + width / 2, region_stats['найдено_количество'], width, label='Найдено')

    ax.set_xlabel('Регионы')
    ax.set_ylabel('Количество')
    ax.set_title('Сравнение общего числа заявок и найденных животных по регионам')
    ax.set_xticks(x)
    ax.set_xticklabels(region_stats.index)
    ax.legend()

    # Добавление значений на столбцы
    for bar in bars1:
        height = bar.get_height()
        ax.annotate(f'{height}',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3),
                    textcoords="offset points",
                    ha='center', va='bottom')

    for bar in bars2:
        height = bar.get_height()
        ax.annotate(f'{height}',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3),
                    textcoords="offset points",
                    ha='center', va='bottom')

    plt.tight_layout()
    plt.savefig(f'{output_prefix}regions_comparison.png', dpi=300, bbox_inches='tight')
    plt.show()


def main_analysis():
    """Основная функция анализа"""

    # Загрузка данных
    df = load_and_prepare_data('pets_dataset_2025.csv')

    print("Первые 5 строк данных:")
    print(df.head())
    print(f"\nВсего записей: {len(df)}")

    # Анализ регионов
    region_stats = analyze_regions(df)

    print("\nСтатистика по регионам (с группировкой):")
    print(region_stats)

    # Создание таблицы с топ-10 регионами
    top_regions = create_regions_table(df)

    # Создание визуализаций
    create_visualizations(region_stats)

    # Дополнительная информация
    print(f"\nОбщее количество заявок: {region_stats['общее_количество'].sum()}")
    print(f"Общее количество найденных животных: {region_stats['найдено_количество'].sum()}")
    print(f"Средний процент найденных по регионам: {region_stats['процент_найденных'].mean():.2f}%")


if __name__ == "__main__":
    main_analysis()