import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from scipy import stats
import warnings
import os

warnings.filterwarnings('ignore')


def load_data(file_path):
    """Загрузка данных"""
    try:
        if not os.path.exists(file_path):
            print(f"ОШИБКА: Файл {file_path} не найден!")
            return None

        encodings = ['utf-8', 'cp1251', 'latin1']
        df = None

        for encoding in encodings:
            try:
                df = pd.read_csv(file_path, encoding=encoding)
                print(f"Файл успешно загружен с кодировкой {encoding}")
                break
            except UnicodeDecodeError:
                continue

        if df is None:
            print("ОШИБКА: Не удалось загрузить файл")
            return None

        print(f"Загружено записей: {len(df)}")
        return df

    except Exception as e:
        print(f"ОШИБКА при загрузке данных: {e}")
        return None


def analyze_publication_factors(df):
    """Анализ влияния фото и описания на успешность"""

    df_analysis = df.copy()

    # Создаем бинарную переменную успеха
    df_analysis['успех'] = 0
    df_analysis.loc[
        ((df_analysis['тип_объявления'] == 'потерян') & (df_analysis['статус_поиска'] == 'найден')) |
        ((df_analysis['тип_объявления'] == 'найден') & (df_analysis['статус_поиска'] == 'хозяин найден')),
        'успех'
    ] = 1

    # Преобразуем есть_фото в числовой формат
    df_analysis['есть_фото_num'] = df_analysis['есть_фото'].map({'да': 1, 'нет': 0})

    print("=" * 60)
    print("АНАЛИЗ ВЛИЯНИЯ ФОТО И ОПИСАНИЯ НА УСПЕШНОСТЬ")
    print("=" * 60)

    # Базовая статистика
    print(f"Всего объявлений: {len(df_analysis)}")
    print(f"Объявления с фото: {df_analysis['есть_фото_num'].sum()} ({df_analysis['есть_фото_num'].mean() * 100:.1f}%)")
    print(f"Среднее количество фото: {df_analysis['количество_фото'].mean():.2f}")
    print(f"Средняя длина описания: {df_analysis['длина_описания'].mean():.2f}")

    # Анализ по наличию фото
    photo_success = df_analysis.groupby('есть_фото_num')['успех'].agg(['mean', 'count'])
    print("\nУспешность по наличию фото:")
    print(photo_success)

    # Анализ корреляций
    photo_corr = df_analysis['есть_фото_num'].corr(df_analysis['успех'])
    photos_count_corr = df_analysis['количество_фото'].corr(df_analysis['успех'])
    desc_length_corr = df_analysis['длина_описания'].corr(df_analysis['успех'])

    print(f"\nКорреляции с успехом:")
    print(f"Наличие фото: {photo_corr:.3f}")
    print(f"Количество фото: {photos_count_corr:.3f}")
    print(f"Длина описания: {desc_length_corr:.3f}")

    return df_analysis, photo_success, photo_corr, photos_count_corr, desc_length_corr


def create_photo_success_chart(photo_success):
    """Создание диаграммы успешности по наличию фото"""

    plt.figure(figsize=(8, 6))

    categories = ['Без фото', 'С фото']

    # Проверяем на NaN и заменяем на 0
    success_rates = [
        (photo_success.loc[0, 'mean'] * 100) if 0 in photo_success.index else 0,
        (photo_success.loc[1, 'mean'] * 100) if 1 in photo_success.index else 0
    ]

    bars = plt.bar(categories, success_rates, color=['lightcoral', 'lightgreen'], alpha=0.7, width=0.6)
    plt.title('Успешность поиска по наличию фото', fontsize=14, fontweight='bold')
    plt.ylabel('Доля успешных поисков (%)')
    plt.grid(True, alpha=0.3, axis='y')

    # Добавление значений на столбцы
    for bar, rate in zip(bars, success_rates):
        plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                 f'{rate:.1f}%', ha='center', va='bottom', fontsize=12, fontweight='bold')

    plt.tight_layout()
    plt.savefig('photo_success_analysis.png', dpi=300, bbox_inches='tight')
    plt.show()


