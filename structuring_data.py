import pandas as pd
import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import time
from random import uniform
import json


def create_unified_dataset():
    """Создает объединенный датасет из lost и found файлов"""

    # Загружаем оба файла
    try:
        lost_df = pd.read_csv('pet911_lost_pets_2025_detailed.csv', encoding='utf-8-sig')
        found_df = pd.read_csv('pet911_found_pets_2025_detailed.csv', encoding='utf-8-sig')

        # Добавляем тип объявления
        lost_df['ad_type'] = 'потерян'
        found_df['ad_type'] = 'найден'

        # Объединяем
        unified_df = pd.concat([lost_df, found_df], ignore_index=True)
        print(f"Объединено: {len(unified_df)} записей (потерян: {len(lost_df)}, найден: {len(found_df)})")

    except Exception as e:
        print(f"Ошибка загрузки: {e}")
        return None

    # Создаем структурированный датасет
    structured_data = []

    for index, row in unified_df.iterrows():
        print(f"Обрабатываю {index + 1}/{len(unified_df)}: {row['url'][:60]}...")

        record = {}

        # БАЗОВАЯ ИНФОРМАЦИЯ
        record['id'] = hash(row['url']) % 10 ** 8
        record['url'] = row['url']
        record['тип_объявления'] = row['ad_type']  # потерян/найден

        # ПАРСИМ ДОПОЛНИТЕЛЬНУЮ ИНФОРМАЦИЮ С СТРАНИЦЫ
        detailed_info = parse_additional_info(row['url'])

        # РЕГИОН И СТАТУС
        record['регион'] = detailed_info.get('region', 'не указано')
        record['статус_поиска'] = translate_status(row.get('status', ''))

        # ДАТА ПУБЛИКАЦИИ
        record['дата_публикации'] = detailed_info.get('publication_date', 'не указана')

        # ДАННЫЕ О ЖИВОТНОМ
        record['тип_животного'] = translate_animal_type(row.get('animal_type', ''))
        record['пол'] = detailed_info.get('gender', 'не указан')
        record['возраст'] = extract_age(row.get('age', ''))
        record['окрас'] = detailed_info.get('color', 'не указан')

        # ФОТО
        record['есть_фото'] = 'да' if detailed_info.get('has_photo', 0) else 'нет'
        record['количество_фото'] = detailed_info.get('photo_count', 0)

        # ОПИСАНИЕ И КОНТАКТЫ
        record['длина_описания'] = detailed_info.get('description_length', 0)  # количество слов в описании
        record['есть_контакты'] = 'да' if row.get('has_contacts', 0) else 'нет'
        record['количество_комментариев'] = detailed_info.get('comments_count', 0)

        structured_data.append(record)

        # Пауза между запросами
        time.sleep(uniform(1, 2))

    # Создаем финальный датасет
    final_df = pd.DataFrame(structured_data)

    # Сохраняем
    final_df.to_csv('pets_dataset_2025.csv', index=False, encoding='utf-8-sig')

    print(f"\nСоздан объединенный датасет: {len(final_df)} записей")
    print(f"Столбцы: {list(final_df.columns)}")

    # Статистика
    print(f"\nСТАТИСТИКА:")
    print(f"Объявлений 'Потерян': {len(final_df[final_df['тип_объявления'] == 'потерян'])}")
    print(f"Объявлений 'Найден': {len(final_df[final_df['тип_объявления'] == 'найден'])}")
    print(f"С фото: {len(final_df[final_df['есть_фото'] == 'да'])}")
    print(f"С контактами: {len(final_df[final_df['есть_контакты'] == 'да'])}")

    return final_df


