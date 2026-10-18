"""LeafyGreen - all-in-one installer and setup.

This single file does everything. Double-click it (or run  py setup.py ).
It asks for administrator rights, installs LeafyGreen (the same steps as
install.bat: build, copy to Program Files, lock the settings folder and
create the background task), then walks through the five setup steps:

    1. Activation key
    2. Daily screen time limits and bedtime
    3. Always Allowed and Always Blocked websites and apps
    4. Limited apps
    5. Accounts (3 at most: at least one Complete and one Child) and the
       4-digit PIN for the computer itself

Run it again later and it offers to redo the setup (PIN needed) or to
uninstall LeafyGreen. Keep this file in the same folder as leafygreen.py,
install.bat and uninstall.bat. The activation keys setup will accept are read
from the child's own folder: C:\\Users\\<Child>\\leafygreen\\activation_keys.txt
(put it there before you install).
"""
import ctypes
import json
import os
import subprocess
import sys
import time
import tkinter as tk
import uuid
from tkinter import messagebox, simpledialog, ttk

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

STEPS = ("1  Activation", "2  Screen Time", "3  Websites & Apps",
         "4  Limited Apps", "5  Accounts")


def fail_early(text):
    root = tk.Tk()
    root.withdraw()
    # Notify
    messagebox.showerror("LeafyGreen Setup", text)
    root.destroy()
    sys.exit(1)


try:
    import leafygreen as lg
except ImportError:
    fail_early("leafygreen.py must be in the same folder as setup.py.")


class Backend:
    """How setup talks to LeafyGreen.

    Installed (install.bat has made the inbox folder): the finished setup is
    written to the inbox as a request file, and LeafyGreen's launcher, which
    runs as SYSTEM, checks it and saves the settings. Not installed yet: the
    same checks run right here and the settings file is written directly.
    """
    TIMEOUT = 25

    def __init__(self):
        self.inbox = os.path.join(lg.SETTINGS_DIR, "inbox")
        self.outbox = os.path.join(lg.SETTINGS_DIR, "outbox")
        self.direct = lg.SetupService()

    def installed(self):
        return os.path.isdir(self.inbox)

    def setup_done(self):
        """True if LeafyGreen was already set up, False if not, None if
        that can't be told (then LeafyGreen itself decides later)."""
        if self.installed():
            try:
                with open(os.path.join(self.outbox, "status.json"),
                          encoding="utf-8") as f:
                    return bool(json.load(f).get("setup_done"))
            except (OSError, ValueError):
                return None
        data = lg.Data.load()
        return None if data.unreadable else data.setup_done

    def request(self, payload, pump=None):
        """Sends a request and returns LeafyGreen's answer (a dict)."""
        payload = dict(payload, v=1)
        if not self.installed():
            return self.direct.handle(json.dumps(payload))
        rid = uuid.uuid4().hex
        try:
            with open(os.path.join(self.inbox, rid + ".json"), "w",
                      encoding="utf-8") as f:
                json.dump(payload, f)
        except OSError as exc:
            return {"ok": False, "code": "send", "message":
                    f"Could not reach LeafyGreen ({exc}). Run install.bat "
                    "again, then try setup again."}
        answer = os.path.join(self.outbox, rid + ".json")
        end = time.monotonic() + self.TIMEOUT
        while time.monotonic() < end:
            try:
                with open(answer, encoding="utf-8") as f:
                    return json.load(f)
            except (OSError, ValueError):
                pass
            if pump:
                pump()
            time.sleep(0.2)
        return {"ok": False, "code": "timeout", "message":
                "LeafyGreen did not answer. Make sure install.bat finished "
                "and the computer has been restarted, then try again."}


class SetupApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("LeafyGreen Setup")
        self.configure(bg=lg.BG)
        self.geometry("980x740")
        self.minsize(900, 700)
        lg.apply_style(self)

        self.allowed = []
        self.blocked = []
        self.limited = []
        self.accounts = []
        self.reached = 0
        self.backend = Backend()
        self.current_pin = ""
        self.finished = False

        self._build_header()
        self.header_end = ttk.Frame(self, height=1)
        self.header_end.pack(fill="x")
        self._build_nav()
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.steps = [self._step_activation, self._step_screen_time,
                      self._step_lists, self._step_limited,
                      self._step_accounts]
        self.frames = []
        for title, builder in zip(STEPS, self.steps):
            frame = ttk.Frame(self.nb, padding=18)
            self.nb.add(frame, text=title)
            builder(frame)
            self.frames.append(frame)
        self.nb.bind("<<NotebookTabChanged>>", self._tab_changed)
        self._update_tabs()
        self.bind("<Return>", self._return_key)

    def _build_header(self):
        header = tk.Frame(self, bg=lg.NAVY)
        header.pack(fill="x")
        tk.Label(header, text="LeafyGreen Setup", bg=lg.NAVY, fg="white",
                 font=(lg.FONT, 20, "bold")).pack(anchor="w", padx=22,
                                                  pady=(16, 0))
        self.header_sub = tk.Label(
            header, text="Finish all five steps before using LeafyGreen",
            bg=lg.NAVY, fg="#cfe6d9", font=(lg.FONT, 10))
        self.header_sub.pack(anchor="w", padx=22, pady=(0, 14))

    def _build_nav(self):
        bar = ttk.Frame(self, padding=(12, 10))
        bar.pack(fill="x")
        self.prev_btn = ttk.Button(bar, text="\u2039  Previous", width=14,
                                   command=self.previous)
        self.prev_btn.pack(side="left")
        self.next_btn = ttk.Button(bar, text="Next  \u203A", width=14,
                                   style="Accent.TButton", command=self.next)
        self.next_btn.pack(side="right")
        self.step_label = tk.StringVar()
        ttk.Label(bar, textvariable=self.step_label,
                  font=(lg.FONT, 11, "bold")).pack(expand=True)
        self.nav_bar = bar

    def _return_key(self, event=None):
        if not self.finished and isinstance(self.focus_get(),
                                            (ttk.Entry, tk.Entry)):
            if self.nb.index("current") == 0:
                self.next()

    def current(self):
        return self.nb.index("current")

    def _tab_changed(self, event=None):
        if self.finished:
            return
        i = self.current()
        last = len(STEPS) - 1
        self.step_label.set(f"Step {i + 1} of {len(STEPS)}")
        self.prev_btn.state(["!disabled" if i > 0 else "disabled"])
        self.next_btn.configure(text="Finish  \u2713" if i == last
                                else "Next  \u203A")

    def _update_tabs(self):
        for i in range(len(STEPS)):
            self.nb.tab(i, state="normal" if i <= self.reached
                        else "disabled")
        self._tab_changed()

    def previous(self):
        i = self.current()
        if i > 0:
            self.nb.select(i - 1)

    def next(self):
        i = self.current()
        if not self._validate(i):
            return
        if i < len(STEPS) - 1:
            self.reached = max(self.reached, i + 1)
            self._update_tabs()
            self.nb.select(i + 1)
        else:
            self.finish()

    def _validate(self, i):
        return (self._check_key, self._check_screen_time, lambda: True,
                lambda: True, self._check_accounts)[i]()

    @staticmethod
    def _title(parent, text, sub):
        ttk.Label(parent, text=text, style="H1.TLabel").pack(anchor="w")
        ttk.Label(parent, text=sub, style="Muted.TLabel", wraplength=880,
                  justify="left").pack(anchor="w", pady=(0, 10))

    @staticmethod
    def _notice(parent):
        """The "you can change this later" band shown on steps 2 to 5."""
        band = tk.Frame(parent, bg=lg.GREEN_BG, highlightthickness=1,
                        highlightbackground=lg.GREEN)
        band.pack(fill="x", pady=(0, 12))
        tk.Label(band, text="\u2139", bg=lg.GREEN_BG, fg=lg.GREEN,
                 font=(lg.FONT, 14, "bold")).pack(side="left", padx=(12, 6),
                                                  pady=8)
        tk.Label(band, text="You can always change this later in "
                 "LeafyGreen. Nothing here is permanent.", bg=lg.GREEN_BG,
                 fg=lg.GREEN, font=(lg.FONT, 10, "bold")).pack(
            side="left", pady=8)

    def _step_activation(self, f):
        self._title(f, "Activation", "Type the activation key you were "
                    "given. LeafyGreen can't be used without it.")
        card = ttk.Frame(f, style="Card.TFrame", padding=24)
        card.pack(anchor="w", fill="x")
        ttk.Label(card, text="Activation key", style="CardBody.TLabel").pack(
            anchor="w")
        self.key_var = tk.StringVar()
        self.key_entry = ttk.Entry(card, textvariable=self.key_var, width=26,
                                   font=(lg.FONT, 16))
        self.key_entry.pack(anchor="w", pady=(4, 6))
        self.key_entry.bind("<KeyPress>", lambda e: self.key_msg.set(""))
        self.key_msg = tk.StringVar()
        self.key_label = tk.Label(card, textvariable=self.key_msg, bg="white",
                                  fg=lg.RED, font=(lg.FONT, 10, "bold"))
        self.key_label.pack(anchor="w")
        ttk.Label(card, text="Type one of the keys listed in the child's "
                  "activation_keys.txt (C:\\Users\\<Child>\\leafygreen\\), "
                  "exactly as written. You can add more keys and end dates "
                  "later with Ctrl+Shift+A on the My Account tab.",
                  style="CardText.TLabel", wraplength=560,
                  justify="left").pack(anchor="w", pady=(8, 0))
        self.after(200, self.key_entry.focus_set)

    def _check_key(self):
        if self.key_var.get().strip():
            self.key_label.configure(fg=lg.GREEN)
            self.key_msg.set("\u2713 Key entered")
            return True
        self.key_label.configure(fg=lg.RED)
        self.key_msg.set("Type the activation key.")
        self.key_entry.focus_set()
        return False

    def _step_screen_time(self, f):
        self._title(f, "Daily screen time and bedtime", "How much screen "
                    "time is allowed each day, and when the computer should "
                    "lock for the night.")
        self._notice(f)
        card = ttk.Frame(f, style="Card.TFrame", padding=14)
        card.pack(fill="x")
        limits = lg.default_limits()
        self.day_rows = {}
        for r, day in enumerate(lg.DAYS):
            enabled = tk.BooleanVar(value=limits[day]["enabled"])
            hours = tk.StringVar(value=str(limits[day]["minutes"] // 60))
            mins = tk.StringVar(value=str(limits[day]["minutes"] % 60))
            ttk.Checkbutton(card, text=day, variable=enabled, width=12,
                            style="Card.TCheckbutton",
                            command=lambda d=day: self._sync_day(d)).grid(
                row=r, column=0, sticky="w", pady=2)
            sp_h = ttk.Spinbox(card, from_=0, to=24, width=4,
                               textvariable=hours)
            sp_h.grid(row=r, column=1, padx=(8, 2))
            ttk.Label(card, text="hours", style="CardBody.TLabel").grid(
                row=r, column=2)
            sp_m = ttk.Spinbox(card, from_=0, to=59, width=4,
                               textvariable=mins)
            sp_m.grid(row=r, column=3, padx=(10, 2))
            ttk.Label(card, text="minutes", style="CardBody.TLabel").grid(
                row=r, column=4)
            self.day_rows[day] = (enabled, hours, mins, sp_h, sp_m)
            self._sync_day(day)
        ttk.Button(card, text="Copy Monday to All Days",
                   command=self._copy_monday).grid(
            row=0, column=6, padx=(30, 0), sticky="e")
        card.columnconfigure(5, weight=1)

        bed = ttk.Frame(f, style="Card.TFrame", padding=14)
        bed.pack(fill="x", pady=(12, 0))
        ttk.Label(bed, text="Bedtime", style="H2.TLabel").grid(
            row=0, column=0, sticky="w")
        self.bed_on = tk.BooleanVar(value=True)
        ttk.Checkbutton(bed, text="Lock the screen at bedtime",
                        style="Card.TCheckbutton",
                        variable=self.bed_on).grid(row=1, column=0,
                                                   columnspan=2, sticky="w")
        self.bed_start = tk.StringVar(value="21:00")
        self.bed_end = tk.StringVar(value="07:00")
        ttk.Label(bed, text="From", style="CardBody.TLabel").grid(
            row=2, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(bed, textvariable=self.bed_start, width=8).grid(
            row=2, column=1, padx=8, pady=(8, 0))
        ttk.Label(bed, text="to", style="CardBody.TLabel").grid(
            row=2, column=2, pady=(8, 0))
        ttk.Entry(bed, textvariable=self.bed_end, width=8).grid(
            row=2, column=3, padx=8, pady=(8, 0))
        ttk.Label(bed, text="24-hour time, HH:MM", style="CardText.TLabel"
                  ).grid(row=2, column=4, sticky="w", pady=(8, 0))

    def _sync_day(self, day):
        enabled, _, _, sp_h, sp_m = self.day_rows[day]
        state = "normal" if enabled.get() else "disabled"
        sp_h.configure(state=state)
        sp_m.configure(state=state)

    def _copy_monday(self):
        enabled, hours, mins, _, _ = self.day_rows["Monday"]
        for day in lg.DAYS[1:]:
            e, h, m, _, _ = self.day_rows[day]
            e.set(enabled.get())
            h.set(hours.get())
            m.set(mins.get())
            self._sync_day(day)

    def _check_screen_time(self):
        limits = {}
        for day, (enabled, hours, mins, _, _) in self.day_rows.items():
            try:
                h, m = int(hours.get()), int(mins.get())
            except ValueError:
                # Notify
                messagebox.showerror("LeafyGreen Setup",
                                     f"Enter whole numbers for {day}.")
                return False
            if not (0 <= h <= 24 and 0 <= m <= 59) or h * 60 + m > 1440:
                # Notify
                messagebox.showerror("LeafyGreen Setup", f"The limit for "
                                     f"{day} must be 24 hours or less.")
                return False
            limits[day] = {"enabled": enabled.get(), "minutes": h * 60 + m}
        start, end = self.bed_start.get().strip(), self.bed_end.get().strip()
        if not (lg.TIME_RE.match(start) and lg.TIME_RE.match(end)):
            # Notify
            messagebox.showerror("LeafyGreen Setup", "Bedtime times must "
                                 "look like 21:00 (HH:MM, 24-hour).")
            return False
        self.limits = limits
        self.bedtime = {"enabled": self.bed_on.get(), "start": start,
                        "end": end}
        return True

    def _step_lists(self, f):
        self._title(f, "Websites and apps", "Choose what is always allowed "
                    "and what is always blocked. Anything you don't list is "
                    "handled by LeafyGreen's normal rules (and SmartSafe "
                    "checks new websites for you).")
        self._notice(f)
        row = ttk.Frame(f)
        row.pack(fill="both", expand=True)
        row.columnconfigure((0, 1), weight=1, uniform="lists")
        row.rowconfigure(0, weight=1)
        self.allow_ui = self._list_card(
            row, 0, "Always Allowed", "Never blocked or limited.",
            self.allowed, self.blocked, "Always Blocked")
        self.block_ui = self._list_card(
            row, 1, "Always Blocked", "Never allowed.", self.blocked,
            self.allowed, "Always Allowed")

    def _list_card(self, parent, col, title, blurb, items, other,
                   other_title):
        card = ttk.Frame(parent, style="Card.TFrame", padding=12)
        card.grid(row=0, column=col, sticky="nsew",
                  padx=(0, 6) if col == 0 else (6, 0))
        ttk.Label(card, text=title, style="H2.TLabel").pack(anchor="w")
        ttk.Label(card, text=blurb, style="CardText.TLabel").pack(anchor="w")
        bar = ttk.Frame(card, style="Inner.TFrame")
        bar.pack(fill="x", pady=(8, 6))
        name = tk.StringVar()
        kind = tk.StringVar(value="Website")
        entry = ttk.Entry(bar, textvariable=name, width=20)
        entry.pack(side="left", fill="x", expand=True)
        ttk.Combobox(bar, textvariable=kind, state="readonly", width=9,
                     values=("Website", "App")).pack(side="left", padx=6)
        wrap, tree = lg.make_tree(card, [("name", "Name", 200, "w"),
                                         ("type", "Type", 80, "w")],
                                  height=5)

        def refresh():
            lg.rebuild_tree(tree, [(str(i), (r[0], r[1]), ())
                                   for i, r in enumerate(items)])

        def add(event=None):
            text = name.get().strip()
            if not text:
                return
            if kind.get() == "Website":
                site = lg.normalize_site_name(text)
                if site is None:
                    # Notify
                    messagebox.showwarning(
                        "LeafyGreen Setup", "That doesn't look like a "
                        "website address. Type something like example.com "
                        "(no spaces).")
                    return
                text = site
            else:
                text = lg.normalize_app_name(text)
            if not text:
                return
            low = text.lower()
            if any(r[0].lower() == low for r in items):
                # Notify
                messagebox.showinfo("LeafyGreen Setup",
                                    f"'{text}' is already in this list.")
                return
            if any(r[0].lower() == low for r in other):
                # Notify
                messagebox.showwarning(
                    "LeafyGreen Setup", f"'{text}' is already in "
                    f"{other_title}. Remove it there first.")
                return
            if kind.get() == "App" and self._protected(text):
                # Notify
                messagebox.showwarning(
                    "LeafyGreen Setup", f"'{text}' is needed by Windows or "
                    "by LeafyGreen itself, so it can't be listed.")
                return
            items.append([text, kind.get(), lg.today_str()])
            name.set("")
            refresh()
            entry.focus_set()

        def remove():
            picked = sorted((int(i) for i in tree.selection()), reverse=True)
            for i in picked:
                del items[i]
            refresh()

        ttk.Button(bar, text="Add", style="Accent.TButton",
                   command=add).pack(side="left")
        entry.bind("<Return>", lambda e: (add(), "break")[1])
        wrap.pack(fill="both", expand=True)
        ttk.Button(card, text="Remove Selected", command=remove).pack(
            anchor="w", pady=(8, 0))
        ttk.Label(card, text="Examples: example.com, Game.exe",
                  style="CardText.TLabel").pack(anchor="w", pady=(6, 0))
        return {"refresh": refresh, "tree": tree}

    @staticmethod
    def _protected(app_name):
        low = app_name.lower()
        return (low in lg.PROTECTED_APP_NAMES
                or low in lg.CRITICAL_PROCESSES)

    def _step_limited(self, f):
        self._title(f, "Limited apps", "Give specific apps their own daily "
                    "time limit. Time counts while the app is running; when "
                    "it is used up, the app is closed until tomorrow.")
        self._notice(f)
        card = ttk.Frame(f, style="Card.TFrame", padding=14)
        card.pack(fill="both", expand=True)
        bar = ttk.Frame(card, style="Inner.TFrame")
        bar.pack(fill="x", pady=(0, 8))
        self.lim_name = tk.StringVar()
        self.lim_min = tk.StringVar(value="60")
        ttk.Label(bar, text="App name", style="CardBody.TLabel").pack(
            side="left")
        entry = ttk.Entry(bar, textvariable=self.lim_name, width=24)
        entry.pack(side="left", padx=8)
        ttk.Label(bar, text="Minutes per day", style="CardBody.TLabel").pack(
            side="left", padx=(8, 0))
        ttk.Spinbox(bar, from_=5, to=1440, increment=5, width=7,
                    textvariable=self.lim_min).pack(side="left", padx=8)
        ttk.Button(bar, text="Add App", style="Accent.TButton",
                   command=self._add_limited).pack(side="left")
        entry.bind("<Return>", lambda e: self._add_limited())
        wrap, self.lim_tree = lg.make_tree(card, [
            ("name", "App", 320, "w"), ("limit", "Daily limit", 160, "w")],
            height=8)
        wrap.pack(fill="both", expand=True)
        bottom = ttk.Frame(card, style="Inner.TFrame")
        bottom.pack(fill="x", pady=(8, 0))
        ttk.Button(bottom, text="Remove Selected",
                   command=self._remove_limited).pack(side="left")
        ttk.Label(bottom, text="Optional: leave it empty if you don't "
                  "want any.", style="CardText.TLabel").pack(side="left",
                                                           padx=12)

    def _refresh_limited(self):
        lg.rebuild_tree(self.lim_tree, [
            (str(i), (a["name"], f"{a['limit']} min"), ())
            for i, a in enumerate(self.limited)])

    def _add_limited(self):
        name = lg.normalize_app_name(self.lim_name.get().strip())
        if not name:
            # Notify
            messagebox.showinfo("LeafyGreen Setup", "Enter an app name.")
            return
        try:
            minutes = int(self.lim_min.get())
        except ValueError:
            minutes = 0
        if not 1 <= minutes <= 1440:
            # Notify
            messagebox.showerror("LeafyGreen Setup", "Enter a limit between "
                                 "1 and 1440 minutes.")
            return
        low = name.lower()
        if self._protected(name):
            # Notify
            messagebox.showwarning(
                "LeafyGreen Setup", f"'{name}' is needed by Windows or by "
                "LeafyGreen itself, so it can't be limited.")
            return
        if any(a["name"].lower() == low for a in self.limited):
            # Notify
            messagebox.showinfo("LeafyGreen Setup",
                                f"'{name}' already has a limit.")
            return
        if any(r[0].lower() == low for r in self.allowed):
            # Notify
            messagebox.showwarning(
                "LeafyGreen Setup", f"'{name}' is on your Always Allowed "
                "list, and allowed apps are never limited. Remove it from "
                "that list in step 3 first.")
            return
        if any(r[0].lower() == low for r in self.blocked):
            # Notify
            messagebox.showwarning(
                "LeafyGreen Setup", f"'{name}' is on your Always Blocked "
                "list, so it can't be opened at all.")
            return
        self.limited.append({"name": name, "limit": minutes,
                             "used_sec": 0.0})
        self.lim_name.set("")
        self._refresh_limited()

    def _remove_limited(self):
        for i in sorted((int(i) for i in self.lim_tree.selection()),
                        reverse=True):
            del self.limited[i]
        self._refresh_limited()

    def _step_accounts(self, f):
        self._title(f, "Accounts and PIN", "Accounts sign in to the Web "
                    "Dashboard from another computer. The PIN is for this "
                    "computer.")
        self._notice(f)
        row = ttk.Frame(f)
        row.pack(fill="both", expand=True)
        row.columnconfigure(0, weight=3, uniform="a")
        row.columnconfigure(1, weight=2, uniform="a")
        row.rowconfigure(0, weight=1)

        left = ttk.Frame(row, style="Card.TFrame", padding=12)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        ttk.Label(left, text=f"Accounts (up to {lg.SETUP_MAX_ACCOUNTS})",
                  style="H2.TLabel").pack(anchor="w")
        ttk.Label(left, text="Lite: review requests and make coupons.  "
                  "Complete: change any setting.  Child: look at everything "
                  "and send requests.", style="CardText.TLabel",
                  wraplength=470, justify="left").pack(anchor="w",
                                                       pady=(0, 8))
        bar = ttk.Frame(left, style="Inner.TFrame")
        bar.pack(fill="x", pady=(0, 6))
        self.add_acct_btn = ttk.Button(bar, text="Add Account",
                                       style="Accent.TButton",
                                       command=self._add_account)
        self.add_acct_btn.pack(side="left")
        ttk.Button(bar, text="Remove Selected",
                   command=self._remove_account).pack(side="left", padx=8)
        wrap, self.acct_tree = lg.make_tree(left, [
            ("user", "Username", 220, "w"), ("role", "Role", 120, "w")],
            height=4)
        wrap.pack(fill="x")
        self.req_vars = []
        self.req_box = ttk.Frame(left, style="Inner.TFrame")
        self.req_box.pack(fill="x", pady=(10, 0))
        for _ in range(3):
            var = tk.StringVar()
            lbl = tk.Label(self.req_box, textvariable=var, bg="white",
                           anchor="w", font=(lg.FONT, 10, "bold"))
            lbl.pack(anchor="w")
            self.req_vars.append((var, lbl))

        right = ttk.Frame(row, style="Card.TFrame", padding=12)
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        ttk.Label(right, text="PIN for this computer",
                  style="H2.TLabel").pack(anchor="w")
        ttk.Label(right, text="Unlocks changes in LeafyGreen on this "
                  "computer.", style="CardText.TLabel", wraplength=300,
                  justify="left").pack(anchor="w", pady=(0, 6))
        for text, attr in (("Create a 4-digit PIN", "pin1"),
                           ("Confirm PIN", "pin2")):
            tk.Label(right, text=text, bg="white", fg=lg.TEXT,
                     font=(lg.FONT, 10, "bold")).pack(pady=(8, 4))
            entry = lg.PinEntry(right, on_edit=self._requirements)
            entry.configure(bg="white")
            entry.pack()
            setattr(self, attr, entry)
        self._refresh_accounts()

    def _add_account(self):
        if len(self.accounts) >= lg.SETUP_MAX_ACCOUNTS:
            return
        dlg = lg.ParentDialog(self, "Add Account",
                              [a[0] for a in self.accounts])
        if dlg.result:
            self.accounts.append(tuple(dlg.result))
            self._refresh_accounts()

    def _remove_account(self):
        for i in sorted((int(i) for i in self.acct_tree.selection()),
                        reverse=True):
            del self.accounts[i]
        self._refresh_accounts()

    def _refresh_accounts(self):
        lg.rebuild_tree(self.acct_tree, [
            (str(i), (a[0], a[2]), ()) for i, a in enumerate(self.accounts)])
        self.add_acct_btn.state(["!disabled" if len(self.accounts)
                                 < lg.SETUP_MAX_ACCOUNTS else "disabled"])
        self._requirements()

    def _requirements(self):
        roles = [a[2] for a in self.accounts]
        pin_ok = (len(self.pin1.get()) == 4
                  and self.pin1.get() == self.pin2.get())
        checks = (("At least one Complete account", "Complete" in roles),
                  ("At least one Child account", "Child" in roles),
                  ("PIN entered twice, the same both times", pin_ok))
        for (var, lbl), (text, ok) in zip(self.req_vars, checks):
            var.set(("\u2713 " if ok else "\u2610 ") + text)
            lbl.configure(fg=lg.GREEN if ok else lg.MUTED)
        return all(ok for _, ok in checks)

    def _check_accounts(self):
        roles = [a[2] for a in self.accounts]
        if "Complete" not in roles or "Child" not in roles:
            # Notify
            messagebox.showwarning(
                "LeafyGreen Setup", "Add at least one Complete account and "
                "one Child account (three accounts at most).")
            return False
        pin, again = self.pin1.get(), self.pin2.get()
        if len(pin) != 4 or not pin.isdigit():
            # Notify
            messagebox.showwarning("LeafyGreen Setup",
                                   "Enter a 4-digit PIN.")
            self.pin1.focus_first()
            return False
        if pin != again:
            # Notify
            messagebox.showwarning("LeafyGreen Setup",
                                   "The two PINs don't match.")
            self.pin2.clear()
            return False
        return True

    def _pin_error(self, pin):
        """Asks LeafyGreen whether this PIN is right. Error text or None."""
        answer = self._send({"type": "check_pin", "pin": pin})
        if answer.get("ok"):
            self.current_pin = pin
            return None
        return answer.get("message") or "That PIN is not correct."

    def require_pin(self):
        """Shown when running setup again. True once the PIN was proven."""
        dlg = lg.PinDialog(self, "Enter PIN",
                           ["Enter the PIN to run setup again"],
                           lambda v: self._pin_error(v[0]))
        return bool(dlg.result)

    def gate(self):
        """Before anything is shown: a repeat run needs the parental PIN."""
        self.nav_bar.pack_forget()
        self.nb.pack_forget()
        if not self.require_pin():
            self.destroy()
            return
        # Notify
        if not messagebox.askyesno(
                "LeafyGreen Setup", "LeafyGreen is already set up.\n\n"
                "Running setup again replaces the PIN, accounts, time limits "
                "and lists with the new ones. Continue?"):
            self.destroy()
            return
        self.nav_bar.pack(fill="x", after=self.header_end)
        self.nb.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    def _send(self, payload):
        """One request to LeafyGreen, with a busy cursor while waiting."""
        self.configure(cursor="watch")
        self.next_btn.state(["disabled"])
        self.update()
        try:
            return self.backend.request(payload, pump=self.update)
        finally:
            self.configure(cursor="")
            self.next_btn.state(["!disabled"])

    def config(self):
        return {"limits": self.limits, "bedtime": self.bedtime,
                "allowed": [list(r) for r in self.allowed],
                "blocked": [list(r) for r in self.blocked],
                "limited": [dict(a) for a in self.limited],
                "accounts": [{"username": n, "password": p, "role": r}
                             for n, p, r in self.accounts],
                "new_pin": self.pin1.get()}

    def finish(self):
        payload = {"type": "setup", "key": self.key_var.get().strip(),
                   "pin": self.current_pin, "config": self.config()}
        answer = self._send(payload)
        while answer.get("code") == "pin":
            dlg = lg.PinDialog(self, "Enter PIN",
                               ["Enter the PIN to run setup again"],
                               lambda v: self._pin_error(v[0]))
            if not dlg.result:
                return
            payload["pin"] = self.current_pin
            answer = self._send(payload)
        if answer.get("ok"):
            self._show_done()
            return
        message = answer.get("message") or "Setup could not be saved."
        if answer.get("code") == "write":
            message += ("\n\nIf LeafyGreen is installed, run install.bat "
                        "again and then try setup again.")
        # Notify
        messagebox.showerror("LeafyGreen Setup", message)
        if answer.get("code") == "key":
            self.nb.select(0)

    def _show_done(self):
        self.finished = True
        self.header_sub.configure(text="All done")
        done = ttk.Frame(self.nb, padding=30)
        self.nb.add(done, text="Done")
        for i in range(len(STEPS)):
            self.nb.tab(i, state="disabled")
        self.nb.select(done)
        self.nav_bar.pack_forget()
        tk.Label(done, text="\u2713", fg="white", bg=lg.GREEN,
                 font=(lg.FONT, 40, "bold"), width=3).pack(pady=(30, 14))
        ttk.Label(done, text="Setup is complete", style="H1.TLabel").pack()
        tk.Label(done, text="Restart the computer to apply the changes.\n\n"
                 "LeafyGreen will then start automatically every time your "
                 "child logs on.", bg=lg.BG, fg=lg.TEXT,
                 font=(lg.FONT, 13), justify="center",
                 wraplength=620).pack(pady=(14, 24))
        buttons = ttk.Frame(done)
        buttons.pack()
        ttk.Button(buttons, text="Restart Now", style="Accent.TButton",
                   command=self.restart_now).pack(side="left", padx=6)
        ttk.Button(buttons, text="Close", command=self.destroy).pack(
            side="left", padx=6)

    def restart_now(self):
        # Notify
        if not messagebox.askyesno("LeafyGreen Setup", "Restart this "
                                   "computer in 30 seconds?"):
            return
        try:
            subprocess.run(["shutdown", "/r", "/t", "30", "/c",
                            "LeafyGreen setup is complete."], check=False)
        except OSError as exc:
            # Notify
            messagebox.showerror("LeafyGreen Setup",
                                 f"Could not restart: {exc}")


APPNAME = "LeafyGreen"


def _program_files():
    return (os.environ.get("ProgramW6432") or os.environ.get("ProgramFiles")
            or r"C:\Program Files")


def install_exe():
    return os.path.join(_program_files(), APPNAME, APPNAME + ".exe")


def is_installed():
    if os.path.exists(install_exe()):
        return True
    try:
        return os.path.isdir(os.path.join(lg.SETTINGS_DIR, "inbox"))
    except OSError:
        return False


def is_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def elevate():
    """Re-launch this script with administrator rights (shows a UAC prompt).
    Returns False if it could not be started."""
    try:
        if getattr(sys, "frozen", False):
            params = ""
            target = sys.executable
        else:
            params = subprocess.list2cmdline([os.path.abspath(__file__)])
            target = sys.executable
        rc = ctypes.windll.shell32.ShellExecuteW(None, "runas", target,
                                                 params, HERE, 1)
        return int(rc) > 32
    except Exception:
        return False


def _mini_root():
    root = tk.Tk()
    root.withdraw()
    try:
        lg.apply_style(root)
    except Exception:
        pass
    return root


def ask_child_name(root):
    """Ask for the child's Windows account name, checking it exists.
    Returns the name, or None if cancelled."""
    while True:
        name = simpledialog.askstring(
            "LeafyGreen", "Windows account name of the child\n"
            "(as shown on the sign-in screen):", parent=root)
        if name is None:
            return None
        name = name.strip()
        if not name:
            continue
        try:
            exists = subprocess.run(["net", "user", name],
                                    capture_output=True).returncode == 0
        except OSError:
            exists = True
        if not exists:
            # Notify
            messagebox.showerror(
                "LeafyGreen", f"There is no account called '{name}' on this "
                "computer. Check the name and try again.", parent=root)
            continue
        return name


def choose_action(root):
    """Already installed: ask whether to redo setup or uninstall.
    Returns 'redo', 'uninstall' or None."""
    dlg = tk.Toplevel(root)
    dlg.title("LeafyGreen")
    dlg.configure(bg=lg.BG)
    dlg.resizable(False, False)
    dlg.transient(root)
    choice = {"v": None}
    ttk.Label(dlg, text="LeafyGreen is already installed.",
              style="H1.TLabel").pack(anchor="w", padx=20, pady=(18, 4))
    ttk.Label(dlg, text="What would you like to do?",
              style="Muted.TLabel").pack(anchor="w", padx=20, pady=(0, 14))
    bar = ttk.Frame(dlg, padding=(20, 0, 20, 18))
    bar.pack(fill="x")

    def pick(v):
        choice["v"] = v
        dlg.destroy()

    ttk.Button(bar, text="Redo Setup", style="Accent.TButton",
               command=lambda: pick("redo")).pack(side="left")
    ttk.Button(bar, text="Uninstall", style="Danger.TButton",
               command=lambda: pick("uninstall")).pack(side="left", padx=8)
    ttk.Button(bar, text="Cancel",
               command=lambda: pick(None)).pack(side="right")
    dlg.update_idletasks()
    try:
        dlg.wait_visibility()
        dlg.grab_set()
    except tk.TclError:
        pass
    dlg.protocol("WM_DELETE_WINDOW", lambda: pick(None))
    dlg.wait_window()
    return choice["v"]


def run_batch(name, extra_env=None):
    """Run install.bat / uninstall.bat in --bundled mode. Returns True on a
    zero exit code."""
    bat = os.path.join(HERE, name)
    if not os.path.exists(bat):
        return False
    env = dict(os.environ)
    if extra_env:
        env.update(extra_env)
    try:
        return subprocess.run(["cmd", "/c", bat, "--bundled"], cwd=HERE,
                              env=env).returncode == 0
    except OSError:
        return False


def do_install(root):
    kid = ask_child_name(root)
    if not kid:
        return False
    root.destroy()
    ok = run_batch("install.bat", {"LG_KID": kid})
    if not ok:
        fail_early("The install did not finish. Read the messages in the "
                   "install window, fix the problem and run this again.")
    return ok


def do_uninstall(root):
    # Notify
    if not messagebox.askyesno(
            "LeafyGreen", "Remove LeafyGreen from this computer?\n\nThe "
            "child's apps and time limits will no longer be controlled.",
            icon="warning", default="no", parent=root):
        return
    # Notify
    purge = messagebox.askyesno(
        "LeafyGreen", "Also delete the saved settings and PIN?",
        default="no", parent=root)
    ok = run_batch("uninstall.bat", {"LG_PURGE": "y" if purge else "n"})
    if ok:
        # Notify
        messagebox.showinfo("LeafyGreen", "LeafyGreen has been removed.",
                            parent=root)
    else:
        # Notify
        messagebox.showerror("LeafyGreen", "The uninstall did not finish. "
                             "Try running uninstall.bat as administrator.",
                             parent=root)


def run_wizard(require_gate):
    app = SetupApp()
    if require_gate:
        app.after(150, app.gate)
    app.mainloop()


def main():
    if sys.platform == "win32" and not is_admin():
        if not elevate():
            fail_early("LeafyGreen needs administrator rights. Right-click "
                       "setup.py and choose 'Run as administrator'.")
        return

    if sys.platform == "win32" and not is_installed():
        root = _mini_root()
        if do_install(root):
            run_wizard(require_gate=False)
        return

    backend = Backend()
    if backend.setup_done():
        root = _mini_root()
        action = choose_action(root)
        if action == "uninstall":
            do_uninstall(root)
            root.destroy()
            return
        root.destroy()
        if action == "redo":
            run_wizard(require_gate=True)
        return

    run_wizard(require_gate=False)


if __name__ == "__main__":
    main()