def create_photos_count_chart(df_analysis):
    """Создание диаграммы успешности по количеству фото"""

    # Создаем группы по количеству фото
    df_analysis['группа_фото'] = pd.cut(df_analysis['количество_фото'],
                                        bins=[-1, 0, 1, 3, 10, 100],
                                        labels=['0 фото', '1 фото', '2-3 фото', '4-10 фото', '10+ фото'])

    photos_success = df_analysis.groupby('группа_фото')['успех'].mean() * 100

    # Заменяем NaN на 0
    photos_success = photos_success.fillna(0)

    plt.figure(figsize=(10, 6))

    bars = plt.bar(range(len(photos_success)), photos_success.values,
                   color='skyblue', alpha=0.7, width=0.6)
    plt.title('Успешность поиска по количеству фото', fontsize=14, fontweight='bold')
    plt.xlabel('Количество фото')
    plt.ylabel('Доля успешных поисков (%)')
    plt.xticks(range(len(photos_success)), photos_success.index, rotation=45)
    plt.grid(True, alpha=0.3, axis='y')

    # Добавление значений на столбцы
    for bar, value in zip(bars, photos_success.values):
        plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                 f'{value:.1f}%', ha='center', va='bottom', fontsize=11, fontweight='bold')

    plt.tight_layout()
    plt.savefig('photos_count_analysis.png', dpi=300, bbox_inches='tight')
    plt.show()

    return photos_success


def create_description_length_chart(df_analysis):
    """Создание диаграммы успешности по длине описания"""

    # Создаем группы по длине описания (количество слов)
    # Определяем границы групп на основе квартилей
    desc_stats = df_analysis['длина_описания'].describe()

    # Создаем группы на основе квартилей
    q1 = desc_stats['25%']
    q2 = desc_stats['50%']
    q3 = desc_stats['75%']

    bins = [-1, q1, q2, q3, df_analysis['длина_описания'].max()]
    labels = [f'0-{int(q1)} слов', f'{int(q1) + 1}-{int(q2)} слов',
              f'{int(q2) + 1}-{int(q3)} слов', f'{int(q3) + 1}+ слов']

    df_analysis['группа_описания'] = pd.cut(df_analysis['длина_описания'],
                                            bins=bins,
                                            labels=labels)

    desc_success = df_analysis.groupby('группа_описания')['успех'].mean() * 100

    # Заменяем NaN на 0
    desc_success = desc_success.fillna(0)

    plt.figure(figsize=(10, 6))

    bars = plt.bar(range(len(desc_success)), desc_success.values,
                   color='lightseagreen', alpha=0.7, width=0.6)
    plt.title('Успешность поиска по длине описания', fontsize=14, fontweight='bold')
    plt.xlabel('Длина описания (количество слов)')
    plt.ylabel('Доля успешных поисков (%)')
    plt.xticks(range(len(desc_success)), desc_success.index, rotation=45)
    plt.grid(True, alpha=0.3, axis='y')

    # Добавление значений на столбцы
    for bar, value in zip(bars, desc_success.values):
        plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                 f'{value:.1f}%', ha='center', va='bottom', fontsize=11, fontweight='bold')

    plt.tight_layout()
    plt.savefig('description_length_analysis.png', dpi=300, bbox_inches='tight')
    plt.show()

    return desc_success


