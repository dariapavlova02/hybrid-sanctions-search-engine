"""
Constants for AI Service
Centralized constants and configuration values
"""

from typing import Dict, List, Any

# Service configuration
DEFAULT_CACHE_SIZE = 10000
DEFAULT_CACHE_TTL = 3600
DEFAULT_MAX_INPUT_LENGTH = 10000
DEFAULT_MAX_VARIANTS = 50
DEFAULT_SIMILARITY_THRESHOLD = 0.8

# Supported languages
SUPPORTED_LANGUAGES = ['en', 'ru', 'uk']
DEFAULT_LANGUAGE = 'en'
FALLBACK_LANGUAGE = 'en'

# Language names
LANGUAGE_NAMES = {
    'en': 'English',
    'ru': 'Russian', 
    'uk': 'Ukrainian'
}

# Language mapping for detection
LANGUAGE_MAPPING = {
    # English and similar
    'en': 'en',
    'en-US': 'en',
    'en-GB': 'en',
    
    # Russian and similar
    'ru': 'ru',
    'be': 'ru',  # Belarusian -> Russian
    'kk': 'ru',  # Kazakh -> Russian
    'ky': 'ru',  # Kyrgyz -> Russian
    
    # Ukrainian
    'uk': 'uk',
    
    # Other Slavic languages -> Russian
    'bg': 'ru',  # Bulgarian
    'sr': 'ru',  # Serbian
    'hr': 'ru',  # Croatian
    'sl': 'ru',  # Slovenian
    'pl': 'ru'   # Polish
}

# Unicode normalization mappings
UNICODE_MAPPINGS = {
    'ё': 'е',  # Russian yo -> e
    'і': 'и',  # Ukrainian i -> i
    'ї': 'и',  # Ukrainian yi -> i
    'є': 'е',  # Ukrainian ye -> e
    'ґ': 'г',  # Ukrainian g -> g
}

# Language patterns for fast detection
LANGUAGE_PATTERNS = {
    'en': [
        r'\b[aeiou]{2,}',  # Long vowels
        r'\b(the|and|or|but|in|on|at|to|for|of|with|by)\b',
        r'\b(is|are|was|were|be|been|being|have|has|had|do|does|did)\b'
    ],
    'ru': [
        r'\b(и|в|на|с|по|за|от|до|из|у|о|а|но|или|если|когда|где|как|что|кто)\b',
        r'\b(был|была|были|быть|есть|нет|это|тот|эта|эти)\b',
        r'[аеёиоуыэюя]{2,}',  # Long vowels
        r'[йцкнгшщзхфвпрлджчсмтб]{3,}'  # Long consonants
    ],
    'uk': [
        r'\b(і|в|на|з|по|за|від|до|з|у|о|а|але|або|якщо|коли|де|як|що|хто)\b',
        r'\b(був|була|були|бути|є|немає|це|той|ця|ці)\b',
        r'[аеєиіїоущюя]{2,}',  # Long vowels
        r'[йцкнгшщзхфвпрлджчсмтб]{3,}'  # Long consonants
    ]
}

# Confidence thresholds
CONFIDENCE_THRESHOLDS = {
    'high_confidence': 0.8,
    'medium_confidence': 0.6,
    'min_processing_threshold': 0.3,
    'low_confidence': 0.1
}

# Variant generation scores
VARIANT_SCORES = {
    'morphological': 1.0,      # Morphological variants (highest priority)
    'transliteration': 0.9,    # Transliterations
    'phonetic': 0.8,           # Phonetic variants
    'visual_similarity': 0.7,  # Visual similarities
    'typo': 0.6,               # Typographical errors
    'regional': 0.5,            # Regional variants
    'fallback': 0.3             # Fallback variants
}

# Morphology configuration
MORPHOLOGY_CONFIG = {
    'max_declensions': 20,      # Maximum number of declensions
    'max_diminutives': 15,      # Maximum number of diminutive forms
    'confidence_threshold': 0.7, # Confidence threshold for pymorphy3
    'blacklist_enabled': True,  # Enable lemmatization blacklist
}

# Variant generation configuration
VARIANT_GENERATION_CONFIG = {
    'max_variants_per_type': 50,    # Maximum number of variants per type
    'max_total_variants': 200,      # Maximum total number of variants
    'include_rare_patterns': False, # Include rare patterns
    'phonetic_similarity_threshold': 0.8,  # Phonetic similarity threshold
}

