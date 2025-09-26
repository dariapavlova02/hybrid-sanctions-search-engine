#!/usr/bin/env python3
"""
Ультра-глубокий анализ оставшихся токенов для максимального извлечения стоп-слов
Цель: выжать из 1М токенов все возможные мусорные токены
"""

import csv
import sys
import re
sys.path.append('/Users/dariapavlova/Desktop/ai-service/src')

from ai_service.data.dicts.stopwords import STOP_ALL

def ultra_deep_mining(filename, top_n=10000):
    """Ультра-агрессивный поиск стоп-слов в топ-10К токенов"""

    print(f"🔥 УЛЬТРА-ГЛУБОКИЙ АНАЛИЗ топ-{top_n} токенов")
    print(f"📚 Текущие стоп-слова: {len(STOP_ALL)}")
    print("🎯 ЦЕЛЬ: Найти все возможные мусорные токены для максимального фильтрования")
    print("=" * 80)

    # Более детальные категории для ультра-анализа
    mining_categories = {
        'numbers_and_codes': [],        # Любые числа, коды, идентификаторы
        'tech_fragments': [],           # Технические обрывки, аббревиатуры
        'business_noise': [],           # Любые бизнес-термины
        'descriptive_words': [],        # Описательные слова, прилагательные
        'conjunctions_particles': [],   # Союзы, частицы, предлоги
        'verb_forms': [],              # Глаголы в любой форме
        'administrative': [],          # Административные, юридические термины
        'service_operations': [],      # Операционные термины услуг
        'measurement_quantities': [],   # Измерения, количества, единицы
        'temporal_references': [],     # Любые временные ссылки
        'geographical_misc': [],       # Дополнительные географические термины
        'financial_terms': [],         # Финансовые термины
        'high_freq_garbage': [],       # Высокочастотный мусор
        'short_noise': [],             # Короткие шумовые токены
        'suspicious_patterns': []      # Подозрительные паттерны
    }

    # Расширенные паттерны для ультра-поиска
    patterns = {
        'numbers_codes': [
            r'^\d+$',                    # Чистые числа
            r'^[0-9a-f]{6,}$',          # Хекс-коды
            r'^[a-z]{1,3}\d+$',         # Буквы + числа (код1, abc123)
            r'^\d+[a-z]{1,3}$',         # Числа + буквы (123abc)
            r'^[0-9-]{6,}$',            # Числа с дефисами
            r'^[0-9\.]{6,}$',           # Числа с точками
        ],

        'fragments': [
            r'^.{1,3}$',                # Очень короткие (1-3 символа)
            r'^[а-я]{1,4}[0-9]',        # Короткие + цифра
            r'^[a-z]{1,4}[0-9]',        # Латиница + цифра
            r'[0-9]$',                  # Заканчивается цифрой
        ],

        'business_patterns': [
            'компан', 'фирм', 'предприят', 'организац', 'учрежден',
            'общест', 'товарищ', 'объедин', 'союз', 'ассоциац',
            'корпорац', 'холдинг', 'концерн', 'группа', 'груп'
        ],

        'service_patterns': [
            'услуг', 'сервис', 'обслуж', 'операц', 'процедур', 'работ',
            'деятельн', 'функц', 'процесс', 'систем', 'механизм',
            'порядок', 'правил', 'норм', 'стандарт', 'требован'
        ],

        'admin_patterns': [
            'управлен', 'администр', 'контрол', 'надзор', 'инспекц',
            'департамент', 'министерств', 'комитет', 'комисс', 'совет',
            'орган', 'власт', 'государств', 'муниципал', 'местн'
        ],

        'descriptive_patterns': [
            'больш', 'мал', 'средн', 'общ', 'специальн', 'основн',
            'дополнительн', 'новый', 'стар', 'молод', 'хорош', 'плох',
            'высок', 'низк', 'широк', 'узк', 'длинн', 'коротк'
        ]
    }

    # Определенно НЕ имена - паттерны для исключения
    definitely_not_names = [
        # Очевидные имена - НЕ трогаем
        'александр', 'владимир', 'сергей', 'андрей', 'дмитрий', 'николай', 'алексей',
        'виктор', 'петр', 'иван', 'юрий', 'михаил', 'евгений', 'василий', 'анатолий',
        'анна', 'мария', 'елена', 'ольга', 'татьяна', 'наталья', 'ирина', 'юлия',
        'екатерина', 'людмила', 'светлана', 'галина', 'валентина', 'надежда',

        # Украинские имена - НЕ трогаем
        'олександр', 'володимир', 'сергій', 'андрій', 'дмитро', 'микола', 'олексій',
        'віктор', 'петро', 'іван', 'юрій', 'михайло', 'євген', 'василь', 'анатолій',
        'олена', 'тетяна', 'наталія', 'ірина', 'юлія', 'катерина', 'людмила', 'світлана',

        # Фамильные паттерны - НЕ трогаем
        'енко', 'ич', 'ович', 'евич', 'івич', 'овна', 'евна', 'івна',
        'ський', 'ська', 'цький', 'цька', 'ук', 'юк', 'чук'
    ]

    with open(filename, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)

        for i, row in enumerate(reader):
            if i >= top_n:
                break

            token = row['Токен'].lower().strip()
            frequency = int(row['Частота'])
            percent = float(row['Процент'].replace('%', ''))

            # Пропускаем уже существующие стоп-слова
            if token in STOP_ALL:
                continue

            # Пропускаем очевидные имена
            is_likely_name = False
            for name_part in definitely_not_names:
                if name_part in token or token.endswith(('енко', 'ович', 'евич', 'івич', 'овна', 'евна', 'івна', 'ський', 'ська')):
                    is_likely_name = True
                    break

            if is_likely_name:
                continue

            # Категоризация токенов
            categorized = False

            # 1. Числа и коды
            for pattern in patterns['numbers_codes']:
                if re.match(pattern, token):
                    mining_categories['numbers_and_codes'].append((token, frequency, percent))
                    categorized = True
                    break

            if not categorized:
                # 2. Технические фрагменты
                if (len(token) <= 4 and any(char.isdigit() for char in token)) or \
                   any(re.match(pattern, token) for pattern in patterns['fragments']):
                    mining_categories['tech_fragments'].append((token, frequency, percent))
                    categorized = True

                # 3. Бизнес термины
                elif any(pattern in token for pattern in patterns['business_patterns']):
                    mining_categories['business_noise'].append((token, frequency, percent))
                    categorized = True

                # 4. Административные термины
                elif any(pattern in token for pattern in patterns['admin_patterns']):
                    mining_categories['administrative'].append((token, frequency, percent))
                    categorized = True

                # 5. Сервисные термины
                elif any(pattern in token for pattern in patterns['service_patterns']):
                    mining_categories['service_operations'].append((token, frequency, percent))
                    categorized = True

                # 6. Описательные слова
                elif any(pattern in token for pattern in patterns['descriptive_patterns']) or \
                     token.endswith(('ный', 'ная', 'ное', 'ный', 'ська', 'ській', 'льный', 'льная')):
                    mining_categories['descriptive_words'].append((token, frequency, percent))
                    categorized = True

                # 7. Глагольные формы
                elif token.endswith(('ать', 'ить', 'еть', 'уть', 'ти', 'тся', 'ться', 'ет', 'ит', 'ут', 'ют')):
                    mining_categories['verb_forms'].append((token, frequency, percent))
                    categorized = True

                # 8. Союзы, предлоги, частицы
                elif len(token) <= 5 and token in ['для', 'при', 'про', 'під', 'над', 'між', 'через', 'після', 'перед', 'біля', 'коло', 'або', 'чи', 'та', 'і', 'й', 'а', 'але', 'однак', 'проте', 'тому', 'оскільки', 'якщо', 'коли', 'де', 'що', 'який', 'яка', 'яке']:
                    mining_categories['conjunctions_particles'].append((token, frequency, percent))
                    categorized = True

                # 9. Финансовые термины
                elif any(fin_term in token for fin_term in ['гривн', 'рубл', 'доллар', 'евро', 'копе', 'цент', 'валют', 'курс', 'обмен', 'размен']):
                    mining_categories['financial_terms'].append((token, frequency, percent))
                    categorized = True

                # 10. Временные ссылки
                elif any(time_ref in token for time_ref in ['час', 'врем', 'период', 'срок', 'дата', 'числ', 'день', 'неделя', 'месяц', 'год', 'век']):
                    mining_categories['temporal_references'].append((token, frequency, percent))
                    categorized = True

                # 11. Измерения и количества
                elif any(measure in token for measure in ['метр', 'литр', 'килограм', 'тонн', 'штук', 'единиц', 'количеств', 'размер', 'объем', 'площад']):
                    mining_categories['measurement_quantities'].append((token, frequency, percent))
                    categorized = True

                # 12. Дополнительные географические
                elif any(geo in token for geo in ['район', 'округ', 'село', 'деревня', 'поселок', 'микрорайон', 'квартал', 'проспект', 'бульвар', 'переулок']):
                    mining_categories['geographical_misc'].append((token, frequency, percent))
                    categorized = True

                # 13. Высокочастотный подозрительный мусор
                elif frequency > 5000:  # Очень высокая частота = вероятно мусор
                    mining_categories['high_freq_garbage'].append((token, frequency, percent))
                    categorized = True

                # 14. Короткий шум (2-3 символа, высокая частота)
                elif len(token) <= 3 and frequency > 1000:
                    mining_categories['short_noise'].append((token, frequency, percent))
                    categorized = True

                # 15. Подозрительные паттерны
                elif frequency > 2000 and (token.count('о') > len(token)/2 or token.count('а') > len(token)/2):
                    mining_categories['suspicious_patterns'].append((token, frequency, percent))
                    categorized = True

    return mining_categories

