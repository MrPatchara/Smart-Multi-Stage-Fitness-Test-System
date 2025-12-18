import asyncio
import tkinter as tk
from bleak import BleakClient, BleakScanner
from datetime import datetime
import statistics
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.animation import FuncAnimation
import numpy as np
from scipy.signal import welch
import threading

HR_SERVICE_UUID = "0000180d-0000-1000-8000-00805f9b34fb"
HR_CHAR_UUID = "00002a37-0000-1000-8000-00805f9b34fb"

rri_list = []
fft_freq = []
fft_power = []
connected = False

# GUI setup
root = tk.Tk()
root.title("Polar H10 HRV Monitor")
root.geometry("800x900")

hr_label = tk.Label(root, text="HR: - bpm", font=("Arial", 16))
hr_label.pack(pady=5)
rri_label = tk.Label(root, text="RRi: - ms", font=("Arial", 14))
rri_label.pack(pady=2)

# HRV Summary Block
tk.Label(root, text="HRV Metrics", font=("Arial", 14, "bold")).pack(pady=5)
rmssd_label = tk.Label(root, text="RMSSD: - ms", font=("Arial", 12))
rmssd_label.pack()
sdnn_label = tk.Label(root, text="SDNN: - ms", font=("Arial", 12))
sdnn_label.pack()
pnn50_label = tk.Label(root, text="pNN50: - %", font=("Arial", 12))
pnn50_label.pack()
lfhf_label = tk.Label(root, text="LF/HF Ratio: -", font=("Arial", 12))
lfhf_label.pack()

interpretation_label = tk.Label(root, text="Interpretation: -", font=("Arial", 12, "bold"), fg="blue")
interpretation_label.pack(pady=5)

status_label = tk.Label(root, text="Status: Not connected", fg="red")
status_label.pack(pady=5)

# ECG-like + FFT plot
fig, (ax, ax_fft) = plt.subplots(2, 1, figsize=(6, 4), dpi=100, gridspec_kw={'height_ratios': [2, 1]})
fig.tight_layout(pad=3.0)

ecglines, = ax.plot([], [], lw=1.5, color="blue")
ax.set_title("ECG-like RRi Plot")
ax.set_xlabel("Time (s)")
ax.set_ylabel("RRi (ms)")
ax.set_ylim(200, 1600)
ax.set_xlim(0, 60)

canvas = FigureCanvasTkAgg(fig, master=root)
canvas.get_tk_widget().pack()

def update_ecg_plot(i):
    if len(rri_list) >= 2:
        times = np.cumsum([r / 1000 for r in rri_list[-100:]])
        rr_vals = rri_list[-100:]
        ecglines.set_data(times, rr_vals)
        ax.set_xlim(times[0], times[-1])
        ax.set_ylim(min(rr_vals) - 50, max(rr_vals) + 50)

    ax_fft.clear()
    ax_fft.set_title("Power Spectrum (LF / HF)")
    ax_fft.set_xlabel("Frequency (Hz)")
    ax_fft.set_ylabel("Power")
    if len(fft_freq) > 0 and len(fft_power) > 0:
        ax_fft.bar(fft_freq, fft_power, width=0.01, color="gray")
        ax_fft.set_xlim(0, 0.5)

    return ecglines,

ani = FuncAnimation(fig, update_ecg_plot, interval=1000, blit=False, cache_frame_data=False)

# BLE connect and notify
async def connect_and_monitor():
    global connected
    devices = await BleakScanner.discover()
    target = None
    for d in devices:
        if d.name and d.name.startswith("Polar H10"):
            target = d
            break

    if not target:
        status_label.config(text="Status: Polar H10 not found", fg="red")
        return

    client = BleakClient(target)
    try:
        await client.connect()
        status_label.config(text=f"Connected to {target.name}", fg="green")
        await client.start_notify(HR_CHAR_UUID, notification_handler)
        connected = True
        while connected:
            await asyncio.sleep(1)
    except Exception as e:
        status_label.config(text=f"Connection error: {e}", fg="red")
    finally:
        try:
            await client.disconnect()
        except:
            pass

def notification_handler(sender, data):
    flags = data[0]
    hr_value = data[1]
    hr_label.config(text=f"HR: {hr_value} bpm")

    index = 2
    rri_values = []
    if flags & 0b00010000:
        while index + 1 < len(data):
            rr = int.from_bytes(data[index:index+2], byteorder='little')
            rri_values.append(rr)
            index += 2

    if rri_values:
        rri_label.config(text=f"RRi: {rri_values[-1]} ms")
        rri_list.extend(rri_values)
        update_hrv()

def update_hrv():
    global fft_freq, fft_power
    if len(rri_list) < 4:
        return

    diffs = [(rri_list[i] - rri_list[i - 1]) for i in range(1, len(rri_list))]
    rmssd = round((sum(d**2 for d in diffs) / len(diffs)) ** 0.5, 2)
    sdnn = round(statistics.stdev(rri_list), 2)
    pnn50 = round(100 * sum(1 for d in diffs if abs(d) > 50) / len(diffs), 2)

    lfhf = "-"
    fft_freq = []
    fft_power = []

    if len(rri_list) >= 128:
        rr_sec = np.array([x / 1000.0 for x in rri_list[-128:]])
        rr_detrend = rr_sec - np.mean(rr_sec)

        freqs, psd = welch(rr_detrend, fs=4.0, nperseg=len(rr_detrend))
        fft_freq = freqs
        fft_power = psd

        lf_band = (freqs >= 0.04) & (freqs < 0.15)
        hf_band = (freqs >= 0.15) & (freqs < 0.4)
        lf = np.trapz(psd[lf_band], freqs[lf_band])
        hf = np.trapz(psd[hf_band], freqs[hf_band])

        if hf > 0:
            lfhf = round(lf / hf, 2)

        print(f"LF: {lf}, HF: {hf}, LF/HF: {lfhf}")

    rmssd_label.config(text=f"RMSSD: {rmssd} ms")
    sdnn_label.config(text=f"SDNN: {sdnn} ms")
    pnn50_label.config(text=f"pNN50: {pnn50}%")
    lfhf_label.config(text=f"LF/HF Ratio: {lfhf}")

    interpretation = "-"
    if rmssd < 20:
        interpretation = "❗ Recovery Low: You may be stressed or fatigued"
    elif rmssd >= 20 and rmssd < 50:
        interpretation = "⚠️ Moderate Recovery: Light training recommended"
    elif rmssd >= 50:
        interpretation = "✅ Good Recovery: Ready for intense activity"

    if isinstance(lfhf, float):
        if lfhf > 3:
            interpretation += "\n⚠️ High stress detected (LF/HF > 3)"
        elif lfhf < 0.5:
            interpretation += "\n⚠️ Over-parasympathetic activation (LF/HF < 0.5)"

    interpretation_label.config(text=f"Interpretation:\n{interpretation}")

def run_asyncio_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(connect_and_monitor())

tk.Button(root, text="Connect to Polar H10", command=lambda: threading.Thread(target=run_asyncio_loop, daemon=True).start(), bg="green", fg="white", font=("Arial", 12)).pack(pady=10)

root.mainloop()