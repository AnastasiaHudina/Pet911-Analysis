import requests
from bs4 import BeautifulSoup
import time
import pandas as pd
from random import uniform
import re


def get_all_pet_links(base_url, ad_type, animal_filter=None):
    """Собирает ВСЕ ссылки на объявления с новых страниц"""

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
        'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
    }

    all_links = []
    max_pages = 50  # СОБИРАЕМ 50 СТРАНИЦ
    target_year = "2025"

    print(f"Собираем ВСЕ {ad_type} объявления (потом отфильтруем по {target_year} году)...")

    for page in range(1, max_pages + 1):
        try:
            # Формируем URL страницы с пагинацией
            if '?' in base_url:
                url = f"{base_url}&page={page}"
            else:
                url = f"{base_url}?page={page}"

            print(f"Страница {page}: {url[:100]}...")

            # Отправляем запрос
            response = requests.get(url, headers=headers, timeout=15)
            time.sleep(uniform(2, 4))

            if response.status_code != 200:
                print(f"Ошибка {response.status_code}")
                break

            # Парсим HTML
            soup = BeautifulSoup(response.text, 'html.parser')

            # Ищем карточки объявлений по новому селектору
            cards = soup.find_all('div', class_='catalog-item')

            if not cards:
                print("Не найдены карточки объявлений")
                break

            page_links_count = 0

            for card in cards:
                # Ищем ссылку в карточке
                link_element = card.find('a', class_='catalog-item__thumb')
                if not link_element:
                    continue

                link = link_element.get('href')
                if not link:
                    continue

                # Формируем полную ссылку
                full_link = "https://pet911.ru" + link if link.startswith('/') else link

                # Проверяем дубликаты
                if any(x['url'] == full_link for x in all_links):
                    continue

                # Определяем тип животного из URL и типа объявления
                animal_type = None
                ad_type_detected = None

                if '/lost/' in full_link:
                    ad_type_detected = 'lost'
                elif '/found/' in full_link:
                    ad_type_detected = 'found'

                if '/dog/' in full_link:
                    animal_type = 'dog'
                elif '/cat/' in full_link:
                    animal_type = 'cat'

                # Фильтруем по типу животного если задан фильтр
                if animal_filter and animal_type != animal_filter:
                    continue

                if not animal_type or not ad_type_detected:
                    continue

                # Извлекаем дату из карточки
                date_element = card.find('div', class_='catalog-item__date')
                if not date_element:
                    continue

                date_text = date_element.get_text().strip()

                # Извлекаем дополнительную информацию
                title_element = card.find('a', class_='catalog-item__title')
                title = title_element.get_text().strip() if title_element else "Без названия"

                excerpt_element = card.find('div', class_='catalog-item__excerpt')
                excerpt = excerpt_element.get_text().strip() if excerpt_element else ""

                # ОПРЕДЕЛЯЕМ ГОД ИЗ ДАТЫ
                year = None
                year_match = re.search(r'(\d{4})', date_text)
                if year_match:
                    year = year_match.group(1)

                # Сохраняем ВСЕ объявления
                all_links.append({
                    'url': full_link,
                    'animal_type': animal_type,
                    'ad_type': ad_type_detected,  # Определяем автоматически из URL
                    'date': date_text,
                    'year': year,
                    'title': title,
                    'excerpt': excerpt,
                    'is_2025': year == target_year  # Отмечаем объявления за 2025 год
                })

                page_links_count += 1

            print(f"Найдено: {len(cards)} карточек, сохранено: {page_links_count}")

            # ПРОВЕРЯЕМ РАСПРЕДЕЛЕНИЕ ПО ГОДАМ НА ЭТОЙ СТРАНИЦЕ
            page_years = [link['year'] for link in all_links[-page_links_count:] if link['year']]
            if page_years:
                from collections import Counter
                year_counts = Counter(page_years)
                print(f"Распределение по годам на странице: {dict(year_counts)}")

            # Проверяем пагинацию для новых страниц
            pagination = soup.find('ul', class_='pagination')
            if pagination:
                current_page_links = pagination.find_all('a', class_='active')
                if not current_page_links or page >= max_pages:
                    print("Пагинация закончена")
                    break
            else:
                # Альтернативная проверка пагинации
                next_btn = soup.find('a', string=re.compile('дальше|следующая|next', re.IGNORECASE))
                if not next_btn and page > 1:
                    print("Пагинация закончена")
                    break

            # ЕСЛИ НА СТРАНИЦЕ УЖЕ НЕТ 2025 ГОДА - ПРЕДУПРЕЖДАЕМ
            current_page_2025 = sum(1 for link in all_links[-page_links_count:] if link['is_2025'])
            if current_page_2025 == 0 and page > 1:
                print("На этой странице нет объявлений за 2025 год")

        except Exception as e:
            print(f"Ошибка: {e}")
            continue

    return all_links


