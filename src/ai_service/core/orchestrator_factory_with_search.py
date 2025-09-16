"""
Orchestrator Factory with Search Integration

Factory for creating UnifiedOrchestratorWithSearch instances with proper service initialization
and search integration.
"""

from typing import Any, Optional

from ..config.settings import DecisionConfig, DECISION_CONFIG
from ..core.decision_engine import DecisionEngine
from ..core.unified_orchestrator_with_search import UnifiedOrchestratorWithSearch
from ..exceptions import ServiceInitializationError
from ..utils import get_logger

logger = get_logger(__name__)


class OrchestratorFactoryWithSearch:
    """
    Factory for creating orchestrators with search integration.
    
    Extends the original OrchestratorFactory with HybridSearchService support.
    """

    @staticmethod
    async def create_orchestrator(
        *,
        # Service feature flags
        enable_smart_filter: bool = True,
        enable_variants: bool = False,
        enable_embeddings: bool = False,
        enable_decision_engine: bool = False,
        enable_hybrid_search: bool = False,  # NEW
        # Processing behavior
        allow_smart_filter_skip: bool = False,
        # Custom service implementations (for testing/customization)
        validation_service: Optional[Any] = None,
        smart_filter_service: Optional[Any] = None,
        language_service: Optional[Any] = None,
        unicode_service: Optional[Any] = None,
        normalization_service: Optional[Any] = None,
        signals_service: Optional[Any] = None,
        variants_service: Optional[Any] = None,
        embeddings_service: Optional[Any] = None,
        decision_engine: Optional[Any] = None,
        hybrid_search_service: Optional[Any] = None,  # NEW
        # Metrics
        metrics_service: Optional[Any] = None,
    ) -> UnifiedOrchestratorWithSearch:
        """
        Create orchestrator with search integration.
        
        Args:
            enable_hybrid_search: Enable hybrid search layer
            hybrid_search_service: Custom HybridSearchService instance
            ... (other parameters same as original factory)
            
        Returns:
            UnifiedOrchestratorWithSearch instance
        """
        logger.info("Creating orchestrator with search integration...")
        
        # ================================================================
        # Initialize core services (same as original factory)
        # ================================================================
        
        # Validation service (required)
        if validation_service is None:
            try:
                from ..layers.validation.validation_service import ValidationService
                validation_service = ValidationService()
                logger.info("Validation service initialized")
            except Exception as e:
                raise ServiceInitializationError(f"Failed to initialize validation service: {e}")
        
        # Smart filter service (optional)
        if enable_smart_filter and smart_filter_service is None:
            try:
                from ..layers.smart_filter.smart_filter_adapter import SmartFilterAdapter
                smart_filter_service = SmartFilterAdapter()
                logger.info("Smart filter service initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize smart filter service: {e}")
                smart_filter_service = None
                enable_smart_filter = False
        
        # Language detection service (required)
        if language_service is None:
            try:
                from ..layers.language_detection.language_detection_service import LanguageDetectionService
                language_service = LanguageDetectionService()
                logger.info("Language detection service initialized")
            except Exception as e:
                raise ServiceInitializationError(f"Failed to initialize language detection service: {e}")
        
        # Unicode service (required)
        if unicode_service is None:
            try:
                from ..layers.unicode.unicode_service import UnicodeService
                unicode_service = UnicodeService()
                logger.info("Unicode service initialized")
            except Exception as e:
                raise ServiceInitializationError(f"Failed to initialize unicode service: {e}")
        
        # Normalization service (required)
        if normalization_service is None:
            try:
                from ..layers.normalization.normalization_service import NormalizationService
                normalization_service = NormalizationService()
                logger.info("Normalization service initialized")
            except Exception as e:
                raise ServiceInitializationError(f"Failed to initialize normalization service: {e}")
        
        # Signals service (required)
        if signals_service is None:
            try:
                from ..layers.signals.signals_service import SignalsService
                signals_service = SignalsService()
                logger.info("Signals service initialized")
            except Exception as e:
                raise ServiceInitializationError(f"Failed to initialize signals service: {e}")
        
        # Variants service (optional)
        if enable_variants and variants_service is None:
            try:
                from ..layers.variants.variants_service import VariantsService
                variants_service = VariantsService()
                logger.info("Variants service initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize variants service: {e}")
                variants_service = None
                enable_variants = False
        
        # Embeddings service (optional)
        if enable_embeddings and embeddings_service is None:
            try:
                from ..config import EmbeddingConfig
                from ..layers.embeddings.embedding_service import EmbeddingService
                embedding_config = EmbeddingConfig()
                embeddings_service = EmbeddingService(embedding_config)
                await embeddings_service.initialize()
                logger.info("Embeddings service initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize embeddings service: {e}")
                embeddings_service = None
                enable_embeddings = False
        
        # Decision engine (optional)
        if enable_decision_engine and decision_engine is None:
            try:
                decision_engine = DecisionEngine(DECISION_CONFIG)
                logger.info("Decision engine initialized with unified config (ENV overrides supported)")
            except Exception as e:
                logger.warning(f"Failed to initialize decision engine: {e}")
                decision_engine = None
                enable_decision_engine = False
        
        # ================================================================
        # Initialize search service (NEW)
        # ================================================================
        if enable_hybrid_search and hybrid_search_service is None:
            try:
                from ..layers.search import HybridSearchService, HybridSearchConfig
                search_config = HybridSearchConfig()
                hybrid_search_service = HybridSearchService(search_config)
                await hybrid_search_service.initialize()
                logger.info("Hybrid search service initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize hybrid search service: {e}")
                hybrid_search_service = None
                enable_hybrid_search = False
        
        # ================================================================
        # Create orchestrator with search integration
        # ================================================================
        
        orchestrator = UnifiedOrchestratorWithSearch(
            # Core services
            validation_service=validation_service,
            smart_filter_service=smart_filter_service,
            language_service=language_service,
            unicode_service=unicode_service,
            normalization_service=normalization_service,
            signals_service=signals_service,
            variants_service=variants_service,
            embeddings_service=embeddings_service,
            decision_engine=decision_engine,
            # Search service (NEW)
            hybrid_search_service=hybrid_search_service,
            # Feature flags
            enable_smart_filter=enable_smart_filter,
            enable_variants=enable_variants,
            enable_embeddings=enable_embeddings,
            enable_decision_engine=enable_decision_engine,
            enable_hybrid_search=enable_hybrid_search,  # NEW
            # Processing behavior
            allow_smart_filter_skip=allow_smart_filter_skip,
            # Metrics
            metrics_service=metrics_service,
        )
        
        logger.info(f"Orchestrator created successfully with search: {enable_hybrid_search}")
        return orchestrator
    
    @staticmethod
    async def create_orchestrator_from_config(config: dict) -> UnifiedOrchestratorWithSearch:
        """
        Create orchestrator from configuration dictionary.
        
        Args:
            config: Configuration dictionary with service settings
            
        Returns:
            UnifiedOrchestratorWithSearch instance
        """
        return await OrchestratorFactoryWithSearch.create_orchestrator(
            enable_smart_filter=config.get("enable_smart_filter", True),
            enable_variants=config.get("enable_variants", False),
            enable_embeddings=config.get("enable_embeddings", False),
            enable_decision_engine=config.get("enable_decision_engine", False),
            enable_hybrid_search=config.get("enable_hybrid_search", False),  # NEW
            allow_smart_filter_skip=config.get("allow_smart_filter_skip", False),
            metrics_service=config.get("metrics_service"),
        )
    
    @staticmethod
    def get_default_config() -> dict:
        """
        Get default configuration for orchestrator with search.
        
        Returns:
            Default configuration dictionary
        """
        return {
            "enable_smart_filter": True,
            "enable_variants": False,
            "enable_embeddings": False,
            "enable_decision_engine": False,
            "enable_hybrid_search": False,  # NEW
            "allow_smart_filter_skip": False,
            "metrics_service": None,
        }
