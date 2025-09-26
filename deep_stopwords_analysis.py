#!/usr/bin/env python3
"""
Deep analysis of remaining tokens from 1M payments to find ALL possible stopwords
"""

import csv
import re
import sys
sys.path.append('/Users/dariapavlova/Desktop/ai-service/src')

from ai_service.data.dicts.stopwords import STOP_ALL

def deep_analyze_stopwords(filename, top_n=5000):
    """Comprehensive analysis of ALL remaining tokens"""

    print(f"🔍 DEEP ANALYSIS of top {top_n} tokens...")
    print(f"📚 Current stopwords: {len(STOP_ALL)}")

    categories = {
        'prepositions_conjunctions': [],  # Предлоги, союзы, частицы
        'verbs_adjectives': [],          # Глаголы, прилагательные
        'numbers_codes': [],             # Числа, коды, идентификаторы
        'fragments_suffixes': [],        # Фрагменты, суффиксы, обрывки
        'company_brands': [],            # Названия компаний, бренды
        'tech_abbreviations': [],        # Технические аббревиатуры
        'service_terms': [],             # Сервисные термины
        'suspicious_high_freq': [],      # Подозрительно частые токены
        'short_garbage': [],             # Короткий мусор
        'descriptive_terms': []          # Описательные термины
    }

    # Expanded patterns for better categorization
    preposition_patterns = [
        'для', 'від', 'при', 'про', 'під', 'над', 'між', 'через', 'після', 'перед',
        'біля', 'коло', 'навколо', 'всередині', 'зовні', 'поруч', 'далі', 'ближче'
    ]

    verb_patterns = [
        'є', 'має', 'буде', 'був', 'була', 'були', 'робить', 'робив', 'зробив',
        'каже', 'казав', 'сказав', 'йде', 'йшов', 'пішов', 'дає', 'давав', 'дав'
    ]

    adjective_patterns = [
        'новий', 'старий', 'великий', 'малий', 'хороший', 'поганий', 'швидкий',
        'повільний', 'високий', 'низький', 'довгий', 'короткий', 'широкий', 'вузький'
    ]

    # Known name patterns (to avoid removing real names)
    definite_name_patterns = [
        'олександр', 'володимир', 'сергій', 'андрій', 'дмитро', 'микола', 'олексій',
        'віктор', 'петро', 'іван', 'юрій', 'михайло', 'євген', 'василь', 'анатолій',
        'анна', 'марія', 'олена', 'ольга', 'тетяна', 'наталія', 'ірина', 'юлія',
        'катерина', 'людмила', 'світлана', 'галина', 'валентина'
    ]

    with open(filename, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)

        for i, row in enumerate(reader):
            if i >= top_n:
                break

            token = row['Токен'].lower().strip()
            frequency = int(row['Частота'])
            percent = float(row['Процент'].replace('%', ''))

            # Skip if already in stopwords
            if token in STOP_ALL:
                continue

            # Skip very short tokens (but collect them separately)
            if len(token) <= 2:
                if frequency > 1000:  # High frequency short tokens are likely garbage
                    categories['short_garbage'].append((token, frequency, percent))
                continue

            # Skip if it's a definite name
            if any(name_part in token for name_part in definite_name_patterns):
                continue

            # Skip patronymic/surname patterns
            if (token.endswith(('ович', 'евич', 'івич', 'овна', 'евна', 'івна')) or
                token.endswith(('енко', 'ук', 'юк', 'чук', 'ський', 'ська'))):
                continue

            # Categorize tokens
            categorized = False

            # 1. Prepositions and conjunctions
            if token in preposition_patterns or any(prep in token for prep in preposition_patterns[:5]):
                categories['prepositions_conjunctions'].append((token, frequency, percent))
                categorized = True

            # 2. Verbs and adjectives
            elif (token in verb_patterns or token in adjective_patterns or
                  token.endswith(('ить', 'ать', 'еть', 'ути', 'ий', 'ый', 'ой', 'ая', 'ее'))):
                categories['verbs_adjectives'].append((token, frequency, percent))
                categorized = True

            # 3. Numbers, codes, technical identifiers
            elif (re.match(r'^[0-9a-f]{6,}$', token) or  # Hex codes
                  re.match(r'^[a-z]{2,4}[0-9]+$', token) or  # Code patterns
                  token.count('0') > len(token)/3):  # Lots of zeros
                categories['numbers_codes'].append((token, frequency, percent))
                categorized = True

            # 4. Company names and brands
            elif (token.endswith(('лтд', 'инк', 'корп', 'груп')) or
                  token.startswith(('укр', 'кий', 'одес', 'харків', 'львів')) or
                  any(brand in token for brand in ['фейсбук', 'гугл', 'амазон', 'майкрософт'])):
                categories['company_brands'].append((token, frequency, percent))
                categorized = True

            # 5. Technical abbreviations (all caps, 3-6 letters)
            elif (token.isupper() and 3 <= len(token) <= 6 and
                  not any(char.isdigit() for char in token)):
                categories['tech_abbreviations'].append((token, frequency, percent))
                categorized = True

            # 6. Service terms
            elif any(service in token for service in [
                'сервіс', 'служб', 'відділ', 'департамент', 'управлінн', 'адміністрац',
                'центр', 'офіс', 'філі', 'відділенн', 'представництв'
            ]):
                categories['service_terms'].append((token, frequency, percent))
                categorized = True

            # 7. Fragments and suffixes (likely parts of compound words)
            elif (len(token) <= 5 and
                  (token.startswith(('не', 'пре', 'про', 'під', 'над', 'роз', 'без')) or
                   token.endswith(('ння', 'тся', 'ться', 'ість', 'ність', 'льн')))):
                categories['fragments_suffixes'].append((token, frequency, percent))
                categorized = True

            # 8. Descriptive terms (adjectives, adverbs, etc.)
            elif (token.endswith(('ний', 'ний', 'ська', 'цька', 'льн', 'ові', 'еві')) and
                  len(token) > 5):
                categories['descriptive_terms'].append((token, frequency, percent))
                categorized = True

            # 9. High frequency suspicious tokens
            elif frequency > 2000:  # Very high frequency, probably not a name
                categories['suspicious_high_freq'].append((token, frequency, percent))
                categorized = True

    return categories

