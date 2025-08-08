import psutil
import time
import threading
import tkinter as tk
from tkinter import ttk
import ttkbootstrap as tb
from ttkbootstrap.constants import *
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Funkcja do pobierania danych systemowych
def get_stats():
    net_io_start = psutil.net_io_counters(pernic=True)
    disk_io_start = psutil.disk_io_counters()
    time.sleep(1)
    net_io_end = psutil.net_io_counters(pernic=True)
    disk_io_end = psutil.disk_io_counters()

    net_speeds = {}
    for iface in net_io_start:
        sent_speed = (net_io_end[iface].bytes_sent - net_io_start[iface].bytes_sent) / 1024
        recv_speed = (net_io_end[iface].bytes_recv - net_io_start[iface].bytes_recv) / 1024
        net_speeds[iface] = (sent_speed, recv_speed)

    cpu_percent = psutil.cpu_percent()
    mem_percent = psutil.virtual_memory().percent
    disk_percent = psutil.disk_usage('/').percent
    disk_read_speed = (disk_io_end.read_bytes - disk_io_start.read_bytes) / 1024
    disk_write_speed = (disk_io_end.write_bytes - disk_io_start.write_bytes) / 1024

    return net_speeds, cpu_percent, mem_percent, disk_percent, disk_read_speed, disk_write_speed

# Aktualizacja GUI
def update_stats():
    net_speeds, cpu_percent, mem_percent, disk_percent, disk_read_speed, disk_write_speed = get_stats()

    cpu_label.config(text=f"CPU: {cpu_percent:.1f}%")
    mem_label.config(text=f"RAM: {mem_percent:.1f}%")
    disk_label.config(text=f"Dysk: {disk_percent:.1f}% ({disk_read_speed:.1f} KB/s odczyt, {disk_write_speed:.1f} KB/s zapis)")

    for widget in net_frame.winfo_children():
        widget.destroy()
    for iface, (sent, recv) in net_speeds.items():
        ttk.Label(net_frame, text=f"{iface}: ↑ {sent:.1f} KB/s   ↓ {recv:.1f} KB/s").pack(anchor="w")

    # Wykres CPU
    cpu_data.append(cpu_percent)
    cpu_data.pop(0)
    ax.clear()
    ax.plot(cpu_data, color="blue")
    ax.set_ylim(0, 100)
    ax.set_ylabel("CPU %")
    canvas.draw()

    root.after(1000, update_stats)

# Uruchomienie wątku do aktualizacji
def start_monitoring():
    threading.Thread(target=update_stats).start()

# Tworzenie okna
root = tb.Window(themename="cyborg")
root.title("System Monitor")
root.geometry("700x500")

# Etykiety główne
cpu_label = ttk.Label(root, text="CPU: 0%", font=("Segoe UI", 12))
cpu_label.pack(anchor="w", pady=2)
mem_label = ttk.Label(root, text="RAM: 0%", font=("Segoe UI", 12))
mem_label.pack(anchor="w", pady=2)
disk_label = ttk.Label(root, text="Dysk: 0%", font=("Segoe UI", 12))
disk_label.pack(anchor="w", pady=2)

# Sekcja sieci
ttk.Label(root, text="Interfejsy sieciowe:", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=4)
net_frame = ttk.Frame(root)
net_frame.pack(fill="x", padx=10)

# Wykres CPU
cpu_data = [0] * 60
fig, ax = plt.subplots(figsize=(5, 2))
ax.plot(cpu_data)
ax.set_ylim(0, 100)
ax.set_ylabel("CPU %")

canvas = FigureCanvasTkAgg(fig, master=root)
canvas.get_tk_widget().pack(pady=10)

# Start monitoringu
root.after(1000, update_stats)
root.mainloop()