def create_combined_factors_chart(df_analysis):
    """Создание диаграммы успешности по комбинации факторов (фото + описание)"""

    # Создаем комбинированные группы на основе количества фото и длины описания
    # Определяем медиану длины описания для разделения на "короткие" и "длинные" описания
    median_desc = df_analysis['длина_описания'].median()

    # Определяем пороги для количества фото
    conditions = [
        (df_analysis['количество_фото'] == 0) & (df_analysis['длина_описания'] <= median_desc),
        (df_analysis['количество_фото'] == 0) & (df_analysis['длина_описания'] > median_desc),
        (df_analysis['количество_фото'] == 1) & (df_analysis['длина_описания'] <= median_desc),
        (df_analysis['количество_фото'] == 1) & (df_analysis['длина_описания'] > median_desc),
        (df_analysis['количество_фото'] >= 2) & (df_analysis['длина_описания'] <= median_desc),
        (df_analysis['количество_фото'] >= 2) & (df_analysis['длина_описания'] > median_desc)
    ]

    choices = [
        f'0 фото, ≤{int(median_desc)} слов',
        f'0 фото, >{int(median_desc)} слов',
        f'1 фото, ≤{int(median_desc)} слов',
        f'1 фото, >{int(median_desc)} слов',
        f'2+ фото, ≤{int(median_desc)} слов',
        f'2+ фото, >{int(median_desc)} слов'
    ]

    df_analysis['комбинированная_группа'] = np.select(conditions, choices, default='Другое')

    combined_success = df_analysis.groupby('комбинированная_группа')['успех'].agg(['mean', 'count'])
    combined_success = combined_success.sort_values('mean', ascending=False)

    # Заменяем NaN на 0
    combined_success['mean'] = combined_success['mean'].fillna(0) * 100

    plt.figure(figsize=(12, 6))

    colors = ['lightcoral', 'lightcoral', 'orange', 'orange', 'lightgreen', 'lightgreen']
    bars = plt.bar(range(len(combined_success)), combined_success['mean'],
                   color=colors[:len(combined_success)], alpha=0.7, width=0.6)

    plt.title('Успешность поиска по комбинации факторов\n(количество фото + длина описания)', fontsize=14,
              fontweight='bold')
    plt.xlabel('Комбинация факторов')
    plt.ylabel('Доля успешных поисков (%)')
    plt.xticks(range(len(combined_success)), combined_success.index, rotation=45, ha='right')
    plt.grid(True, alpha=0.3, axis='y')

    # Добавление значений и количества наблюдений
    for i, (bar, (group, row)) in enumerate(zip(bars, combined_success.iterrows())):
        plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                 f'{row["mean"]:.1f}%', ha='center', va='bottom', fontsize=10, fontweight='bold')

    # Добавление легенды для цветов
    plt.figtext(0.15, 0.02, 'Цвета: красный - 0 фото, оранжевый - 1 фото, зеленый - 2+ фото',
                fontsize=10, style='italic')

    plt.tight_layout()
    plt.subplots_adjust(bottom=0.15)
    plt.savefig('combined_factors_analysis.png', dpi=300, bbox_inches='tight')
    plt.show()

    return combined_success


def main_publication_analysis():
    """Основная функция анализа типов публикаций"""

    print("Анализ влияния фото и описания на успешность поиска...")
    print("=" * 50)

    # Загрузка данных
    file_path = 'pets_dataset_2025.csv'
    df = load_data(file_path)

    if df is None:
        return

    # Анализ факторов публикации
    df_analysis, photo_success, photo_corr, photos_count_corr, desc_length_corr = analyze_publication_factors(df)

    # Создание четырех диаграмм
    print("\nСоздание диаграмм...")
    create_photo_success_chart(photo_success)
    photos_success = create_photos_count_chart(df_analysis)
    desc_success = create_description_length_chart(df_analysis)
    combined_success = create_combined_factors_chart(df_analysis)

    # Вывод результатов
    print("\n" + "=" * 60)
    print("РЕЗУЛЬТАТЫ АНАЛИЗА")
    print("=" * 60)

    success_with_photo = (photo_success.loc[1, 'mean'] * 100) if 1 in photo_success.index else 0
    success_without_photo = (photo_success.loc[0, 'mean'] * 100) if 0 in photo_success.index else 0

    print(f"• Успешность с фото: {success_with_photo:.1f}%")
    print(f"• Успешность без фото: {success_without_photo:.1f}%")
    print(f"• Корреляция наличия фото с успехом: {photo_corr:.3f}")
    print(f"• Корреляция количества фото с успехом: {photos_count_corr:.3f}")
    print(f"• Корреляция длины описания с успехом: {desc_length_corr:.3f}")

    if not photos_success.empty:
        best_photos_group = photos_success.idxmax()
        best_photos_rate = photos_success.max()
        print(f"• Лучшая группа по фото: {best_photos_group} ({best_photos_rate:.1f}% успеха)")

    if not desc_success.empty:
        best_desc_group = desc_success.idxmax()
        best_desc_rate = desc_success.max()
        print(f"• Лучшая группа по описанию: {best_desc_group} ({best_desc_rate:.1f}% успеха)")

    if not combined_success.empty:
        best_combination = combined_success.index[0]
        best_rate = combined_success.iloc[0]['mean']
        print(f"• Лучшая комбинация факторов: {best_combination} ({best_rate:.1f}% успеха)")


if __name__ == "__main__":
    main_publication_analysis()