import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import time
import threading
import paho.mqtt.client as mqtt
import os
from datetime import datetime
from PIL import Image, ImageTk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.cm as cm  # สำหรับ color map

# Get the project root directory (parent of src/)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")

# ----------------------------
# ตั้งค่าเริ่มต้น
# ----------------------------
BROKER_DEFAULT_IP = "192.168.100.189"
RESULT_FILE = os.path.join(DATA_DIR, "timing_gate_results.json")
ATHLETE_FILE = os.path.join(DATA_DIR, "athletes.json")
TEAM_FILE = os.path.join(DATA_DIR, "teams.json")
TEAM_RESULT_FILE = os.path.join(DATA_DIR, "team_results.json")


start_times = {}  # athlete_id -> start timestamp
results = {}       # athlete_id -> list of timings
selected_athlete = None
athlete_dict = {}
running = False

active_sensors = {chr(65 + i): True for i in range(10)}  # A–J

allow_next_round = False  # ✅ กำหนดว่าอนุญาตจับเวลารอบใหม่หรือยัง

running_distance_m = 100.0  # ค่า default เป็น 100 เมตร
after_id = None

is_team_mode = False
selected_team = None
current_team_index = 0
team_test_results = {}  # athlete_id → list of timings

sensor_distances = {}  # {"A-B": 10.0, "B-C": 15.0, "Total": 25.0}


