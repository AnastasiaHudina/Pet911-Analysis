from .deps import *



# ----------------------------------------------------------------------------------------------------------------------
# Константы по умолчанию (пути/названия столбцов)
# ----------------------------------------------------------------------------------------------------------------------
DEFAULT_LOST_FILE = 'data/Dataset_final_Pet911_lost.csv'
DEFAULT_FOUND_FILE = 'data/dataset_final_Pet911_found.csv'
DEFAULT_OUTPUT_DIR = 'results/Результаты 5 главы анализа'

COLUMN_NAMES_LOST = [
    'url', 'id', 'тип объявления', 'регион', 'статус', 'тип_животного',
    'окрас', 'порода', 'место события', 'дата_публикации', 'пол', 'возраст',
    'описание', 'Длина_описания_в_словах', 'наличие_описания', 'есть_фото',
    'количество_фото', 'количество_комментариев', 'дата пропажи', 'есть_контакты'
]

COLUMN_NAMES_FOUND = [
    'url', 'id', 'тип объявления', 'регион', 'статус', 'тип_животного',
    'окрас', 'порода', 'место события', 'дата_публикации', 'пол', 'возраст',
    'описание', 'Длина_описания_в_словах', 'наличие_описания', 'есть_фото',
    'количество_фото', 'количество_комментариев', 'дата находки', 'есть_контакты'
]

# Словарь замены русских дней недели
DAY_MAP = {'пн': 'Mon', 'вт': 'Tue', 'ср': 'Wed', 'чт': 'Thu', 'пт': 'Fri', 'сб': 'Sat', 'вс': 'Sun'}

# Ключевые города для определения "город/область"
URBAN_KEYWORDS = ['москва', 'санкт-петербург', 'vidnoye', 'kolomna', 'obninsk', 'moskva']


