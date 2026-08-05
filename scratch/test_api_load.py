import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    print("[*] Testing API import...")
    import src.api
    print("[✓] API module loaded successfully!")
except Exception as e:
    import traceback
    print("[✗] Error loading API:")
    traceback.print_exc()
