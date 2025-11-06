"""
Quick script to enable friendly chat feature
Configures the settings in database
"""

import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from config.loader import ConfigLoader
from core.db import get_db
from core.settings import get_settings, init_settings


def enable_friendly_chat():
    """Enable friendly chat feature with recommended settings"""
    print("=" * 60)
    print("Enabling Friendly Chat Feature")
    print("=" * 60)

    # Initialize
    print("\nInitializing...")
    config_loader = ConfigLoader()
    config_loader.load()

    db = get_db()
    init_settings(config_loader, db)
    settings = get_settings()
    print("✓ Settings manager initialized")

    # Show current settings
    print("\nCurrent friendly_chat settings:")
    current = settings.get_friendly_chat_settings()
    for key, value in current.items():
        print(f"  • {key}: {value}")

    # Enable friendly chat
    print("\nEnabling friendly chat...")
    updates = {
        "enabled": True,  # Enable the feature
        "interval": 20,  # Trigger every 20 minutes
        "data_window": 20,  # Look at last 20 minutes of activity
        "enable_system_notification": True,  # Enable system notifications
        "enable_live2d_display": True,  # Enable Live2D display
    }

    updated = settings.update_friendly_chat_settings(updates)
    print("✓ Friendly chat enabled!")

    print("\nNew settings:")
    for key, value in updated.items():
        print(f"  • {key}: {value}")

    # Also enable Live2D if not already enabled
    print("\nChecking Live2D settings...")
    live2d_settings = settings.get_live2d_settings()
    if not live2d_settings.get("enabled"):
        print("Live2D is disabled, enabling it...")
        settings.update_live2d_settings({"enabled": True})
        print("✓ Live2D enabled!")
    else:
        print("✓ Live2D is already enabled")

    print("\n" + "=" * 60)
    print("✅ Configuration Complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("  1. Restart the application")
    print("  2. Start using the app normally")
    print("  3. Wait 20 minutes for the first chat message")
    print("  4. Or click 'Manual Trigger' in settings to test immediately")
    print("\nYou should now receive:")
    print("  • Live2D dialog messages (5 second display)")
    print("  • System notifications")
    print("\nBoth will appear every 20 minutes based on your recent activity.")


if __name__ == "__main__":
    try:
        enable_friendly_chat()
    except Exception as e:
        print(f"\n❌ Failed to enable friendly chat: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
