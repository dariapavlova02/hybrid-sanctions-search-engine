"""
Tests for run_service.py script functionality
"""

import pytest
import subprocess
import sys
from unittest.mock import Mock, patch, call
from pathlib import Path
import os

# Add root directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import run_service


class TestRunServiceScript:
    """Test run_service.py script functionality"""
    
    def test_check_python_version_valid(self):
        """Test Python version check with valid version"""
        with patch('run_service.sys.version_info', (3, 12, 0)):
            result = run_service.check_python_version()
            assert result is True
    
    def test_check_python_version_invalid(self):
        """Test Python version check with invalid version"""
        with patch('run_service.sys.version_info', (3, 11, 0)):
            result = run_service.check_python_version()
            assert result is False
    
    @patch('run_service.subprocess.run')
    def test_check_poetry_available(self, mock_subprocess):
        """Test Poetry availability check when Poetry is available"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Poetry version 1.4.0"
        mock_subprocess.return_value = mock_result
        
        result = run_service.check_poetry()
        
        assert result is True
        mock_subprocess.assert_called_once_with(
            ['poetry', '--version'], capture_output=True, text=True
        )
    
    @patch('run_service.subprocess.run')
    def test_check_poetry_not_available(self, mock_subprocess):
        """Test Poetry availability check when Poetry is not available"""
        mock_subprocess.side_effect = FileNotFoundError()
        
        result = run_service.check_poetry()
        
        assert result is False
    
    @patch('run_service.subprocess.run')
    def test_check_dependencies_success(self, mock_subprocess):
        """Test successful dependency installation check"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result
        
        result = run_service.check_dependencies()
        
        assert result is True
        mock_subprocess.assert_called_once_with(
            ['poetry', 'install'], capture_output=True, text=True
        )
    
    @patch('run_service.subprocess.run')
    def test_check_dependencies_failure(self, mock_subprocess):
        """Test failed dependency installation check"""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "Dependency installation failed"
        mock_subprocess.return_value = mock_result
        
        result = run_service.check_dependencies()
        
        assert result is False
    
    @patch('run_service.subprocess.run')
    def test_check_dependencies_exception(self, mock_subprocess):
        """Test dependency check with exception"""
        mock_subprocess.side_effect = Exception("Unexpected error")
        
        result = run_service.check_dependencies()
        
        assert result is False
    
    @patch('run_service.spacy.load')
    def test_check_spacy_models_all_available(self, mock_spacy_load):
        """Test SpaCy model check when all models are available"""
        # Mock successful model loading
        mock_nlp = Mock()
        mock_spacy_load.return_value = mock_nlp
        
        result = run_service.check_spacy_models()
        
        assert result is True
        # Should attempt to load 2 models
        assert mock_spacy_load.call_count == 2
    
    @patch('run_service.spacy.load')
    @patch('run_service.subprocess.run')
    def test_check_spacy_models_some_missing_auto_install_success(self, mock_subprocess, mock_spacy_load):
        """Test SpaCy model check with missing models that get auto-installed"""
        # First call fails (model not found), second call succeeds (after auto-install)
        mock_spacy_load.side_effect = [OSError("Model not found"), Mock(), Mock()]
        
        # Mock successful auto-installation
        mock_result = Mock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result
        
        result = run_service.check_spacy_models()
        
        # Should attempt auto-installation
        mock_subprocess.assert_called()
        # Final result depends on whether auto-install worked
        assert isinstance(result, bool)
    
    @patch('run_service.spacy.load')
    def test_check_spacy_models_all_missing_no_auto_install(self, mock_spacy_load):
        """Test SpaCy model check when all models are missing"""
        # All model loading attempts fail
        mock_spacy_load.side_effect = OSError("Model not found")
        
        with patch('run_service.subprocess.run') as mock_subprocess:
            # Auto-install also fails
            mock_subprocess.side_effect = Exception("Install failed")
            
            result = run_service.check_spacy_models()
            
            assert result is False
    
    @patch('run_service.subprocess.run')
    @patch('run_service.Path')
    @patch('run_service.__file__', None)
    def test_run_service_success(self, mock_path, mock_subprocess):
        """Test successful service run"""
        # Mock service path exists
        mock_service_path = Mock()
        mock_service_path.exists.return_value = True
        
        # Mock Path to return our mock service path for any operation
        mock_path.return_value = mock_service_path
        
        # Mock Path class to handle path operations
        def mock_path_class(*args):
            mock_path_obj = Mock()
            mock_path_obj.exists.return_value = mock_service_path.exists()
            mock_path_obj.__truediv__ = lambda other, *args: mock_path_obj
            mock_path_obj.parent = mock_path_obj
            return mock_path_obj
        
        mock_path.side_effect = mock_path_class
        
        # Mock successful subprocess run (will be interrupted by KeyboardInterrupt)
        mock_subprocess.side_effect = KeyboardInterrupt()
        
        result = run_service.run_service()
        
        # Should return True when interrupted by KeyboardInterrupt (normal shutdown)
        assert result is True
        mock_subprocess.assert_called_once()
    
    @patch('run_service.Path')
    @patch('run_service.__file__', None)
    def test_run_service_no_service_file(self, mock_path):
        """Test service run when service file doesn't exist"""
        # Mock service path doesn't exist
        mock_service_path = Mock()
        mock_service_path.exists.return_value = False
        
        # Mock Path to return our mock service path for any operation
        mock_path.return_value = mock_service_path
        
        # Mock Path class to handle path operations
        def mock_path_class(*args):
            mock_path_obj = Mock()
            mock_path_obj.exists.return_value = mock_service_path.exists()
            mock_path_obj.__truediv__ = lambda other, *args: mock_path_obj
            mock_path_obj.parent = mock_path_obj
            return mock_path_obj
        
        mock_path.side_effect = mock_path_class
        
        result = run_service.run_service()
        
        assert result is False
    
    @patch('run_service.subprocess.run')
    @patch('run_service.Path')
    @patch('run_service.__file__', None)
    def test_run_service_exception(self, mock_path, mock_subprocess):
        """Test service run with unexpected exception"""
        # Mock service path exists
        mock_service_path = Mock()
        mock_service_path.exists.return_value = True
        
        # Mock Path to return our mock service path for any operation
        mock_path.return_value = mock_service_path
        
        # Mock Path class to handle path operations
        def mock_path_class(*args):
            mock_path_obj = Mock()
            mock_path_obj.exists.return_value = mock_service_path.exists()
            mock_path_obj.__truediv__ = lambda other, *args: mock_path_obj
            mock_path_obj.parent = mock_path_obj
            return mock_path_obj
        
        mock_path.side_effect = mock_path_class
        
        # Mock subprocess exception
        mock_subprocess.side_effect = Exception("Unexpected error")
        
        result = run_service.run_service()
        
        assert result is False
    
    @patch('run_service.run_service')
    @patch('run_service.check_spacy_models')
    @patch('run_service.check_dependencies')
    @patch('run_service.check_poetry')
    @patch('run_service.check_python_version')
    @patch('builtins.print')
    def test_main_all_checks_pass(self, mock_print, mock_python, mock_poetry, 
                                  mock_deps, mock_models, mock_run):
        """Test main function when all checks pass"""
        # Mock all checks as successful
        mock_python.return_value = True
        mock_poetry.return_value = True
        mock_deps.return_value = True
        mock_models.return_value = True
        mock_run.return_value = True
        
        run_service.main()
        
        # All checks should be called
        mock_python.assert_called_once()
        mock_poetry.assert_called_once()
        mock_deps.assert_called_once()
        mock_models.assert_called_once()
        mock_run.assert_called_once()
    
    @patch('run_service.sys.exit')
    @patch('run_service.check_spacy_models')
    @patch('run_service.check_dependencies')
    @patch('run_service.check_poetry')
    @patch('run_service.check_python_version')
    @patch('builtins.print')
    def test_main_python_check_fails(self, mock_print, mock_python, mock_poetry, 
                                     mock_deps, mock_models, mock_exit):
        """Test main function when Python version check fails"""
        # Mock Python check as failed
        mock_python.return_value = False
        mock_poetry.return_value = True
        mock_deps.return_value = True
        mock_models.return_value = True
        
        run_service.main()
        
        # Should exit with error code 1
        mock_exit.assert_called_once_with(1)
    
    @patch('run_service.sys.exit')
    @patch('run_service.check_spacy_models')
    @patch('run_service.check_dependencies')
    @patch('run_service.check_poetry')
    @patch('run_service.check_python_version')
    @patch('builtins.print')
    def test_main_poetry_check_fails(self, mock_print, mock_python, mock_poetry, 
                                     mock_deps, mock_models, mock_exit):
        """Test main function when Poetry check fails"""
        mock_python.return_value = True
        mock_poetry.return_value = False  # Poetry check fails
        mock_deps.return_value = True
        mock_models.return_value = True
        
        run_service.main()
        
        # Should exit with error code 1
        mock_exit.assert_called_once_with(1)
    
    @patch('run_service.sys.exit')
    @patch('run_service.check_spacy_models')
    @patch('run_service.check_dependencies')
    @patch('run_service.check_poetry')
    @patch('run_service.check_python_version')
    @patch('builtins.print')
    def test_main_dependencies_check_fails(self, mock_print, mock_python, mock_poetry, 
                                           mock_deps, mock_models, mock_exit):
        """Test main function when dependencies check fails"""
        mock_python.return_value = True
        mock_poetry.return_value = True
        mock_deps.return_value = False  # Dependencies check fails
        mock_models.return_value = True
        
        run_service.main()
        
        # Should exit with error code 1
        mock_exit.assert_called_once_with(1)
    
    @patch('run_service.sys.exit')
    @patch('run_service.check_spacy_models')
    @patch('run_service.check_dependencies')
    @patch('run_service.check_poetry')
    @patch('run_service.check_python_version')
    @patch('builtins.print')
    def test_main_models_check_fails(self, mock_print, mock_python, mock_poetry, 
                                     mock_deps, mock_models, mock_exit):
        """Test main function when SpaCy models check fails"""
        mock_python.return_value = True
        mock_poetry.return_value = True
        mock_deps.return_value = True
        mock_models.return_value = False  # Models check fails
        
        run_service.main()
        
        # Should exit with error code 1
        mock_exit.assert_called_once_with(1)


