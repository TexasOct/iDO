#!/bin/bash

# Create Self-Signed Code Signing Certificate for Development
# Purpose: Preserve macOS permissions across app updates
# Usage: sh scripts/unix/create-signing-cert.sh

set -e

# Color output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

printf "${BLUE}================================================${NC}\n"
printf "${BLUE}  Create Self-Signed Code Signing Certificate${NC}\n"
printf "${BLUE}================================================${NC}\n"
printf "\n"

# Certificate details
CERT_NAME="iDO Development Signing"
KEYCHAIN_NAME="login.keychain-db"

# Check if certificate already exists
if security find-identity -v -p codesigning | grep -q "$CERT_NAME"; then
    printf "${YELLOW}⚠${NC}  Certificate '$CERT_NAME' already exists\n"
    printf "${YELLOW}   You can use it directly for signing${NC}\n"
    printf "\n"

    # Show existing certificate
    printf "${BLUE}Existing certificate:${NC}\n"
    security find-identity -v -p codesigning | grep "$CERT_NAME"
    printf "\n"

    printf "${YELLOW}Do you want to recreate it? (y/N): ${NC}"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        printf "${GREEN}✓${NC} Using existing certificate\n"
        exit 0
    fi

    # Delete old certificate
    printf "${BLUE}Deleting old certificate...${NC}\n"
    CERT_HASH=$(security find-identity -v -p codesigning | grep "$CERT_NAME" | awk '{print $2}')
    security delete-identity -Z "$CERT_HASH" "$KEYCHAIN_NAME" 2>/dev/null || true
    printf "${GREEN}✓${NC} Old certificate deleted\n"
fi

# Create temporary directory for certificate files
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

# Create certificate configuration
cat > "$TEMP_DIR/cert.conf" <<EOF
[ req ]
default_bits       = 2048
distinguished_name = req_distinguished_name
x509_extensions    = v3_ca
prompt             = no

[ req_distinguished_name ]
CN = $CERT_NAME
O  = iDO Development
OU = Development

[ v3_ca ]
basicConstraints       = critical,CA:FALSE
keyUsage               = critical,digitalSignature
extendedKeyUsage       = critical,codeSigning
subjectKeyIdentifier   = hash
authorityKeyIdentifier = keyid:always
EOF

printf "${BLUE}[1/4]${NC} Generating RSA key pair...\n"
openssl genrsa -out "$TEMP_DIR/key.pem" 2048 2>&1 | grep -v "^e is" || true
printf "${GREEN}✓${NC} Key pair generated\n"
printf "\n"

printf "${BLUE}[2/4]${NC} Creating self-signed certificate...\n"
openssl req -new -x509 -days 3650 \
    -key "$TEMP_DIR/key.pem" \
    -out "$TEMP_DIR/cert.pem" \
    -config "$TEMP_DIR/cert.conf" 2>&1 | grep -v "^You are about to" || true
printf "${GREEN}✓${NC} Certificate created (valid for 10 years)\n"
printf "\n"

printf "${BLUE}[3/4]${NC} Converting to PKCS12 format...\n"
openssl pkcs12 -export \
    -inkey "$TEMP_DIR/key.pem" \
    -in "$TEMP_DIR/cert.pem" \
    -out "$TEMP_DIR/cert.p12" \
    -name "$CERT_NAME" \
    -passout pass:
printf "${GREEN}✓${NC} Certificate converted\n"
printf "\n"

printf "${BLUE}[4/4]${NC} Importing certificate to Keychain...\n"
security import "$TEMP_DIR/cert.p12" \
    -k "$KEYCHAIN_NAME" \
    -T /usr/bin/codesign \
    -T /usr/bin/security \
    -P "" 2>&1 | grep -v "1 identity imported" || true

# Trust the certificate for code signing
CERT_HASH=$(security find-identity -v -p codesigning | grep "$CERT_NAME" | awk '{print $2}')
security set-key-partition-list -S apple-tool:,apple:,codesign: -s -k "" "$KEYCHAIN_NAME" 2>&1 | grep -v "The authorization was denied" || true

printf "${GREEN}✓${NC} Certificate imported to Keychain\n"
printf "\n"

# Verify certificate
printf "${BLUE}Verifying certificate...${NC}\n"
if security find-identity -v -p codesigning | grep -q "$CERT_NAME"; then
    printf "${GREEN}✓${NC} Certificate installed successfully\n"
    printf "\n"
    printf "${BLUE}Certificate details:${NC}\n"
    security find-identity -v -p codesigning | grep "$CERT_NAME"
else
    printf "${RED}✗${NC} Certificate verification failed\n"
    exit 1
fi

printf "\n"
printf "${BLUE}================================================${NC}\n"
printf "${GREEN}🎉 Certificate Created Successfully!${NC}\n"
printf "${BLUE}================================================${NC}\n"
printf "\n"
printf "${YELLOW}Next steps:${NC}\n"
printf "  1. Run ${GREEN}pnpm bundle${NC} to build your app\n"
printf "  2. Run ${GREEN}pnpm sign-macos${NC} to sign with the new certificate\n"
printf "  3. Grant permissions when prompted\n"
printf "  4. Future updates will ${GREEN}preserve${NC} your permissions\n"
printf "\n"
printf "${YELLOW}Note:${NC} This certificate is for development only.\n"
printf "For distribution, you need an Apple Developer ID.\n"
printf "\n"
