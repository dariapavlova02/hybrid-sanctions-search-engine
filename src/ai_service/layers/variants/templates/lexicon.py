"""
Unified lexicon source for Aho-Corasick pattern matching and role tagging.
Single source of truth for stopwords, legal forms, and contextual triggers.
"""

# Russian stopwords - core conjunctions, prepositions, service words
STOPWORDS_RU = {
    # Basic conjunctions and prepositions
    'и', 'в', 'с', 'на', 'по', 'за', 'до', 'от', 'для', 'к', 'о', 'у', 'без', 'под', 'над', 'при', 'через', 'между', 'среди', 'вокруг', 'около', 'вместо', 'кроме', 'благодаря', 'согласно', 'вопреки', 'навстречу', 'вслед', 'вследствие', 'ввиду', 'наподобие', 'подобно', 'наряду', 'вместе', 'вдвоем', 'втроем', 'вчетвером', 'впятером', 'вшестером', 'всемером', 'восьмером', 'вдевятером', 'вдесятером',
    # Conjunctions and particles
    'а', 'но', 'да', 'или', 'либо', 'то', 'же', 'ли', 'бы', 'как', 'что', 'чтобы', 'если', 'хотя', 'пока', 'когда', 'где', 'куда', 'откуда', 'зачем', 'почему', 'сколько', 'чей', 'какой', 'который', 'тот', 'этот', 'сам', 'самый', 'весь', 'всякий', 'каждый', 'любой', 'никто', 'ничто', 'кто-то', 'что-то', 'кто-нибудь', 'что-нибудь', 'кто-либо', 'что-либо',
    # Common verbs and auxiliaries
    'быть', 'есть', 'был', 'была', 'было', 'были', 'будет', 'буду', 'будешь', 'будут', 'иметь', 'иметь', 'может', 'могу', 'можешь', 'могут', 'должен', 'должна', 'должно', 'должны',
    # Payment context stopwords
    'оплата', 'сплата', 'платеж', 'пользу', 'услуги', 'товары', 'работы', 'поставка', 'договор', 'контракт', 'счет', 'инвойс', 'основании', 'согласно', 'назначение', 'платежа',
    # Insurance context
    'страховой', 'страховая', 'страхование', 'полис', 'полиса', 'ОСЦПВ', 'ОСАГО', 'КАСКО'
}

# Ukrainian stopwords - core conjunctions, prepositions, service words
STOPWORDS_UK = {
    # Basic conjunctions and prepositions
    'і', 'в', 'з', 'та', 'на', 'по', 'за', 'до', 'від', 'для', 'к', 'о', 'у', 'без', 'під', 'над', 'при', 'через', 'між', 'серед', 'навколо', 'біля', 'замість', 'окрім', 'крім', 'завдяки', 'згідно', 'попри', 'назустріч', 'вслід', 'внаслідок', 'з огляду на', 'на кшталт', 'подібно', 'на зразок', 'разом', 'вдвох', 'втрьох', 'вчетверо', "вп'ятеро", 'вшестеро', 'всемеро', 'восьмеро', "вдев'ятеро", 'вдесятеро',
    # Conjunctions and particles
    'а', 'але', 'та', 'або', 'то', 'же', 'чи', 'би', 'як', 'що', 'щоб', 'якщо', 'хоча', 'поки', 'коли', 'де', 'куди', 'звідки', 'навіщо', 'чому', 'скільки', 'чий', 'який', 'той', 'цей', 'сам', 'самий', 'весь', 'всякий', 'кожен', 'будь-який', 'ніхто', 'ніщо', 'хтось', 'щось', 'хто-небудь', 'що-небудь', 'хто-або', 'що-або',
    # Common verbs and auxiliaries
    'бути', 'є', 'був', 'була', 'було', 'були', 'буде', 'буду', 'будеш', 'будуть', 'мати', 'може', 'можу', 'можеш', 'можуть', 'повинен', 'повинна', 'повинно', 'повинні',
    # Payment context stopwords
    'оплата', 'сплата', 'платіж', 'користь', 'послуги', 'товари', 'роботи', 'поставка', 'договір', 'контракт', 'рахунок', 'інвойс', 'підставі', 'згідно', 'призначення', 'платежу',
    # Insurance context
    'страховий', 'страхової', 'страхування', 'поліс', 'полісу', 'ОСЦПВ', 'ОСАГО', 'КАСКО'
}

