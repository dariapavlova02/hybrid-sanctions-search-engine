#!/usr/bin/env python3
"""
Aggressive stopwords analysis - extract more garbage terms from payment data
"""

import csv
import re
from collections import defaultdict

def aggressive_stopwords_analysis(filename, top_n=10000):
    """More aggressive analysis to find garbage terms that should be stopwords"""

    # Categories for more aggressive filtering
    definite_stopwords = set()
    potential_stopwords = set()
    business_terms = set()

    # Known name patterns to exclude (so we don't accidentally add names)
    name_patterns = {
        'patronymics': ['ович', 'евич', 'івич', 'овна', 'евна', 'івна'],
        'surnames': ['енко', 'ук', 'юк', 'чук', 'ський', 'ська', 'ич'],
        'common_names': {
            'олександр', 'володимир', 'сергій', 'андрій', 'дмитро', 'микола', 'олексій',
            'віктор', 'петро', 'іван', 'юрій', 'михайло', 'євген', 'василь', 'анатолій',
            'анна', 'марія', 'олена', 'ольга', 'тетяна', 'наталія', 'ірина', 'юлія',
            'катерина', 'людмила', 'світлана', 'галина', 'валентина'
        }
    }

    # Aggressive business/service term patterns
    business_keywords = [
        # Payment terms
        'оплат', 'плат', 'платеж', 'платіж', 'сплат', 'уплат',
        'послуг', 'сервіс', 'услуг', 'обслуг',
        'договор', 'договір', 'контракт', 'угод',
        'баланс', 'рахунок', 'счет', 'рахівн',
        'тариф', 'тарифн', 'ставк',
        'комісі', 'комиссі', 'збор',
        'заборг', 'борг', 'долг',

        # Services
        'абонент', 'клієнт', 'користув',
        'доступ', 'підключ', 'подключ',
        'надан', 'предоставл', 'наданн',
        'обладнан', 'оборудован', 'техніч',

        # Transport
        'транспорт', 'проїзд', 'проезд', 'поїзд', 'поезд',
        'квиток', 'билет', 'проїзн', 'проездн',
        'паркув', 'стоянк', 'гараж',
        'автобус', 'тролейбус', 'троллейбус', 'метро',

        # Utilities
        'електр', 'енерг', 'энерг', 'світл', 'освітл',
        'води', 'водн', 'водопост', 'водовід',
        'газу', 'газов', 'газифік',
        'тепло', 'опален', 'отоплен',

        # Documents/Cards
        'карт', 'картк', 'карточ',
        'документ', 'довід', 'справк',
        'паспорт', 'посвід',
        'номер', 'код', 'ідентифік',

        # Financial
        'банк', 'фінанс', 'кредит', 'позик',
        'страхов', 'страхув', 'поліс',
        'внеск', 'внесок', 'депозит',
        'процент', 'відсотк',

        # Legal/Official
        'держав', 'урядов', 'офіційн',
        'реєстр', 'регістр', 'облік',
        'дозвіл', 'ліценз', 'патент',
        'штраф', 'санкці', 'пеня'
    ]

    # Time/date terms
    time_terms = [
        'день', 'дня', 'днів', 'дней',
        'тиждень', 'тижн', 'недел',
        'місяць', 'месяц', 'міс',
        'рік', 'року', 'років', 'год', 'лет',
        'година', 'годин', 'час',
        'хвилин', 'минут',
        'січень', 'лютий', 'березень', 'квітень', 'травень', 'червень',
        'липень', 'серпень', 'вересень', 'жовтень', 'листопад', 'грудень',
        'январь', 'февраль', 'март', 'апрель', 'май', 'июнь',
        'июль', 'август', 'сентябрь', 'октябрь', 'ноябрь', 'декабрь'
    ]

    # Location terms (cities, regions, addresses)
    location_terms = [
        'київ', 'одеса', 'харків', 'дніпро', 'львів', 'запоріжжя',
        'кривий', 'миколаїв', 'маріуполь', 'луганськ', 'севастополь',
        'вінниця', 'чернігів', 'черкаси', 'житомир', 'суми', 'хмельниц',
        'чернівці', 'рівне', 'кременчуг', 'кропивниц', 'івано', 'тернопіль',
        'луцьк', 'ужгород', 'біла', 'мелітополь', 'керч', 'бердянськ',
        'нікополь', 'слов', 'краматорськ', 'конотоп', 'умань', 'бровари',
        'мукачево', 'коломия', 'євпаторія', 'ялта', 'алушта', 'феодосія',

        'область', 'обласн', 'район', 'районн', 'місто', 'город',
        'село', 'селищ', 'поселок', 'станція', 'вокзал',
        'вулиця', 'улица', 'проспект', 'бульвар', 'площа', 'площад',
        'провулок', 'переулок', 'набережна', 'набережная'
    ]

    print(f"🔍 Aggressive stopwords analysis of top {top_n} tokens...")

    with open(filename, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)

        for i, row in enumerate(reader):
            if i >= top_n:
                break

            token = row['Токен'].lower().strip()
            frequency = int(row['Частота'])
            percent = float(row['Процент'].replace('%', ''))

            # Skip very short tokens or numbers
            if len(token) < 3 or any(char.isdigit() for char in token):
                continue

            # Skip if it looks like a name
            is_likely_name = False

            # Check if it's a known name
            if token in name_patterns['common_names']:
                continue

            # Check patronymic patterns
            if any(token.endswith(pattern) for pattern in name_patterns['patronymics']):
                continue

            # Check surname patterns
            if any(token.endswith(pattern) for pattern in name_patterns['surnames']):
                continue

            # Check if it matches business patterns
            business_score = 0
            for keyword in business_keywords:
                if keyword in token:
                    business_score += 1
                    break

            # Check time terms
            time_score = 0
            for term in time_terms:
                if term in token or token in term:
                    time_score += 1
                    break

            # Check location terms
            location_score = 0
            for term in location_terms:
                if term in token or token in term:
                    location_score += 1
                    break

            # Decision logic
            total_score = business_score + time_score + location_score

            # High frequency terms are more likely to be garbage
            frequency_bonus = 0
            if frequency > 10000:  # >0.14%
                frequency_bonus = 2
            elif frequency > 5000:   # >0.07%
                frequency_bonus = 1

            final_score = total_score + frequency_bonus

            # Categorize
            if final_score >= 2:
                definite_stopwords.add(token)
                print(f"✅ DEFINITE: {token} (freq: {frequency}, {percent:.3f}%, score: {final_score})")
            elif final_score == 1 and frequency > 1000:
                potential_stopwords.add(token)
                print(f"❓ POTENTIAL: {token} (freq: {frequency}, {percent:.3f}%, score: {final_score})")

            # Additional check for very high frequency non-name terms
            if (frequency > 5000 and
                len(token) >= 4 and
                not any(token.endswith(pattern) for pattern in name_patterns['patronymics']) and
                not any(token.endswith(pattern) for pattern in name_patterns['surnames']) and
                token not in name_patterns['common_names']):

                # Check if it could be a business term by content
                if (any(substring in token for substring in ['оплат', 'послуг', 'договор', 'карт', 'банк', 'сервіс', 'тариф']) or
                    token in time_terms or
                    any(loc_term in token for loc_term in location_terms[:20])): # Top cities only

                    business_terms.add(token)
                    print(f"💼 BUSINESS: {token} (freq: {frequency}, {percent:.3f}%)")

    return definite_stopwords, potential_stopwords, business_terms

