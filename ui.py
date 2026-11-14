import calendar
import csv
import os
import sys
from datetime import datetime, timedelta
import customtkinter as ctk

import database
import telemetry
from urgency_engine import sort_tasks_by_urgency

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

RED, YEL, GRN = "#D32F2F", "#F57C00", "#388E3C"
MONTHS = list(calendar.month_abbr)[1:]


def resource_path(relative_path: str) -> str:
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


def color_for_tier(tier: str):
    if "CRITICAL" in tier:
        return RED
    elif "MEDIUM" in tier:
        return YEL
    return GRN


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
        self._apply_window_icon()
        self.after(250, self._apply_window_icon)

        self.geometry("1150x720")
        self.minsize(980, 640)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)

        self.current_user = None
        self.sidebar_frame = None
        self.footer_bar = None
        self.pages = {}

        self.show_login_screen()
        self.tick()

    def _apply_window_icon(self):
        try:
            ico = resource_path("academix.ico")
            if os.path.exists(ico):
                self.iconbitmap(ico)
                self.wm_iconbitmap(ico)
        except Exception:
            pass

    def tick(self):
        now = datetime.now()
        if self.current_user:
            part = "morning" if now.hour < 12 else "afternoon" if now.hour < 18 else "evening"
            if hasattr(self, "greet") and self.greet.winfo_exists():
                self.greet.configure(text=f"Good {part}, {self.current_user['username']} 👋")
            if hasattr(self, "clock") and self.clock.winfo_exists():
                self.clock.configure(text=now.strftime("%A, %d %B %Y  •  %H:%M:%S"))

            self.update_timer_dock_ui()

            if now.second % 5 == 0:
                self.refresh()

        self.after(1000, self.tick)

    # ---------------- Login / Multi-User Auth Screen ----------------
    def show_login_screen(self):
        telemetry.set_active_user(None)
        for child in self.winfo_children():
            child.destroy()

        self.login_container = ctk.CTkFrame(self, fg_color="transparent")
        self.login_container.grid(row=0, column=0, rowspan=2, columnspan=2, sticky="nsew")
        self.login_container.grid_columnconfigure(0, weight=1)
        self.login_container.grid_rowconfigure(0, weight=1)

        card = ctk.CTkFrame(self.login_container, width=380, corner_radius=16)
        card.grid(row=0, column=0, padx=20, pady=20)

        ctk.CTkLabel(card, text="🎓 Academix Engine", font=ctk.CTkFont(size=24, weight="bold")).pack(
            padx=35, pady=(30, 5)
        )
        ctk.CTkLabel(card, text="Multi-User Task & Telemetry Portal", text_color="gray",
                     font=ctk.CTkFont(size=12)).pack(padx=35, pady=(0, 20))

        ctk.CTkLabel(card, text="Username").pack(padx=35, anchor="w")
        self.auth_user = ctk.CTkEntry(card, placeholder_text="Enter username", width=280, height=36)
        self.auth_user.pack(padx=35, pady=(4, 12))

        ctk.CTkLabel(card, text="Password").pack(padx=35, anchor="w")
        self.auth_pass = ctk.CTkEntry(card, placeholder_text="Enter password", show="*", width=280, height=36)
        self.auth_pass.pack(padx=35, pady=(4, 10))

        self.auth_msg = ctk.CTkLabel(card, text="", text_color=RED, font=ctk.CTkFont(size=12))
        self.auth_msg.pack(padx=35, pady=(2, 8))

        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.pack(padx=35, pady=(5, 30), fill="x")
        ctk.CTkButton(btn_row, text="Login", width=135, height=38,
                      font=ctk.CTkFont(weight="bold"), command=self.handle_login).pack(side="left", padx=(0, 10))
        ctk.CTkButton(btn_row, text="Register", width=135, height=38, fg_color="transparent",
                      border_width=1, text_color=("gray10", "gray90"),
                      command=self.handle_register).pack(side="left")

    def handle_login(self):
        u = self.auth_user.get().strip()
        p = self.auth_pass.get().strip()
        if not u or not p:
            self.auth_msg.configure(text="⚠ Enter both username and password.", text_color=RED)
            return
        user = database.authenticate_user(u, p)
        if not user:
            self.auth_msg.configure(text="⚠ Invalid username or password.", text_color=RED)
            return
        self.start_user_session(user)

    def handle_register(self):
        u = self.auth_user.get().strip()
        p = self.auth_pass.get().strip()
        if not u or not p:
            self.auth_msg.configure(text="⚠ Enter a username and password to register.", text_color=RED)
            return
        user = database.register_user(u, p)
        if not user:
            self.auth_msg.configure(text="⚠ Username already exists. Try logging in.", text_color=RED)
            return
        self.start_user_session(user)

    def start_user_session(self, user):
        self.current_user = user
        telemetry.set_active_user(user["id"])
        self.login_container.destroy()

        self.build_sidebar()
        self.pages = {
            "Home": self.build_home(),
            "Tasks": self.build_tasks(),
            "Telemetry": self.build_telemetry(),
            "Analytics": self.build_analytics(),
        }
        self.build_pinned_footer()
        self.show_page("Home")

    # ---------------- Sidebar ----------------
    def build_sidebar(self):
        sb = ctk.CTkFrame(self, width=210, corner_radius=0)
        sb.grid(row=0, column=0, rowspan=2, sticky="nsew")
        sb.grid_columnconfigure(0, weight=1)
        sb.grid_rowconfigure(6, weight=1)
        self.sidebar_frame = sb

        ctk.CTkLabel(sb, text="🎓 Academix", font=ctk.CTkFont(size=20, weight="bold")).grid(
            row=0, column=0, padx=20, pady=(28, 2), sticky="w"
        )
        ctk.CTkLabel(sb, text=f"👤 {self.current_user['username']}", font=ctk.CTkFont(size=12),
                     text_color="gray").grid(row=1, column=0, padx=24, pady=(0, 20), sticky="w")

        self.nav = {}
        nav_items = [
            ("Home", "🏠  Home"),
            ("Tasks", "📝  Tasks"),
            ("Telemetry", "🛡️  Telemetry"),
            ("Analytics", "📈  Analytics"),
        ]
        for i, (name, label) in enumerate(nav_items, start=2):
            b = ctk.CTkButton(sb, text=label, anchor="w", height=38,
                              fg_color="transparent", text_color=("gray10", "gray90"),
                              hover_color=("gray70", "gray30"),
                              command=lambda n=name: self.show_page(n))
            b.grid(row=i, column=0, padx=15, pady=4, sticky="ew")
            self.nav[name] = b

        ctk.CTkLabel(sb, text="🟢 Telemetry Active\nDB Connected (WAL)", font=ctk.CTkFont(size=11),
                     text_color="green").grid(row=7, column=0, pady=(10, 10), sticky="s")
        ctk.CTkOptionMenu(sb, values=["System", "Dark", "Light"], width=150,
                          command=ctk.set_appearance_mode).grid(row=8, column=0, pady=(0, 10))
        ctk.CTkButton(sb, text="🚪 Logout / Switch", width=150, height=34, fg_color=RED,
                      hover_color="#B71C1C", command=self.show_login_screen).grid(row=9, column=0, pady=(0, 22))

    # ---------------- Fixed Bottom Footer Bar ----------------
    def build_pinned_footer(self):
        footer = ctk.CTkFrame(self, height=58, corner_radius=0, fg_color=("gray88", "gray14"))
        footer.grid(row=1, column=1, sticky="ew")
        self.footer_bar = footer

        right_controls = ctk.CTkFrame(footer, fg_color="transparent")
        right_controls.pack(side="right", padx=20, pady=10)

        ctk.CTkLabel(right_controls, text="⏱️  DND Time (Max 1h):",
                     font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(0, 8))

        self.timer_min_menu = ctk.CTkOptionMenu(
            right_controls, values=[f"{m:02d}:00" for m in [0, 5, 10, 15, 20, 30, 45, 60]], width=85, height=30
        )
        self.timer_min_menu.set("05:00")
        self.timer_min_menu.pack(side="left", padx=4)

        self.btn_set_timer = ctk.CTkButton(
            right_controls, text="Set Timer", width=85, height=30, command=self.apply_personal_timer
        )
        self.btn_set_timer.pack(side="left", padx=4)

        self.lbl_timer_countdown = ctk.CTkLabel(
            right_controls, text="00:00", font=ctk.CTkFont(family="Consolas", size=16, weight="bold"), text_color=GRN
        )
        self.lbl_timer_countdown.pack(side="left", padx=12)

        self.btn_pause_timer = ctk.CTkButton(
            right_controls, text="⏸ Pause", width=85, height=30, fg_color=YEL, hover_color="#E65100",
            state="disabled", command=self.handle_pause_timer
        )
        self.btn_pause_timer.pack(side="left", padx=4)

        self.btn_reset_timer = ctk.CTkButton(
            right_controls, text="🔒 Reset", width=110, height=30, state="disabled",
            command=self.handle_reset_timer
        )
        self.btn_reset_timer.pack(side="left", padx=(4, 0))

    def apply_personal_timer(self):
        selected = self.timer_min_menu.get()
        mins = int(selected.split(":")[0])
        if telemetry.configure_personal_timer(minutes=mins, seconds=0):
            self.btn_pause_timer.configure(text="⏸ Pause")
            self.update_timer_dock_ui()

    def handle_pause_timer(self):
        paused = telemetry.toggle_pause_timer()
        self.btn_pause_timer.configure(text="▶ Resume" if paused else "⏸ Pause")
        self.update_timer_dock_ui()

    def handle_reset_timer(self):
        if telemetry.reset_personal_timer():
            self.btn_pause_timer.configure(text="⏸ Pause")
            self.update_timer_dock_ui()

    def update_timer_dock_ui(self):
        if not self.footer_bar or not self.footer_bar.winfo_exists():
            return
        rem = telemetry.TELEMETRY_STATE["remaining_sec"]
        configured = telemetry.TELEMETRY_STATE["timer_configured"]
        paused = telemetry.TELEMETRY_STATE["paused"]

        mins, secs = divmod(rem, 60)
        status_tag = " (PAUSED)" if paused else ""
        self.lbl_timer_countdown.configure(
            text=f"{mins:02d}:{secs:02d}{status_tag}",
            text_color=YEL if paused else (GRN if rem > 0 else RED)
        )

        if rem > 0:
            self.btn_pause_timer.configure(state="normal")
            self.btn_set_timer.configure(state="disabled")
            self.timer_min_menu.configure(state="disabled")
            self.btn_reset_timer.configure(state="disabled", text="🔒 Running...")
        else:
            self.btn_pause_timer.configure(state="disabled", text="⏸ Pause")
            self.btn_set_timer.configure(state="normal")
            self.timer_min_menu.configure(state="normal")
            if configured:
                self.btn_reset_timer.configure(state="normal", text="↺ Reset Timer")
            else:
                self.btn_reset_timer.configure(state="disabled", text="🔒 Reset")

    def show_page(self, name):
        for p in self.pages.values():
            p.grid_forget()
        self.pages[name].grid(row=0, column=1, sticky="nsew", padx=20, pady=(20, 10))
        for n, b in self.nav.items():
            b.configure(fg_color=("gray75", "gray28") if n == name else "transparent")
        self.refresh()

    def new_page(self):
        f = ctk.CTkScrollableFrame(self, fg_color="transparent")
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
        for i, (key, label) in enumerate([("active", "Active Tasks"), ("urgent", "Critical Tasks"),
                                         ("focus", "Distraction (1h)")]):
            row.grid_columnconfigure(i, weight=1)
            card = ctk.CTkFrame(row, corner_radius=12, height=100)
            card.grid(row=0, column=i, sticky="ew", padx=6)
            v = ctk.CTkLabel(card, text="0", font=ctk.CTkFont(size=30, weight="bold"))
            v.pack(pady=(15, 0))
            ctk.CTkLabel(card, text=label, text_color="gray").pack(pady=(0, 15))
            self.stats[key] = v

        self.next_card = ctk.CTkFrame(p, corner_radius=12)
        self.next_card.grid(row=3, column=0, sticky="ew", padx=6, pady=20)
        ctk.CTkLabel(self.next_card, text="⚡ Next Priority Task", font=ctk.CTkFont(size=14, weight="bold")).pack(
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

        form = ctk.CTkFrame(p, corner_radius=12)
        form.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        ctk.CTkLabel(form, text="Add New Assignment", font=ctk.CTkFont(size=16, weight="bold")).pack(
            padx=20, pady=(15, 10), anchor="w")

        ctk.CTkLabel(form, text="Task Title").pack(padx=20, anchor="w")
        self.entry_title = ctk.CTkEntry(form, placeholder_text="e.g., Algorithms Final Submission", height=34)
        self.entry_title.pack(padx=20, pady=(4, 10), fill="x")

        ctk.CTkLabel(form, text="Estimated Effort (Hours)").pack(padx=20, anchor="w")
        self.entry_effort = ctk.CTkEntry(form, placeholder_text="e.g., 2.0", height=34)
        self.entry_effort.pack(padx=20, pady=(4, 10), fill="x")
        self.entry_effort.insert(0, "2.0")

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
        t.pack(padx=20, pady=(0, 10), fill="x")
        ctk.CTkLabel(t, text="🕒 Time").pack(side="left", padx=(0, 8))
        self.hour = ctk.CTkOptionMenu(t, values=[f"{i:02d}" for i in range(24)], width=62)
        self.minute = ctk.CTkOptionMenu(t, values=["00", "15", "30", "45", "59"], width=62)
        self.hour.set("23")
        self.minute.set("59")
        self.hour.pack(side="left")
        ctk.CTkLabel(t, text=":").pack(side="left", padx=3)
        self.minute.pack(side="left")

        ctk.CTkLabel(form, text="Priority Weight (1 - 10)").pack(padx=20, anchor="w")
        self.slider = ctk.CTkSlider(form, from_=1, to=10, number_of_steps=9, command=self.on_slide)
        self.slider.set(5)
        self.slider.pack(padx=20, pady=(4, 2), fill="x")
        self.w_lbl = ctk.CTkLabel(form, text="Selected: 5", text_color="gray", font=ctk.CTkFont(size=11))
        self.w_lbl.pack(padx=20, anchor="w")

        self.msg = ctk.CTkLabel(form, text="", text_color=RED, font=ctk.CTkFont(size=11))
        self.msg.pack(padx=20, pady=(6, 0), anchor="w")
        ctk.CTkButton(form, text="Save & Compute Urgency", height=38,
                      font=ctk.CTkFont(size=13, weight="bold"), command=self.add_task).pack(
            padx=20, pady=(8, 18), fill="x")

        feed = ctk.CTkFrame(p, corner_radius=12, fg_color=("gray92", "gray17"))
        feed.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        feed.grid_rowconfigure(1, weight=1)
        feed.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(feed, text="🔥 Smart Urgency Feed", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, padx=20, pady=(22, 8), sticky="w")
        self.feed = ctk.CTkScrollableFrame(feed, fg_color="transparent", height=420)
        self.feed.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 12))
        return p

    def on_slide(self, v):
        self.w_lbl.configure(text=f"Selected: {int(v)}")

    def add_task(self):
        if not self.current_user:
            return
        title = self.entry_title.get().strip()
        if not title:
            self.msg.configure(text="⚠ Please enter a task title.")
            return

        try:
            effort = float(self.entry_effort.get().strip())
        except ValueError:
            self.msg.configure(text="⚠ Estimated effort must be a number.")
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

        dl_str = dl.strftime("%Y-%m-%d %H:%M")
        weight = float(self.slider.get())

        database.add_task(
            title=title, deadline=dl_str, estimated_effort=effort,
            priority_weight=weight, user_id=self.current_user["id"]
        )
        self.entry_title.delete(0, "end")
        self.msg.configure(text="")
        self.refresh()

    def card(self, t):
        hours = t.get("hours_left", 0.0)
        score = t.get("tui_score", 0.0)
        tier = t.get("urgency_tier", "SAFE (Green)")
        color = color_for_tier(tier)
        short_tier = "CRITICAL" if "CRITICAL" in tier else ("MEDIUM" if "MEDIUM" in tier else "SAFE")

        c = ctk.CTkFrame(self.feed, corner_radius=10, fg_color=("white", "gray25"))
        c.pack(fill="x", pady=5, padx=4)
        ctk.CTkFrame(c, width=6, fg_color=color, corner_radius=0).pack(side="left", fill="y")

        box = ctk.CTkFrame(c, fg_color="transparent")
        box.pack(side="left", fill="both", expand=True, padx=12, pady=10)

        top_row = ctk.CTkFrame(box, fg_color="transparent")
        top_row.pack(fill="x")
        ctk.CTkLabel(top_row, text=t["title"], font=ctk.CTkFont(size=13, weight="bold"), anchor="w").pack(side="left")

        pill = ctk.CTkFrame(top_row, fg_color=color, corner_radius=8)
        pill.pack(side="right", padx=4)
        ctk.CTkLabel(pill, text=short_tier, font=ctk.CTkFont(size=10, weight="bold"),
                     text_color="white").pack(padx=8, pady=2)

        ctk.CTkLabel(box, text=f"⏳ {fmt_left(hours)}   •   TUI Score: {score:.2f}",
                     font=ctk.CTkFont(size=11), text_color="gray", anchor="w").pack(fill="x", pady=(2, 0))
        bar = ctk.CTkProgressBar(box, height=5, progress_color=color)
        bar.set(min(1.0, score))
        bar.pack(fill="x", pady=(6, 0))

        ctk.CTkButton(c, text="✓ Done", width=64, fg_color="transparent", border_width=1,
                      text_color=("gray10", "gray90"),
                      command=lambda task_id=t["id"]: self.complete(task_id)).pack(side="right", padx=10)

    def complete(self, task_id):
        database.mark_task_complete(task_id)
        self.refresh()

    # ---------------- Telemetry + Custom Keyword Manager (Sprint 3) ----------------
    def build_telemetry(self):
        p = self.new_page()
        ctk.CTkLabel(p, text="🛡️ Telemetry & Live Monitor", font=ctk.CTkFont(size=22, weight="bold")).grid(
            row=0, column=0, sticky="w", pady=(0, 12))

        kw_card = ctk.CTkFrame(p, corner_radius=12)
        kw_card.grid(row=1, column=0, sticky="ew", pady=(0, 15))
        kw_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(kw_card, text="🎯 Custom Distraction Keyword Filter (Per-User)",
                     font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, padx=20, pady=(14, 4), sticky="w")

        ctrl_row = ctk.CTkFrame(kw_card, fg_color="transparent")
        ctrl_row.grid(row=1, column=0, sticky="ew", padx=20, pady=(4, 8))

        self.entry_kw = ctk.CTkEntry(ctrl_row, placeholder_text="Add app/site keyword (e.g., TikTok, Chess)", width=240, height=32)
        self.entry_kw.pack(side="left", padx=(0, 8))
        ctk.CTkButton(ctrl_row, text="➕ Add Keyword", width=120, height=32,
                      command=self.handle_add_keyword).pack(side="left", padx=(0, 16))

        self.remove_kw_menu = ctk.CTkOptionMenu(ctrl_row, values=["YouTube"], width=150, height=32)
        self.remove_kw_menu.pack(side="left", padx=(0, 8))
        ctk.CTkButton(ctrl_row, text="🗑 Remove Selected", width=135, height=32, fg_color=RED,
                      hover_color="#B71C1C", command=self.handle_remove_keyword).pack(side="left")

        self.lbl_kw_list = ctk.CTkLabel(
            kw_card, text="", font=ctk.CTkFont(size=11), text_color="gray",
            wraplength=820, justify="left"
        )
        self.lbl_kw_list.grid(row=2, column=0, padx=20, pady=(0, 14), sticky="w")

        ctk.CTkLabel(p, text="Real-time Distraction Logs (Isolated per User)", text_color="gray").grid(
            row=2, column=0, sticky="w", pady=(5, 4))
        self.telemetry_box = ctk.CTkTextbox(p, corner_radius=12, height=310, font=ctk.CTkFont(family="Consolas", size=12))
        self.telemetry_box.grid(row=3, column=0, sticky="ew")
        return p

    def handle_add_keyword(self):
        if not self.current_user:
            return
        kw = self.entry_kw.get().strip()
        if kw and database.add_user_keyword(kw, self.current_user["id"]):
            self.entry_kw.delete(0, "end")
            telemetry.reload_user_keywords(self.current_user["id"])
            self.refresh()

    def handle_remove_keyword(self):
        if not self.current_user:
            return
        selected = self.remove_kw_menu.get()
        if selected:
            database.remove_user_keyword(selected, self.current_user["id"])
            telemetry.reload_user_keywords(self.current_user["id"])
            self.refresh()

    # ---------------- Sprint 3 Visual Focus Analytics Dashboard ----------------
    def build_analytics(self):
        p = self.new_page()

        header_row = ctk.CTkFrame(p, fg_color="transparent")
        header_row.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        ctk.CTkLabel(header_row, text="📈 Focus & Productivity Analytics (24h)",
                     font=ctk.CTkFont(size=22, weight="bold")).pack(side="left")
        ctk.CTkButton(header_row, text="📥 Export Analytics CSV", width=175, height=34,
                      command=self.export_analytics_csv).pack(side="right")

        self.export_msg = ctk.CTkLabel(header_row, text="", text_color=GRN, font=ctk.CTkFont(size=12))
        self.export_msg.pack(side="right", padx=12)

        kpi_row = ctk.CTkFrame(p, fg_color="transparent")
        kpi_row.grid(row=1, column=0, sticky="ew", pady=(0, 15))
        self.analytics_kpis = {}
        kpi_specs = [
            ("ratio", "Focus Efficiency"),
            ("prod", "Productive Time"),
            ("dist", "Distraction Time"),
            ("done", "Completed Tasks"),
        ]
        for i, (key, title) in enumerate(kpi_specs):
            kpi_row.grid_columnconfigure(i, weight=1)
            card = ctk.CTkFrame(kpi_row, corner_radius=12, height=95)
            card.grid(row=0, column=i, sticky="ew", padx=5)
            val_lbl = ctk.CTkLabel(card, text="--", font=ctk.CTkFont(size=26, weight="bold"))
            val_lbl.pack(pady=(14, 2))
            ctk.CTkLabel(card, text=title, text_color="gray", font=ctk.CTkFont(size=12)).pack(pady=(0, 14))
            self.analytics_kpis[key] = val_lbl

        ratio_card = ctk.CTkFrame(p, corner_radius=12)
        ratio_card.grid(row=2, column=0, sticky="ew", padx=5, pady=(0, 15))
        self.lbl_ratio_bar = ctk.CTkLabel(
            ratio_card, text="Productive vs. Distracting Ratio: 100% Productive",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.lbl_ratio_bar.pack(anchor="w", padx=20, pady=(15, 8))
        self.focus_progress_bar = ctk.CTkProgressBar(ratio_card, height=14, progress_color=GRN)
        self.focus_progress_bar.set(1.0)
        self.focus_progress_bar.pack(fill="x", padx=20, pady=(0, 18))

        top_card = ctk.CTkFrame(p, corner_radius=12)
        top_card.grid(row=3, column=0, sticky="ew", padx=5, pady=(0, 10))
        ctk.CTkLabel(top_card, text="🔥 Top Distracting Windows Logged",
                     font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", padx=20, pady=(15, 8))
        self.top_distractions_frame = ctk.CTkFrame(top_card, fg_color="transparent")
        self.top_distractions_frame.pack(fill="x", padx=20, pady=(0, 15))

        return p

    def export_analytics_csv(self):
        if not self.current_user:
            return
        uid = self.current_user["id"]
        uname = self.current_user["username"]
        summary = database.get_analytics_summary(uid)
        filename = f"academix_report_{uname}.csv"
        try:
            with open(filename, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Academix Engine - User Focus Report"])
                writer.writerow(["Username", uname])
                writer.writerow(["Generated At", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
                writer.writerow([])
                writer.writerow(["Metric", "Value"])
                writer.writerow(["Focus Efficiency (%)", f"{summary['focus_ratio']}%"])
                writer.writerow(["Productive Time (mins)", summary["productive_mins"]])
                writer.writerow(["Distracting Time (mins)", summary["distracting_mins"]])
                writer.writerow(["Completed Tasks", summary["completed_tasks"]])
                writer.writerow(["Pending Tasks", summary["pending_tasks"]])
                writer.writerow([])
                writer.writerow(["Top Distracting Window Title", "Logged Minutes", "Polled Samples"])
                for item in summary["top_distractions"]:
                    writer.writerow([item["title"], item["minutes"], item["samples"]])
            self.export_msg.configure(text=f"✓ Saved {filename}")
        except Exception as e:
            self.export_msg.configure(text=f"⚠ Export error: {e}", text_color=RED)

    # ---------------- Refresh / loop ----------------
    def refresh(self):
        if not self.current_user:
            return
        uid = self.current_user["id"]

        raw_tasks = database.fetch_tasks(status="pending", user_id=uid)
        distraction_minutes = database.get_distraction_minutes_last_hour(user_id=uid)
        sorted_tasks = sort_tasks_by_urgency(raw_tasks, distraction_minutes=distraction_minutes)

        for w in self.feed.winfo_children():
            w.destroy()
        for r in sorted_tasks:
            self.card(r)

        urgent_count = sum(1 for r in sorted_tasks if "CRITICAL" in r.get("urgency_tier", ""))
        self.stats["active"].configure(text=str(len(sorted_tasks)))
        self.stats["urgent"].configure(text=str(urgent_count))
        self.stats["focus"].configure(text=f"{distraction_minutes}m")

        if sorted_tasks:
            top = sorted_tasks[0]
            self.next_lbl.configure(text=top["title"])
            self.next_sub.configure(text=f"{fmt_left(top['hours_left'])}  |  TUI: {top['tui_score']:.2f} ({top['urgency_tier']})")
        else:
            self.next_lbl.configure(text="All clear 🎉")
            self.next_sub.configure(text="No pending tasks.")

        if hasattr(self, "lbl_kw_list") and self.lbl_kw_list.winfo_exists():
            kws = database.get_user_keywords(uid)
            self.lbl_kw_list.configure(text="Active Keywords: " + (", ".join(kws) if kws else "None"))
            if kws:
                self.remove_kw_menu.configure(values=kws)
                if self.remove_kw_menu.get() not in kws:
                    self.remove_kw_menu.set(kws[0])

        if hasattr(self, "telemetry_box") and self.telemetry_box.winfo_exists():
            try:
                logs = database.get_recent_logs(limit=15, user_id=uid)
                self.telemetry_box.configure(state="normal")
                self.telemetry_box.delete("0.0", "end")
                if logs:
                    for entry in logs:
                        raw_ts = entry.get("timestamp", "")
                        ts = raw_ts.split()[-1] if raw_ts else "--:--:--"
                        cat = entry.get("category", "Unknown")
                        title = (entry.get("window_title") or "Unknown")[:45]
                        icon = "❌" if cat == "Distracting" else "✅"
                        self.telemetry_box.insert("end", f"[{ts}] {icon} {cat:<12} | {title}\n")
                else:
                    self.telemetry_box.insert("end", "Waiting for telemetry samples...\n")
                self.telemetry_box.configure(state="disabled")
            except Exception as e:
                print("Telemetry box update error:", e)

        if hasattr(self, "analytics_kpis") and self.analytics_kpis:
            summary = database.get_analytics_summary(uid)
            ratio = summary["focus_ratio"]
            self.analytics_kpis["ratio"].configure(
                text=f"{ratio}%", text_color=GRN if ratio >= 70 else (YEL if ratio >= 45 else RED)
            )
            self.analytics_kpis["prod"].configure(text=f"{summary['productive_mins']}m")
            self.analytics_kpis["dist"].configure(text=f"{summary['distracting_mins']}m")
            self.analytics_kpis["done"].configure(text=str(summary["completed_tasks"]))

            self.lbl_ratio_bar.configure(
                text=f"Productive vs. Distracting Ratio (24h): {ratio}% Productive  •  {round(100 - ratio, 1)}% Distracting"
            )
            self.focus_progress_bar.configure(progress_color=GRN if ratio >= 70 else (YEL if ratio >= 45 else RED))
            self.focus_progress_bar.set(max(0.0, min(1.0, ratio / 100.0)))

            for child in self.top_distractions_frame.winfo_children():
                child.destroy()

            top_list = summary["top_distractions"]
            if not top_list:
                ctk.CTkLabel(self.top_distractions_frame, text="No distracting windows logged yet. Great focus! 🎉",
                             text_color="gray").pack(anchor="w", pady=4)
            else:
                max_samples = max(item["samples"] for item in top_list) or 1
                for item in top_list:
                    row_f = ctk.CTkFrame(self.top_distractions_frame, fg_color="transparent")
                    row_f.pack(fill="x", pady=4)
                    title_short = item["title"][:55]
                    ctk.CTkLabel(row_f, text=f"❌ {title_short}", width=380, anchor="w",
                                 font=ctk.CTkFont(size=12)).pack(side="left")
                    bar = ctk.CTkProgressBar(row_f, height=8, width=220, progress_color=RED)
                    bar.set(item["samples"] / max_samples)
                    bar.pack(side="left", padx=12)
                    ctk.CTkLabel(row_f, text=f"{item['minutes']}m ({item['samples']}s)",
                                 font=ctk.CTkFont(size=12, weight="bold"), text_color="gray").pack(side="right")