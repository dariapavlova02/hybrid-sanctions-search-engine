#!/usr/bin/env python3
"""
Basic warmup script for AI normalization service.

This script tests only the core functionality without complex dependencies.
"""

import argparse
import os
import sys
import time
from typing import List, Dict, Any

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from ai_service.layers.normalization.normalization_service import NormalizationService
from ai_service.utils import get_logger

logger = get_logger(__name__)

# Basic test data
BASIC_TEST_DATA = [
    "John Smith",
    "Mary Johnson", 
    "Robert Brown",
    "Jennifer Davis",
    "Michael Wilson"
]

class BasicWarmupService:
    """Basic service for warming up the normalization service."""
    
    def __init__(self):
        self.service = None
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_time": 0.0
        }
    
    def initialize_service(self) -> None:
        """Initialize the normalization service."""
        try:
            logger.info("Initializing normalization service...")
            self.service = NormalizationService()
            logger.info("✓ Service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize service: {e}")
            raise
    
    def warmup_single_text(self, text: str, language: str = "en") -> Dict[str, Any]:
        """Warmup a single text."""
        start_time = time.time()
        
        try:
            result = self.service.normalize(text, language=language)
            end_time = time.time()
            
            self.stats["total_requests"] += 1
            self.stats["successful_requests"] += 1
            self.stats["total_time"] += (end_time - start_time)
            
            return {
                "text": text,
                "language": language,
                "success": result.success,
                "normalized": result.normalized_text,
                "tokens": len(result.tokens),
                "processing_time": end_time - start_time
            }
            
        except Exception as e:
            end_time = time.time()
            self.stats["total_requests"] += 1
            self.stats["failed_requests"] += 1
            self.stats["total_time"] += (end_time - start_time)
            
            logger.warning(f"Failed to normalize '{text}': {e}")
            return {
                "text": text,
                "language": language,
                "success": False,
                "error": str(e),
                "processing_time": end_time - start_time
            }
    
    def run_warmup(self, n: int = 200) -> None:
        """Run the complete warmup process."""
        logger.info(f"Starting basic warmup with {n} requests...")
        
        # Initialize service
        self.initialize_service()
        
        # Prepare test data
        test_data = []
        while len(test_data) < n:
            test_data.extend(BASIC_TEST_DATA)
        
        # Take first n texts
        selected_texts = test_data[:n]
        
        # Warmup with English only to avoid morphology issues
        results = []
        
        for i, text in enumerate(selected_texts):
            if i % 20 == 0:
                logger.info(f"Processing text {i+1}/{n}: {text[:30]}...")
            
            result = self.warmup_single_text(text, "en")
            results.append(result)
        
        # Print statistics
        self.print_statistics()
    
    def print_statistics(self) -> None:
        """Print warmup statistics."""
        logger.info("=== Warmup Statistics ===")
        logger.info(f"Total requests: {self.stats['total_requests']}")
        logger.info(f"Successful requests: {self.stats['successful_requests']}")
        logger.info(f"Failed requests: {self.stats['failed_requests']}")
        logger.info(f"Success rate: {self.stats['successful_requests']/self.stats['total_requests']*100:.1f}%")
        logger.info(f"Total time: {self.stats['total_time']:.2f}s")
        logger.info(f"Average time per request: {self.stats['total_time']/self.stats['total_requests']*1000:.1f}ms")

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Basic warmup for AI normalization service")
    parser.add_argument("--n", type=int, default=200, help="Number of warmup requests")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    # Set up logging
    if args.verbose:
        import logging
        logging.basicConfig(level=logging.INFO)
    
    # Create and run warmup service
    warmup_service = BasicWarmupService()
    warmup_service.run_warmup(args.n)
    
    logger.info("✓ Basic warmup completed successfully!")

if __name__ == "__main__":
    main()
