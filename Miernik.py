import tkinter as tk
from tkinter import ttk, messagebox, Menu
import psutil
import threading
import time
import json
import os
from pystray import Icon, Menu as TrayMenu, MenuItem as TrayItem
from PIL import Image, ImageDraw, ImageFont
import logging

# Konfiguracja logowania
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class NetSpeedWidget:
    CONFIG_FILE = "netspeed_config.json"
    DEFAULT_CONFIG = {
        "interface": "",
        "interval": 1.0,
        "units": "Mbps",
        "alpha": 0.9,
        "pos_x": 100,
        "pos_y": 100,
        "width": 220,
        "height": 60
    }
    MIN_WIDTH = 150  # Minimalna szerokość okna
    MIN_HEIGHT = 40  # Minimalna wysokość okna
    RESIZE_MARGIN = 5  # Margines (px) do wykrywania krawędzi dla zmiany rozmiaru
    AUTHOR_INFO = (
        "Autor: Filip Dąbrowski\n"
        "E-mail: filipdab@gmail.com\n"
        "Strona: soon..."
    )

    def __init__(self, root):
        self.root = root
        self.root.title("NetSpeed")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg="black")

        # Wczytanie konfiguracji
        self.config = self.load_config()
        self.root.attributes("-alpha", self.config["alpha"])
        self.root.geometry(
            f"{self.config['width']}x{self.config['height']}+{self.config['pos_x']}+{self.config['pos_y']}")

        # Dane sieciowe
        self.interfaces = []
        self.update_interfaces()
        self.selected_interface = tk.StringVar(
            value=self.config["interface"] or (self.interfaces[0] if self.interfaces else ""))
        self.units = tk.StringVar(value=self.config["units"])
        self.interval = tk.DoubleVar(value=self.config["interval"])
        self.lock = threading.Lock()

        # Widżety GUI
        self.label_down = tk.Label(root, text="↓ -- Mbps", fg="lime", bg="black", font=("Segoe UI", 10))
        self.label_down.pack(pady=(5, 0))
        self.label_up = tk.Label(root, text="↑ -- Mbps", fg="cyan", bg="black", font=("Segoe UI", 10))
        self.label_up.pack()

        # Dane pomiarowe
        self.running = True
        self.prev_recv = 0
        self.prev_sent = 0
        self.prev_time = time.time()

        # Wątek monitorujący
        threading.Thread(target=self.monitor_loop, daemon=True).start()

        # System tray
        self.icon = None
        self.tray_thread = None
        self.setup_tray()

        # Menu kontekstowe w oknie
        self.context_menu = Menu(self.root, tearoff=0)
        self.update_context_menu()
        self.root.bind("<Button-3>", self.show_context_menu)

        # Obsługa zamykania, przeciągania i zmiany rozmiaru
        self.root.protocol("WM_DELETE_WINDOW", self.hide_window)
        self.root.bind("<ButtonPress-1>", self.start_action)
        self.root.bind("<B1-Motion>", self.do_action)
        self.root.bind("<ButtonRelease-1>", self.stop_action)
        self.root.bind("<Motion>", self.update_cursor)

        # Zmienne do zmiany rozmiaru i przeciągania
        self.action = None
        self.start_x = 0
        self.start_y = 0
        self.start_width = 0
        self.start_height = 0
        self.start_pos_x = 0
        self.start_pos_y = 0

    def load_config(self):
        try:
            if os.path.exists(self.CONFIG_FILE):
                with open(self.CONFIG_FILE, 'r') as f:
                    return {**self.DEFAULT_CONFIG, **json.load(f)}
            return self.DEFAULT_CONFIG
        except Exception as e:
            logging.error(f"Błąd wczytywania konfiguracji: {e}")
            return self.DEFAULT_CONFIG

    def save_config(self):
        try:
            config = {
                "interface": self.selected_interface.get(),
                "interval": self.interval.get(),
                "units": self.units.get(),
                "alpha": self.config["alpha"],
                "pos_x": self.root.winfo_x(),
                "pos_y": self.root.winfo_y(),
                "width": self.root.winfo_width(),
                "height": self.root.winfo_height()
            }
            with open(self.CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=4)
        except Exception as e:
            logging.error(f"Błąd zapisywania konfiguracji: {e}")

    def update_interfaces(self):
        self.interfaces = list(psutil.net_if_stats().keys())
        if not self.interfaces:
            logging.warning("Brak dostępnych interfejsów sieciowych.")
            self.interfaces = ["Brak interfejsów"]

    def monitor_loop(self):
        while self.running:
            try:
                start_time = time.time()
                counters = psutil.net_io_counters(pernic=True)
                with self.lock:
                    iface = self.selected_interface.get()
                if not iface or iface not in counters:
                    if self.root.winfo_viewable():
                        self.label_down.config(text="↓ Brak interfejsu")
                        self.label_up.config(text="↑ Brak interfejsu")
                    time.sleep(5)
                    continue

                stats = counters[iface]
                recv = stats.bytes_recv
                sent = stats.bytes_sent

                if self.prev_recv:
                    delta = start_time - self.prev_time
                    factor = 8 / delta / (1_000_000 if self.units.get() == "Mbps" else 1_000)
                    down = (recv - self.prev_recv) * factor
                    up = (sent - self.prev_sent) * factor

                    if self.root.winfo_viewable():
                        unit = self.units.get()
                        self.label_down.config(text=f"↓ {down:.2f} {unit}")
                        self.label_up.config(text=f"↑ {up:.2f} {unit}")

                    if self.icon:
                        self.icon.title = f"{iface} | ↓ {down:.1f} {unit} ↑ {up:.1f} {unit}"
                        self.icon.icon = self.create_tray_icon(down)

                self.prev_recv = recv
                self.prev_sent = sent
                self.prev_time = start_time

                elapsed = time.time() - start_time
                sleep_time = max(0, self.interval.get() - elapsed)
                time.sleep(sleep_time)
            except Exception as e:
                if self.root.winfo_viewable():
                    self.label_down.config(text="Błąd")
                    self.label_up.config(text=str(e))
                self.prev_recv = self.prev_sent = 0
                self.prev_time = time.time()
                logging.error(f"Błąd w monitor_loop: {e}")
                time.sleep(5)

    def create_tray_icon(self, speed=0):
        img = Image.new('RGB', (64, 64), color='black')
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("arial.ttf", 20)
        except:
            font = None
        intensity = min(255, int(speed * 10))
        draw.rectangle([10, 26, 54, 38], fill=(0, intensity, 0))
        draw.text((10, 10), "NS", fill='lime', font=font)
        return img

    def setup_tray(self):
        if self.icon and self.tray_thread and self.tray_thread.is_alive():
            self.icon.stop()
        menu = self.create_tray_menu()
        self.icon = Icon("NetSpeed", self.create_tray_icon(), "NetSpeed", menu)
        self.tray_thread = threading.Thread(target=self.icon.run, daemon=True)
        self.tray_thread.start()

    def create_tray_menu(self):
        return TrayMenu(
            TrayItem("Pokaż/Ukryj okno", self.toggle_window),
            TrayItem("Wybierz interfejs", self.create_interface_menu),
            TrayItem("Jednostki", TrayMenu(
                TrayItem("Mbps", self.set_units("Mbps"), checked=lambda item: self.units.get() == "Mbps", radio=True),
                TrayItem("KB/s", self.set_units("KB/s"), checked=lambda item: self.units.get() == "KB/s", radio=True)
            )),
            TrayItem("Interwał (s)", TrayMenu(
                TrayItem("0.5", self.set_interval(0.5), checked=lambda item: self.interval.get() == 0.5, radio=True),
                TrayItem("1.0", self.set_interval(1.0), checked=lambda item: self.interval.get() == 1.0, radio=True),
                TrayItem("2.0", self.set_interval(2.0), checked=lambda item: self.interval.get() == 2.0, radio=True)
            )),
            TrayItem("Przeźroczystość", self.create_alpha_menu),
            TrayItem("Odśwież interfejsy", self.refresh_interfaces),
            TrayItem("O autorze", self.show_author_info),
            TrayItem("Zamknij", self.quit_app)
        )

    def create_interface_menu(self):
        self.update_interfaces()
        return TrayMenu(
            *[TrayItem(
                iface,
                self.make_interface_selector(iface),
                checked=lambda item, i=iface: i == self.selected_interface.get(),
                radio=True
            ) for iface in self.interfaces]
        )

    def create_alpha_menu(self):
        return TrayMenu(
            *[TrayItem(
                f"{alpha:.1f}",
                self.set_alpha(alpha),
                checked=lambda item, a=alpha: self.config["alpha"] == a,
                radio=True
            ) for alpha in [0.5, 0.7, 0.9, 1.0]]
        )

    def update_context_menu(self):
        self.context_menu.delete(0, tk.END)
        self.context_menu.add_command(label="Pokaż/Ukryj okno", command=self.toggle_window)
        self.context_menu.add_cascade(label="Wybierz interfejs", menu=self.create_tk_interface_menu())
        self.context_menu.add_cascade(label="Jednostki", menu=self.create_tk_units_menu())
        self.context_menu.add_cascade(label="Interwał (s)", menu=self.create_tk_interval_menu())
        self.context_menu.add_cascade(label="Przeźroczystość", menu=self.create_tk_alpha_menu())
        self.context_menu.add_command(label="Odśwież interfejsy", command=self.refresh_interfaces)
        self.context_menu.add_command(label="O autorze", command=self.show_author_info)
        self.context_menu.add_command(label="Zamknij", command=self.quit_app)

    def create_tk_interface_menu(self):
        menu = Menu(self.context_menu, tearoff=0)
        self.update_interfaces()
        for iface in self.interfaces:
            menu.add_radiobutton(
                label=iface,
                command=self.make_interface_selector(iface),
                variable=self.selected_interface,
                value=iface
            )
        return menu

    def create_tk_units_menu(self):
        menu = Menu(self.context_menu, tearoff=0)
        menu.add_radiobutton(label="Mbps", command=self.set_units("Mbps"), variable=self.units, value="Mbps")
        menu.add_radiobutton(label="KB/s", command=self.set_units("KB/s"), variable=self.units, value="KB/s")
        return menu

    def create_tk_interval_menu(self):
        menu = Menu(self.context_menu, tearoff=0)
        for interval in [0.5, 1.0, 2.0]:
            menu.add_radiobutton(
                label=str(interval),
                command=self.set_interval(interval),
                variable=self.interval,
                value=interval
            )
        return menu

    def create_tk_alpha_menu(self):
        menu = Menu(self.context_menu, tearoff=0)
        for alpha in [0.5, 0.7, 0.9, 1.0]:
            menu.add_radiobutton(
                label=f"{alpha:.1f}",
                command=self.set_alpha(alpha),
                variable=tk.DoubleVar(value=self.config["alpha"]),
                value=alpha
            )
        return menu

    def show_context_menu(self, event):
        self.update_context_menu()
        self.context_menu.post(event.x_root, event.y_root)

    def show_author_info(self):
        logging.info("Wyświetlono informacje o autorze")
        messagebox.showinfo("O autorze", self.AUTHOR_INFO)

    def make_interface_selector(self, iface):
        def select():
            logging.info(f"Wybrano interfejs: {iface}")
            with self.lock:
                self.selected_interface.set(iface)
                self.prev_recv = self.prev_sent = 0
                self.prev_time = time.time()
                self.save_config()

        return select

    def set_units(self, unit):
        def action():
            logging.info(f"Ustawiono jednostki: {unit}")
            self.units.set(unit)
            self.save_config()

        return action

    def set_interval(self, interval):
        def action():
            logging.info(f"Ustawiono interwał: {interval}")
            self.interval.set(interval)
            self.save_config()

        return action

    def set_alpha(self, alpha):
        def action():
            logging.info(f"Ustawiono przeźroczystość: {alpha}")
            self.config["alpha"] = alpha
            self.root.attributes("-alpha", alpha)
            self.save_config()
            if self.icon:
                self.icon.stop()
                self.setup_tray()

        return action

    def refresh_interfaces(self, icon=None, item=None):
        logging.info("Odświeżanie interfejsów sieciowych")
        with self.lock:
            old_iface = self.selected_interface.get()
            self.update_interfaces()
            if old_iface not in self.interfaces:
                self.selected_interface.set(self.interfaces[0] if self.interfaces else "")
                self.prev_recv = self.prev_sent = 0
                self.prev_time = time.time()
            if self.icon:
                self.icon.stop()
                self.setup_tray()
            self.save_config()

    def toggle_window(self):
        if self.root.winfo_viewable():
            self.hide_window()
        else:
            self.show_window()

    def hide_window(self):
        self.root.withdraw()
        self.save_config()

    def show_window(self, icon=None, item=None):
        self.root.deiconify()
        self.root.attributes("-topmost", True)

    def quit_app(self, icon=None, item=None):
        logging.info("Zamykanie aplikacji")
        self.running = False
        if self.icon:
            self.icon.stop()
        self.save_config()
        self.root.after(100, self.root.destroy)

    def update_cursor(self, event):
        x, y = event.x, event.y
        w, h = self.root.winfo_width(), self.root.winfo_height()
        margin = self.RESIZE_MARGIN

        if x >= w - margin and y >= h - margin:
            self.root.config(cursor="size_nw_se")
            self.action = "resize_se"
        elif x <= margin and y >= h - margin:
            self.root.config(cursor="size_ne_sw")
            self.action = "resize_sw"
        elif x >= w - margin and y <= margin:
            self.root.config(cursor="size_ne_sw")
            self.action = "resize_ne"
        elif x <= margin and y <= margin:
            self.root.config(cursor="size_nw_se")
            self.action = "resize_nw"
        else:
            self.root.config(cursor="arrow")
            self.action = "move"

    def start_action(self, event):
        self.start_x = event.x_root
        self.start_y = event.y_root
        self.start_width = self.root.winfo_width()
        self.start_height = self.root.winfo_height()
        self.start_pos_x = self.root.winfo_x()
        self.start_pos_y = self.root.winfo_y()

    def do_action(self, event):
        dx = event.x_root - self.start_x
        dy = event.y_root - self.start_y

        if self.action == "move":
            x = self.start_pos_x + dx
            y = self.start_pos_y + dy
            max_x = self.root.winfo_screenwidth() - self.root.winfo_width()
            max_y = self.root.winfo_screenheight() - self.root.winfo_height()
            x = max(0, min(x, max_x))
            y = max(0, min(y, max_y))
            self.root.geometry(f"+{x}+{y}")
        elif self.action in ("resize_se", "resize_sw", "resize_ne", "resize_nw"):
            new_width = self.start_width
            new_height = self.start_height
            new_x = self.start_pos_x
            new_y = self.start_pos_y

            if self.action in ("resize_se", "resize_ne"):
                new_width = max(self.MIN_WIDTH, self.start_width + dx)
            elif self.action in ("resize_sw", "resize_nw"):
                new_width = max(self.MIN_WIDTH, self.start_width - dx)
                new_x = self.start_pos_x + dx if new_width > self.MIN_WIDTH else self.start_pos_x

            if self.action in ("resize_se", "resize_sw"):
                new_height = max(self.MIN_HEIGHT, self.start_height + dy)
            elif self.action in ("resize_ne", "resize_nw"):
                new_height = max(self.MIN_HEIGHT, self.start_height - dy)
                new_y = self.start_pos_y + dy if new_height > self.MIN_HEIGHT else self.start_pos_y

            self.root.geometry(f"{new_width}x{new_height}+{new_x}+{new_y}")

            font_size = max(8, min(12, int(new_height / 4)))
            self.label_down.config(font=("Segoe UI", font_size))
            self.label_up.config(font=("Segoe UI", font_size))

    def stop_action(self, event):
        self.save_config()


if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = NetSpeedWidget(root)
        root.mainloop()
    except Exception as e:
        logging.critical(f"Błąd uruchamiania aplikacji: {e}")
        messagebox.showerror("NetSpeed Error", f"Błąd uruchamiania: {e}")