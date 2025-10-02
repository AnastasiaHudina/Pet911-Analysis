import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
from random import uniform
import re
from datetime import datetime


def parse_pet_details(url, ad_type):
    """Парсит детальную информацию с страницы объявления"""

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        time.sleep(uniform(2, 3))

        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.text, 'html.parser')

        # Базовые данные
        data = {
            'url': url,
            'ad_type': ad_type,
            'timestamp_collected': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        # ОСНОВНАЯ ИНФОРМАЦИЯ
        # Заголовок
        title_elem = soup.find('h1')
        data['title'] = title_elem.get_text().strip() if title_elem else None

        # Регион (из URL или заголовка)
        region_match = re.search(r'/([^/]+)/(lost|found)/(dog|cat)', url)
        data['region'] = region_match.group(1).replace('-', ' ').title() if region_match else None

        # ПРАВИЛЬНОЕ ОПРЕДЕЛЕНИЕ СТАТУСА ЧЕРЕЗ CARD-NOTICE
        data['status'] = determine_status(soup, ad_type)

        # ДАННЫЕ О ЖИВОТНОМ
        # Вид животного
        if '/dog/' in url:
            data['animal_type'] = 'собака'
        elif '/cat/' in url:
            data['animal_type'] = 'кошка'
        else:
            data['animal_type'] = None

        # Пытаемся извлечь данные из текста (универсальные селекторы)
        page_text_lower = soup.get_text().lower()

        # Порода (ищем в заголовке или тексте)
        breed_patterns = [r'порода[:\s]*([^\n\.]+)', r'породы[:\s]*([^\n\.]+)']
        data['breed'] = extract_by_pattern(soup, breed_patterns)

        # Пол
        gender_patterns = [r'пол[:\s]*([^\n\.]+)', r'мальчик', r'девочка', r'кот\\b', r'кошка\\b', r'пёс\\b',
                           r'собака\\b']
        gender_text = extract_by_pattern(soup, gender_patterns)
        if gender_text:
            if any(word in gender_text.lower() for word in ['мальчик', 'кот', 'пёс', 'самец']):
                data['gender'] = 'самец'
            elif any(word in gender_text.lower() for word in ['девочка', 'кошка', 'собака', 'самка']):
                data['gender'] = 'самка'
            else:
                data['gender'] = gender_text.strip()
        else:
            data['gender'] = None

        # Окрас
        color_patterns = [r'окрас[:\s]*([^\n\.]+)', r'цвет[:\s]*([^\n\.]+)', r'шерсть[:\s]*([^\n\.]+)']
        data['color'] = extract_by_pattern(soup, color_patterns)

        # Кличка
        name_patterns = [r'кличка[:\s]*([^\n\.]+)', r'имя[:\s]*([^\n\.]+)']
        data['name'] = extract_by_pattern(soup, name_patterns)

        # Возраст
        age_patterns = [r'возраст[:\s]*([^\n\.]+)', r'лет', r'год', r'месяц']
        data['age'] = extract_by_pattern(soup, age_patterns)

        # ДАТЫ И МЕСТО
        # Дата события
        date_patterns = [r'дата[:\s]*([^\n\.]+)', r'потерян[:\s]*([^\n\.]+)', r'найден[:\s]*([^\n\.]+)']
        data['event_date'] = extract_by_pattern(soup, date_patterns)

        # Место события
        location_patterns = [r'место[:\s]*([^\n\.]+)', r'район[:\s]*([^\n\.]+)', r'адрес[:\s]*([^\n\.]+)']
        data['location'] = extract_by_pattern(soup, location_patterns)

        # ОПИСАНИЕ И ОБСТОЯТЕЛЬСТВА
        # Ищем основной текст описания
        description_elem = soup.find('div', class_=re.compile('description|text|content'))
        if not description_elem:
            # Ищем любой div с большим количеством текста
            divs = soup.find_all('div')
            for div in divs:
                text = div.get_text().strip()
                if len(text) > 100 and not any(
                        cls in str(div.get('class', '')).lower() for cls in ['header', 'nav', 'menu', 'footer']):
                    description_elem = div
                    break

        data['description'] = description_elem.get_text().strip() if description_elem else None
        data['description_length'] = len(data['description']) if data['description'] else 0

        # КОНТАКТЫ И ВЗАИМОДЕЙСТВИЕ
        # Телефон (ищем в тексте)
        phone_match = re.search(r'[\+\(]?[1-9][0-9 .\-\(\)]{8,}[0-9]', soup.get_text())
        data['has_contacts'] = bool(phone_match)

        # Просмотры (ищем числа которые могут быть просмотрами)
        views_match = re.search(r'(\d+)\s*(просмотр|view)', soup.get_text().lower())
        data['views'] = int(views_match.group(1)) if views_match else None

        # Комментарии
        comments = soup.find_all('div', class_=re.compile('comment|message'))
        data['comments_count'] = len(comments)

        # Текст комментариев (первые 3)
        comment_texts = []
        for i, comment in enumerate(comments[:3]):
            text = comment.get_text().strip()
            if text:
                comment_texts.append(text)
        data['comments_sample'] = ' | '.join(comment_texts) if comment_texts else None

        # ФОТО
        images = soup.find_all('img')
        data['has_photo'] = any(
            'pet' in str(img.get('src', '')).lower() or 'animal' in str(img.get('src', '')).lower() for img in images)
        data['photos_count'] = len(
            [img for img in images if img.get('src') and not img.get('src', '').startswith('/img/')])

        # Особые приметы (ищем в описании)
        if data['description']:
            marks_keywords = ['особые приметы', 'отличительные', 'приметы', 'метка', 'шрам']
            for keyword in marks_keywords:
                if keyword in data['description'].lower():
                    # Берем предложение с ключевым словом
                    sentences = re.split(r'[.!?]', data['description'])
                    for sentence in sentences:
                        if keyword in sentence.lower():
                            data['special_marks'] = sentence.strip()
                            break
                    break
            else:
                data['special_marks'] = None
        else:
            data['special_marks'] = None

        return data

    except Exception as e:
        print(f"Ошибка при парсинге {url}: {e}")
        return None


def determine_status(soup, ad_type):
    """Правильно определяет статус объявления на основе card-notice элементов"""

    # ИЩЕМ ЭЛЕМЕНТ CARD-NOTICE С ТЕКСТОМ "ПИТОМЕЦ НАШЕЛСЯ" ИЛИ "ХОЗЯИН НАШЕЛСЯ"
    card_notice = soup.find('div', class_='card-notice')

    if card_notice:
        # Ищем заголовок внутри card-notice
        notice_title = card_notice.find('div', class_='card-notice__title')

        if notice_title:
            notice_text = notice_title.get_text().strip().lower()

            # Для пропавших животных
            if ad_type == 'lost':
                if 'питомец нашелся' in notice_text:
                    return 'найден'
                elif 'животное найдено' in notice_text:
                    return 'найден'

            # Для найденных животных
            elif ad_type == 'found':
                if 'хозяин нашелся' in notice_text:
                    return 'хозяин найден'
                elif 'хозяин найден' in notice_text:
                    return 'хозяин найден'

    # ДОПОЛНИТЕЛЬНАЯ ПРОВЕРКА - ИЩЕМ НАПРЯМУЮ ТЕКСТ В CARD-NOTICE__TITLE
    notice_title_elements = soup.find_all('div', class_='card-notice__title')
    for notice_title in notice_title_elements:
        notice_text = notice_title.get_text().strip().lower()

        if ad_type == 'lost':
            if any(phrase in notice_text for phrase in ['питомец нашелся', 'животное найдено', 'питомец найден']):
                return 'найден'
        elif ad_type == 'found':
            if any(phrase in notice_text for phrase in ['хозяин нашелся', 'хозяин найден']):
                return 'хозяин найден'

    # ЕСЛИ CARD-NOTICE НЕ НАЙДЕН, ИЩЕМ В ОБЩЕМ ТЕКСТЕ СТРАНИЦЫ
    page_text = soup.get_text().lower()

    if ad_type == 'lost':
        if any(phrase in page_text for phrase in ['питомец нашелся', 'животное найдено']):
            return 'найден'
        else:
            return 'в поиске'
    else:
        if any(phrase in page_text for phrase in ['хозяин нашелся', 'хозяин найден']):
            return 'хозяин найден'
        else:
            return 'ищут хозяина'


def extract_by_pattern(soup, patterns):
    """Извлекает текст по регулярным выражениям"""
    text = soup.get_text()

    for pattern in patterns:
        if len(pattern) > 2:  # Это регулярное выражение
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                # Если есть группа захвата, берем её, иначе весь матч
                return match.group(1).strip() if match.lastindex else match.group(0).strip()
        else:  # Это просто ключевое слово
            if pattern in text.lower():
                return pattern

    return None


def process_ads_file(filename, ad_type):
    """Обрабатывает файл с ссылками и собирает детальную информацию"""

    print(f"\n{'=' * 60}")
    print(f"ОБРАБОТКА: {ad_type.upper()} ОБЪЯВЛЕНИЙ")
    print(f"Файл: {filename}")
    print(f"{'=' * 60}")

    try:
        # Читаем файл с ссылками
        df_links = pd.read_csv(filename)
        print(f"Загружено ссылок: {len(df_links)}")
    except Exception as e:
        print(f"Ошибка при чтении файла {filename}: {e}")
        return None

    all_data = []
    completed_ads = 0

    # Обрабатываем каждое объявление
    for index, row in df_links.iterrows():
        url = row['url']
        print(f"Обрабатываю {index + 1}/{len(df_links)}: {url[:60]}...")

        data = parse_pet_details(url, ad_type)

        if data:
            all_data.append(data)

            # Считаем завершенные объявления
            if (ad_type == 'lost' and data['status'] == 'найден') or \
                    (ad_type == 'found' and data['status'] == 'хозяин найден'):
                completed_ads += 1
                print(f"  ЗАВЕРШЕНО: {data['status']}")
            else:
                print(f"  В ПРОЦЕССЕ: {data['status']}")

            # Периодически сохраняем прогресс
            if (index + 1) % 10 == 0:
                print(f"Прогресс: {index + 1}/{len(df_links)}")

        # Пауза между запросами
        time.sleep(uniform(1, 2))

    # Сохраняем результаты
    if all_data:
        output_filename = f"pet911_{ad_type}_pets_2025_detailed.csv"
        df_result = pd.DataFrame(all_data)
        df_result.to_csv(output_filename, index=False, encoding='utf-8-sig')

        print(f"\nРЕЗУЛЬТАТЫ ДЛЯ {ad_type.upper()}:")
        print(f"Обработано объявлений: {len(all_data)}")
        print(f"Завершенных случаев: {completed_ads}")
        print(f"Файл сохранен: {output_filename}")

        # Детальная статистика
        if ad_type == 'lost':
            found_count = len([x for x in all_data if x['status'] == 'найден'])
            searching_count = len([x for x in all_data if x['status'] == 'в поиске'])
            print(f"Статусы:")
            print(f"  - Найдены: {found_count}")
            print(f"  - В поиске: {searching_count}")
        else:
            owner_found = len([x for x in all_data if x['status'] == 'хозяин найден'])
            searching_owner = len([x for x in all_data if x['status'] == 'ищут хозяина'])
            print(f"Статусы:")
            print(f"  - Хозяин найден: {owner_found}")
            print(f"  - Ищут хозяина: {searching_owner}")

        return df_result
    else:
        print(f"Не удалось собрать данные из {filename}")
        return None


def main():
    """Основная функция"""

    print("ЗАПУСК СБОРА ДЕТАЛЬНЫХ ДАННЫХ С ОБЪЯВЛЕНИЙ")
    print("=" * 60)

    # СЕКЦИЯ 1: ПРОПАВШИЕ ЖИВОТНЫЕ
    lost_data = process_ads_file('pet911_lost_pets_2025_links.csv', 'lost')

    # СЕКЦИЯ 2: НАЙДЕННЫЕ ЖИВОТНЫЕ
    found_data = process_ads_file('pet911_found_pets_2025_links.csv', 'found')

    # ОБЩАЯ СТАТИСТИКА
    print(f"\n{'=' * 60}")
    print("ОБЩАЯ СТАТИСТИКА")
    print(f"{'=' * 60}")

    total_processed = 0
    total_completed = 0

    if lost_data is not None:
        lost_completed = len([x for x in lost_data.to_dict('records') if x['status'] == 'найден'])
        total_processed += len(lost_data)
        total_completed += lost_completed
        print(f"Пропавшие животные: {len(lost_data)} объявлений")
        print(f"  - Успешно найдены: {lost_completed}")

    if found_data is not None:
        found_completed = len([x for x in found_data.to_dict('records') if x['status'] == 'хозяин найден'])
        total_processed += len(found_data)
        total_completed += found_completed
        print(f"Найденные животные: {len(found_data)} объявлений")
        print(f"  - Хозяева найдены: {found_completed}")

    print(f"\nИТОГО:")
    print(f"Всего обработано: {total_processed} объявлений")
    print(f"Завершенных случаев: {total_completed}")

    if total_processed > 0:
        completion_rate = (total_completed / total_processed) * 100
        print(f"Процент завершенных: {completion_rate:.1f}%")

    print(f"\nСОХРАНЕННЫЕ ФАЙЛЫ:")
    print(f"Детальные данные пропавших: pet911_lost_pets_2025_detailed.csv")
    print(f"Детальные данные найденных: pet911_found_pets_2025_detailed.csv")


if __name__ == "__main__":
    main()