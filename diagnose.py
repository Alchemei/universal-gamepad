"""Diagnostic script — dumps all pydualsense state attributes."""
from pydualsense import pydualsense
import time

ds = pydualsense()
ds.init()
print("DualSense connected! Press L2/R2 triggers and buttons...")
print("=" * 60)

try:
    for i in range(10):
        time.sleep(1)
        state = ds.state
        attrs = {k: v for k, v in vars(state).items() if not k.startswith('_')}
        
        # Print all attributes grouped
        print(f"\n--- Read #{i+1} ---")
        for name, val in sorted(attrs.items()):
            vtype = type(val).__name__
            # Highlight non-default values
            highlight = ""
            if isinstance(val, bool) and val:
                highlight = " <<<< PRESSED"
            elif isinstance(val, (int, float)) and val != 0 and val != -1:
                highlight = f" <<<< ACTIVE"
            print(f"  {name:20s} = {val!r:>10s}  ({vtype}){highlight}")
except KeyboardInterrupt:
    pass
finally:
    ds.close()
    print("\nDone.")