def filter_2025_links(all_links, animal_type_name):
    """Фильтрует объявления за 2025 год и сохраняет в отдельные файлы для lost и found"""

    links_2025 = [link for link in all_links if link['is_2025']]
    links_other = [link for link in all_links if not link['is_2025']]

    print(f"\nСТАТИСТИКА ДЛЯ {animal_type_name.upper()}:")
    print(f"Всего собрано объявлений: {len(all_links)}")
    print(f"За 2025 год: {len(links_2025)}")
    print(f"За другие годы: {len(links_other)}")

    # Распределение по годам
    from collections import Counter
    year_counts = Counter([link['year'] for link in all_links if link['year']])
    print(f"Распределение по годам: {dict(year_counts)}")

    # СОХРАНЯЕМ ОТДЕЛЬНО ДЛЯ LOST И FOUND
    saved_files = []

    for ad_type in ['lost', 'found']:
        links_ad_type = [link for link in links_2025 if link['ad_type'] == ad_type]

        if links_ad_type:
            df_ad_type = pd.DataFrame(links_ad_type)
            filename = f'pet911_{ad_type}_pets_2025_links.csv'

            # Если файл уже существует, добавляем к нему
            try:
                existing_df = pd.read_csv(filename)
                combined_df = pd.concat([existing_df, df_ad_type], ignore_index=True)
                # Удаляем дубликаты
                combined_df = combined_df.drop_duplicates(subset=['url'])
                combined_df.to_csv(filename, index=False, encoding='utf-8-sig')
                print(f"Добавлены объявления в: {filename} (всего: {len(combined_df)})")
            except FileNotFoundError:
                df_ad_type.to_csv(filename, index=False, encoding='utf-8-sig')
                print(f"Создан файл: {filename} (объявлений: {len(links_ad_type)})")

            saved_files.append(filename)

            # Статистика по типу объявления
            dogs_count = len([x for x in links_ad_type if x['animal_type'] == 'dog'])
            cats_count = len([x for x in links_ad_type if x['animal_type'] == 'cat'])
            print(f"  {ad_type.upper()}: {len(links_ad_type)} объявлений")
            print(f"    - Собаки: {dogs_count}")
            print(f"    - Кошки: {cats_count}")
        else:
            print(f"  {ad_type.upper()}: нет объявлений за 2025 год")

    return saved_files