def print_ultra_mining_results(mining_results):
    """Вывод результатов ультра-анализа"""

    print(f"\n🔥 РЕЗУЛЬТАТЫ УЛЬТРА-ГЛУБОКОГО АНАЛИЗА")
    print("=" * 80)

    total_found = sum(len(tokens) for tokens in mining_results.values())
    print(f"🎯 ВСЕГО НАЙДЕНО КАНДИДАТОВ: {total_found}")

    # Приоритетные категории для немедленного добавления
    priority_categories = [
        'high_freq_garbage', 'numbers_and_codes', 'short_noise',
        'tech_fragments', 'conjunctions_particles'
    ]

    priority_tokens = []

    for category, tokens in mining_results.items():
        if not tokens:
            continue

        print(f"\n📂 {category.upper().replace('_', ' ')} ({len(tokens)} кандидатов):")

        # Сортировка по частоте
        sorted_tokens = sorted(tokens, key=lambda x: x[1], reverse=True)

        # Показываем топ-20 для приоритетных категорий, топ-10 для остальных
        show_count = 20 if category in priority_categories else 10

        for i, (token, freq, percent) in enumerate(sorted_tokens[:show_count], 1):
            print(f"   {i:2}. {token:<15} (freq: {freq:>6}, {percent:>6.3f}%)")

            # Собираем приоритетные токены
            if category in priority_categories and freq > 500:  # Только высокочастотные
                priority_tokens.append(token)

        if len(sorted_tokens) > show_count:
            print(f"       ... и еще {len(sorted_tokens) - show_count}")

    return priority_tokens

