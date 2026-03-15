"""System tray icon using pystray."""
import threading
from PIL import Image, ImageDraw
import pystray

from app_state import AppState, Status

# Color per status
STATUS_TRAY_COLOR = {
    Status.LOADING:      "#888888",
    Status.IDLE:         "#4CAF50",
    Status.RECORDING:    "#F44336",
    Status.TRANSCRIBING: "#FF9800",
}


def _make_icon(color: str = "#4CAF50") -> Image.Image:
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse((4, 4, 60, 60), fill=color)
    return img


class TrayIcon:
    def __init__(self, state: AppState, on_show_window, on_quit):
        self.state = state
        self.on_show_window = on_show_window
        self.on_quit = on_quit
        self._icon: pystray.Icon | None = None

        state.on_status_change(self._update_icon_color)

    def start(self):
        menu = pystray.Menu(
            pystray.MenuItem("Open Voice Tool", self._open, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", self._quit),
        )
        self._icon = pystray.Icon(
            "voice_tool",
            icon=_make_icon(),
            title="Voice Tool",
            menu=menu,
        )
        # Run in its own thread so it doesn't block tkinter
        threading.Thread(target=self._icon.run, daemon=True).start()

    def _open(self, icon, item):
        self.on_show_window()

    def _quit(self, icon, item):
        icon.stop()
        self.on_quit()

    def _update_icon_color(self, status: Status):
        if self._icon is None:
            return
        color = STATUS_TRAY_COLOR.get(status, "#888888")
        self._icon.icon = _make_icon(color)
