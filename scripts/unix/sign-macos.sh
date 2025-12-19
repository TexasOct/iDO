#!/bin/bash

# macOS Application Signing Fix Script
# Purpose: Fix double-click launch issue caused by adhoc signature
# Usage: sh scripts/sign-macos.sh

set -e  # Exit immediately on error

# Color output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Project root directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Application path
APP_PATH="$PROJECT_ROOT/src-tauri/target/bundle-release/bundle/macos/iDO.app"
ENTITLEMENTS="$PROJECT_ROOT/src-tauri/entitlements.plist"

printf "${BLUE}================================================${NC}\n"
printf "${BLUE}  iDO macOS Application Signing Fix Tool${NC}\n"
printf "${BLUE}================================================${NC}\n"
printf "\n"

# Check if application exists
if [ ! -d "$APP_PATH" ]; then
    printf "${RED}❌ Error: Application bundle not found${NC}\n"
    printf "${YELLOW}Path: $APP_PATH${NC}\n"
    printf "${YELLOW}Please run first: pnpm tauri build${NC}\n"
    exit 1
fi

printf "${GREEN}✓${NC} Found application bundle: ${APP_PATH##*/}\n"
printf "\n"

# Check entitlements file
if [ ! -f "$ENTITLEMENTS" ]; then
    printf "${RED}❌ Error: entitlements.plist not found${NC}\n"
    printf "${YELLOW}Path: $ENTITLEMENTS${NC}\n"
    exit 1
fi

printf "${GREEN}✓${NC} Found entitlements file\n"
printf "\n"

# Detect signing identity
CERT_NAME="iDO Development Signing"
SIGNING_IDENTITY=""

# Check if APPLE_SIGNING_IDENTITY environment variable is set (for CI/CD)
if [ -n "${APPLE_SIGNING_IDENTITY:-}" ]; then
    SIGNING_IDENTITY="$APPLE_SIGNING_IDENTITY"
    printf "${GREEN}✓${NC} Using signing identity from environment: ${APPLE_SIGNING_IDENTITY}\n"
    printf "${YELLOW}   This will preserve permissions across updates${NC}\n"
# Check if development certificate exists
elif security find-identity -v -p codesigning | grep -q "$CERT_NAME"; then
    SIGNING_IDENTITY="$CERT_NAME"
    printf "${GREEN}✓${NC} Found development certificate: ${CERT_NAME}\n"
    printf "${YELLOW}   This will preserve permissions across updates${NC}\n"
else
    # Try to find any valid Developer ID certificate
    DEV_ID=$(security find-identity -v -p codesigning | grep "Developer ID Application" | head -n 1 | awk -F'"' '{print $2}')
    if [ -n "$DEV_ID" ]; then
        SIGNING_IDENTITY="$DEV_ID"
        printf "${GREEN}✓${NC} Found Developer ID: ${DEV_ID}\n"
        printf "${YELLOW}   This will preserve permissions across updates${NC}\n"
    else
        # Fall back to adhoc signing
        SIGNING_IDENTITY="-"
        printf "${YELLOW}⚠${NC}  No signing certificate found, using adhoc signature\n"
        printf "${YELLOW}   Permissions will be reset on each update${NC}\n"
        printf "${YELLOW}   Run ${GREEN}sh scripts/unix/create-signing-cert.sh${NC} to fix this\n"
    fi
fi
printf "\n"

# Step 1: Sign all dynamic libraries
printf "${BLUE}[1/3]${NC} Signing all dynamic library files...\n"
printf "${YELLOW}      This may take 10-30 seconds...${NC}\n"

DYLIB_COUNT=$(find "$APP_PATH/Contents/Resources" \( -name "*.dylib" -o -name "*.so" \) | wc -l | tr -d ' ')
printf "${YELLOW}      Found ${DYLIB_COUNT} dynamic library files${NC}\n"

find "$APP_PATH/Contents/Resources" \( -name "*.dylib" -o -name "*.so" \) \
    -exec codesign --force --sign "$SIGNING_IDENTITY" --timestamp=none --preserve-metadata=identifier,entitlements,flags {} \; 2>&1 | \
    grep -E "replacing existing signature" | wc -l | \
    xargs -I {} printf "${GREEN}      ✓ Signed {} files${NC}\n"

printf "${GREEN}✓${NC} Dynamic library signing complete\n"
printf "\n"

# Step 2: Sign application bundle with detected signing identity
printf "${BLUE}[2/3]${NC} Signing application bundle...\n"
codesign --force --sign "$SIGNING_IDENTITY" \
    --timestamp=none \
    --identifier "com.ido.desktop" \
    --entitlements "$ENTITLEMENTS" \
    --options runtime \
    "$APP_PATH" 2>&1 | grep -q "replacing existing signature" && \
    printf "${GREEN}✓${NC} Application bundle signing complete\n" || \
    printf "${GREEN}✓${NC} Application bundle signing complete (new signature)\n"
printf "\n"

# Step 3: Remove quarantine attributes
printf "${BLUE}[3/3]${NC} Removing quarantine attributes...\n"
xattr -cr "$APP_PATH" 2>&1
printf "${GREEN}✓${NC} Quarantine attributes removed\n"
printf "\n"

# Verify signature
printf "${BLUE}Verifying signature status...${NC}\n"
SIGNATURE_INFO=$(codesign -dvvv "$APP_PATH" 2>&1)

# Extract and display signature type
if echo "$SIGNATURE_INFO" | grep -q "Signature=adhoc"; then
    printf "${YELLOW}⚠${NC}  Signature type: adhoc (permissions will reset on updates)\n"
    printf "${YELLOW}   Run ${GREEN}sh scripts/unix/create-signing-cert.sh${NC} to create a stable certificate\n"
elif echo "$SIGNATURE_INFO" | grep -q "Authority=iDO Development Signing"; then
    printf "${GREEN}✓${NC} Signature type: Self-signed development certificate\n"
    printf "${GREEN}   Permissions will be preserved across updates\n"
elif echo "$SIGNATURE_INFO" | grep -q "Authority=Developer ID Application"; then
    DEV_ID_NAME=$(echo "$SIGNATURE_INFO" | grep "Authority=Developer ID Application" | head -n 1 | sed 's/.*Authority=//')
    printf "${GREEN}✓${NC} Signature type: Apple Developer ID\n"
    printf "${GREEN}   Certificate: ${DEV_ID_NAME}\n"
    printf "${GREEN}   Permissions will be preserved across updates\n"
else
    printf "${YELLOW}⚠${NC}  Signature type: Unknown\n"
fi

# Check entitlements (requires separate command)
ENTITLEMENTS_INFO=$(codesign -d --entitlements :- "$APP_PATH" 2>&1)
if echo "$ENTITLEMENTS_INFO" | grep -q "com.apple.security.cs.disable-library-validation"; then
    printf "${GREEN}✓${NC} Library Validation: Disabled (correct)\n"
else
    printf "${RED}✗${NC} Library Validation: Entitlements not detected\n"
fi

printf "\n"
printf "${BLUE}================================================${NC}\n"
printf "${GREEN}🎉 Signing Fix Complete!${NC}\n"
printf "${BLUE}================================================${NC}\n"
printf "\n"
printf "You can now launch the application by:\n"
printf "  1. Double-clicking ${GREEN}iDO.app${NC} in Finder\n"
printf "  2. Running: ${YELLOW}open \"%s\"${NC}\n" "$APP_PATH"
printf "\n"
printf "${YELLOW}Note: This script needs to be run again after each rebuild${NC}\n"
printf "\n"
