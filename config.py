"""
AI Service Configuration
Legacy configuration file - use src/ai_service/config/ for new code
This file is maintained for backward compatibility
"""

import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import from new configuration system
try:
    from src.ai_service.config import (
        SERVICE_CONFIG,
        SECURITY_CONFIG,
        INTEGRATION_CONFIG,
        DEPLOYMENT_CONFIG,
        PERFORMANCE_CONFIG,
        LOGGING_CONFIG
    )
    from src.ai_service.constants import (
        VARIANT_SCORES,
        MORPHOLOGY_CONFIG,
        VARIANT_GENERATION_CONFIG,
        NORMALIZATION_CONFIG,
        CACHE_CONFIG,
        TESTING_CONFIG
    )
    
    # Re-export for backward compatibility
    __all__ = [
        'SERVICE_CONFIG',
        'SECURITY_CONFIG', 
        'INTEGRATION_CONFIG',
        'DEPLOYMENT_CONFIG',
        'PERFORMANCE_CONFIG',
        'LOGGING_CONFIG',
        'VARIANT_SCORES',
        'MORPHOLOGY_CONFIG',
        'VARIANT_GENERATION_CONFIG',
        'NORMALIZATION_CONFIG',
        'CACHE_CONFIG',
        'TESTING_CONFIG'
    ]
    
except ImportError:
    # Fallback to old configuration if new system is not available
    print("Warning: Using fallback configuration. Please update imports to use src.ai_service.config")
    
    # Legacy configuration (fallback)
    VARIANT_SCORES = {
        'morphological': 1.0,
        'transliteration': 0.9,
        'phonetic': 0.8,
        'visual_similarity': 0.7,
        'typo': 0.6,
        'regional': 0.5,
        'fallback': 0.3
    }
    
    MORPHOLOGY_CONFIG = {
        'max_declensions': 20,
        'max_diminutives': 15,
        'confidence_threshold': 0.7,
        'blacklist_enabled': True,
    }
    
    VARIANT_GENERATION_CONFIG = {
        'max_variants_per_type': 50,
        'max_total_variants': 200,
        'include_rare_patterns': False,
        'phonetic_similarity_threshold': 0.8,
    }
    
    NORMALIZATION_CONFIG = {
        'max_tokens': 100,
        'preserve_names': True,
        'clean_unicode': True,
        'enable_morphology': True,
        'enable_transliterations': True,
    }
    
    CACHE_CONFIG = {
        'default_ttl': 3600,
        'max_size': 10000,
        'cleanup_interval': 300,
    }
    
    LOGGING_CONFIG = {
        'level': 'INFO',
        'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        'file_logging': True,
        'console_logging': True,
    }
    
    TESTING_CONFIG = {
        'max_test_variants': 10,
        'test_timeout': 30,
        'parallel_tests': True,
    }
    
    PERFORMANCE_CONFIG = {
        'max_concurrent_requests': 10,
        'batch_size': 100,
        'memory_limit_mb': 1024,
        'cpu_limit_percent': 80,
    }
    
    SECURITY_CONFIG = {
        'max_input_length': 10000,
        'sanitize_input': True,
        'rate_limit_enabled': True,
        'max_requests_per_minute': 100,
        'admin_api_key': os.getenv('ADMIN_API_KEY', ''),
    }
    
    INTEGRATION_CONFIG = {
        'api_version': 'v1',
        'cors_enabled': True,
        'health_check_interval': 60,
        'metrics_enabled': True,
        'allowed_origins': ['http://localhost:3000', 'http://localhost:8080'],
    }
    
    APP_ENV = os.getenv('APP_ENV', 'development')
    
    DEPLOYMENT_CONFIG = {
        'environment': APP_ENV,
        'debug_mode': APP_ENV == 'development',
        'auto_reload': APP_ENV == 'development',
        'workers': int(os.getenv('WORKERS', '1') if APP_ENV == 'production' else '1'),
    }
