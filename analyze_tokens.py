#!/usr/bin/env python3
"""
Analyze payment tokens and categorize for stopwords and diminutives
"""

import csv
import re
from collections import defaultdict

def analyze_tokens(filename, top_n=1000):
    """Analyze top N tokens from payment descriptions"""

    # Categories for classification
    categories = {
        'payment_words': set(),        # Payment/service related
        'numbers_dates': set(),        # Numbers, dates, codes
        'service_names': set(),        # Company/service names
        'locations': set(),           # Cities, addresses
        'technical_terms': set(),     # Technical/system terms
        'potential_names': set(),     # Potential first names
        'potential_patronymics': set(), # Potential patronymics
        'potential_surnames': set(),  # Potential surnames
        'garbage_tokens': set(),      # Short/meaningless tokens
        'already_in_stopwords': set() # Already covered
    }

    # Existing stopwords for comparison
    existing_stopwords = {
        'оплата', 'за', 'послуг', 'на', 'поповнення', 'послуги', 'балансу', 'сплата', 'плата',
        'договору', 'договор', 'рахунок', 'рахунку', 'платіж', 'платеж', 'доступ', 'клієнта',
        'тов', 'заборгованість', 'сума', 'суми', 'сумма', 'через', 'компанії', 'доставку',
        'платник', 'комісії', 'номер', 'карту', 'для', 'по', 'від', 'та', 'і', 'і', 'у', 'в', 'з'
    }

    # Name patterns
    name_endings_m = ['ович', 'евич', 'івич', 'йович', 'льович', 'рович', 'сович', 'тович']
    name_endings_f = ['івна', 'овна', 'евна', 'йівна', 'льівна', 'рівна', 'сівна', 'тівна']
    surname_endings = ['енко', 'ук', 'юк', 'чук', 'ський', 'ська', 'цький', 'цька', 'ич', 'ович', 'ко', 'енко']

    # Service/company indicators
    service_indicators = ['газ', 'електр', 'вод', 'тепло', 'інтернет', 'телеком', 'транспорт', 'банк']

    print(f"🔍 Analyzing top {top_n} payment tokens...")

    with open(filename, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)

        for i, row in enumerate(reader):
            if i >= top_n:
                break

            token = row['Токен'].lower().strip()
            frequency = int(row['Частота'])
            percent = float(row['Процент'].replace('%', ''))

            # Skip very short tokens (likely fragments)
            if len(token) <= 2 and not token.isdigit():
                categories['garbage_tokens'].add(token)
                continue

            # Already in stopwords
            if token in existing_stopwords:
                categories['already_in_stopwords'].add(token)
                continue

            # Numbers and dates
            if token.isdigit() or re.match(r'\d+', token):
                categories['numbers_dates'].add(token)
                continue

            # Payment/service words (high frequency business terms)
            if any(indicator in token for indicator in ['оплат', 'плат', 'послуг', 'сервіс', 'баланс', 'рахунок', 'договір', 'договор', 'абонент', 'тариф', 'комісі', 'заборг']):
                categories['payment_words'].add(token)
                continue

            # Technical/service names
            if any(indicator in token for indicator in service_indicators):
                categories['service_names'].add(token)
                continue

            # Location indicators (cities, regions)
            if any(indicator in token for indicator in ['київ', 'одес', 'харків', 'львів', 'дніпр', 'запоріж', 'кремен', 'луцьк', 'ужгород', 'чернігів', 'мукачів']):
                categories['locations'].add(token)
                continue

            # Potential patronymics
            if any(token.endswith(ending) for ending in name_endings_m + name_endings_f):
                if len(token) > 6:  # Reasonable length for patronymic
                    categories['potential_patronymics'].add(token)
                continue

            # Potential surnames
            if any(token.endswith(ending) for ending in surname_endings):
                if len(token) > 4:  # Reasonable length for surname
                    categories['potential_surnames'].add(token)
                continue

            # Potential first names (common Ukrainian/Russian names in top frequency)
            common_names = ['олександр', 'володимир', 'сергій', 'андрій', 'олег', 'дмитро', 'яна', 'ольга', 'анна', 'марія']
            if token in common_names or (len(token) >= 4 and token.endswith(('а', 'я', 'й', 'р', 'н'))):
                # Only if it's reasonably frequent (appears in payment descriptions)
                if frequency > 1000:
                    categories['potential_names'].add(token)
                continue

            # Everything else - potential garbage/stopwords
            # High frequency (>0.01%) non-name tokens are likely stopwords
            if percent > 0.01:
                categories['garbage_tokens'].add(token)

    return categories

def print_analysis(categories):
    """Print categorized analysis"""

    print("\n" + "="*80)
    print("📊 TOKEN ANALYSIS RESULTS")
    print("="*80)

    for category, tokens in categories.items():
        if tokens:
            print(f"\n🔖 {category.upper().replace('_', ' ')} ({len(tokens)} tokens):")
            sorted_tokens = sorted(list(tokens))

            # Print in columns for readability
            for i in range(0, len(sorted_tokens), 10):
                batch = sorted_tokens[i:i+10]
                print("   " + ", ".join(batch))

    print("\n" + "="*80)

def generate_stopwords_additions(categories):
    """Generate additions for stopwords list"""

    print("\n🎯 RECOMMENDED ADDITIONS TO STOPWORDS:")
    print("="*60)

    stopword_candidates = set()
    stopword_candidates.update(categories['payment_words'])
    stopword_candidates.update(categories['garbage_tokens'])

    # Filter out names and keep only business terms
    business_terms = set()
    for token in stopword_candidates:
        # Skip if looks like name
        if token in categories['potential_names'] or token in categories['potential_patronymics'] or token in categories['potential_surnames']:
            continue
        # Keep if business/payment related
        if len(token) >= 3:  # Reasonable length
            business_terms.add(token)

    print("\n📝 Add these to STOP_ALL in stopwords.py:")
    sorted_terms = sorted(list(business_terms))
    for i in range(0, len(sorted_terms), 8):
        batch = sorted_terms[i:i+8]
        formatted = [f'"{term}"' for term in batch]
        print("    " + ", ".join(formatted) + ",")

if __name__ == "__main__":
    categories = analyze_tokens("all_tokens_by_frequency.csv", top_n=500)
    print_analysis(categories)
    generate_stopwords_additions(categories)