"""
Base service class for AI Service
Provides common functionality and patterns for all services
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime

from ..exceptions import AIServiceException
from ..utils import get_logger, LoggingMixin


class BaseService(ABC, LoggingMixin):
    """Base class for all AI services"""
    
    def __init__(self, service_name: str):
        """
        Initialize base service
        
        Args:
            service_name: Name of the service for logging
        """
        self.service_name = service_name
        self.logger = get_logger(f"{self.__module__}.{service_name}")
        self._initialized = False
        self._initialization_time = None
        self._stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'average_processing_time': 0.0,
            'last_request_time': None
        }
    
    def initialize(self) -> None:
        """
        Initialize the service
        
        Raises:
            AIServiceException: If initialization fails
        """
        if self._initialized:
            return
        
        try:
            self._do_initialize()
            self._initialized = True
            self._initialization_time = datetime.now()
            self.logger.info(f"{self.service_name} initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize {self.service_name}: {e}")
            raise AIServiceException(f"Service initialization failed: {str(e)}")
    
    @abstractmethod
    def _do_initialize(self) -> None:
        """Service-specific initialization logic"""
        pass
    
    def is_initialized(self) -> bool:
        """Check if service is initialized"""
        return self._initialized
    
    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics"""
        stats = self._stats.copy()
        stats.update({
            'service_name': self.service_name,
            'initialized': self._initialized,
            'initialization_time': self._initialization_time.isoformat() if self._initialization_time else None
        })
        return stats
    
    def reset_stats(self) -> None:
        """Reset service statistics"""
        self._stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'average_processing_time': 0.0,
            'last_request_time': None
        }
        self.logger.info(f"{self.service_name} statistics reset")
    
    def _update_stats(self, success: bool, processing_time: float) -> None:
        """Update service statistics"""
        self._stats['total_requests'] += 1
        self._stats['last_request_time'] = datetime.now().isoformat()
        
        if success:
            self._stats['successful_requests'] += 1
        else:
            self._stats['failed_requests'] += 1
        
        # Update average processing time
        total_time = self._stats['average_processing_time'] * (self._stats['total_requests'] - 1)
        self._stats['average_processing_time'] = (total_time + processing_time) / self._stats['total_requests']
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        return {
            'service_name': self.service_name,
            'status': 'healthy' if self._initialized else 'unhealthy',
            'initialized': self._initialized,
            'stats': self.get_stats()
        }


class ProcessingService(BaseService):
    """Base class for text processing services"""
    
    def __init__(self, service_name: str):
        super().__init__(service_name)
        self._processing_stats = {
            'total_processed': 0,
            'successful_processed': 0,
            'failed_processed': 0,
            'average_processing_time': 0.0,
            'last_processing_time': None
        }
    
    def process_text(self, text: str, **kwargs) -> Any:
        """
        Process text with error handling and statistics
        
        Args:
            text: Text to process
            **kwargs: Additional processing parameters
            
        Returns:
            Processing result
            
        Raises:
            AIServiceException: If processing fails
        """
        if not self._initialized:
            self.initialize()
        
        start_time = datetime.now()
        
        try:
            result = self._process_text_impl(text, **kwargs)
            processing_time = (datetime.now() - start_time).total_seconds()
            
            self._update_processing_stats(True, processing_time)
            return result
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            self._update_processing_stats(False, processing_time)
            self.logger.error(f"Text processing failed in {self.service_name}: {e}")
            raise AIServiceException(f"Text processing failed: {str(e)}")
    
    @abstractmethod
    def _process_text_impl(self, text: str, **kwargs) -> Any:
        """Service-specific text processing implementation"""
        pass
    
    def _update_processing_stats(self, success: bool, processing_time: float) -> None:
        """Update processing statistics"""
        self._processing_stats['total_processed'] += 1
        self._processing_stats['last_processing_time'] = datetime.now().isoformat()
        
        if success:
            self._processing_stats['successful_processed'] += 1
        else:
            self._processing_stats['failed_processed'] += 1
        
        # Update average processing time
        total_time = self._processing_stats['average_processing_time'] * (self._processing_stats['total_processed'] - 1)
        self._processing_stats['average_processing_time'] = (total_time + processing_time) / self._processing_stats['total_processed']
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        return self._processing_stats.copy()
    
    def reset_processing_stats(self) -> None:
        """Reset processing statistics"""
        self._processing_stats = {
            'total_processed': 0,
            'successful_processed': 0,
            'failed_processed': 0,
            'average_processing_time': 0.0,
            'last_processing_time': None
        }
        self.logger.info(f"{self.service_name} processing statistics reset")
