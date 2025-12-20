#!/bin/bash

# Create Self-Signed Certificate for macOS Code Signing
# This ensures consistent signing across builds to preserve permissions

set -e

CERT_NAME="iDO Development Signing"
KEYCHAIN_PASSWORD="temp_password_$(openssl rand -hex 8)"
P12_PASSWORD=${1:-"ido_signing_2024"}

echo "🔐 Creating self-signed certificate for iDO code signing..."
echo ""

# Create a temporary keychain
TEMP_KEYCHAIN="$HOME/Library/Keychains/ido-temp.keychain-db"
echo "📦 Creating temporary keychain..."
security create-keychain -p "$KEYCHAIN_PASSWORD" "$TEMP_KEYCHAIN"
security set-keychain-settings -lut 21600 "$TEMP_KEYCHAIN"
security unlock-keychain -p "$KEYCHAIN_PASSWORD" "$TEMP_KEYCHAIN"

# Generate certificate
echo "🔑 Generating certificate..."
cat > cert-config.txt <<EOF
[ req ]
default_bits       = 2048
distinguished_name = req_distinguished_name
x509_extensions    = v3_ca
prompt             = no

[ req_distinguished_name ]
C  = US
ST = California
L  = San Francisco
O  = iDO Development
OU = Engineering
CN = $CERT_NAME

[ v3_ca ]
basicConstraints       = critical,CA:TRUE
keyUsage              = critical,keyCertSign,cRLSign,digitalSignature
subjectKeyIdentifier  = hash
authorityKeyIdentifier = keyid:always,issuer:always
codeSigning           = critical,codeSigning
EOF

# Create certificate and key
openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
    -keyout ido-signing-key.pem \
    -out ido-signing-cert.pem \
    -config cert-config.txt

# Convert to PKCS12
echo "📦 Creating PKCS12 bundle..."
openssl pkcs12 -export \
    -out ido-signing.p12 \
    -inkey ido-signing-key.pem \
    -in ido-signing-cert.pem \
    -password pass:$P12_PASSWORD \
    -name "$CERT_NAME"

# Import to keychain
echo "📥 Importing to keychain..."
security import ido-signing.p12 \
    -k "$TEMP_KEYCHAIN" \
    -P "$P12_PASSWORD" \
    -T /usr/bin/codesign \
    -T /usr/bin/productbuild

# Set certificate as trusted for code signing
security add-trusted-cert -d -r trustRoot -k "$TEMP_KEYCHAIN" ido-signing-cert.pem

# Move to login keychain
echo "🔄 Moving certificate to login keychain..."
security import ido-signing.p12 \
    -k "$HOME/Library/Keychains/login.keychain-db" \
    -P "$P12_PASSWORD" \
    -T /usr/bin/codesign \
    -T /usr/bin/productbuild

security add-trusted-cert -d -r trustRoot \
    -k "$HOME/Library/Keychains/login.keychain-db" \
    ido-signing-cert.pem

# Set partition list
security set-key-partition-list -S apple-tool:,apple:,codesign: -s \
    -k "$KEYCHAIN_PASSWORD" "$TEMP_KEYCHAIN" || true

# Clean up temp files
rm -f ido-signing-key.pem ido-signing-cert.pem cert-config.txt
rm -f "$TEMP_KEYCHAIN"

# Encode for GitHub Secrets
echo "🔒 Encoding certificate for GitHub Secrets..."
CERT_BASE64=$(base64 -i ido-signing.p12)

echo ""
echo "✅ Certificate created successfully!"
echo ""
echo "📋 Next steps:"
echo ""
echo "1. Add the following secrets to your GitHub repository:"
echo "   Settings → Secrets and variables → Actions → New repository secret"
echo ""
echo "   Secret: APPLE_CERTIFICATE"
echo "   Value:"
echo "   ----------------------------------------"
echo "$CERT_BASE64"
echo "   ----------------------------------------"
echo ""
echo "   Secret: APPLE_CERTIFICATE_PASSWORD"
echo "   Value: $P12_PASSWORD"
echo ""
echo "   Secret: APPLE_SIGNING_IDENTITY"
echo "   Value: iDO Development Signing"
echo ""
echo "2. The certificate file 'ido-signing.p12' has been saved."
echo "   Keep this file safe - you'll need it for local builds too."
echo ""
echo "3. To find the certificate identity for local use:"
echo "   security find-identity -p codesigning -v"
echo ""
echo "💡 After setting up GitHub Secrets, all releases will use"
echo "   the same certificate, preserving macOS permissions across updates."
echo ""
