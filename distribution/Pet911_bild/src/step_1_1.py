from .deps import *



def load_and_prepare_data(file_path, dataset_type):
    """Загрузка и подготовка данных для lost или found датасета"""
    df = pd.read_csv(file_path)

    # Преобразование даты
    df['дата_публикации'] = pd.to_datetime(df['дата_публикации'], format='%a, %d.%m.%Y', errors='coerce')

    # Заполнение пропущенных регионов
    df['регион'] = df['регион'].fillna('Неизвестно')

    # Создание флага "найдено" в зависимости от типа датасета
    if dataset_type == 'lost':
        df['найдено'] = df['статус'] == 'питомец найден'
    elif dataset_type == 'found':
        df['найдено'] = df['статус'] == 'хозяин найден'

    return df


def analyze_regions(df, top_regions_count=5):
    """Анализ региональной статистики с группировкой по топ-N регионов"""

    # Группировка по регионам
    region_stats = df.groupby('регион').agg({
        'id': 'count',  # общее количество заявок
        'найдено': 'sum'  # количество найденных
    }).rename(columns={'id': 'общее_количество', 'найдено': 'найдено_количество'})

    # Расчет процента найденных
    region_stats['процент_найденных'] = (
            region_stats['найдено_количество'] / region_stats['общее_количество'] * 100
    ).round(2)

    # Сортировка по общему количеству заявок
    region_stats_sorted = region_stats.sort_values('общее_количество', ascending=False)

    # Группировка для визуализации: топ-N регионов + остальные как "Другие"
    if len(region_stats_sorted) > top_regions_count:
        top_regions = region_stats_sorted.head(top_regions_count)
        other_regions = region_stats_sorted.iloc[top_regions_count:]

        other_total = other_regions['общее_количество'].sum()
        other_found = other_regions['найдено_количество'].sum()
        other_percent = (other_found / other_total * 100) if other_total > 0 else 0

        # Создаем Series для "Другие"
        other_series = pd.Series({
            'общее_количество': other_total,
            'найдено_количество': other_found,
            'процент_найденных': round(other_percent, 2)
        }, name='Другие')

        # Объединяем топ регионы и "Другие"
        final_stats = pd.concat([top_regions, other_series.to_frame().T])
    else:
        final_stats = region_stats_sorted

    return final_stats, region_stats


def create_regions_table(region_stats_full, dataset_type, top_regions_count=5, output_prefix=''):
    """Создание таблицы с топ-10 регионов по проценту найденных"""

    # Фильтруем регионы с достаточным количеством заявок (минимум 5)
    filtered_stats = region_stats_full[region_stats_full['общее_количество'] >= 5]

    # Сортировка по проценту найденных (по убыванию)
    top_regions = filtered_stats.sort_values('процент_найденных', ascending=False).head(10)

    # Создаем таблицу
    fig, ax = plt.subplots(figsize=(14, 8))
    ax.axis('tight')
    ax.axis('off')

    # Подготовка данных для таблицы
    table_data = []
    for region, row in top_regions.iterrows():
        table_data.append([
            region,
            row['общее_количество'],
            row['найдено_количество'],
            f"{row['процент_найденных']}%"
        ])

    # Создание таблицы
    table = ax.table(
        cellText=table_data,
        colLabels=['Регион', 'Всего заявок', 'Найдено', 'Процент найденных'],
        cellLoc='center',
        loc='center',
        bbox=[0.1, 0.1, 0.8, 0.8]
    )

    # Стилизация таблицы
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1.2, 1.8)

    # Заголовок строк
    for i in range(len(table_data) + 1):
        for j in range(4):
            if i == 0:  # Заголовок
                table[(i, j)].set_facecolor('#4CAF50')
                table[(i, j)].set_text_props(weight='bold', color='white')
            else:  # Данные
                table[(i, j)].set_facecolor('#f0f0f0')

    title_map = {
        'lost': 'поиска питомцев',
        'found': 'поиска хозяев'
    }

    dataset_title = title_map[dataset_type]

    plt.title(f'Топ-10 регионов по проценту успешных случаев {dataset_title}',
              fontsize=14, fontweight='bold', pad=20)

    # Добавляем пояснение в окошке внизу слева
    explanation = "За 100% принято общее количество заявок в регионе"
    plt.figtext(0.02, 0.02, explanation, fontsize=10, style='italic',
                bbox={'facecolor': 'lightgray', 'alpha': 0.7, 'pad': 5})

    plt.tight_layout()
    plt.savefig(f'results/Результаты 1 главы анализа/1.1.1 Топ-10 регионов по проценту успешных случаев для {output_prefix}.png', dpi=300, bbox_inches='tight')
    plt.close()

    return top_regions


