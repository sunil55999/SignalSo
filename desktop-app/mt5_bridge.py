#!/usr/bin/env python3
"""
MT5 Bridge - Main interface
"""

from trade.mt5_socket_bridge import MT5SocketBridge

# Main MT5 Bridge class (alias for compatibility)
class MT5Bridge(MT5SocketBridge):
    """Main MT5 Bridge interface"""
    pass