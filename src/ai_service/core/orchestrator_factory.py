"""
Orchestrator Factory - Build unified orchestrator with existing services.

This factory wires together all the existing service implementations
into the unified orchestrator architecture.
"""

from typing import Optional

from ..config import SERVICE_CONFIG, FEATURE_FLAGS
from ..exceptions import ServiceInitializationError
# EmbeddingService imported locally to avoid circular imports
from ..layers.language.language_detection_service import LanguageDetectionService
from ..layers.normalization.normalization_service import NormalizationService
from ..layers.signals.signals_service import SignalsService
from ..layers.smart_filter.smart_filter_adapter import SmartFilterAdapter
from ..layers.unicode.unicode_service import UnicodeService

# Import existing service implementations
from ..layers.validation.validation_service import ValidationService
# VariantGenerationService imported locally to avoid circular imports
from ..utils import get_logger
from .decision_engine import DecisionEngine
from ..config.settings import DecisionConfig, DECISION_CONFIG
from .unified_orchestrator import UnifiedOrchestrator

logger = get_logger(__name__)


class OrchestratorFactory:
    """
    Factory for creating properly configured UnifiedOrchestrator instances.

    This handles the complexity of wiring together all the service dependencies
    and ensures proper initialization order.
    """

    @staticmethod
    async def create_orchestrator(
        *,
        # Service feature flags
        enable_smart_filter: bool = True,
        enable_variants: bool = False,
        enable_embeddings: bool = False,
        enable_decision_engine: bool = False,
        # Processing behavior
        allow_smart_filter_skip: bool = False,
        # Custom service implementations (for testing/customization)
        validation_service: Optional = None,
        smart_filter_service: Optional = None,
        language_service: Optional = None,
        unicode_service: Optional = None,
        normalization_service: Optional = None,
        signals_service: Optional = None,
        variants_service: Optional = None,
        embeddings_service: Optional = None,
        decision_engine: Optional = None,
    ) -> UnifiedOrchestrator:
        """
        Create a fully configured UnifiedOrchestrator.

        Args:
            enable_smart_filter: Enable pre-processing filter
            enable_variants: Enable variant generation
            enable_embeddings: Enable embedding generation
            enable_decision_engine: Enable automated match/no-match decisions
            allow_smart_filter_skip: Allow smart filter to skip expensive processing
            *_service: Custom service implementations (optional)

        Returns:
            Configured UnifiedOrchestrator instance

        Raises:
            ServiceInitializationError: If required services fail to initialize
        """
        logger.info(
            "Creating unified orchestrator with configuration: "
            f"smart_filter={enable_smart_filter}, variants={enable_variants}, "
            f"embeddings={enable_embeddings}, decision_engine={enable_decision_engine}"
        )

        try:
            # ============================================================
            # Initialize core services (required)
            # ============================================================

            # Validation service - always required
            if validation_service is None:
                try:
                    validation_service = ValidationService()
                    await validation_service.initialize()
                except Exception as e:
                    logger.error(f"Failed to initialize validation service: {e}")
                    raise ServiceInitializationError(f"Validation service: {e}")

            # Language detection service - always required
            if language_service is None:
                try:
                    language_service = LanguageDetectionService()
                except Exception as e:
                    logger.error(f"Failed to initialize language service: {e}")
                    raise ServiceInitializationError(f"Language service: {e}")

            # Unicode service - always required
            if unicode_service is None:
                try:
                    unicode_service = UnicodeService()
                except Exception as e:
                    logger.error(f"Failed to initialize unicode service: {e}")
                    raise ServiceInitializationError(f"Unicode service: {e}")

            # Normalization service - always required, THE CORE
            if normalization_service is None:
                try:
                    normalization_service = NormalizationService()
                except Exception as e:
                    logger.error(f"Failed to initialize normalization service: {e}")
                    raise ServiceInitializationError(f"Normalization service: {e}")

            # Signals service - always required
            if signals_service is None:
                try:
                    signals_service = SignalsService()
                except Exception as e:
                    logger.error(f"Failed to initialize signals service: {e}")
                    raise ServiceInitializationError(f"Signals service: {e}")

            # ============================================================
            # Initialize optional services
            # ============================================================

            # Smart filter service - optional but recommended
            if enable_smart_filter and smart_filter_service is None:
                try:
                    smart_filter_service = SmartFilterAdapter()
                    await smart_filter_service.initialize()
                    logger.info("Smart filter adapter initialized")
                except Exception as e:
                    logger.warning(f"Failed to initialize smart filter adapter: {e}")
                    smart_filter_service = None
                    enable_smart_filter = False

            # Variants service - optional
            if enable_variants and variants_service is None:
                try:
                    from ..layers.variants.variant_generation_service import VariantGenerationService
                    variants_service = VariantGenerationService()
                    await variants_service.initialize()
                    logger.info("Variants service initialized")
                except Exception as e:
                    logger.warning(f"Failed to initialize variants service: {e}")
                    variants_service = None
                    enable_variants = False

            # Embeddings service - optional
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

            # Decision engine - optional
            if enable_decision_engine and decision_engine is None:
                try:
                    # Use unified config with ENV overrides
                    decision_engine = DecisionEngine(DECISION_CONFIG)
                    logger.info("Decision engine initialized with unified config (ENV overrides supported)")
                except Exception as e:
                    logger.warning(f"Failed to initialize decision engine: {e}")
                    decision_engine = None
                    enable_decision_engine = False

            # ============================================================
            # Create orchestrator
            # ============================================================

            orchestrator = UnifiedOrchestrator(
                # Required services
                validation_service=validation_service,
                language_service=language_service,
                unicode_service=unicode_service,
                normalization_service=normalization_service,
                signals_service=signals_service,
                # Optional services
                smart_filter_service=smart_filter_service,
                variants_service=variants_service,
                embeddings_service=embeddings_service,
                decision_engine=decision_engine,
                metrics_service=metrics_service,
                default_feature_flags=FEATURE_FLAGS,
                # Configuration
                enable_smart_filter=enable_smart_filter,
                enable_variants=enable_variants,
                enable_embeddings=enable_embeddings,
                enable_decision_engine=enable_decision_engine,
                allow_smart_filter_skip=allow_smart_filter_skip,
            )

            logger.info("UnifiedOrchestrator created successfully")
            return orchestrator

        except Exception as e:
            logger.error(f"Failed to create orchestrator: {e}", exc_info=True)
            raise ServiceInitializationError(f"Orchestrator creation failed: {e}")

    @staticmethod
    async def create_testing_orchestrator(minimal: bool = False) -> UnifiedOrchestrator:
        """
        Create orchestrator optimized for testing.

        Args:
            minimal: If True, only enable core services (no smart filter, variants, embeddings)

        Returns:
            Testing-optimized orchestrator
        """
        logger.info(f"Creating testing orchestrator (minimal={minimal})")

        return await OrchestratorFactory.create_orchestrator(
            enable_smart_filter=not minimal,
            enable_variants=not minimal,  # Enable variants for full testing
            enable_embeddings=not minimal,  # Enable embeddings for full testing
            allow_smart_filter_skip=False,  # Don't skip processing in tests
        )

    @staticmethod
    async def create_production_orchestrator() -> UnifiedOrchestrator:
        """
        Create orchestrator optimized for production.

        Returns:
            Production-optimized orchestrator
        """
        logger.info("Creating production orchestrator")

        return await OrchestratorFactory.create_orchestrator(
            enable_smart_filter=True,
            enable_variants=True,
            enable_embeddings=True,
            enable_decision_engine=True,    # Enable automated decision making
            allow_smart_filter_skip=False,  # Don't skip processing - always normalize
        )