def parse_additional_info(url):
    """Парсит дополнительную информацию с страницы объявления"""

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        time.sleep(uniform(1, 2))

        if response.status_code != 200:
            return {'has_photo': 0, 'photo_count': 0, 'comments_count': 0, 'gender': 'не указан', 'color': 'не указан',
                    'region': 'не указано', 'publication_date': 'не указана', 'description_length': 0}

        soup = BeautifulSoup(response.text, 'html.parser')

        result = {}

        # ПАРСИМ РЕГИОН - ищем в breadcrumbs
        region = 'не указано'

        # Ищем breadcrumbs
        breadcrumbs = soup.find('div', class_='breadcrumbs')
        if breadcrumbs:
            # Ищем все ссылки в breadcrumbs кроме первой (Pet911.ru)
            breadcrumb_links = breadcrumbs.find_all('a', class_='breadcrumbs__item')
            if len(breadcrumb_links) >= 2:
                # Второй элемент обычно содержит регион
                region_link = breadcrumb_links[1]
                region = region_link.get_text().strip()

        # Если не нашли в breadcrumbs, ищем в JSON-LD
        if region == 'не указано':
            script_tag = soup.find('script', type='application/ld+json')
            if script_tag:
                try:
                    # Парсим JSON для извлечения региона
                    json_data = json.loads(script_tag.string)
                    if 'itemListElement' in json_data:
                        for item in json_data['itemListElement']:
                            if item.get('position') == 2:  # Второй элемент обычно регион
                                region_name = item.get('name', '')
                                if region_name and region_name != 'Pet911.ru':
                                    region = region_name
                                    break
                except:
                    pass

        result['region'] = region

        # ПАРСИМ ФОТО - ищем слайдер с фото
        photo_count = 0
        has_photo = 0

        # Ищем карточку слайдера
        card_slider = soup.find('div', class_='card-slider')
        if card_slider:
            # Ищем все изображения в слайдере
            slider_images = card_slider.find_all('img', class_='img-crop')
            unique_photos = set()
            for img in slider_images:
                src = img.get('src', '')
                if src and 'cdn.pet911.ru' in src:
                    unique_photos.add(src)

            photo_count = len(unique_photos)
            has_photo = 1 if photo_count > 0 else 0

            # Если не нашли через слайдер, пробуем другой способ
            if photo_count == 0:
                # Ищем пагинацию слайдера
                pagination = card_slider.find('div', class_='card-slider__pagination')
                if pagination:
                    total_span = pagination.find('span', class_='swiper-pagination-total')
                    if total_span:
                        try:
                            photo_count = int(total_span.get_text().strip())
                            has_photo = 1 if photo_count > 0 else 0
                        except:
                            pass

        result['has_photo'] = has_photo
        result['photo_count'] = photo_count

        # ПАРСИМ КОММЕНТАРИИ - ищем заголовок с количеством комментариев
        comments_count = 0

        # Ищем заголовок раздела комментариев
        section_titles = soup.find_all(['div', 'h2'], string=re.compile(r'комментари[евй]+', re.IGNORECASE))
        for element in section_titles:
            text = element.get_text().lower()
            # Ищем числа в тексте "Комментариев 5"
            numbers = re.findall(r'\d+', text)
            if numbers:
                comments_count = int(numbers[0])
                break

        # Альтернативный способ: ищем контейнер комментариев
        if comments_count == 0:
            comment_containers = soup.find_all('div', class_=re.compile(r'comment|message'))
            comments_count = len(comment_containers)

        result['comments_count'] = comments_count

        # ПАРСИМ ПОЛ ЖИВОТНОГО - ищем только в элементе card-info с заголовком "Пол питомца"
        gender = 'не указан'

        # Ищем блок card-information
        card_information = soup.find('div', class_='card-information')
        if card_information:
            # Ищем все блоки card-info внутри card-information
            card_info_blocks = card_information.find_all('div', class_='card-info')

            for block in card_info_blocks:
                # Ищем заголовок "Пол питомца"
                title_div = block.find('div', class_='card-info__title')
                if title_div and title_div.get_text().strip() == 'Пол питомца':
                    # Ищем значение
                    value_div = block.find('div', class_='card-info__value')
                    if value_div:
                        gender_text = value_div.get_text().strip().lower()
                        # Приводим к стандартным значениям
                        if any(word in gender_text for word in ['мужской', 'мальчик', 'самец', 'кот', 'пёс']):
                            gender = 'мужской'
                        elif any(word in gender_text for word in ['женский', 'девочка', 'самка', 'кошка']):
                            gender = 'женский'
                        else:
                            gender = 'не указан'
                    break

        result['gender'] = gender

        # ПАРСИМ ДАТУ ПУБЛИКАЦИИ - ищем только в элементе card-info с заголовком "Добавлено"
        publication_date = 'не указана'

        if card_information:
            card_info_blocks = card_information.find_all('div', class_='card-info')

            for block in card_info_blocks:
                # Ищем заголовок "Добавлено"
                title_div = block.find('div', class_='card-info__title')
                if title_div and title_div.get_text().strip() == 'Добавлено':
                    # Ищем значение даты
                    value_div = block.find('div', class_='card-info__value')
                    if value_div:
                        date_text = value_div.get_text().strip()
                        publication_date = date_text
                    break

        result['publication_date'] = publication_date

        # ПАРСИМ ДЛИНУ ОПИСАНИЯ И ОКРАС - в элементе с классом text text-lt card__descr content
        description_length = 0
        color = 'не указан'

        # Ищем блок card__content
        card_content = soup.find('div', class_='card__content')
        if card_content:
            # Ищем описание в элементе с классом text text-lt card__descr content
            description_div = card_content.find('div', class_='text text-lt card__descr content')
            if description_div:
                # Получаем весь текст из описания
                description_text = description_div.get_text().strip()

                # Считаем количество слов (разделитель - пробелы)
                words = description_text.split()
                description_length = len(words)

                # ИЩЕМ ПРИЛАГАТЕЛЬНЫЕ-ЦВЕТА в описании
                found_colors = extract_colors_from_text(description_text)
                if found_colors:
                    color = ', '.join(found_colors)

        result['description_length'] = description_length
        result['color'] = color

        return result

    except Exception as e:
        print(f"Ошибка парсинга {url}: {e}")
        return {'has_photo': 0, 'photo_count': 0, 'comments_count': 0, 'gender': 'не указан', 'color': 'не указан',
                'region': 'не указано', 'publication_date': 'не указана', 'description_length': 0}


