"""
Test Suite for Authentication Token Manager
Tests token storage, validation, and secure session management
"""

import unittest
import tempfile
import os
import json
import shutil
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auth import (
    AuthTokenManager, get_auth_token, store_auth_token, validate_token,
    is_authenticated, get_user_info
)


class TestAuthTokenManager(unittest.TestCase):
    """Unit tests for AuthTokenManager"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_dir = os.path.join(self.temp_dir, '.signalos')
        self.auth_manager = AuthTokenManager(config_dir=self.config_dir)
        
        # Mock server URL
        self.test_server_url = "http://test-server:5000"
        self.auth_manager.server_url = self.test_server_url
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir)
    
    def test_token_storage_and_retrieval(self):
        """Test storing and retrieving authentication tokens"""
        test_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoxMjMsImV4cCI6MTY0MDk5NTIwMH0.test_signature"
        
        # Store token
        success = self.auth_manager.store_auth_token(test_token)
        self.assertTrue(success)
        
        # Retrieve token
        retrieved_token = self.auth_manager.get_auth_token()
        self.assertEqual(retrieved_token, test_token)
        
        # Check token file exists with correct permissions
        self.assertTrue(self.auth_manager.token_file.exists())
        
        # Check file permissions (should be 600)
        file_mode = oct(os.stat(self.auth_manager.token_file).st_mode)[-3:]
        self.assertEqual(file_mode, '600')
    
    def test_invalid_jwt_format_rejection(self):
        """Test rejection of invalid JWT tokens"""
        invalid_tokens = [
            "invalid_token",
            "not.a.jwt",
            "too.many.parts.here.invalid",
            "",
            None
        ]
        
        for invalid_token in invalid_tokens:
            with self.subTest(token=invalid_token):
                if invalid_token is not None:
                    success = self.auth_manager.store_auth_token(invalid_token)
                    self.assertFalse(success)
    
    @patch('requests.get')
    def test_token_validation_success(self, mock_get):
        """Test successful token validation"""
        test_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoxMjMsImV4cCI6MTY0MDk5NTIwMH0.test_signature"
        
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'username': 'testuser', 'id': 123}
        mock_get.return_value = mock_response
        
        # Store token and validate
        self.auth_manager.store_auth_token(test_token)
        is_valid = self.auth_manager.validate_token(test_token)
        
        self.assertTrue(is_valid)
        mock_get.assert_called_once_with(
            f"{self.test_server_url}/api/me",
            headers={'Authorization': f'Bearer {test_token}'},
            timeout=10
        )
    
    @patch('requests.get')
    def test_token_validation_failure(self, mock_get):
        """Test token validation failure scenarios"""
        test_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoxMjMsImV4cCI6MTY0MDk5NTIwMH0.test_signature"
        
        # Test unauthorized response
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_get.return_value = mock_response
        
        self.auth_manager.store_auth_token(test_token)
        is_valid = self.auth_manager.validate_token(test_token)
        
        self.assertFalse(is_valid)
        
        # Token should be cleared after 401
        token_after_failure = self.auth_manager.get_auth_token()
        self.assertIsNone(token_after_failure)
    
    @patch('requests.get')
    def test_token_validation_network_error(self, mock_get):
        """Test token validation with network errors"""
        import requests
        test_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoxMjMsImV4cCI6MTY0MDk5NTIwMH0.test_signature"
        
        # Mock network error
        mock_get.side_effect = requests.exceptions.RequestException("Network error")
        
        self.auth_manager.store_auth_token(test_token)
        is_valid = self.auth_manager.validate_token(test_token)
        
        self.assertFalse(is_valid)
    
    def test_token_from_config_file(self):
        """Test loading token from config.json file"""
        test_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoxMjMsImV4cCI6MTY0MDk5NTIwMH0.test_signature"
        
        # Create config file with token
        config_data = {
            'auth_token': test_token,
            'server_url': self.test_server_url
        }
        
        with open(self.auth_manager.config_file, 'w') as f:
            json.dump(config_data, f)
        
        # Clear cache and retrieve token
        self.auth_manager._cached_token = None
        retrieved_token = self.auth_manager.get_auth_token()
        
        self.assertEqual(retrieved_token, test_token)
    
    def test_validation_cache(self):
        """Test validation result caching"""
        test_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoxMjMsImV4cCI6MTY0MDk5NTIwMH0.test_signature"
        
        with patch('requests.get') as mock_get:
            # Mock successful API response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'username': 'testuser'}
            mock_get.return_value = mock_response
            
            self.auth_manager.store_auth_token(test_token)
            
            # First validation should make API call
            is_valid1 = self.auth_manager.validate_token(test_token)
            self.assertTrue(is_valid1)
            self.assertEqual(mock_get.call_count, 1)
            
            # Second validation within cache duration should not make API call
            is_valid2 = self.auth_manager.validate_token(test_token)
            self.assertTrue(is_valid2)
            self.assertEqual(mock_get.call_count, 1)  # No additional call
    
    @patch('requests.get')
    def test_get_user_info(self, mock_get):
        """Test getting user information"""
        test_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoxMjMsImV4cCI6MTY0MDk5NTIwMH0.test_signature"
        user_data = {'username': 'testuser', 'id': 123, 'email': 'test@example.com'}
        
        # Mock API responses
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = user_data
        mock_get.return_value = mock_response
        
        self.auth_manager.store_auth_token(test_token)
        retrieved_user_info = self.auth_manager.get_user_info()
        
        self.assertEqual(retrieved_user_info, user_data)
    
    def test_logout_functionality(self):
        """Test logout and token clearing"""
        test_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoxMjMsImV4cCI6MTY0MDk5NTIwMH0.test_signature"
        
        # Store token
        self.auth_manager.store_auth_token(test_token)
        self.assertIsNotNone(self.auth_manager.get_auth_token())
        
        # Logout
        success = self.auth_manager.logout()
        self.assertTrue(success)
        
        # Token should be cleared
        self.assertIsNone(self.auth_manager.get_auth_token())
        self.assertFalse(self.auth_manager.token_file.exists())
    
    @patch('requests.post')
    def test_token_refresh(self, mock_post):
        """Test token refresh functionality"""
        old_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoxMjMsImV4cCI6MTY0MDk5NTIwMH0.old_signature"
        new_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoxMjMsImV4cCI6MTY0MDk5NTIwMH0.new_signature"
        
        # Mock successful refresh response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'token': new_token}
        mock_post.return_value = mock_response
        
        self.auth_manager.store_auth_token(old_token)
        success = self.auth_manager.refresh_token()
        
        self.assertTrue(success)
        self.assertEqual(self.auth_manager.get_auth_token(), new_token)
    
    def test_is_authenticated(self):
        """Test authentication status checking"""
        # Should be false with no token
        self.assertFalse(self.auth_manager.is_authenticated())
        
        with patch.object(self.auth_manager, 'validate_token', return_value=True):
            test_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoxMjMsImV4cCI6MTY0MDk5NTIwMH0.test_signature"
            self.auth_manager.store_auth_token(test_token)
            
            self.assertTrue(self.auth_manager.is_authenticated())
    
    def test_get_token_info(self):
        """Test getting comprehensive token information"""
        test_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoxMjMsImV4cCI6MTY0MDk5NTIwMH0.test_signature"
        
        with patch.object(self.auth_manager, 'validate_token', return_value=True), \
             patch.object(self.auth_manager, 'get_user_info', return_value={'username': 'testuser'}):
            
            self.auth_manager.store_auth_token(test_token)
            token_info = self.auth_manager.get_token_info()
            
            self.assertTrue(token_info['has_token'])
            self.assertTrue(token_info['token_validated'])
            self.assertIsNotNone(token_info['user_info'])
            self.assertEqual(token_info['server_url'], self.test_server_url)


class TestGlobalFunctions(unittest.TestCase):
    """Test global utility functions"""
    
    def setUp(self):
        """Set up test environment"""
        # Clear global instance
        import auth
        auth._auth_manager = None
    
    def test_global_token_operations(self):
        """Test global token storage and retrieval functions"""
        test_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoxMjMsImV4cCI6MTY0MDk5NTIwMH0.test_signature"
        
        # Test storage
        success = store_auth_token(test_token)
        self.assertTrue(success)
        
        # Test retrieval
        retrieved_token = get_auth_token()
        self.assertEqual(retrieved_token, test_token)
    
    @patch('requests.get')
    def test_global_validation(self, mock_get):
        """Test global token validation function"""
        test_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoxMjMsImV4cCI6MTY0MDk5NTIwMH0.test_signature"
        
        # Mock successful validation
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'username': 'testuser'}
        mock_get.return_value = mock_response
        
        store_auth_token(test_token)
        is_valid = validate_token(test_token)
        
        self.assertTrue(is_valid)
    
    @patch('requests.get')
    def test_global_authentication_check(self, mock_get):
        """Test global authentication status function"""
        test_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoxMjMsImV4cCI6MTY0MDk5NTIwMH0.test_signature"
        
        # Mock successful validation
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'username': 'testuser'}
        mock_get.return_value = mock_response
        
        store_auth_token(test_token)
        authenticated = is_authenticated()
        
        self.assertTrue(authenticated)
    
    @patch('requests.get')
    def test_global_user_info(self, mock_get):
        """Test global user info function"""
        test_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoxMjMsImV4cCI6MTY0MDk5NTIwMH0.test_signature"
        user_data = {'username': 'testuser', 'id': 123}
        
        # Mock successful API calls
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = user_data
        mock_get.return_value = mock_response
        
        store_auth_token(test_token)
        user_info = get_user_info()
        
        self.assertEqual(user_info, user_data)


class TestRetryLogic(unittest.TestCase):
    """Test retry and error handling logic"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_dir = os.path.join(self.temp_dir, '.signalos')
        self.auth_manager = AuthTokenManager(config_dir=self.config_dir)
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir)
    
    @patch('requests.get')
    def test_validation_retry_on_network_error(self, mock_get):
        """Test validation retry behavior on network errors"""
        import requests
        test_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoxMjMsImV4cCI6MTY0MDk5NTIwMH0.test_signature"
        
        # First call fails, second succeeds
        mock_get.side_effect = [
            requests.exceptions.RequestException("Network error"),
            Mock(status_code=200, json=lambda: {'username': 'testuser'})
        ]
        
        self.auth_manager.store_auth_token(test_token)
        
        # First validation should fail due to network error
        is_valid_1 = self.auth_manager.validate_token(test_token)
        self.assertFalse(is_valid_1)
        
        # Clear validation cache
        self.auth_manager._token_validated_at = None
        
        # Second validation should succeed
        is_valid_2 = self.auth_manager.validate_token(test_token)
        self.assertTrue(is_valid_2)
    
    def test_fallback_configuration_loading(self):
        """Test fallback behavior when config files are missing"""
        # Remove config directory
        if os.path.exists(self.config_dir):
            shutil.rmtree(self.config_dir)
        
        # Create new auth manager (should handle missing config gracefully)
        auth_manager = AuthTokenManager(config_dir=self.config_dir)
        
        # Should still be able to store and retrieve tokens
        test_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoxMjMsImV4cCI6MTY0MDk5NTIwMH0.test_signature"
        
        success = auth_manager.store_auth_token(test_token)
        self.assertTrue(success)
        
        retrieved_token = auth_manager.get_auth_token()
        self.assertEqual(retrieved_token, test_token)


if __name__ == '__main__':
    unittest.main()