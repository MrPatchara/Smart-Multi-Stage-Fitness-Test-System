import paho.mqtt.client as mqtt
import tkinter as tk
from tkinter import ttk
import time
import threading
import pyttsx3
import platform
import os
import pygame
import queue
from tkinter import filedialog, messagebox, simpledialog, ttk
import json
from PIL import Image, ImageTk
import datetime
from tkinter import Toplevel, StringVar  # เพิ่ม StringVar ถ้ายังไม่มี
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Get the project root directory (parent of src/)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")

ATHLETE_FILE = os.path.join(DATA_DIR, "athletes.json")

# เก็บ athlete_id ของแต่ละ Player ที่เลือก
selected_player_ids = {f'Player {i}': None for i in range(1, 11)}

# ✅ เพิ่ม dictionary สำหรับ mapping HR sensor กับ Player
player_hr_mapping = {f'Player {i}': None for i in range(1, 11)}
player_hr_values = {f'Player {i}': "-" for i in range(1, 11)}  # เก็บค่า HR ล่าสุด

# เก็บค่า HR ที่จับระหว่างทดสอบ
hr_record = {f"Player {i}": [] for i in range(1, 11)}
recording_hr = False
recording_start_time = None

current_shuttle_start_time = time.time()

phase = {f'Player {i}': "A-B" for i in range(1, 11)}  # global