def extract_colors_from_text(text):
    """Извлекает прилагательные, обозначающие цвет, из текста"""

    # Словарь цветов и их вариантов
    color_words = {
        'белый': ['белый', 'белая', 'белое', 'белые', 'белым', 'белом', 'белой', 'белую'],
        'черный': ['черный', 'черная', 'черное', 'черные', 'черным', 'черном', 'черной', 'черную'],
        'рыжий': ['рыжий', 'рыжая', 'рыжее', 'рыжие', 'рыжим', 'рыжем', 'рыжей', 'рыжую'],
        'серый': ['серый', 'серая', 'серое', 'серые', 'серым', 'сером', 'серой', 'серую'],
        'коричневый': ['коричневый', 'коричневая', 'коричневое', 'коричневые', 'коричневым', 'коричневом', 'коричневой',
                       'коричневую'],
        'рыжеватый': ['рыжеватый', 'рыжеватая', 'рыжеватое', 'рыжеватые'],
        'сероватый': ['сероватый', 'сероватая', 'сероватое', 'сероватые'],
        'бежевый': ['бежевый', 'бежевая', 'бежевое', 'бежевые'],
        'палевый': ['палевый', 'палевая', 'палевое', 'палевые'],
        'красный': ['красный', 'красная', 'красное', 'красные'],
        'голубой': ['голубой', 'голубая', 'голубое', 'голубые'],
        'пегий': ['пегий', 'пегая', 'пегое', 'пегие'],
        'пятнистый': ['пятнистый', 'пятнистая', 'пятнистое', 'пятнистые'],
        'полосатый': ['полосатый', 'полосатая', 'полосатое', 'полосатые'],
        'трехцветный': ['трехцветный', 'трехцветная', 'трехцветное', 'трехцветные'],
        'двухцветный': ['двухцветный', 'двухцветная', 'двухцветное', 'двухцветные'],
        'светлый': ['светлый', 'светлая', 'светлое', 'светлые'],
        'темный': ['темный', 'темная', 'темное', 'темные'],
        'пестрый': ['пестрый', 'пестрая', 'пестрое', 'пестрые']
    }

    found_colors = []
    text_lower = text.lower()

    # Ищем основные цвета
    for base_color, variants in color_words.items():
        for variant in variants:
            if variant in text_lower:
                if base_color not in found_colors:
                    found_colors.append(base_color)
                break

    return found_colors