def generate_comprehensive_additions(definite_stopwords, potential_stopwords, business_terms):
    """Generate comprehensive stopwords additions"""

    print(f"\n" + "="*80)
    print(f"🎯 COMPREHENSIVE STOPWORDS ANALYSIS")
    print(f"="*80)

    print(f"\n📊 STATISTICS:")
    print(f"  • Definite stopwords: {len(definite_stopwords)}")
    print(f"  • Potential stopwords: {len(potential_stopwords)}")
    print(f"  • Business terms: {len(business_terms)}")
    print(f"  • TOTAL RECOMMENDED: {len(definite_stopwords) + len(potential_stopwords) + len(business_terms)}")

    all_recommendations = definite_stopwords.union(potential_stopwords).union(business_terms)

    print(f"\n🔧 RECOMMENDED ADDITIONS TO stopwords.py:")
    print(f"Add these {len(all_recommendations)} terms to STOP_ALL:")
    print()

    # Format for easy copy-paste
    sorted_terms = sorted(list(all_recommendations))
    for i in range(0, len(sorted_terms), 6):
        batch = sorted_terms[i:i+6]
        formatted = [f'"{term}"' for term in batch]
        print("    " + ", ".join(formatted) + ",")

    print(f"\n💡 IMPACT ANALYSIS:")
    print(f"  • This will filter out {len(all_recommendations)} high-frequency garbage terms")
    print(f"  • Should significantly improve name detection precision")
    print(f"  • Covers payment, service, location, and temporal terms")
    print(f"  • Preserves all identified person names")

if __name__ == "__main__":
    definite, potential, business = aggressive_stopwords_analysis("all_tokens_by_frequency.csv", top_n=5000)
    generate_comprehensive_additions(definite, potential, business)