def create_visualizations(region_stats, dataset_type, top_regions_count=5, output_prefix=''):
    """Создание визуализаций для анализа регионов"""

    title_map = {
        'lost': 'поиска питомцев',
        'found': 'поиска хозяев'
    }

    dataset_title = title_map[dataset_type]

    # 1. Горизонтальная гистограмма - регионы по общему количеству заявок
    fig, ax = plt.subplots(figsize=(12, 8))
    bars = ax.barh(region_stats.index, region_stats['общее_количество'])
    ax.set_xlabel('Количество заявок')
    ax.set_title(f'Распределение заявок по регионам ({dataset_title})')
    ax.grid(axis='x', alpha=0.3)

    # Добавление значений на столбцы
    for bar, value in zip(bars, region_stats['общее_количество']):
        ax.text(bar.get_width() + max(region_stats['общее_количество']) * 0.01,
                bar.get_y() + bar.get_height() / 2,
                f'{value}', va='center', ha='left', fontsize=10)

    # Добавляем пояснение про "Другие" в окошке внизу слева если нужно
    if 'Другие' in region_stats.index:
        explanation = f"Категория 'Другие' включает все регионы кроме топ-{top_regions_count} по количеству заявок"
        plt.figtext(0.02, 0.02, explanation, fontsize=10, style='italic',
                    bbox={'facecolor': 'lightgray', 'alpha': 0.7, 'pad': 5})

    plt.tight_layout()
    plt.savefig(f'results/Результаты 1 главы анализа/1.1.2. Распределение количества заявок по регионам для {output_prefix}.png', dpi=300, bbox_inches='tight')
    plt.close()

    # 2. Круговая диаграмма - распределение заявок по регионам
    fig, ax = plt.subplots(figsize=(12, 8))

    # Рассчитываем проценты для круговой диаграммы
    total_by_region = region_stats['общее_количество']
    total_requests = total_by_region.sum()

    percentages = (total_by_region / total_requests * 100).round(1)

    # Создаем круговую диаграмму
    colors = plt.cm.Set3(np.linspace(0, 1, len(percentages)))
    wedges, texts, autotexts = ax.pie(
        percentages.values,
        labels=percentages.index,
        autopct='%1.1f%%',
        colors=colors,
        startangle=90,
        textprops={'fontsize': 10}
    )

    # Улучшаем отображение текста
    for autotext in autotexts:
        autotext.set_color('black')
        autotext.set_fontweight('bold')

    ax.set_title(f'Распределение заявок по регионам ({dataset_title})',
                 fontsize=14)

    # Добавляем пояснение в окошке внизу слева
    explanation = f"За 100% принято общее количество заявок: {total_requests}"
    if 'Другие' in region_stats.index:
        explanation += f"\nКатегория 'Другие' включает все регионы кроме топ-{top_regions_count}"

    plt.figtext(0.02, 0.02, explanation, fontsize=10, style='italic',
                bbox={'facecolor': 'lightgray', 'alpha': 0.7, 'pad': 5})

    plt.tight_layout()
    plt.savefig(f'results/Результаты 1 главы анализа/1.1.3. Распределение количества заявок по регионам для {output_prefix} (Круговая диаграмма).png', dpi=300, bbox_inches='tight')
    plt.close()

    # 3. График эффективности регионов (процент найденных)
    fig, ax = plt.subplots(figsize=(12, 8))

    # Сортируем по проценту найденных для лучшего отображения
    region_stats_sorted_eff = region_stats.sort_values('процент_найденных', ascending=True)

    bars = ax.barh(region_stats_sorted_eff.index, region_stats_sorted_eff['процент_найденных'])
    ax.set_xlabel('Процент успешных случаев (%)')
    ax.set_title(f'Эффективность {dataset_title} по регионам', fontsize=14)
    ax.grid(axis='x', alpha=0.3)

    # Добавление значений на столбцы
    for bar, value in zip(bars, region_stats_sorted_eff['процент_найденных']):
        ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height() / 2,
                f'{value}%', va='center', ha='left', fontsize=10)

    # Добавляем пояснение в окошке внизу слева
    explanation = "За 100% принято общее количество заявок в регионе"
    if 'Другие' in region_stats.index:
        explanation += f"\nКатегория 'Другие' включает все регионы кроме топ-{top_regions_count}"

    plt.figtext(0.02, 0.02, explanation, fontsize=10, style='italic',
                bbox={'facecolor': 'lightgray', 'alpha': 0.7, 'pad': 5})

    plt.tight_layout()
    plt.savefig(f'results/Результаты 1 главы анализа/1.1.4. Процент успешных случаев поиска по регионам для {output_prefix}.png', dpi=300, bbox_inches='tight')
    plt.close()

    # 4. Столбчатая диаграмма - сравнение абсолютных чисел
    fig, ax = plt.subplots(figsize=(12, 8))

    x = np.arange(len(region_stats))
    width = 0.35

    bars1 = ax.bar(x - width / 2, region_stats['общее_количество'], width,
                   label='Все заявки', alpha=0.8, color='lightblue')
    bars2 = ax.bar(x + width / 2, region_stats['найдено_количество'], width,
                   label='Успешные случаи', alpha=0.8, color='orange')

    ax.set_xlabel('Регионы')
    ax.set_ylabel('Количество')
    ax.set_title(f'Сравнение общего числа заявок и успешных случаев по регионам ({dataset_title})')
    ax.set_xticks(x)
    ax.set_xticklabels(region_stats.index, rotation=45, ha='right')

    # Добавляем обычную легенду для столбцов
    ax.legend(loc='upper right', fontsize=10)

    # Добавление значений на столбцы
    for bar in bars1:
        height = bar.get_height()
        ax.annotate(f'{height}',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3),
                    textcoords="offset points",
                    ha='center', va='bottom', fontsize=9)

    for bar in bars2:
        height = bar.get_height()
        ax.annotate(f'{height}',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3),
                    textcoords="offset points",
                    ha='center', va='bottom', fontsize=9)

    # Добавляем пояснение в окошке внизу слева
    explanation = "Проценты успешных случаев рассчитываются от общего количества заявок в регионе"
    if 'Другие' in region_stats.index:
        explanation += f"\nКатегория 'Другие' включает все регионы кроме топ-{top_regions_count}"

    plt.figtext(0.02, 0.02, explanation, fontsize=10, style='italic',
                bbox={'facecolor': 'lightgray', 'alpha': 0.7, 'pad': 5})

    plt.tight_layout()
    plt.savefig(f'results/Результаты 1 главы анализа/1.1.5. Сравнение общего количества заявок и успешных случаев по регионам для {output_prefix}.png', dpi=300, bbox_inches='tight')
    plt.close()


