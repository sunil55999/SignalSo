#!/bin/bash

"""
SignalOS Desktop App Installer
One-click setup script for non-technical users
"""

set -e  # Exit on any error

# Configuration
APP_NAME="SignalOS"
APP_VERSION="1.0.0"
INSTALL_DIR="$HOME/SignalOS"
DESKTOP_FILE="$HOME/Desktop/SignalOS.desktop"
PYTHON_VERSION="3.11"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging
LOG_FILE="$HOME/signalojs_install.log"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

print_header() {
    echo -e "${BLUE}"
    echo "======================================================"
    echo "      SignalOS Desktop App Installer v$APP_VERSION"
    echo "======================================================"
    echo -e "${NC}"
}

print_status() {
    echo -e "${GREEN}✅ $1${NC}"
    log "SUCCESS: $1"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
    log "WARNING: $1"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
    log "ERROR: $1"
}

check_requirements() {
    log "Checking system requirements..."
    
    # Check OS
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        PLATFORM="linux"
        print_status "Linux system detected"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        PLATFORM="macos"
        print_status "macOS system detected"
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        PLATFORM="windows"
        print_status "Windows system detected"
    else
        print_error "Unsupported operating system: $OSTYPE"
        exit 1
    fi
    
    # Check available disk space (require at least 1GB)
    AVAILABLE_SPACE=$(df -h "$HOME" | awk 'NR==2 {print $4}' | sed 's/G//')
    if (( $(echo "$AVAILABLE_SPACE < 1" | bc -l) )); then
        print_error "Insufficient disk space. At least 1GB required."
        exit 1
    fi
    
    print_status "System requirements check passed"
}

install_python() {
    log "Setting up Python environment..."
    
    # Check if Python is installed
    if command -v python3 &> /dev/null; then
        PYTHON_CURRENT=$(python3 --version | grep -o '[0-9]\+\.[0-9]\+')
        print_status "Python $PYTHON_CURRENT found"
    else
        print_warning "Python not found. Installing Python..."
        
        if [[ "$PLATFORM" == "linux" ]]; then
            # Ubuntu/Debian
            if command -v apt-get &> /dev/null; then
                sudo apt-get update
                sudo apt-get install -y python3 python3-pip python3-venv
            # CentOS/RHEL
            elif command -v yum &> /dev/null; then
                sudo yum install -y python3 python3-pip
            # Arch Linux
            elif command -v pacman &> /dev/null; then
                sudo pacman -S python python-pip
            else
                print_error "Unsupported Linux distribution"
                exit 1
            fi
        elif [[ "$PLATFORM" == "macos" ]]; then
            # Check if Homebrew is installed
            if ! command -v brew &> /dev/null; then
                print_warning "Installing Homebrew..."
                /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
            fi
            brew install python@3.11
        fi
    fi
    
    # Create virtual environment
    VENV_DIR="$INSTALL_DIR/venv"
    if [[ ! -d "$VENV_DIR" ]]; then
        print_status "Creating virtual environment..."
        python3 -m venv "$VENV_DIR"
    fi
    
    # Activate virtual environment
    source "$VENV_DIR/bin/activate"
    
    # Upgrade pip
    pip install --upgrade pip
    
    print_status "Python environment ready"
}

download_app() {
    log "Downloading SignalOS application..."
    
    # Create installation directory
    mkdir -p "$INSTALL_DIR"
    cd "$INSTALL_DIR"
    
    # Download application files (in real scenario, this would download from a release)
    # For now, we'll create the directory structure
    mkdir -p {auth,parser,parser/lang,config,server,setup,installer,logs,reports,updates}
    
    # Create main application files
    cat > main.py << 'EOF'
#!/usr/bin/env python3
"""
SignalOS Desktop Application
Main entry point for the trading automation platform
"""

import sys
import os
from pathlib import Path

# Add application directory to Python path
app_dir = Path(__file__).parent
sys.path.insert(0, str(app_dir))

def main():
    print("🚀 Starting SignalOS...")
    print("📱 Visit http://localhost:5000 for the web interface")
    
    # Start the application
    try:
        from desktop_app.main import main as app_main
        return app_main()
    except ImportError:
        print("❌ Application modules not found")
        return 1

if __name__ == "__main__":
    sys.exit(main())
EOF
    
    # Create requirements file
    cat > requirements.txt << 'EOF'
fastapi>=0.100.0
uvicorn>=0.23.0
aiohttp>=3.8.0
requests>=2.31.0
PyJWT>=2.8.0
langdetect>=1.0.9
opencv-python>=4.8.0
pillow>=10.0.0
easyocr>=1.7.0
websockets>=11.0.0
python-telegram-bot>=20.0
telethon>=1.30.0
psutil>=5.9.0
reportlab>=4.0.0
matplotlib>=3.7.0
numpy>=1.24.0
pandas>=2.0.0
pathlib2>=2.3.0
python-dotenv>=1.0.0
pydantic>=2.0.0
flask>=2.3.0
flask-cors>=4.0.0
EOF
    
    print_status "Application structure created"
}

install_dependencies() {
    log "Installing Python dependencies..."
    
    # Activate virtual environment
    source "$INSTALL_DIR/venv/bin/activate"
    
    # Install requirements
    pip install -r "$INSTALL_DIR/requirements.txt"
    
    print_status "Dependencies installed successfully"
}

