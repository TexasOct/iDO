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
x509_extensions    = v3_req
prompt             = no

[ req_distinguished_name ]
CN = $CERT_NAME
O  = iDO Development
OU = Development

[ v3_req ]
basicConstraints       = CA:FALSE
keyUsage               = digitalSignature
extendedKeyUsage       = codeSigning
subjectKeyIdentifier   = hash
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
# Use a temporary password for PKCS12
TEMP_PASSWORD="temp_$(openssl rand -hex 8)"

# Check OpenSSL version and use appropriate options
OPENSSL_VERSION=$(openssl version | awk '{print $2}')
if [[ "$OPENSSL_VERSION" =~ ^3\. ]]; then
    # OpenSSL 3.x - use legacy mode for macOS compatibility
    openssl pkcs12 -export -legacy \
        -inkey "$TEMP_DIR/key.pem" \
        -in "$TEMP_DIR/cert.pem" \
        -out "$TEMP_DIR/cert.p12" \
        -name "$CERT_NAME" \
        -passout pass:"$TEMP_PASSWORD"
else
    # OpenSSL 1.x - use traditional format
    openssl pkcs12 -export \
        -inkey "$TEMP_DIR/key.pem" \
        -in "$TEMP_DIR/cert.pem" \
        -out "$TEMP_DIR/cert.p12" \
        -name "$CERT_NAME" \
        -keypbe PBE-SHA1-3DES \
        -certpbe PBE-SHA1-3DES \
        -passout pass:"$TEMP_PASSWORD"
fi
printf "${GREEN}✓${NC} Certificate converted\n"
printf "\n"

printf "${BLUE}[4/4]${NC} Importing certificate to Keychain...\n"
printf "${YELLOW}   You will be prompted for your Mac login password${NC}\n"
printf "\n"

# Unlock keychain first
security unlock-keychain "$KEYCHAIN_NAME" || {
    printf "${RED}✗${NC} Failed to unlock keychain\n"
    exit 1
}

# Import certificate to keychain (this should trigger password prompt)
if security import "$TEMP_DIR/cert.p12" \
    -k "$KEYCHAIN_NAME" \
    -T /usr/bin/codesign \
    -T /usr/bin/security \
    -T /usr/bin/productbuild \
    -P "$TEMP_PASSWORD" \
    -A; then
    printf "${GREEN}✓${NC} Certificate imported successfully\n"
else
    printf "${RED}✗${NC} Failed to import certificate\n"
    printf "${YELLOW}Please ensure you entered the correct Mac login password${NC}\n"
    exit 1
fi

# Get the certificate SHA-1 hash for trust settings
printf "${YELLOW}   Getting certificate hash for trust settings...${NC}\n"
CERT_SHA1=$(security find-certificate -c "$CERT_NAME" -Z "$KEYCHAIN_NAME" 2>/dev/null | grep "SHA-1" | awk '{print $3}')
if [ -z "$CERT_SHA1" ]; then
    printf "${RED}✗${NC} Could not get certificate hash\n"
    exit 1
fi
printf "${GREEN}✓${NC} Certificate SHA-1: $CERT_SHA1\n"

# Set certificate trust for code signing
printf "${YELLOW}   Setting certificate trust (you may need to approve)...${NC}\n"
if sudo security add-trusted-cert -d -r trustRoot -k "$KEYCHAIN_NAME" \
    -p codeSign -p basic \
    "$TEMP_DIR/cert.pem"; then
    printf "${GREEN}✓${NC} Certificate trust set\n"
else
    printf "${YELLOW}⚠${NC}  Could not set trust automatically, trying manual trust settings...\n"
    # Try alternative method without sudo
    security trust-settings-import -d "$TEMP_DIR/cert.pem" 2>/dev/null || true
fi

# Wait a moment for keychain to update
sleep 1

# Debug: Check if certificate exists in keychain at all
printf "${YELLOW}   Checking if certificate exists in keychain...${NC}\n"
CERT_EXISTS=$(security find-certificate -a -c "$CERT_NAME" "$KEYCHAIN_NAME" 2>&1 | grep -c "labl" || echo "0")
if [ "$CERT_EXISTS" -gt 0 ]; then
    printf "${GREEN}✓${NC} Certificate found in keychain\n"
else
    printf "${RED}✗${NC} Certificate not found in keychain\n"
    exit 1
fi

# Debug: Show certificate details
printf "${YELLOW}   Certificate details:${NC}\n"
security find-certificate -c "$CERT_NAME" -p "$KEYCHAIN_NAME" 2>/dev/null | openssl x509 -noout -subject -ext extendedKeyUsage 2>/dev/null || true
printf "\n"

# Get certificate hash
printf "${YELLOW}   Looking for certificate in codesigning identities: $CERT_NAME${NC}\n"
printf "${YELLOW}   All codesigning identities:${NC}\n"
security find-identity -v -p codesigning
printf "\n"

CERT_HASH=$(security find-identity -v -p codesigning | grep "$CERT_NAME" | awk '{print $2}')

if [ -z "$CERT_HASH" ]; then
    # Try case-insensitive search
    CERT_HASH=$(security find-identity -v -p codesigning | grep -i "ido" | grep -i "development" | awk '{print $2}' | head -n1)
fi

if [ -z "$CERT_HASH" ]; then
    printf "${RED}✗${NC} Certificate imported but not recognized as codesigning identity\n"
    printf "${YELLOW}This might be due to missing private key association${NC}\n"
    printf "${YELLOW}Try: Open 'Keychain Access' > Find '$CERT_NAME' > Right-click > Get Info${NC}\n"
    exit 1
fi

printf "${GREEN}✓${NC} Found certificate hash: $CERT_HASH\n"

# Trust the certificate for code signing (may require password again)
printf "${YELLOW}   Setting certificate access control (may prompt for password again)...${NC}\n"
if security set-key-partition-list -S apple-tool:,apple:,codesign: \
    -s -k "$KEYCHAIN_NAME"; then
    printf "${GREEN}✓${NC} Certificate access control set\n"
else
    printf "${YELLOW}⚠${NC}  Could not set access control automatically\n"
    printf "${YELLOW}   You may need to grant access when signing${NC}\n"
fi

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
