#!/bin/bash

# Dirty CLI - Automated Installer
# Optimized for Linux & Termux

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

echo -e "${BOLD}${BLUE}=== Dirty CLI & Edge Services Installer ===${NC}"
echo -e "${CYAN}Starting automatic setup...${NC}\n"

# Function to check for command
check_cmd() {
    command -v "$1" >/dev/null 2>&1
}

# 1. Dependency Checks
echo -e "${BOLD}[1/4] Checking Dependencies...${NC}"

if check_cmd python3; then
    echo -e "${GREEN}✓ Python 3 is installed: $(python3 --version)${NC}"
else
    echo -e "${RED}✗ Python 3 is not found. Please install it.${NC}"
    exit 1
fi

if check_cmd npm; then
    echo -e "${GREEN}✓ npm is installed: $(npm --version)${NC}"
else
    echo -e "${YELLOW}! npm not found. You'll need it if you want to deploy the Cloudflare Worker.${NC}"
fi

# 2. Permissions
echo -e "\n${BOLD}[2/4] Setting Permissions...${NC}"
chmod +x dirty.py
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ dirty.py is now executable.${NC}"
else
    echo -e "${RED}✗ Failed to set permissions on dirty.py.${NC}"
fi

# 3. Embedding Worker Scripts
echo -e "\n${BOLD}[3/4] Preparing Worker Bridge...${NC}"
if [ -f "generate_worker.py" ]; then
    python3 generate_worker.py
    echo -e "${GREEN}✓ unified_worker.ts updated with latest logic.${NC}"
else
    echo -e "${YELLOW}! generate_worker.py not found, skipping bridge update.${NC}"
fi

# 4. Model Setup (Interactive)
echo -e "\n${BOLD}[4/4] Model Setup${NC}"
read -p "Do you want to download the SmolLM2-135M model now? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    ./dirty.py setup
else
    echo -e "${BLUE}Skipping model download. You can run './dirty.py setup' later.${NC}"
fi

echo -e "\n${BOLD}${GREEN}=== Installation Complete! ===${NC}"
echo -e "You can now use the ${BOLD}dirty${NC} command."
echo -e "Try: ${CYAN}./dirty.py --help${NC}"

# Optional: Suggest adding to path
if [[ "$OSTYPE" == "linux-android"* ]]; then
    # Termux
    echo -e "\n${BOLD}${BLUE}Termux Tip:${NC}"
    echo -e "To run from anywhere, move dirty.py to your bin:"
    echo -e "${CYAN}mv dirty.py \$PREFIX/bin/dirty && chmod +x \$PREFIX/bin/dirty${NC}"
fi