# English stopwords - core conjunctions, prepositions, service words
STOPWORDS_EN = {
    # Basic prepositions and conjunctions
    'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'about', 'into', 'through', 'during', 'before', 'after', 'above', 'below', 'up', 'down', 'out', 'off', 'over', 'under', 'again', 'further', 'then', 'once',
    # Articles and determiners
    'the', 'a', 'an', 'this', 'that', 'these', 'those', 'my', 'your', 'his', 'her', 'its', 'our', 'their', 'some', 'any', 'all', 'each', 'every', 'no', 'none', 'both', 'either', 'neither', 'such', 'what', 'which', 'who', 'whom', 'whose', 'where', 'when', 'why', 'how',
    # Common verbs and auxiliaries
    'be', 'is', 'am', 'are', 'was', 'were', 'being', 'been', 'have', 'has', 'had', 'having', 'do', 'does', 'did', 'doing', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'shall',
    # Payment context stopwords
    'payment', 'for', 'services', 'goods', 'invoice', 'according', 'to', 'contract', 'agreement', 'purpose', 'beneficiary', 'reference'
}

# Legal forms for organizations (case-insensitive matching)
LEGAL_FORMS = {
    # Russian legal forms
    'ооо', 'оао', 'зао', 'пао', 'нао', 'тоо', 'ип', 'сп', 'кх', 'гуп', 'муп', 'фгуп', 'фгбу', 'фку', 'бу', 'ау', 'казенное', 'учреждение', 'предприятие', 'товарищество', 'общество', 'организация', 'компания', 'фирма', 'группа', 'холдинг', 'концерн', 'корпорация', 'банк', 'кооператив', 'артель', 'совхоз', 'колхоз',
    # Ukrainian legal forms
    'тов', 'тдв', 'ват', 'зат', 'пат', 'кт', 'фоп', 'сп', 'кфг', 'дп', 'кп', 'пп', 'установа', 'підприємство', 'товариство', 'компанія', 'фірма', 'група', 'холдинг', 'концерн', 'корпорація', 'банк', 'кооператив', 'артіль', 'радгосп', 'колгосп',
    # English legal forms
    'llc', 'ltd', 'inc', 'corp', 'co', 'company', 'corporation', 'limited', 'incorporated', 'partnership', 'lp', 'llp', 'pllc', 'pc', 'pa', 'group', 'holdings', 'holding', 'enterprises', 'enterprise', 'solutions', 'services', 'systems', 'technologies', 'tech', 'consulting', 'consultancy', 'firm', 'associates', 'partners', 'capital', 'investments', 'fund', 'trust', 'bank', 'financial', 'insurance', 'realty', 'properties', 'development', 'construction', 'trading', 'logistics', 'transport', 'shipping', 'manufacturing', 'industries', 'industrial', 'international', 'global', 'worldwide', 'universal', 'general', 'central', 'national', 'federal', 'state', 'municipal', 'public', 'private',
    # European legal forms
    'gmbh', 'ag', 'kg', 'ohg', 'sa', 'sarl', 'sas', 'sasu', 'eurl', 'sci', 'scp', 'sep', 'snc', 'scs', 'see', 'bv', 'nv', 'vof', 'cv', 'eenmanszaak', 'maatschap', 'cooperatie', 'onderlinge', 'stichting', 'vereniging', 'srl', 'spa', 'snc', 'sas', 'sapa', 'scrl', 'scri', 'sc', 'sd', 'se', 'eeig', 'ewiv', 'ab', 'hb', 'kb', 'ek', 'bf', 'mb', 'if', 'fmba', 'ba', 'sf', 'uf', 'da', 'i/s', 'k/s', 'a/s', 'aps', 'smba', 'g/s', 'p/s', 'as', 'ans', 'ba', 'bf', 'da', 'enk', 'fkf', 'iks', 'kf', 'nuf', 'sf', 'da'
}

