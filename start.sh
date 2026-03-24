#!/usr/bin/env bash
set -euo pipefail

APP_NAME="OpenXS Paper"
APP_EXEC="openxs-paper"
REQUIRED_MAJOR=3
REQUIRED_MINOR=12
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
ICON="$SCRIPT_DIR/assets/icons/logo.png"   # .png for Linux .desktop; .icns for macOS

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()  { echo -e "${GREEN}[+]${NC} $*"; }
warn()  { echo -e "${YELLOW}[*]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

echo ""
echo " ============================================="
echo "  $APP_NAME - Installer & Launcher"
echo " ============================================="
echo ""

# ─────────────────────────────────────────────
# 1. Detect package manager
# ─────────────────────────────────────────────
detect_pm() {
    if [[ "$OSTYPE" == "darwin"* ]]; then echo "brew"
    elif command -v apt-get &>/dev/null; then echo "apt"
    elif command -v pacman   &>/dev/null; then echo "pacman"
    elif command -v dnf      &>/dev/null; then echo "dnf"
    elif command -v zypper   &>/dev/null; then echo "zypper"
    else echo "unknown"
    fi
}

# ─────────────────────────────────────────────
# 2. Install Python 3.12
# ─────────────────────────────────────────────
install_python() {
    local pm; pm=$(detect_pm)
    warn "Python ${REQUIRED_MAJOR}.${REQUIRED_MINOR} not found. Installing via $pm..."
    case "$pm" in
        brew)
            command -v brew &>/dev/null || error "Homebrew not found. Install from https://brew.sh"
            brew install python@3.12
            brew link --force python@3.12
            ;;
        apt)
            sudo apt-get update -qq
            if command -v add-apt-repository &>/dev/null; then
                sudo add-apt-repository -y ppa:deadsnakes/ppa
                sudo apt-get update -qq
            fi
            sudo apt-get install -y python3.12 python3.12-venv python3.12-dev
            ;;
        pacman)  sudo pacman -Sy --noconfirm python ;;
        dnf)     sudo dnf install -y python3.12 python3.12-devel ;;
        zypper)  sudo zypper install -y python312 ;;
        *)       error "Unsupported package manager. Install Python 3.12 from https://www.python.org/downloads/" ;;
    esac
}

# ─────────────────────────────────────────────
# 3. Find Python 3.12+
# ─────────────────────────────────────────────
find_python() {
    for cmd in python3.12 python3 python; do
        if command -v "$cmd" &>/dev/null; then
            local ver major minor
            ver=$("$cmd" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || true)
            major=$(echo "$ver" | cut -d. -f1)
            minor=$(echo "$ver" | cut -d. -f2)
            if [[ "$major" -eq "$REQUIRED_MAJOR" && "$minor" -ge "$REQUIRED_MINOR" ]]; then
                echo "$cmd"; return 0
            fi
        fi
    done
    return 1
}

# ─────────────────────────────────────────────
# 4. Check / install Python
# ─────────────────────────────────────────────
warn "Checking for Python ${REQUIRED_MAJOR}.${REQUIRED_MINOR}..."
PYTHON_CMD=""
if ! PYTHON_CMD=$(find_python); then
    install_python
    PYTHON_CMD=$(find_python) || error "Python ${REQUIRED_MAJOR}.${REQUIRED_MINOR}+ still not found. Install manually."
fi
info "Using: $PYTHON_CMD ($(${PYTHON_CMD} --version))"

# ─────────────────────────────────────────────
# 5. Create / reuse venv
# ─────────────────────────────────────────────
if [[ -f "$VENV_DIR/bin/python" ]]; then
    info "Virtual environment already exists."
else
    warn "Creating virtual environment..."
    "$PYTHON_CMD" -m venv "$VENV_DIR"
    info "Virtual environment created."
fi

VENV_PYTHON="$VENV_DIR/bin/python"
VENV_PIP="$VENV_DIR/bin/pip"

# ─────────────────────────────────────────────
# 6. Install dependencies
# ─────────────────────────────────────────────
warn "Installing dependencies..."
"$VENV_PIP" install --upgrade pip --quiet
"$VENV_PIP" install -r "$SCRIPT_DIR/requirements.txt" --quiet
info "Dependencies ready."

# ─────────────────────────────────────────────
# 7. Create shortcuts
# ─────────────────────────────────────────────
create_shortcuts_linux() {
    # launcher wrapper script
    LAUNCHER="$SCRIPT_DIR/$APP_EXEC"
    cat > "$LAUNCHER" <<EOF
#!/usr/bin/env bash
cd "$SCRIPT_DIR"
exec "$VENV_PYTHON" main.py "\$@"
EOF
    chmod +x "$LAUNCHER"

    # .desktop file
    DESKTOP_ENTRY="[Desktop Entry]
Name=$APP_NAME
Comment=Live Video Wallpaper Engine
Exec=$LAUNCHER
Icon=$ICON
Terminal=false
Type=Application
Categories=Utility;
StartupNotify=true"

    # Desktop
    DESKTOP_FILE="$HOME/Desktop/$APP_EXEC.desktop"
    echo "$DESKTOP_ENTRY" > "$DESKTOP_FILE"
    chmod +x "$DESKTOP_FILE"
    gio set "$DESKTOP_FILE" metadata::trusted true 2>/dev/null || true

    # Start menu (applications)
    APPS_DIR="$HOME/.local/share/applications"
    mkdir -p "$APPS_DIR"
    echo "$DESKTOP_ENTRY" > "$APPS_DIR/$APP_EXEC.desktop"
    update-desktop-database "$APPS_DIR" 2>/dev/null || true

    info "Desktop & Start Menu shortcuts created."
}

create_shortcuts_macos() {
    APP_BUNDLE="$HOME/Applications/$APP_NAME.app"
    MACOS_DIR="$APP_BUNDLE/Contents/MacOS"
    mkdir -p "$MACOS_DIR"

    # launcher script inside .app
    cat > "$MACOS_DIR/$APP_EXEC" <<EOF
#!/usr/bin/env bash
cd "$SCRIPT_DIR"
exec "$VENV_PYTHON" main.py "\$@"
EOF
    chmod +x "$MACOS_DIR/$APP_EXEC"

    # minimal Info.plist
    cat > "$APP_BUNDLE/Contents/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleName</key><string>$APP_NAME</string>
  <key>CFBundleExecutable</key><string>$APP_EXEC</string>
  <key>CFBundleIdentifier</key><string>com.shirushimori.openxspaper</string>
  <key>CFBundleVersion</key><string>1.0</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>LSUIElement</key><false/>
</dict></plist>
EOF

    # symlink to Desktop
    ln -sf "$APP_BUNDLE" "$HOME/Desktop/$APP_NAME.app" 2>/dev/null || true
    info "macOS .app bundle created in ~/Applications and linked to Desktop."
}

warn "Creating shortcuts..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    create_shortcuts_macos
else
    create_shortcuts_linux
fi

# ─────────────────────────────────────────────
# 8. Launch
# ─────────────────────────────────────────────
echo ""
info "Starting $APP_NAME..."
echo ""
cd "$SCRIPT_DIR"
exec "$VENV_PYTHON" main.py