def load_teams():
    if not os.path.exists(TEAM_FILE):
        return []
    with open(TEAM_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_teams(teams):
    with open(TEAM_FILE, "w", encoding="utf-8") as f:
        json.dump(teams, f, indent=4)


def update_display_timer():
    global after_id
    if running:
        now = time.time()

        if is_team_mode:
            if selected_team and current_team_index < len(selected_team["members"]):
                aid = selected_team["members"][current_team_index]
                if aid in start_times:
                    elapsed = now - start_times[aid]
                    minutes = int(elapsed // 60)
                    seconds = int(elapsed % 60)
                    milliseconds = int((elapsed % 1) * 100)
                    current_display_time.set(f"{minutes:02}:{seconds:02}:{milliseconds:02}")
                else:
                    current_display_time.set("00:00:00")
        else:
            if selected_athlete and selected_athlete["id"] in start_times:
                elapsed = now - start_times[selected_athlete["id"]]
                minutes = int(elapsed // 60)
                seconds = int(elapsed % 60)
                milliseconds = int((elapsed % 1) * 100)
                current_display_time.set(f"{minutes:02}:{seconds:02}:{milliseconds:02}")
            else:
                current_display_time.set("00:00:00")

    after_id = root.after(50, update_display_timer)


# ----------------------------
# โหลดรายชื่อนักกีฬา
# ----------------------------
def load_athletes():
    global athlete_dict
    if not os.path.exists(ATHLETE_FILE):
        return []
    with open(ATHLETE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f).get("athletes", [])
        athlete_dict = {a["id"]: a for a in data}
        return data

def save_athletes(athletes):
    with open(ATHLETE_FILE, "w", encoding="utf-8") as f:
        json.dump({"athletes": athletes}, f, indent=4)

# ----------------------------
# ฟังก์ชัน MQTT
# ----------------------------
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        log("Connected to MQTT Broker")
        client.subscribe("fitness_test/#")
    else:
        log(f"Failed to connect with code {rc}")

player_splits = {}
player_sensors = {}
start_times = {}

def on_message(client, userdata, msg):
    global selected_athlete, running, allow_next_round, is_team_mode, selected_team, current_team_index

    if not running or (not selected_athlete and not is_team_mode):
        return

    topic = msg.topic
    sensor_key = topic.split("_")[-1]

    if not allow_next_round:
        log(f"Ignored sensor {sensor_key} — waiting for 'Next Round'")
        return

    if not active_sensors.get(sensor_key, False):
        return

    # ✅ ดึง athlete ID จากโหมดที่ใช้งาน
    if is_team_mode:
        aid = selected_team["members"][current_team_index]
    else:
        aid = selected_athlete["id"]

    active_sequence = [k for k, v in active_sensors.items() if v]
    total_selected = len(active_sequence)

    if total_selected == 1:
        # ✅ โหมด 1 เซ็นเซอร์ (ไป-กลับ)
        if aid not in start_times:
            start_times[aid] = time.time()
            log(f"Single-sensor: Start timing at {sensor_key}")
        else:
            duration = time.time() - start_times[aid]
            del start_times[aid]

            if is_team_mode:
                if aid not in team_test_results:
                    team_test_results[aid] = []
                team_test_results[aid].append(duration)
                log(f"{aid} (Team) time: {duration:.6f}s")
            else:
                if aid not in results:
                    results[aid] = []
                results[aid].append(duration)
                log(f"Single-sensor: Stop timing at {sensor_key} → Time: {duration:.6f}s")

            update_result_table()
            allow_next_round = False

    elif total_selected == 2:
        # ✅ โหมด 2 เซ็นเซอร์
        if aid not in player_sensors:
            player_sensors[aid] = []

        if len(player_sensors[aid]) == 0:
            player_sensors[aid].append(sensor_key)
            start_times[aid] = time.time()
            log(f"Dual-sensor: Start timing at {sensor_key}")
        elif len(player_sensors[aid]) == 1 and sensor_key != player_sensors[aid][0]:
            duration = time.time() - start_times[aid]
            player_sensors[aid] = []
            del start_times[aid]

            if is_team_mode:
                if aid not in team_test_results:
                    team_test_results[aid] = []
                team_test_results[aid].append(duration)
                log(f"{aid} (Team) time: {duration:.6f}s")
            else:
                if aid not in results:
                    results[aid] = []
                results[aid].append(duration)
                log(f"Dual-sensor: Stop timing at {sensor_key} → Time: {duration:.6f}s")

            update_result_table()
            allow_next_round = False

    else:
        # ✅ โหมด Split Timing (>2 sensors)
        if aid not in player_splits:
            player_splits[aid] = []
            player_sensors[aid] = set()

        if sensor_key in player_sensors[aid]:
            log(f"Split: Sensor {sensor_key} already triggered – ignoring")
            return

        now = time.time()
        player_splits[aid].append((sensor_key, now))
        player_sensors[aid].add(sensor_key)
        log(f"Split: Sensor {sensor_key} triggered at {now:.2f}")

        if len(player_splits[aid]) == 1:
            start_times[aid] = now

        if len(player_splits[aid]) == total_selected:
            timestamps = [t[1] for t in sorted(player_splits[aid], key=lambda x: x[1])]
            sensor_sequence = [t[0] for t in sorted(player_splits[aid], key=lambda x: x[1])]
            split_keys = [f"{sensor_sequence[i]}-{sensor_sequence[i+1]}" for i in range(len(sensor_sequence)-1)]

            split_durations = [round(timestamps[i+1] - timestamps[i], 2) for i in range(len(timestamps)-1)]
            split_distances = [sensor_distances.get(k, 0.0) for k in split_keys]
            total_distance = sensor_distances.get("Total", sum(split_distances))
            split_speeds = [round(d / t, 2) if t > 0 else 0 for d, t in zip(split_distances, split_durations)]
            split_accels = [round((2 * d) / (t ** 2), 2) if t > 0 else 0 for d, t in zip(split_distances, split_durations)]
            total_time = timestamps[-1] - timestamps[0]

            split_result = {
                "splits": split_durations,
                "distances": split_distances,
                "speeds": split_speeds,
                "accels": split_accels,
                "total_time": total_time
            }

            if is_team_mode:
                if aid not in team_test_results:
                    team_test_results[aid] = []
                team_test_results[aid].append(split_result)
                log(f"{aid} (Team) Split: Total: {total_time:.6f}s | Splits: {split_durations}")
            else:
                if aid not in results:
                    results[aid] = []
                results[aid].append(split_result)
                log(f"Split: Finished. Total: {total_time:.6f}s | Splits: {split_durations}")

            update_result_table()

            # ✅ reset
            del start_times[aid]
            player_splits[aid] = []
            player_sensors[aid] = set()
            allow_next_round = False


# ----------------------------
# ฟังก์ชัน GUI
# ----------------------------
def log(text):
    text_box.insert(tk.END, text + "\n")
    text_box.see(tk.END)

def connect_mqtt():
    global mqtt_connected
    broker_ip = mqtt_ip_entry.get()
    client.connect(broker_ip, 1883)
    threading.Thread(target=client.loop_forever, daemon=True).start()
    mqtt_connected = True
    if not session_started:
        start_button.config(state="normal")

selected_athlete = None

def select_athlete():
    global selected_athlete, is_team_mode, selected_team
    is_team_mode = False
    selected_team = None
    selected_athlete = None  # ✅ reset เผื่อเคยเลือกทีมไว้

    def confirm():
        nonlocal selected
        index = selected.curselection()
        if index:
            aid = str(athletes[index[0]]["id"])
            set_selected_athlete(aid)
            athlete = athletes[index[0]]
            athlete_label.config(text=f"Selected: {athlete['first_name']} {athlete['last_name']}")
            win.destroy()

    athletes = load_athletes()
    win = tk.Toplevel(root)
    win.geometry("300x200")
    win.title("Select Athlete")
    selected = tk.Listbox(win, font=("Arial", 12))
    for a in athletes:
        selected.insert(tk.END, f"{a['first_name']} {a['last_name']} ({a['sport']})")
    selected.pack(fill="both", expand=True)
    tk.Button(win, text="Select", command=confirm).pack(pady=5)


def select_team():
    global selected_team, is_team_mode, selected_athlete, current_team_index, team_test_results
    is_team_mode = True
    selected_athlete = None
    def confirm():
        nonlocal selected
        index = selected.curselection()
        if index:
            global selected_team, is_team_mode, current_team_index, team_test_results
            teams = load_teams()
            selected_team = teams[index[0]]
            is_team_mode = True
            current_team_index = 0
            team_test_results = {}
            win.destroy()
            show_team_status()

    teams = load_teams()
    win = tk.Toplevel()
    win.title("Select Team")
    selected = tk.Listbox(win, font=("Arial", 12))
    for t in teams:
        selected.insert(tk.END, f"{t['name']} - {t['sport']}")
    selected.pack(fill="both", expand=True)
    tk.Button(win, text="Select", command=confirm).pack(pady=5)

def show_team_status():
    if not selected_team:
        return

    members = selected_team.get("members", [])
    if current_team_index >= len(members):
        athlete_label.config(text=f"Team Mode: {selected_team['name']} → ✅ Finished")
        return

    member_id = members[current_team_index]
    athlete = next((a for a in load_athletes() if a["id"] == member_id), None)

    if athlete:
        athlete_label.config(
            text=f"Team Mode: {selected_team['name']} → {athlete['first_name']} {athlete['last_name']}"
        )
    else:
        athlete_label.config(
            text=f"Team Mode: {selected_team['name']} → [Unknown Athlete: {member_id}]"
        )


def set_selected_athlete(aid):
    global selected_athlete
    selected_athlete = athlete_dict.get(str(aid))
    if selected_athlete:
        athlete_label.config(text=f"Selected: {selected_athlete['first_name']} {selected_athlete['last_name']}")
        update_result_table()

def update_result_table():
    for widget in result_frame.winfo_children():
        widget.destroy()

    global result_tree

    if is_team_mode and selected_team:
        columns = ("Athlete", "Time")
    else:
        columns = ("Round", "Time")

    result_tree = ttk.Treeview(result_frame, columns=columns, show="headings", height=10)

    for col in columns:
        result_tree.heading(col, text=col, anchor="center")
        result_tree.column(col, anchor="center", width=180 if col == "Time" else 160)

    result_tree.pack(fill="both", expand=True)

    if is_team_mode and selected_team:
        print("🔍 Mode: TEAM")
        for aid in selected_team["members"]:
            times = team_test_results.get(aid, [])
            print(f"  - {aid} | {len(times)} rounds")

            athlete = next((a for a in load_athletes() if a["id"] == aid), None)
            name = f"{athlete['first_name']} {athlete['last_name']}" if athlete else str(aid)

            for t in times:
                if isinstance(t, dict):
                    display = f"{t['total_time']:.6f} sec"
                else:
                    display = f"{t:.6f} sec"

                print(f"     ✅ Insert: {name} → {display}")
                result_tree.insert("", "end", values=(name, display))

    elif selected_athlete:
        print("🔍 Mode: INDIVIDUAL")
        aid = selected_athlete["id"]
        rounds = results.get(aid, [])
        for i, t in enumerate(rounds, 1):
            if isinstance(t, dict):
                display = f"{t['total_time']:.6f} sec"
            else:
                display = f"{t:.6f} sec"
            result_tree.insert("", "end", values=(i, display))


def save_results():
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    if is_team_mode and selected_team:
        # ✅ โหมดทีม → เซฟ team_results.json
        try:
            with open(TEAM_RESULT_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                all_results = data.get("results", [])
        except:
            all_results = []

        for aid, times in team_test_results.items():
            athlete = athlete_dict.get(str(aid))
            if athlete and times:
                result_entry = {
                    "team": selected_team["name"],
                    "athlete_id": aid,
                    "first_name": athlete["first_name"],
                    "last_name": athlete["last_name"],
                    "sport": athlete.get("sport", ""),
                    "date": now,
                    "distance_m": running_distance_m,
                    "timings": times  # ✅ เก็บข้อมูลทั้งก้อน (รวม splits, total_time ฯลฯ)
                }
                all_results.append(result_entry)

        with open(TEAM_RESULT_FILE, "w", encoding="utf-8") as f:
            json.dump({"results": all_results}, f, indent=4)

        messagebox.showinfo("Saved", f"Team '{selected_team['name']}' results saved.")

    else:
        # ✅ โหมดรายบุคคล → เซฟปกติ
        try:
            with open(RESULT_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                all_results = data.get("results", [])
        except:
            all_results = []

        for aid, times in results.items():
            athlete = athlete_dict.get(str(aid))
            if athlete and times:
                result_entry = {
                    "athlete_id": aid,
                    "first_name": athlete["first_name"],
                    "last_name": athlete["last_name"],
                    "sport": athlete.get("sport", ""),
                    "date": now,
                    "distance_m": running_distance_m,
                    "timings": times  # ✅ เก็บข้อมูล split result ทั้งหมด
                }
                all_results.append(result_entry)

        with open(RESULT_FILE, "w", encoding="utf-8") as f:
            json.dump({"results": all_results}, f, indent=4)

        messagebox.showinfo("Saved", "Results saved successfully.")



def start_session():
    global running, session_started, allow_next_round
    if is_team_mode and not selected_team:
        messagebox.showwarning("Warning", "Please select a team first.")
        return
    if not mqtt_connected:
        messagebox.showwarning("MQTT", "Please connect to MQTT first.")
        return

    running = True
    session_started = True
    allow_next_round = True  # ✅ เริ่มรอบแรกได้
    start_button.config(state="disabled")
    save_button.config(state="normal")
    next_button.config(state="normal")
    log("Session started. Waiting for sensor triggers...")


def reset_session():
    global running, start_times, results, session_started, allow_next_round
    running = False
    session_started = False
    allow_next_round = False
    start_times = {}
    results = {}
    update_result_table()
    current_display_time.set("00:00:00")
    start_button.config(state="normal" if mqtt_connected else "disabled")
    save_button.config(state="disabled")
    next_button.config(state="disabled")
    log("Session reset. Please press 'Start Session' again.")

def manage_teams():
    teams = load_teams()
    athletes = load_athletes()

    team_win = tk.Toplevel()
    team_win.title("Manage Teams")

    # Table
    tree = ttk.Treeview(team_win, columns=("ID", "Name", "Sport"), show="headings")
    tree.heading("ID", text="ID")
    tree.heading("Name", text="Team Name")
    tree.heading("Sport", text="Sport")
    tree.pack(fill="both", expand=True)

    def refresh():
        for row in tree.get_children():
            tree.delete(row)
        for t in teams:
            tree.insert("", "end", values=(t["id"], t["name"], t["sport"]))

    def add_team():
        edit_team()

    def edit_team(existing=None):
        team = existing.copy() if existing else {}
        form = tk.Toplevel()
        form.title("Team Form")

        tk.Label(form, text="Team Name").grid(row=0, column=0)
        name_var = tk.StringVar(value=team.get("name", ""))
        tk.Entry(form, textvariable=name_var).grid(row=0, column=1)

        tk.Label(form, text="Sport").grid(row=1, column=0)
        sport_var = tk.StringVar(value=team.get("sport", ""))
        tk.Entry(form, textvariable=sport_var).grid(row=1, column=1)

        tk.Label(form, text="Select Members").grid(row=2, column=0, columnspan=2)
        listbox = tk.Listbox(form, selectmode="multiple", width=30, height=10)
        for i, a in enumerate(athletes):
            listbox.insert(tk.END, f"{a['first_name']} {a['last_name']} ({a['id']})")
            if team.get("members") and a["id"] in team["members"]:
                listbox.selection_set(i)
        listbox.grid(row=3, column=0, columnspan=2)

        def save():
            team["name"] = name_var.get()
            team["sport"] = sport_var.get()
            team["members"] = [athletes[i]["id"] for i in listbox.curselection()]
            if not team.get("id"):
                team["id"] = f"T{len(teams)+1}"
                teams.append(team)
            else:
                for i, t in enumerate(teams):
                    if t["id"] == team["id"]:
                        teams[i] = team
            save_teams(teams)
            form.destroy()
            refresh()

        tk.Button(form, text="Save", command=save).grid(row=4, column=0, columnspan=2, pady=5)

    def edit_selected():
        sel = tree.focus()
        if sel:
            index = int(tree.index(sel))
            edit_team(teams[index])

    def delete_selected():
        sel = tree.focus()
        if sel:
            index = int(tree.index(sel))
            del teams[index]
            save_teams(teams)
            refresh()

    btn_frame = tk.Frame(team_win)
    btn_frame.pack(pady=5)
    tk.Button(btn_frame, text="Add Team", command=add_team).pack(side="left", padx=5)
    tk.Button(btn_frame, text="Edit", command=edit_selected).pack(side="left", padx=5)
    tk.Button(btn_frame, text="Delete", command=delete_selected).pack(side="left", padx=5)

    refresh()

def manage_athletes():
    athletes = load_athletes()

    def refresh():
        for row in table.get_children():
            table.delete(row)
        for i, a in enumerate(athletes):
            table.insert("", "end", values=(a["id"], a["first_name"], a["last_name"], a.get("sport", "")))

    def add():
        edit_athlete()
        refresh()

    def edit():
        sel = table.focus()
        if sel:
            index = int(table.index(sel))
            edit_athlete(athletes[index])
            refresh()

    def delete():
        sel = table.focus()
        if sel:
            index = int(table.index(sel))
            del athletes[index]
            save_athletes(athletes)
            refresh()

    def edit_athlete(data=None):
        athlete = {} if data is None else data.copy()
        win = tk.Toplevel()
        win.title("Athlete Form")
        fields = ["first_name", "last_name", "age", "gender", "sport"]
        entries = {}
        for i, f in enumerate(fields):
            tk.Label(win, text=f).grid(row=i, column=0)
            var = tk.StringVar(value=athlete.get(f, ""))
            tk.Entry(win, textvariable=var).grid(row=i, column=1)
            entries[f] = var
        def save():
            for f in fields:
                athlete[f] = entries[f].get()
            if not athlete.get("id"):
                athlete["id"] = str(len(athletes) + 1)
                athletes.append(athlete)
            else:
                for i, a in enumerate(athletes):
                    if a["id"] == athlete["id"]:
                        athletes[i] = athlete
            save_athletes(athletes)
            win.destroy()
        tk.Button(win, text="Save", command=save).grid(row=len(fields), columnspan=2)

    win = tk.Toplevel()
    win.title("Manage Athletes")
    table = ttk.Treeview(win, columns=("ID", "First Name", "Last Name", "Sport"), show="headings")
    for col in table["columns"]:
        table.heading(col, text=col)
    table.pack(fill="both", expand=True)
    btn_frame = tk.Frame(win)
    btn_frame.pack()
    tk.Button(btn_frame, text="Add", command=add).pack(side="left")
    tk.Button(btn_frame, text="Edit", command=edit).pack(side="left")
    tk.Button(btn_frame, text="Delete", command=delete).pack(side="left")
    refresh()
    tk.Button(win, text="Manage Teams", command=manage_teams).pack(pady=5)


def view_result_detail(tree, data):
    import tkinter as tk
    from tkinter import messagebox
    from tkinter import filedialog

    selected = tree.focus()
    if not selected:
        return
    record = data[int(selected)]

    win = tk.Toplevel()
    win.title("Test Detail")
    win.geometry("800x550")

    info = f"Name   : {record['first_name']} {record['last_name']}\n"
    info += f"Sport  : {record.get('sport','')}\n"
    info += f"Date   : {record.get('date','')}\n"

    times = record.get("timings", [])
    is_split = isinstance(times[0], dict) if times else False

    if is_split:
        split_distances = times[0].get("distances", [])
        total_distance = sum(split_distances) if split_distances else record.get("distance_m", running_distance_m)
        dist_text = ", ".join([f"{d:.1f} m" for d in split_distances])
        info += f"Distance Set : {dist_text} → Total: {total_distance:.1f} m\n\n"
    else:
        total_distance = record.get("distance_m", running_distance_m)
        info += f"Distance     : {total_distance:.1f} m\n\n"

    if is_split:
        info += f"{'Split':<12}{'Time (s)':<12}{'Speed (m/s)':<15}{'Accel (m/s²)':<15}\n"
        info += "-" * 70 + "\n"
        for idx, r in enumerate(times, 1):
            splits = r.get("splits", [])
            speeds = r.get("speeds", [])
            accels = r.get("accels", [])
            for i, (t, v, a) in enumerate(zip(splits, speeds, accels), 1):
                label = f"{idx}.{i}"
                info += f"{label:<12}{t:<12.2f}{v:<15.2f}{a:<15.2f}\n"
            # ✅ เพิ่ม Total Velocity & Acceleration
            tt = r["total_time"]
            v_total = total_distance / tt
            a_total = (2 * total_distance) / (tt ** 2)
            info += f"{'':<12}{'-'*50}\n"
            info += f"{'Round Total':<12}{tt:<12.2f}{v_total:<15.2f}{a_total:<15.2f}\n\n"
    else:
        info += f"{'Round':<8}{'Time (s)':<15}{'Speed (m/s)':<15}{'Accel (m/s²)':<15}\n"
        info += "-" * 60 + "\n"
        for i, t in enumerate(times):
            v = total_distance / t
            a = (2 * total_distance) / (t ** 2)
            info += f"{i+1:<8}{t:<15.6f}{v:<15.6f}{a:<15.6f}\n"

    scroll = tk.Scrollbar(win)
    scroll.pack(side="right", fill="y")

    text = tk.Text(win, width=85, height=25, yscrollcommand=scroll.set, font=("Courier New", 11))
    text.insert("1.0", info)
    text.config(state="disabled")
    text.pack(fill="both", expand=True, padx=10, pady=10)

    scroll.config(command=text.yview)

    def export_individual_csv(record):
        import csv
        path = filedialog.asksaveasfilename(defaultextension=".csv",
                                            filetypes=[("CSV files", "*.csv")],
                                            title="Save as CSV")
        if not path:
            return

        try:
            with open(path, mode='w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(["ATHLETE REPORT"])
                writer.writerow(["Name", f"{record['first_name']} {record['last_name']}"])
                writer.writerow(["Sport", record.get("sport", "")])
                writer.writerow(["Date", record.get("date", "")])

                times = record.get("timings", [])
                is_split = isinstance(times[0], dict) if times else False

                if is_split:
                    dists = times[0].get("distances", [])
                    total_dist = sum(dists) if dists else record.get("distance_m", 100.0)
                    writer.writerow(["Distance Set", ", ".join([f"{d:.1f} m" for d in dists])])
                    writer.writerow(["Total Distance", f"{total_dist:.1f} m"])
                else:
                    total_dist = record.get("distance_m", 100.0)
                    writer.writerow(["Distance", f"{total_dist:.1f} m"])

                writer.writerow([])
                writer.writerow(["Split", "Time (s)", "Speed (m/s)", "Acceleration (m/s²)"])

                for idx, r in enumerate(times, 1):
                    if isinstance(r, dict):
                        splits = r.get("splits", [])
                        speeds = r.get("speeds", [])
                        accels = r.get("accels", [])
                        for i, (sp, sv, sa) in enumerate(zip(splits, speeds, accels), 1):
                            label = f"{idx}.{i}"
                            writer.writerow([label, f"{sp:.6f}", f"{sv:.3f}", f"{sa:.3f}"])
                        # ✅ Total
                        tt = r["total_time"]
                        v_total = total_dist / tt
                        a_total = (2 * total_dist) / (tt ** 2)
                        writer.writerow(["Total", f"{tt:.6f}", f"{v_total:.3f}", f"{a_total:.3f}"])
                        writer.writerow([])
                    else:
                        v = total_dist / r
                        a = (2 * total_dist) / (r ** 2)
                        writer.writerow([f"{idx}", f"{r:.6f}", f"{v:.3f}", f"{a:.3f}"])
                        writer.writerow([])

                messagebox.showinfo("Export Complete", f"CSV saved to:\n{path}")

        except Exception as e:
            messagebox.showerror("Export Error", str(e))

    # ✅ ปุ่มด้านล่าง
    btn_frame = tk.Frame(win)
    btn_frame.pack(pady=5)
    tk.Button(btn_frame, text="Plot Graphs", command=lambda: plot_graphs(times, total_distance), bg="navy", fg="white", width=15).pack(side="left", padx=8)
    tk.Button(btn_frame, text="Export PDF", command=lambda: export_pdf(record), bg="darkred", fg="white", width=15).pack(side="left", padx=8)
    tk.Button(btn_frame, text="Export to CSV", command=lambda: export_individual_csv(record), bg="darkgreen", fg="white", width=15).pack(side="left", padx=8)


def export_pdf(record):
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_pdf import PdfPages
    import tempfile
    import os
    import pandas as pd

    name = f"{record['first_name']} {record['last_name']}"
    date = record.get("date", "")
    distance = record.get("distance_m", running_distance_m)
    times = record.get("timings", [])
    is_split = isinstance(times[0], dict) if times else False

    # สร้างไฟล์ชั่วคราวก่อน export
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmpfile:
        with PdfPages(tmpfile.name) as pdf:

            # หน้าแรก: Cover
            fig_cover = plt.figure(figsize=(8.3, 11.7))
            plt.axis('off')
            fig_cover.text(0.5, 0.9, "Timing Gate Performance Report", ha="center", fontsize=20, weight="bold")
            fig_cover.text(0.5, 0.84, f"Athlete: {name}", ha="center", fontsize=14)
            fig_cover.text(0.5, 0.80, f"Test Date: {date}", ha="center", fontsize=12)
            fig_cover.text(0.5, 0.76, f"Running Distance: {distance:.2f} meters", ha="center", fontsize=12)
            fig_cover.text(0.5, 0.65, "This document includes measured times and calculated performance", ha="center", fontsize=10, style="italic")
            fig_cover.text(0.5, 0.62, "metrics such as speed and acceleration based on kinematic formulas.", ha="center", fontsize=10, style="italic")
            pdf.savefig(fig_cover)
            plt.close(fig_cover)

            # ตารางผลลัพธ์
            fig_table = plt.figure(figsize=(8.3, 11.7))
            ax = fig_table.add_subplot(111)
            ax.axis('off')
            ax.set_title("Detailed Results", fontsize=14, weight="bold", loc="left")

            if is_split:
                rows, round_labels = [], []
                for idx, r in enumerate(times, 1):
                    splits = r["splits"]
                    speeds = r["speeds"]
                    accels = r["accels"]
                    for i in range(len(splits)):
                        round_labels.append(f"{idx}.{i+1}")
                        rows.append([f"{splits[i]:.2f}", f"{speeds[i]:.2f}", f"{accels[i]:.2f}"])
                df = pd.DataFrame(rows, columns=["Time (s)", "Speed (m/s)", "Accel (m/s²)"])
                df.insert(0, "Split", round_labels)
            else:
                speeds = [distance / t for t in times]
                accels = [(2 * distance) / (t ** 2) for t in times]
                df = pd.DataFrame({
                    "Round": list(range(1, len(times)+1)),
                    "Time (s)": [f"{t:.6f}" for t in times],
                    "Speed (m/s)": [f"{s:.6f}" for s in speeds],
                    "Accel (m/s²)": [f"{a:.6f}" for a in accels]
                })

            table = ax.table(cellText=df.values,
                             colLabels=df.columns,
                             cellLoc='center',
                             colLoc='center',
                             loc='upper center',
                             bbox=[0, 0.4, 1, 0.55])
            table.auto_set_font_size(False)
            table.set_fontsize(10)
            table.scale(1, 1.3)
            pdf.savefig(fig_table)
            plt.close(fig_table)

            # Summary
            fig_summary = plt.figure(figsize=(8.3, 11.7))
            ax = fig_summary.add_subplot(111)
            ax.axis('off')
            ax.set_title("SUMMARY STATISTICS", fontsize=14, weight="bold", loc="center")

            all_times = []
            all_speeds = []
            all_accels = []

            if is_split:
                for r in times:
                    all_times.extend(r["splits"])
                    all_speeds.extend(r["speeds"])
                    all_accels.extend(r["accels"])
            else:
                all_times = times
                all_speeds = [distance / t for t in times]
                all_accels = [(2 * distance) / (t ** 2) for t in times]

            summary_data = [
                ["Athlete", name],
                ["Date", date],
                ["Distance (m)", f"{distance:.2f}"],
                ["Total Splits", len(all_times)],
                ["Average Time (s)", f"{sum(all_times)/len(all_times):.6f}"],
                ["Average Speed (m/s)", f"{sum(all_speeds)/len(all_speeds):.6f}"],
                ["Average Acceleration (m/s²)", f"{sum(all_accels)/len(all_accels):.6f}"],
                ["Max Speed (m/s)", f"{max(all_speeds):.6f}"],
                ["Max Acceleration (m/s²)", f"{max(all_accels):.6f}"],
                ["Min Time (s)", f"{min(all_times):.6f}"]
            ]

            summary_table = ax.table(cellText=summary_data,
                                     colWidths=[0.6, 0.6],
                                     cellLoc='left',
                                     colLoc='left',
                                     loc='center',
                                     bbox=[0.1, 0.45, 0.8, 0.45])
            summary_table.auto_set_font_size(False)
            summary_table.set_fontsize(10)
            summary_table.scale(1.3, 1.5)

            for (row, col), cell in summary_table.get_celld().items():
                if col == 0:
                    cell.get_text().set_weight('bold')

            pdf.savefig(fig_summary)
            plt.close(fig_summary)

            # กราฟ
            def add_chart(title, y_data, y_label, color):
                fig = Figure(figsize=(8.3, 5))
                ax = fig.add_subplot(111)
                ax.plot(list(range(1, len(y_data)+1)), y_data, marker='o', color=color, linewidth=2)
                ax.set_title(title, fontsize=12, weight="bold")
                ax.set_xlabel("Split" if is_split else "Round")
                ax.set_ylabel(y_label)
                ax.grid(True)
                fig.tight_layout()
                pdf.savefig(fig)
                plt.close(fig)

            if is_split:
                for idx, r in enumerate(times, 1):
                    add_chart(f"Split Time – Round {idx}", r["splits"], "Time (s)", "blue")
                    add_chart(f"Split Speed – Round {idx}", r["speeds"], "Speed (m/s)", "green")
                    add_chart(f"Split Acceleration – Round {idx}", r["accels"], "Accel (m/s²)", "red")
            else:
                add_chart("Time per Round", times, "Time (s)", "blue")
                add_chart("Speed per Round", [distance / t for t in times], "Speed (m/s)", "green")
                add_chart("Acceleration per Round", [(2 * distance) / (t ** 2) for t in times], "Acceleration (m/s²)", "red")

    filepath = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")])
    if filepath:
        os.replace(tmpfile.name, filepath)
        messagebox.showinfo("Exported", f"PDF saved to:\n{filepath}")

def plot_graphs(times, distance):
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

    is_split = isinstance(times[0], dict) if times else False

    if is_split:
        fig, axs = plt.subplots(3, 1, figsize=(5.2, 6.8), constrained_layout=True)
        fig.suptitle("Performance Analysis (Split Mode)", fontsize=16, fontweight="bold", fontname="Arial")

        # รวมข้อมูล split ทุกชุดไว้ต่อเนื่อง
        all_time = []
        all_speed = []
        all_accel = []
        labels = []

        for idx, r in enumerate(times, 1):
            for i in range(len(r["splits"])):
                all_time.append(r["splits"][i])
                all_speed.append(r["speeds"][i])
                all_accel.append(r["accels"][i])
                labels.append(f"{idx}.{i+1}")

        x = list(range(1, len(all_time) + 1))

        # Time Graph
        axs[0].plot(x, all_time, marker='o', color='blue', linewidth=2)
        axs[0].set_title("Split Time", fontsize=12, fontname="Arial")
        axs[0].set_xlabel("Split Index", fontsize=11)
        axs[0].set_ylabel("Time (s)", fontsize=11)
        axs[0].grid(True)

        # Speed Graph
        axs[1].plot(x, all_speed, marker='s', color='green', linewidth=2)
        axs[1].set_title("Split Speed", fontsize=12, fontname="Arial")
        axs[1].set_xlabel("Split Index", fontsize=11)
        axs[1].set_ylabel("Speed (m/s)", fontsize=11)
        axs[1].grid(True)

        # Acceleration Graph
        axs[2].plot(x, all_accel, marker='^', color='red', linewidth=2)
        axs[2].set_title("Split Acceleration", fontsize=12, fontname="Arial")
        axs[2].set_xlabel("Split Index", fontsize=11)
        axs[2].set_ylabel("Acceleration (m/s²)", fontsize=11)
        axs[2].grid(True)

    else:
        rounds = list(range(1, len(times) + 1))
        speeds = [distance / t for t in times]
        accels = [(2 * distance) / (t ** 2) for t in times]

        fig, axs = plt.subplots(3, 1, figsize=(5.2, 6.8), constrained_layout=True)
        fig.suptitle("Performance Analysis", fontsize=16, fontweight="bold", fontname="Arial")

        # Time Graph
        axs[0].plot(rounds, times, marker='o', color='blue', linewidth=2)
        axs[0].set_title("Time per Round", fontsize=12, fontname="Arial")
        axs[0].set_xlabel("Round", fontsize=11)
        axs[0].set_ylabel("Time (seconds)", fontsize=11)
        axs[0].grid(True)

        # Speed Graph
        axs[1].plot(rounds, speeds, marker='s', color='green', linewidth=2)
        axs[1].set_title("Speed per Round", fontsize=12, fontname="Arial")
        axs[1].set_xlabel("Round", fontsize=11)
        axs[1].set_ylabel("Speed (m/s)", fontsize=11)
        axs[1].grid(True)

        # Acceleration Graph
        axs[2].plot(rounds, accels, marker='^', color='red', linewidth=2)
        axs[2].set_title("Acceleration per Round", fontsize=12, fontname="Arial")
        axs[2].set_xlabel("Round", fontsize=11)
        axs[2].set_ylabel("Acceleration (m/s²)", fontsize=11)
        axs[2].grid(True)

    for ax in axs:
        ax.tick_params(axis='both', which='major', labelsize=10)
        ax.set_facecolor("#f5f5f5")

    graph_win = tk.Toplevel()
    graph_win.title("Performance Graphs")

    canvas = FigureCanvasTkAgg(fig, master=graph_win)
    canvas.draw()
    canvas.get_tk_widget().pack(fill="both", expand=True)

    def close_graph_window():
        plt.close(fig)
        graph_win.destroy()

    graph_win.protocol("WM_DELETE_WINDOW", close_graph_window)


def view_history():
    if not os.path.exists(RESULT_FILE):
        messagebox.showinfo("No Data", "No test results found.")
        return
    with open(RESULT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f).get("results", [])

    win = tk.Toplevel()
    win.title("Test History")
    tree = ttk.Treeview(win, columns=("Name", "Date", "Times"), show="headings")
    tree.heading("Name", text="Name")
    tree.heading("Date", text="Date")
    tree.heading("Times", text="Timings")
    tree.pack(fill="both", expand=True)

    for i, r in enumerate(data):
        name = f"{r['first_name']} {r['last_name']}"
        date = r['date']
        times = ", ".join([
        f"{t['total_time']:.6f}s" if isinstance(t, dict) else f"{t:.6f}s"
        for t in r.get("timings", [])
        ])

        tree.insert("", "end", iid=str(i), values=(name, date, times))

    def delete_selected():
        selected = tree.focus()
        if not selected:
            return
        confirm = messagebox.askyesno("Delete", "Are you sure to delete this result?")
        if confirm:
            del data[int(selected)]
            with open(RESULT_FILE, "w", encoding="utf-8") as f:
                json.dump({"results": data}, f, indent=4)
            tree.delete(selected)

    tk.Button(win, text="Delete Selected", command=delete_selected, bg="red", fg="white").pack(pady=5)
    tk.Button(win, text="View", command=lambda: view_result_detail(tree, data), bg="green", fg="white").pack(pady=5)



def show_sensor_options():
    win = tk.Toplevel()
    win.title("Select Active Sensors")
    vars = {}

    def save_settings():
        for k in vars:
            active_sensors[k] = vars[k].get()
        win.destroy()

    for i, key in enumerate(active_sensors.keys()):
        vars[key] = tk.BooleanVar(value=active_sensors[key])
        cb = tk.Checkbutton(win, text=f"Sensor {key}", variable=vars[key])
        cb.grid(row=i//5, column=i%5, padx=10, pady=5)

    tk.Button(win, text="Save", command=save_settings).grid(row=3, columnspan=5, pady=10)

def allow_next_timing():
    global allow_next_round, current_team_index, selected_team, is_team_mode
    allow_next_round = True
    if is_team_mode:
        current_team_index += 1
        if current_team_index >= len(selected_team["members"]):
            log(f"✅ Team '{selected_team['name']}' finished testing.")
            next_button.config(state="disabled")
            start_button.config(state="normal")
        else:
            show_team_status()
            log(f"Next athlete: {current_team_index + 1} / {len(selected_team['members'])}")


def set_running_distance():
    def save_distance():
        global running_distance_m
        try:
            val = float(entry.get())
            if val > 0:
                running_distance_m = val
                win.destroy()
            else:
                messagebox.showwarning("Invalid", "Distance must be positive")
        except:
            messagebox.showwarning("Invalid", "Please enter a valid number")

    win = tk.Toplevel()
    win.title("Set Running Distance (meters)")
    tk.Label(win, text="Distance (m):").pack(padx=10, pady=5)
    entry = tk.Entry(win)
    entry.insert(0, str(running_distance_m))
    entry.pack(padx=10)
    tk.Button(win, text="Save", command=save_distance).pack(pady=10)

def on_closing():
    global after_id
    if after_id is not None:
        root.after_cancel(after_id)  # ยกเลิก callback
    root.destroy()

def view_team_results():
    try:
        with open("team_results.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            results = data.get("results", [])
    except:
        messagebox.showerror("Error", "No team results found.")
        return

    # 🔁 รวมตาม (team, date)
    grouped = {}
    for r in results:
        key = (r["team"], r["date"])
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(r)

    win = tk.Toplevel()
    win.title("Team Test Results")

    tree = ttk.Treeview(win, columns=("Team", "Date", "Athletes"), show="headings", height=12)
    tree.heading("Team", text="Team")
    tree.heading("Date", text="Date")
    tree.heading("Athletes", text="Entries")
    tree.pack(fill="both", expand=True)

    display_data = list(grouped.items())
    for (team, date), members in display_data:
        tree.insert("", "end", values=(team, date, len(members)))

    def view_selected():
        sel = tree.focus()
        if not sel:
            return
        item = tree.item(sel)
        team = item["values"][0]
        date = item["values"][1]
        members = [r for r in results if r["team"] == team and r["date"] == date]

        win_detail = tk.Toplevel()
        win_detail.title(f"{team} – {date}")
        text = tk.Text(win_detail, width=90, height=30, font=("Courier New", 10))
        text.pack(fill="both", expand=True)

        # ✅ ดึงค่าระยะทางจาก timing[0]["distances"]
        example = members[0]
        first_timing = example.get("timings", [{}])[0]
        split_distances = first_timing.get("distances", [])
        total_distance = sum(split_distances) if split_distances else example.get("distance_m", running_distance_m)

        # ✅ สร้างข้อความแสดงระยะทางแยกช่วง + รวม
        if split_distances:
            split_text = ", ".join([f"{d:.1f} m" for d in split_distances])
            split_info = f"{split_text}  →  Total: {total_distance:.1f} m"
        else:
            split_info = f"{total_distance:.1f} m"

        # ✅ หัวข้อความ
        info = f"TEAM: {team}\nDATE: {date}\nDISTANCE SET: {split_info}\n\n"
        info += f"{'Name':<30}{'Split':<10}{'Time(s)':<12}{'Speed(m/s)':<14}{'Accel(m/s²)'}\n"
        info += "-" * 80 + "\n"

        for r in members:
            name = f"{r['first_name']} {r['last_name']}"
            first_shown = False

            for i, t in enumerate(r["timings"]):
                if isinstance(t, dict):
                    splits = t.get("splits", [])
                    speeds = t.get("speeds", [])
                    accels = t.get("accels", [])
                    for j, (st, sv, sa) in enumerate(zip(splits, speeds, accels), 1):
                        split_label = f"{i+1}.{j}"
                        info += f"{name:<30}{split_label:<10}{st:<12.6f}{sv:<14.3f}{sa:.3f}\n"
                        if not first_shown:
                            name = ""
                            first_shown = True

                    # ✅ เพิ่ม Total Velocity & Acceleration
                    tt = t["total_time"]
                    v_total = total_distance / tt
                    a_total = (2 * total_distance) / (tt ** 2)
                    info += f"{'':<30}{'Total':<10}{tt:<12.6f}{v_total:<14.3f}{a_total:.3f}\n\n"

                else:
                    v = total_distance / t
                    a = (2 * total_distance) / (t ** 2)
                    info += f"{name:<30}{f'{i+1}':<10}{t:<12.6f}{v:<14.3f}{a:.3f}\n"
                    name = ""

      # ✅ ปุ่มเรียงแนวนอนในบรรทัดเดียว
        btn_frame = tk.Frame(win_detail)
        btn_frame.pack(pady=5)

        tk.Button(btn_frame, text="Plot Compare Graphs", command=plot_selected, bg="navy", fg="white", width=20).pack(side="left", padx=8)
        tk.Button(btn_frame, text="Export PDF", command=lambda: export_team_pdf(members, team, date), bg="darkred", fg="white", width=15).pack(side="left", padx=8)
        tk.Button(btn_frame, text="Export CSV", command=lambda: export_team_csv(members, team, date), bg="darkgreen", fg="white", width=15).pack(side="left", padx=8)

        text.insert("1.0", info)
        text.config(state="disabled")


    def delete_selected():
        sel = tree.focus()
        if not sel:
            return
        item = tree.item(sel)
        team = item["values"][0]
        date = item["values"][1]

        confirm = messagebox.askyesno("Delete", f"Delete results for team '{team}' on {date}?")
        if not confirm:
            return

        new_data = [r for r in results if not (r["team"] == team and r["date"] == date)]
        with open(TEAM_RESULT_FILE, "w", encoding="utf-8") as f:
            json.dump({"results": new_data}, f, indent=4)

        tree.delete(sel)
        messagebox.showinfo("Deleted", "Team result deleted.")

    def plot_selected():
        import numpy as np  # ✅ แก้ NameError
        from matplotlib import cm
        sel = tree.focus()
        if not sel:
            return
        item = tree.item(sel)
        team = item["values"][0]
        date = item["values"][1]
        members = [r for r in results if r["team"] == team and r["date"] == date]

        if not members:
            messagebox.showwarning("No data", "No data found.")
            return

        labels = [f"{r['first_name']} {r['last_name']}" for r in members]

        total_times = []
        speeds = []
        accels = []

        for r in members:
            t = r["timings"][0]
            if isinstance(t, dict):
                total_time = t["total_time"]
            else:
                total_time = t
            dist = sum(t.get("distances", [])) if isinstance(t, dict) else r.get("distance_m", 100.0)
            total_times.append(total_time)
            speeds.append(dist / total_time)
            accels.append((2 * dist) / (total_time ** 2))

        # ใช้ color map ที่เป็นทางการ
        colors = cm.get_cmap('tab10')(np.linspace(0, 1, len(labels)))

        fig, axs = plt.subplots(3, 1, figsize=(8, 9), constrained_layout=True)
        fig.suptitle(f"Team Performance Summary – {team} ({date})", fontsize=14, fontweight="bold")

        # กราฟเวลา
        axs[0].bar(labels, total_times, color=colors, edgecolor="black")
        axs[0].set_title("Total Time", fontsize=12)
        axs[0].set_ylabel("Time (s)")
        axs[0].tick_params(axis='x', labelrotation=15)
        axs[0].grid(axis='y', linestyle='--', alpha=0.5)

        # กราฟ speed
        axs[1].bar(labels, speeds, color=colors, edgecolor="black")
        axs[1].set_title("Average Speed", fontsize=12)
        axs[1].set_ylabel("Speed (m/s)")
        axs[1].tick_params(axis='x', labelrotation=15)
        axs[1].grid(axis='y', linestyle='--', alpha=0.5)

        # กราฟ accel
        axs[2].bar(labels, accels, color=colors, edgecolor="black")
        axs[2].set_title("Average Acceleration", fontsize=12)
        axs[2].set_ylabel("Accel (m/s²)")
        axs[2].set_xlabel("Athletes")
        axs[2].tick_params(axis='x', labelrotation=15)
        axs[2].grid(axis='y', linestyle='--', alpha=0.5)

        # สร้างหน้าต่างกราฟ
        graph_win = tk.Toplevel()
        graph_win.title("Team Comparison – Bar Charts")
        graph_win.geometry("850x700")

        canvas = FigureCanvasTkAgg(fig, master=graph_win)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

        def close_graph_window():
            plt.close(fig)
            graph_win.destroy()

        graph_win.protocol("WM_DELETE_WINDOW", close_graph_window)

    btn_frame = tk.Frame(win)
    btn_frame.pack(pady=5)
    tk.Button(btn_frame, text="View", command=view_selected,bg="green", fg="white").pack(side="left", padx=5)
    tk.Button(btn_frame, text="Delete Selected", command=delete_selected, bg="red", fg="white").pack(side="left", padx=5)

def export_team_csv(members, team_name, date):
    import csv
    from tkinter import filedialog, messagebox

    path = filedialog.asksaveasfilename(defaultextension=".csv",
                                        filetypes=[("CSV files", "*.csv")],
                                        title="Save as CSV")
    if not path:
        return

    try:
        with open(path, mode='w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)

            # ✅ ดึงระยะจาก timing[0]["distances"]
            first_timing = members[0].get("timings", [{}])[0]
            split_distances = first_timing.get("distances", [])
            total_distance = sum(split_distances) if split_distances else members[0].get("distance_m", 100.0)
            if split_distances:
                split_text = ", ".join([f"{d:.1f} m" for d in split_distances])
                distance_summary = f"{split_text} → Total: {total_distance:.1f} m"
            else:
                distance_summary = f"{total_distance:.1f} m"

            # 🧾 Header รายงาน
            writer.writerow(["TEAM PERFORMANCE REPORT"])
            writer.writerow(["Team Name", team_name])
            writer.writerow(["Test Date", date])
            writer.writerow(["Distance Set", distance_summary])
            writer.writerow([])

            writer.writerow(["Name", "Split", "Time (s)", "Speed (m/s)", "Acceleration (m/s²)"])

            for r in members:
                name = f"{r['first_name']} {r['last_name']}"
                for i, t in enumerate(r["timings"]):
                    if isinstance(t, dict):
                        splits = t.get("splits", [])
                        speeds = t.get("speeds", [])
                        accels = t.get("accels", [])
                        total_time = t["total_time"]
                        dists = t.get("distances", [])
                        dist_total = sum(dists) if dists else r.get("distance_m", 100.0)
                        v_total = dist_total / total_time
                        a_total = (2 * dist_total) / (total_time ** 2)

                        for j, (sp, spd, acc) in enumerate(zip(splits, speeds, accels), 1):
                            split_label = f"{i+1}.{j}"
                            writer.writerow([name, split_label, f"{sp:.6f}", f"{spd:.3f}", f"{acc:.3f}"])
                            name = ""
                        writer.writerow(["", "Total", f"{total_time:.6f}", f"{v_total:.3f}", f"{a_total:.3f}"])
                        writer.writerow([])
                    else:
                        d = r.get("distance_m", 100.0)
                        v = d / t
                        a = (2 * d) / (t ** 2)
                        writer.writerow([name, f"{i+1}", f"{t:.6f}", f"{v:.3f}", f"{a:.3f}"])
                        name = ""

        messagebox.showinfo("Export Complete", f"CSV saved to:\n{path}")

    except Exception as e:
        messagebox.showerror("Error", f"Failed to export CSV:\n{e}")


def export_team_pdf(members, team_name, date):
    from matplotlib.backends.backend_pdf import PdfPages
    from matplotlib import pyplot as plt, cm
    from tkinter import filedialog, messagebox
    import numpy as np
    import tempfile
    import os

    # 🧮 ระยะทางรวม
    first_timing = members[0]["timings"][0]
    split_distances = first_timing.get("distances", [])
    total_distance = sum(split_distances) if split_distances else members[0].get("distance_m", 100.0)

    # 📄 รายงานหลัก
    text = f"TEAM PERFORMANCE REPORT\n"
    text += "=" * 80 + "\n"
    text += f"Team Name     : {team_name}\n"
    text += f"Test Date     : {date}\n"
    if split_distances:
        text += f"Distance Set  : {', '.join([f'{d:.1f} m' for d in split_distances])} → Total: {total_distance:.1f} m\n"
    else:
        text += f"Distance      : {total_distance:.1f} m\n"
    text += "=" * 80 + "\n\n"

    text += f"{'Name':<25}{'Split':<10}{'Time(s)':<10}{'Speed(m/s)':<12}{'Accel(m/s²)'}\n"
    text += "-" * 75 + "\n"

    labels = []
    all_total_times = []

    for r in members:
        name = f"{r['first_name']} {r['last_name']}"
        labels.append(name)
        for i, t in enumerate(r["timings"]):
            if isinstance(t, dict):
                splits = t.get("splits", [])
                speeds = t.get("speeds", [])
                accels = t.get("accels", [])
                for j, (sp, spd, acc) in enumerate(zip(splits, speeds, accels), 1):
                    split_label = f"{i+1}.{j}"
                    text += f"{name:<25}{split_label:<10}{sp:<10.2f}{spd:<12.2f}{acc:.2f}\n"
                    name = ""
                text += f"{'':<25}{'Total':<10}{t['total_time']:<10.2f}\n\n"
                all_total_times.append(t['total_time'])

    # 📊 สถิติเบื้องต้น
    stats = {
        "Total Athletes" : len(members),
        "Max Time (s)"   : np.max(all_total_times),
        "Min Time (s)"   : np.min(all_total_times),
        "Mean Time (s)"  : np.mean(all_total_times)
    }

    # 📊 กราฟแท่ง
    fig_bar, ax = plt.subplots(figsize=(8.3, 4.5))
    ax.bar(labels, all_total_times, color="steelblue", edgecolor="black")
    ax.set_title(f"Total Time per Athlete – {team_name}", fontsize=13, weight="bold")
    ax.set_ylabel("Time (s)")
    ax.set_xlabel("Athletes")
    ax.tick_params(axis='x', labelrotation=15)
    ax.grid(axis="y", linestyle="--", alpha=0.6)
    fig_bar.tight_layout()

    # ✅ Export PDF
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmpfile:
        temp_pdf_path = tmpfile.name

    with PdfPages(temp_pdf_path) as pdf:
        # 📄 Page 1: ตาราง Split
        fig_text = plt.figure(figsize=(8.3, 11.7))
        plt.axis("off")
        plt.text(0.03, 0.98, text, fontsize=10, family="monospace", va="top")
        pdf.savefig(fig_text)
        plt.close(fig_text)

        # 📄 Page 2: Summary Stats
        fig_summary = plt.figure(figsize=(8.3, 11.7))
        ax2 = fig_summary.add_subplot(111)
        ax2.axis("off")
        ax2.set_title("Summary Statistics", fontsize=14, weight="bold", loc="center")

        lines = "\n".join([f"{k:<20}: {v:.2f}" if isinstance(v, float) else f"{k:<20}: {v}" for k, v in stats.items()])
        ax2.text(0.05, 0.90, lines, fontsize=12, family="monospace", va="top")
        pdf.savefig(fig_summary)
        plt.close(fig_summary)

        # 📄 Page 3: Bar Chart
        pdf.savefig(fig_bar)
        plt.close(fig_bar)

    # 📂 บันทึก
    path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")])
    if path:
        os.replace(temp_pdf_path, path)
        messagebox.showinfo("Exported", f"PDF saved to:\n{path}")


def set_split_distances():
    active = [k for k, v in active_sensors.items() if v]
    if len(active) < 2:
        messagebox.showinfo("Info", "You must select at least 2 sensors.")
        return

    win = tk.Toplevel()
    win.title("Set Split Distances")

    entries = {}
    for i in range(len(active) - 1):
        key = f"{active[i]}-{active[i+1]}"
        tk.Label(win, text=f"Distance {key} (m):").grid(row=i, column=0, padx=10, pady=5)
        val = tk.DoubleVar(value=sensor_distances.get(key, 0.0))
        entry = tk.Entry(win, textvariable=val)
        entry.grid(row=i, column=1, padx=10, pady=5)
        entries[key] = val

    tk.Label(win, text="Total Distance (m):").grid(row=len(active), column=0, padx=10, pady=10)
    total_var = tk.DoubleVar(value=sensor_distances.get("Total", 0.0))
    total_entry = tk.Entry(win, textvariable=total_var)
    total_entry.grid(row=len(active), column=1, padx=10, pady=10)

    def save():
        for key, var in entries.items():
            try:
                sensor_distances[key] = float(var.get())
            except ValueError:
                messagebox.showwarning("Invalid Input", f"Please enter a valid number for {key}.")
                return
        try:
            sensor_distances["Total"] = float(total_var.get())
        except ValueError:
            messagebox.showwarning("Invalid Input", "Please enter a valid total distance.")
            return
        win.destroy()

    tk.Button(win, text="Save", command=save).grid(row=len(active)+1, columnspan=2, pady=10)

# ----------------------------
# GUI Layout
# ----------------------------
root = tk.Tk()
root.protocol("WM_DELETE_WINDOW", on_closing)
root.title("Timing Gate System")
root.geometry("900x750")

# เพิ่มไว้หลัง root = tk.Tk()
mqtt_connected = False
session_started = False


# เพิ่ม: ตัวแปรจับเวลาแบบ realtime
current_display_time = tk.StringVar(value="00:00:00")
# 🔻 ป้ายไฟแบบ 7-segment
segment_frame = tk.Frame(root, bg="black")
segment_frame.pack(pady=10)
segment_label = tk.Label(
    segment_frame,
    textvariable=current_display_time,
    font=("Courier New", 56, "bold"),  # หรือใช้ฟอนต์ nixie ถ้ามี
    fg="#ff6600",        # สีส้มอำพันคล้าย nixie
    bg="black",
    padx=30,
    pady=20,
    bd=4,
    relief="sunken",     # มีขอบให้เหมือนกรอบหลอด
    highlightthickness=2,
    highlightbackground="#330000"
)

segment_label.pack()

menu_bar = tk.Menu(root)
root.config(menu=menu_bar)

setting_menu = tk.Menu(menu_bar, tearoff=0)
menu_bar.add_cascade(label="Settings", menu=setting_menu)
setting_menu.add_command(label="Manage Athletes", command=manage_athletes)
setting_menu.add_command(label="Sensor Options", command=show_sensor_options)
setting_menu.add_command(label="Set Running Distance", command=set_running_distance)
setting_menu.add_command(label="Set Split Distances", command=set_split_distances)



result_menu = tk.Menu(menu_bar, tearoff=0)
menu_bar.add_cascade(label="Results", menu=result_menu)
result_menu.add_command(label="View History", command=view_history)
result_menu.add_command(label="View Team Results", command=view_team_results)


# MQTT + Athlete
mqtt_frame = tk.LabelFrame(root, text="MQTT Broker")
mqtt_frame.pack(fill="x", padx=10, pady=5)

mqtt_ip_entry = tk.Entry(mqtt_frame)
mqtt_ip_entry.insert(0, BROKER_DEFAULT_IP)
mqtt_ip_entry.pack(side="left", padx=5)
tk.Button(mqtt_frame, text="Connect", command=connect_mqtt).pack(side="left", padx=10)

athlete_frame = tk.Frame(root)
athlete_frame.pack(fill="x", pady=5)

athlete_label = tk.Label(athlete_frame, text="Selected: None", font=("Arial", 12))
athlete_label.pack(side="left", padx=10)

# ✅ เพิ่มปุ่ม Select Athlete และ Select Team แยกกัน
tk.Button(athlete_frame, text="Select Athlete", command=select_athlete).pack(side="left", padx=5)
tk.Button(athlete_frame, text="Select Team", command=select_team).pack(side="left", padx=5)


control_frame = tk.Frame(root)
control_frame.pack(pady=5)
start_button = tk.Button(control_frame, text="Start Session", command=start_session, bg="green", fg="white", font=("Arial", 12), state="disabled")
start_button.pack(side="left", padx=10)

reset_button = tk.Button(control_frame, text="Reset Session", command=reset_session, bg="orange", fg="black", font=("Arial", 12))
reset_button.pack(side="left", padx=10)

next_button = tk.Button(control_frame, text="Next Round", command=allow_next_timing, bg="purple", fg="white", font=("Arial", 12), state="disabled")
next_button.pack(side="left", padx=10)

save_button = tk.Button(control_frame, text="Save Results", command=save_results, bg="blue", fg="white", font=("Arial", 12), state="disabled")
save_button.pack(side="left", padx=10)


# 🔻 แบ่งซ้ายขวา Timing Results และ Log
main_content_frame = tk.Frame(root)
main_content_frame.pack(fill="both", expand=True, padx=10, pady=10)

left_frame = tk.Frame(main_content_frame)
left_frame.pack(side="left", fill="both", expand=True)

right_frame = tk.Frame(main_content_frame, width=300)
right_frame.pack(side="right", fill="y")

# ✅ Timing Results
result_frame = tk.LabelFrame(left_frame, text="Timing Results")
result_frame.pack(fill="both", expand=True)


# ✅ Log Box
log_label = tk.Label(right_frame, text="Log")
log_label.pack()
text_box = tk.Text(right_frame, height=30, width=40)
text_box.pack(fill="y", expand=True, padx=5)


client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
update_display_timer()
root.mainloop()