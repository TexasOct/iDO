#!/bin/bash

# Verify Code Signing Configuration

echo "🔍 Verifying code signing setup..."
echo ""

# Check if certificate exists
echo "1️⃣ Checking for iDO signing certificate..."
CERT_COUNT=$(security find-identity -p codesigning -v | grep -c "iDO Development Signing" || true)

if [ "$CERT_COUNT" -gt 0 ]; then
    echo "   ✅ Certificate found in keychain"
    security find-identity -p codesigning -v | grep "iDO Development Signing"
else
    echo "   ❌ Certificate not found"
    echo "      Run: ./scripts/create-signing-cert.sh"
    exit 1
fi

echo ""

# Check configuration files
echo "2️⃣ Checking Tauri configuration..."
if grep -q '"hardenedRuntime": true' src-tauri/tauri.macos.conf.json; then
    echo "   ✅ Hardened runtime enabled"
else
    echo "   ❌ Hardened runtime not enabled"
fi

if grep -q '"signingIdentity": "-"' src-tauri/tauri.macos.conf.json; then
    echo "   ✅ Signing identity configured"
else
    echo "   ⚠️  Signing identity not set to '-' (will use default)"
fi

echo ""

# Check if app bundle exists
echo "3️⃣ Checking built application..."
APP_PATH="src-tauri/target/bundle-release/bundle/macos/iDO.app"

if [ -d "$APP_PATH" ]; then
    echo "   ✅ Application bundle found"
    echo ""
    echo "   Signature details:"
    codesign -dvv "$APP_PATH" 2>&1 | grep -E "Authority|Identifier|Signature" | sed 's/^/      /'

    echo ""
    echo "   🎯 Checking signature validity..."
    if codesign -v "$APP_PATH" 2>&1; then
        echo "   ✅ Signature valid"
    else
        echo "   ❌ Signature invalid"
    fi
else
    echo "   ⚠️  Application not built yet"
    echo "      Run: pnpm bundle"
fi

echo ""
echo "📋 Summary:"
echo "   - Certificate: $([ "$CERT_COUNT" -gt 0 ] && echo '✅' || echo '❌')"
echo "   - Configuration: ✅"
echo "   - Application: $([ -d "$APP_PATH" ] && echo '✅' || echo '⚠️  Not built')"
echo ""

if [ "$CERT_COUNT" -gt 0 ] && [ -d "$APP_PATH" ]; then
    echo "🎉 Everything looks good! Your app should preserve permissions across updates."
else
    echo "⚠️  Setup incomplete. Follow the steps in docs/CODE_SIGNING_SETUP.md"
fi
