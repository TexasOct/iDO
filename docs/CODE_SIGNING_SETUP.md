# macOS Code Signing Setup

## Problem

When updating iDO on macOS, the system may ask for Accessibility and Screen Recording permissions again. This happens because each build has a different code signature, making macOS think it's a different application.

## Solution

Use a **consistent self-signed certificate** for all builds. This ensures macOS recognizes updates as the same application and preserves permissions.

---

## Quick Setup (5 minutes)

### Step 1: Generate Certificate

Run the certificate generation script:

```bash
cd scripts
./create-signing-cert.sh
```

This will:

- Create a self-signed certificate named "iDO Development Signing"
- Install it in your macOS keychain
- Generate a `.p12` file for GitHub Actions
- Output the secrets you need to add to GitHub

### Step 2: Add GitHub Secrets

1. Go to your repository on GitHub
2. Navigate to: **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add these three secrets (values provided by the script):
   - `APPLE_CERTIFICATE` - The base64-encoded certificate
   - `APPLE_CERTIFICATE_PASSWORD` - The password for the certificate
   - `APPLE_SIGNING_IDENTITY` - The certificate name (`iDO Development Signing`)

### Step 3: Done!

That's it! All future builds (both local and CI/CD) will now use the same certificate, preserving macOS permissions across updates.

---

## How It Works

### Before (Adhoc Signing)

```
Build 1: Adhoc Signature A → macOS grants permissions
Build 2: Adhoc Signature B → macOS sees different app → asks for permissions again ❌
```

### After (Consistent Signing)

```
Build 1: Certificate Signature → macOS grants permissions
Build 2: Certificate Signature → macOS sees same app → keeps permissions ✅
```

---

## Verification

### Check Local Certificate

```bash
# List all code signing certificates
security find-identity -p codesigning -v

# Should show: "iDO Development Signing"
```

### Check Signed Application

```bash
# After building locally
codesign -dvv src-tauri/target/bundle-release/bundle/macos/iDO.app

# Should show:
# Signature=adhoc → ❌ Wrong (won't preserve permissions)
# Authority=iDO Development Signing → ✅ Correct
```

---

## Troubleshooting

### "Certificate not found" during build

Make sure the certificate is in your login keychain:

```bash
security list-keychains
security find-identity -p codesigning -v
```

If missing, re-run the setup script.

### GitHub Actions failing to sign

Verify secrets are correctly set:

1. Check that `APPLE_CERTIFICATE` contains the full base64 string
2. Check that `APPLE_CERTIFICATE_PASSWORD` matches the password you set
3. Check workflow logs for detailed error messages

### Different certificate on different machines

All developers should use the **same** `.p12` file. Share `ido-signing.p12` securely with your team (don't commit it to git).

---

## Security Notes

1. **Self-signed certificates are fine** for this use case - you're not distributing through the App Store
2. Keep `ido-signing.p12` safe - store it in a secure location (password manager, encrypted storage)
3. The certificate password is only for protecting the `.p12` file, not critical security
4. Users will see a "developer cannot be verified" warning on first launch - this is normal for self-signed apps

---

## Advanced: Using Apple Developer Certificate

If you have an Apple Developer account ($99/year), you can use an official certificate:

1. Get your Developer ID Application certificate from Apple
2. Export it as `.p12` from Keychain Access
3. Use the same GitHub Secrets setup as above
4. Your app can then be notarized for a smoother user experience

---

## Summary

✅ **What this solves:**

- Permissions preserved across updates
- Consistent signing for all builds
- No more "grant access" prompts after updates

❌ **What this doesn't solve:**

- First-launch security warnings (requires Apple Developer certificate + notarization)
- App Store distribution (requires Apple Developer account)

For most users, the self-signed certificate approach is perfect and free!
