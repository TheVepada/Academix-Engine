# ui.py
import calendar
from datetime import datetime, timedelta
import customtkinter as ctk

try:
    import database  # Member 1's file (optional while developing)
except ImportError:
    database = None

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

RED, YEL, GRN = "#D32F2F", "#F57C00", "#388E3C"
MONTHS = list(calendar.month_abbr)[1:]


# ------------------------------------------------------------------
# Urgency helpers (placeholder: swap with Member 2's urgency_engine)
# ------------------------------------------------------------------
def compute_urgency(weight, deadline):
    hours = (deadline - datetime.now()).total_seconds() / 3600
    if hours <= 0:
        return hours, 100.0
    return hours, min(100.0, round(weight / (hours + 1) * 50, 1))


def color_for(hours):
    return RED if hours < 24 else YEL if hours < 72 else GRN


def fmt_left(hours):
    if hours <= 0:
        return "Overdue"
    if hours < 1:
        return "Due in under 1 hour"
    if hours < 48:
        return f"Due in {int(hours)} hours"
    return f"Due in {int(hours // 24)} days"


class AcademixApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Academix Engine")
        self.geometry("1100x680")
        self.minsize(950, 600)
        self.tasks = []  # {"title", "deadline", "weight"}
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.build_sidebar()
        self.pages = {
            "Home": self.build_home(),
            "Tasks": self.build_tasks(),
            "Telemetry": self.build_telemetry(),
            "Analytics": self.build_analytics(),
        }
        self.seed_tasks()
        self.show_page("Home")
        self.tick()

    # ---------------- Sidebar ----------------
    def build_sidebar(self):
        sb = ctk.CTkFrame(self, width=210, corner_radius=0)
        sb.grid(row=0, column=0, sticky="nsew")
        sb.grid_rowconfigure(5, weight=1)
        ctk.CTkLabel(sb, text="🎓 Academix", font=ctk.CTkFont(size=20, weight="bold")).grid(
            row=0, column=0, padx=20, pady=(30, 25))
        self.nav = {}
        for i, (name, icon) in enumerate([("Home", "🏠"), ("Tasks", "📝"),
                                         ("Telemetry", "🛡️"), ("Analytics", "📈")], start=1):
            b = ctk.CTkButton(sb, text=f"{icon}  {name}", anchor="w", height=38,
                              fg_color="transparent", text_color=("gray10", "gray90"),
                              hover_color=("gray70", "gray30"),
                              command=lambda n=name: self.show_page(n))
            b.grid(row=i, column=0, padx=15, pady=4, sticky="ew")
            self.nav[name] = b
        ctk.CTkLabel(sb, text="🟢 Telemetry Active\nDB Connected (WAL)", font=ctk.CTkFont(size=11),
                     text_color="green").grid(row=6, column=0, pady=20, sticky="s")
        ctk.CTkOptionMenu(sb, values=["System", "Dark", "Light"], width=120,
                          command=ctk.set_appearance_mode).grid(row=7, column=0, pady=(0, 20))

    def show_page(self, name):
        for p in self.pages.values():
            p.grid_forget()
        self.pages[name].grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        for n, b in self.nav.items():
            b.configure(fg_color=("gray75", "gray28") if n == name else "transparent")
        self.refresh()

    def new_page(self):
        f = ctk.CTkFrame(self, fg_color="transparent")
        f.grid_columnconfigure(0, weight=1)
        return f

    # ---------------- Home ----------------
    def build_home(self):
        p = self.new_page()
        self.greet = ctk.CTkLabel(p, text="", font=ctk.CTkFont(size=28, weight="bold"))
        self.greet.grid(row=0, column=0, sticky="w")
        self.clock = ctk.CTkLabel(p, text="", font=ctk.CTkFont(size=13), text_color="gray")
        self.clock.grid(row=1, column=0, sticky="w", pady=(2, 20))

        row = ctk.CTkFrame(p, fg_color="transparent")
        row.grid(row=2, column=0, sticky="ew")
        self.stats = {}
        for i, (key, label) in enumerate([("active", "Active Tasks"), ("urgent", "Urgent (<24h)"),
                                         ("focus", "Focus Score")]):
            row.grid_columnconfigure(i, weight=1)
            card = ctk.CTkFrame(row, corner_radius=12, height=100)
            card.grid(row=0, column=i, sticky="ew", padx=6)
            v = ctk.CTkLabel(card, text="0", font=ctk.CTkFont(size=30, weight="bold"))
            v.pack(pady=(15, 0))
            ctk.CTkLabel(card, text=label, text_color="gray").pack(pady=(0, 15))
            self.stats[key] = v

        self.next_card = ctk.CTkFrame(p, corner_radius=12)
        self.next_card.grid(row=3, column=0, sticky="ew", padx=6, pady=20)
        ctk.CTkLabel(self.next_card, text="⚡ Next Up", font=ctk.CTkFont(size=14, weight="bold")).pack(
            anchor="w", padx=20, pady=(15, 0))
        self.next_lbl = ctk.CTkLabel(self.next_card, text="", font=ctk.CTkFont(size=18), anchor="w")
        self.next_lbl.pack(anchor="w", padx=20, pady=(5, 0))
        self.next_sub = ctk.CTkLabel(self.next_card, text="", text_color="gray", anchor="w")
        self.next_sub.pack(anchor="w", padx=20, pady=(0, 15))

        ctk.CTkButton(p, text="➕ Add New Assignment", height=42, width=220,
                      command=lambda: self.show_page("Tasks")).grid(row=4, column=0, sticky="w", padx=6)
        return p

    # ---------------- Tasks ----------------
    def build_tasks(self):
        p = self.new_page()
        p.grid_columnconfigure(0, weight=1)
        p.grid_columnconfigure(1, weight=2)
        p.grid_rowconfigure(0, weight=1)

        form = ctk.CTkFrame(p, corner_radius=12)
        form.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        ctk.CTkLabel(form, text="Add New Assignment", font=ctk.CTkFont(size=16, weight="bold")).pack(
            padx=20, pady=(22, 12), anchor="w")

        ctk.CTkLabel(form, text="Task Title").pack(padx=20, anchor="w")
        self.entry_title = ctk.CTkEntry(form, placeholder_text="e.g., Data Structures Lab Report", height=36)
        self.entry_title.pack(padx=20, pady=(4, 12), fill="x")

        ctk.CTkLabel(form, text="Deadline").pack(padx=20, anchor="w")
        d = ctk.CTkFrame(form, fg_color="transparent")
        d.pack(padx=20, pady=(4, 4), fill="x")
        tmr = datetime.now() + timedelta(days=1)
        self.day = ctk.CTkOptionMenu(d, values=[f"{i:02d}" for i in range(1, 32)], width=62)
        self.month = ctk.CTkOptionMenu(d, values=MONTHS, width=72)
        self.year = ctk.CTkOptionMenu(d, values=[str(tmr.year + i) for i in range(3)], width=80)
        self.day.set(f"{tmr.day:02d}")
        self.month.set(MONTHS[tmr.month - 1])
        self.year.set(str(tmr.year))
        for w in (self.day, self.month, self.year):
            w.pack(side="left", padx=(0, 5))
        t = ctk.CTkFrame(form, fg_color="transparent")
        t.pack(padx=20, pady=(0, 12), fill="x")
        ctk.CTkLabel(t, text="🕒 Time").pack(side="left", padx=(0, 8))
        self.hour = ctk.CTkOptionMenu(t, values=[f"{i:02d}" for i in range(24)], width=62)
        self.minute = ctk.CTkOptionMenu(t, values=["00", "15", "30", "45", "59"], width=62)
        self.hour.set("23")
        self.minute.set("59")
        self.hour.pack(side="left")
        ctk.CTkLabel(t, text=":").pack(side="left", padx=3)
        self.minute.pack(side="left")

        ctk.CTkLabel(form, text="Importance (1 - 10)").pack(padx=20, anchor="w")
        self.slider = ctk.CTkSlider(form, from_=1, to=10, number_of_steps=9, command=self.on_slide)
        self.slider.set(5)
        self.slider.pack(padx=20, pady=(4, 2), fill="x")
        self.w_lbl = ctk.CTkLabel(form, text="Selected: 5", text_color="gray", font=ctk.CTkFont(size=11))
        self.w_lbl.pack(padx=20, anchor="w")

        self.msg = ctk.CTkLabel(form, text="", text_color=RED, font=ctk.CTkFont(size=11))
        self.msg.pack(padx=20, pady=(8, 0), anchor="w")
        ctk.CTkButton(form, text="Save & Compute Urgency", height=40,
                      font=ctk.CTkFont(size=13, weight="bold"), command=self.add_task).pack(
            padx=20, pady=8, fill="x")

        feed = ctk.CTkFrame(p, corner_radius=12, fg_color=("gray92", "gray17"))
        feed.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        feed.grid_rowconfigure(1, weight=1)
        feed.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(feed, text="🔥 Smart Urgency Feed", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, padx=20, pady=(22, 8), sticky="w")
        self.feed = ctk.CTkScrollableFrame(feed, fg_color="transparent")
        self.feed.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 12))
        return p

    def on_slide(self, v):
        self.w_lbl.configure(text=f"Selected: {int(v)}")

    def add_task(self):
        title = self.entry_title.get().strip()
        if not title:
            self.msg.configure(text="⚠ Please enter a task title.")
            return
        try:
            dl = datetime(int(self.year.get()), MONTHS.index(self.month.get()) + 1,
                          int(self.day.get()), int(self.hour.get()), int(self.minute.get()))
        except ValueError:
            self.msg.configure(text="⚠ That date doesn't exist.")
            return
        if dl <= datetime.now():
            self.msg.configure(text="⚠ Deadline must be in the future.")
            return
        task = {"title": title, "deadline": dl, "weight": int(self.slider.get())}
        self.tasks.append(task)
        self.save_to_db(task)
        self.entry_title.delete(0, "end")
        self.msg.configure(text="")
        self.refresh()

    def save_to_db(self, task):
        fn = getattr(database, "save_task", None) or getattr(database, "add_task", None)
        if fn:
            try:
                fn(task["title"], task["deadline"].strftime("%Y-%m-%d %H:%M"), task["weight"])
            except Exception as e:
                print("DB save failed (check signature):", e)

    def seed_tasks(self):
        now = datetime.now()
        for title, hrs, w in [("Algorithms Assignment 3", 6, 9), ("SRS Report Draft", 18, 8),
                            ("Database Normalization Lab", 72, 6), ("Web Engineering Project Setup", 168, 4)]:
            self.tasks.append({"title": title, "deadline": now + timedelta(hours=hrs), "weight": w})

    def card(self, t):
        hours, score = t["hours"], t["score"]
        c = ctk.CTkFrame(self.feed, corner_radius=8, fg_color=("white", "gray25"))
        c.pack(fill="x", pady=5, padx=4)
        ctk.CTkFrame(c, width=6, fg_color=color_for(hours), corner_radius=0).pack(side="left", fill="y")
        box = ctk.CTkFrame(c, fg_color="transparent")
        box.pack(side="left", fill="both", expand=True, padx=12, pady=10)
        ctk.CTkLabel(box, text=t["title"], font=ctk.CTkFont(size=13, weight="bold"), anchor="w").pack(fill="x")
        ctk.CTkLabel(box, text=f"⏳ {fmt_left(hours)}  |  Score {score}  |  Weight {t['weight']}",
                     font=ctk.CTkFont(size=11), text_color="gray", anchor="w").pack(fill="x")
        bar = ctk.CTkProgressBar(box, height=5, progress_color=color_for(hours))
        bar.set(score / 100)
        bar.pack(fill="x", pady=(6, 0))
        ctk.CTkButton(c, text="✓ Done", width=64, fg_color="transparent", border_width=1,
                      text_color=("gray10", "gray90"),
                      command=lambda x=t: self.complete(x)).pack(side="right", padx=10)

    def complete(self, t):
        self.tasks.remove(t["ref"])
        self.refresh()

    # ---------------- Telemetry ----------------
    def build_telemetry(self):
        p = self.new_page()
        p.grid_rowconfigure(3, weight=1)
        ctk.CTkLabel(p, text="🛡️ Telemetry & Alerts", font=ctk.CTkFont(size=22, weight="bold")).grid(
            row=0, column=0, sticky="w", pady=(0, 15))
        box = ctk.CTkFrame(p, corner_radius=12)
        box.grid(row=1, column=0, sticky="ew")
        self.track = ctk.CTkSwitch(box, text="Track active window every 3s")
        self.track.select()
        self.track.pack(anchor="w", padx=20, pady=(18, 10))
        self.lim_lbl = ctk.CTkLabel(box, text="Alert after 20 min of distraction")
        self.lim_lbl.pack(anchor="w", padx=20)
        s = ctk.CTkSlider(box, from_=5, to=60, number_of_steps=11,
                        command=lambda v: self.lim_lbl.configure(
                            text=f"Alert after {int(v)} min of distraction"))
        s.set(20)
        s.pack(fill="x", padx=20, pady=(4, 18))
        ctk.CTkLabel(p, text="Recent Activity (sample data; Member 3 feeds real logs)",
                     text_color="gray").grid(row=2, column=0, sticky="w", pady=(18, 4))
        log = ctk.CTkTextbox(p, corner_radius=12)
        log.grid(row=3, column=0, sticky="nsew")
        log.insert("end", "10:02  Code.exe      - VS Code         ✅ Productive\n"
                          "10:05  chrome.exe    - YouTube          ❌ Distracting\n"
                          "10:09  WINWORD.EXE   - SRS Report       ✅ Productive\n"
                          "10:14  Discord.exe   - #general         ❌ Distracting\n")
        log.configure(state="disabled")
        return p

    # ---------------- Analytics ----------------
    def build_analytics(self):
        p = self.new_page()
        ctk.CTkLabel(p, text="📈 Focus Analytics", font=ctk.CTkFont(size=22, weight="bold")).grid(
            row=0, column=0, sticky="w", pady=(0, 15))
        box = ctk.CTkFrame(p, corner_radius=12)
        box.grid(row=1, column=0, sticky="ew")
        box.grid_columnconfigure(1, weight=1)
        data = [("Mon", .72), ("Tue", .55), ("Wed", .80), ("Thu", .40), ("Fri", .65), ("Sat", .30), ("Sun", .50)]
        for i, (d, v) in enumerate(data):
            ctk.CTkLabel(box, text=d, width=50).grid(row=i, column=0, padx=(20, 10), pady=8)
            bar = ctk.CTkProgressBar(box, height=14, progress_color=GRN if v > .6 else YEL if v > .45 else RED)
            bar.set(v)
            bar.grid(row=i, column=1, sticky="ew", pady=8)
            ctk.CTkLabel(box, text=f"{int(v * 100)}%", width=50).grid(row=i, column=2, padx=(10, 20))
        ctk.CTkLabel(p, text="Sample data; replace with focus logs from the database.",
                     text_color="gray").grid(row=2, column=0, sticky="w", pady=10)
        return p

    # ---------------- Refresh / loop ----------------
    def refresh(self):
        rows = []
        for t in self.tasks:
            h, s = compute_urgency(t["weight"], t["deadline"])
            rows.append({**t, "hours": h, "score": s, "ref": t})
        rows.sort(key=lambda r: r["score"], reverse=True)

        for w in self.feed.winfo_children():
            w.destroy()
        for r in rows:
            self.card(r)

        self.stats["active"].configure(text=str(len(rows)))
        self.stats["urgent"].configure(text=str(sum(1 for r in rows if r["hours"] < 24)))
        self.stats["focus"].configure(text="75%")
        if rows:
            self.next_lbl.configure(text=rows[0]["title"])
            self.next_sub.configure(text=f"{fmt_left(rows[0]['hours'])}  |  Score {rows[0]['score']}")
        else:
            self.next_lbl.configure(text="All clear 🎉")
            self.next_sub.configure(text="No pending tasks.")

    def tick(self):
        now = datetime.now()
        part = "morning" if now.hour < 12 else "afternoon" if now.hour < 18 else "evening"
        self.greet.configure(text=f"Good {part}, student 👋")
        self.clock.configure(text=now.strftime("%A, %d %B %Y  •  %H:%M:%S"))
        if now.second == 0:  # recalculate scores every 60s
            self.refresh()
        self.after(1000, self.tick)