def translate_status(status_text):
    """Переводит статус на русский"""
    if pd.isna(status_text) or not status_text:
        return 'не указан'

    status_text = str(status_text).lower()

    status_mapping = {
        'в поиске': 'в поиске',
        'ищут хозяина': 'ищут хозяина',
        'найден': 'найден',
        'хозяин найден': 'хозяин найден',
        'searching': 'в поиске',
        'found': 'найден',
        'owner found': 'хозяин найден'
    }

    return status_mapping.get(status_text, status_text)


def translate_animal_type(animal_type):
    """Переводит тип животного на русский"""
    if pd.isna(animal_type) or not animal_type:
        return 'не указан'

    animal_type = str(animal_type).lower()

    type_mapping = {
        'dog': 'собака',
        'cat': 'кошка',
        'собака': 'собака',
        'кошка': 'кошка'
    }

    return type_mapping.get(animal_type, animal_type)


def extract_age(age_text):
    """Извлекает возраст"""
    if pd.isna(age_text) or not age_text:
        return 'не указан'

    # Ищем числа в возрасте
    matches = re.findall(r'(\d+)\s*(год|лет|месяц|мес)', str(age_text).lower())
    if matches:
        age, unit = matches[0]
        age = int(age)
        if 'мес' in unit:
            return f"{age} мес"
        return f"{age} лет"

    # Если не нашли паттерн, возвращаем как есть
    return clean_text(age_text)


def clean_text(text):
    """Очищает текст"""
    if pd.isna(text) or not text:
        return 'не указано'
    cleaned = re.sub(r'\s+', ' ', str(text)).strip()
    return cleaned[:50]  # Ограничиваем длину


# Запуск создания датасета
if __name__ == "__main__":
    dataset = create_unified_dataset()

    if dataset is not None:
        print(f"\nПЕРВЫЕ 5 ЗАПИСЕЙ:")
        print(dataset.head())

        print(f"\nРАСПРЕДЕЛЕНИЕ ПО ТИПАМ:")
        print(dataset['тип_объявления'].value_counts())

        print(f"\nРАСПРЕДЕЛЕНИЕ ПО РЕГИОНАМ:")
        print(dataset['регион'].value_counts().head(10))

        print(f"\nРАСПРЕДЕЛЕНИЕ ПО ПОЛУ:")
        print(dataset['пол'].value_counts())

        print(f"\nРАСПРЕДЕЛЕНИЕ ПО ОКРАСУ:")
        print(dataset['окрас'].value_counts().head(10))

        print(f"\nСТАТИСТИКА ФОТО:")
        print(f"Объявления с фото: {len(dataset[dataset['есть_фото'] == 'да'])}")
        print(f"Среднее количество фото: {dataset['количество_фото'].mean():.1f}")

        print(f"\nСТАТИСТИКА КОММЕНТАРИЕВ:")
        print(f"Объявления с комментариями: {len(dataset[dataset['количество_комментариев'] > 0])}")
        print(f"Среднее количество комментариев: {dataset['количество_комментариев'].mean():.1f}")

        print(f"\nСТАТИСТИКА ОПИСАНИЙ:")
        print(f"Средняя длина описания (слов): {dataset['длина_описания'].mean():.1f}")
        print(f"Максимальная длина описания: {dataset['длина_описания'].max()} слов")
        print(f"Минимальная длина описания: {dataset['длина_описания'].min()} слов")

        print(f"\nДАТАСЕТ СОХРАНЕН В: pets_dataset_2025.csv")