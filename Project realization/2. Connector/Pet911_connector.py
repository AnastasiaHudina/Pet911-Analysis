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
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Accept-Language': 'en-US,en;q=0.9,ru;q=0.8',
            'DNT': '1',
            'Upgrade-Insecure-Requests': '1',
        }

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
        """Правильно определяет статус объявления на основе card-notice элементов и типа объявления."""
        card_notice = soup.find('div', class_='card-notice')

        if card_notice:
            notice_title = card_notice.find('div', class_='card-notice__title')
            if notice_title:
                notice_text = notice_title.get_text().strip().lower()
                if ad_type == 'потерян':
                    if any(phrase in notice_text for phrase in ['питомец нашелся', 'животное найдено', 'питомец найден']):
                        return 'питомец найден'
                    else:
                         # Если есть card-notice, но статус не "найден", то он "в поиске"
                         return 'в поиске'
                elif ad_type == 'найден':
                    if any(phrase in notice_text for phrase in ['хозяин нашелся', 'хозяин найден']):
                        return 'хозяин найден'
                    else:
                         # Если есть card-notice, но статус не "хозяин найден", то он "ищут хозяина"
                         return 'ищут хозяина'

        # Если card-notice не найден, используем запасной вариант с поиском по всему тексту страницы
        page_text = soup.get_text().lower()
        if ad_type == 'потерян':
            if any(phrase in page_text for phrase in ['питомец нашелся', 'животное найдено', 'питомец найден']):
                return 'питомец найден'
            else:
                return 'в поиске'
        elif ad_type == 'найден':
            if any(phrase in page_text for phrase in ['хозяин нашелся', 'хозяин найден']):
                return 'хозяин найден'
            else:
                return 'ищут хозяина'
        else: # Если ad_type неизвестен
             return 'статус неизвестен'


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

    def parse_age(self, age_text):
        """Парсит текст возраста и возвращает число и единицу измерения."""
        if not age_text or age_text == 'Неизвестно':
            return 'Неизвестно'

        age_text = age_text.lower()

        month_patterns = [r'(\d+)\s*(месяц|месяца|месяцев)', r'(\d+)\s*мес']
        year_patterns = [r'(\d+)\s*(год|года|лет)', r'(\d+)\s*г']

        for pattern in month_patterns:
            match = re.search(pattern, age_text)
            if match:
                return f"{match.group(1)}, месяц"

        for pattern in year_patterns:
            match = re.search(pattern, age_text)
            if match:
                return f"{match.group(1)}, год"

        # Handle cases like "около 3 лет"
        around_match = re.search(r'около\s*(\d+)\s*(год|года|лет|месяц|месяца|месяцев)', age_text)
        if around_match:
             number = around_match.group(1)
             unit = around_match.group(2)
             if 'месяц' in unit or 'мес' in unit:
                  return f"{number}, месяц"
             elif 'год' in unit or 'лет' in unit or 'г' in unit:
                  return f"{number}, год"

        number_match = re.search(r'\d+', age_text)
        if number_match:
             return age_text.strip()

        return 'Неизвестно' # Return Неизвестно if no relevant info found

    def parse_color_and_patterns(self, text):
        """Извлекает из текста цвета и слова, связанные с узорами, включая составные цвета."""
        if not text:
            return 'Неизвестно'

        text = text.lower()
        extracted_info = []

        # СПИСОК ЦВЕТОВ И КЛЮЧЕВЫХ СЛОВ
        color_keywords = ['белый', 'белая', 'белые', 'белое', 'серый', 'серое', 'серая', 'серые',
                          'черный', 'черная', 'черные', 'черное', 'чёрное', 'чёрная', 'чёрный', 'чёрные',
                          'рыжий', 'рыжая', 'рыжие', 'рыжее', 'коричневый', 'коричневая', 'коричневое', 'коричневые',
                          'белую', 'черную', 'серую', 'рыжую', 'коричневую',
                          'трехцветный', 'трёхцветный', 'трехшерстный', 'двухцветный', 'двухшерстный'] # Added more forms

        eye_color_keywords = ['голубой', 'зелёный', 'коричневый', 'желтый', 'серый', 'черный'] # Added eye colors

        pattern_keywords = ['полоски', 'полосы', 'пятно', 'пятна', 'пятнышки', 'полоса', 'тигровый', 'мраморный',
                            'пятнышка', 'пятнышко', 'пятен'] # Added more forms

        all_keywords = color_keywords + pattern_keywords + eye_color_keywords

        # Find individual color and pattern keywords
        # Use word boundaries and process the lowercased text
        words = re.findall(r'\b\w+\b', text)
        found_keywords = [word for word in words if word in all_keywords]

        # Find hyphenated colors
        hyphenated_color_patterns = [r'(бело|черно|чёрно|серо|рыже|коричнево)-(\w+)', r'(\w+)-(бело|черно|чёрно|серо|рыже|коричнево)']
        for pattern in hyphenated_color_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                 extracted_info.append('-'.join(match)) # Add hyphenated words as a single string

        extracted_info.extend(found_keywords)

        processed_info = []
        i = 0
        while i < len(words):
             if words[i] in color_keywords and i + 1 < len(words) and words[i+1] in color_keywords:
                  processed_info.append(f"{words[i]} {words[i+1]}")
                  i += 2
             elif words[i] in all_keywords:
                  processed_info.append(words[i])
                  i += 1
             else:
                  i += 1

        final_extracted_info = list(set(extracted_info + processed_info))

        if final_extracted_info:
             return ', '.join(final_extracted_info)
        else:
            return 'Неизвестно'

    def extract_breed(self, text):
        "Извлекает породу из текста описания по заданному списку."
        if not text:
            return 'Неизвестно'

        text = text.lower()
        # породы
        breeds = ['овчарка', 'шпиц', 'лабрадор', 'немецкая овчарка', 'лабрадор-ретривер',
                  'золотистый ретривер', 'французский бульдог', 'бульдог', 'пудель', 'бигль',
                  'ротвейлер', 'такса', 'померанский шпиц', 'йоркширский терьер',
                  'сибирский хаски', 'доберман', 'боксер', 'ши-тцу', 'английский кокер-спаниель',
                  'чихуахуа', 'австралийская овчарка', 'шелти', 'мопс', 'мальтийская болонка',
                  'акита-ину', 'вельш-корги пемброк', 'бордер-колли', 'шнауцер',
                  'мейн-кун', 'британская короткошерстная', 'сиамская', 'абиссинская', 'персидская',
                  'русская голубая', 'бенгальская', 'сфинкс (канадский)', 'шотландская вислоухая',
                  'рэгдолл', 'американская короткошерстная', 'ориентальная', 'турецкая ангора',
                  'норвежская лесная', 'девон-рекс', 'корниш-рекс', 'бурманская', 'сингапурская',
                  'манул', 'египетская мау', 'сомали', 'манчкин', 'украинский левкой',
                  'селкирк-рекс', 'бобтейл', 'корги', 'домашняя']

        found_breeds = [breed for breed in breeds if breed in text]

        if found_breeds:
            # Return the first found breed for simplicity, or join them if multiple found
            return ', '.join(found_breeds)
        else:
            # Also try to find keywords like "метис", "беспородный"
            if 'метис' in text: return 'метис'
            if 'беспородный' in text: return 'беспородный'
            return 'Неизвестно'


    def parse_pet_details(self, url): # Removed ad_type_from_list parameter
        """Парсит детальную информацию с страницы объявления"""
        html_content = self.get_html(url)
        if not html_content:
            return None

        soup = BeautifulSoup(html_content, 'html.parser')

        data = {
            'url': url,
        }

        try:
            # 1. id: Extract ID from the URL using the new pattern
            match = re.search(r'/(rf|rl)(\d{7})$', url) # Use the passed URL
            data['id'] = match.group(1) + match.group(2) if match else None # Combine letters and digits for ID

            # Определяем тип объявления ('найден' или 'потерян') на основе второй буквы ID
            if data['id'] and len(data['id']) > 1:
                 if data['id'][1].lower() == 'f':
                      data['тип объявления'] = 'найден'
                 elif data['id'][1].lower() == 'l':
                      data['тип объявления'] = 'потерян'
                 else:
                      data['тип объявления'] = 'Неизвестно'
            else:
                 data['тип объявления'] = 'Неизвестно'

        except Exception as e:
            print(f"Error extracting ID or determining ad_type from URL {url}: {e}")
            data['id'] = None
            data['тип объявления'] = 'Неизвестно'

        # Регион часто можно извлечь из URL или найти на странице.
        region_match = re.search(r'/([^/]+)/(lost|found)/(dog|cat)', url)
        data['регион'] = region_match.group(1).replace('-', ' ').title() if region_match else None
        if data['регион'] == 'Pet911.Ru':
          data['регион'] = ''

        # Используем определенный ad_type для определения статуса
        data['статус'] = self.determine_status(soup, data['тип объявления']) # Pass the determined ad_type

        # ДАННЫЕ О ЖИВОТНОМ

        # Изначально определяем тип животного по URL
        if '/dog/' in url:
            data['тип_животного'] = 'собака'
        elif '/cat/' in url:
            data['тип_животного'] = 'кошка'
        elif '/bird/' in url:
            data['тип_животного'] = 'птица'
        elif '/ferret/' in url: # Убедимся, что эти типы не удалены
            data['тип_животного'] = 'хорек'
        elif '/other/' in url: # Убедимся, что эти типы не удалены
            data['тип_животного'] = 'другой'

        else:
            data['тип_животного'] = None

        # СЕЛЕКТОРЫ
        selectors = {
            # Пример: 'название_поля': 'ваш_css_селектор',
            # Селектор для региона, если он есть отдельным элементом, а не только в URL
            'регион': 'md-font card-map__address',
            # Селектор для даты публикации объявления
            'дата_публикации': 'div.card-info:has(.gray-dk-color.card-info__title:-soup-contains("Добавлено")) .card-info__value',
            # Селектор для типа животного (может совпадать с извлеченным из URL)
            'тип_животного': '.pet-card__type .pet-card__text', # <-- ОБНОВИТЕ ЭТОТ СЕЛЕКТОР
            # Селектор для пола животного
            'пол': 'div.card-info:has(.gray-dk-color.card-info__title:-soup-contains("Пол питомца")) .card-info__value',
            # Селектор для возраста животного
            'возраст': '.pet-card__age .pet-card__text', # <-- ОБНОВИТЕ ЭТОТ СЕЛЕКТОР
            # Селектор для блока с описанием
            'описание': 'body > div.card.card-print > div.container > div > div.card__content > div.text.text-lt.card__descr.content', # Updated selector
            # Селектор для всех изображений в галерее (для подсчета фото)
            'фотографии': '.card-slider .swiper-slide img.img-crop', # Updated selector to exclude the background image
            # Селектор для блока с контактной информации (для проверки наличия контактов)
            'наличие контактной информации': 'btn btn-fill-accent-lt card__show-number js-popup-btns', # <-- ОБНОВИТЕ ЭТОТ СЕЛЕКТОР
            # Селектор для всех комментариев (для подсчета комментариев)
            'комментарии': 'div.section__title h2:-soup-contains("Комментариев")', # Updated selector for comment count
            'порода_селектор': 'card-info__value', # Added a selector for breed if it exists separately
            'место_события_селектор': 'div.card-map__info > div.md-font.card-map__address', # Updated selector for location
            # Селектор для даты находки (для найденных животных)
            'дата находки': 'div.card-info:has(.gray-dk-color.card-info__title:-soup-contains("Найден(а)")) .card-info__value',
            # Селектор для даты пропажи (для потерянных животных)
            'дата пропажи': 'div.card-info:has(.gray-dk-color.card-info__title:-soup-contains("Пропал(а)")) .card-info__value',
            'id' : 'card-info__value',

        }

        # Поля, которые будем пытаться извлечь селекторами в первую очередь
        fields_to_extract_by_selector = [
            'регион', 'дата_публикации', 'тип_животного',
            'пол', 'возраст', 'описание', 'фотографии', # Removed 'окрас_селектор'
            'наличие_контактной_информации', 'комментарии', 'дата находки', 'дата пропажи', 'порода_селектор', 'место_события_селектор' # Changed key names for selectors
        ]

        # Initialize fields
        data['окрас'] = 'Неизвестно'
        data['порода'] = 'Неизвестно'
        data['место события'] = 'Неизвестно'


        for key in fields_to_extract_by_selector:
            selector = selectors.get(key)
            if not selector:
                continue # Пропускаем, если селектор не определен

            try:
                if key == 'описание':
                    description_tag = soup.select_one(selector)
                    description_text = description_tag.text.strip() if description_tag else ''
                    data['описание'] = description_text # Сохраняем полное описание
                    # Calculate word count
                    data['Длина_описания_в_словах'] = len(description_text.split()) if description_text else 0
                    data['наличие_описания'] = bool(description_text) # Check if description exists

                elif key == 'фотографии': # Modified to handle 'фотографии' key
                    photo_tags = soup.select(selector)
                    data['есть_фото'] = bool(photo_tags)
                    data['количество_фото'] = len(photo_tags)
                elif key == 'наличие_контактной_информации':
                     data['есть_контакты'] = soup.select_one(selector) is not None
                elif key == 'комментарии':
                    comment_tag = soup.select_one(selector)
                    if comment_tag:
                        comment_text = comment_tag.get_text().strip()
                        match = re.search(r'\d+', comment_text)
                        data['количество_комментариев'] = int(match.group(0)) if match else 0
                    else:
                        data['количество_комментариев'] = 0 # Set to 0 if the selector is not found


                elif key == 'регион': # Обработка региона с страницы, если есть
                    tag = soup.select_one(selector)
                    data['регион'] = tag.text.strip() if tag else data.get('регион', 'Неизвестно') # Предпочитаем данные с страницы
                elif key == 'тип_животного': # Обработка типа животного со страницы
                     tag = soup.select_one(selector)
                     # Если нашли тип животного селектором, обновляем его
                     data['тип_животного'] = tag.text.strip() if tag else data.get('тип_животного', 'Неизвестно')
                elif key == 'возраст': # Special handling for age
                    tag = soup.select_one(selector)
                    age_text = tag.text.strip() if tag else 'Неизвестно'
                    data['возраст'] = self.parse_age(age_text) # Use the new parse_age method
                elif key == 'порода_селектор': # Handle breed extraction from selector
                    tag = soup.select_one(selector)
                    data['порода'] = tag.text.strip() if tag else 'Неизвестно' # Prioritize breed from selector
                elif key == 'место_события_селектор': # Handle location extraction from selector
                    tag = soup.select_one(selector)
                    data['место события'] = tag.text.strip() if tag else 'Неизвестно' # Prioritize location from selector


                else:
                    tag = soup.select_one(selector)
                    data[key] = tag.text.strip() if tag else 'Неизвестно'
            except Exception as e:
                print(f"Error extracting {key} for {url} using selector {selector}: {e}")
                if key == 'описание':
                     data['описание'] = None
                     data['Длина_описания_в_словах'] = 0
                     data['наличие_описания'] = False
                elif key == 'фотографии': # Modified to handle 'фотографии' key
                    data['есть_фото'] = False
                    data['количество_фото'] = 0
                elif key == 'есть контакты': data['есть_контакты'] = False
                elif key == 'комментарии': data['количество_комментариев'] = 0 # Set to 0 on error
                elif key == 'регион': data['регион'] = data.get('регион', 'Неизвестно')
                elif key == 'тип_животного': data['тип_животного'] = data.get('тип_животного', 'Неизвестно')
                elif key == 'возраст': data['возраст'] = 'Неизвестно' # Set to Неизвестно on error for age
                elif key == 'порода_селектор': data['порода'] = 'Неизвестно' # Set to Неизвестно on error for breed selector
                elif key == 'место_события_селектор': data['место события'] = 'Неизвестно' # Set to Неизвестно on error for location selector
                elif key in ['дата находки', 'дата пропажи']: # Устанавливаем None для даты события при ошибке
                    # При ошибке парсинга даты, оставляем поле без изменения, оно будет None если не было найдено ранее
                    pass
                else: data[key] = 'Неизвестно'

        # Порода
        # Проверяем, не нашли ли уже селектором. Если нет, пытаемся найти в описании.
        if data.get('порода') is None or data['порода'] == 'Неизвестно' or data['порода'] == '': # Added empty string check
            extracted_breed = self.extract_breed(data.get('описание'))
            if extracted_breed:
                 data['порода'] = extracted_breed.strip()
            else:
                 data['порода'] = 'Неизвестно' # Устанавливаем в Неизвестно, если не нашли ни селектором, ни в описании

        # Окрас (из описания)
        # Note: 'окрас_селектор' key is removed, so this block will always be executed to extract color from description
        extracted_color_description = self.parse_color_and_patterns(data.get('описание'))

        if extracted_color_description and extracted_color_description != 'Неизвестно':
             data['окрас'] = extracted_color_description
        else:
             data['окрас'] = 'Неизвестно' # Устанавливаем в Неизвестно, если не нашли ни селектором, ни в описании


        # Тип животного (если не удалось определить по URL или селектором)
        # Проверяем, не нашли ли уже по URL или селектором. Если нет, пытаемся найти в описании.
        if data.get('тип_животного') is None or data['тип_животного'] == 'Неизвестно':
             animal_type_patterns = ['собака', 'кошка', 'щенок', 'котенок', 'пёс', 'кошечка', 'котёнок', 'Собака', 'Кошка'] # Добавьте сюда ключевые слова для типа животного
             extracted_type = self.extract_from_description(data.get('описание'), animal_type_patterns)
             if extracted_type:
                  data['тип_животного'] = extracted_type.strip()
             else:
                  data['тип_животного'] = 'Неизвестно'


        # Возраст (из описания, если не найден селектором)
        # Проверяем, не нашли ли уже селектором. Если нет, пытаемся найти в описании.
        if data.get('возраст') is None or data['возраст'] == 'Неизвестно':
            age_patterns = [r'возраст[:\s]*([^\n\.]+)', 'лет', 'год', 'года', 'месяц', 'месяца', 'месяцев', r'около\s*\d+'] # Added raw string for regex
            extracted_age = self.extract_from_description(data.get('описание'), age_patterns)
            if extracted_age:
                 data['возраст'] = self.parse_age(extracted_age) # Use parse_age for extracted description age
            else:
                 data['возраст'] = 'Неизвестно' # Устанавливаем в Неизвестно, если не нашли ни селектором, ни в описании


        location_patterns = [r'место[:\s]*([^\n\.]+)', r'район[:\s]*([^\n\.]+)', r'адрес[:\s]*([^\n\.]+)']
        # Проверяем, не нашли ли место события селектором. Если нет, пытаемся найти по паттерну.
        if data.get('место события') is None or data['место события'] == 'Неизвестно' or data['место события'] == '': # Corrected key name and added empty string check
             extracted_location = self.extract_by_pattern(soup, location_patterns)
             if extracted_location:
                  data['место события'] = extracted_location.strip() # Changed key to 'место события'
             # No else needed here, as we only update if something is found by pattern and selector didn't find it.


        # КОНТАКТЫ И ВЗАИМОДЕЙСТВИЕ (Используют extract_by_pattern или простые проверки, возможно, потребуют доработки)
        phone_match = re.search(r'[\+\(]?[1-9][0-9 .\-\(\)]{8,}[0-9]', soup.get_text()) # <-- ПРОВЕРЬТЕ ШАБЛОН НОМЕРА ТЕЛЕФОНА
        data['есть_контакты'] = bool(phone_match)

        views_match = re.search(r'(\d+)\s*(просмотр|view)', soup.get_text().lower()) # <-- ПРОВЕРЬТЕ ШАБЛОН ПРОСМОТРОВ
        data['просмотры'] = int(views_match.group(1)) if views_match else None

        # Особые приметы (Используют поиск по ключевым словам в описании)
        # Этот код ищет ключевые слова в уже извлеченном описании.
        if data.get('описание'): # Используем извлеченное описание
            marks_keywords = ['особые приметы', 'отличительные черты', 'приметы', 'метка', 'шрам', 'отметины', 'пятна']
            for keyword in marks_keywords:
                if keyword in data['описание'].lower():
                    sentences = re.split(r'[.!?]', data['описание'])
                    for sentence in sentences:
                        if keyword in sentence.lower():
                            data['особые приметы'] = sentence.strip()
                            break
                    break
            else:
                data['особые приметы'] = None
        else:
            data['особые приметы'] = None


        # Убедимся, что все требуемые поля присутствуют в словаре data, даже если они None или 'Неизвестно'
        required_fields = [
            'id', 'url', 'тип объявления', 'регион', 'дата_публикации', 'дата находки', 'дата пропажи', # Вернули оба поля даты
            'тип_животного', 'пол', 'возраст', 'окрас', 'есть_фото', 'количество_фото',
            'Длина_описания_в_словах', 'наличие_описания', 'есть_контакты', 'количество_комментариев', 'место события', 'порода' # Added new fields
        ]
        for field in required_fields:
            if field not in data:
                data[field] = None # Или 'Неизвестно', в зависимости от предпочтений


        return data


    def scrape_links_from_page(self, url):
        """Scrapes animal detail URLs from a list page."""
        all_animal_urls = set()
        html_content = self.get_html(url)
        if not html_content:
            return []

        soup = BeautifulSoup(html_content, 'html.parser') # Using html.parser for potentially broader compatibility
        animal_urls_on_page = []

        # Пока используется широкий поиск по всем ссылкам и их фильтрация:
        all_links = soup.select('a[href]') # <-- МОЖЕТ ПОТРЕБОВАТЬСЯ УТОЧНЕНИЕ

        for link_tag in all_links:
            try:
                relative_url = link_tag['href']
                # Фильтруем ссылки, которые похожи на детальные страницы животных
                if '/card/' in relative_url or re.search(r'/(rf|rl)\d{7}$', relative_url): # Updated filtering based on ID pattern
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

        # Найдем все ссылки пагинации с классом 'pagination__item'
        pagination_links = soup.select('a.pagination__item')
        next_page_url = None

        current_url = soup.select_one('link[rel="canonical"]')
        if current_url and 'href' in current_url.attrs:
             current_url_str = current_url['href']
        else:
             pass


        target_data_page = str(self.current_page_num) # Используем self.current_page_num из scrape_list_pages
        for link_tag in pagination_links:
             if link_tag.get('data-page') == target_data_page and 'href' in link_tag.attrs:
                  relative_next_url = link_tag['href']
                  next_page_url = relative_next_url if relative_next_url.startswith('http') else self.base_url + relative_url
                  # Ensure the URL is absolute
                  if not next_page_url.startswith('http'):
                       next_page_url = self.base_url + next_page_url

                  # Handle relative URLs in the pagination link
                  if next_page_url.startswith('/'):
                       next_page_url = self.base_url + next_page_url
                  break # Нашли ссылку на следующую страницу, выходим из цикла

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
                # КОНЕЦ СОХРАНЕНИЯ


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


    def scrape_and_save(self, initial_lost_url, initial_found_url, max_pages=5):
        """Scrapes data for lost and found animals and saves to separate files."""
        all_urls = self.scrape_list_pages(initial_lost_url, max_pages) # Scrape from the lost page first, can extend to found later
        all_urls.extend(self.scrape_list_pages(initial_found_url, max_pages)) # Scrape from found page as well
        all_urls = list(set(all_urls)) # Remove duplicates

        if not all_urls:
            print("Не найдено ссылок для обработки.")
            return pd.DataFrame(), pd.DataFrame()

        all_data = []
        print(f"\n{'=' * 60}")
        print(f"НАЧАЛО СБОРА ДЕТАЛЕЙ СО ВСЕХ ССЫЛОК")
        print(f"Всего ссылок для обработки: {len(all_urls)}")
        print(f"{'=' * 60}")


        for i, url in enumerate(all_urls):
            print(f"Обработка {i + 1}/{len(all_urls)}: {url[:60]}...")
            try:
                details = self.parse_pet_details(url) # Call parse_pet_details without ad_type
                if details:
                    all_data.append(details)
            except Exception as e:
                print(f"Произошла ошибка при парсинге деталей для {url}: {e}")
            time.sleep(uniform(1, 2)) # Pause between detail pages

        if not all_data:
            print("Не удалось собрать детальные данные.")
            return pd.DataFrame(), pd.DataFrame()

        df_all = pd.DataFrame(all_data)

        # Filter into lost and found DataFrames based on 'тип объявления' determined by ID
        df_lost = df_all[df_all['тип объявления'] == 'потерян'].copy()
        df_found = df_all[df_all['тип объявления'] == 'найден'].copy()

        # Remove unnecessary date columns based on type and requested columns
        columns_to_drop = ['дата находки', 'просмотры', 'особые приметы']
        df_lost = df_lost.drop(columns=[col for col in columns_to_drop if col in df_lost.columns])

        columns_to_drop = ['дата пропажи', 'просмотры', 'особые приметы']
        df_found = df_found.drop(columns=[col for col in columns_to_drop if col in df_found.columns])


        print(f"\nСобранные данные (Пропавшие, первые 5 строк):\n{df_lost.head()}")
        print(f"\nСобранные данные (Найденные, первые 5 строк):\n{df_found.head()}")


        return df_lost, df_found



