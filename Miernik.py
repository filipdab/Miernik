import tkinter as tk
from tkinter import ttk
import psutil
import threading
import time
from pystray import Icon, Menu as TrayMenu, MenuItem as TrayItem
from PIL import Image, ImageDraw


class NetSpeedWidget:
    def __init__(self, root):
        self.root = root
        self.root.title("NetSpeed")
        self.root.geometry("220x60")
        self.root.overrideredirect(True)  # 🧱 Bez ramki
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.9)
        self.root.configure(bg="black")

        # Dane sieciowe
        self.interfaces = list(psutil.net_if_stats().keys())
        self.selected_interface = tk.StringVar(value=self.interfaces[0])

        # Widżety
        self.label_down = tk.Label(root, text="↓ -- Mbps", fg="lime", bg="black", font=("Segoe UI", 10))
        self.label_down.pack(pady=(5, 0))

        self.label_up = tk.Label(root, text="↑ -- Mbps", fg="cyan", bg="black", font=("Segoe UI", 10))
        self.label_up.pack()

        # Dane pomiarowe
        self.running = True
        self.prev_recv = 0
        self.prev_sent = 0
        self.prev_time = time.time()

        # Monitor w tle
        threading.Thread(target=self.monitor_loop, daemon=True).start()

        # Tray
        self.icon = None
        threading.Thread(target=self.setup_tray, daemon=True).start()

        # Zamknięcie (ukrycie tylko)
        self.root.protocol("WM_DELETE_WINDOW", self.hide_window)

        # Przeciąganie
        self.root.bind("<ButtonPress-1>", self.start_move)
        self.root.bind("<B1-Motion>", self.do_move)

    def monitor_loop(self):
        while self.running:
            try:
                counters = psutil.net_io_counters(pernic=True)
                iface = self.selected_interface.get()
                if iface in counters:
                    now = time.time()
                    stats = counters[iface]
                    recv = stats.bytes_recv
                    sent = stats.bytes_sent

                    if self.prev_recv:
                        delta = now - self.prev_time
                        down = (recv - self.prev_recv) * 8 / delta / 1_000_000
                        up = (sent - self.prev_sent) * 8 / delta / 1_000_000

                        self.label_down.config(text=f"↓ {down:.2f} Mbps")
                        self.label_up.config(text=f"↑ {up:.2f} Mbps")

                        if self.icon:
                            self.icon.title = f"{iface} | ↓ {down:.1f} Mbps ↑ {up:.1f} Mbps"

                    self.prev_recv = recv
                    self.prev_sent = sent
                    self.prev_time = now

                time.sleep(1)
            except Exception as e:
                self.label_down.config(text="Błąd")
                self.label_up.config(text=str(e))
                time.sleep(5)

    def setup_tray(self):
        image = self.create_tray_icon()

        # Menu interfejsów
        iface_menu = TrayMenu(
            *[TrayItem(
                iface,
                self.make_interface_selector(iface),
                checked=lambda item, iface=iface: iface == self.selected_interface.get(),
                radio=True
            ) for iface in self.interfaces]
        )

        # Tray menu
        menu = TrayMenu(
            TrayItem("Pokaż okno", self.show_window),
            TrayItem("Wybierz interfejs", iface_menu),
            TrayItem("Zamknij", self.quit_app)
        )

        self.icon = Icon("NetSpeed", image, "NetSpeed", menu)
        self.icon.run()

    def create_tray_icon(self):
        # Ikonka – prosta zielona kreska
        img = Image.new('RGB', (64, 64), color='black')
        draw = ImageDraw.Draw(img)
        draw.rectangle([10, 26, 54, 38], fill='green')
        return img

    def make_interface_selector(self, iface):
        def select(icon, item):
            self.selected_interface.set(iface)
            self.prev_recv = 0
            self.prev_sent = 0
        return select

    def hide_window(self):
        self.root.withdraw()

    def show_window(self, icon=None, item=None):
        self.root.deiconify()
        self.root.attributes("-topmost", True)

    def quit_app(self, icon=None, item=None):
        self.running = False
        if self.icon:
            self.icon.stop()
        self.root.destroy()

    # Możliwość przeciągania okna myszką
    def start_move(self, event):
        self._x = event.x
        self._y = event.y

    def do_move(self, event):
        x = event.x_root - self._x
        y = event.y_root - self._y
        self.root.geometry(f"+{x}+{y}")


if __name__ == "__main__":
    root = tk.Tk()
    app = NetSpeedWidget(root)
    root.mainloop()
