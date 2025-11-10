#!/bin/bash

# iDO Tauri Dev with PyTauri TypeScript Generation
# This script starts Tauri dev mode with PYTAURI_GEN_TS=1 to generate TypeScript bindings

set -e

# Color codes for output
GREEN=$'\033[0;32m'
BLUE=$'\033[0;34m'
YELLOW=$'\033[1;33m'
NC=$'\033[0m' # No Color

echo "${BLUE}🚀 Starting Tauri dev with PyTauri TS generation...${NC}"
echo ""
echo "${YELLOW}Info:${NC}"
echo "  • PYTAURI_GEN_TS=1 is enabled"
echo "  • TypeScript bindings will be generated to: src/lib/client/"
echo "  • First run may take longer to generate types"
echo ""

# Export the environment variable and run tauri dev
export PYTAURI_GEN_TS=1

# Activate Python virtual environment if it exists
if [ -d ".venv" ]; then
  echo "${BLUE}Activating Python virtual environment...${NC}"
  source ./.venv/bin/activate
else
  echo "${YELLOW}Warning: .venv directory not found. Please activate your Python virtual environment manually or set VIRTUAL_ENV.${NC}"
fi

echo "${BLUE}Running: pnpm tauri dev${NC}"
echo ""

pnpm tauri dev
