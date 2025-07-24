import tkinter as tk
from tkinter import ttk
import psutil
import threading
import time

class NetSpeedWidget:
    def __init__(self, root):
        self.root = root
        self.root.title("Monitor sieci")
        self.root.geometry("300x200")
        self.root.resizable(False, False)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.90)

        style = ttk.Style()
        style.configure("TLabel", font=("Segoe UI", 11))
        style.configure("TButton", font=("Segoe UI", 10))

        # Lista interfejsów
        self.interfaces = list(psutil.net_if_stats().keys())
        self.selected_interface = tk.StringVar(value=self.interfaces[0])

        ttk.Label(root, text="Wybierz interfejs:").pack(pady=(10, 0))
        self.interface_dropdown = ttk.Combobox(root, values=self.interfaces, textvariable=self.selected_interface, state="readonly")
        self.interface_dropdown.pack(pady=5)

        self.start_button = ttk.Button(root, text="Start monitorowania", command=self.start_monitoring)
        self.start_button.pack(pady=5)

        self.label_down = ttk.Label(root, text="Pobieranie: -- Mbps")
        self.label_down.pack(pady=5)

        self.label_up = ttk.Label(root, text="Wysyłanie: -- Mbps")
        self.label_up.pack()

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
                        down_speed = (recv - prev_recv) * 8 / delta_time / 1_000_000  # Mbps
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
        # Zatrzymaj ewentualny poprzedni monitoring
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1)

        # Uruchom nowy monitoring
        interface = self.selected_interface.get()
        self.running = True
        self.monitor_thread = threading.Thread(target=self.monitor, args=(interface,), daemon=True)
        self.monitor_thread.start()

    def stop(self):
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1)

# 🟢 Start aplikacji
if __name__ == "__main__":
    root = tk.Tk()
    app = NetSpeedWidget(root)
    root.protocol("WM_DELETE_WINDOW", lambda: (app.stop(), root.destroy()))
    root.mainloop()
