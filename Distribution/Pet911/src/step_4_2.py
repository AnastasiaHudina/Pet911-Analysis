from .deps import *



def create_directories():
    """
    Создает структуру папок для результатов.
    """
    base_dir = "results/Результаты 4 главы анализа"
    clustering_dir = os.path.join(base_dir, "4.2. Результаты кластеризации")
    
    # Создаем папки, если они не существуют
    os.makedirs(base_dir, exist_ok=True)
    os.makedirs(clustering_dir, exist_ok=True)
    
    
    return base_dir, clustering_dir

def load_and_prepare_data(lost_file, found_file):
    """
    Загружает данные из двух файлов и объединяет их.
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
    
    return df_combined

def create_clustering_features(df):
    """
    Создает признаки для кластеризации на основе качества оформления заявок.
    """
    print("\nСоздание признаков для кластеризации...")
    
    # 1. Количество фото (прямой признак)
    df['количество_фото_норм'] = df['количество_фото'].fillna(0)
    
    # 2. Длина описания (прямой признак)
    df['длина_описания_норм'] = df['Длина_описания_в_словах'].fillna(0)
    
    # 3. Полнота заполнения (вычисляем процент заполненных ключевых полей)
    key_columns = ['тип_животного', 'порода', 'пол', 'возраст', 'окрас', 'место события']
    
    def calculate_completeness(row):
        filled = 0
        total = len(key_columns)
        
        for col in key_columns:
            if (col in row and 
                pd.notna(row[col]) and 
                str(row[col]).strip() not in ['', 'Неизвестно', 'Unknown']):
                filled += 1
        
        return filled / total if total > 0 else 0
    
    df['полнота_заполнения'] = df.apply(calculate_completeness, axis=1)
    
    # 4. Скорость публикации (разница между датой события и публикации)
    def parse_date(date_str):
        """Парсит дату из формата 'вс, 12.10.2025'"""
        try:
            if pd.isna(date_str):
                return None
            # Убираем день недели и лишние пробелы
            date_part = str(date_str).split(',')[-1].strip()
            return datetime.strptime(date_part, '%d.%m.%Y')
        except:
            return None
    
    # Парсим даты
    df['дата_публикации_парс'] = df['дата_публикации'].apply(parse_date)
    
    # Определяем столбец с датой события в зависимости от типа объявления
    def get_event_date(row):
        if row['объявление_тип'] == 'lost':
            return parse_date(row['дата пропажи'])
        else:
            return parse_date(row['дата находки'])
    
    df['дата_события_парс'] = df.apply(get_event_date, axis=1)
    
    # Вычисляем разницу в днях
    def calculate_time_diff(row):
        if pd.isna(row['дата_публикации_парс']) or pd.isna(row['дата_события_парс']):
            return 0
        diff = (row['дата_публикации_парс'] - row['дата_события_парс']).days
        return max(0, diff)  # Отрицательные значения не имеют смысла
    
    df['скорость_публикации_дни'] = df.apply(calculate_time_diff, axis=1)
    
    # 5. Активность обсуждения
    df['активность_обсуждения'] = df['количество_комментариев'].fillna(0)
    
    # Создаем финальный датафрейм для кластеризации
    clustering_features = df[[
        'количество_фото_норм', 'длина_описания_норм', 'полнота_заполнения',
        'скорость_публикации_дни', 'активность_обсуждения'
    ]].copy()
    
    # Заполняем пропуски
    clustering_features = clustering_features.fillna(0)
    
    print("Статистика признаков для кластеризации:")
    print(clustering_features.describe().round(2))
    
    return clustering_features, df

def find_optimal_clusters(features_scaled, clustering_dir):
    """
    Находит оптимальное количество кластеров.
    """
    print("\nПоиск оптимального количества кластеров...")
    
    silhouette_scores = []
    wcss = []  # Within-Cluster Sum of Square
    k_range = range(2, 8)
    
    for k in k_range:
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        cluster_labels = kmeans.fit_predict(features_scaled)
        
        silhouette_scores.append(silhouette_score(features_scaled, cluster_labels))
        wcss.append(kmeans.inertia_)
    
    # Визуализация выбора k
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 5))
    
    # Elbow method
    ax1.plot(k_range, wcss, 'bo-', linewidth=2, markersize=8)
    ax1.set_xlabel('Количество кластеров')
    ax1.set_ylabel('WCSS (Within-Cluster Sum of Square)')
    ax1.set_title('Elbow Method')
    ax1.grid(True, alpha=0.3)
    
    # Silhouette score
    ax2.plot(k_range, silhouette_scores, 'ro-', linewidth=2, markersize=8)
    ax2.set_xlabel('Количество кластеров')
    ax2.set_ylabel('Silhouette Score')
    ax2.set_title('Silhouette Analysis')
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Сохраняем в папку кластеризации
    output_path = os.path.join('results/Результаты 4 главы анализа/4.2.1. Оптимальное количество кластеров.png')
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    # Выбираем k=4 согласно требованиям
    optimal_k = 4
    print(f"Выбрано количество кластеров: {optimal_k}")
    
    return optimal_k

def perform_clustering(features_scaled, optimal_k):
    """
    Выполняет кластеризацию K-means.
    """
    print(f"\nВыполнение кластеризации с {optimal_k} кластерами...")
    
    kmeans = KMeans(n_clusters=optimal_k, random_state=42, n_init=10)
    cluster_labels = kmeans.fit_predict(features_scaled)
    
    silhouette_avg = silhouette_score(features_scaled, cluster_labels)
    print(f"Средний silhouette score: {silhouette_avg:.3f}")
    
    return cluster_labels, kmeans

def visualize_clusters_2d(features_scaled, cluster_labels, feature_names, clustering_dir):
    """
    Визуализирует кластеры в 2D пространстве с помощью PCA.
    """
    print("\nВизуализация кластеров в 2D...")
    
    # Применяем PCA для визуализации в 2D
    pca = PCA(n_components=2, random_state=42)
    features_2d = pca.fit_transform(features_scaled)
    
    # Создаем красивую визуализацию
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 8))
    
    # 1. Базовая визуализация кластеров
    scatter1 = ax1.scatter(features_2d[:, 0], features_2d[:, 1], 
                          c=cluster_labels, cmap='viridis', alpha=0.7, s=50)
    ax1.set_xlabel('Главная компонента 1')
    ax1.set_ylabel('Главная компонента 2')
    ax1.set_title('Визуализация кластеров (PCA)\nРазделение объявлений по качеству оформления')
    ax1.grid(True, alpha=0.3)
    
    # Добавляем объяснение компонент
    explained_var = pca.explained_variance_ratio_
    ax1.text(0.02, 0.98, f'Объясненная дисперсия:\nPC1: {explained_var[0]:.1%}\nPC2: {explained_var[1]:.1%}', 
             transform=ax1.transAxes, verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    # 2. Улучшенная визуализация с центроидами
    unique_clusters = np.unique(cluster_labels)
    colors = plt.cm.viridis(np.linspace(0, 1, len(unique_clusters)))
    
    for i, cluster_id in enumerate(unique_clusters):
        cluster_points = features_2d[cluster_labels == cluster_id]
        ax2.scatter(cluster_points[:, 0], cluster_points[:, 1], 
                   c=[colors[i]], label=f'Кластер {cluster_id}', alpha=0.7, s=50)
        
        # Центроид кластера
        centroid = cluster_points.mean(axis=0)
        ax2.scatter(centroid[0], centroid[1], marker='*', s=300, 
                   c=[colors[i]], edgecolors='black', linewidth=2)
    
    ax2.set_xlabel('Главная компонента 1')
    ax2.set_ylabel('Главная компонента 2')
    ax2.set_title('Кластеры с центроидами')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Сохраняем в папку кластеризации
    output_path = os.path.join('results/Результаты 4 главы анализа/4.2.2. Визуализация кластеров.png')
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    return features_2d

def create_cluster_profiles(df, cluster_labels, feature_names):
    """
    Создает профили кластеров и интерпретирует их.
    """
    print("\nСоздание профилей кластеров...")
    
    # Добавляем метки кластеров в исходный датафрейм
    df_result = df.copy()
    df_result['cluster'] = cluster_labels
    
    # Анализ средних значений по кластерам
    cluster_analysis = df_result.groupby('cluster').agg({
        'количество_фото_норм': 'mean',
        'длина_описания_норм': 'mean',
        'полнота_заполнения': 'mean',
        'скорость_публикации_дни': 'mean',
        'активность_обсуждения': 'mean',
        'is_success': 'mean',
        'id': 'count'
    }).round(3)
    
    cluster_analysis.columns = [
        'Ср_фото', 'Ср_длина_описания', 'Ср_полнота', 
        'Ср_скорость_публикации', 'Ср_активность', 'Доля_успеха', 'Размер_кластера'
    ]
    
    # Интерпретация кластеров согласно заданным названиям
    cluster_names = {
        0: "Минимальные анкеты",
        1: "Средние анкеты", 
        2: "Полные анкеты",
        3: "Идеальные анкеты"
    }
    
    # Сортируем кластеры по качеству (сумме ключевых признаков)
    quality_scores = (
        cluster_analysis['Ср_фото'] + 
        cluster_analysis['Ср_длина_описания'] + 
        cluster_analysis['Ср_полнота']
    )
    
    # Присваиваем названия в порядке качества
    sorted_clusters = quality_scores.sort_values().index
    for i, cluster_id in enumerate(sorted_clusters):
        if i == 0:
            cluster_names[cluster_id] = "Минимальные анкеты"
        elif i == 1:
            cluster_names[cluster_id] = "Средние анкеты"
        elif i == 2:
            cluster_names[cluster_id] = "Полные анкеты"
        else:
            cluster_names[cluster_id] = "Идеальные анкеты"
    
    cluster_analysis['Название'] = [cluster_names.get(i, 'Неизвестно') for i in cluster_analysis.index]
    
    print("\nХАРАКТЕРИСТИКИ КЛАСТЕРОВ:")
    print(cluster_analysis)
    
    return df_result, cluster_analysis, cluster_names

def visualize_cluster_profiles(cluster_analysis, cluster_names, clustering_dir):
    """
    Визуализирует профили кластеров.
    """
    print("\nВизуализация профилей кластеров...")
    
    # 1. Radar chart для сравнения кластеров
    fig, axes = plt.subplots(2, 2, figsize=(20, 16))
    
    # Признаки для radar chart (исключаем размер и успешность)
    radar_features = ['Ср_фото', 'Ср_длина_описания', 'Ср_полнота', 
                     'Ср_скорость_публикации', 'Ср_активность']
    n_features = len(radar_features)
    
    # Углы для radar chart
    angles = np.linspace(0, 2 * np.pi, n_features, endpoint=False).tolist()
    angles += angles[:1]  # Замыкаем круг
    
    # Нормализуем данные для radar chart
    normalized_data = cluster_analysis[radar_features].copy()
    for feature in radar_features:
        max_val = normalized_data[feature].max()
        if max_val > 0:
            normalized_data[feature] = normalized_data[feature] / max_val
    
    # Создаем radar chart для каждого кластера
    colors = ['red', 'orange', 'lightgreen', 'darkgreen']
    
    for idx, (cluster_id, row) in enumerate(cluster_analysis.iterrows()):
        ax = axes[idx // 2, idx % 2]
        
        values = normalized_data.loc[cluster_id].values.tolist()
        values += values[:1]  # Замыкаем круг
        
        ax.plot(angles, values, 'o-', linewidth=2, color=colors[idx], label=cluster_names[cluster_id])
        ax.fill(angles, values, alpha=0.25, color=colors[idx])
        
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(['Фото', 'Описание', 'Полнота', 'Скорость', 'Активность'])
        ax.set_ylim(0, 1)
        ax.set_title(f'{cluster_names[cluster_id]}\n(Успешность: {row["Доля_успеха"]:.1%})', 
                    fontsize=14, fontweight='bold')
        ax.grid(True)
    
    plt.tight_layout()
    
    # Сохраняем radar chart
    radar_path = os.path.join('results/Результаты 4 главы анализа/4.2.3. Средние значения данных анкет внутри кластеров.png')
    plt.savefig(radar_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    # 2. Bar plot сравнения успешности
    plt.figure(figsize=(12, 6))
    success_data = cluster_analysis[['Доля_успеха', 'Название']].sort_values('Доля_успеха')
    
    bars = plt.bar(range(len(success_data)), success_data['Доля_успеха'], 
                  color=['red', 'orange', 'lightgreen', 'darkgreen'])
    plt.xlabel('Тип анкеты')
    plt.ylabel('Доля успешных случаев')
    plt.title('Эффективность разных типов анкет')
    plt.xticks(range(len(success_data)), success_data['Название'], rotation=45)
    
    # Добавляем значения на столбцы
    for bar, value in zip(bars, success_data['Доля_успеха']):
        plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01, 
                f'{value:.1%}', ha='center', va='bottom', fontweight='bold')
    
    plt.grid(True, alpha=0.3, axis='y')
    plt.tight_layout()
    
    # Сохраняем bar plot
    bar_path = os.path.join('results/Результаты 4 главы анализа/4.2.4. Успешность поиска по типам кластеров.png')
    plt.savefig(bar_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    # 3. Heatmap характеристик кластеров
    plt.figure(figsize=(12, 8))
    
    # Подготовка данных для heatmap
    heatmap_data = cluster_analysis[radar_features].copy()
    heatmap_data['Размер'] = cluster_analysis['Размер_кластера']
    heatmap_data['Успешность'] = cluster_analysis['Доля_успеха']
    
    # Нормализуем для heatmap (кроме успешности)
    for feature in radar_features + ['Размер']:
        max_val = heatmap_data[feature].max()
        if max_val > 0:
            heatmap_data[feature] = heatmap_data[feature] / max_val
    
    sns.heatmap(heatmap_data.T, annot=True, cmap='YlOrRd', 
                fmt='.2f', linewidths=1, cbar_kws={'label': 'Нормализованное значение'})
    plt.title('Сравнение характеристик кластеров (Heatmap)')
    plt.tight_layout()
    
    # Сохраняем heatmap
    heatmap_path = os.path.join('results/Результаты 4 главы анализа/4.2.5. Тепловая карта кластеров.png')
    plt.savefig(heatmap_path, dpi=300, bbox_inches='tight')
    plt.close()

def print_cluster_insights(cluster_analysis, cluster_names):
    """
    Выводит ключевые инсайты по кластерам.
    """
    print("\n" + "="*80)
    print("КЛЮЧЕВЫЕ ИНСАЙТЫ КЛАСТЕРИЗАЦИИ")
    print("="*80)
    
    # Сортируем по успешности
    sorted_clusters = cluster_analysis.sort_values('Доля_успеха', ascending=False)
    
    for cluster_id, row in sorted_clusters.iterrows():
        name = cluster_names[cluster_id]
        success_rate = row['Доля_успеха']
        size = row['Размер_кластера']
        
        print(f"\n🎯 {name.upper()}")
        print(f"   Успешность: {success_rate:.1%} | Размер: {size} объявлений")
        print(f"   Характеристики:")
        print(f"   • Фото: {row['Ср_фото']:.1f} шт.")
        print(f"   • Длина описания: {row['Ср_длина_описания']:.0f} слов")
        print(f"   • Полнота: {row['Ср_полнота']:.0%}")
        print(f"   • Скорость публикации: {row['Ср_скорость_публикации']:.1f} дней")
        print(f"   • Активность: {row['Ср_активность']:.1f} комментариев")
    
    print(f"\n📊 ОБЩАЯ СТАТИСТИКА:")
    total_success = (cluster_analysis['Доля_успеха'] * cluster_analysis['Размер_кластера']).sum()
    total_ads = cluster_analysis['Размер_кластера'].sum()
    print(f"   Общая успешность: {total_success/total_ads:.1%}")
    print(f"   Распределение по кластерам:")
    for cluster_id, row in cluster_analysis.iterrows():
        percentage = row['Размер_кластера'] / total_ads * 100
        print(f"   • {cluster_names[cluster_id]}: {percentage:.1f}%")

def step_4_2():
    """
    Основная функция для кластеризации.
    """
    # Настройка отображения
    plt.rcParams['font.family'] = 'DejaVu Sans'
    plt.rcParams['font.size'] = 12
    sns.set_palette("husl")
    pd.set_option('display.max_columns', None)

    # Укажите пути к вашим файлам
    LOST_FILE = 'data/Dataset_final_Pet911_lost.csv'
    FOUND_FILE = 'data/dataset_final_Pet911_found.csv'
    
    try:
        print("=== КЛАСТЕРИЗАЦИЯ ПО КАЧЕСТВУ ОФОРМЛЕНИЯ АНКЕТ ===")
        
        # Создаем структуру папок
        base_dir, clustering_dir = create_directories()
        
        # 1. Загрузка и подготовка данных
        df = load_and_prepare_data(LOST_FILE, FOUND_FILE)
        clustering_features, df_with_features = create_clustering_features(df)
        
        # 2. Масштабирование признаков
        scaler = StandardScaler()
        features_scaled = scaler.fit_transform(clustering_features)
        feature_names = clustering_features.columns.tolist()
        
        # 3. Поиск оптимального количества кластеров
        optimal_k = find_optimal_clusters(features_scaled, clustering_dir)
        
        # 4. Выполнение кластеризации
        cluster_labels, kmeans_model = perform_clustering(features_scaled, optimal_k)
        
        # 5. Визуализация в 2D
        features_2d = visualize_clusters_2d(features_scaled, cluster_labels, feature_names, clustering_dir)
        
        # 6. Создание профилей кластеров
        df_result, cluster_analysis, cluster_names = create_cluster_profiles(
            df_with_features, cluster_labels, feature_names
        )
        
        # 7. Визуализация профилей
        visualize_cluster_profiles(cluster_analysis, cluster_names, clustering_dir)
        
        # 8. Вывод инсайтов
        print_cluster_insights(cluster_analysis, cluster_names)
        
        # 9. Сохранение результатов в соответствующие папки
        # CSV файлы сохраняем в папку кластеризации
        csv_result_path = os.path.join(clustering_dir, 'объявления_с_кластерами.csv')
        csv_analysis_path = os.path.join(clustering_dir, 'анализ_кластеров.csv')
        
        df_result.to_csv(csv_result_path, index=False, encoding='utf-8-sig')
        cluster_analysis.to_csv(csv_analysis_path, encoding='utf-8-sig')
        

        
        print(f"\n💡 Все файлы успешно сохранены в папку: 'results/Результаты 4 главы анализа'")
        
    except Exception as e:
        print(f"Произошла ошибка: {e}")
        import traceback
        traceback.print_exc()