def analyze_dataset(file_path, dataset_type, top_regions_count=5):
    """Полный анализ для одного датасета (без вывода в консоль)"""

    # Загрузка данных
    df = load_and_prepare_data(file_path, dataset_type)

    # Анализ регионов
    region_stats_viz, region_stats_full = analyze_regions(df, top_regions_count)

    # Создание таблицы с топ-10 регионами
    top_regions = create_regions_table(region_stats_full, dataset_type, top_regions_count,
                                       output_prefix=f'{dataset_type}')

    # Создание визуализаций
    create_visualizations(region_stats_viz, dataset_type, top_regions_count, output_prefix=f'{dataset_type}')

    return df, region_stats_viz, region_stats_full


def step_1_1():
    """Основная функция анализа для обоих датасетов (без вывода в консоль)"""

        # Настройка отображения
    plt.style.use('default')
    sns.set_palette("husl")
    
    # Создаем папку для результатов
    os.makedirs('results/Результаты 1 главы анализа', exist_ok=True)

    # Анализ для lost датасета (поиск питомцев)
    df_lost, stats_lost_viz, stats_lost_full = analyze_dataset(
        'data/Dataset_final_Pet911_lost.csv', 'lost', top_regions_count=5
    )

    # Анализ для found датасета (поиск хозяев)
    df_found, stats_found_viz, stats_found_full = analyze_dataset(
        'data/dataset_final_Pet911_found.csv', 'found', top_regions_count=5
    )