# Payment and financial context triggers
PAYMENT_CONTEXT = {
    # Russian payment context
    'платеж', 'платёж', 'оплата', 'сплата', 'платити', 'отправитель', 'получатель', 'рахунок', 'счет', 'инвойс', 'транзакция', 'переказ', 'перевод', 'депозит', 'зняття', 'снятие', 'банк', 'карта', 'картка', 'готівка', 'наличные', 'чек', 'переказ', 'перевод', 'онлайн', 'цифровий', 'цифровой', 'мобільний', 'мобильный', 'моментальний', 'мгновенный', 'безпечний', 'безопасный', 'верифікований', 'верифицированный', 'підтверджений', 'подтвержденный', 'завершений', 'завершенный', 'очікується', 'ожидается', 'невдалий', 'неудачный', 'скасований', 'отмененный', 'повернення', 'возврат', 'збір', 'сбор', 'комісія', 'комиссия', 'податок', 'налог', 'знижка', 'скидка', 'бонус', 'нагорода', 'награда', 'кредит', 'дебет', 'баланс', 'виписка', 'выписка', 'звіт', 'отчет',
    # Insurance context
    'страховой', 'страховая', 'страхование', 'полис', 'полиса', 'ОСЦПВ', 'ОСАГО', 'КАСКО',
    # Ukrainian payment context
    'платіж', 'оплата', 'сплата', 'платити', 'одержувач', 'відправник', 'рахунок', 'інвойс', 'транзакція', 'переказ', 'депозит', 'зняття', 'банк', 'картка', 'готівка', 'чек', 'онлайн', 'цифровий', 'мобільний', 'моментальний', 'безпечний', 'верифікований', 'підтверджений', 'завершений', 'очікується', 'невдалий', 'скасований', 'повернення', 'збір', 'комісія', 'податок', 'знижка', 'бонус', 'нагорода', 'кредит', 'дебет', 'баланс', 'виписка', 'звіт',
    # Insurance context
    'страховий', 'страхової', 'страхування', 'поліс', 'полісу', 'ОСЦПВ', 'ОСАГО', 'КАСКО',
    # English payment context
    'payment', 'pay', 'beneficiary', 'sender', 'receiver', 'recipient', 'account', 'invoice', 'bill', 'transaction', 'transfer', 'deposit', 'withdrawal', 'bank', 'card', 'cash', 'check', 'wire', 'online', 'digital', 'mobile', 'instant', 'secure', 'verified', 'confirmed', 'completed', 'pending', 'failed', 'cancelled', 'refund', 'charge', 'fee', 'commission', 'tax', 'discount', 'bonus', 'reward', 'credit', 'debit', 'balance', 'statement', 'report'
}

# Aho-Corasick tier configuration for pattern organization
AC_TIERS = {
    'T0': {
        'name': 'Exact Documents & IDs',
        'confidence': 0.95,
        'patterns': ['passport', 'tax_id', 'iban', 'swift', 'inn', 'edrpou', 'ogrn'],
        'description': 'High-precision document and identifier patterns'
    },
    'T1': {
        'name': 'Contextual Names',
        'confidence': 0.85,
        'patterns': ['payment_triggers', 'contract_triggers', 'legal_context'],
        'description': 'Names with strong contextual triggers'
    },
    'T2': {
        'name': 'Structured Names',
        'confidence': 0.75,
        'patterns': ['last_f_m_format', 'formal_titles', 'initials'],
        'description': 'Formal name formats and structures'
    },
    'T3': {
        'name': 'Company Names',
        'confidence': 0.65,
        'patterns': ['legal_forms', 'quoted_names', 'caps_names'],
        'description': 'Organization names with legal forms'
    }
}

def get_stopwords(language: str) -> set:
    """Get stopwords for specified language."""
    language_map = {
        'ru': STOPWORDS_RU,
        'uk': STOPWORDS_UK,
        'en': STOPWORDS_EN
    }
    return language_map.get(language, set())

def get_all_stopwords() -> set:
    """Get combined stopwords from all languages."""
    return STOPWORDS_RU | STOPWORDS_UK | STOPWORDS_EN

def is_stopword(token: str, language: str = None) -> bool:
    """Check if token is a stopword in specified language or any language."""
    token_lower = token.lower()
    if language:
        return token_lower in get_stopwords(language)
    return token_lower in get_all_stopwords()

def is_legal_form(token: str) -> bool:
    """Check if token is a legal form."""
    return token.lower() in LEGAL_FORMS

def is_payment_context(token: str) -> bool:
    """Check if token is payment/financial context."""
    return token.lower() in PAYMENT_CONTEXT

def get_tier_patterns(tier: str) -> dict:
    """Get pattern configuration for specified tier."""
    return AC_TIERS.get(tier, {})

def get_all_lexicon_tokens() -> set:
    """Get all tokens from all lexicons for comprehensive AC pattern generation."""
    all_tokens = set()
    all_tokens.update(get_all_stopwords())
    all_tokens.update(LEGAL_FORMS)
    all_tokens.update(PAYMENT_CONTEXT)
    return all_tokens

# Export main collections for backward compatibility
__all__ = [
    'STOPWORDS_RU', 'STOPWORDS_UK', 'STOPWORDS_EN',
    'LEGAL_FORMS', 'PAYMENT_CONTEXT', 'AC_TIERS',
    'get_stopwords', 'get_all_stopwords', 'is_stopword',
    'is_legal_form', 'is_payment_context', 'get_tier_patterns',
    'get_all_lexicon_tokens'
]