def generate_ultra_additions(priority_tokens):
    """Генерация кода для добавления в стоп-слова"""

    print(f"\n" + "=" * 80)
    print("💥 КОД ДЛЯ УЛЬТРА-ДОПОЛНЕНИЯ СТОП-СЛОВ")
    print("=" * 80)

    print(f"\n# Ультра-глубокий анализ 1М токенов - финальная зачистка:")
    print(f"# Найдено {len(priority_tokens)} высокоприоритетных мусорных токенов")

    # Разбиваем на группы по 10 для читаемости
    for i in range(0, len(priority_tokens), 10):
        batch = priority_tokens[i:i+10]
        formatted = [f'"{token}"' for token in batch]
        print("    " + ", ".join(formatted) + ",")

    print(f"\n📊 СТАТИСТИКА УЛЬТРА-АНАЛИЗА:")
    print(f"   • Проанализировано: топ-10,000 токенов")
    print(f"   • Найдено кандидатов: {len(priority_tokens)}")
    print(f"   • Текущий размер: {len(STOP_ALL)} стоп-слов")
    print(f"   • После добавления: ~{len(STOP_ALL) + len(priority_tokens)} стоп-слов")
    print(f"   • Ожидаемое улучшение фильтрации: +2-5%")

def main():
    """Основная функция ультра-анализа"""

    mining_results = ultra_deep_mining("all_tokens_by_frequency.csv", top_n=10000)
    priority_tokens = print_ultra_mining_results(mining_results)

    if priority_tokens:
        generate_ultra_additions(priority_tokens[:50])  # Топ-50 для начала

    print(f"\n✅ Ультра-анализ завершен. Готово для максимального фильтрования!")

if __name__ == "__main__":
    main()