def print_deep_analysis(categories):
    """Print comprehensive analysis results"""

    print(f"\n" + "="*80)
    print(f"🔬 COMPREHENSIVE STOPWORDS ANALYSIS")
    print(f"="*80)

    total_found = sum(len(tokens) for tokens in categories.values())
    print(f"\n🎯 TOTAL CANDIDATES: {total_found}")

    # Detailed breakdown by category
    for category, tokens in categories.items():
        if not tokens:
            continue

        print(f"\n📂 {category.upper().replace('_', ' ')} ({len(tokens)} candidates):")

        # Sort by frequency
        sorted_tokens = sorted(tokens, key=lambda x: x[1], reverse=True)

        # Show top 20 for high-impact categories
        show_count = 20 if category in ['suspicious_high_freq', 'fragments_suffixes', 'short_garbage'] else 10

        for i, (token, freq, percent) in enumerate(sorted_tokens[:show_count], 1):
            print(f"   {i:2}. {token:<15} (freq: {freq:>6}, {percent:>6.3f}%)")

        if len(sorted_tokens) > show_count:
            print(f"       ... and {len(sorted_tokens) - show_count} more")

    # Generate priority recommendations
    print(f"\n🚀 PRIORITY RECOMMENDATIONS:")

    # High impact categories
    high_impact = []
    for category in ['suspicious_high_freq', 'prepositions_conjunctions', 'short_garbage']:
        if category in categories:
            high_impact.extend([token for token, freq, _ in categories[category] if freq > 1000])

    if high_impact:
        print(f"\n🔥 IMMEDIATE ACTION (high frequency garbage):")
        for i in range(0, min(30, len(high_impact)), 10):
            batch = high_impact[i:i+10]
            print(f"   {', '.join(batch)}")

    # Medium impact categories
    medium_impact = []
    for category in ['fragments_suffixes', 'verbs_adjectives', 'descriptive_terms']:
        if category in categories:
            medium_impact.extend([token for token, freq, _ in categories[category][:5] if freq > 500])

    if medium_impact:
        print(f"\n⚠️  REVIEW AND ADD (medium frequency):")
        for i in range(0, min(20, len(medium_impact)), 10):
            batch = medium_impact[i:i+10]
            print(f"   {', '.join(batch)}")

    return high_impact + medium_impact

def generate_stopwords_code(recommendations):
    """Generate code for adding to stopwords.py"""

    print(f"\n" + "="*80)
    print(f"📝 CODE FOR STOPWORDS.PY:")
    print(f"="*80)

    print(f"\n# Final cleanup - high-frequency non-name tokens from deep analysis:")

    # Split into logical groups for better organization
    for i in range(0, len(recommendations), 8):
        batch = recommendations[i:i+8]
        formatted = [f'"{term}"' for term in batch]
        print("    " + ", ".join(formatted) + ",")

def main():
    """Run deep stopwords analysis"""

    categories = deep_analyze_stopwords("all_tokens_by_frequency.csv", top_n=5000)
    recommendations = print_deep_analysis(categories)

    if recommendations:
        generate_stopwords_code(recommendations[:40])  # Top 40 recommendations

    print(f"\n✅ Analysis complete. Found {len(recommendations)} high-priority additions.")

if __name__ == "__main__":
    main()