#!/usr/bin/env python3
"""
Strategy Runtime for SignalOS Desktop Application
"""

import logging
from strategy.prop_firm_mode import PropFirmMode

class StrategyRuntime:
    """Main strategy runtime engine"""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.logger = logging.getLogger('StrategyRuntime')
        self.prop_firm_mode = PropFirmMode(config_file)
        
    def enable_prop_firm_mode(self):
        """Enable prop firm mode"""
        return self.prop_firm_mode.enable_prop_firm_mode()
        
    def get_status(self):
        """Get strategy runtime status"""
        return {
            "prop_firm": self.prop_firm_mode.get_status()
        }