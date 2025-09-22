"""
Orchestrator factory with search integration - stub implementation.
"""

from .orchestrator_factory import OrchestratorFactory


class OrchestratorFactoryWithSearch(OrchestratorFactory):
    """Orchestrator factory with search capabilities."""

    def __init__(self, *args, **kwargs):
        """Initialize with search capabilities."""
        super().__init__(*args, **kwargs)
        self.search_enabled = True

    def create_with_search(self, *args, **kwargs):
        """Create orchestrator with search integration."""
        # Fallback to regular orchestrator for now
        return self.create(*args, **kwargs)