# ----------------------------------------------------------------------------------------------------------------------
# Класс-аналитик
# ----------------------------------------------------------------------------------------------------------------------
class Pet911Analyzer:
    """
    Класс, содержащий всю логику из исходного скрипта в методах.
    - Конструктор принимает пути к csv и директорию для результатов.
    - Вызов run() последовательно выполняет загрузку, предобработку, генерацию графиков и сохранение вывода.
    """

    def __init__(self,
                 lost_file: str = DEFAULT_LOST_FILE,
                 found_file: str = DEFAULT_FOUND_FILE,
                 output_dir: str = DEFAULT_OUTPUT_DIR):
        self.lost_file = lost_file
        self.found_file = found_file
        self.output_dir = output_dir

        # Датафреймы будут храниться как атрибуты
        self.lost_df = pd.DataFrame()
        self.found_df = pd.DataFrame()

        # Подготовка стилей графиков (как в оригинале)
        plt.rcParams['font.size'] = 12
        plt.rcParams['axes.labelsize'] = 12
        plt.rcParams['axes.titlesize'] = 14
        sns.set_style("whitegrid")

        # Создаём папку вывода
        os.makedirs(self.output_dir, exist_ok=True)

    # ----------------------------- Работа с файлами и загрузка -----------------------------
    def load_data(self, file_path: str, columns: list) -> pd.DataFrame:
        """
        Загружает CSV с заданными колонками. Поведение совпадает с оригиналом:
        - использует encoding='utf-8'
        - header=None и передаёт names=columns
        - удаляет первую строку, если она похоже на заголовки (проверяется по 'url')
        """
        try:
            df = pd.read_csv(file_path, names=columns, header=None, encoding='utf-8')
            # Удаляем первую строку, если это заголовки (как в оригинале)
            if isinstance(df.iloc[0]['url'], str) and 'http' not in df.iloc[0]['url']:
                df = df.drop(0).reset_index(drop=True)
            return df
        except Exception as e:
            print(f"❌ Ошибка загрузки {file_path}: {e}")
            return pd.DataFrame()

    # ----------------------------- Вспомогательные функции для обработки -----------------------------
    @staticmethod
    def parse_russian_date(date_str: str):
        """
        Парсит строку вида 'пн, 01.01.2020' -> pd.Timestamp
        Поведение и проверки совпадают с оригиналом.
        """
        if pd.isna(date_str) or str(date_str).strip() in ['Неизвестно', '', 'nan']:
            return pd.NaT
        try:
            parts = str(date_str).strip().split(', ')
            if len(parts) != 2:
                return pd.NaT
            day_en = DAY_MAP.get(parts[0].strip())
            if not day_en:
                return pd.NaT
            full_str = f"{day_en}, {parts[1]}"
            return pd.to_datetime(full_str, format='%a, %d.%m.%Y', errors='coerce')
        except Exception:
            return pd.NaT

    @staticmethod
    def clean_age(age):
        """
        Очищает поле возраста и возвращает число (float) или np.nan — как в оригинале.
        """
        if pd.isna(age) or str(age).strip() in ['Неизвестно', '', 'nan', 'не указан']:
            return np.nan
        try:
            num_str = ''.join(filter(str.isdigit, str(age).split(',')[0]))
            return float(num_str) if num_str else np.nan
        except Exception:
            return np.nan

    @staticmethod
    def is_pedigree(breed):
        """
        Определяет породистость: если неизвестно или 'метис' -> 'Нет', иначе 'Да'
        """
        if pd.isna(breed) or breed in ['Неизвестно', 'метис']:
            return 'Нет'
        return 'Да'

    # ----------------------------- Подготовка данных -----------------------------
    def prepare_data(self):
        """
        Выполняет все шаги предобработки, идентичные оригиналу:
        - парсит даты
        - считает время_до_публикации
        - очищает возраст
        - определяет тип_местности
        - помечает породистость
        """
        # Загружаем
        print("🔍 Начало загрузки данных...")
        self.lost_df = self.load_data(self.lost_file, COLUMN_NAMES_LOST)
        self.found_df = self.load_data(self.found_file, COLUMN_NAMES_FOUND)

        if self.lost_df.empty or self.found_df.empty:
            print("❌ Не удалось загрузить данные. Проверьте пути к файлам.")
            raise FileNotFoundError("Один из входных файлов не загружен")

        print("✅ Данные успешно загружены")
        print(f"📊 Пропавшие: {len(self.lost_df)}, Найденные: {len(self.found_df)}")

        # Парсинг дат и расчёт времени до публикации (lost)
        for col in ['дата_публикации', 'дата пропажи']:
            if col in self.lost_df.columns:
                self.lost_df[col] = self.lost_df[col].astype(str).apply(self.parse_russian_date)
        self.lost_df['время_до_публикации'] = (
            self.lost_df['дата_публикации'] - self.lost_df['дата пропажи']
        ).dt.days

        # Парсинг дат и расчёт времени до публикации (found)
        for col in ['дата_публикации', 'дата находки']:
            if col in self.found_df.columns:
                self.found_df[col] = self.found_df[col].astype(str).apply(self.parse_russian_date)
        self.found_df['время_до_публикации'] = (
            self.found_df['дата_публикации'] - self.found_df['дата находки']
        ).dt.days

        # Очистка возраста
        self.lost_df['возраст_число'] = self.lost_df['возраст'].apply(self.clean_age)
        self.found_df['возраст_число'] = self.found_df['возраст'].apply(self.clean_age)

        # Тип местности
        self.lost_df['тип_местности'] = self.lost_df['регион'].astype(str).str.lower().apply(
            lambda x: 'город' if any(city in x for city in URBAN_KEYWORDS) else 'область/село'
        )
        self.found_df['тип_местности'] = self.found_df['регион'].astype(str).str.lower().apply(
            lambda x: 'город' if any(city in x for city in URBAN_KEYWORDS) else 'область/село'
        )

        # Породистость
        self.lost_df['породистое'] = self.lost_df['порода'].apply(self.is_pedigree)
        self.found_df['породистое'] = self.found_df['порода'].apply(self.is_pedigree)

    # ----------------------------- Генерация графиков -----------------------------
    def generate_plots(self):
        """
        Генерирует и сохраняет все графики в директорию output_dir,
        с теми же именами файлов и логикой, что и в оригинале.
        """
        print("\n📌 Генерация графиков по пропаже...")

        success_mask_lost = self.lost_df['статус'] == 'питомец найден'

        # 1. Время до публикации (lost)
        valid_data = self.lost_df[['статус', 'время_до_публикации']].dropna()
        if len(valid_data) > 0 and valid_data['статус'].nunique() > 1:
            plt.figure(figsize=(10, 6))
            sns.boxplot(data=valid_data, x='статус', y='время_до_публикации')
            plt.title("Влияние скорости публикации на успех (При пропаже)")
            plt.ylabel("Время до публикации, дни")
            plt.xlabel("Статус объявления")
            plt.tight_layout()
            plt.savefig(os.path.join(self.output_dir, '5.1. Влияние скорости публикации на успех (При пропаже).png'), dpi=150)
            plt.close()

        # 2. Возраст (lost)
        age_data = self.lost_df[self.lost_df['возраст_число'].notna()]
        if len(age_data) > 0:
            plt.figure(figsize=(10, 6))
            sns.boxplot(data=age_data, x='статус', y='возраст_число')
            plt.title("Возраст (При пропаже)")
            plt.ylabel("Возраст, лет")
            plt.xlabel("Статус")
            plt.tight_layout()
            plt.savefig(os.path.join(self.output_dir, '5.2. Возраст (При пропаже).png'), dpi=150)
            plt.close()

        # 3. Местность (lost)
        plt.figure(figsize=(8, 6))
        terrain_success = self.lost_df.groupby('тип_местности')['статус'].apply(lambda x: (x == 'питомец найден').mean())
        terrain_success.plot(kind='bar')
        plt.title("Успешность по типу местности (При пропаже)")
        plt.ylabel("Доля найденных")
        plt.xlabel("Тип местности")
        plt.xticks(rotation=0)
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, '5.3. Успешность по типу местности (При пропаже).png'), dpi=150)
        plt.close()

        # 4. Породистость (lost)
        plt.figure(figsize=(8, 6))
        breed_success = self.lost_df.groupby('породистое')['статус'].apply(lambda x: (x == 'питомец найден').mean())
        breed_success.plot(kind='bar')
        plt.title("Влияние породистости на успех (При пропаже)")
        plt.ylabel("Доля найденных")
        plt.xlabel("Породистое животное")
        plt.xticks(rotation=0)
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, '5.4. Влияние породистости на успех (При пропаже).png'), dpi=150)
        plt.close()

        # ------------------ По находке ------------------
        print("\n📌 Генерация графиков по находке...")

        # return_mask для вывода
        # в оригинале использовалось: return_mask = found_df['статус'] == 'хозяин найден'
        return_mask = self.found_df['статус'] == 'хозяин найден'

        # 1. Время до публикации (found)
        valid_data = self.found_df[['статус', 'время_до_публикации']].dropna()
        if len(valid_data) > 0 and valid_data['статус'].nunique() > 1:
            plt.figure(figsize=(10, 6))
            sns.boxplot(data=valid_data, x='статус', y='время_до_публикации')
            plt.title("Влияние скорости публикации на успех (При находке)")
            plt.ylabel("Время до публикации, дни")
            plt.xlabel("Статус")
            plt.tight_layout()
            plt.savefig(os.path.join(self.output_dir, '5.5. Влияние скорости публикации на успех (При находке).png'), dpi=150)
            plt.close()

        # 2. Местность (found)
        plt.figure(figsize=(8, 6))
        place_success = self.found_df.groupby('тип_местности')['статус'].apply(lambda x: (x == 'хозяин найден').mean())
        place_success.plot(kind='bar')
        plt.title("Успешность по типу местности (При находке)")
        plt.ylabel("Доля возвратов")
        plt.xlabel("Тип местности")
        plt.xticks(rotation=0)
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, '5.6. Успешность по типу местности (При находке).png'), dpi=150)
        plt.close()

        # 3. Породистость (found)
        plt.figure(figsize=(8, 6))
        breed_return = self.found_df.groupby('породистое')['статус'].apply(lambda x: (x == 'хозяин найден').mean())
        breed_return.plot(kind='bar')
        plt.title("Влияние породистости на успех (При находке)")
        plt.ylabel("Доля возвратов")
        plt.xlabel("Породистое животное")
        plt.xticks(rotation=0)
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, '5.7. Влияние породистости на успех (При находке).png'), dpi=150)
        plt.close()

    # ----------------------------- Сводный вывод (текст) -----------------------------
    def generate_summary(self) -> list:
        """
        Генерирует список строк с итоговым выводом (output_lines) — логика как в оригинале.
        """
        print("\n📌 Сравнительный анализ...")

        success_mask_lost = self.lost_df['статус'] == 'питомец найден'
        return_mask = self.found_df['статус'] == 'хозяин найден'

        mean_delay_lost = self.lost_df['время_до_публикации'].mean()
        mean_delay_found = self.found_df['время_до_публикации'].mean()

        breed_eff_lost = self.lost_df.groupby('породистое')['статус'].apply(lambda x: (x == 'питомец найден').mean())
        breed_eff_found = self.found_df.groupby('породистое')['статус'].apply(lambda x: (x == 'хозяин найден').mean())

        output_lines = []
        output_lines.append("📌 5.1. АНАЛИЗ ОБЪЯВЛЕНИЙ О ПРОПАЖЕ ЖИВОТНОГО")
        output_lines.append(f" • Всего объявлений: {len(self.lost_df)}")
        output_lines.append(f" • Найдено: {success_mask_lost.sum()}")
        output_lines.append(f" • В поиске: {len(self.lost_df) - success_mask_lost.sum()}")
        output_lines.append(f" • Среднее время до публикации: {mean_delay_lost:.1f} дней")

        output_lines.append("\n📌 5.2. АНАЛИЗ ОБЪЯВЛЕНИЙ О НАХОДКЕ ЖИВОТНОГО")
        output_lines.append(f" • Всего объявлений: {len(self.found_df)}")
        output_lines.append(f" • Хозяин найден: {return_mask.sum()}")
        output_lines.append(f" • Ищут хозяина: {len(self.found_df) - return_mask.sum()}")
        output_lines.append(f" • Среднее время до публикации: {mean_delay_found:.1f} дней")

        output_lines.append("\n📌 5.3. СРАВНЕНИЕ: ПРОПАЖА vs НАХОДКА")
        output_lines.append(f" • Пропажа: {mean_delay_lost:.1f} дней, Находка: {mean_delay_found:.1f} дней")

        # Защита на случай отсутствия ключей 'Да'/'Нет' в результатах группировки
        lost_da = breed_eff_lost.get('Да', 0) if isinstance(breed_eff_lost, pd.Series) else 0
        lost_net = breed_eff_lost.get('Нет', 0) if isinstance(breed_eff_lost, pd.Series) else 0
        found_da = breed_eff_found.get('Да', 0) if isinstance(breed_eff_found, pd.Series) else 0
        found_net = breed_eff_found.get('Нет', 0) if isinstance(breed_eff_found, pd.Series) else 0

        output_lines.append(f" • Эффект породистости (пропажа): +{(lost_da - lost_net):.1%}")
        output_lines.append(f" • Эффект породистости (находка): +{(found_da - found_net):.1%}")

        if mean_delay_found < mean_delay_lost:
            output_lines.append("✅ Публикация о находке происходит быстрее.")
        else:
            output_lines.append("⚠️ Люди медленнее публикуют находки.")

        if found_da > lost_da:
            output_lines.append("✅ Породистые животные чаще узнаются при находке.")
        else:
            output_lines.append("💡 Порода важна, но не решающе.")

        return output_lines

    def save_summary(self, output_lines: list):
        """
        Сохраняет output_lines в файл 'Вывод 5 главы.txt' в output_dir и печатает строки — поведение как в оригинале.
        """
        out_path = os.path.join(self.output_dir, 'Вывод 5 главы.txt')
        with open(out_path, 'w', encoding='utf-8') as f:
            for line in output_lines:
                print(line)
                f.write(line + '\n')
        print(f"✅ Все результаты сохранены в папке '{self.output_dir}'")
        print(f"\n✅ Вывод сохранён в файле 'Вывод 5 главы.txt'")

    # ----------------------------- Основной запуск -----------------------------
    def run(self):
        """
        Основной метод для последовательного выполнения всех шагов:
        prepare_data -> generate_plots -> generate_summary -> save_summary
        """
        self.prepare_data()
        self.generate_plots()
        summary = self.generate_summary()
        self.save_summary(summary)


# ----------------------------------------------------------------------------------------------------------------------
# Скрипт-обёртка для запуска файла напрямую
# ----------------------------------------------------------------------------------------------------------------------
def step_5_proxy(lost_file: str = DEFAULT_LOST_FILE, found_file: str = DEFAULT_FOUND_FILE, output_dir: str = DEFAULT_OUTPUT_DIR):
    analyzer = Pet911Analyzer(lost_file=lost_file, found_file=found_file, output_dir=output_dir)
    analyzer.run()

def step_5():

    warnings.filterwarnings("ignore")

    lf = DEFAULT_LOST_FILE
    ff = DEFAULT_FOUND_FILE
    od = DEFAULT_OUTPUT_DIR

    step_5_proxy(lost_file=lf, found_file=ff, output_dir=od)
  