def load_athletes():
    if not os.path.exists(ATHLETE_FILE):
        return []
    with open(ATHLETE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        return data.get("athletes", [])

def save_athletes(athletes):
    with open(ATHLETE_FILE, "w", encoding="utf-8") as f:
        json.dump({"athletes": athletes}, f, indent=4)

def manage_athletes_window():
    athletes = load_athletes()
    image_cache = {}

    def refresh_table():
        for row in table.get_children():
            table.delete(row)
        for i, a in enumerate(athletes):
            values = (a["id"], a["first_name"], a["last_name"], a["sport"])
            img_path = a.get("photo_path", "")
            img = Image.new("RGB", (50, 50), color="gray")  # default image
            if os.path.exists(img_path):
                try:
                    img = Image.open(img_path).resize((60, 60))  # ✅ ปรับให้พอดีแถว

                except:
                    pass
            img_tk = ImageTk.PhotoImage(img)
            image_cache[i] = img_tk  # keep a reference
            table.insert("", "end", text="", image=img_tk, values=values)

    def get_next_available_id(athletes):
        used_ids = {int(a["id"]) for a in athletes if a.get("id")}
        i = 1
        while i in used_ids:
            i += 1
        return str(i)

    def add_athlete():
        athlete = edit_athlete_form()
        if athlete:
            athlete["id"] = get_next_available_id(athletes)  # ✅ ใช้ ID ที่ว่าง
            athletes.append(athlete)
            save_athletes(athletes)
            refresh_table()

    def edit_selected():
        selected = table.focus()
        if not selected:
            return
        index = int(table.index(selected))
        athlete = edit_athlete_form(athletes[index])
        if athlete:
            athlete["id"] = athletes[index]["id"]
            athletes[index] = athlete
            save_athletes(athletes)
            refresh_table()

    def delete_selected():
        selected = table.focus()
        if not selected:
            return
        index = int(table.index(selected))
        confirm = messagebox.askyesno("Delete", "Are you sure to delete this athlete?")
        if confirm:
            del athletes[index]
            save_athletes(athletes)
            refresh_table()

    win = tk.Toplevel()
    win.title("Manage Athletes")
    #✅ ปรับขนาดหน้าต่างเต็มจอ
    win.state('zoomed')  # ✅ เต็มจอ

    # ✅ Style เฉพาะหน้าต่างนี้
    style = ttk.Style()
    style.theme_use("default")
    style.configure("Custom.Treeview", rowheight=60)

    # ✅ ตาราง Treeview
    table = ttk.Treeview(
        win,
        columns=("ID", "First Name", "Last Name", "Sport"),
        show="tree headings",
        style="Custom.Treeview"
    )
    table.heading("#0", text="Photo")
    table.column("#0", width=60)

    table.heading("ID", text="ID")
    table.heading("First Name", text="First Name")
    table.heading("Last Name", text="Last Name")
    table.heading("Sport", text="Sport")

    table.column("ID", width=50, anchor="center")
    table.column("First Name", width=120, anchor="center")
    table.column("Last Name", width=120, anchor="center")
    table.column("Sport", width=120, anchor="center")


    table.pack(fill="both", expand=True, pady=10)

    btn_frame = tk.Frame(win)
    btn_frame.pack(pady=5)
    tk.Button(btn_frame, text="Add Athlete", command=add_athlete, bg="green", fg="white").pack(side="left", padx=5)
    tk.Button(btn_frame, text="Edit Selected", command=edit_selected, bg="blue", fg="white").pack(side="left", padx=5)
    tk.Button(btn_frame, text="Delete Selected", command=delete_selected, bg="red", fg="white").pack(side="left", padx=5)

    refresh_table()

def edit_athlete_form(existing=None):
    athlete = {} if existing is None else existing.copy()

    form = tk.Toplevel()
    form.title("Athlete Form")

    fields = ["first_name", "last_name", "age", "gender", "sport", "height", "weight"]
    entries = {}

    for i, field in enumerate(fields):
        tk.Label(form, text=field.replace("_", " ").title()).grid(row=i, column=0, sticky="e")
        var = tk.StringVar(value=str(athlete.get(field, "")))
        entries[field] = var
        tk.Entry(form, textvariable=var).grid(row=i, column=1)

    photo_path = tk.StringVar(value=athlete.get("photo_path", ""))
    def browse_photo():
        path = filedialog.askopenfilename(title="Select Profile Photo", filetypes=[("Images", "*.jpg *.png")])
        if path:
            photo_path.set(path)

    tk.Label(form, text="Profile Photo").grid(row=len(fields), column=0, sticky="e")
    tk.Entry(form, textvariable=photo_path, width=40).grid(row=len(fields), column=1)
    tk.Button(form, text="Browse", command=browse_photo).grid(row=len(fields), column=2)

    result = {}

    def submit():
        for field in fields:
            athlete[field] = entries[field].get()
        athlete["photo_path"] = photo_path.get()
        result["data"] = athlete
        form.destroy()

    tk.Button(form, text="Save", command=submit).grid(row=len(fields)+1, columnspan=2, pady=10)
    form.wait_window()

    return result.get("data")

def select_player_from_database(player_key, chk_button):
    try:
        with open("athletes.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            athletes = data.get("athletes", [])
    except Exception as e:
        messagebox.showerror("Error", f"Failed to load athletes.json: {e}")
        return

    # สร้างหน้าต่าง popup
    win = tk.Toplevel()
    win.title(f"Select Athlete for {player_key}")
    win.geometry("400x300")

    listbox = tk.Listbox(win, font=("Arial", 12))
    listbox.pack(fill="both", expand=True, padx=10, pady=10)

    # ใส่ชื่อ + sport ลง Listbox
    for athlete in athletes:
        full_name = f"{athlete['first_name']} {athlete['last_name']}"
        display_text = f"{full_name} ({athlete['sport']})"
        listbox.insert(tk.END, display_text)

    def confirm_selection():
        index = listbox.curselection()
        if not index:
            return
        athlete = athletes[index[0]]
        full_name = f"{athlete['first_name']} {athlete['last_name']}"
        player_names[player_key] = full_name
        selected_player_ids[player_key] = athlete["id"]

        chk_button.config(text=full_name)  # ✅ เปลี่ยนชื่อที่ checkbox
        win.destroy()
        update_table()

    tk.Button(win, text="Select", command=confirm_selection).pack(pady=10)


def view_test_history():
    try:
        with open("test_results.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            results = data.get("results", [])
    except:
        results = []

    try:
        with open("athletes.json", "r", encoding="utf-8") as f:
            athletes_data = json.load(f).get("athletes", [])
            athlete_dict = {a["id"]: a for a in athletes_data}
    except:
        athlete_dict = {}

    win = tk.Toplevel()
    win.title("Test History")
    win.state('zoomed')

    tree = ttk.Treeview(
        win,
        columns=("Name", "Date", "Test Type", "Result", "Distance", "VO2max"),
        show="headings",
        selectmode="browse"
    )
    tree.heading("Name", text="Name")
    tree.heading("Date", text="Date")
    tree.heading("Test Type", text="Test Type")
    tree.heading("Result", text="Result")
    tree.heading("Distance", text="Distance (m)")
    tree.heading("VO2max", text="VO₂max (ml/kg/min)")

    tree.pack(fill="both", expand=True, padx=10, pady=10)

    for i, r in enumerate(results):
        athlete_id = str(r.get("athlete_id", ""))
        athlete = athlete_dict.get(athlete_id, {})
        name = f"{r['first_name']} {r['last_name']}"
        result_text = r.get("result", "")
        level, shuttle = extract_level_shuttle(result_text)
        test_type = r["test_type"]
        distance = 0
        vo2max = "-"

        try:
            if "Beep Test" in test_type:
                distance = get_beep_test_distance(level, shuttle)
                vo2max = get_beep_vo2max(level, shuttle)
            elif test_type == "YYIR1 test":
                distance = get_yoyo_ir1_distance(level, shuttle)
                vo2max = get_yoyo_ir1_vo2max(distance)
            elif test_type == "YYIR2 test":
                distance = get_yoyo_ir2_distance(level, shuttle)
                vo2max = get_yoyo_ir2_vo2max(distance)
        except:
            vo2max = "-"

        tree.insert("", "end", iid=str(i), values=(
            name,
            r["date"],
            test_type,
            result_text,
            distance,
            vo2max,
        ))

    def delete_selected_result():
        selected = tree.focus()
        if not selected:
            messagebox.showwarning("Warning", "Please select a result to delete.")
            return

        confirm = messagebox.askyesno("Confirm", "Are you sure you want to delete this result?")
        if confirm:
            index = int(selected)
            del results[index]
            with open("test_results.json", "w", encoding="utf-8") as f:
                json.dump({"results": results}, f, indent=4)
            tree.delete(selected)
            messagebox.showinfo("Deleted", "Result deleted successfully.")

    def view_selected_result():
        selected = tree.focus()
        if not selected:
            messagebox.showwarning("Warning", "Please select a result to view.")
            return
        index = int(selected)
        if 0 <= index < len(results):
            view_result_details(results[index])

    def export_selected_to_pdf():
        selected = tree.focus()
        if not selected:
            messagebox.showwarning("Warning", "Please select a result to export.")
            return
        index = int(selected)
        export_pdf_beep_test(results[index])

    button_frame = tk.Frame(win)
    button_frame.pack(pady=5)

    delete_button = tk.Button(button_frame, text="Delete Selected", command=delete_selected_result, bg="red", fg="white", font=("Arial", 11), width=18)
    delete_button.pack(side="left", padx=5)

    view_button = tk.Button(button_frame, text="View Selected", command=view_selected_result, bg="green", fg="white", font=("Arial", 11), width=18)
    view_button.pack(side="left", padx=5)

    export_button = tk.Button(button_frame, text="Export PDF", command=export_selected_to_pdf, bg="darkred", fg="white", font=("Arial", 11), width=18)
    export_button.pack(side="left", padx=5)





# ------------------------------
# ✅ Helper Functions
# ------------------------------

def extract_level_shuttle(result_text):
    try:
        parts = result_text.replace("Level", "").replace("Shuttle", "").split(",")
        level = int(parts[0].strip())
        shuttle = int(parts[1].strip())
        return level, shuttle
    except:
        return 0, 0

def get_beep_test_distance(level, shuttle):
    # ตารางจำนวน shuttle ต่อ level (ตามมาตรฐาน Ramsbottom & Léger)
    shuttles_per_level = {
        1: 7, 2: 8, 3: 8, 4: 9, 5: 9,
        6: 10, 7: 10, 8: 11, 9: 11,
        10: 11, 11: 12, 12: 12, 13: 13,
        14: 13, 15: 13, 16: 14, 17: 14,
        18: 15, 19: 15, 20: 16, 21: 16
    }

    total_shuttles = 0

    # สะสม shuttle ของทุก level ก่อนหน้า
    for l in range(1, level):
        total_shuttles += shuttles_per_level.get(l, 0)

    # เพิ่ม shuttle ของ level ปัจจุบัน
    total_shuttles += shuttle

    return total_shuttles * 20  # ระยะทาง 1 shuttle = 20 เมตร


# ตารางจำนวน shuttle ต่อ level สำหรับ YYIR1
shuttles_per_level_ir1 = {
    5: 1, 8: 1, 11: 2, 12: 3, 13: 4, 14: 8, 15: 8,
    16: 8, 17: 8, 18: 8, 19: 8, 20: 8, 21: 8,
    22: 8, 23: 8
}

# ตารางสำหรับ YYIR2 (คุณสามารถปรับให้ตรงตามโปรโตคอลที่คุณใช้จริง)
shuttles_per_level_ir2 = {
    11: 1, 15: 1, 17: 2, 18: 3, 19: 4, 20: 8, 21: 8,
    22: 8, 23: 8, 24: 8, 25: 8, 26: 8, 27: 8, 27: 8, 28: 8, 29: 8
}

def get_yoyo_ir1_distance(level, shuttle):
    total_shuttles = 0
    for l in range(1, level):
        total_shuttles += shuttles_per_level_ir1.get(l, 0)
    total_shuttles += shuttle
    return total_shuttles * 40  # 1 shuttle = 40m

def get_yoyo_ir2_distance(level, shuttle):
    total_shuttles = 0
    for l in range(1, level):
        total_shuttles += shuttles_per_level_ir2.get(l, 0)
    total_shuttles += shuttle
    return total_shuttles * 40

def get_beep_vo2max(level, shuttle):
    if level == 0:
        return 0.0
    try:
        vo2max = 3.46 * (level + shuttle / (level * 0.4325 + 7.0048)) + 12.2
        return round(vo2max, 2)
    except ZeroDivisionError:
        return 0.0

def get_yoyo_ir1_vo2max(distance):
    return round(distance * 0.0084 + 36.4, 2)

def get_yoyo_ir2_vo2max(distance):
    return round(distance * 0.0136 + 45.3, 2)

def extract_level_shuttle(result_text):
    try:
        parts = result_text.replace("Level", "").replace("Shuttle", "").split(",")
        level = int(parts[0].strip())
        shuttle = int(parts[1].strip())
        return level, shuttle
    except:
        return 0, 0

def connect_mqtt(broker_ip):
    """เชื่อมต่อกับ MQTT Broker โดยใช้ค่า IP จาก GUI"""
    global client
    client = mqtt.Client()
    client.on_message = on_message
    try:
        client.connect(broker_ip, 1883)  # ✅ ใช้ค่าจาก GUI
        client.subscribe("fitness_test/#")
        client.subscribe("hr/#")  # ✅ เพิ่มบรรทัดนี้
        client.loop_start()
        timer_label.config(text=f"Connected to {broker_ip}", fg="green")
    except Exception as e:
        timer_label.config(text="Connection Failed", fg="red")

# ✅ สร้าง dictionary เก็บชื่อของ Player
player_names = {f'Player {i}': f'Player {i}' for i in range(1, 11)}
selected_player_ids = {f'Player {i}': None for i in range(1, 11)}  # เก็บ athlete_id

# ✅ ตัวแปรสำหรับเก็บจำนวน Warning สูงสุด (ค่าเริ่มต้นคือ 2)
max_warnings = 2

# ✅ ฟังก์ชันสำหรับตั้งค่า Warning
def set_max_warnings():
    global max_warnings
    try:
        new_value = int(warning_var.get())
        if new_value >= 0:
            max_warnings = new_value
            speak_text(f"Maximum warnings set to {max_warnings}")
        else:
            speak_text("Please enter a value 0 or higher.")
    except ValueError:
        speak_text("Invalid input. Please enter a valid number.")


def change_player_name(player, chk_button):
    """ เปลี่ยนชื่อ Player และอัปเดต Checkbox """
    new_name = simpledialog.askstring("Change Player Name", f"Enter new name for {player}:")
    if new_name:
        player_names[player] = new_name  # ✅ อัปเดตชื่อใน dictionary
        chk_button.config(text=new_name)  # ✅ อัปเดตชื่อที่ Checkbox
        root.after(0, update_table)  # ✅ อัปเดต GUI

# ตั้งค่าเสียงพูด
engine = pyttsx3.init()
engine.setProperty("rate", 150)  # ปรับความเร็วเสียงพูด
speech_queue = queue.Queue()

def speech_worker():
    """ รันคิวข้อความที่ต้องพูด เพื่อป้องกัน run loop already started """
    while True:
        text = speech_queue.get()
        engine.say(text)
        engine.runAndWait()
        speech_queue.task_done()

# เริ่ม thread สำหรับพูด
speech_thread = threading.Thread(target=speech_worker, daemon=True)
speech_thread.start()

def speak_text(text):
    """ ใส่ข้อความเข้า queue เพื่อป้องกันการเรียกซ้อนกันของ pyttsx3 """
    speech_queue.put(text)

# ตั้งค่า pygame สำหรับเล่นไฟล์เสียง
pygame.mixer.init()

def play_beep(beep_type="shuttle"):
    """ เล่นเสียง Beep จากไฟล์ """
    if beep_type == "shuttle":
        pygame.mixer.music.load("beep.mp3")
    elif beep_type == "level":
        pygame.mixer.music.load("double_beep.mp3")
    
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():  # รอให้เสียงเล่นจบก่อน
        time.sleep(0.1)

def play_yoyo_beep(beep_type="shuttle"):
    """ เล่นเสียง Beep สำหรับ Yo-Yo Test แบบแยกเฉพาะ """
    if beep_type == "shuttle":
        pygame.mixer.music.load("yoyo_beep.mp3")
    elif beep_type == "level":
        pygame.mixer.music.load("yoyo_double_beep.mp3")

    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        time.sleep(0.1)

# ✅ โปรโตคอลที่สามารถเลือกได้
# ✅ Standard Beep Test
protocols_beep = {
    "Standard Beep Test": [
        {"level": 1, "shuttles": 7, "time_per_shuttle": 9},
    {"level": 2, "shuttles": 8, "time_per_shuttle": 8},
    {"level": 3, "shuttles": 8, "time_per_shuttle": 7.58},
    {"level": 4, "shuttles": 9, "time_per_shuttle": 7.2},
    {"level": 5, "shuttles": 9, "time_per_shuttle": 6.86},
    {"level": 6, "shuttles": 10, "time_per_shuttle": 6.55},
    {"level": 7, "shuttles": 10, "time_per_shuttle": 6.26},
    {"level": 8, "shuttles": 11, "time_per_shuttle": 6},
    {"level": 9, "shuttles": 11, "time_per_shuttle": 5.76},
    {"level": 10, "shuttles": 11, "time_per_shuttle": 5.54},
    {"level": 11, "shuttles": 12, "time_per_shuttle": 5.33},
    {"level": 12, "shuttles": 12, "time_per_shuttle": 5.14},
    {"level": 13, "shuttles": 13, "time_per_shuttle": 4.97},
    {"level": 14, "shuttles": 13, "time_per_shuttle": 4.8},
    {"level": 15, "shuttles": 13, "time_per_shuttle": 4.65},
    {"level": 16, "shuttles": 14, "time_per_shuttle": 4.5},
    {"level": 17, "shuttles": 14, "time_per_shuttle": 4.36},
    {"level": 18, "shuttles": 15, "time_per_shuttle": 4.24},
    {"level": 19, "shuttles": 15, "time_per_shuttle": 4.11},
    {"level": 20, "shuttles": 16, "time_per_shuttle": 4},
    {"level": 21, "shuttles": 16, "time_per_shuttle": 3.89},
    ]
}

# ✅ Yo-Yo Intermittent Recovery Test Level 1
protocols_yoyo = {
    "Yo-Yo Intermittent Recovery Test Level 1": [
        {"level": 5, "shuttle": 1, "A-B": 7, "B-A": 7, "rest_time": 10},
        {"level": 9, "shuttle": 1, "A-B": 6.26, "B-A": 6.26, "rest_time": 10},
        {"level": 11, "shuttle": 2, "A-B": 5.53846, "B-A": 5.53846, "rest_time": 10},
        {"level": 12, "shuttle": 3, "A-B": 5.33333, "B-A": 5.33333, "rest_time": 10},
        {"level": 13, "shuttle": 4, "A-B": 5.14286, "B-A": 5.14286, "rest_time": 10},
        {"level": 14, "shuttle": 8, "A-B": 4.96552, "B-A": 4.96552, "rest_time": 10},
        {"level": 15, "shuttle": 8, "A-B": 4.8, "B-A": 4.8, "rest_time": 10},
        {"level": 16, "shuttle": 8, "A-B": 4.64516, "B-A": 4.64516, "rest_time": 10},
        {"level": 17, "shuttle": 8, "A-B": 4.5, "B-A": 4.5, "rest_time": 10},
        {"level": 18, "shuttle": 8, "A-B": 4.36364, "B-A": 4.36364, "rest_time": 10},
        {"level": 19, "shuttle": 8, "A-B": 4.23529, "B-A": 4.23529, "rest_time": 10},
        {"level": 20, "shuttle": 8, "A-B": 4.11429, "B-A": 4.11429, "rest_time": 10},
        {"level": 21, "shuttle": 8, "A-B": 4, "B-A": 4, "rest_time": 10},
        {"level": 22, "shuttle": 8, "A-B": 3.89189, "B-A": 3.89189, "rest_time": 10},
        {"level": 23, "shuttle": 8, "A-B": 3.78947, "B-A": 3.78947, "rest_time": 10},
    ]
}

# ✅ Protocol สำหรับ Yo-Yo Level 2 แยกจาก Level 1
protocols_yoyo2 = {
    "Yo-Yo Intermittent Recovery Test Level 2": [
        {"level": 11, "shuttle": 1, "A-B":  5.53846, "B-A":  5.53846, "rest_time": 10},
        {"level": 15, "shuttle": 1, "A-B": 4.8, "B-A": 4.8, "rest_time": 10},
        {"level": 17, "shuttle": 2, "A-B": 4.5, "B-A": 4.5, "rest_time": 10},
        {"level": 18, "shuttle": 3, "A-B": 4.36364, "B-A": 4.36364, "rest_time": 10},
        {"level": 19, "shuttle": 4, "A-B": 4.23529, "B-A": 4.23529, "rest_time": 10},
        {"level": 20, "shuttle": 8, "A-B": 4.11429, "B-A": 4.11429, "rest_time": 10},
        {"level": 21, "shuttle": 8, "A-B": 4, "B-A": 4, "rest_time": 10},
        {"level": 22, "shuttle": 8, "A-B": 3.89189, "B-A": 3.89189, "rest_time": 10},
        {"level": 23, "shuttle": 8, "A-B": 3.78947, "B-A": 3.78947, "rest_time": 10},
        {"level": 24, "shuttle": 8, "A-B": 3.69231, "B-A": 3.69231, "rest_time": 10},
        {"level": 25, "shuttle": 8, "A-B": 3.6, "B-A": 3.6, "rest_time": 10},
        {"level": 26, "shuttle": 8, "A-B": 3.51219, "B-A": 3.51219, "rest_time": 10},
        {"level": 27, "shuttle": 8, "A-B": 3.42857, "B-A": 3.42857, "rest_time": 10},
        {"level": 28, "shuttle": 8, "A-B": 3.34884, "B-A": 3.34884, "rest_time": 10},
        {"level": 29, "shuttle": 8, "A-B": 3.27273, "B-A": 3.27273, "rest_time": 10}
    ]
}

yo_yo_mode = None

def set_protocol():
    """เลือกโปรโตคอลและอัปเดตการทำงาน"""
    global protocol, is_yo_yo_test, is_yo_yo_level_2, yo_yo_mode

    selected = selected_protocol.get()

    if selected in protocols_beep:
        protocol = protocols_beep[selected]
        is_yo_yo_test = False
        is_yo_yo_level_2 = False
        yo_yo_mode = None  # ✅ ไม่ใช่ Yo-Yo Test
        speak_text(f"{selected} selected")

    elif selected in protocols_yoyo:
        protocol = protocols_yoyo[selected]
        is_yo_yo_test = True
        is_yo_yo_level_2 = False
        yo_yo_mode = "YYIR1"  # ✅ ชนิดของ Yo-Yo
        speak_text(f"{selected} selected")

    elif selected in protocols_yoyo2:
        protocol = protocols_yoyo2[selected]
        is_yo_yo_test = True
        is_yo_yo_level_2 = True
        yo_yo_mode = "YYIR2"  # ✅ ชนิดของ Yo-Yo
        speak_text(f"{selected} selected")

    update_table_header()
    reset_test()
    start_button["state"] = "normal"
    # ✅ รีเซ็ตหน้าต่าง: ย่อแล้วขยายเต็มจอใหม่
    root.state("normal")
    root.update_idletasks()
    root.state("zoomed")
    # ✅ ปิดการใช้งานปุ่ม Set Protocol
    set_protocol_button["state"] = "disabled"

def speak_yo_yo(level, shuttle, is_recovery=False, is_change=False):
    """พูด Speed Level และ Recovery ตามลำดับที่ถูกต้อง"""
    if is_recovery:
        speak_text("Recovery")
    elif is_change:
        speak_text(f"change to speed LEVEL: {level} , {shuttle}")
    else:
        speak_text(f"speed LEVEL: {level} , {shuttle}")

def start_yo_yo_test():
    """เริ่ม Yo-Yo Test"""
    global current_level, current_shuttle, running
    
    if not running:
        return

    if current_level >= len(protocol):
        running = False
        return

    level_data = protocol[current_level]
    num_shuttles = level_data["shuttle"]

    if current_shuttle > num_shuttles:
        current_level += 1
        current_shuttle = 1
        if current_level >= len(protocol):
            running = False
            return

    # ✅ พูด Speed Level ก่อนเริ่ม A → B (พูดครั้งเดียว)
    if current_shuttle == 1:
        if current_level == 0:
            speak_yo_yo(level_data["level"], current_shuttle)
        else:
            speak_yo_yo(level_data["level"], current_shuttle, is_change=True)
    
    countdown_yo_yo(level_data["A-B"], "A-B")

def countdown_yo_yo(duration, direction):
    """นับเวลาถอยหลังแบบแม่นยำ (real-time) สำหรับ A-B หรือ B-A"""
    global running
    start_time = time.time()

    def update():
        if not running:
            return

        elapsed = time.time() - start_time
        remaining = duration - elapsed

        if remaining <= 0:
            root.after(0, timer_label.config(text=f"{direction} Done"))

            if direction == "A-B":
                # ✅ เล่นเสียง beep ทันที
                threading.Thread(target=play_yoyo_beep, args=("shuttle",), daemon=True).start()

                # ✅ เริ่ม B-A ทันที ไม่รอดีเลย์ 1 วินาที
                countdown_yo_yo(protocol[current_level]["B-A"], "B-A")
            elif direction == "B-A":
                root.after(0, check_yo_yo_shuttle_completion)
            return

        # ✅ แสดงเวลาที่เหลือจริง
        root.after(0, timer_label.config(text=f"{direction} | Time Left: {remaining:.1f}s"))
        root.after(10, update)  # วนถี่ขึ้น 10ms เพื่อความลื่นและแม่น

    update()



def check_yo_yo_shuttle_completion():
    global running
    with lock:
        for player in selected_players:
            if player_status[player] == "Disqualified":
                continue

            passed_A = passed_checkpoints[player]["A"]
            passed_B = passed_checkpoints[player]["B"]

            if passed_A and passed_B:
                player_status[player] = "Passed"
            else:
                if max_warnings == 0:
                    player_status[player] = "Disqualified"
                else:
                    warning_count[player] += 1
                    if warning_count[player] >= max_warnings:
                        player_status[player] = "Disqualified"
                    else:
                        player_status[player] = "Warning"

            # ✅ รีเซ็ตทุกอย่างเพื่อ shuttle ถัดไป
            passed_checkpoints[player] = {"A": False, "B": False}
            checkpoint_time[player] = {"A": None, "B": None}
            phase[player] = "A-B"
            if player_status[player] != "Disqualified":
                player_status[player] = "Waiting"

    root.after(0, update_table)
    root.after(500, rest_before_next_yo_yo_shuttle)


def rest_before_next_yo_yo_shuttle():
    """พัก 10 วินาทีก่อนเริ่ม Shuttle ใหม่ พร้อมนับถอยหลังแสดงผล"""
    global current_shuttle, current_level, running
    with lock:
        if not running:
            return

        level_data = protocol[current_level]
        rest_time = level_data["rest_time"]

        # ✅ พูด "Recovery" ก่อนพัก
        speak_yo_yo(level_data["level"], current_shuttle, is_recovery=True)

        # ✅ เล่น beep ช่วงเริ่ม Recovery
        threading.Thread(target=play_yoyo_beep, args=("shuttle",), daemon=True).start()

    # ✅ เริ่มจับเวลาจริงหลังจากปล่อย lock
    start_time = time.time()

    def update_recovery():
        if not running:
            return
        elapsed = time.time() - start_time
        remaining = rest_time - elapsed

        if remaining <= 0:
            root.after(0, timer_label.config(text="Recovery Done"))
            reset_yo_yo_shuttle()
        else:
            # ✅ แสดงเวลาที่เหลือใน Recovery
            root.after(0, timer_label.config(text=f"Recovery | Time Left: {remaining:.1f}s"))
            root.after(50, update_recovery)  # อัปเดตทุก 50ms พอเหมาะ ไม่หนักระบบ

    update_recovery()


def reset_yo_yo_shuttle():
    """รีเซ็ต Shuttle และเริ่ม Shuttle ใหม่"""
    global current_shuttle, current_level, running, current_shuttle_start_time
    with lock:
        if not running:
            return

        level_data = protocol[current_level]
        num_shuttles = level_data["shuttle"]
        level_up = current_shuttle >= num_shuttles  # ✅ ตรวจว่าเป็น shuttle สุดท้ายไหม

        if level_up:
            current_level += 1
            current_shuttle = 1
        else:
            current_shuttle += 1

        if current_level >= len(protocol):
            running = False
            return

        current_shuttle_start_time = time.time()

        def beep_and_start():
            if level_up:
                play_yoyo_beep("level")  # ✅ double beep เมื่อเปลี่ยนระดับ
            else:
                play_yoyo_beep("shuttle")  # ✅ beep ปกติ

            # ✅ เริ่ม shuttle ใหม่หลัง beep (ไม่รอ 1 วิ เต็ม)
            root.after(100, start_yo_yo_test)

        threading.Thread(target=beep_and_start, daemon=True).start()

        for player in selected_players:
            if player_status[player] not in ["Disqualified"]:
                passed_checkpoints[player] = {"A": False, "B": False}
                player_status[player] = "Waiting"

        root.after(0, update_table)


def start_beep_test():
    """เริ่ม Beep Test"""
    global current_level, current_shuttle, running

    if not running:
        return

    if current_level >= len(protocol):
        running = False
        return

    level_data = protocol[current_level]
    num_shuttles = level_data["shuttles"]
    time_per_shuttle = level_data["time_per_shuttle"]

    if current_shuttle > num_shuttles:
        current_level += 1
        current_shuttle = 1
        if current_level >= len(protocol):
            running = False
            return

    countdown(time_per_shuttle)

def check_beep_shuttle_completion():
    """ตรวจสอบ Shuttle Completion สำหรับ Beep Test"""
    global running
    with lock:
        for player in selected_players:
            if player_status[player] == "Disqualified":
                continue

            passed_A = passed_checkpoints[player]["A"]
            passed_B = passed_checkpoints[player]["B"]

            if passed_A and passed_B:
                if player_status[player] != "Disqualified":
                    player_status[player] = "Passed"
            else:
                if max_warnings == 0:
                    player_status[player] = "Disqualified"
                else:
                    warning_count[player] += 1
                    if warning_count[player] >= max_warnings:
                        player_status[player] = "Disqualified"
                    else:
                        player_status[player] = "Warning"

            passed_checkpoints[player] = {"A": False, "B": False}

    root.after(0, update_table)
    reset_beep_shuttle()  # ✅ เริ่ม shuttle ถัดไปทันที

def reset_beep_shuttle():
    """รีเซ็ต Shuttle และเริ่ม Shuttle ใหม่"""
    global current_shuttle, current_level, running
    with lock:
        if not running:
            return

        level_up = current_shuttle >= protocol[current_level]["shuttles"]

        if level_up:
            current_level += 1
            current_shuttle = 1
        else:
            current_shuttle += 1

        if current_level >= len(protocol):
            running = False
            return

        def beep_and_speak_and_start():
            if level_up:
                pygame.mixer.music.load("double_beep.mp3")
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)
                speak_text(f"Level {current_level + 1}")
            else:
                pygame.mixer.music.load("beep.mp3")
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)
                speak_text(f"Level {current_level + 1} - Shuttle {current_shuttle}")

            # ✅ เริ่ม Beep Test ทันทีหลังพูดจบ
            time.sleep(0.2)  # (optional) เว้นระยะหายใจเล็กน้อย
            root.after(0, start_beep_test)

        threading.Thread(target=beep_and_speak_and_start, daemon=True).start()

        for player in selected_players:
            if player_status[player] not in ["Disqualified"]:
                passed_checkpoints[player] = {"A": False, "B": False}
                player_status[player] = "Waiting"

        root.after(0, update_table)


current_level = 0
current_shuttle = 1
running = True
lock = threading.Lock()
warning_count = {f'Player {i}': 0 for i in range(1, 11)}

selected_players = {f'Player {i}': False for i in range(1, 11)}
player_status = {f'Player {i}': "Waiting" for i in range(1, 11)}
passed_checkpoints = {f'Player {i}': {"A": False, "B": False} for i in range(1, 11)}
checkpoint_time = {f'Player {i}': {"A": None, "B": None} for i in range(1, 11)}

def start_protocol():
    """ เริ่มโปรโตคอลและควบคุมการทำงานของ Shuttle Test """
    global current_level, current_shuttle, running
    if not running:
        return

    if current_level >= len(protocol):
        running = False
        return

    level_data = protocol[current_level]
    num_shuttles = level_data["shuttles"]
    time_per_shuttle = level_data["time_per_shuttle"]

    if current_shuttle > num_shuttles:
        current_level += 1
        current_shuttle = 1
        if current_level >= len(protocol):
            running = False
            return

    # ✅ เล่นเสียง Beep และเริ่มนับเวลาพร้อมกัน
    countdown(time_per_shuttle)

def countdown(duration):
    """ นับเวลาถอยหลังแบบแม่นยำโดยใช้ time.time() """
    global running
    start_time = time.time()

    def update():
        if not running:
            return

        elapsed = time.time() - start_time
        remaining = duration - elapsed

        if remaining <= 0:
            root.after(0, timer_label.config(
                text=f"Level: {current_level + 1} | Shuttle: {current_shuttle} | Time Left: 0.0s"
            ))
            root.after(0, check_shuttle_completion)  # ✅ เรียกทันที ไม่ delay 500ms
            return

        # ✅ แสดงเวลาที่เหลือจริง
        root.after(0, timer_label.config(
            text=f"Level: {current_level + 1} | Shuttle: {current_shuttle} | Time Left: {remaining:.1f}s"
        ))

        root.after(10, update)  # ✅ อัปเดตถี่ทุก 10ms เพื่อความแม่นยำ

    update()


def check_shuttle_completion():
    """ตรวจสอบ Shuttle Completion สำหรับ Beep Test"""
    global running
    with lock:
        for player in selected_players:
            if player_status[player] == "Disqualified":
                continue  # ✅ ข้ามผู้เล่นที่ถูก Disqualified แล้ว

            passed_A = passed_checkpoints[player]["A"]
            passed_B = passed_checkpoints[player]["B"]

            # ✅ เงื่อนไข 1: ถ้าผ่านทั้ง A และ B ถือว่าสำเร็จ
            if passed_A and passed_B:
                if player_status[player] != "Disqualified":
                    player_status[player] = "Passed"
                # ❌ ไม่รีเซ็ต Warning เพื่อให้สะสมได้

            else:
                # ✅ เงื่อนไข 2: ถ้าไม่ผ่าน ให้ตรวจสอบค่าของ max_warnings
                if max_warnings == 0:
                    # ✅ ถ้า max_warnings = 0 → Disqualified ทันที
                    player_status[player] = "Disqualified"
                else:
                    # ✅ เพิ่มจำนวน Warning
                    warning_count[player] += 1

                    # ✅ ตรวจสอบว่าจำนวน Warning ถึง max_warnings หรือยัง
                    if warning_count[player] >= max_warnings:
                        player_status[player] = "Disqualified"
                    else:
                        player_status[player] = "Warning"

            # ✅ รีเซ็ตค่าการตรวจสอบสำหรับ Shuttle ถัดไป
            passed_checkpoints[player] = {"A": False, "B": False}

    root.after(0, update_table)  # ✅ อัปเดต GUI
    root.after(500, reset_beep_shuttle)  # ✅ ไปยัง Shuttle ถัดไป

def reset_shuttle():
    """ รีเซ็ต Shuttle และเริ่ม Shuttle ใหม่ """
    global current_shuttle, current_level, running
    with lock:
        if not running:
            return

        # เช็คว่ากำลังเปลี่ยน Level หรือไม่
        level_up = current_shuttle >= protocol[current_level]["shuttles"]

        if level_up:
            current_level += 1
            current_shuttle = 1
        else:
            current_shuttle += 1

        if current_level >= len(protocol):
            running = False
            return

        # ✅ เล่นเสียง Beep ก่อนพูด (ตัด Beep ที่ซ้ำหลังพูดออก)
        def beep_and_speak():
            if level_up:
                pygame.mixer.music.load("double_beep.mp3")
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():  # ✅ รอเสียง Beep จบก่อนพูด
                    time.sleep(0.1)
                speak_text(f"Level {current_level + 1}")  # ✅ พูด Level ใหม่
            else:
                pygame.mixer.music.load("beep.mp3")
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():  # ✅ รอเสียง Beep จบก่อนพูด
                    time.sleep(0.1)
                speak_text(f"Level {current_level + 1} - Shuttle {current_shuttle}")  # ✅ พูด Shuttle (ไม่มี Beep ซ้ำ)

        threading.Thread(target=beep_and_speak, daemon=True).start()

        # ✅ รีเซ็ตเฉพาะคนที่ยังไม่ Disqualified
        for player in selected_players:
            if player_status[player] not in ["Disqualified"]:
                passed_checkpoints[player] = {"A": False, "B": False}
                player_status[player] = "Waiting"

        root.after(0, update_table)

    # ✅ เริ่ม Shuttle ถัดไปทันที ไม่ต้องดีเลย์
    root.after(1000, start_protocol)

def reset_checkpoint_after_A_B(player):
    with lock:
        passed_checkpoints[player] = {"A": False, "B": False}
        checkpoint_time[player] = {"A": None, "B": None}
        if player_status[player] != "Disqualified":
            player_status[player] = "Waiting"
    root.after(0, update_table)

def reset_status_if_not_disqualified(player):
    with lock:
        if player_status[player] != "Disqualified":
            player_status[player] = "Waiting"
    root.after(0, update_table)

def on_message(client, userdata, msg):
    """รับข้อมูลจาก MQTT"""
    sensor_data = msg.topic.split("/")[-1]

    # ✅ ตรวจจับ HR Topic เช่น hr/HR1
    if msg.topic.startswith("hr/"):
        hr_sensor = sensor_data  # เช่น HR1, HR2
        hr_value = msg.payload.decode()

        # หา Player ที่จับคู่กับ HR sensor ตัวนี้
        for player, hr in player_hr_mapping.items():
            if hr == hr_sensor:
                player_hr_values[player] = hr_value
                root.after(0, update_table)
                break
        return  # ✅ ไม่ต้องไปต่อ ถ้าเป็น HR message

    # ✅ ตรวจจับสถานะเซ็นเซอร์ athlete_status_*
    sensor_mapping = {}
    for i in range(10):
        player = f"Player {i+1}"
        sensor_mapping[f"athlete_status_{chr(65 + i * 2)}"] = (player, "A")
        sensor_mapping[f"athlete_status_{chr(66 + i * 2)}"] = (player, "B")

    if sensor_data in sensor_mapping:
        player, checkpoint = sensor_mapping[sensor_data]
        if selected_players[player]:
            now = time.time()
            if now < current_shuttle_start_time:
                return  # ป้องกัน signal เก่า

            with lock:
                if is_yo_yo_test:
                    if phase[player] == "A-B" and checkpoint == "B":
                        passed_checkpoints[player]["B"] = True
                        checkpoint_time[player]["B"] = now
                        player_status[player] = "Passed"  # แสดงผลว่า B ผ่าน
                        phase[player] = "B-A"  # รอไป A
                        root.after(500, lambda: reset_status_if_not_disqualified(player))  # แค่ reset view

                    elif phase[player] == "B-A" and checkpoint == "A":
                        passed_checkpoints[player]["A"] = True
                        checkpoint_time[player]["A"] = now
                        player_status[player] = "Passed"  # แสดงว่ากลับมาครบ

                else:
                    passed_checkpoints[player][checkpoint] = True
                    checkpoint_time[player][checkpoint] = now
                    if passed_checkpoints[player]["A"] and passed_checkpoints[player]["B"]:
                        player_status[player] = "Passed"

            root.after(0, update_table)


# ✅ แยกเก็บผลลัพธ์สำหรับ Beep Test และ Yo-Yo Test
player_results_beep = {f'Player {i}': "" for i in range(1, 11)}
player_results_yoyo = {f'Player {i}': "" for i in range(1, 11)}

def update_table():
    """อัปเดตตารางผลลัพธ์แยกกันสำหรับ Beep Test และ Yo-Yo Test"""
    tree.delete(*tree.get_children())  # ✅ ลบข้อมูลเก่าทั้งหมด

    for player, status in player_status.items():
        if selected_players[player]:
            # ✅ ตั้งค่าสีตามสถานะของผู้เล่น
            color = (
                "green" if status == "Passed" else 
                "orange" if status == "Warning" else 
                "red" if status in ["Disqualified", "Fails"] else "white"
            )

            # ✅ แสดงจำนวน Warnings ที่สะสมได้
            display_name = f"{player_names[player]} ({warning_count[player]} warnings)" if warning_count[player] > 0 else player_names[player]

            # ✅ แยกการแสดงผลระหว่าง Beep Test และ Yo-Yo Test
            if is_yo_yo_test:
                level_data = protocol[current_level] if current_level < len(protocol) else {}

                if status in ["Fails", "Disqualified"] and not player_results_yoyo[player]:
                    player_results_yoyo[player] = f"Level {level_data.get('level', '-')}, Shuttle {current_shuttle}"

                result_text = player_results_yoyo[player] if player_results_yoyo[player] else "-"

                tree.insert("", "end", values=(
                    display_name,
                    status,
                    level_data.get("level", "-"),
                    current_shuttle,
                    player_hr_values[player],  # ✅ แสดง HR ที่ผูกไว้
                    result_text
                ), tags=(color,))
            else:
                # ✅ สำหรับ Beep Test
                level_data = protocol[current_level] if current_level < len(protocol) else {}

                if status in ["Fails", "Disqualified"] and not player_results_beep[player]:
                    player_results_beep[player] = f"Level {level_data.get('level', '-')}, Shuttle {current_shuttle}"

                result_text = player_results_beep[player] if player_results_beep[player] else "-"

                tree.insert("", "end", values=(
                    display_name,
                    status,
                    level_data.get("level", "-"),
                    current_shuttle,
                    player_hr_values[player],  # ✅ แสดง HR ที่ผูกไว้
                    result_text
                ), tags=(color,))

    # ✅ การตั้งค่าสีของแถวตามสถานะ
    tree.tag_configure("green", background="lightgreen")
    tree.tag_configure("orange", background="yellow")
    tree.tag_configure("red", background="lightcoral")

def start_test():
    """เริ่มต้นการทดสอบตามโปรโตคอลที่เลือก"""
    global running
    running = True
    start_button.config(state="disabled")
    reset_button.config(state="normal")
    finish_button["state"] = "normal"
    
    play_beep("shuttle")
    time.sleep(1)

    speak_text("Starting the test")

    for player in selected_players:
        selected_players[player] = player_vars[player].get()
    
    root.after(0, update_table)
    
    if is_yo_yo_test:
        threading.Thread(target=start_yo_yo_test, daemon=True).start()
    else:
        threading.Thread(target=start_beep_test, daemon=True).start()

    # ✅ เริ่มจับ HR ทุก 30 วินาที
    global recording_hr, recording_start_time
    recording_hr = True
    recording_start_time = time.time()
    record_hr_every_30s()


def reset_test():
    """รีเซ็ตสถานะทั้งหมดให้พร้อมเริ่มใหม่"""
    global running, current_level, current_shuttle
    running = False
    current_level = 0
    current_shuttle = 1

    start_button["state"] = "normal"

    with lock:
        for player in selected_players:
            player_status[player] = "Waiting"
            warning_count[player] = 0  # ✅ รีเซ็ตจำนวน Warning
            passed_checkpoints[player] = {"A": False, "B": False}
            checkpoint_time[player] = {"A": None, "B": None}
            player_results_beep[player] = ""
            player_results_yoyo[player] = ""
            start_button["state"] = "disabled"

    root.after(0, update_table)
    root.after(0, timer_label.config(text="Ready to Start"))
    root.state("normal")
    set_protocol_button["state"] = "normal"
 


def update_table_header():
    """อัปเดตหัวตารางสำหรับ Beep Test และ Yo-Yo Test"""
    tree.delete(*tree.get_children())  # ลบข้อมูลเก่า

    if is_yo_yo_test:
        # ✅ หัวตารางสำหรับ Yo-Yo Test
        tree["columns"] = ("Player", "Status", "Level", "Shuttle", "HR", "Result")
        tree.heading("Player", text="Player")
        tree.heading("Status", text="Status")
        tree.heading("Level", text="Level")
        tree.heading("Shuttle", text="Shuttle")
        tree.heading("Result", text="Yo-Yo Result")
        tree.heading("HR", text="HR (bpm)")
    else:
        # ✅ หัวตารางสำหรับ Beep Test
        tree["columns"] = ("Player", "Status", "Level", "Shuttle", "HR", "Result")
        tree.heading("Player", text="Player")
        tree.heading("Status", text="Status")
        tree.heading("Level", text="Level")
        tree.heading("Shuttle", text="Shuttle")
        tree.heading("Result", text="Beep Test Result")
        tree.heading("HR", text="HR (bpm)")

    tree.pack()

def finish_test_and_save():
    global running, recording_hr
    running = False
    recording_hr = False  # ❌ หยุดการจับ HR เมื่อจบการทดสอบ

    try:
        with open("test_results.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            results = data.get("results", [])
    except:
        results = []

    # ✅ ระบุประเภทการทดสอบ
    if is_yo_yo_test:
        if yo_yo_mode == "YYIR1":
            test_type = "YYIR1 test"
        elif yo_yo_mode == "YYIR2":
            test_type = "YYIR2 test"
        else:
            test_type = "Yo-Yo Test"
    else:
        test_type = "Beep Test"

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    for player in selected_players:
        if selected_players[player] and selected_player_ids[player]:

            # ✅ คำนวณ HR ถ้ามีการจับ HR ระหว่างทดสอบ
            if hr_record[player]:
                values = hr_record[player]
                avg_hr = sum(values) / len(values)
                max_hr = max(values)
                min_hr = min(values)

                # คำนวณ Zone (HR max สมมุติ 200)
                zones = {"Zone 1": 0, "Zone 2": 0, "Zone 3": 0, "Zone 4": 0, "Zone 5": 0}
                for hr in values:
                    percent = hr / 200 * 100
                    if percent < 60:
                        zones["Zone 1"] += 1
                    elif percent < 70:
                        zones["Zone 2"] += 1
                    elif percent < 80:
                        zones["Zone 3"] += 1
                    elif percent < 90:
                        zones["Zone 4"] += 1
                    else:
                        zones["Zone 5"] += 1

                total = len(values)
                zone_percent = {z: round((zones[z] * 100) / total, 1) for z in zones}

                hr_data = {
                    "values": values,
                    "avg": round(avg_hr, 1),
                    "max": max_hr,
                    "min": min_hr,
                    "zone_percent": zone_percent
                }
            else:
                hr_data = None  # ถ้าไม่มีข้อมูล HR ไม่ต้องเก็บ

            result = {
                "athlete_id": selected_player_ids[player],
                "first_name": player_names[player].split()[0],
                "last_name": " ".join(player_names[player].split()[1:]),
                "date": now,
                "test_type": test_type,
                "result": player_results_yoyo[player] if is_yo_yo_test else player_results_beep[player],
                "hr_data": hr_data  # ✅ เพิ่มข้อมูล HR ลงผลลัพธ์
            }

            results.append(result)

    with open("test_results.json", "w", encoding="utf-8") as f:
        json.dump({"results": results}, f, indent=4)

    messagebox.showinfo("Saved", "Test results saved and test stopped.")
    finish_button["state"] = "disabled"


def select_hr_sensor(player_key):
    win = Toplevel()
    win.title(f"Select HR Sensor for {player_key}")
    win.geometry("300x150")

    tk.Label(win, text="Choose HR Sensor:", font=("Arial", 12)).pack(pady=10)

    hr_options = [f"HR{i}" for i in range(1, 11)]
    selected_hr = StringVar(value=player_hr_mapping[player_key] or hr_options[0])

    dropdown = ttk.Combobox(win, textvariable=selected_hr, values=hr_options, state="readonly", font=("Arial", 12))
    dropdown.pack(pady=10)

    def confirm():
        player_hr_mapping[player_key] = selected_hr.get()
        speak_text(f"{player_key} paired with {selected_hr.get()}")
        win.destroy()

    tk.Button(win, text="Confirm", command=confirm, font=("Arial", 11), bg="green", fg="white").pack(pady=5)

def record_hr_every_30s():
    if not recording_hr:
        return

    for player in selected_players:
        if selected_players[player] and player_hr_values[player] != "-":
            try:
                hr_value = int(player_hr_values[player])
                hr_record[player].append(hr_value)
            except ValueError:
                pass  # ข้ามถ้า HR เป็นข้อความหรือ "-"

    root.after(30000, record_hr_every_30s)  # เรียกตัวเองอีกครั้งใน 30 วินาที

def plot_hr_graph(hr_data, parent_frame, age):
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

    hr_values = hr_data["values"]
    if not hr_values:
        return

    interval_sec = 30
    timestamps = [i * interval_sec for i in range(len(hr_values))]
    max_hr = 208 - (0.7 * age)  # ✅ HRmax ตามอายุ

    fig, ax = plt.subplots(figsize=(8, 4))

    zones = [
        (0.0, 0.6, "#cce5ff", "Zone 1"),
        (0.6, 0.7, "#d4f4dd", "Zone 2"),
        (0.7, 0.8, "#fff7cc", "Zone 3"),
        (0.8, 0.9, "#ffe0b3", "Zone 4"),
        (0.9, 1.0, "#ffc2c2", "Zone 5")
    ]

    for zmin, zmax, color, label in zones:
        ax.axhspan(zmin * max_hr, zmax * max_hr, color=color, alpha=0.6)

    ax.plot(timestamps, hr_values, color="red", linewidth=2, label="Heart Rate")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Heart Rate (bpm)")
    ax.set_title(f"HR Timeline (HRmax={round(max_hr)})")
    ax.grid(True)

    zone_counts = {z[3]: 0 for z in zones}
    for hr in hr_values:
        percent = hr / max_hr
        for zmin, zmax, _, label in zones:
            if zmin <= percent < zmax:
                zone_counts[label] += 1
                break

    total = len(hr_values)
    zone_summary = "\n".join([
        f"{z}: {round((count / total) * 100, 1)}% ({count * 30 // 60}m {count * 30 % 60}s)"
        for z, count in zone_counts.items()
    ])

    canvas = FigureCanvasTkAgg(fig, master=parent_frame)
    canvas.draw()
    canvas.get_tk_widget().pack(pady=5)

    tk.Label(parent_frame, text="Zone Summary:", font=("Arial", 12, "bold")).pack()
    tk.Label(parent_frame, text=zone_summary, font=("Arial", 11), justify="left").pack()
    plt.close(fig)  # ✅ แก้ปัญหาค้างหลังปิดกราฟ


def view_result_details(result):
    win = tk.Toplevel()
    win.title("Individual Result Details")
    win.geometry("800x680")

    tk.Label(win, text=f"{result['first_name']} {result['last_name']}", font=("Arial", 16)).pack(pady=5)
    tk.Label(win, text=f"Date: {result['date']}", font=("Arial", 12)).pack()
    tk.Label(win, text=f"Test Type: {result['test_type']}", font=("Arial", 12)).pack()

    # ✅ VO2max / Shuttle / Level
    level, shuttle = extract_level_shuttle(result.get("result", ""))
    vo2max = "-"

    try:
        if "Beep Test" in result["test_type"]:
            vo2max = get_beep_vo2max(level, shuttle)
        elif "YYIR1" in result["test_type"]:
            distance = get_yoyo_ir1_distance(level, shuttle)
            vo2max = get_yoyo_ir1_vo2max(distance)
        elif "YYIR2" in result["test_type"]:
            distance = get_yoyo_ir2_distance(level, shuttle)
            vo2max = get_yoyo_ir2_vo2max(distance)
    except:
        vo2max = "-"

    info = f"Level: {level}, Shuttle: {shuttle}, VO2max: {vo2max}"
    tk.Label(win, text=info, font=("Arial", 12)).pack(pady=3)

    # ✅ ค่า HR
    if result.get("hr_data"):
        hr = result["hr_data"]
        tk.Label(win, text=f"Avg HR: {hr['avg']} | Max: {hr['max']} | Min: {hr['min']}", font=("Arial", 12)).pack(pady=5)

        # ✅ หาค่า HRmax จากอายุ (สูตร Tanaka)
        age = result.get("age", 20)  # fallback เผื่อไม่มีในไฟล์

        # ✅ วาดกราฟ HR Timeline แบบ Zone โดยใช้ HRmax จากอายุ
        plot_hr_graph(hr, win, age)

    else:
        tk.Label(win, text="No HR data available", font=("Arial", 12), fg="gray").pack(pady=10)
    

def export_pdf_beep_test(result):
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages
    from tkinter import filedialog, messagebox
    import tempfile
    import os

    name = f"{result['first_name']} {result['last_name']}"
    date = result.get("date", "")
    test_type = result.get("test_type", "-")
    level, shuttle = extract_level_shuttle(result.get("result", ""))
    result_text = result.get("result", "")
    if isinstance(result_text, dict):
        vo2max = result_text.get("vo2max", "-")
    else:
        # ดึงจาก extract + คำนวณใหม่
        level, shuttle = extract_level_shuttle(result_text)
        if "Beep Test" in result["test_type"]:
            vo2max = get_beep_vo2max(level, shuttle)
        elif "YYIR1" in result["test_type"]:
            distance = get_yoyo_ir1_distance(level, shuttle)
            vo2max = get_yoyo_ir1_vo2max(distance)
        elif "YYIR2" in result["test_type"]:
            distance = get_yoyo_ir2_distance(level, shuttle)
            vo2max = get_yoyo_ir2_vo2max(distance)
        else:
            vo2max = "-"
    hr_data = result.get("hr_data", {})

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmpfile:
        with PdfPages(tmpfile.name) as pdf:

            # ✅ หน้า 1: Cover page
            fig_cover = plt.figure(figsize=(8.3, 11.7))
            plt.axis('off')
            fig_cover.text(0.5, 0.9, "Beep Test / Yo-Yo Test Report", ha="center", fontsize=20, weight="bold")
            fig_cover.text(0.5, 0.82, f"Athlete: {name}", ha="center", fontsize=14)
            fig_cover.text(0.5, 0.78, f"Test Date: {date}", ha="center", fontsize=12)
            fig_cover.text(0.5, 0.74, f"Test Type: {test_type}", ha="center", fontsize=12)
            fig_cover.text(0.5, 0.70, f"Result: Level {level}, Shuttle {shuttle}", ha="center", fontsize=12)
            fig_cover.text(0.5, 0.66, f"VO2max (ml/kg/min): {vo2max}", ha="center", fontsize=12)
            pdf.savefig(fig_cover)
            plt.close(fig_cover)

            # ✅ หน้า 2: HR Summary Table
            fig_summary = plt.figure(figsize=(8.3, 11.7))
            ax = fig_summary.add_subplot(111)
            ax.axis('off')
            ax.set_title("SUMMARY", fontsize=14, weight="bold", loc="center")

            summary_data = [
                ["Athlete", name],
                ["Date", date],
                ["Test Type", test_type],
                ["Level / Shuttle", f"{level} / {shuttle}"],
                ["VO2max (ml/kg/min)", vo2max],
            ]

            if hr_data:
                summary_data += [
                    ["Avg HR (bpm)", hr_data.get("avg", "-")],
                    ["Max HR (bpm)", hr_data.get("max", "-")],
                    ["Min HR (bpm)", hr_data.get("min", "-")]
                ]

            ax.table(
                cellText=summary_data,
                colWidths=[0.6, 0.6],
                loc="center",
                cellLoc="left",
                bbox=[0.1, 0.45, 0.8, 0.45]
            ).scale(1.3, 1.5)

            pdf.savefig(fig_summary)
            plt.close(fig_summary)

            # ✅ หน้า 3: HR Timeline with Zone Background + Summary
            if hr_data and "values" in hr_data:
    
                hr_values = hr_data["values"]
                if not hr_values:
                    return

            # คำนวณ HRmax จากอายุ (fallback = 20)
            age = result.get("age", 20)
            max_hr = 208 - 0.7 * age

            timestamps = [i * 30 / 60 for i in range(len(hr_values))]  # หน่วยเป็นนาที
            


            fig, ax = plt.subplots(figsize=(8.3, 6))

            # สี Zone
            zones = [
                (0.0, 0.6, "#cce5ff", "Zone 1"),
                (0.6, 0.7, "#d4f4dd", "Zone 2"),
                (0.7, 0.8, "#fff7cc", "Zone 3"),
                (0.8, 0.9, "#ffe0b3", "Zone 4"),
                (0.9, 1.0, "#ffc2c2", "Zone 5")
            ]

            for zmin, zmax, color, label in zones:
                ax.axhspan(zmin * max_hr, zmax * max_hr, color=color, alpha=0.6)

            ax.plot(timestamps, hr_values, color="red", linewidth=2)
            ax.set_title(f"HR Timeline (HRmax={int(max_hr)})")
            ax.set_xlabel("Time (min)")
            ax.set_ylabel("Heart Rate (bpm)")
            ax.set_ylim(0, max(200, int(max(hr_values)) + 20))
            ax.grid(True)

            pdf.savefig(fig)
            plt.close(fig)

            # ✅ Zone Summary แยกหน้า
            zone_counts = {z[3]: 0 for z in zones}
            for hr in hr_values:
                percent = hr / max_hr
                for zmin, zmax, _, label in zones:
                    if zmin <= percent < zmax:
                        zone_counts[label] += 1
                        break

            total = len(hr_values)
            summary_lines = ["Zone Summary:"]
            for z in zone_counts:
                pct = (zone_counts[z] / total) * 100
                sec = zone_counts[z] * 30
                summary_lines.append(f"{z}: {pct:.1f}% ({sec // 60}m {sec % 60}s)")

            # สร้างหน้าใหม่ไว้แสดง summary
            fig_sum = plt.figure(figsize=(8.3, 3))
            plt.axis("off")
            fig_sum.text(0.5, 0.9, "Zone Summary:", fontsize=14, weight="bold", ha="center")
            for i, line in enumerate(summary_lines[1:]):
                fig_sum.text(0.5, 0.8 - i * 0.1, line, fontsize=12, ha="center")
            pdf.savefig(fig_sum)
            plt.close(fig_sum)

    path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")])
    if path:
        os.replace(tmpfile.name, path)
        messagebox.showinfo("Exported", f"PDF saved to:\n{path}")

# ✅ สร้างหน้าต่างหลัก
root = tk.Tk()
root.title("Multi-Stage Fitness Test")
root.geometry("1000x550")  # ✅ กำหนดขนาดหน้าต่าง

# ✅ ตั้งค่าฟอนต์หลัก
FONT_LARGE = ("Arial", 14, "bold")
FONT_MEDIUM = ("Arial", 12)
FONT_SMALL = ("Arial", 10)

# ✅ ส่วนแสดงเวลา
timer_frame = tk.Frame(root, pady=10)
timer_frame.pack(fill="x")

timer_label = tk.Label(timer_frame, text="Waiting to start...", font=FONT_LARGE, fg="blue")
timer_label.pack()

# ✅ สร้าง Treeview สำหรับแสดงผลลัพธ์
tree_frame = tk.Frame(root, padx=10, pady=10)
tree_frame.pack(fill="both", expand=True)

tree = ttk.Treeview(tree_frame, columns=("Player", "Status", "Result"), show="headings", height=10)
tree.heading("Player", text="Player")
tree.heading("Status", text="Status")
tree.heading("Result", text="Result")
tree.column("Player", width=150)
tree.column("Status", width=100)
tree.column("Result", width=200)

# ✅ แถบเลื่อนแนวตั้ง
tree_scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
tree.configure(yscrollcommand=tree_scroll.set)
tree_scroll.pack(side="right", fill="y")

tree.pack(fill="both", expand=True)

# ✅ ส่วนเลือก Player
player_frame = tk.LabelFrame(root, text="Select Players", padx=10, pady=10)
player_frame.pack(fill="x", padx=10, pady=5)

player_vars = {f'Player {i}': tk.BooleanVar() for i in range(1, 11)}

for i, (player, var) in enumerate(player_vars.items()):
    frame = tk.Frame(player_frame)
    frame.grid(row=i//5, column=i%5, padx=5, pady=5)

    # ✅ Checkbox สำหรับเลือก Player
    chk = tk.Checkbutton(frame, text=player, variable=var, font=FONT_SMALL)
    chk.pack(side="left")

    # ✅ ปุ่ม Rename Player อยู่ข้าง Checkbox
    select_btn = tk.Button(frame, text="Select Player", font=FONT_SMALL, command=lambda p=player, c=chk: select_player_from_database(p, c))
    select_btn.pack(side="left", padx=5)
    # ✅ ใน loop สร้าง checkbox Player (เพิ่มเข้าไปหลัง select_btn)
    hr_btn = tk.Button(frame, text="HR", font=FONT_SMALL, command=lambda p=player: select_hr_sensor(p))
    hr_btn.pack(side="left", padx=2)


# ✅ ส่วนเลือกโปรโตคอล
protocol_frame = tk.LabelFrame(root, text="Test Protocol", padx=10, pady=10)
protocol_frame.pack(fill="x", padx=10, pady=5)

selected_protocol = tk.StringVar()
selected_protocol.set("Standard Beep Test")  # ค่าเริ่มต้น

all_protocols = {**protocols_beep, **protocols_yoyo, **protocols_yoyo2}  # รวมทั้ง Beep และ Yo-Yo Test
protocol_menu = ttk.Combobox(protocol_frame, textvariable=selected_protocol, values=list(all_protocols.keys()), state="readonly", font=FONT_MEDIUM)
protocol_menu.pack(side="left", padx=5)

set_protocol_button = tk.Button(protocol_frame, text="Set Protocol", font=FONT_MEDIUM, command=set_protocol)
set_protocol_button.pack(side="left", padx=10)

# ✅ ส่วนควบคุมการทดสอบ
control_frame = tk.Frame(root, pady=10)
control_frame.pack(fill="x")

start_button = tk.Button(control_frame, text="Start Test", font=FONT_MEDIUM, command=start_test, state="disabled", width=12, bg="green", fg="white")
start_button.pack(side="left", padx=10)

reset_button = tk.Button(control_frame, text="Reset Test", font=FONT_MEDIUM, command=reset_test, width=12, bg="red", fg="white")
reset_button.pack(side="left", padx=10)

finish_button = tk.Button(control_frame, text="Finished", font=FONT_MEDIUM, command=finish_test_and_save, width=12, bg="blue", fg="white",state="disabled" )
finish_button.pack(side="left", padx=10)

# ✅ ส่วนตั้งค่า Warning
warning_frame = tk.LabelFrame(root, text="Settings", padx=10, pady=10)
warning_frame.pack(fill="x", padx=10, pady=5)

warning_label = tk.Label(warning_frame, text="Max Warnings (0 = Instant Disqualify):", font=FONT_MEDIUM)
warning_label.pack(side="left")

warning_var = tk.IntVar(value=max_warnings)
warning_entry = tk.Entry(warning_frame, textvariable=warning_var, width=5, font=FONT_MEDIUM)
warning_entry.pack(side="left", padx=5)

set_warning_button = tk.Button(warning_frame, text="Set Warnings", font=FONT_MEDIUM, command=set_max_warnings)
set_warning_button.pack(side="left", padx=5)

# ✅ สร้าง Frame สำหรับตั้งค่า MQTT
mqtt_frame = tk.LabelFrame(root, text="MQTT Settings", padx=10, pady=10)
mqtt_frame.pack(fill="x", padx=10, pady=5)

# ✅ ตัวแปรเก็บค่า MQTT Broker IP
mqtt_broker_ip = tk.StringVar(value="192.168.100.189")  # ค่าเริ่มต้นเป็น IP ปัจจุบัน

tk.Label(mqtt_frame, text="MQTT Broker IP:", font=FONT_MEDIUM).pack(side="left", padx=5)

# ✅ ช่องให้ผู้ใช้พิมพ์ค่า IP ของ MQTT Broker
mqtt_entry = tk.Entry(mqtt_frame, textvariable=mqtt_broker_ip, width=20, font=FONT_MEDIUM)
mqtt_entry.pack(side="left", padx=5)

# ✅ ปุ่ม Connect MQTT
connect_button = tk.Button(mqtt_frame, text="Connect", font=FONT_MEDIUM, command=lambda: connect_mqtt(mqtt_broker_ip.get()))
connect_button.pack(side="left", padx=5)

# ✅ สร้าง Menu Bar
menu_bar = tk.Menu(root)
root.config(menu=menu_bar)

# ✅ เมนู "นักกีฬา"
athlete_menu = tk.Menu(menu_bar, tearoff=0)
menu_bar.add_cascade(label="Setting", menu=athlete_menu)
athlete_menu.add_command(label="Athletes", command=manage_athletes_window)

history_menu = tk.Menu(menu_bar, tearoff=0)
menu_bar.add_cascade(label="Result", menu=history_menu)
history_menu.add_command(label="History", command=view_test_history)

# ✅ เริ่ม GUI
root.mainloop()