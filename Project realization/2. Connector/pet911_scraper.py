# pet911_scraper.py
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
from random import uniform
import re
from datetime import datetime
import os

class Pet911Scraper:
    """
    A class to scrape data about lost and found animals from pet911.ru.
    """

    def __init__(self, base_url="https://pet911.ru"):
        self.base_url = base_url
        # Изменен User-Agent и добавлены другие стандартные заголовки для имитации десктопного браузера
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Accept-Language': 'en-US,en;q=0.9,ru;q=0.8',
            'DNT': '1', # Do Not Track Request Header
            'Upgrade-Insecure-Requests': '1',
        }
        # Remove debug file if it exists from previous runs
        debug_html_file = "page_1_full_html.html"
        if os.path.exists(debug_html_file):
             try:
                 os.remove(debug_html_file)
                 print(f"Removed old debug file: {debug_html_file}")
             except OSError as e:
                 print(f"Error removing debug file {debug_html_file}: {e}")


    def get_html(self, url):
        """Получает HTML-код страницы."""
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()  # Проверяем на ошибки HTTP (4xx, 5xx)
            time.sleep(uniform(1, 2)) # Added a default sleep here
            return response.text
        except requests.exceptions.RequestException as e:
            print(f"Ошибка при получении URL {url}: {e}")
            return None

    def determine_status(self, soup, ad_type):
        """Правильно определяет статус объявления на основе card-notice элементов"""
        card_notice = soup.find('div', class_='card-notice')

        if card_notice:
            notice_title = card_notice.find('div', class_='card-notice__title')
            if notice_title:
                notice_text = notice_title.get_text().strip().lower()
                if ad_type == 'lost':
                    if any(phrase in notice_text for phrase in ['питомец нашелся', 'животное найдено', 'питомец найден']):
                        return 'найден'
                elif ad_type == 'found':
                    if any(phrase in notice_text for phrase in ['хозяин нашелся', 'хозяин найден']):
                        return 'хозяин найден'

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


    def extract_by_pattern(self, soup, patterns):
        """Извлекает текст по регулярным выражениям"""
        text = soup.get_text()

        for pattern in patterns:
            # Use raw strings for regex patterns to avoid SyntaxWarning
            if isinstance(pattern, str) and len(pattern) > 2 and pattern.startswith('r'): # Check if it looks like a regex pattern
                 # Ensure it's treated as a raw string for regex
                 if pattern.startswith('r\''):
                      regex_pattern = re.compile(pattern[2:-1], re.IGNORECASE)
                 elif pattern.startswith('r\"'):
                      regex_pattern = re.compile(pattern[2:-1], re.IGNORECASE)
                 else:
                      regex_pattern = re.compile(pattern, re.IGNORECASE)

                 match = regex_pattern.search(text)

                 if match:
                    return match.group(1).strip() if match.lastindex else match.group(0).strip()
            elif isinstance(pattern, str):  # It's a simple keyword
                if pattern.lower() in text.lower():
                    # Find the first occurrence and return the surrounding text (e.g., sentence)
                    sentences = re.split(r'[.!?]', text)
                    for sentence in sentences:
                        if pattern.lower() in sentence.lower():
                            return sentence.strip()
        return None

    def extract_from_description(self, description, patterns):
        """Извлекает информацию из текста описания по регулярным выражениям или ключевым словам."""
        if not description:
            return None

        text = description.lower()

        for pattern in patterns:
             # Use raw strings for regex patterns to avoid SyntaxWarning
             if isinstance(pattern, str) and len(pattern) > 2 and pattern.startswith('r'): # Check if it looks like a regex pattern
                 # Ensure it's treated as a raw string for regex
                 if pattern.startswith('r\''):
                      regex_pattern = re.compile(pattern[2:-1])
                 elif pattern.startswith('r\"'):
                      regex_pattern = re.compile(pattern[2:-1])
                 else:
                      regex_pattern = re.compile(pattern)

                 match = regex_pattern.search(text)

                 if match:
                     return match.group(1).strip() if match.lastindex else match.group(0).strip()
             elif isinstance(pattern, str): # Simple keyword search
                 if pattern.lower() in text:
                      # Try to extract the sentence containing the keyword
                      sentences = re.split(r'[.!?]', description)
                      for sentence in sentences:
                           if pattern.lower() in sentence.lower():
                                # Simple approach: return the whole sentence
                                return sentence.strip()
        return None


    def parse_pet_details(self, url, ad_type):
        """Парсит детальную информацию с страницы объявления"""
        html_content = self.get_html(url)
        if not html_content:
            return None

        soup = BeautifulSoup(html_content, 'html.parser')

        data = {
            'url': url,
            'ad_type': ad_type,
            'timestamp_collected': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        try:
            # 1. id: Extract ID from the URL
            match = re.search(r'/(\d+)$', url) # Use the passed URL
            data['id'] = int(match.group(1)) if match else None
        except Exception as e:
            print(f"Error extracting ID from URL {url}: {e}")
            data['id'] = None

        # ОСНОВНАЯ ИНФОРМАЦИЯ
        # Вам может потребоваться селектор для заголовка (имени животного), если оно есть отдельно
        # title_elem = soup.find('h1') # Пример
        # data['title'] = title_elem.get_text().strip() if title_elem else None


        # Регион часто можно извлечь из URL или найти на странице.
        region_match = re.search(r'/([^/]+)/(lost|found)/(dog|cat)', url)
        data['region'] = region_match.group(1).replace('-', ' ').title() if region_match else None

        data['status'] = self.determine_status(soup, ad_type)

        # ДАННЫЕ О ЖИВОТНОМ

        # Изначально определяем тип животного по URL
        if '/dog/' in url:
            data['animal_type'] = 'собака'
        elif '/cat/' in url:
            data['animal_type'] = 'кошка'
        else:
            data['animal_type'] = None


        # --- МЕСТА ДЛЯ ВСТАВКИ СЕЛЕКТОРОВ ДЕТАЛЕЙ ---
        # Вам нужно будет найти актуальные CSS-селекторы на странице конкретного животного
        # и вставить их вместо placeholder'ов ниже.

        selectors = {
            # Пример: 'название_поля': 'ваш_css_селектор',
            # Селектор для региона, если он есть отдельным элементом, а не только в URL
            'регион_page': '.pet-card__location .pet-card__text', # <-- ОБНОВИТЕ ЭТОТ СЕЛЕКТОР
            # Селектор для статуса поиска на детальной странице
            'статус_поиска': '.pet-card__status .pet-card__text', # <-- ОБНОВИТЕ ЭТОТ СЕЛЕКТОР
            # Селектор для даты публикации объявления
            'дата_публикации': '.pet-card__date .pet-card__text', # <-- ОБНОВИТЕ ЭТОТ СЕЛЕКТОР
            # Селектор для типа животного (может совпадать с извлеченным из URL)
            'тип_животного_page': '.pet-card__type .pet-card__text', # <-- ОБНОВИТЕ ЭТОТ СЕЛЕКТОР
            # Селектор для пола животного
            'пол': '.pet-card__gender .pet-card__text', # <-- ОБНОВИТЕ ЭТОТ СЕЛЕКТОР
            # Селектор для возраста животного
            'возраст': '.pet-card__age .pet-card__text', # <-- ОБНОВИТЕ ЭТОТ СЕЛЕКТОР
            # Селектор для окраса животного
            'окрас': '.pet-card__color .pet-card__text', # <-- ОБНОВИТЕ ЭТОТ СЕЛЕКТОР
            # Селектор для блока с описанием
            'description_tag': '.pet-card__description .pet-card__text', # <-- ОБНОВИТЕ ЭТОТ СЕЛЕКТОР
            # Селектор для всех изображений в галерее (для подсчета фото)
            'photo_tags': '.pet-card__gallery img', # <-- ОБНОВИТЕ ЭТОТ СЕЛЕКТОР
            # Селектор для блока с контактной информацией (для проверки наличия контактов)
            'contact_info_present': '.pet-card__contacts', # <-- ОБНОВИТЕ ЭТОТ СЕЛЕКТОР
            # Селектор для всех комментариев (для подсчета комментариев)
            'comment_tags': '.comment-item' # <-- ОБНОВИТЕ ЭТОТ СЕЛЕКТОР
            # Добавьте сюда другие селекторы, если нужны другие поля из схемы БД
            # Пример: 'название': '.animal-name',
            # Пример: 'порода': '.animal-breed',
            # Пример: 'место_события': '.event-location',
        }

        # Поля, которые будем пытаться извлечь селекторами в первую очередь
        fields_to_extract_by_selector = [
            'регион_page', 'статус_поиска', 'дата_публикации', 'тип_животного_page',
            'пол', 'возраст', 'окрас', 'description_tag', 'photo_tags',
            'contact_info_present', 'comment_tags'
        ]

        for key in fields_to_extract_by_selector:
            selector = selectors.get(key)
            if not selector:
                continue # Пропускаем, если селектор не определен

            try:
                if key == 'description_tag':
                    description_tag = soup.select_one(selector)
                    description_text = description_tag.text.strip() if description_tag else ''
                    data['description'] = description_text # Сохраняем полное описание
                    data['Длина_описания'] = len(description_text)
                elif key == 'photo_tags':
                    photo_tags = soup.select(selector)
                    data['есть_фото'] = bool(photo_tags)
                    data['количество_фото'] = len(photo_tags)
                elif key == 'contact_info_present':
                     data['есть_контакты'] = soup.select_one(selector) is not None
                elif key == 'comment_tags':
                    comment_tags = soup.select(selector)
                    data['количество_комментариев'] = len(comment_tags)
                elif key == 'регион_page': # Обработка региона с страницы, если есть
                    tag = soup.select_one(selector)
                    data['регион'] = tag.text.strip() if tag else data.get('регион', 'Неизвестно') # Предпочитаем данные с страницы
                elif key == 'тип_животного_page': # Обработка типа животного с страницы
                     tag = soup.select_one(selector)
                     # Если нашли тип животного селектором, обновляем его
                     data['тип_животного'] = tag.text.strip() if tag else data.get('animal_type', 'Неизвестно')
                else:
                    tag = soup.select_one(selector)
                    data[key] = tag.text.strip() if tag else 'Неизвестно'
            except Exception as e:
                print(f"Error extracting {key} for {url} using selector {selector}: {e}")
                if key == 'description_tag':
                     data['description'] = None
                     data['Длина_описания'] = 0
                elif key == 'photo_tags':
                    data['есть_фото'] = False
                    data['количество_фото'] = 0
                elif key == 'contact_info_present': data['есть_контакты'] = False
                elif key == 'comment_tags': data['количество_комментариев'] = 0
                elif key == 'регион_page': data['регион'] = data.get('регион', 'Неизвестно')
                elif key == 'тип_животного_page': data['тип_животного'] = data.get('animal_type', 'Неизвестно')
                else: data[key] = 'Неизвестно'

        # --- ИЗВЛЕЧЕНИЕ ДАННЫХ ИЗ ОПИСАНИЯ, ЕСЛИ НЕ НАЙДЕНЫ СЕЛЕКТОРАМИ ---
        # Используем extract_from_description для полей, которые могут быть в описании

        # Порода
        # Проверяем, не нашли ли уже селектором. Если нет, пытаемся найти в описании.
        if data.get('порода') is None or data['порода'] == 'Неизвестно':
            breed_patterns = [r'порода[:\s]*([^\n\.]+)', r'породы[:\s]*([^\n\.]+)', 'порода'] # Добавьте сюда шаблоны или ключевые слова для породы
            extracted_breed = self.extract_from_description(data.get('description'), breed_patterns)
            if extracted_breed:
                 data['порода'] = extracted_breed.strip()
            else:
                 data['порода'] = 'Неизвестно' # Устанавливаем в Неизвестно, если не нашли ни селектором, ни в описании

        # Окрас
        # Проверяем, не нашли ли уже селектором. Если нет, пытаемся найти в описании.
        if data.get('окрас') is None or data['окрас'] == 'Неизвестно':
            color_patterns = [r'окрас[:\s]*([^\n\.]+)', r'цвет[:\s]*([^\n\.]+)', r'шерсть[:\s]*([^\n\.]+)', 'окрас', 'цвет'] # Добавьте сюда шаблоны или ключевые слова для окраса
            extracted_color = self.extract_from_description(data.get('description'), color_patterns)
            if extracted_color:
                 data['окрас'] = extracted_color.strip()
            else:
                 data['окрас'] = 'Неизвестно' # Устанавливаем в Неизвестно, если не нашли ни селектором, ни в описании


        # Тип животного (если не удалось определить по URL или селектором)
        # Проверяем, не нашли ли уже по URL или селектором. Если нет, пытаемся найти в описании.
        if data.get('тип_животного') is None or data['тип_животного'] == 'Неизвестно':
             animal_type_patterns = ['собака', 'кошка', 'щенок', 'котенок'] # Добавьте сюда ключевые слова для типа животного
             extracted_type = self.extract_from_description(data.get('description'), animal_type_patterns)
             if extracted_type:
                  data['тип_животного'] = extracted_type.strip()
             else:
                  data['тип_животного'] = 'Неизвестно'


        # Возраст
        # Проверяем, не нашли ли уже селектором. Если нет, пытаемся найти в описании.
        if data.get('возраст') is None or data['возраст'] == 'Неизвестно':
            age_patterns = [r'возраст[:\s]*([^\n\.]+)', 'лет', 'год', 'года', 'месяц', 'месяца', 'месяцев', r'около\s*\d+'] # Added raw string for regex
            extracted_age = self.extract_from_description(data.get('description'), age_patterns)
            if extracted_age:
                 data['возраст'] = extracted_age.strip()
            else:
                 data['возраст'] = 'Неизвестно' # Устанавливаем в Неизвестно, если не нашли ни селектором, ни в описании


        # ДАТЫ И МЕСТО (Используют extract_by_pattern, возможно, потребуют доработки шаблонов)
        # Эти поля уже пытаются извлекаться из всего текста страницы, включая описание,
        # с помощью extract_by_pattern. Возможно, потребуется уточнить шаблоны.
        date_patterns = [r'дата[:\s]*([^\n\.]+)', r'потерян[:\s]*([^\n\.]+)', r'найден[:\s]*([^\n\.]+)']
        data['event_date'] = self.extract_by_pattern(soup, date_patterns) # <-- ПРОВЕРЬТЕ ШАБЛОНЫ

        location_patterns = [r'место[:\s]*([^\n\.]+)', r'район[:\s]*([^\n\.]+)', r'адрес[:\s]*([^\n\.]+)']
        data['location'] = self.extract_by_pattern(soup, location_patterns) # <-- ПРОВЕРЬТЕ ШАБЛОНЫ


        # КОНТАКТЫ И ВЗАИМОДЕЙСТВИЕ (Используют extract_by_pattern или простые проверки, возможно, потребуют доработки)
        phone_match = re.search(r'[\+\(]?[1-9][0-9 .\-\(\)]{8,}[0-9]', soup.get_text()) # <-- ПРОВЕРЬТЕ ШАБЛОН НОМЕРА ТЕЛЕФОНА
        data['has_contacts'] = bool(phone_match)

        views_match = re.search(r'(\d+)\s*(просмотр|view)', soup.get_text().lower()) # <-- ПРОВЕРЬТЕ ШАБЛОН ПРОСМОТРОВ
        data['views'] = int(views_match.group(1)) if views_match else None

        # Комментарии подсчитываются по селектору comment_tags выше.
        # Извлечение текста комментариев (для примера)
        comment_texts = []
        try:
            comment_elements = soup.select(selectors.get('comment_tags', '')) # Используем селектор из словаря
            for i, comment in enumerate(comment_elements[:3]): # Извлекаем текст первых 3 комментариев
                text = comment.get_text().strip()
                if text:
                    comment_texts.append(text)
            data['comments_sample'] = ' | '.join(comment_texts) if comment_texts else None
        except Exception as e:
             print(f"Error extracting comment text for {url}: {e}")
             data['comments_sample'] = None


        # ФОТО (Количество фото подсчитывается по селектору photo_tags выше)
        # Проверка наличия фото делается по наличию тегов img по селектору photo_tags.

        # Особые приметы (Используют поиск по ключевым словам в описании)
        # Этот код ищет ключевые слова в уже извлеченном описании.
        if data.get('description'): # Используем извлеченное описание
            marks_keywords = ['особые приметы', 'отличительные', 'приметы', 'метка', 'шрам']
            for keyword in marks_keywords:
                if keyword in data['description'].lower():
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


        # Убедимся, что все требуемые поля присутствуют в словаре data, даже если они None или 'Неизвестно'
        required_fields = [
            'id', 'url', 'тип объявления', 'регион', 'статус_поиска', 'дата_публикации',
            'тип_животного', 'пол', 'возраст', 'окрас', 'есть_фото', 'количество_фото',
            'Длина_описания', 'есть_контакты', 'количество_комментариев'
        ]
        for field in required_fields:
            if field not in data:
                data[field] = None # Или 'Неизвестно', в зависимости от предпочтений

        # Переименовываем 'animal_type' в 'тип_животного' для соответствия схеме БД,
        # если оно не было установлено селектором 'тип_животного_page'
        if 'тип_животного' not in data or data.get('тип_животного') in [None, 'Неизвестно']:
             data['тип_животного'] = data.get('animal_type', 'Неизвестно')

        # Удаляем временное поле 'animal_type' если оно не нужно
        if 'animal_type' in data and 'тип_животного' in data:
             del data['animal_type']


        return data


    def scrape_links_from_page(self, url):
        """Scrapes animal detail URLs from a list page."""
        html_content = self.get_html(url)
        if not html_content:
            return []

        soup = BeautifulSoup(html_content, 'html.parser') # Using html.parser for potentially broader compatibility
        animal_urls_on_page = []

        # --- МЕСТО ДЛЯ ВСТАВКИ БОЛЕЕ ТОЧНОГО СЕЛЕКТОРА ССЫЛОК НА ОБЪЯВЛЕНИЯ ---
        # Замените этот блок кода на поиск ссылок, используя точный селектор,
        # который вы нашли для ссылок на детальные страницы объявлений (тег <a>).
        #
        # Пример:
        # link_selector = 'ваш_точный_css_селектор_для_ссылки_на_объявление'
        # animal_link_tags = soup.select(link_selector)
        #
        # for link_tag in animal_link_tags:
        #     if 'href' in link_tag.attrs:
        #         relative_url = link_tag['href']
        #         animal_url = relative_url if relative_url.startswith('http') else self.base_url + relative_url
        #         animal_urls_on_page.append(animal_url)

        # Пока используется широкий поиск по всем ссылкам и их фильтрация:
        all_links = soup.select('a[href]') # <-- МОЖЕТ ПОТРЕБОВАТЬСЯ УТОЧНЕНИЕ

        for link_tag in all_links:
            try:
                relative_url = link_tag['href']
                # Фильтруем ссылки, которые похожи на детальные страницы животных
                if '/card/' in relative_url or '/lost/' in relative_url or '/found/' in relative_url: # <-- ПРОВЕРЬТЕ ШАБЛОНЫ URL
                    animal_url = relative_url if relative_url.startswith('http') else self.base_url + relative_url
                    # Избегаем добавления ссылки на главную страницу каталога
                    if animal_url != url:
                         animal_urls_on_page.append(animal_url)
            except Exception as e:
                print(f"Error processing link {link_tag.get('href')}: {e}")
                continue


        # Remove duplicates just in case
        animal_urls_on_page = list(set(animal_urls_on_page))
        return animal_urls_on_page


    def get_next_page_url(self, soup):
        """Finds the URL of the next page."""
        # --- МЕСТО ДЛЯ ВСТАВКИ СЕЛЕКТОРА СЛЕДУЮЩЕЙ СТРАНИЦЫ ---
        # Вам нужно найти на странице списка элемент (обычно ссылка <a>),
        # который ведет на следующую страницу, и определить его CSS-селектор.
        #
        # Ищите элементы пагинации, например кнопки с номерами страниц или стрелки "Вперед".

        # Найдем все ссылки пагинации с классом 'pagination__item'
        pagination_links = soup.select('a.pagination__item')
        next_page_url = None

        # Ищем ссылку, у которой атрибут data-page равен текущему номеру страницы (для перехода на страницу page_num + 1)
        # В HTML data-page для страницы 2 равно 1, для страницы 3 равно 2 и т.д.
        # Значит, для перехода с страницы N на N+1, нам нужна ссылка с data-page = N.
        # В scrape_list_pages current_page_url соответствует странице page_num.
        # Для перехода на следующую страницу (page_num + 1) нам нужна ссылка с data-page = page_num.
        # Исправлено: data-page для страницы N+1 равно N. Значит, для перехода с page_num на page_num+1
        # нам нужна ссылка с data-page = page_num.
        target_data_page = str(self.current_page_num) # Используем self.current_page_num из scrape_list_pages


        for link_tag in pagination_links:
             # Проверяем, что у ссылки есть атрибут data-page и его значение равно ожидаемому
             if link_tag.get('data-page') == target_data_page and 'href' in link_tag.attrs:
                  relative_next_url = link_tag['href']
                  next_page_url = relative_next_url if relative_next_url.startswith('http') else self.base_url + relative_next_url
                  # Ensure the URL is absolute
                  if not next_page_url.startswith('http'):
                       next_page_url = self.base_url + next_page_url

                  # Handle relative URLs in the pagination link
                  if next_page_url.startswith('/'):
                       next_page_url = self.base_url + next_page_url
                  break # Нашли ссылку на следующую страницу, выходим из цикла


        # Проверка стрелки "Вперед" (если есть)
        # В вашем HTML есть стрелка, но она span. Возможно, есть другая стрелка-ссылка?
        # <a class="pagination__item pagination-arrow" href="..."> > </a>
        # Поищите такую ссылку "вперед" в полном HTML файле.
        # Пример селектора для стрелки "Вперед":
        # next_arrow_link_tag = soup.select_one('a.pagination-arrow[rel="next"]') # Пример, нужно проверить актуальный селектор

        # if next_arrow_link_tag and 'href' in next_arrow_link_tag.attrs:
        #      relative_next_url = next_arrow_link_tag['href']
        #      next_page_url = relative_next_url if relative_next_url.startswith('http') else self.base_url + relative_url
        #      if not next_page_url.startswith('http'):
        #           next_page_url = self.base_url + next_page_url
        #      if next_page_url.startswith('/'):
        #           next_page_url = self.base_url + next_page_url
        #      # Если нашли ссылку со стрелкой, она приоритетнее, т.k. ведет непосредственно на следующую
        #      return next_page_url


        return next_page_url

    def scrape_list_pages(self, initial_url, max_pages=5):
        """Scrapes links from multiple list pages with pagination."""
        all_animal_urls = set()
        current_page_url = initial_url
        self.current_page_num = 1 # Добавили атрибут класса для использования в get_next_page_url

        print(f"\n{'=' * 60}")
        print(f"НАЧАЛО СБОРА ССЫЛОК С КАТАЛОГА")
        print(f"Начальный URL: {initial_url}")
        print(f"{'=' * 60}")

        try: # Добавил обработку ошибок для цикла по страницам
            while self.current_page_num <= max_pages:
                print(f"Сбор ссылок со страницы {self.current_page_num}: {current_page_url}")
                html_content = self.get_html(current_page_url)

                if not html_content:
                    print(f"Не удалось получить HTML для страницы {self.current_page_num}. Остановка.")
                    break

                # --- СОХРАНЕНИЕ ПОЛНОГО HTML ПЕРВОЙ СТРАНИЦЫ ДЛЯ ОТЛАДКИ (только для первой страницы) ---
                if self.current_page_num == 1:
                    html_filename = "page_1_full_html.html"
                    try:
                        with open(html_filename, "w", encoding="utf-8") as f:
                            f.write(html_content)
                        print(f"\n--- ПОЛНЫЙ HTML ПЕРВОЙ СТРАНИЦЫ СОХРАНЕН В ФАЙЛ: {html_filename} ---")
                    except Exception as e:
                        print(f"Ошибка при сохранении HTML в файл: {e}")
                # --- КОНЕЦ СОХРАНЕНИЯ ---


                soup = BeautifulSoup(html_content, 'html.parser')
                urls_on_page = self.scrape_links_from_page(current_page_url) # Pass current_page_url to scrape_links_from_page
                all_animal_urls.update(urls_on_page)
                print(f"Найдено {len(urls_on_page)} ссылок на странице {self.current_page_num}. Всего собрано: {len(all_animal_urls)}")

                next_page_url = self.get_next_page_url(soup)

                if next_page_url and self.current_page_num < max_pages:
                    current_page_url = next_page_url
                    self.current_page_num += 1 # Увеличиваем номер страницы только если нашли ссылку на следующую
                    time.sleep(uniform(2, 4)) # Longer pause between list pages
                else:
                    print("Ссылка на следующую страницу не найдена или достигнут лимит страниц. Остановка сбора ссылок.")
                    break
        except Exception as e:
            print(f"Произошла ошибка при сборе ссылок со страниц: {e}")


        print(f"\nЗавершено сбор ссылок. Всего уникальных ссылок: {len(all_animal_urls)}")
        return list(all_animal_urls)


    def scrape_details_from_urls(self, animal_urls, ad_type):
        """Scrapes detailed data from a list of animal detail URLs."""
        all_animals_data = []
        print(f"\n{'=' * 60}")
        print(f"НАЧАЛО СБОРА ДЕТАЛЕЙ ДЛЯ {ad_type.upper()}")
        print(f"Всего ссылок для обработки: {len(animal_urls)}")
        print(f"{'=' * 60}")

        for i, url in enumerate(animal_urls):
            print(f"Обработка {i + 1}/{len(animal_urls)}: {url[:60]}...")
            try: # Добавил обработку ошибок для каждой детальной страницы
                details = self.parse_pet_details(url, ad_type)
                if details:
                    all_animals_data.append(details)
            except Exception as e:
                print(f"Произошла ошибка при парсинге деталей для {url}: {e}")
                # Можно добавить пропуск или запись частичных данных
            time.sleep(uniform(1, 2)) # Pause between detail pages

        print(f"\nЗавершено сбор деталей. Собрано данных для {len(all_animals_data)} животных.")
        return all_animals_data

    def scrape_lost_animals(self, initial_catalog_url, max_pages=5):
        """Scrapes data for lost animals."""
        print("\n" + "="*60)
        print("ЗАПУСК СКРЕЙПИНГА ПРОПАВШИХ ЖИВОТНЫХ")
        print("="*60)

        # 1. Scrape links from list pages
        lost_links = self.scrape_list_pages(initial_catalog_url, max_pages)

        if not lost_links:
            print("Не найдено ссылок для пропавших животных.")
            return pd.DataFrame()

        # 2. Scrape details from individual pages
        lost_data = self.scrape_details_from_urls(lost_links, 'lost')

        if lost_data:
            df_lost = pd.DataFrame(lost_data)
            print(f"\nСобранные данные (Пропавшие, первые 5 строк):\n{df_lost.head()}")
            return df_lost
        else:
            print("Не удалось собрать детальные данные для пропавших животных.")
            return pd.DataFrame()

    def scrape_found_animals(self, initial_catalog_url, max_pages=5):
        """Scrapes data for found animals."""
        print("\n" + "="*60)
        print("ЗАПУСК СКРЕЙПИНГА НАЙДЕННЫХ ЖИВОТНЫХ")
        print("="*60)

        # 1. Scrape links from list pages
        # Note: The initial URL and query parameters might need adjustment for 'found' animals
        # For this example, I'll assume a similar structure or that the initial_catalog_url
        # can be modified (e.g., by changing a query parameter).
        # In a real scenario, you'd need to determine the correct URL for found animals.
        # For demonstration, let's modify the query_params if they were used to build the initial URL.
        # If the initial_catalog_url is hardcoded for 'lost', you'd need a separate one for 'found'.

        # Example: Assuming initial_catalog_url uses query_params and 'PetsSearch[type]=0' for lost
        # We'd need to change 'PetsSearch[type]' for found. Let's assume 'PetsSearch[type]=1' is for found.
        # This requires knowing how the site structures its URLs for different types.

        # If the initial_catalog_url is fixed, you might need to modify the URL string directly
        # or provide a different starting URL for found animals.
        # For now, I'll use the provided initial_catalog_url and assume the link scraping
        # will naturally find 'found' links if they are present on those pages, or
        # require a different starting URL to be passed to this method.

        # Let's assume for demonstration that replacing 'lost' with 'found' in the URL path works
        # or that a different initial_catalog_url is provided for found animals.
        # A more robust solution would involve understanding the URL structure for 'found'.

        # For now, I'll just use the provided initial_catalog_url for demonstration,
        # but highlight this as a point needing real-world verification.
        # If the initial_catalog_url is specifically for lost, you might need a different entry point.

        # --- IMPORTANT: Verify the actual URL structure for FOUND animals on pet911.ru ---
        # You might need a different initial_catalog_url here, e.g.,
        # found_catalog_url = "https://pet911.ru/catalog?PetsSearch%5Btype%5D=1&..."
        # For this example, I'll just use the passed initial_catalog_url, assuming it might list both
        # or you'll provide a specific one for found.

        found_links = self.scrape_list_pages(initial_catalog_url, max_pages)

        if not found_links:
            print("Не найдено ссылок для найденных животных.")
            return pd.DataFrame()

        # Filter links to ensure we only process 'found' links if the list page contains both
        found_links_filtered = [link for link in found_links if '/found/' in link]
        print(f"Отфильтровано {len(found_links_filtered)} ссылок, содержащих '/found/'.")

        if not found_links_filtered:
             print("После фильтрации не осталось ссылок на найденных животных.")
             return pd.DataFrame()


        # 2. Scrape details from individual pages
        found_data = self.scrape_details_from_urls(found_links_filtered, 'found')

        if found_data:
            df_found = pd.DataFrame(found_data)
            print(f"\nСобранные данные (Найденные, первые 5 строк):\n{df_found.head()}")
            return df_found
        else:
            print("Не удалось собрать детальные данные для найденных животных.")
            return pd.DataFrame()


# Example Usage:
if __name__ == "__main__":
    # Define the initial URLs for lost and found animals
    # IMPORTANT: Replace these with the actual initial URLs for lost and found
    # animals on pet911.ru that you found by inspecting the website.
    lost_animals_initial_url = "https://pet911.ru/catalog?PetsSearch%5Blatitude%5D=55.45035126520772&PetsSearch%5Blongitude%5D=37.36999511718751&PetsSearch%5BlatTopLeft%5D=56.02292412058638&PetsSearch%5BlngTopLeft%5D=39.47937011718751&PetsSearch%5BlatBotRight%5D=54.86930913144641&PetsSearch%5BlngBotRight%5D=35.26062011718751&zoom=9&PetsSearch%5Banimal%5D=on&PetsSearch%5Banimal%5D=-1&PetsSearch%5Btype%5D=0&PetsSearch%5BdateField%5D=1&PetsSearch%5BdatePeriod%5D=4&PetsSearch%5BshowClosedPets%5D=0&PetsSearch%5BshowClosedPets%5D=1"

    # You would need to determine the correct initial URL for found animals
    # For this example, let's just use the same URL for demonstration, but note this limitation.
    # A real implementation needs the correct 'found' URL.
    found_animals_initial_url = "https://pet911.ru/catalog?PetsSearch%5Blatitude%5D=55.45035126520772&PetsSearch%5Blongitude%5D=37.36999511718751&PetsSearch%5BlatTopLeft%5D=56.02292412058638&PetsSearch%5BlngTopLeft%5D=39.47937011718751&PetsSearch%5BlatBotRight%5D=54.86930913144641&PetsSearch%5BlngBotRight%5D=35.26062011718751&zoom=9&PetsSearch%5Banimal%5D=on&PetsSearch%5Banimal%5D=-1&PetsSearch%5Btype%5D=1&PetsSearch%5BdateField%5D=1&PetsSearch%5BdatePeriod%5D=4&PetsSearch%5BshowClosedPets%5D=0&PetsSearch%5BshowClosedPets%5D=1" # Assuming type=1 is for found


    scraper = Pet911Scraper()

    # Scrape lost animals
    print("\n--- Starting Lost Animals Scrape ---")
    df_lost_pets = scraper.scrape_lost_animals(lost_animals_initial_url, max_pages=10) # Scrape first 10 pages
    if not df_lost_pets.empty:
        output_filename_lost = "pet911_lost_pets_scraped_connector.csv"
        df_lost_pets.to_csv(output_filename_lost, index=False, encoding='utf-8-sig')
        print(f"\nSaved scraped lost pets data to {output_filename_lost}")
    else:
        print("\nNo lost pets data scraped.")

    # Scrape found animals
    print("\n--- Starting Found Animals Scrape ---")
    df_found_pets = scraper.scrape_found_animals(found_animals_initial_url, max_pages=10) # Scrape first 10 pages
    if not df_found_pets.empty:
         output_filename_found = "pet911_found_pets_scraped_connector.csv"
         df_found_pets.to_csv(output_filename_found, index=False, encoding='utf-8-sig')
         print(f"\nSaved scraped found pets data to {output_filename_found}")
    else:
        print("\nNo found pets data scraped.")

    print("\nScraping process finished.")