def main():
    """Основная функция для сбора данных с новых страниц"""

    # НОВЫЕ НАСТРОЙКИ ДЛЯ СБОРА
    sources = [
        {
            'base_url': "https://pet911.ru/catalog?PetsSearch%5Blatitude%5D=59.93859786876066&PetsSearch%5Blongitude%5D=30.31539916992188&PetsSearch%5BlatTopLeft%5D=60.43781352156256&PetsSearch%5BlngTopLeft%5D=31.643371582031254&PetsSearch%5BlatBotRight%5D=59.431726050400236&PetsSearch%5BlngBotRight%5D=28.987426757812504&zoom=9&PetsSearch%5Baddress%5D=&PetsSearch%5Banimal%5D=&PetsSearch%5Banimal%5D=1&PetsSearch%5Btype%5D=&PetsSearch%5Btype%5D=0&PetsSearch%5BdateField%5D=&PetsSearch%5BdateField%5D=1&PetsSearch%5BdatePeriod%5D=4&PetsSearch%5BshowClosedPets%5D=0&PetsSearch%5BshowClosedPets%5D=1",
            'animal_filter': 'dog',
            'animal_name': 'СОБАКИ'
        },
        {
            'base_url': "https://pet911.ru/catalog?PetsSearch%5Blatitude%5D=59.93859786876066&PetsSearch%5Blongitude%5D=30.31539916992188&PetsSearch%5BlatTopLeft%5D=60.43781352156256&PetsSearch%5BlngTopLeft%5D=31.643371582031254&PetsSearch%5BlatBotRight%5D=59.431726050400236&PetsSearch%5BlngBotRight%5D=28.987426757812504&zoom=9&PetsSearch%5Baddress%5D=&PetsSearch%5Banimal%5D=&PetsSearch%5Banimal%5D=2&PetsSearch%5Btype%5D=&PetsSearch%5Btype%5D=0&PetsSearch%5BdateField%5D=&PetsSearch%5BdateField%5D=1&PetsSearch%5BdatePeriod%5D=4&PetsSearch%5BshowClosedPets%5D=0&PetsSearch%5BshowClosedPets%5D=1",
            'animal_filter': 'cat',
            'animal_name': 'КОШКИ'
        }
    ]

    all_results = {}
    all_saved_files = []

    for source in sources:
        print(f"\n{'=' * 60}")
        print(f"ОБРАБОТКА: {source['animal_name']}")
        print(f"{'=' * 60}")

        # Собираем ВСЕ объявления для данного типа животных
        all_links = get_all_pet_links(
            source['base_url'],
            source['animal_name'].lower(),
            animal_filter=source['animal_filter']
        )
        all_results[source['animal_name']] = all_links

        # Фильтруем за 2025 год и сохраняем
        saved_files = filter_2025_links(all_links, source['animal_name'])
        all_saved_files.extend(saved_files)

    # ОБЩАЯ СТАТИСТИКА
    print(f"\n{'=' * 60}")
    print("ОБЩАЯ СТАТИСТИКА")
    print(f"{'=' * 60}")

    total_all = sum(len(links) for links in all_results.values())
    total_2025 = 0

    # Подсчитываем общее количество за 2025 год
    for animal_links in all_results.values():
        total_2025 += sum(1 for link in animal_links if link['is_2025'])

    print(f"Всего собрано объявлений: {total_all}")
    print(f"Из них за 2025 год: {total_2025}")

    if total_all > 0:
        print(f"Процент за 2025 год: {(total_2025 / total_all) * 100:.1f}%")

    # ДЕТАЛЬНАЯ СТАТИСТИКА ПО ТИПАМ ОБЪЯВЛЕНИЙ
    print(f"\nДЕТАЛЬНАЯ СТАТИСТИКА ЗА 2025 ГОД:")

    for ad_type in ['lost', 'found']:
        try:
            df = pd.read_csv(f'pet911_{ad_type}_pets_2025_links.csv')
            dogs_count = len(df[df['animal_type'] == 'dog'])
            cats_count = len(df[df['animal_type'] == 'cat'])
            print(f"\n{ad_type.upper()}: {len(df)} объявлений")
            print(f"  - Собаки: {dogs_count}")
            print(f"  - Кошки: {cats_count}")
        except FileNotFoundError:
            print(f"\n{ad_type.upper()}: файл не найден")

    print(f"\nСОХРАНЕННЫЕ ФАЙЛЫ (ТОЛЬКО 2025 ГОД):")
    print(f"  - Пропавшие: pet911_lost_pets_2025_links.csv")
    print(f"  - Найденные: pet911_found_pets_2025_links.csv")


if __name__ == "__main__":
    # Запускаем сбор сразу
    main()