# macOS Code Signing Setup for GitHub Actions

This document explains how to configure code signing for macOS builds in GitHub Actions.

## Overview

The project uses Tauri's built-in certificate handling for macOS code signing. Tauri will automatically import and use certificates when the appropriate environment variables are set.

## Required GitHub Secrets

Configure the following secrets in your repository settings (`Settings > Secrets and variables > Actions`):

### Required for Code Signing

- **`APPLE_CERTIFICATE`** - Base64-encoded `.p12` certificate file
- **`APPLE_CERTIFICATE_PASSWORD`** - Password for the `.p12` certificate
- **`APPLE_SIGNING_IDENTITY`** - Certificate name (e.g., `Developer ID Application: Your Name (TEAM_ID)`)

### Optional for Notarization

- **`APPLE_ID`** - Your Apple ID email
- **`APPLE_PASSWORD`** - App-specific password for your Apple ID
- **`APPLE_TEAM_ID`** - Your Apple Developer Team ID

## How to Export Your Certificate

### Step 1: Export from Keychain

1. Open **Keychain Access** on your Mac
2. Navigate to the **"My Certificates"** tab in your login keychain
3. Find your **"Developer ID Application"** certificate
4. Expand the certificate to see the private key
5. **Right-click** on the certificate (not the key) and select **"Export"**
6. Save as `.p12` format
7. Set a strong password when prompted
8. Save the file (e.g., `certificate.p12`)

### Step 2: Convert to Base64

Run this command in Terminal:

```bash
openssl base64 -in certificate.p12 -out certificate-base64.txt
```

The output file `certificate-base64.txt` contains your base64-encoded certificate.

### Step 3: Add to GitHub Secrets

1. Go to your repository on GitHub
2. Navigate to **Settings > Secrets and variables > Actions**
3. Click **"New repository secret"**
4. Add each secret:
   - Name: `APPLE_CERTIFICATE`
   - Value: Paste the contents of `certificate-base64.txt`
   - Click **"Add secret"**

5. Repeat for other secrets:
   - `APPLE_CERTIFICATE_PASSWORD`: The password you set when exporting
   - `APPLE_SIGNING_IDENTITY`: Your certificate name (see below)

### Step 4: Find Your Signing Identity

To find your certificate name, run:

```bash
security find-identity -v -p codesigning
```

Look for a line like:

```
1) ABC123DEF456 "Developer ID Application: Your Name (TEAM_ID)"
```

Your **`APPLE_SIGNING_IDENTITY`** is the full name in quotes, or just the Team ID in parentheses (e.g., `TEAM_ID`).

## How It Works

1. **GitHub Actions** provides the secrets as environment variables
2. **Tauri CLI** automatically detects these variables during build
3. **Tauri** imports the certificate into a temporary keychain
4. **Tauri** signs the application during the build process
5. **Custom signing script** (`sign-macos.sh`) performs additional signing if needed
6. **DMG creation** uses the signed `.app` bundle

## CI Behavior

- **With secrets configured**: Full code signing with your Developer ID certificate
- **Without secrets**: Skips signing in CI (relies on Tauri's default behavior)
- **Local development**: Uses local certificates or adhoc signing

## Notarization (Optional)

For notarization, you'll need:

1. **App-specific password**: Generate at [appleid.apple.com](https://appleid.apple.com)
2. Add these additional secrets:
   - `APPLE_ID`: Your Apple ID email
   - `APPLE_PASSWORD`: The app-specific password
   - `APPLE_TEAM_ID`: Your 10-character Team ID

Tauri will automatically notarize the app if these are provided.

## Troubleshooting

### Build fails with "Unable to decode the provided data"

- Check that `APPLE_CERTIFICATE` is properly base64-encoded
- Verify the secret doesn't have extra whitespace or newlines

### Build fails with "No identity found"

- Verify `APPLE_SIGNING_IDENTITY` matches your certificate name exactly
- Try using just the Team ID instead of the full name

### Certificate not found in keychain

- Tauri handles certificate import automatically
- Ensure `APPLE_CERTIFICATE` and `APPLE_CERTIFICATE_PASSWORD` are both set

## References

- [Tauri macOS Code Signing Guide](https://v2.tauri.app/distribute/sign/macos/)
- [Apple Developer Documentation](https://developer.apple.com/support/code-signing/)
- [GitHub Actions Secrets](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
