#!/usr/bin/env python3
"""
Analyze remaining tokens from 1M payments to find missing stopwords
"""

import csv
import sys
sys.path.append('/Users/dariapavlova/Desktop/ai-service/src')

from ai_service.data.dicts.stopwords import STOP_ALL

def analyze_missing_stopwords(filename, top_n=2000):
    """Find tokens that should be stopwords but aren't yet"""

    print(f"🔍 Analyzing top {top_n} tokens to find missing stopwords...")
    print(f"📚 Current stopwords count: {len(STOP_ALL)}")

    # Categories for new potential stopwords
    candidates = {
        'technical_terms': [],      # Technical/system terms
        'business_services': [],    # Business/service related
        'government_official': [],  # Government/official terms
        'measurement_units': [],    # Units, measurements
        'common_words': [],        # Common words that aren't names
        'unclear_abbreviations': [], # Abbreviations/codes
        'potential_garbage': []     # High frequency garbage
    }

    # Known name patterns to avoid (we don't want to remove actual names)
    name_indicators = [
        # Patronymic endings
        'ович', 'евич', 'івич', 'овна', 'евна', 'івна', 'йович', 'йівна',
        # Surname endings
        'енко', 'ук', 'юк', 'чук', 'ський', 'ська', 'цький', 'цька', 'ич',
        # Common name roots
        'олександр', 'володимир', 'сергій', 'андрій', 'дмитро', 'микола', 'олексій',
        'анна', 'марія', 'олена', 'ольга', 'тетяна', 'наталія', 'ірина', 'юлія'
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

            # Skip very short tokens or numbers
            if len(token) < 3 or token.isdigit():
                continue

            # Skip if it looks like a name
            is_likely_name = False
            for indicator in name_indicators:
                if (token.endswith(indicator) or indicator in token or
                    token.startswith(indicator)):
                    is_likely_name = True
                    break

            if is_likely_name:
                continue

            # Categorize remaining tokens
            categorized = False

            # Technical/system terms
            technical_keywords = [
                'система', 'сервіс', 'портал', 'платформа', 'додаток', 'програма',
                'мобільний', 'онлайн', 'цифров', 'електрон', 'автомат', 'термінал',
                'інтерфейс', 'модуль', 'версія', 'оновлення', 'налаштування', 'конфігур'
            ]

            if any(keyword in token for keyword in technical_keywords):
                candidates['technical_terms'].append((token, frequency, percent))
                categorized = True

            # Business/service terms
            if not categorized:
                business_keywords = [
                    'бізнес', 'офіс', 'центр', 'департамент', 'відділ', 'служба',
                    'управління', 'адміністрація', 'інспекція', 'комісія', 'комітет',
                    'ради', 'збори', 'засідання', 'нарада', 'конференція', 'семінар'
                ]

                if any(keyword in token for keyword in business_keywords):
                    candidates['business_services'].append((token, frequency, percent))
                    categorized = True

            # Government/official terms
            if not categorized:
                gov_keywords = [
                    'держав', 'муніципал', 'комунал', 'бюджет', 'казна', 'фінанс',
                    'податк', 'мито', 'збір', 'внесок', 'відрахування', 'нарахування',
                    'реєстр', 'ліценз', 'дозвіл', 'сертифікат', 'довідк', 'довіреність'
                ]

                if any(keyword in token for keyword in gov_keywords):
                    candidates['government_official'].append((token, frequency, percent))
                    categorized = True

            # Measurement units and quantities
            if not categorized:
                measurement_keywords = [
                    'метр', 'кілометр', 'сантиметр', 'літр', 'кілограм', 'грам', 'тонн',
                    'штук', 'одиниц', 'екземпляр', 'комплект', 'набір', 'пакет', 'упаков',
                    'кубічн', 'квадратн', 'погонн', 'лінійн', 'площ', 'об', 'ємн'
                ]

                if any(keyword in token for keyword in measurement_keywords):
                    candidates['measurement_units'].append((token, frequency, percent))
                    categorized = True

            # Common non-name words
            if not categorized:
                common_patterns = [
                    # High frequency (>0.1%) non-names
                    (frequency > 7000, 'potential_garbage'),
                    # Medium frequency (0.05-0.1%) descriptive words
                    (3500 <= frequency <= 7000 and len(token) >= 4, 'common_words'),
                    # Unknown abbreviations
                    (len(token) <= 5 and token.isupper(), 'unclear_abbreviations')
                ]

                for condition, category in common_patterns:
                    if condition:
                        candidates[category].append((token, frequency, percent))
                        categorized = True
                        break

            # If still not categorized but high frequency, might be garbage
            if not categorized and frequency > 1000:
                candidates['potential_garbage'].append((token, frequency, percent))

    return candidates

def print_analysis_results(candidates):
    """Print detailed analysis of potential stopwords"""

    print(f"\n" + "="*80)
    print(f"📊 MISSING STOPWORDS ANALYSIS")
    print(f"="*80)

    total_candidates = sum(len(tokens) for tokens in candidates.values())
    print(f"\n🎯 SUMMARY: Found {total_candidates} potential new stopwords")

    for category, tokens in candidates.items():
        if not tokens:
            continue

        print(f"\n📂 {category.upper().replace('_', ' ')} ({len(tokens)} candidates):")

        # Sort by frequency (highest first)
        sorted_tokens = sorted(tokens, key=lambda x: x[1], reverse=True)

        # Show top 15 in each category
        for i, (token, freq, percent) in enumerate(sorted_tokens[:15], 1):
            print(f"   {i:2}. {token:<20} (freq: {freq:>6}, {percent:>6.3f}%)")

        if len(sorted_tokens) > 15:
            print(f"       ... and {len(sorted_tokens) - 15} more")

    # Generate recommendations
    print(f"\n💡 RECOMMENDATIONS:")

    high_priority = []
    for category in ['potential_garbage', 'government_official', 'business_services']:
        if category in candidates and candidates[category]:
            high_priority.extend([token for token, _, _ in candidates[category][:10]])

    if high_priority:
        print(f"\n🔥 HIGH PRIORITY (add immediately):")
        print(f"   {', '.join(high_priority[:20])}")
        if len(high_priority) > 20:
            print(f"   ... and {len(high_priority) - 20} more")

    print(f"\n⚠️  REVIEW NEEDED:")
    print(f"   • technical_terms - might contain company names")
    print(f"   • unclear_abbreviations - could be person initials")
    print(f"   • common_words - verify they're not regional name variants")

def main():
    """Main analysis function"""

    candidates = analyze_missing_stopwords("all_tokens_by_frequency.csv", top_n=3000)
    print_analysis_results(candidates)

    # Generate code for easy addition
    print(f"\n" + "="*80)
    print("📝 CODE TO ADD TO STOPWORDS.PY:")
    print("="*80)

    all_recommendations = []
    for category, tokens in candidates.items():
        if category in ['potential_garbage', 'government_official', 'business_services', 'measurement_units']:
            all_recommendations.extend([token for token, _, _ in tokens[:5]])  # Top 5 from each category

    # Format for easy copy-paste
    print("\n# Additional stopwords from 1M payment analysis:")
    for i in range(0, len(all_recommendations), 8):
        batch = all_recommendations[i:i+8]
        formatted = [f'"{term}"' for term in batch]
        print("    " + ", ".join(formatted) + ",")

if __name__ == "__main__":
    main()