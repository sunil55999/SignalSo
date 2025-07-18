"""
Tests for marketplace functionality
"""

import pytest
import asyncio
import json
import zipfile
import io
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path

from core.marketplace import MarketplaceEngine, PluginStatus, PluginType


class TestMarketplaceEngine:
    """Test marketplace engine functionality"""
    
    @pytest.fixture
    def engine(self):
        """Create marketplace engine instance"""
        return MarketplaceEngine()
    
    @pytest.mark.asyncio
    async def test_initialization(self, engine):
        """Test engine initialization"""
        await engine.initialize()
        assert engine.plugins_dir.exists()
        assert engine.loaded_plugins == {}
        assert engine.plugin_registry == {}
    
    @pytest.mark.asyncio
    async def test_validate_plugin_package(self, engine):
        """Test plugin package validation"""
        await engine.initialize()
        
        # Create valid plugin package
        plugin_data = io.BytesIO()
        with zipfile.ZipFile(plugin_data, 'w') as zf:
            # Add required files
            zf.writestr('plugin.json', json.dumps({
                "name": "Test Plugin",
                "version": "1.0.0",
                "author": "Test Author",
                "description": "Test description",
                "type": "signal_provider"
            }))
            zf.writestr('main.py', 'def test(): pass')
        
        plugin_data.seek(0)
        result = await engine._validate_plugin_package(plugin_data.read())
        
        assert result["name"] == "Test Plugin"
        assert result["version"] == "1.0.0"
        assert result["type"] == "signal_provider"
    
    @pytest.mark.asyncio
    async def test_validate_plugin_package_invalid(self, engine):
        """Test plugin package validation with invalid package"""
        await engine.initialize()
        
        # Create invalid plugin package (missing files)
        plugin_data = io.BytesIO()
        with zipfile.ZipFile(plugin_data, 'w') as zf:
            zf.writestr('readme.txt', 'Invalid package')
        
        plugin_data.seek(0)
        
        with pytest.raises(ValueError):
            await engine._validate_plugin_package(plugin_data.read())
    
    @pytest.mark.asyncio
    async def test_install_plugin(self, engine):
        """Test plugin installation"""
        await engine.initialize()
        
        # Mock plugin validation
        with patch.object(engine, '_validate_plugin_package') as mock_validate:
            mock_validate.return_value = {
                "name": "Test Plugin",
                "version": "1.0.0",
                "type": "signal_provider"
            }
            
            with patch.object(engine, '_extract_plugin') as mock_extract:
                mock_extract.return_value = Path("test_plugin")
                
                with patch.object(engine, '_register_plugin') as mock_register:
                    with patch.object(engine, '_create_user_plugin_record') as mock_create:
                        
                        plugin_data = b"mock_plugin_data"
                        result = await engine.install_plugin("test_plugin", "user_123", plugin_data)
                        
                        assert result["success"] is True
                        assert result["plugin_id"] == "test_plugin"
                        mock_validate.assert_called_once()
                        mock_extract.assert_called_once()
                        mock_register.assert_called_once()
                        mock_create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_activate_plugin(self, engine):
        """Test plugin activation"""
        await engine.initialize()
        
        # Mock loaded plugin
        mock_module = Mock()
        mock_module.activate = AsyncMock()
        
        engine.loaded_plugins["test_plugin"] = {
            "module": mock_module,
            "info": {"name": "Test Plugin"}
        }
        
        with patch.object(engine, '_update_plugin_status') as mock_update:
            result = await engine.activate_plugin("user_123", "test_plugin")
            
            assert result["success"] is True
            mock_module.activate.assert_called_once_with("user_123")
            mock_update.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_deactivate_plugin(self, engine):
        """Test plugin deactivation"""
        await engine.initialize()
        
        # Mock loaded plugin
        mock_module = Mock()
        mock_module.deactivate = AsyncMock()
        
        engine.loaded_plugins["test_plugin"] = {
            "module": mock_module,
            "info": {"name": "Test Plugin"}
        }
        
        with patch.object(engine, '_update_plugin_status') as mock_update:
            result = await engine.deactivate_plugin("user_123", "test_plugin")
            
            assert result["success"] is True
            mock_module.deactivate.assert_called_once_with("user_123")
            mock_update.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_uninstall_plugin(self, engine):
        """Test plugin uninstallation"""
        await engine.initialize()
        
        # Mock loaded plugin
        mock_module = Mock()
        mock_module.cleanup = AsyncMock()
        
        engine.loaded_plugins["test_plugin"] = {
            "module": mock_module,
            "info": {"name": "Test Plugin"}
        }
        
        with patch.object(engine, '_update_plugin_status') as mock_update:
            with patch('shutil.rmtree') as mock_rmtree:
                result = await engine.uninstall_plugin("user_123", "test_plugin")
                
                assert result["success"] is True
                mock_module.cleanup.assert_called_once_with("user_123")
                mock_update.assert_called_once()
                assert "test_plugin" not in engine.loaded_plugins
    
    @pytest.mark.asyncio
    async def test_get_marketplace_plugins(self, engine):
        """Test getting marketplace plugins"""
        await engine.initialize()
        
        result = await engine.get_marketplace_plugins()
        
        assert result["success"] is True
        assert "plugins" in result
        assert "total" in result
        assert isinstance(result["plugins"], list)
    
    @pytest.mark.asyncio
    async def test_get_marketplace_plugins_filtered(self, engine):
        """Test getting filtered marketplace plugins"""
        await engine.initialize()
        
        result = await engine.get_marketplace_plugins(category="signal_provider")
        
        assert result["success"] is True
        assert "plugins" in result
        # All plugins should be signal_provider category
        for plugin in result["plugins"]:
            assert plugin["category"] == "signal_provider"
    
    @pytest.mark.asyncio
    async def test_get_user_plugins(self, engine):
        """Test getting user plugins"""
        await engine.initialize()
        
        result = await engine.get_user_plugins("user_123")
        
        assert result["success"] is True
        assert "plugins" in result
        assert "total" in result
        assert isinstance(result["plugins"], list)
    
    @pytest.mark.asyncio
    async def test_execute_plugin_method(self, engine):
        """Test executing plugin method"""
        await engine.initialize()
        
        # Mock loaded plugin
        mock_module = Mock()
        mock_method = AsyncMock(return_value="test_result")
        mock_module.test_method = mock_method
        
        engine.loaded_plugins["test_plugin"] = {
            "module": mock_module,
            "info": {"name": "Test Plugin"}
        }
        
        result = await engine.execute_plugin_method("user_123", "test_plugin", "test_method", "arg1", key="value")
        
        assert result["success"] is True
        assert result["result"] == "test_result"
        mock_method.assert_called_once_with("user_123", "arg1", key="value")
    
    @pytest.mark.asyncio
    async def test_get_plugin_config_schema(self, engine):
        """Test getting plugin configuration schema"""
        await engine.initialize()
        
        # Mock loaded plugin
        engine.loaded_plugins["test_plugin"] = {
            "module": Mock(),
            "info": {
                "name": "Test Plugin",
                "config_schema": {
                    "type": "object",
                    "properties": {
                        "api_key": {"type": "string"},
                        "timeout": {"type": "number"}
                    }
                }
            }
        }
        
        result = await engine.get_plugin_config_schema("test_plugin")
        
        assert result["success"] is True
        assert "schema" in result
        assert result["schema"]["type"] == "object"
    
    @pytest.mark.asyncio
    async def test_update_plugin_config(self, engine):
        """Test updating plugin configuration"""
        await engine.initialize()
        
        # Mock loaded plugin
        mock_module = Mock()
        mock_module.on_config_update = AsyncMock()
        
        engine.loaded_plugins["test_plugin"] = {
            "module": mock_module,
            "info": {"name": "Test Plugin"}
        }
        
        with patch.object(engine, 'get_plugin_config_schema') as mock_schema:
            mock_schema.return_value = {"success": True, "schema": {}}
            
            with patch.object(engine, '_update_plugin_config_db') as mock_update:
                config = {"api_key": "test_key", "timeout": 30}
                result = await engine.update_plugin_config("user_123", "test_plugin", config)
                
                assert result["success"] is True
                mock_module.on_config_update.assert_called_once_with("user_123", config)
                mock_update.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_plugin_stats(self, engine):
        """Test getting plugin statistics"""
        await engine.initialize()
        
        stats = await engine.get_plugin_stats()
        
        assert "total_plugins" in stats
        assert "active_plugins" in stats
        assert "categories" in stats
        assert "marketplace_health" in stats
        assert isinstance(stats["categories"], dict)