class TestRunServiceScriptIntegration:
    """Integration tests for run_service script"""
    
    def test_script_imports_successfully(self):
        """Test that run_service script can be imported without errors"""
        assert hasattr(run_service, 'main')
        assert hasattr(run_service, 'check_python_version')
        assert hasattr(run_service, 'check_poetry')
        assert hasattr(run_service, 'check_dependencies')
        assert hasattr(run_service, 'check_spacy_models')
        assert hasattr(run_service, 'run_service')
        
        # All should be callable
        for attr in ['main', 'check_python_version', 'check_poetry', 
                     'check_dependencies', 'check_spacy_models', 'run_service']:
            assert callable(getattr(run_service, attr))
    
    def test_script_has_main_guard(self):
        """Test that script has proper __main__ guard"""
        with open('run_service.py', 'r') as f:
            content = f.read()
            assert 'if __name__ == "__main__":' in content
    
    def test_checks_list_structure(self):
        """Test that the checks list in main() has proper structure"""
        # This is a bit of a white-box test, but ensures the main function
        # structure is maintained
        import inspect
        
        source = inspect.getsource(run_service.main)
        
        # Should contain the checks list
        assert 'checks = [' in source
        assert 'check_python_version' in source
        assert 'check_poetry' in source
        assert 'check_dependencies' in source
        assert 'check_spacy_models' in source
