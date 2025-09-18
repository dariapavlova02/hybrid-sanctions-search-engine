"""
Configuration Hot-reloading Support

Provides hot-reloading capabilities for configuration changes
without requiring service restart.
"""

import asyncio
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

from ..utils.logging_config import get_logger

logger = get_logger(__name__)


class ConfigurationWatcher:
    """
    Watches configuration files for changes and triggers reload callbacks.
    
    This class provides a simple file-based configuration hot-reloading
    mechanism that can be extended for more complex scenarios.
    """
    
    def __init__(self, watch_paths: List[Path], check_interval: float = 1.0):
        """
        Initialize configuration watcher.
        
        Args:
            watch_paths: List of file paths to watch for changes
            check_interval: Interval in seconds to check for changes
        """
        self.watch_paths = [Path(p) for p in watch_paths]
        self.check_interval = check_interval
        self.last_modified: Dict[Path, float] = {}
        self.callbacks: List[Callable[[], None]] = []
        self._running = False
        self._task: Optional[asyncio.Task] = None
        
        # Initialize last modified times
        for path in self.watch_paths:
            if path.exists():
                self.last_modified[path] = path.stat().st_mtime
            else:
                logger.warning(f"Configuration file does not exist: {path}")
    
    def add_callback(self, callback: Callable[[], None]) -> None:
        """Add a callback to be called when configuration changes."""
        self.callbacks.append(callback)
    
    def remove_callback(self, callback: Callable[[], None]) -> None:
        """Remove a callback."""
        if callback in self.callbacks:
            self.callbacks.remove(callback)
    
    async def start(self) -> None:
        """Start watching for configuration changes."""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._watch_loop())
        logger.info(f"Started configuration watcher for {len(self.watch_paths)} files")
    
    async def stop(self) -> None:
        """Stop watching for configuration changes."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Stopped configuration watcher")
    
    async def _watch_loop(self) -> None:
        """Main watching loop."""
        while self._running:
            try:
                await self._check_for_changes()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in configuration watcher: {e}")
                await asyncio.sleep(self.check_interval)
    
    async def _check_for_changes(self) -> None:
        """Check for configuration file changes."""
        changed_files = []
        
        for path in self.watch_paths:
            if not path.exists():
                continue
            
            try:
                current_mtime = path.stat().st_mtime
                last_mtime = self.last_modified.get(path, 0)
                
                if current_mtime > last_mtime:
                    self.last_modified[path] = current_mtime
                    changed_files.append(path)
                    logger.info(f"Configuration file changed: {path}")
            
            except OSError as e:
                logger.warning(f"Error checking file {path}: {e}")
        
        if changed_files:
            await self._trigger_callbacks(changed_files)
    
    async def _trigger_callbacks(self, changed_files: List[Path]) -> None:
        """Trigger all registered callbacks."""
        logger.info(f"Triggering configuration reload for {len(changed_files)} changed files")
        
        for callback in self.callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
            except Exception as e:
                logger.error(f"Error in configuration reload callback: {e}")


class HotReloadableConfig:
    """
    Base class for hot-reloadable configuration.
    
    This provides a foundation for configuration classes that need
    to support hot-reloading without service restart.
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize hot-reloadable configuration.
        
        Args:
            config_path: Path to configuration file (optional)
        """
        self.config_path = config_path
        self._watcher: Optional[ConfigurationWatcher] = None
        self._last_reload = datetime.now()
        self._reload_count = 0
    
    async def start_hot_reload(self, watch_paths: List[Path]) -> None:
        """
        Start hot-reloading for this configuration.
        
        Args:
            watch_paths: List of file paths to watch for changes
        """
        if self._watcher:
            await self._watcher.stop()
        
        self._watcher = ConfigurationWatcher(watch_paths)
        self._watcher.add_callback(self._on_config_changed)
        await self._watcher.start()
        
        logger.info(f"Started hot-reload for configuration: {self.__class__.__name__}")
    
    async def stop_hot_reload(self) -> None:
        """Stop hot-reloading for this configuration."""
        if self._watcher:
            await self._watcher.stop()
            self._watcher = None
        
        logger.info(f"Stopped hot-reload for configuration: {self.__class__.__name__}")
    
    def _on_config_changed(self) -> None:
        """Called when configuration changes are detected."""
        self._last_reload = datetime.now()
        self._reload_count += 1
        
        logger.info(f"Configuration reloaded: {self.__class__.__name__} (count: {self._reload_count})")
        
        # Override this method in subclasses to handle specific reload logic
        self._reload_configuration()
    
    def _reload_configuration(self) -> None:
        """
        Reload configuration from source.
        
        Override this method in subclasses to implement specific
        configuration reloading logic.
        """
        pass
    
    def get_reload_stats(self) -> Dict[str, Any]:
        """Get hot-reload statistics."""
        return {
            "last_reload": self._last_reload.isoformat(),
            "reload_count": self._reload_count,
            "watcher_running": self._watcher is not None and self._watcher._running,
        }


class EnvironmentConfigReloader:
    """
    Reloader for environment variable-based configuration.
    
    This provides a way to reload configuration that depends on
    environment variables, though environment variables typically
    require process restart to take effect.
    """
    
    def __init__(self, config_class: type, env_vars: List[str]):
        """
        Initialize environment config reloader.
        
        Args:
            config_class: Configuration class to reload
            env_vars: List of environment variables to monitor
        """
        self.config_class = config_class
        self.env_vars = env_vars
        self._last_values: Dict[str, str] = {}
        self._reload_count = 0
        self._last_reload = datetime.now()
    
    def check_for_changes(self) -> bool:
        """
        Check if environment variables have changed.
        
        Returns:
            True if changes detected, False otherwise
        """
        changed = False
        
        for env_var in self.env_vars:
            current_value = os.getenv(env_var, "")
            last_value = self._last_values.get(env_var, "")
            
            if current_value != last_value:
                self._last_values[env_var] = current_value
                changed = True
                logger.info(f"Environment variable changed: {env_var}")
        
        if changed:
            self._reload_count += 1
            self._last_reload = datetime.now()
            logger.info(f"Environment configuration reloaded (count: {self._reload_count})")
        
        return changed
    
    def get_reload_stats(self) -> Dict[str, Any]:
        """Get reload statistics."""
        return {
            "last_reload": self._last_reload.isoformat(),
            "reload_count": self._reload_count,
            "monitored_vars": self.env_vars,
            "current_values": {var: os.getenv(var, "") for var in self.env_vars},
        }