# Example Usage:
if __name__ == "__main__":
    # Определите начальный URL-адрес для потерянных животных (из пользовательской уценки)
    lost_animals_initial_url = "https://pet911.ru/catalog?PetsSearch%5Blatitude%5D=55.45035126520772&PetsSearch%5Blongitude%5D=37.36999511718751&PetsSearch%5BlatTopLeft%5D=56.02292412058638&PetsSearch%5BlngTopLeft%5D=39.47937011718751&PetsSearch%5BlatBotRight%5D=54.86930913144641&PetsSearch%5BlngBotRight%5D=35.26062011718751&zoom=9&PetsSearch%5Banimal%5D=on&PetsSearch%5Banimal%5D=-1&PetsSearch%5Btype%5D=0&PetsSearch%5BdateField%5D=1&PetsSearch%5Bperiod%5D=all"
    

    found_animals_initial_url = "https://pet911.ru/catalog?PetsSearch%5Blatitude%5D=55.45035126520772&PetsSearch%5Blongitude%5D=37.36999511718751&PetsSearch%5BlatTopLeft%5D=56.02292412058638&PetsSearch%5BlngTopLeft%5D=39.47937011718751&PetsSearch%5BlatBotRight%5D=54.86930913144641&PetsSearch%5BlngBotRight%5D=35.26062011718751&zoom=9&PetsSearch%5Banimal%5D=on&PetsSearch%5Banimal%5D=-1&PetsSearch%5Btype%5D=1&PetsSearch%5BdateField%5D=1&PetsSearch%5Bperiod%5D=all" # Assuming type=1 is for found
    scraper = Pet911Scraper()

    # Скэпинг и сохранение
    df_lost_pets, df_found_pets = scraper.scrape_and_save(lost_animals_initial_url, found_animals_initial_url, max_pages=1) # количество страниц парсить

    if not df_lost_pets.empty:
        df_lost_pets.to_csv("Pet911_lost.csv", index=False, encoding='utf-8-sig')
        print("\nSaved scraped lost pets data to Pet911_lost.csv")

    if not df_found_pets.empty:
         df_found_pets.to_csv("Pet911_found.csv", index=False, encoding='utf-8-sig')
         print("\nSaved scraped found pets data to Pet911_found.csv")


    print("\nRefactoring complete. The code has been structured into the Pet911Scraper class.")
    print("Please update the CSS selectors for list items, detail fields, and pagination links based on the actual website structure.")
    print("Uncomment the example usage section at the bottom to run the scraper.")