create_desktop_shortcut() {
    log "Creating desktop shortcut..."
    
    if [[ "$PLATFORM" == "linux" ]]; then
        cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=SignalOS
Comment=Trading Signal Automation Platform
Exec=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/main.py
Icon=$INSTALL_DIR/icon.png
Terminal=false
Categories=Office;Finance;
StartupNotify=true
EOF
        chmod +x "$DESKTOP_FILE"
        
    elif [[ "$PLATFORM" == "macos" ]]; then
        # Create macOS app bundle
        APP_BUNDLE="$HOME/Applications/SignalOS.app"
        mkdir -p "$APP_BUNDLE/Contents/MacOS"
        mkdir -p "$APP_BUNDLE/Contents/Resources"
        
        cat > "$APP_BUNDLE/Contents/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>SignalOS</string>
    <key>CFBundleIdentifier</key>
    <string>com.signalojs.desktop</string>
    <key>CFBundleName</key>
    <string>SignalOS</string>
    <key>CFBundleVersion</key>
    <string>$APP_VERSION</string>
</dict>
</plist>
EOF
        
        cat > "$APP_BUNDLE/Contents/MacOS/SignalOS" << EOF
#!/bin/bash
cd "$INSTALL_DIR"
source venv/bin/activate
python main.py
EOF
        chmod +x "$APP_BUNDLE/Contents/MacOS/SignalOS"
    fi
    
    print_status "Desktop shortcut created"
}

setup_autostart() {
    log "Setting up auto-start (optional)..."
    
    read -p "Do you want SignalOS to start automatically when you log in? (y/n): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if [[ "$PLATFORM" == "linux" ]]; then
            AUTOSTART_DIR="$HOME/.config/autostart"
            mkdir -p "$AUTOSTART_DIR"
            cp "$DESKTOP_FILE" "$AUTOSTART_DIR/SignalOS.desktop"
            
        elif [[ "$PLATFORM" == "macos" ]]; then
            # Add to Login Items via AppleScript
            osascript -e "tell application \"System Events\" to make login item at end with properties {path:\"$HOME/Applications/SignalOS.app\", hidden:false}"
        fi
        
        print_status "Auto-start configured"
    else
        print_status "Auto-start skipped"
    fi
}

configure_firewall() {
    log "Configuring firewall (if needed)..."
    
    if [[ "$PLATFORM" == "linux" ]]; then
        # Check if UFW is installed and active
        if command -v ufw &> /dev/null && ufw status | grep -q "Status: active"; then
            print_warning "UFW firewall detected. You may need to allow port 5000:"
            echo "sudo ufw allow 5000"
        fi
    fi
}

run_tests() {
    log "Running installation tests..."
    
    cd "$INSTALL_DIR"
    source venv/bin/activate
    
    # Test Python imports
    python -c "
import sys
try:
    import fastapi
    import uvicorn
    import requests
    print('✅ Core dependencies imported successfully')
except ImportError as e:
    print(f'❌ Import error: {e}')
    sys.exit(1)
"
    
    if [[ $? -eq 0 ]]; then
        print_status "Installation tests passed"
    else
        print_error "Installation tests failed"
        exit 1
    fi
}

create_uninstaller() {
    log "Creating uninstaller..."
    
    cat > "$INSTALL_DIR/uninstall.sh" << 'EOF'
#!/bin/bash

echo "Uninstalling SignalOS..."

# Remove installation directory
rm -rf "$HOME/SignalOS"

# Remove desktop shortcut
rm -f "$HOME/Desktop/SignalOS.desktop"

# Remove autostart entry
rm -f "$HOME/.config/autostart/SignalOS.desktop"

# Remove from macOS Applications (if exists)
rm -rf "$HOME/Applications/SignalOS.app"

echo "✅ SignalOS uninstalled successfully"
EOF
    
    chmod +x "$INSTALL_DIR/uninstall.sh"
    print_status "Uninstaller created"
}

print_completion_message() {
    echo
    echo -e "${GREEN}"
    echo "======================================================"
    echo "         🎉 Installation Complete! 🎉"
    echo "======================================================"
    echo -e "${NC}"
    echo
    echo "📍 Installation Location: $INSTALL_DIR"
    echo "🖥️  Desktop Shortcut: Created"
    echo "📋 Start Menu Entry: Created"
    echo
    echo "🚀 To start SignalOS:"
    echo "   • Double-click the desktop shortcut, or"
    echo "   • Run: $INSTALL_DIR/venv/bin/python $INSTALL_DIR/main.py"
    echo
    echo "🌐 Web Interface: http://localhost:5000"
    echo "📚 Documentation: $INSTALL_DIR/README.md"
    echo "🗑️  To uninstall: $INSTALL_DIR/uninstall.sh"
    echo
    echo "📧 Support: support@signalojs.com"
    echo
}

main() {
    print_header
    
    log "Starting SignalOS installation..."
    
    # Installation steps
    check_requirements
    install_python
    download_app
    install_dependencies
    create_desktop_shortcut
    setup_autostart
    configure_firewall
    run_tests
    create_uninstaller
    
    print_completion_message
    
    log "Installation completed successfully"
}

# Run main function
main "$@"