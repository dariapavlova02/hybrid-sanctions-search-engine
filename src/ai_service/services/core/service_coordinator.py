"""
Service Coordinator
Manages initialization and coordination of all AI services following SOLID principles.
"""

from typing import Any, Dict, Optional
from dataclasses import dataclass, field

from ..config import PERFORMANCE_CONFIG
from ..exceptions import ServiceInitializationError
from ..utils import get_logger
from .cache_service import CacheService
from .embedding_service import EmbeddingService
from .language_detection_service import LanguageDetectionService
from .normalization_service import NormalizationService
from .pattern_service import PatternService
from .signal_service import SignalService
from .smart_filter.smart_filter_service import SmartFilterService
from .template_builder import TemplateBuilder
from .unicode_service import UnicodeService


@dataclass
class ServiceRegistry:
    """Registry of initialized services"""
    
    unicode_service: Optional[UnicodeService] = None
    language_service: Optional[LanguageDetectionService] = None
    normalization_service: Optional[NormalizationService] = None
    pattern_service: Optional[PatternService] = None
    template_builder: Optional[TemplateBuilder] = None
    embedding_service: Optional[EmbeddingService] = None
    cache_service: Optional[CacheService] = None
    signal_service: Optional[SignalService] = None
    smart_filter: Optional[SmartFilterService] = None
    
    # Service states for health checking
    service_states: Dict[str, str] = field(default_factory=dict)


class ServiceCoordinator:
    """
    Coordinates initialization and management of all AI services.
    Follows Single Responsibility Principle - only handles service lifecycle.
    """
    
    def __init__(self, cache_size: Optional[int] = None, default_ttl: Optional[int] = None):
        """
        Initialize service coordinator
        
        Args:
            cache_size: Cache size override
            default_ttl: Default TTL override
        """
        self.logger = get_logger(__name__)
        self._cache_size = cache_size or PERFORMANCE_CONFIG.cache_size
        self._default_ttl = default_ttl or PERFORMANCE_CONFIG.cache_ttl
        self._registry = ServiceRegistry()
        
    def initialize_all_services(self) -> ServiceRegistry:
        """
        Initialize all services in dependency order
        
        Returns:
            ServiceRegistry with all initialized services
            
        Raises:
            ServiceInitializationError: If any service fails to initialize
        """
        try:
            # Initialize core services first (no dependencies)
            self._initialize_core_services()
            
            # Initialize dependent services
            self._initialize_dependent_services()
            
            # Initialize composite services last
            self._initialize_composite_services()
            
            self.logger.info("All services initialized successfully")
            return self._registry
            
        except Exception as e:
            self.logger.error(f"Failed to initialize services: {e}")
            raise ServiceInitializationError(f"Service initialization failed: {str(e)}")
    
    def _initialize_core_services(self) -> None:
        """Initialize core services with no dependencies"""
        
        # Unicode service - no dependencies
        self._registry.unicode_service = UnicodeService()
        self._registry.service_states['unicode'] = 'active'
        self.logger.debug("Unicode service initialized")
        
        # Language detection service - no dependencies
        self._registry.language_service = LanguageDetectionService()
        self._registry.service_states['language'] = 'active'
        self.logger.debug("Language detection service initialized")
        
        # Cache service - no dependencies
        self._registry.cache_service = CacheService(
            max_size=self._cache_size,
            default_ttl=self._default_ttl
        )
        self._registry.service_states['cache'] = 'active'
        self.logger.debug("Cache service initialized")
        
    def _initialize_dependent_services(self) -> None:
        """Initialize services that depend on core services"""
        
        # Normalization service - may use language detection internally
        self._registry.normalization_service = NormalizationService()
        self._registry.service_states['normalization'] = 'active'
        self.logger.debug("Normalization service initialized")
        
        # Pattern service - depends on normalization
        self._registry.pattern_service = PatternService()
        self._registry.service_states['patterns'] = 'active'
        self.logger.debug("Pattern service initialized")
        
        # Template builder - depends on pattern service
        self._registry.template_builder = TemplateBuilder()
        self._registry.service_states['templates'] = 'active'
        self.logger.debug("Template builder initialized")
        
        # Embedding service - independent but resource-heavy
        self._registry.embedding_service = EmbeddingService()
        self._registry.service_states['embeddings'] = 'active'
        self.logger.debug("Embedding service initialized")
        
        # Signal service - may depend on multiple core services
        self._registry.signal_service = SignalService()
        self._registry.service_states['signals'] = 'active'
        self.logger.debug("Signal service initialized")
        
    def _initialize_composite_services(self) -> None:
        """Initialize composite services that depend on multiple other services"""
        
        # Smart filter - depends on language and signal services
        try:
            self._registry.smart_filter = SmartFilterService(
                language_service=self._registry.language_service,
                signal_service=self._registry.signal_service,
            )
            self._registry.service_states['smart_filter'] = 'active'
            self.logger.debug("Smart filter service initialized")
        except Exception as e:
            self.logger.warning(f"Smart filter initialization failed: {e}")
            self._registry.smart_filter = None
            self._registry.service_states['smart_filter'] = 'disabled'
    
    def get_service_health(self) -> Dict[str, Any]:
        """
        Get health status of all services
        
        Returns:
            Health status information
        """
        return {
            'total_services': len(self._registry.service_states),
            'active_services': sum(1 for state in self._registry.service_states.values() if state == 'active'),
            'service_states': self._registry.service_states.copy(),
            'registry_status': 'healthy' if self._registry else 'uninitialized'
        }
    
    def shutdown_services(self) -> None:
        """Clean shutdown of all services"""
        
        # Shutdown in reverse dependency order
        services_to_shutdown = [
            ('smart_filter', self._registry.smart_filter),
            ('signals', self._registry.signal_service),
            ('embeddings', self._registry.embedding_service),
            ('templates', self._registry.template_builder),
            ('patterns', self._registry.pattern_service),
            ('normalization', self._registry.normalization_service),
            ('cache', self._registry.cache_service),
            ('language', self._registry.language_service),
            ('unicode', self._registry.unicode_service),
        ]
        
        for service_name, service in services_to_shutdown:
            try:
                if service and hasattr(service, 'shutdown'):
                    service.shutdown()
                self._registry.service_states[service_name] = 'shutdown'
                self.logger.debug(f"{service_name} service shutdown")
            except Exception as e:
                self.logger.warning(f"Error shutting down {service_name}: {e}")
        
        self.logger.info("All services shutdown completed")