class TestMarketplaceAPI:
    """Test marketplace API endpoints"""
    
    @pytest.fixture
    def mock_user(self):
        """Mock authenticated user"""
        return {"user_id": "test_user", "username": "test@example.com"}
    
    @pytest.mark.asyncio
    async def test_get_marketplace_plugins_endpoint(self, mock_user):
        """Test get marketplace plugins endpoint"""
        from api.marketplace import get_marketplace_plugins
        
        with patch('core.marketplace.MarketplaceEngine') as mock_engine:
            mock_instance = AsyncMock()
            mock_instance.get_marketplace_plugins.return_value = {
                "success": True,
                "plugins": [
                    {
                        "id": "test_plugin",
                        "name": "Test Plugin",
                        "category": "signal_provider"
                    }
                ],
                "total": 1
            }
            mock_engine.return_value = mock_instance
            
            result = await get_marketplace_plugins(None, mock_user)
            
            assert result["success"] is True
            assert "plugins" in result
            mock_instance.initialize.assert_called_once()
            mock_instance.get_marketplace_plugins.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_install_plugin_endpoint(self, mock_user):
        """Test install plugin endpoint"""
        from api.marketplace import install_plugin
        
        # Mock file upload
        mock_file = Mock()
        mock_file.read = AsyncMock(return_value=b"mock_plugin_data")
        
        with patch('core.marketplace.MarketplaceEngine') as mock_engine:
            mock_instance = AsyncMock()
            mock_instance.install_plugin.return_value = {
                "success": True,
                "plugin_id": "test_plugin"
            }
            mock_engine.return_value = mock_instance
            
            result = await install_plugin("test_plugin", mock_file, mock_user)
            
            assert result["success"] is True
            mock_instance.initialize.assert_called_once()
            mock_instance.install_plugin.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_activate_plugin_endpoint(self, mock_user):
        """Test activate plugin endpoint"""
        from api.marketplace import activate_plugin
        
        with patch('core.marketplace.MarketplaceEngine') as mock_engine:
            mock_instance = AsyncMock()
            mock_instance.activate_plugin.return_value = {
                "success": True,
                "message": "Plugin activated"
            }
            mock_engine.return_value = mock_instance
            
            result = await activate_plugin("test_plugin", mock_user)
            
            assert result["success"] is True
            mock_instance.initialize.assert_called_once()
            mock_instance.activate_plugin.assert_called_once_with("test_user", "test_plugin")


if __name__ == "__main__":
    pytest.main([__file__])