"""Run this once to see exact key names reported by the keyboard library.
Press keys you want to use, then Ctrl+C to exit."""
import keyboard

print("Press keys to see their names. Ctrl+C to exit.\n")

def on_key(event):
    print(f"  type={event.event_type:8s}  name={event.name!r:20s}  scan={event.scan_code}")

keyboard.hook(on_key)
keyboard.wait()
