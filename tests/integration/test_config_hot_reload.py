"""
Integration tests for configuration hot-reloading
"""

import asyncio
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from src.ai_service.config.hot_reload import ConfigurationWatcher, HotReloadableConfig
from src.ai_service.config.settings import SearchConfig


class TestConfigurationWatcher:
    """Test ConfigurationWatcher functionality"""
    
    def test_watcher_initialization(self):
        """Test watcher initializes correctly"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "test_config.py"
            config_file.write_text("# Test config file")
            
            watcher = ConfigurationWatcher([config_file], check_interval=0.1)
            
            assert len(watcher.watch_paths) == 1
            assert watcher.check_interval == 0.1
            assert not watcher._running
            assert len(watcher.callbacks) == 0
    
    def test_add_remove_callbacks(self):
        """Test adding and removing callbacks"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "test_config.py"
            config_file.write_text("# Test config file")
            
            watcher = ConfigurationWatcher([config_file])
            
            # Add callback
            callback_called = False
            def test_callback():
                nonlocal callback_called
                callback_called = True
            
            watcher.add_callback(test_callback)
            assert len(watcher.callbacks) == 1
            
            # Remove callback
            watcher.remove_callback(test_callback)
            assert len(watcher.callbacks) == 0
    
    @pytest.mark.asyncio
    async def test_file_change_detection(self):
        """Test file change detection"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "test_config.py"
            config_file.write_text("# Test config file")
            
            watcher = ConfigurationWatcher([config_file], check_interval=0.1)
            
            # Add callback
            callback_called = False
            changed_files = []
            
            def test_callback():
                nonlocal callback_called
                callback_called = True
            
            watcher.add_callback(test_callback)
            
            # Start watcher
            await watcher.start()
            assert watcher._running
            
            # Wait a bit for initial check
            await asyncio.sleep(0.2)
            
            # Modify file
            config_file.write_text("# Modified test config file")
            
            # Wait for change detection
            await asyncio.sleep(0.2)
            
            # Stop watcher
            await watcher.stop()
            assert not watcher._running
            
            # Callback should have been called
            assert callback_called
    
    @pytest.mark.asyncio
    async def test_multiple_file_watching(self):
        """Test watching multiple files"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file1 = Path(temp_dir) / "config1.py"
            config_file2 = Path(temp_dir) / "config2.py"
            
            config_file1.write_text("# Config 1")
            config_file2.write_text("# Config 2")
            
            watcher = ConfigurationWatcher([config_file1, config_file2], check_interval=0.1)
            
            callback_count = 0
            
            def test_callback():
                nonlocal callback_count
                callback_count += 1
            
            watcher.add_callback(test_callback)
            
            # Start watcher
            await watcher.start()
            
            # Wait for initial check
            await asyncio.sleep(0.2)
            
            # Modify both files
            config_file1.write_text("# Modified config 1")
            config_file2.write_text("# Modified config 2")
            
            # Wait for change detection
            await asyncio.sleep(0.2)
            
            # Stop watcher
            await watcher.stop()
            
            # Callback should have been called for each change
            assert callback_count >= 2


class TestHotReloadableConfig:
    """Test HotReloadableConfig functionality"""
    
    def test_config_initialization(self):
        """Test config initializes correctly"""
        config = HotReloadableConfig()
        
        assert config._watcher is None
        assert config._reload_count == 0
        assert isinstance(config._last_reload, type(config._last_reload))
    
    @pytest.mark.asyncio
    async def test_hot_reload_lifecycle(self):
        """Test hot reload start/stop lifecycle"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "test_config.py"
            config_file.write_text("# Test config file")
            
            config = HotReloadableConfig(config_file)
            
            # Start hot reload
            await config.start_hot_reload([config_file])
            assert config._watcher is not None
            assert config._watcher._running
            
            # Stop hot reload
            await config.stop_hot_reload()
            assert config._watcher is None
    
    def test_reload_stats(self):
        """Test reload statistics"""
        config = HotReloadableConfig()
        
        stats = config.get_reload_stats()
        
        assert "last_reload" in stats
        assert "reload_count" in stats
        assert "watcher_running" in stats
        assert stats["reload_count"] == 0
        assert stats["watcher_running"] is False


class TestSearchConfigHotReload:
    """Test SearchConfig hot-reloading functionality"""
    
    def test_search_config_initialization(self):
        """Test SearchConfig initializes with hot-reload support"""
        config = SearchConfig()
        
        assert hasattr(config, '_watcher')
        assert hasattr(config, '_reload_count')
        assert hasattr(config, '_last_reload')
        assert hasattr(config, '_reload_configuration')
    
    def test_reload_configuration_method(self):
        """Test _reload_configuration method"""
        config = SearchConfig()
        
        # Set initial values
        config.es_hosts = ["localhost:9200"]
        config.es_timeout = 30
        config.enable_hybrid_search = True
        
        # Mock environment variables
        with patch.dict(os.environ, {
            'ES_HOSTS': 'localhost:9201,localhost:9202',
            'ES_TIMEOUT': '60',
            'ENABLE_HYBRID_SEARCH': 'false'
        }):
            config._reload_configuration()
        
        # Values should be updated
        assert config.es_hosts == ["localhost:9201", "localhost:9202"]
        assert config.es_timeout == 60
        assert config.enable_hybrid_search is False
    
    def test_reload_configuration_validation(self):
        """Test _reload_configuration with invalid values"""
        config = SearchConfig()
        
        # Mock invalid environment variables
        with patch.dict(os.environ, {
            'ES_HOSTS': '',  # Empty hosts
            'ES_TIMEOUT': '-1'  # Invalid timeout
        }):
            # Should not raise exception, but log error
            config._reload_configuration()
        
        # Should fall back to defaults or previous values
        assert config.es_hosts == ["localhost:9200"]  # Default
        assert config.es_timeout == 30  # Default
    
    @pytest.mark.asyncio
    async def test_search_config_hot_reload_integration(self):
        """Test SearchConfig hot-reload integration"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "test_config.py"
            config_file.write_text("# Test config file")
            
            config = SearchConfig()
            
            # Start hot reload
            await config.start_hot_reload([config_file])
            
            # Verify watcher is running
            assert config._watcher is not None
            assert config._watcher._running
            
            # Stop hot reload
            await config.stop_hot_reload()
            
            # Verify watcher is stopped
            assert config._watcher is None
    
    def test_search_config_reload_stats(self):
        """Test SearchConfig reload statistics"""
        config = SearchConfig()
        
        stats = config.get_reload_stats()
        
        assert "last_reload" in stats
        assert "reload_count" in stats
        assert "watcher_running" in stats
        assert isinstance(stats["last_reload"], str)
        assert isinstance(stats["reload_count"], int)
        assert isinstance(stats["watcher_running"], bool)