# Normalization configuration
NORMALIZATION_CONFIG = {
    'max_tokens': 100,          # Maximum number of tokens
    'preserve_names': True,      # Preserve names
    'clean_unicode': True,       # Clean Unicode
    'enable_morphology': True,   # Enable morphology
    'enable_transliterations': True,  # Enable transliterations
}

# Cache configuration
CACHE_CONFIG = {
    'default_ttl': 3600,        # Default TTL (seconds)
    'max_size': 10000,          # Maximum cache size
    'cleanup_interval': 300,    # Cleanup interval (seconds)
}

# Performance configuration
PERFORMANCE_CONFIG = {
    'max_concurrent_requests': 10,  # Maximum number of concurrent requests
    'batch_size': 100,              # Batch size for processing
    'memory_limit_mb': 1024,        # Memory limit (MB)
    'cpu_limit_percent': 80,        # CPU limit (%)
}

# Security configuration
SECURITY_CONFIG = {
    'max_input_length': 10000,      # Maximum input text length
    'sanitize_input': True,         # Input sanitization
    'rate_limit_enabled': True,     # Enable rate limiting
    'max_requests_per_minute': 100, # Maximum requests per minute
    'admin_api_key': 'your-secure-api-key-here',  # API key for administrative endpoints
}

# Integration configuration
INTEGRATION_CONFIG = {
    'api_version': 'v1',            # API version
    'cors_enabled': True,           # Enable CORS
    'health_check_interval': 60,    # Health check interval (seconds)
    'metrics_enabled': True,        # Enable metrics
    'allowed_origins': ['http://localhost:3000', 'http://localhost:8080'],  # Allowed domains for CORS
}

# Logging configuration
LOGGING_CONFIG = {
    'level': 'INFO',            # Logging level
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'file_logging': True,       # File logging
    'console_logging': True,    # Console logging
}

# Testing configuration
TESTING_CONFIG = {
    'max_test_variants': 10,    # Maximum number of variants in tests
    'test_timeout': 30,         # Test timeout (seconds)
    'parallel_tests': True,     # Parallel test execution
}

# API endpoints
API_ENDPOINTS = {
    'health': '/health',
    'process': '/process',
    'process_batch': '/process-batch',
    'search_similar': '/search-similar',
    'analyze_complexity': '/analyze-complexity',
    'stats': '/stats',
    'clear_cache': '/clear-cache',
    'reset_stats': '/reset-stats',
    'normalize': '/normalize',
    'languages': '/languages'
}

# Service features
SERVICE_FEATURES = [
    'Text normalization',
    'Variant generation',
    'Signal detection',
    'Similarity search',
    'Complexity analysis',
    'Batch processing',
    'Caching',
    'Multi-language support',
    'Real-time statistics'
]

# Error messages
ERROR_MESSAGES = {
    'SERVICE_NOT_INITIALIZED': 'Service not initialized',
    'INVALID_INPUT': 'Invalid input provided',
    'PROCESSING_FAILED': 'Text processing failed',
    'LANGUAGE_DETECTION_FAILED': 'Language detection failed',
    'NORMALIZATION_FAILED': 'Text normalization failed',
    'VARIANT_GENERATION_FAILED': 'Variant generation failed',
    'EMBEDDING_FAILED': 'Embedding generation failed',
    'CACHE_ERROR': 'Cache operation failed',
    'VALIDATION_ERROR': 'Input validation failed',
    'AUTHENTICATION_FAILED': 'Authentication failed',
    'AUTHORIZATION_FAILED': 'Authorization failed',
    'RATE_LIMIT_EXCEEDED': 'Rate limit exceeded',
    'SERVICE_UNAVAILABLE': 'Service temporarily unavailable',
    'INTERNAL_ERROR': 'Internal server error'
}

# Success messages
SUCCESS_MESSAGES = {
    'PROCESSING_SUCCESS': 'Text processed successfully',
    'NORMALIZATION_SUCCESS': 'Text normalized successfully',
    'VARIANT_GENERATION_SUCCESS': 'Variants generated successfully',
    'CACHE_CLEARED': 'Cache cleared successfully',
    'STATS_RESET': 'Statistics reset successfully'
}
