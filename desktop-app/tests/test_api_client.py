"""
Test Suite for API Client
Tests authenticated requests, retry logic, and error handling
"""

import unittest
import json
from unittest.mock import Mock, patch, MagicMock
import requests

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api_client import (
    APIClient, APIException, get_api_client, register_terminal, 
    get_terminal_config, report_status, validate_terminal_auth
)


class TestAPIClient(unittest.TestCase):
    """Unit tests for APIClient"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_server_url = "http://test-server:5000"
        self.api_client = APIClient(server_url=self.test_server_url)
        
        # Mock auth and terminal identity functions
        self.mock_token = "test_jwt_token"
        self.mock_terminal_id = "test-terminal-123"
    
    @patch('api_client.get_auth_token')
    def test_auth_headers_generation(self, mock_get_token):
        """Test authentication headers generation"""
        mock_get_token.return_value = self.mock_token
        
        headers = self.api_client._get_auth_headers()
        
        expected_headers = {'Authorization': f'Bearer {self.mock_token}'}
        self.assertEqual(headers, expected_headers)
    
    @patch('api_client.get_auth_token')
    def test_auth_headers_no_token(self, mock_get_token):
        """Test authentication headers when no token available"""
        mock_get_token.return_value = None
        
        with self.assertRaises(ValueError):
            self.api_client._get_auth_headers()
    
    @patch('requests.Session.request')
    @patch('api_client.get_auth_token')
    def test_successful_get_request(self, mock_get_token, mock_request):
        """Test successful GET request"""
        mock_get_token.return_value = self.mock_token
        
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'status': 'success', 'data': 'test'}
        mock_response.content = b'{"status": "success"}'
        mock_request.return_value = mock_response
        
        result = self.api_client._make_request('GET', '/api/test')
        
        self.assertEqual(result, {'status': 'success', 'data': 'test'})
        mock_request.assert_called_once()
    
    @patch('requests.Session.request')
    @patch('api_client.get_auth_token')
    def test_successful_post_request(self, mock_get_token, mock_request):
        """Test successful POST request with data"""
        mock_get_token.return_value = self.mock_token
        
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'created': True}
        mock_response.content = b'{"created": true}'
        mock_request.return_value = mock_response
        
        test_data = {'name': 'test', 'value': 123}
        result = self.api_client._make_request('POST', '/api/create', data=test_data)
        
        self.assertEqual(result, {'created': True})
        
        # Verify request was made with correct parameters
        call_args = mock_request.call_args
        self.assertEqual(call_args[1]['method'], 'POST')
        self.assertEqual(call_args[1]['json'], test_data)
        self.assertIn('Content-Type', call_args[1]['headers'])
    
    @patch('requests.Session.request')
    @patch('api_client.get_auth_token')
    def test_unauthorized_response(self, mock_get_token, mock_request):
        """Test handling of 401 Unauthorized response"""
        mock_get_token.return_value = self.mock_token
        
        # Mock 401 response
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_request.return_value = mock_response
        
        with self.assertRaises(APIException) as context:
            self.api_client._make_request('GET', '/api/protected')
        
        self.assertEqual(context.exception.status_code, 401)
        self.assertIn("Unauthorized", str(context.exception))
    
    @patch('requests.Session.request')
    @patch('api_client.get_auth_token')
    def test_forbidden_response(self, mock_get_token, mock_request):
        """Test handling of 403 Forbidden response"""
        mock_get_token.return_value = self.mock_token
        
        # Mock 403 response
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"
        mock_request.return_value = mock_response
        
        with self.assertRaises(APIException) as context:
            self.api_client._make_request('GET', '/api/forbidden')
        
        self.assertEqual(context.exception.status_code, 403)
        self.assertIn("Forbidden", str(context.exception))
    
    @patch('requests.Session.request')
    @patch('api_client.get_auth_token')
    def test_not_found_response(self, mock_get_token, mock_request):
        """Test handling of 404 Not Found response"""
        mock_get_token.return_value = self.mock_token
        
        # Mock 404 response
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_request.return_value = mock_response
        
        with self.assertRaises(APIException) as context:
            self.api_client._make_request('GET', '/api/nonexistent')
        
        self.assertEqual(context.exception.status_code, 404)
        self.assertIn("Not found", str(context.exception))
    
    @patch('requests.Session.request')
    @patch('api_client.get_auth_token')
    def test_network_error_handling(self, mock_get_token, mock_request):
        """Test handling of network errors"""
        mock_get_token.return_value = self.mock_token
        
        # Mock network error
        mock_request.side_effect = requests.exceptions.RequestException("Connection error")
        
        with self.assertRaises(APIException) as context:
            self.api_client._make_request('GET', '/api/test')
        
        self.assertIn("Network error", str(context.exception))
    
    @patch('api_client.get_terminal_metadata')
    @patch('api_client.get_auth_token')
    @patch('requests.Session.request')
    def test_register_terminal(self, mock_request, mock_get_token, mock_get_metadata):
        """Test terminal registration"""
        mock_get_token.return_value = self.mock_token
        mock_get_metadata.return_value = {
            'terminal_id': self.mock_terminal_id,
            'os': 'Linux-5.4.0',
            'version': '1.0.6',
            'hostname': 'test-host',
            'architecture': 'x86_64',
            'python_version': '3.9.7',
            'memory_gb': 8,
            'app_name': 'SignalOS Desktop'
        }
        
        # Mock successful registration response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'status': 'approved',
            'approved': True,
            'config_overrides': {'sync_interval': 30}
        }
        mock_response.content = b'{"status": "approved"}'
        mock_request.return_value = mock_response
        
        result = self.api_client.register_terminal()
        
        self.assertTrue(result['approved'])
        self.assertEqual(result['status'], 'approved')
        
        # Verify request payload
        call_args = mock_request.call_args
        payload = call_args[1]['json']
        self.assertEqual(payload['terminal_id'], self.mock_terminal_id)
        self.assertEqual(payload['token'], self.mock_token)
    
    @patch('api_client.get_terminal_id')
    @patch('api_client.get_auth_token')
    @patch('requests.Session.request')
    def test_get_terminal_config(self, mock_request, mock_get_token, mock_get_terminal_id):
        """Test getting terminal configuration"""
        mock_get_token.return_value = self.mock_token
        mock_get_terminal_id.return_value = self.mock_terminal_id
        
        # Mock successful config response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'approved': True,
            'config': {'sync_interval': 60, 'max_trades': 10}
        }
        mock_response.content = b'{"approved": true}'
        mock_request.return_value = mock_response
        
        result = self.api_client.get_terminal_config()
        
        self.assertTrue(result['approved'])
        self.assertIn('config', result)
        
        # Verify request URL
        call_args = mock_request.call_args
        self.assertIn(f'terminal_id={self.mock_terminal_id}', call_args[1]['url'])
    
    @patch('api_client.get_terminal_id')
    @patch('api_client.get_auth_token')
    @patch('requests.Session.request')
    def test_report_status(self, mock_request, mock_get_token, mock_get_terminal_id):
        """Test status reporting"""
        mock_get_token.return_value = self.mock_token
        mock_get_terminal_id.return_value = self.mock_terminal_id
        
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'received': True}
        mock_response.content = b'{"received": true}'
        mock_request.return_value = mock_response
        
        status_data = {
            'mt5_connected': True,
            'active_trades': 5,
            'last_signal_time': '2023-01-01T12:00:00'
        }
        
        result = self.api_client.report_status(status_data)
        
        self.assertTrue(result['received'])
        
        # Verify payload includes terminal_id and timestamp
        call_args = mock_request.call_args
        payload = call_args[1]['json']
        self.assertEqual(payload['terminal_id'], self.mock_terminal_id)
        self.assertIn('timestamp', payload)
        self.assertEqual(payload['mt5_connected'], True)
    
    @patch('api_client.validate_token')
    @patch('requests.Session.request')
    def test_validate_terminal_auth_success(self, mock_request, mock_validate_token):
        """Test successful terminal authentication validation"""
        mock_validate_token.return_value = True
        
        # Mock successful config response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'approved': True}
        mock_response.content = b'{"approved": true}'
        mock_request.return_value = mock_response
        
        result = self.api_client.validate_terminal_auth()
        
        self.assertTrue(result)
    
    @patch('api_client.validate_token')
    def test_validate_terminal_auth_token_failure(self, mock_validate_token):
        """Test terminal auth validation when token is invalid"""
        mock_validate_token.return_value = False
        
        result = self.api_client.validate_terminal_auth()
        
        self.assertFalse(result)
    
    @patch('api_client.validate_token')
    @patch('requests.Session.request')
    def test_validate_terminal_auth_not_approved(self, mock_request, mock_validate_token):
        """Test terminal auth validation when terminal not approved"""
        mock_validate_token.return_value = True
        
        # Mock response with approved=False
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'approved': False}
        mock_response.content = b'{"approved": false}'
        mock_request.return_value = mock_response
        
        result = self.api_client.validate_terminal_auth()
        
        self.assertFalse(result)
    
    @patch('requests.Session.request')
    def test_unauthenticated_request(self, mock_request):
        """Test making unauthenticated requests"""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'server_time': '2023-01-01T12:00:00Z'}
        mock_response.content = b'{"server_time": "2023-01-01T12:00:00Z"}'
        mock_request.return_value = mock_response
        
        result = self.api_client._make_request('GET', '/api/time', authenticated=False)
        
        self.assertIn('server_time', result)
        
        # Verify no Authorization header was sent
        call_args = mock_request.call_args
        headers = call_args[1]['headers']
        self.assertNotIn('Authorization', headers)
    
    def test_api_statistics_tracking(self):
        """Test API request statistics tracking"""
        # Initial stats should be zero
        stats = self.api_client.get_api_statistics()
        self.assertEqual(stats['total_requests'], 0)
        self.assertEqual(stats['successful_requests'], 0)
        self.assertEqual(stats['failed_requests'], 0)
        
        with patch('requests.Session.request') as mock_request, \
             patch('api_client.get_auth_token', return_value=self.mock_token):
            
            # Mock successful request
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {}
            mock_response.content = b'{}'
            mock_request.return_value = mock_response
            
            self.api_client._make_request('GET', '/api/test')
            
            # Stats should be updated
            stats = self.api_client.get_api_statistics()
            self.assertEqual(stats['total_requests'], 1)
            self.assertEqual(stats['successful_requests'], 1)
            self.assertEqual(stats['success_rate'], 1.0)
    
    def test_test_connection(self):
        """Test connection testing functionality"""
        with patch('requests.Session.request') as mock_request:
            # Mock successful health check
            mock_response = Mock()
            mock_response.status_code = 200
            mock_request.return_value = mock_response
            
            result = self.api_client.test_connection()
            self.assertTrue(result)
            
            # Mock failed health check
            mock_request.side_effect = requests.exceptions.RequestException("Connection failed")
            
            result = self.api_client.test_connection()
            self.assertFalse(result)
    
    def test_statistics_reset(self):
        """Test resetting API statistics"""
        # Manually set some stats
        self.api_client.stats['total_requests'] = 10
        self.api_client.stats['successful_requests'] = 8
        
        # Reset stats
        self.api_client.reset_statistics()
        
        # Should be back to zero
        stats = self.api_client.get_api_statistics()
        self.assertEqual(stats['total_requests'], 0)
        self.assertEqual(stats['successful_requests'], 0)


class TestGlobalFunctions(unittest.TestCase):
    """Test global utility functions"""
    
    def setUp(self):
        """Set up test environment"""
        # Clear global instance
        import api_client
        api_client._api_client = None
    
    def test_get_api_client(self):
        """Test global get_api_client function"""
        client = get_api_client()
        self.assertIsInstance(client, APIClient)
        
        # Second call should return same instance
        client2 = get_api_client()
        self.assertIs(client, client2)
    
    @patch('api_client.get_terminal_metadata')
    @patch('api_client.get_auth_token')
    @patch('requests.Session.request')
    def test_global_register_terminal(self, mock_request, mock_get_token, mock_get_metadata):
        """Test global register_terminal function"""
        mock_get_token.return_value = "test_token"
        mock_get_metadata.return_value = {
            'terminal_id': 'test-terminal',
            'os': 'Linux',
            'version': '1.0.6',
            'hostname': 'test-host',
            'architecture': 'x86_64',
            'python_version': '3.9.7',
            'memory_gb': 8,
            'app_name': 'SignalOS Desktop'
        }
        
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'approved': True}
        mock_response.content = b'{"approved": true}'
        mock_request.return_value = mock_response
        
        result = register_terminal()
        self.assertTrue(result['approved'])
    
    @patch('api_client.get_terminal_id')
    @patch('api_client.get_auth_token')
    @patch('requests.Session.request')
    def test_global_get_terminal_config(self, mock_request, mock_get_token, mock_get_terminal_id):
        """Test global get_terminal_config function"""
        mock_get_token.return_value = "test_token"
        mock_get_terminal_id.return_value = "test-terminal"
        
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'config': {'setting': 'value'}}
        mock_response.content = b'{"config": {"setting": "value"}}'
        mock_request.return_value = mock_response
        
        result = get_terminal_config()
        self.assertIn('config', result)
    
    @patch('api_client.get_terminal_id')
    @patch('api_client.get_auth_token')
    @patch('requests.Session.request')
    def test_global_report_status(self, mock_request, mock_get_token, mock_get_terminal_id):
        """Test global report_status function"""
        mock_get_token.return_value = "test_token"
        mock_get_terminal_id.return_value = "test-terminal"
        
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'received': True}
        mock_response.content = b'{"received": true}'
        mock_request.return_value = mock_response
        
        status_data = {'status': 'active'}
        result = report_status(status_data)
        self.assertTrue(result['received'])
    
    @patch('api_client.validate_token')
    @patch('requests.Session.request')
    def test_global_validate_terminal_auth(self, mock_request, mock_validate_token):
        """Test global validate_terminal_auth function"""
        mock_validate_token.return_value = True
        
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'approved': True}
        mock_response.content = b'{"approved": true}'
        mock_request.return_value = mock_response
        
        result = validate_terminal_auth()
        self.assertTrue(result)


class TestRetryLogic(unittest.TestCase):
    """Test retry logic and error handling"""
    
    def setUp(self):
        """Set up test environment"""
        self.api_client = APIClient(server_url="http://test-server:5000")
    
    @patch('requests.Session.request')
    @patch('api_client.get_auth_token')
    def test_retry_on_server_error(self, mock_get_token, mock_request):
        """Test retry behavior on server errors"""
        mock_get_token.return_value = "test_token"
        
        # Mock server error followed by success
        error_response = Mock()
        error_response.status_code = 500
        error_response.text = "Internal Server Error"
        
        success_response = Mock()
        success_response.status_code = 200
        success_response.json.return_value = {'status': 'success'}
        success_response.content = b'{"status": "success"}'
        
        mock_request.side_effect = [error_response, success_response]
        
        # Should eventually succeed after retry
        result = self.api_client._make_request('GET', '/api/test')
        self.assertEqual(result['status'], 'success')
    
    @patch('requests.Session.request')
    @patch('api_client.get_auth_token')
    def test_timeout_handling(self, mock_get_token, mock_request):
        """Test timeout handling"""
        mock_get_token.return_value = "test_token"
        
        # Mock timeout error
        mock_request.side_effect = requests.exceptions.Timeout("Request timeout")
        
        with self.assertRaises(APIException) as context:
            self.api_client._make_request('GET', '/api/test')
        
        self.assertIn("Network error", str(context.exception))


if __name__ == '__main__':
    unittest.main()