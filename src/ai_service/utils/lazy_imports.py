"""
Lazy imports with graceful degradation for optional dependencies.
"""

from typing import Optional, Any, Dict
import logging

logger = logging.getLogger(__name__)

# Global cache for loaded modules
_loaded_modules: Dict[str, Any] = {}

def lazy_import(module_name: str, package: Optional[str] = None) -> Any:
    """
    Lazy import with graceful degradation.
    
    Args:
        module_name: Name of the module to import
        package: Package name for relative imports
        
    Returns:
        The imported module or None if import fails
    """
    if module_name in _loaded_modules:
        return _loaded_modules[module_name]
    
    try:
        module = __import__(module_name, fromlist=[package] if package else None)
        _loaded_modules[module_name] = module
        logger.debug(f"Successfully imported {module_name}")
        return module
    except ImportError as e:
        logger.warning(f"Failed to import {module_name}: {e}")
        _loaded_modules[module_name] = None
        return None
    except Exception as e:
        logger.error(f"Unexpected error importing {module_name}: {e}")
        _loaded_modules[module_name] = None
        return None

def get_nameparser() -> Optional[Any]:
    """Get nameparser module if available."""
    return lazy_import("nameparser")

def get_rapidfuzz() -> Optional[Any]:
    """Get rapidfuzz module if available."""
    return lazy_import("rapidfuzz")

def get_spacy_en() -> Optional[Any]:
    """Get English spacy model if available."""
    try:
        import en_core_web_sm
        return en_core_web_sm.load()
    except Exception as e:
        logger.warning(f"Failed to load en_core_web_sm: {e}")
        return None

def get_spacy_uk() -> Optional[Any]:
    """Get Ukrainian spacy model if available."""
    try:
        import uk_core_news_sm
        return uk_core_news_sm.load()
    except Exception as e:
        logger.warning(f"Failed to load uk_core_news_sm: {e}")
        return None

def get_spacy_ru() -> Optional[Any]:
    """Get Russian spacy model if available."""
    try:
        import ru_core_news_sm
        return ru_core_news_sm.load()
    except Exception as e:
        logger.warning(f"Failed to load ru_core_news_sm: {e}")
        return None

# Global instances for easy access
NLP_EN: Optional[Any] = None
NLP_UK: Optional[Any] = None
NLP_RU: Optional[Any] = None
NAMEPARSER: Optional[Any] = None
RAPIDFUZZ: Optional[Any] = None

def initialize_lazy_imports() -> None:
    """Initialize all lazy imports."""
    global NLP_EN, NLP_UK, NLP_RU, NAMEPARSER, RAPIDFUZZ
    
    logger.info("Initializing lazy imports...")
    
    # Initialize spacy models
    NLP_EN = get_spacy_en()
    NLP_UK = get_spacy_uk()
    NLP_RU = get_spacy_ru()
    
    # Initialize other modules
    NAMEPARSER = get_nameparser()
    RAPIDFUZZ = get_rapidfuzz()
    
    # Log status
    status = {
        "spacy_en": NLP_EN is not None,
        "spacy_uk": NLP_UK is not None,
        "spacy_ru": NLP_RU is not None,
        "nameparser": NAMEPARSER is not None,
        "rapidfuzz": RAPIDFUZZ is not None,
    }
    
    logger.info(f"Lazy imports status: {status}")

def is_available(module_name: str) -> bool:
    """Check if a module is available."""
    return _loaded_modules.get(module_name) is not None

def get_available_modules() -> Dict[str, bool]:
    """Get status of all modules."""
    return {
        "spacy_en": NLP_EN is not None,
        "spacy_uk": NLP_UK is not None,
        "spacy_ru": NLP_RU is not None,
        "nameparser": NAMEPARSER is not None,
        "rapidfuzz": RAPIDFUZZ is not None,
    }
