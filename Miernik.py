import tkinter as tk
from tkinter import ttk, Menu
import psutil
import threading
import time

class NetSpeedWidget:
    def __init__(self, root):
        self.root = root
        self.root.title("📡 NetMonitor")
        self.root.geometry("220x80")
        self.root.resizable(False, False)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.90)

        # Styl
        style = ttk.Style()
        style.configure("TLabel", font=("Segoe UI", 10))

        # Etykiety
        self.label_down = ttk.Label(root, text="Pobieranie: -- Mbps")
        self.label_down.pack(pady=(10, 0))

        self.label_up = ttk.Label(root, text="Wysyłanie: -- Mbps")
        self.label_up.pack()

        # Interfejsy
        self.interfaces = list(psutil.net_if_stats().keys())
        self.selected_interface = tk.StringVar(value=self.interfaces[0])

        # Menu
        menubar = Menu(root)
        settings_menu = Menu(menubar, tearoff=0)

        interface_submenu = Menu(settings_menu, tearoff=0)
        for iface in self.interfaces:
            interface_submenu.add_radiobutton(label=iface, variable=self.selected_interface, value=iface, command=self.restart_monitoring)

        settings_menu.add_cascade(label="Wybierz interfejs", menu=interface_submenu)
        settings_menu.add_separator()
        settings_menu.add_command(label="Start monitorowania", command=self.start_monitoring)
        settings_menu.add_command(label="Zatrzymaj monitorowanie", command=self.stop)
        settings_menu.add_separator()
        settings_menu.add_command(label="Zamknij", command=self.close_app)

        menubar.add_cascade(label="Ustawienia", menu=settings_menu)
        root.config(menu=menubar)

        self.monitor_thread = None
        self.running = False

    def monitor(self, interface_name):
        prev_recv = 0
        prev_sent = 0
        prev_time = time.time()

        while self.running:
            try:
                counters = psutil.net_io_counters(pernic=True)
                if interface_name in counters:
                    now = time.time()
                    stats = counters[interface_name]
                    recv = stats.bytes_recv
                    sent = stats.bytes_sent

                    if prev_recv != 0:
                        delta_time = now - prev_time
                        down_speed = (recv - prev_recv) * 8 / delta_time / 1_000_000
                        up_speed = (sent - prev_sent) * 8 / delta_time / 1_000_000

                        self.label_down.config(text=f"Pobieranie: {down_speed:.2f} Mbps")
                        self.label_up.config(text=f"Wysyłanie: {up_speed:.2f} Mbps")

                    prev_recv = recv
                    prev_sent = sent
                    prev_time = now

                time.sleep(1)
            except Exception as e:
                self.label_down.config(text="Błąd")
                self.label_up.config(text=str(e))
                break

    def start_monitoring(self):
        self.stop()
        interface = self.selected_interface.get()
        self.running = True
        self.monitor_thread = threading.Thread(target=self.monitor, args=(interface,), daemon=True)
        self.monitor_thread.start()

    def restart_monitoring(self):
        if self.running:
            self.start_monitoring()

    def stop(self):
        self.running = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=1)

    def close_app(self):
        self.stop()
        self.root.destroy()

# 🔌 Start
if __name__ == "__main__":
    root = tk.Tk()
    app = NetSpeedWidget(root)
    root.protocol("WM_DELETE_WINDOW", app.close_app)
    root.mainloop()
