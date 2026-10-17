"""LeafyGreen - parental control software.

Working: app blocking, website blocking (with SmartSafe automatic checks),
Pause Internet, time-limit and bedtime locking, settings saved to disk, PIN
protection and up to four Web Dashboard accounts (Lite, Complete or Child). Pause Internet, website blocking and the locks need
administrator rights (install.bat runs the app as SYSTEM so it has them).
Website blocking works by domain name (hosts file), so a VPN, a different
DNS setting in the browser, or another spelling of a site can get around it.

Web Dashboard: open http://<this PC's IP>:8765 on the same network and sign
in with a username and password (made on the My Account tab). The
address is shown in the window header. Pause Internet turns this computer's
network off, so the Web Dashboard is unreachable until it is resumed from
the LeafyGreen window.

Run:      python leafygreen.py
Install:  right-click install.bat > Run as administrator. It builds the exe, puts
          it in Program Files and runs it as a protected background task.
"""

import collections
import ctypes
import datetime
import hashlib
import json
import math
import os
import queue
import random
import re
import secrets
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import tkinter as tk
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from tkinter import messagebox, ttk

APP_NAME = "LeafyGreen"
APP_SUBTITLE = "Parental Controls"
APP_VERSION = "v2.3 (release)"

UNLOCK_SECONDS = 300
MAX_TRIES = 5
LOCKOUT_SECONDS = 30
GUARD_INTERVAL_MS = 250
ACTIVE_WITHIN_SECONDS = 120
COUNTER_SAVE_SECONDS = 60
WEB_ENABLED = True
WEB_PORT = 8765
LOG_LIMIT = 1000
GRACE_MINUTES_PER_DAY = 3
EXPIRY_GRACE_DAYS = 5
COUNTDOWN_SECONDS = 60
NOTICE_IDLE_SECONDS = 45
MAX_PENDING_REQUESTS = 10
REQUEST_KEEP = 60

FONT = "Segoe UI"

OLIVE = "#1b4d36"
OLIVE_DARK = "#12382a"
LIME = "#1f8a5b"
LIME_DARK = "#17704a"
MINT = "#f2f6f3"
NAVY = OLIVE
NAVY_DARK = OLIVE_DARK
ACCENT = LIME
ACCENT_FG = "#ffffff"
ACCENT_LIGHT = "#6fc79c"
BG = MINT
BORDER = "#d3dfd8"
BLUE_BG = "#ffffff"
BUTTON_HOVER = "#e7f1eb"
TEXT = "#1d2b24"
MUTED = "#617268"
GREEN = "#1a7a4a"
GREEN_BG = "#e3f3ea"
RED = "#b3261e"
RED_DARK = "#8c1d18"
RED_BG = "#fbeaea"
AMBER_TEXT = "#8a5a00"
AMBER_BG = "#fff4e0"


def apply_style(root):
    s = ttk.Style(root)
    s.theme_use("clam")

    s.configure(".", font=(FONT, 10), background=BG, foreground=TEXT,
                bordercolor=BORDER, lightcolor=BG, darkcolor=BG,
                troughcolor=BG)

    s.configure("TFrame", background=BG)
    s.configure("Header.TFrame", background=NAVY)
    s.configure("Card.TFrame", background="white", relief="solid",
                borderwidth=1, bordercolor=BORDER, lightcolor=BORDER,
                darkcolor=BORDER)
    s.configure("Inner.TFrame", background="white")

    s.configure("TLabel", background=BG, foreground=TEXT)
    s.configure("Title.TLabel", background=NAVY, foreground="white",
                font=(FONT, 20, "bold"))
    s.configure("HeaderSub.TLabel", background=NAVY, foreground="#cfe6d9",
                font=(FONT, 10))
    s.configure("H1.TLabel", font=(FONT, 16, "bold"), foreground=NAVY_DARK)
    s.configure("H2.TLabel", background="white", font=(FONT, 11, "bold"),
                foreground=NAVY)
    s.configure("Muted.TLabel", foreground=MUTED)
    s.configure("CardNum.TLabel", background="white",
                font=(FONT, 26, "bold"), foreground=NAVY_DARK)
    s.configure("CardText.TLabel", background="white", foreground=MUTED)
    s.configure("CardBody.TLabel", background="white", foreground=TEXT)
    s.configure("Active.TLabel", background="white", foreground=GREEN,
                font=(FONT, 10, "bold"))
    s.configure("Status.TLabel", background="white", foreground=MUTED,
                padding=(14, 6))

    s.configure("TButton", padding=(14, 6), background=BLUE_BG,
                foreground=NAVY, bordercolor=BORDER, focusthickness=0,
                relief="flat")
    s.map("TButton",
          background=[("disabled", "#eef1ef"), ("active", BUTTON_HOVER)],
          foreground=[("disabled", "#999999")])
    s.configure("Accent.TButton", background=ACCENT, foreground=ACCENT_FG,
                bordercolor=OLIVE)
    s.map("Accent.TButton",
          background=[("active", LIME_DARK), ("pressed", LIME_DARK)],
          foreground=[("active", ACCENT_FG)])
    s.configure("Danger.TButton", background=RED, foreground="white",
                bordercolor=RED)
    s.map("Danger.TButton",
          background=[("active", RED_DARK), ("pressed", RED_DARK)],
          foreground=[("active", "white")])

    s.configure("TCheckbutton", background=BG, indicatorbackground="white")
    s.map("TCheckbutton", background=[("active", BG)])
    s.configure("Card.TRadiobutton", background="white")
    s.map("Card.TRadiobutton", background=[("active", "white")])
    s.configure("TRadiobutton", background=BG)
    s.map("TRadiobutton", background=[("active", BG)])
    s.configure("Icon.TButton", padding=(6, 1), font=(FONT, 12))
    s.configure("Card.TCheckbutton", background="white",
                indicatorbackground="white")
    s.map("Card.TCheckbutton", background=[("active", "white")])

    s.configure("TEntry", fieldbackground="white", padding=5,
                bordercolor=BORDER)
    s.configure("TCombobox", fieldbackground="white", padding=4,
                arrowcolor=NAVY, bordercolor=BORDER)
    s.map("TCombobox", fieldbackground=[("readonly", "white")])
    s.configure("TSpinbox", fieldbackground="white", padding=4,
                arrowcolor=NAVY, bordercolor=BORDER)

    s.configure("TNotebook", background=BG, borderwidth=0,
                tabmargins=(0, 4, 0, 0))
    s.configure("TNotebook.Tab", padding=(18, 8), background="#e3ebe6",
                foreground=NAVY_DARK, font=(FONT, 10, "bold"))
    s.map("TNotebook.Tab",
          background=[("selected", "white"), ("active", "#d3e6da")],
          foreground=[("selected", NAVY_DARK)],
          expand=[("selected", (0, 0, 0, 2))])

    s.configure("Treeview", background="white", fieldbackground="white",
                foreground=TEXT, rowheight=28, bordercolor=BORDER,
                borderwidth=1, font=(FONT, 10))
    s.map("Treeview",
          background=[("selected", ACCENT)],
          foreground=[("selected", ACCENT_FG)])
    s.configure("Treeview.Heading", background=NAVY, foreground="white",
                font=(FONT, 10, "bold"), padding=(8, 6), relief="flat")
    s.map("Treeview.Heading", background=[("active", NAVY_DARK)])

    s.configure("Vertical.TScrollbar", background=BORDER, troughcolor=BG,
                bordercolor=BG, arrowcolor=NAVY)


CHILD_USER = None


DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday",
        "Sunday"]
WEEKDAYS = DAYS[:5]
TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
RESULT_TAGS = {"Blocked": "blocked", "Allowed": "allowed",
               "Limited": "warn", "Failed": "warn"}


def fmt_minutes(m):
    h, mm = divmod(int(m), 60)
    return f"{h}h {mm:02d}m" if h else f"{mm}m"


def today_str():
    return datetime.date.today().isoformat()


def activation_keyfile_path():
    """Where the plain-text record of activation keys and their end dates
    lives, in the child's own folder (e.g.
    C:\\Users\\Child\\leafygreen\\activation_keys.txt). The app runs as
    SYSTEM, so the child's home is resolved from CHILD_USER rather than ~."""
    return os.path.join(child_home(), "leafygreen", "activation_keys.txt")


def write_activation_keyfile(key_log):
    """Write the human-readable record of every activated key and when it
    expires. Best effort: a failure here never stops activation."""
    path = activation_keyfile_path()
    lines = ["LeafyGreen - activation keys", "=" * 36, ""]
    if not key_log:
        lines.append("No activation key recorded yet.")
    for rec in key_log:
        lines.append(f"Activation key : {rec.get('key', '')}")
        lines.append(f"Expires on     : {rec.get('expiry') or '(no end date)'}")
        lines.append(f"Recorded       : {rec.get('recorded', '')}")
        lines.append("")
    lines.append("Renew with a new key and activate it on the My Account tab "
                 "in the LeafyGreen window.")
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    except OSError:
        pass
    return path


def split_stamp(stamp):
    """('2026-10-05', '17:11:02') from a log time. Lines written by older
    versions have only the time, so their date is ''."""
    if (len(stamp) >= 19 and stamp[4] == "-" and stamp[7] == "-"
            and stamp[10] == " "):
        return stamp[:10], stamp[11:19]
    return "", stamp


def short_stamp(stamp, today=None):
    """Time of day for today's lines, 'MM-DD HH:MM' for older days."""
    date, clock = split_stamp(stamp)
    if not date or date == (today or today_str()):
        return clock
    return f"{date[5:]} {clock[:5]}"


LOG_SORTS = ("Newest first", "Oldest first", "By day", "By hour of day")


def log_rows(activity):
    """Log lines as dictionaries (i = position in the stored log, which is
    newest first)."""
    rows = []
    for i, (stamp, event, target, result) in enumerate(activity):
        date, clock = split_stamp(stamp)
        try:
            hour = int(clock[:2])
        except ValueError:
            hour = None
        rows.append({"i": i, "date": date, "time": clock, "hour": hour,
                     "event": event, "target": target, "result": result})
    return rows


def filter_log(rows, day=None, hour=None, result=None, text=""):
    """day: None = all days, else a date like '2026-10-05' ('' = lines with
    no date). hour: None = all, else 0-23. result: None = all."""
    text = text.strip().lower()
    out = []
    for r in rows:
        if day is not None and r["date"] != day:
            continue
        if hour is not None and r["hour"] != hour:
            continue
        if result is not None and r["result"] != result:
            continue
        if text and text not in " ".join(
                (r["event"], r["target"], r["result"])).lower():
            continue
        out.append(r)
    return out


def sort_log(rows, mode):
    """Newest first (as stored), Oldest first, By day (newest day first, and
    newest first inside each day) or By hour of day (00 to 23, across all
    days)."""
    if mode == "Oldest first":
        return list(reversed(rows))
    if mode == "By day":
        return sorted(rows, key=lambda r: r["date"], reverse=True)
    if mode == "By hour of day":
        return sorted(rows, key=lambda r: 99 if r["hour"] is None
                      else r["hour"])
    return list(rows)


def sort_tree(tree, col, reverse):
    """Sort a Treeview by a column; numbers sort numerically. The choice is
    remembered, so a refresh keeps the same order."""
    tree._sort_state = (col, reverse)
    items = [(tree.set(k, col), k) for k in tree.get_children("")]

    def key(item):
        text = item[0]
        try:
            return (0, float(text))
        except ValueError:
            return (1, text.lower())

    items.sort(key=key, reverse=reverse)
    for index, (_, k) in enumerate(items):
        tree.move(k, "", index)
    tree.heading(col, command=lambda: sort_tree(tree, col, not reverse))


def rebuild_tree(tree, rows):
    """Replace a table's rows, keeping the sort order and the selection.

    rows: list of (iid, values, tags). A row stays selected only if the same
    row (same values) is still in the table, so removing or moving a row
    never selects the one that slid into its place."""
    def ident(values):
        return tuple(str(v) for v in values)

    selected = {ident(tree.item(i, "values")) for i in tree.selection()}
    tree.delete(*tree.get_children())
    keep = []
    for iid, values, tags in rows:
        tree.insert("", "end", iid=iid, values=values, tags=tags)
        if selected and ident(values) in selected:
            keep.append(iid)
    state = getattr(tree, "_sort_state", None)
    if state:
        sort_tree(tree, *state)
    if keep:
        tree.selection_set(keep)


def normalize_app_name(name):
    """'C:\\Games\\Game' -> 'Game.exe'."""
    name = name.strip().strip('"').replace("/", "\\").split("\\")[-1].strip()
    if name and not name.lower().endswith(".exe"):
        name += ".exe"
    return name


_SITE_LABEL = re.compile(r"^(?!-)[a-z0-9-]{1,63}(?<!-)$")


def normalize_site_name(text):
    """'https://WWW.Example.com/a?b=1' -> 'example.com'.

    Returns None unless the text is a plausible website name (letters,
    digits and hyphens, at least one dot, a real-looking ending), so
    nothing odd can end up in the hosts file."""
    t = str(text).strip().lower()
    if not t or any(ch.isspace() or ord(ch) < 32 for ch in t):
        return None
    t = re.sub(r"^[a-z][a-z0-9+.-]*://", "", t)
    t = re.split(r"[/?#]", t, maxsplit=1)[0]
    t = t.rsplit("@", 1)[-1]
    t = re.sub(r":\d+$", "", t)
    t = t.strip(".")
    if t.startswith("www."):
        t = t[4:]
    if len(t) > 253 or "." not in t:
        return None
    labels = t.split(".")
    if not all(_SITE_LABEL.match(label) for label in labels):
        return None
    tld = labels[-1]
    if not (tld.startswith("xn--") or (tld.isalpha() and len(tld) >= 2)):
        return None
    return t


def make_tree(parent, columns, height=10):
    """Treeview with scrollbar, sortable headings and row tags.

    columns: list of (column id, heading text, width, anchor)
    Returns (container frame, tree).
    """
    wrap = ttk.Frame(parent)
    tree = ttk.Treeview(wrap, columns=[c[0] for c in columns],
                        show="headings", height=height,
                        selectmode="extended")
    vsb = ttk.Scrollbar(wrap, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    for cid, head, width, anchor in columns:
        tree.heading(cid, text=head,
                     command=lambda c=cid: sort_tree(tree, c, False))
        tree.column(cid, width=width, anchor=anchor, stretch=True)
    tree.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    wrap.rowconfigure(0, weight=1)
    wrap.columnconfigure(0, weight=1)
    tree.tag_configure("blocked", background=RED_BG, foreground=RED)
    tree.tag_configure("allowed", background=GREEN_BG, foreground=GREEN)
    tree.tag_configure("warn", background=AMBER_BG, foreground=AMBER_TEXT)
    tree.tag_configure("muted", foreground="#8a968f")
    enable_drag_select(tree)
    return wrap, tree


def rows_between(children, first, last):
    """The rows from `first` to `last` (either order) in display order."""
    a, b = children.index(first), children.index(last)
    return children[min(a, b):max(a, b) + 1]


def enable_drag_select(tree):
    """Click and drag over rows to select several at once. Shift-click,
    Ctrl-click and Ctrl+A keep working as usual."""
    state = {"anchor": None}

    def press(event):
        on_row = tree.identify_region(event.x, event.y) in ("cell", "tree")
        plain = not (event.state & 0x0005)
        state["anchor"] = tree.identify_row(event.y) if on_row and plain \
            else None

    def drag(event):
        if not state["anchor"]:
            return None
        y, height = event.y, tree.winfo_height()
        if y < 0:
            tree.yview_scroll(-1, "units")
            y = 1
        elif y > height:
            tree.yview_scroll(1, "units")
            y = height - 1
        row = tree.identify_row(y)
        if row:
            tree.selection_set(rows_between(
                list(tree.get_children()), state["anchor"], row))
        return "break"

    def select_all(_event):
        tree.selection_set(tree.get_children())
        return "break"

    tree.bind("<ButtonPress-1>", press, add="+")
    tree.bind("<B1-Motion>", drag)
    tree.bind("<Control-a>", select_all)
    tree.bind("<Control-A>", select_all)


def default_limits():
    return {d: {"enabled": True, "minutes": 120 if d in WEEKDAYS else 180}
            for d in DAYS}


ALERT_CHOICES = (1, 2, 3, 5, 10, 15, 20, 30)
MAX_ALERTS = 3
DEFAULT_ALERTS = [10]


def clean_alerts(values):
    """A sensible alert list: whole minutes from ALERT_CHOICES, no repeats,
    at most MAX_ALERTS, largest first."""
    out = []
    for v in values if isinstance(values, (list, tuple)) else []:
        if isinstance(v, bool):
            continue
        try:
            minutes = int(v)
        except (TypeError, ValueError):
            continue
        if minutes in ALERT_CHOICES and minutes not in out:
            out.append(minutes)
    return sorted(out[:MAX_ALERTS], reverse=True)


def alert_label(minutes):
    return "1 minute" if minutes == 1 else f"{minutes} minutes"


def describe_alerts(alerts):
    if not alerts:
        return "Alerts are off."
    names = [str(m) for m in alerts]
    text = (names[0] if len(names) == 1
            else ", ".join(names[:-1]) + " and " + names[-1])
    return f"Alerts at {text} minute(s) before time runs out."

QUICK_CHOICES = (("pause", "Pause Internet"), ("coupon", "Add New Coupon"),
                 ("requests", "Review Requests"))
DEFAULT_QUICK = [key for key, _ in QUICK_CHOICES]
ROLES = ("Lite", "Complete", "Child")
ROLE_HELP = {
    "Lite": "Can review requests (approve or deny) and make new coupons.",
    "Complete": "Can change any setting.",
    "Child": "Can look at all the settings and send requests.",
}
REQUEST_KINDS = {"time": "More screen time", "app": "Unblock an app",
                 "site": "Unblock a website"}
TIME_REQUEST_CHOICES = (15, 30, 60, 120)
PAUSE_CHOICES = (("15 minutes", 15), ("30 minutes", 30), ("1 hour", 60),
                 ("2 hours", 120), ("4 hours", 240),
                 ("Until I turn it back on", 0))



def _settings_dir():
    """C:\\ProgramData\\LeafyGreen on Windows (install.bat locks it so only
    administrators and the SYSTEM account can read or change it). Set the
    LEAFYGREEN_DATA_DIR environment variable to use a different folder."""
    override = (os.environ.get("LEAFYGREEN_DATA_DIR")
                or os.environ.get("SNORT_DATA_DIR"))
    if override:
        return override
    if sys.platform == "win32" and os.environ.get("PROGRAMDATA"):
        return os.path.join(os.environ["PROGRAMDATA"], "LeafyGreen")
    return os.path.join(
        os.environ.get("APPDATA") or os.path.expanduser("~"), "LeafyGreen")


SETTINGS_DIR = _settings_dir()
SETTINGS_FILE = os.path.join(SETTINGS_DIR, "settings.json")

SAVE_FIELDS = ("pin_salt", "pin_hash", "protection_enabled", "limits",
               "bedtime", "warn_alerts", "blocked", "allowed", "limited",
               "coupons", "activity", "bonus_min", "used_today_sec",
               "usage_date", "baseline_done", "hidden", "parents",
               "pin_plain", "requests", "grace_used",
               "smart_denied", "smart_approved", "smartsafe_enabled",
               "setup_done", "expiry", "expiry_warn_days", "key_log")


class Data:
    def __init__(self):
        self.pin_salt = os.urandom(8).hex()
        self.pin_hash = None
        self.pin_plain = None
        self.parents = []
        self.protection_enabled = True
        self.internet_paused = False
        self.pause_until = 0.0
        self.grace_used = 0
        self.quick_actions = list(DEFAULT_QUICK)
        self.requests = []
        self.bonus_min = 0
        self.used_today_sec = 0.0
        self.usage_date = ""
        self.baseline_done = False

        self.limits = default_limits()
        self.bedtime = {"enabled": True, "start": "21:00", "end": "07:00"}
        self.warn_alerts = list(DEFAULT_ALERTS)

        self.blocked = []
        self.allowed = []
        self.smart_denied = []
        self.smart_approved = []
        self.smartsafe_enabled = True
        self.setup_done = False
        self.expiry = ""
        self.expiry_warn_days = 14
        self.key_log = []
        self.hidden = []
        self.limited = []
        self.coupons = []
        self.activity = []
        self.load_error = None
        self.unreadable = None

    @property
    def used_today_min(self):
        return int(self.used_today_sec // 60)

    def days_left(self, today=None):
        """Whole days until the subscription expires, or None if no end date
        is set. 0 on the last day; negative once it has expired."""
        if not self.expiry:
            return None
        try:
            end = datetime.date.fromisoformat(self.expiry)
        except ValueError:
            return None
        return (end - (today or datetime.date.today())).days

    @property
    def expired(self):
        """True once the end date has passed (the day after it)."""
        left = self.days_left()
        return left is not None and left < 0

    @property
    def settings_locked(self):
        """Once expired, no setting can be changed until a new key is
        activated. (The key list and activation are the only exceptions.)"""
        return self.expired

    @property
    def protection_effective(self):
        """What protection actually does right now. Protection stays on
        through the end date and for EXPIRY_GRACE_DAYS after it, then stops
        for good. The parent's on/off switch still applies throughout."""
        if not self.protection_enabled:
            return False
        left = self.days_left()
        return left is None or left >= -EXPIRY_GRACE_DAYS

    def grace_days_left(self):
        """Days of the post-expiry grace period still to come (protection
        turns off once this reaches zero), or None when not expired."""
        left = self.days_left()
        if left is None or left >= 0:
            return None
        return EXPIRY_GRACE_DAYS + 1 + left

    @staticmethod
    def _key_norm(key):
        return str(key or "").strip().upper()

    @staticmethod
    def _expiry_ok(expiry, today=None):
        """True if this end date is empty (no end date) or still in future."""
        if not expiry:
            return True
        try:
            return datetime.date.fromisoformat(expiry) >= \
                (today or datetime.date.today())
        except ValueError:
            return False

    def key_entry(self, key):
        """The matching entry in the key list, or None."""
        norm = self._key_norm(key)
        for e in self.key_log:
            if self._key_norm(e.get("key")) == norm:
                return e
        return None

    def validate_activation(self, key):
        """Decide whether `key` may be used to activate. Returns
        (ok, expiry, error). A key counts if it is in the key list and not
        past its end date; the built-in key always works as a fallback."""
        entry = self.key_entry(key)
        if entry is not None:
            if self._expiry_ok(entry.get("expiry", "")):
                return True, str(entry.get("expiry", "")), None
            return False, None, "That key is in the list but has expired."
        if activation_key_ok(key):
            return True, "", None
        return False, None, "That key is not in the key list."

    def activate(self, key):
        """Turn the subscription on with `key`. Returns (ok, error). On
        success the end date becomes that key's end date and the record file
        is refreshed."""
        ok, expiry, error = self.validate_activation(key)
        if not ok:
            return False, error
        if self.key_entry(key) is None:
            self.key_log.append({"key": self._key_norm(key), "expiry": expiry,
                                  "recorded": today_str()})
            self.key_log = self.key_log[-50:]
        self.expiry = expiry
        write_activation_keyfile(self.key_log)
        return True, None

    def set_key_list(self, entries):
        """Replace the key list (from the Ctrl+Shift+A manager) and refresh
        the record file. `entries` is a list of {"key", "expiry"}."""
        clean = []
        seen = set()
        for e in entries:
            key = self._key_norm(e.get("key"))
            if not key or key in seen:
                continue
            seen.add(key)
            clean.append({"key": key, "expiry": str(e.get("expiry", "")),
                          "recorded": str(e.get("recorded") or today_str())})
        self.key_log = clean[-50:]
        write_activation_keyfile(self.key_log)

    def _hash(self, pin):
        return hashlib.sha256((self.pin_salt + pin).encode()).hexdigest()

    def set_pin(self, pin):
        self.pin_hash = self._hash(pin)
        self.pin_plain = pin

    def check_pin(self, pin):
        ok = self.pin_hash is not None and self._hash(pin) == self.pin_hash
        if ok and self.pin_plain is None:
            self.pin_plain = pin
        return ok

    MAX_PARENTS = 4

    @staticmethod
    def _pw_hash(salt, password):
        return hashlib.sha256((salt + password).encode()).hexdigest()

    def _find_parent(self, username):
        key = username.strip().lower()
        return next((p for p in self.parents
                     if p["username"].lower() == key), None)

    def add_parent(self, username, password, role="Complete"):
        """Returns False if the name is taken, the role is unknown or four
        accounts already exist."""
        username = username.strip()
        if (not username or role not in ROLES or self._find_parent(username)
                or len(self.parents) >= self.MAX_PARENTS):
            return False
        salt = os.urandom(8).hex()
        self.parents.append({"username": username, "pass_salt": salt,
                             "pass_hash": self._pw_hash(salt, password),
                             "added": today_str(), "role": role})
        return True

    def parent_role(self, username):
        """'Lite', 'Complete' or 'Child' (None if there is no such account)."""
        p = self._find_parent(username)
        return None if p is None else p.get("role", "Complete")

    def set_parent_role(self, username, role):
        p = self._find_parent(username)
        if p is None or role not in ROLES:
            return False
        p["role"] = role
        return True

    def check_parent(self, username, password):
        p = self._find_parent(username)
        return p is not None and \
            self._pw_hash(p["pass_salt"], password) == p["pass_hash"]

    def set_parent_password(self, username, password):
        p = self._find_parent(username)
        if p is None:
            return False
        p["pass_salt"] = os.urandom(8).hex()
        p["pass_hash"] = self._pw_hash(p["pass_salt"], password)
        return True

    def remove_parent(self, username):
        p = self._find_parent(username)
        if p is not None:
            self.parents.remove(p)

    def pending_requests(self):
        return [r for r in self.requests if r["status"] == "Pending"]

    def new_request(self, kind, detail="", minutes=0, note=""):
        """A child asks for something. Returns (True, message) or
        (False, reason)."""
        if kind not in REQUEST_KINDS:
            return False, "Choose what you are asking for."
        detail = str(detail).strip()
        if kind == "app":
            detail = normalize_app_name(detail)
            if not detail:
                return False, "Type the name of the app."
        elif kind == "site":
            site = normalize_site_name(detail)
            if site is None:
                return False, ("Type the website as a full address, such "
                               "as example.com.")
            detail = site
        else:
            detail = ""
            if minutes not in TIME_REQUEST_CHOICES:
                return False, "Choose how much time you are asking for."
        if kind != "time":
            minutes = 0
        pending = self.pending_requests()
        if len(pending) >= MAX_PENDING_REQUESTS:
            return False, ("There are already several requests waiting. "
                           "Wait for a parent to answer them first.")
        if any(r["kind"] == kind and r["detail"].lower() == detail.lower()
               and (kind != "time" or r["minutes"] == minutes)
               for r in pending):
            return False, "You already asked for that. A parent will see it."
        self.requests.insert(0, {
            "id": os.urandom(4).hex(), "kind": kind, "detail": detail,
            "minutes": int(minutes), "note": str(note).strip()[:120],
            "created": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "status": "Pending", "told": False})
        self.log("Request sent", self.describe_request(self.requests[0]))
        self._trim_requests()
        return True, "Your request was sent to a parent."

    @staticmethod
    def describe_request(r):
        if r["kind"] == "time":
            return f"{r['minutes']} more minutes of screen time"
        return f"Unblock {r['detail']}"

    def _trim_requests(self):
        """Keeps all waiting requests and the newest finished ones."""
        keep, finished = [], 0
        for r in self.requests:
            if r["status"] == "Pending" or not r["told"]:
                keep.append(r)
            elif finished < REQUEST_KEEP:
                finished += 1
                keep.append(r)
        self.requests = keep

    def review_request(self, req_id, approve):
        """Approve or deny a waiting request. Returns a message, or None if
        the request is gone or was already answered."""
        r = next((x for x in self.requests
                  if x["id"] == req_id and x["status"] == "Pending"), None)
        if r is None:
            return None
        r["status"] = "Approved" if approve else "Denied"
        r["told"] = False
        what = self.describe_request(r)
        if approve:
            if r["kind"] == "time":
                self.bonus_min += r["minutes"]
            else:
                kind = "App" if r["kind"] == "app" else "Website"
                low = r["detail"].lower()
                self.blocked = [b for b in self.blocked
                                if not (b[0].lower() == low and b[1] == kind)]
                if not any(a[0].lower() == low for a in self.allowed):
                    self.allowed.append([r["detail"], kind, today_str()])
        self.log("Request " + ("approved" if approve else "denied"), what,
                 "Allowed" if approve else "Blocked")
        return f"{'Approved' if approve else 'Denied'}: {what}."

    def new_coupon_code(self):
        alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
        existing = {c["code"] for c in self.coupons}
        while True:
            code = "LEAFY-{}-{}".format(
                "".join(random.choices(alphabet, k=4)),
                "".join(random.choices(alphabet, k=4)))
            if code not in existing:
                return code

    def add_coupon(self, minutes, note=""):
        """Creates an unused coupon and returns its code."""
        code = self.new_coupon_code()
        self.coupons.insert(0, {"code": code, "minutes": int(minutes),
                                "note": str(note).strip()[:60],
                                "created": today_str(), "status": "Unused"})
        self.log("Coupon created", f"{code} (+{int(minutes)} min)")
        return code

    def unused_coupons(self):
        return [c for c in self.coupons if c["status"] == "Unused"]

    def redeem_coupon(self, code):
        """Uses a coupon: its minutes become bonus time. Returns the minutes,
        or None if there is no such unused coupon."""
        c = next((x for x in self.coupons
                  if x["code"] == code and x["status"] == "Unused"), None)
        if c is None:
            return None
        c["status"] = "Redeemed"
        self.bonus_min += c["minutes"]
        self.log("Coupon redeemed", f"{code} (+{c['minutes']} min)")
        return c["minutes"]

    def untold_results(self):
        return [r for r in reversed(self.requests)
                if r["status"] != "Pending" and not r["told"]]

    def pause_expired(self, now_epoch):
        """True (once) when a timed Pause Internet has run out."""
        if (self.internet_paused and self.pause_until
                and now_epoch >= self.pause_until):
            self.internet_paused = False
            self.pause_until = 0.0
            return True
        return False

    def _log_is_hidden(self, target):
        """True if a log line is about an app or website that is hidden.
        Catches "Game.exe", "Game.exe (30 min)", "Unblock Game.exe" and
        lists such as "Game.exe, Other.exe" (any hidden name in the line)."""
        if not self.hidden:
            return False
        hidden = set(self.hidden)
        text = str(target).strip().lower()
        main = text.split(" (")[0].strip()
        names = {main}
        if main.startswith("unblock "):
            names.add(main[8:].strip())
        names.update(p.strip() for p in re.split(r"[,;]", main) if p.strip())
        return bool(names & hidden)

    def purge_hidden_log(self):
        """Removes log lines about hidden apps and websites."""
        self.activity[:] = [a for a in self.activity
                            if not self._log_is_hidden(a[2])]

    def visible_activity(self):
        """The log without anything about a hidden app or website. Every
        screen that shows the log uses this."""
        return [a for a in self.activity if not self._log_is_hidden(a[2])]

    def log(self, event, target, result="Info"):
        if self._log_is_hidden(target):
            return
        stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.activity.insert(0, (stamp, event, target, result))
        del self.activity[LOG_LIMIT:]

    def roll_day(self):
        """Start fresh usage numbers when the date changes."""
        today = today_str()
        if self.usage_date != today:
            self.usage_date = today
            self.used_today_sec = 0.0
            self.bonus_min = 0
            self.grace_used = 0
            for entry in self.limited:
                entry["used_sec"] = 0.0

    def reset_time_settings(self):
        self.limits = default_limits()
        self.bedtime = {"enabled": True, "start": "21:00", "end": "07:00"}
        self.warn_alerts = list(DEFAULT_ALERTS)

    def prune_hidden(self):
        """Forget hidden names that are no longer in Always Allowed."""
        names = {r[0].lower() for r in self.allowed}
        self.hidden = [h for h in dict.fromkeys(self.hidden) if h in names]

    def to_dict(self):
        out = {k: getattr(self, k) for k in SAVE_FIELDS}
        out["used_today_sec"] = round(self.used_today_sec, 1)
        out["limited"] = [dict(e, used_sec=round(e.get("used_sec", 0.0), 1))
                          for e in self.limited]
        out["activity"] = [list(a) for a in self.activity]
        return out

    @staticmethod
    def write(text, path=SETTINGS_FILE):
        """Write the settings file safely. Returns an error message or None."""
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(text)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, path)
        except OSError as exc:
            return str(exc)
        return None

    @classmethod
    def load(cls, path=SETTINGS_FILE):
        data = cls()
        try:
            with open(path, encoding="utf-8") as f:
                raw = json.load(f)
            if not isinstance(raw, dict):
                raise ValueError("unexpected file contents")
        except FileNotFoundError:
            raw = None
        except ValueError as exc:
            raw = None
            data.load_error = str(exc)
            try:
                os.replace(path, path + ".corrupt")
            except OSError:
                pass
        except OSError as exc:
            raw = None
            data.unreadable = str(exc)
        if raw is not None:
            data._apply(raw)
        data.roll_day()
        return data

    def _apply(self, raw):
        for key in SAVE_FIELDS:
            if key not in raw:
                continue
            value, default = raw[key], getattr(self, key)
            if key in ("pin_hash", "pin_plain"):
                if value is None or isinstance(value, str):
                    setattr(self, key, value)
            elif isinstance(default, bool):
                if isinstance(value, bool):
                    setattr(self, key, value)
            elif isinstance(default, (int, float)):
                if isinstance(value, (int, float)) \
                        and not isinstance(value, bool):
                    setattr(self, key, type(default)(value))
            elif isinstance(value, type(default)):
                setattr(self, key, value)
        if "warn_alerts" not in raw and isinstance(raw.get("warn_before"),
                                                    str):
            try:
                self.warn_alerts = [int(raw["warn_before"].split()[0])]
            except (ValueError, IndexError):
                pass
        self._clean()

    def _clean(self):
        """Drop anything in a loaded file that is not the expected shape."""
        defaults = default_limits()
        limits = {}
        for day in DAYS:
            e = self.limits.get(day)
            ok = (isinstance(e, dict)
                  and isinstance(e.get("enabled"), bool)
                  and isinstance(e.get("minutes"), int)
                  and 0 <= e["minutes"] <= 1440)
            limits[day] = ({"enabled": e["enabled"], "minutes": e["minutes"]}
                           if ok else defaults[day])
        self.limits = limits

        b = self.bedtime
        if not (isinstance(b, dict) and isinstance(b.get("enabled"), bool)
                and TIME_RE.match(str(b.get("start", "")))
                and TIME_RE.match(str(b.get("end", "")))):
            self.bedtime = {"enabled": True, "start": "21:00",
                            "end": "07:00"}
        self.warn_alerts = clean_alerts(self.warn_alerts)

        if not isinstance(self.expiry, str):
            self.expiry = ""
        if self.expiry:
            try:
                datetime.date.fromisoformat(self.expiry)
            except ValueError:
                self.expiry = ""
        try:
            self.expiry_warn_days = min(60, max(1, int(self.expiry_warn_days)))
        except (TypeError, ValueError):
            self.expiry_warn_days = 14
        self.key_log = [
            {"key": str(r.get("key", "")),
             "expiry": str(r.get("expiry", "")),
             "recorded": str(r.get("recorded", ""))}
            for r in self.key_log
            if isinstance(r, dict)][-20:]

        def rows(items):
            return [list(r) for r in items
                    if isinstance(r, (list, tuple)) and len(r) == 3
                    and all(isinstance(x, str) for x in r)
                    and r[1] in ("App", "Website")]

        self.blocked = rows(self.blocked)
        self.allowed = rows(self.allowed)
        self.smart_denied = [r for r in rows(self.smart_denied)
                             if r[1] == "Website"][-SMART_DENIED_MAX:]
        self.smart_approved = [r for r in rows(self.smart_approved)
                               if r[1] == "Website"][-SMART_APPROVED_MAX:]
        self.blocked = [r for r in self.blocked
                        if not (r[1] == "App"
                                and r[0].lower() in PROTECTED_APP_NAMES)]
        self.limited = [e for e in self.limited
                        if e["name"].lower() not in PROTECTED_APP_NAMES]
        self.hidden = [h for h in self.hidden if isinstance(h, str)]
        self.prune_hidden()
        if not (isinstance(self.pin_plain, str) and len(self.pin_plain) == 4
                and self.pin_plain.isdigit()):
            self.pin_plain = None
        parents, seen = [], set()
        for p in self.parents:
            if (isinstance(p, dict)
                    and all(isinstance(p.get(k), str) and p.get(k)
                            for k in ("username", "pass_salt", "pass_hash"))
                    and p["username"].lower() not in seen):
                seen.add(p["username"].lower())
                parents.append({"username": p["username"],
                                "pass_salt": p["pass_salt"],
                                "pass_hash": p["pass_hash"],
                                "added": p.get("added")
                                if isinstance(p.get("added"), str) else "",
                                "role": p.get("role") if p.get("role")
                                in ROLES else "Complete"})
        self.parents = parents[:self.MAX_PARENTS]
        self.limited = [
            {"name": e["name"], "limit": e["limit"],
             "used_sec": float(e.get("used_sec", 0))}
            for e in self.limited
            if isinstance(e, dict) and isinstance(e.get("name"), str)
            and isinstance(e.get("limit"), int) and e["limit"] > 0
            and isinstance(e.get("used_sec", 0), (int, float))]
        self.coupons = [
            c for c in self.coupons
            if isinstance(c, dict) and isinstance(c.get("code"), str)
            and isinstance(c.get("minutes"), int)
            and isinstance(c.get("note"), str)
            and isinstance(c.get("created"), str)
            and c.get("status") in ("Unused", "Redeemed")]
        self.activity = [
            tuple(a) for a in self.activity
            if isinstance(a, (list, tuple)) and len(a) == 4
            and all(isinstance(x, str) for x in a)][:LOG_LIMIT]
        self.purge_hidden_log()
        self.quick_actions = list(DEFAULT_QUICK)
        self.grace_used = max(0, min(self.grace_used, 1000))
        cleaned = []
        for r in self.requests:
            if (isinstance(r, dict)
                    and all(isinstance(r.get(k), str)
                            for k in ("id", "detail", "note", "created"))
                    and r.get("kind") in REQUEST_KINDS
                    and isinstance(r.get("minutes"), int)
                    and not isinstance(r.get("minutes"), bool)
                    and 0 <= r["minutes"] <= 1440
                    and r.get("status") in ("Pending", "Approved", "Denied")
                    and isinstance(r.get("told"), bool)):
                cleaned.append({k: r[k] for k in (
                    "id", "kind", "detail", "minutes", "note", "created",
                    "status", "told")})
        self.requests = cleaned
        self._trim_requests()


PROTECTED_APP_NAMES = frozenset({"leafygreen.exe", "snortsecure.exe"})
CRITICAL_PROCESSES = frozenset({
    "system", "registry", "smss.exe", "csrss.exe", "wininit.exe",
    "winlogon.exe", "services.exe", "lsass.exe", "lsm.exe", "svchost.exe",
    "dwm.exe", "explorer.exe", "fontdrvhost.exe", "sihost.exe",
    "taskhostw.exe", "ctfmon.exe", "audiodg.exe", "userinit.exe",
    "logonui.exe", "consent.exe", "lockapp.exe", "runtimebroker.exe",
    "searchhost.exe", "startmenuexperiencehost.exe",
    "shellexperiencehost.exe", "textinputhost.exe",
    "applicationframehost.exe", "dllhost.exe", "conhost.exe",
    "spoolsv.exe", "wmiprvse.exe", "msmpeng.exe", "nissrv.exe",
    "securityhealthsystray.exe", "securityhealthservice.exe",
})

Proc = collections.namedtuple("Proc", "pid name path session",
                              defaults=(None,))


class _ProcessEntry(ctypes.Structure):
    """PROCESSENTRY32W from the Windows API (568 bytes on 64-bit)."""
    _fields_ = [
        ("dwSize", ctypes.c_uint32),
        ("cntUsage", ctypes.c_uint32),
        ("th32ProcessID", ctypes.c_uint32),
        ("th32DefaultHeapID", ctypes.c_size_t),
        ("th32ModuleID", ctypes.c_uint32),
        ("cntThreads", ctypes.c_uint32),
        ("th32ParentProcessID", ctypes.c_uint32),
        ("pcPriClassBase", ctypes.c_int32),
        ("dwFlags", ctypes.c_uint32),
        ("szExeFile", ctypes.c_uint16 * 260),
    ]


def _exe_name(entry):
    chars = []
    for c in entry.szExeFile:
        if c == 0:
            break
        chars.append(chr(c))
    return "".join(chars)


class _Luid(ctypes.Structure):
    _fields_ = [("LowPart", ctypes.c_uint32), ("HighPart", ctypes.c_int32)]


class _TokenPrivileges(ctypes.Structure):
    """TOKEN_PRIVILEGES holding exactly one privilege (16 bytes)."""
    _fields_ = [("PrivilegeCount", ctypes.c_uint32), ("Luid", _Luid),
                ("Attributes", ctypes.c_uint32)]


class WindowsProcessApi:
    """Lists and closes programs using the Windows API (no extra installs).
    Only programs in the signed-in user's own session are seen, which
    leaves Windows services alone. Closing a program that is running with
    higher rights (started as administrator, or by another account) needs
    this app to have administrator rights too (install.bat gives it
    SYSTEM rights); without them Windows answers "access denied".
    """

    TH32CS_SNAPPROCESS = 0x2
    PROCESS_TERMINATE = 0x0001
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

    def __init__(self):
        k = ctypes.WinDLL("kernel32", use_last_error=True)
        handle = ctypes.c_void_p
        entry_ptr = ctypes.POINTER(_ProcessEntry)
        dword_ptr = ctypes.POINTER(ctypes.c_uint32)
        k.CreateToolhelp32Snapshot.argtypes = [ctypes.c_uint32,
                                               ctypes.c_uint32]
        k.CreateToolhelp32Snapshot.restype = handle
        k.Process32FirstW.argtypes = [handle, entry_ptr]
        k.Process32FirstW.restype = ctypes.c_int
        k.Process32NextW.argtypes = [handle, entry_ptr]
        k.Process32NextW.restype = ctypes.c_int
        k.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int,
                                  ctypes.c_uint32]
        k.OpenProcess.restype = handle
        k.CloseHandle.argtypes = [handle]
        k.CloseHandle.restype = ctypes.c_int
        k.QueryFullProcessImageNameW.argtypes = [
            handle, ctypes.c_uint32, ctypes.c_wchar_p, dword_ptr]
        k.QueryFullProcessImageNameW.restype = ctypes.c_int
        k.ProcessIdToSessionId.argtypes = [ctypes.c_uint32, dword_ptr]
        k.ProcessIdToSessionId.restype = ctypes.c_int
        k.TerminateProcess.argtypes = [handle, ctypes.c_uint32]
        k.TerminateProcess.restype = ctypes.c_int
        k.GetCurrentProcessId.restype = ctypes.c_uint32
        self._k = k
        self._invalid = ctypes.c_void_p(-1).value
        self._cache = {}
        self._my_session = self._session_of(k.GetCurrentProcessId())
        self.last_error = 0
        self.has_debug = self._enable_debug_privilege()

    def _enable_debug_privilege(self):
        """Turns on SeDebugPrivilege when this process is allowed to have
        it (administrator or SYSTEM). It lets us close programs that would
        otherwise refuse with "access denied". Returns True if enabled."""
        try:
            a = ctypes.WinDLL("advapi32", use_last_error=True)
            vp, k = ctypes.c_void_p, self._k
            k.GetCurrentProcess.restype = vp
            a.OpenProcessToken.argtypes = [vp, ctypes.c_uint32,
                                           ctypes.POINTER(vp)]
            a.OpenProcessToken.restype = ctypes.c_int
            a.LookupPrivilegeValueW.argtypes = [
                ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.POINTER(_Luid)]
            a.LookupPrivilegeValueW.restype = ctypes.c_int
            a.AdjustTokenPrivileges.argtypes = [
                vp, ctypes.c_int, ctypes.POINTER(_TokenPrivileges),
                ctypes.c_uint32, vp, vp]
            a.AdjustTokenPrivileges.restype = ctypes.c_int
            token = vp()
            if not a.OpenProcessToken(k.GetCurrentProcess(), 0x28,
                                      ctypes.byref(token)):
                return False
            try:
                tp = _TokenPrivileges()
                tp.PrivilegeCount = 1
                tp.Attributes = 0x2
                if not a.LookupPrivilegeValueW(None, "SeDebugPrivilege",
                                               ctypes.byref(tp.Luid)):
                    return False
                a.AdjustTokenPrivileges(token, 0, ctypes.byref(tp), 0,
                                        None, None)
                return ctypes.get_last_error() == 0
            finally:
                k.CloseHandle(token)
        except Exception:
            return False

    def _session_of(self, pid):
        session = ctypes.c_uint32()
        if self._k.ProcessIdToSessionId(pid, ctypes.byref(session)):
            return session.value
        return -1

    def _path_of(self, pid):
        h = self._k.OpenProcess(self.PROCESS_QUERY_LIMITED_INFORMATION, 0,
                                pid)
        if not h:
            return None
        try:
            buf = ctypes.create_unicode_buffer(1024)
            size = ctypes.c_uint32(len(buf))
            if self._k.QueryFullProcessImageNameW(h, 0, buf,
                                                  ctypes.byref(size)):
                return buf.value
            return None
        finally:
            self._k.CloseHandle(h)

    def _info(self, pid, name):
        """(name, path, session) for a process, remembered per PID. A lookup
        that failed is tried again next time instead of being remembered."""
        cached = self._cache.get(pid)
        if (cached is None or cached[0] != name or cached[1] is None
                or cached[2] == -1):
            cached = (name, self._path_of(pid), self._session_of(pid))
            self._cache[pid] = cached
        return cached

    def list_processes(self):
        k = self._k
        snap = k.CreateToolhelp32Snapshot(self.TH32CS_SNAPPROCESS, 0)
        if not snap or snap == self._invalid:
            return []
        procs, seen = [], set()
        try:
            entry = _ProcessEntry()
            entry.dwSize = ctypes.sizeof(entry)
            ok = k.Process32FirstW(snap, ctypes.byref(entry))
            while ok:
                pid = entry.th32ProcessID
                if pid > 4:
                    name = _exe_name(entry)
                    seen.add(pid)
                    cached = self._info(pid, name)
                    if cached[2] in (self._my_session, -1):
                        procs.append(Proc(pid, name, cached[1], cached[2]))
                ok = k.Process32NextW(snap, ctypes.byref(entry))
        finally:
            k.CloseHandle(snap)
        for pid in [p for p in self._cache if p not in seen]:
            del self._cache[pid]
        return procs

    def terminate(self, pid):
        h = self._k.OpenProcess(self.PROCESS_TERMINATE, 0, pid)
        if not h:
            self.last_error = ctypes.get_last_error()
            return False
        try:
            ok = bool(self._k.TerminateProcess(h, 1))
            if not ok:
                self.last_error = ctypes.get_last_error()
            return ok
        finally:
            self._k.CloseHandle(h)


class AppGuard:
    """Decides what to do with each running program, every half second.

    1. A program not seen before (and not part of Windows) is recorded in
       Always Allowed.
    2. A program that is not allowed right now (Always Blocked, or its
       daily limit is used up) is closed again and again until it stays
       closed.
    Programs in Always Allowed are never closed, unless they also have a
    daily limit, which always applies.

    Screen time counts only while there has been keyboard or mouse input
    in the last couple of minutes, or a video is playing (when `idle` is
    given), so a PC left on does not use up the day.
    """

    def __init__(self, data, api, windir=None, own_pid=None, own_names=(),
                 watcher=None, idle=None, media=None):
        self.data = data
        self.idle = idle
        self.media = media
        self.api = api
        self.watcher = watcher
        self._event_logged = {}
        windir = windir or os.environ.get("SystemRoot") or r"C:\Windows"
        self.windir = windir.lower().rstrip("\\") + "\\"
        self.own_pid = os.getpid() if own_pid is None else own_pid
        self.never_kill = (CRITICAL_PROCESSES | PROTECTED_APP_NAMES
                           | {n.lower() for n in own_names})
        self.changed = False
        self._last = None
        self._streaks = set()

    def is_protected(self, name):
        return name.lower() in self.never_kill

    def _is_system_path(self, path):
        return path.lower().startswith(self.windir)

    @staticmethod
    def _names(rows):
        return {r[0].lower() for r in rows if r[1] == "App"}

    @staticmethod
    def _why(code):
        if code == 5:
            return ("access denied: the app runs with higher rights, so "
                    "LeafyGreen needs to run as administrator "
                    "(install.bat)")
        return f"Windows error {code}"

    def _log_watcher_events(self, now):
        """Writes what the background watcher closed into the activity log."""
        latest = {}
        while self.watcher.events:
            try:
                name, ok, code = self.watcher.events.popleft()
            except IndexError:
                break
            latest[name] = (ok, code)
        for name, (ok, code) in latest.items():
            key = name.lower()
            if now - self._event_logged.get(key, -999.0) < 10:
                continue
            self._event_logged[key] = now
            if ok:
                self.data.log("Blocked app closed", name, "Blocked")
            else:
                self.data.log("Could not close app",
                              f"{name} ({self._why(code)})", "Failed")
            self.changed = True

    def tick(self, now):
        d = self.data
        dt = 0.0
        if self._last is not None:
            dt = min(max(now - self._last, 0.0), 2.0)
        self._last = now
        d.roll_day()
        if (self.idle is None or self.idle() < ACTIVE_WITHIN_SECONDS
                or (self.media is not None and self.media())):
            d.used_today_sec += dt
        if self.api is None:
            return
        if self.watcher is not None:
            self.watcher.set_names(
                self._names(d.blocked) if d.protection_effective else ())
            self._log_watcher_events(now)

        procs = self.api.list_processes()
        running = {}
        for p in procs:
            running.setdefault(p.name.lower(), []).append(p)

        blocked = self._names(d.blocked)
        allowed = self._names(d.allowed)
        limited = {e["name"].lower(): e for e in d.limited}
        enforcing = d.protection_effective

        still_blocked = set()
        new_apps = []
        for name_l, plist in running.items():
            if name_l in self.never_kill:
                continue
            reason = None
            if name_l in blocked:
                reason = ("Blocked app closed", "Blocked")
            elif name_l in limited:
                entry = limited[name_l]
                if entry.get("used_sec", 0) >= entry["limit"] * 60:
                    reason = ("Daily limit reached, app closed", "Limited")
                else:
                    entry["used_sec"] = entry.get("used_sec", 0) + dt
            elif name_l in allowed:
                pass
            elif any(p.path and p.session != -1
                     and not self._is_system_path(p.path) for p in plist):
                new_apps.append(plist[0].name)

            if reason and enforcing:
                still_blocked.add(name_l)
                closed = False
                for p in plist:
                    if p.pid != self.own_pid and self.api.terminate(p.pid):
                        closed = True
                if name_l not in self._streaks:
                    self._streaks.add(name_l)
                    recent = now - self._event_logged.get(name_l, -999.0) < 10
                    self._event_logged[name_l] = now
                    if not recent:
                        if closed:
                            d.log(reason[0], plist[0].name, reason[1])
                        else:
                            code = getattr(self.api, "last_error", 0)
                            d.log("Could not close app",
                                  f"{plist[0].name} ({self._why(code)})",
                                  "Failed")
                    self.changed = True
        self._streaks &= still_blocked

        if enforcing and new_apps:
            first_scan = not d.baseline_done
            for name in new_apps:
                d.allowed.append([name, "App", today_str()])
                if not first_scan:
                    d.log("New app recorded", name, "Allowed")
            if first_scan:
                d.log("First scan", f"{len(new_apps)} running apps recorded "
                      "as allowed")
            self.changed = True
        if enforcing and procs and not d.baseline_done:
            d.baseline_done = True


class BlockWatcher:
    """Closes Always Blocked apps from its own background thread, ten times
    a second, so a busy or stalled window can never delay it. It has its own
    copy of the process API (the cache is not shared between threads). The
    main loop still does the logging, daily limits and new-app recording."""

    INTERVAL = 0.1

    def __init__(self, never_kill, own_pid=None):
        self.api = WindowsProcessApi()
        self.never_kill = frozenset(never_kill)
        self.own_pid = os.getpid() if own_pid is None else own_pid
        self.names = frozenset()
        self.events = collections.deque(maxlen=200)
        self._stop = threading.Event()
        threading.Thread(target=self._run, daemon=True).start()

    def set_names(self, names):
        self.names = frozenset(n for n in names if n not in self.never_kill)

    def stop(self):
        self._stop.set()

    def sweep(self):
        names = self.names
        if not names:
            return
        for p in self.api.list_processes():
            if p.name.lower() in names and p.pid != self.own_pid:
                ok = self.api.terminate(p.pid)
                self.events.append((p.name, ok, self.api.last_error))

    def _run(self):
        while not self._stop.wait(self.INTERVAL):
            try:
                self.sweep()
            except Exception:
                pass


NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
HOSTS_MARK_START = "# >>> LeafyGreen blocked websites (managed automatically) >>>"
HOSTS_MARK_END = "# <<< LeafyGreen blocked websites <<<"
LEGACY_HOSTS_MARKS = (
    ("# >>> Snort Secure blocked websites (managed automatically) >>>",
     "# <<< Snort Secure blocked websites <<<"),)
BROWSER_EXES = frozenset({"chrome.exe", "msedge.exe", "firefox.exe",
                          "brave.exe", "opera.exe", "vivaldi.exe",
                          "iexplore.exe"})
FIREFOX_ERROR_TITLES = ("unable to connect", "server not found",
                        "problem loading page", "secure connection failed",
                        "did not connect")
COMMON_SUBDOMAINS = ("www", "m", "mobile")
SITE_ALIASES = {
    "youtube.com": ("youtu.be", "youtube-nocookie.com"),
    "facebook.com": ("fb.com", "fb.me"),
    "twitter.com": ("x.com",),
    "x.com": ("twitter.com",),
    "reddit.com": ("redd.it",),
    "discord.com": ("discordapp.com", "discord.gg"),
}
SITE_SUBDOMAINS = {
    "youtube.com": ("music", "studio", "kids"),
    "reddit.com": ("old", "new"),
}


def title_shows_site(title, domain):
    """True if a browser window title looks like it is showing `domain`.

    The full name always counts (this is what Chrome and Edge show on the
    error page of a blocked site). The main word of the name (youtube for
    youtube.com) counts too, but only if it is 5+ letters and stands alone,
    so 'news.com' doesn't match 'Google News' and 'x.com' can't match
    every title with an x in it."""
    low = title.lower()
    if re.search(r"(?<![a-z0-9-])" + re.escape(domain) + r"(?![a-z0-9])",
                 low):
        return True
    labels = domain.split(".")
    word = labels[-2] if len(labels) >= 2 else ""
    return len(word) >= 5 and re.search(
        r"(?<![a-z0-9])" + re.escape(word) + r"(?![a-z0-9])", low) is not None


def lock_workstation():
    """Locks the screen (same as Windows+L). Returns True if it worked."""
    try:
        return bool(ctypes.WinDLL("user32").LockWorkStation())
    except Exception:
        return False


class _LastInputInfo(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint32), ("dwTime", ctypes.c_uint32)]


class InputMonitor:
    """Seconds since the last key press or mouse movement in this session."""

    def __init__(self):
        self._u = ctypes.WinDLL("user32", use_last_error=True)
        self._k = ctypes.WinDLL("kernel32")
        self._u.GetLastInputInfo.argtypes = [ctypes.POINTER(_LastInputInfo)]
        self._u.GetLastInputInfo.restype = ctypes.c_int
        self._k.GetTickCount.restype = ctypes.c_uint32

    def idle_seconds(self):
        try:
            info = _LastInputInfo()
            info.cbSize = ctypes.sizeof(info)
            if not self._u.GetLastInputInfo(ctypes.byref(info)):
                return 0.0
            return ((self._k.GetTickCount() - info.dwTime) & 0xFFFFFFFF) \
                / 1000.0
        except Exception:
            return 0.0


class MediaMonitor:
    """True while something is keeping the screen awake on purpose (a video
    playing in a browser or player), so watching without touching the mouse
    still counts as screen time. Asks Windows with `powercfg /requests` every
    20 seconds in the background. If it can't tell, the answer is False and
    only keyboard and mouse use counts."""

    INTERVAL = 20.0

    def __init__(self, start=True):
        self.playing = False
        self._stop = threading.Event()
        if start:
            threading.Thread(target=self._run, daemon=True).start()

    def __call__(self):
        return self.playing

    @staticmethod
    def parse(text):
        """True if the DISPLAY section of `powercfg /requests` lists a
        program (English Windows)."""
        in_display = False
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.upper().startswith("DISPLAY:"):
                in_display = True
                continue
            if in_display:
                if not stripped:
                    if in_display == "seen":
                        return False
                    continue
                if stripped.upper().endswith(":") and stripped.isupper():
                    return False
                if stripped.startswith("["):
                    return True
                in_display = "seen"
        return False

    def check(self):
        try:
            out = subprocess.run(["powercfg", "/requests"],
                                 capture_output=True, text=True, timeout=8,
                                 creationflags=NO_WINDOW)
            return self.parse(out.stdout)
        except (OSError, subprocess.SubprocessError):
            return False

    def _run(self):
        while not self._stop.is_set():
            self.playing = self.check()
            self._stop.wait(self.INTERVAL)

    def stop(self):
        self._stop.set()


class BrowserWindows:
    """Lists visible windows with a title and the process that owns each."""

    def __init__(self):
        u = ctypes.WinDLL("user32", use_last_error=True)
        self._proc_type = ctypes.WINFUNCTYPE(
            ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p)
        u.EnumWindows.argtypes = [self._proc_type, ctypes.c_void_p]
        u.EnumWindows.restype = ctypes.c_int
        u.IsWindowVisible.argtypes = [ctypes.c_void_p]
        u.IsWindowVisible.restype = ctypes.c_int
        u.GetWindowTextLengthW.argtypes = [ctypes.c_void_p]
        u.GetWindowTextLengthW.restype = ctypes.c_int
        u.GetWindowTextW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p,
                                     ctypes.c_int]
        u.GetWindowTextW.restype = ctypes.c_int
        u.GetWindowThreadProcessId.argtypes = [
            ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32)]
        self._u = u

    def titles(self):
        """[(pid, title), ...]"""
        found, u = [], self._u

        def callback(hwnd, _):
            if u.IsWindowVisible(hwnd):
                n = u.GetWindowTextLengthW(hwnd)
                if n > 0:
                    buf = ctypes.create_unicode_buffer(n + 1)
                    u.GetWindowTextW(hwnd, buf, n + 1)
                    pid = ctypes.c_uint32()
                    u.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                    found.append((pid.value, buf.value))
            return 1

        u.EnumWindows(self._proc_type(callback), 0)
        return found


class WebsiteGuard:
    """Blocks websites listed in Always Blocked.

    The Windows hosts file is pointed at 127.0.0.1 for each blocked domain
    (and its www. form), so no browser can reach it. If a browser window
    still shows a blocked site (a page loaded before the block, or a cached
    lookup), that browser is closed.

    This works by domain name only. It does not read the contents of network
    traffic, so a VPN, a different DNS setting inside the browser, or a
    different spelling of the same site can get around it.
    """

    def __init__(self, api, hosts_path=None):
        self.api = api
        self.hosts_path = hosts_path or os.path.join(
            os.environ.get("SystemRoot", r"C:\Windows"),
            "System32", "drivers", "etc", "hosts")
        self._applied = None
        self._last_try = -999.0
        self._last_error = None
        self._windows = None
        if api is not None:
            try:
                self._windows = BrowserWindows()
            except Exception:
                self._windows = None

    @staticmethod
    def base_domains(blocked_rows):
        """The valid blocked websites plus their well-known aliases."""
        out = set()
        for name, kind, _added in blocked_rows:
            if kind != "Website":
                continue
            site = normalize_site_name(name)
            if site is not None:
                out.add(site)
                out.update(SITE_ALIASES.get(site, ()))
        return out

    @classmethod
    def domains(cls, blocked_rows):
        """Every name written to the hosts file (adds www., m., ...)."""
        out = set()
        for site in cls.base_domains(blocked_rows):
            out.add(site)
            for sub_name in COMMON_SUBDOMAINS + SITE_SUBDOMAINS.get(site, ()):
                out.add(f"{sub_name}.{site}")
        return out

    @staticmethod
    def build_hosts_text(original, domains, newline="\n"):
        """Returns the hosts file text with our block replaced/removed."""
        keep, end_mark = [], None
        starts = dict(((HOSTS_MARK_START, HOSTS_MARK_END),)
                      + LEGACY_HOSTS_MARKS)
        for line in original.splitlines():
            stripped = line.strip()
            if end_mark is None and stripped in starts:
                end_mark = starts[stripped]
            elif end_mark is not None and stripped == end_mark:
                end_mark = None
            elif end_mark is None:
                keep.append(line)
        while keep and not keep[-1].strip():
            keep.pop()
        if domains:
            keep.append("")
            keep.append(HOSTS_MARK_START)
            for d in sorted(domains):
                keep.append(f"127.0.0.1 {d}")
                keep.append(f"::1 {d}")
            keep.append(HOSTS_MARK_END)
        return newline.join(keep) + newline

    def _sync_hosts(self, domains):
        """Returns an error message or None."""
        try:
            with open(self.hosts_path, encoding="utf-8",
                      errors="surrogateescape", newline="") as f:
                original = f.read()
            if not domains and HOSTS_MARK_START not in original and not any(
                    legacy in original for legacy, _ in LEGACY_HOSTS_MARKS):
                return None
            newline = "\r\n" if "\r\n" in original else "\n"
            new_text = self.build_hosts_text(original, domains, newline)
            if new_text.splitlines() != original.splitlines():
                with open(self.hosts_path, "w", encoding="utf-8",
                          errors="surrogateescape", newline="") as f:
                    f.write(new_text)
                subprocess.run(["ipconfig", "/flushdns"],
                               capture_output=True, timeout=10,
                               creationflags=NO_WINDOW)
        except (OSError, subprocess.SubprocessError) as exc:
            return str(exc)
        return None

    def tick(self, blocked_rows, data, now):
        domains = self.domains(blocked_rows)
        if domains != self._applied and now - self._last_try >= 10:
            self._last_try = now
            error = self._sync_hosts(domains)
            if error is None:
                self._applied = domains
                self._last_error = None
            elif error != self._last_error:
                self._last_error = error
                data.log("Website blocking failed", error, "Failed")
        if not domains or self._windows is None or self.api is None:
            return
        bases = self.base_domains(blocked_rows)
        names = {p.pid: p.name.lower() for p in self.api.list_processes()}
        closed = set()
        for pid, title in self._windows.titles():
            exe = names.get(pid)
            if exe not in BROWSER_EXES or exe in closed:
                continue
            hit = next((b for b in sorted(bases)
                        if title_shows_site(title, b)), None)
            if hit is None and exe == "firefox.exe" and \
                    title.lower().startswith(FIREFOX_ERROR_TITLES):
                hit = "blocked site (Firefox error page)"
            if hit and self.api.terminate(pid):
                closed.add(exe)
                data.log("Browser closed (blocked site)", hit, "Blocked")


SMARTSAFE_DOH_URL = "https://family.cloudflare-dns.com/dns-query"
SMARTSAFE_SCAN_SECONDS = 3
ALWAYS_ALLOWED_SITES = ("discord.gg", "discord.com")
SMARTSAFE_PER_SCAN = 8
SMARTSAFE_RECHECK_SECONDS = 6 * 3600
SMART_DENIED_MAX = 500
SMART_APPROVED_MAX = 1000
PRIVATE_SUFFIXES = (".local", ".lan", ".internal", ".home", ".localdomain",
                    ".corp", ".intranet", ".localhost")
CHROMIUM_BASES = (
    r"AppData\Local\Google\Chrome\User Data",
    r"AppData\Local\Microsoft\Edge\User Data",
    r"AppData\Local\BraveSoftware\Brave-Browser\User Data",
    r"AppData\Local\Vivaldi\User Data",
    r"AppData\Roaming\Opera Software\Opera Stable",
)
FIREFOX_PROFILES = r"AppData\Roaming\Mozilla\Firefox\Profiles"
_WEBKIT_EPOCH = 11644473600


def child_home():
    if sys.platform == "win32" and CHILD_USER:
        home = os.path.join(os.environ.get("SystemDrive", "C:") + "\\",
                            "Users", CHILD_USER)
        if os.path.isdir(home):
            return home
    return os.path.expanduser("~")


def _doh_json(host, rtype):
    url = (f"{SMARTSAFE_DOH_URL}?name={urllib.parse.quote(host)}"
           f"&type={rtype}")
    req = urllib.request.Request(
        url, headers={"accept": "application/dns-json",
                      "User-Agent": "LeafyGreen"})
    with urllib.request.urlopen(req, timeout=6) as resp:
        return json.loads(resp.read(65536).decode("utf-8"))


def smartsafe_check(host, fetch_json=None):
    """'unsafe', 'safe' or 'unknown' (the name does not exist). Raises if
    the lookup itself fails, so the caller can try again later."""
    fetch_json = fetch_json or _doh_json
    for rtype in ("A", "AAAA"):
        answer = fetch_json(host, rtype)
        status = answer.get("Status")
        if status not in (0, 3):
            raise RuntimeError(f"DNS status {status}")
        ips = [a.get("data", "") for a in answer.get("Answer") or []
               if a.get("type") in (1, 28)]
        if any(ip in ("0.0.0.0", "::") for ip in ips):
            return "unsafe"
        if ips:
            return "safe"
        if status == 3:
            return "unknown"
    return "unknown"


def host_from_url(url):
    """'https://www.Example.com/a' -> 'example.com' (None for anything that
    is not an ordinary website address)."""
    try:
        parts = urllib.parse.urlsplit(str(url))
        if parts.scheme not in ("http", "https") or not parts.hostname:
            return None
        host = normalize_site_name(parts.hostname)
    except ValueError:
        return None
    if host is None or host.endswith(PRIVATE_SUFFIXES):
        return None
    return host


def _copy_db(path, tmp, wal=False):
    dest = os.path.join(tmp, "h.sqlite")
    shutil.copyfile(path, dest)
    if wal and os.path.exists(path + "-wal"):
        shutil.copyfile(path + "-wal", dest + "-wal")
    return dest


def _read_history(path, kind, cursor):
    """[(url, time), ...] newer than `cursor`, from a copy of the file (the
    browser keeps the real one open)."""
    tmp = tempfile.mkdtemp(prefix="lg_")
    try:
        db = _copy_db(path, tmp, wal=(kind == "firefox"))
        con = sqlite3.connect(db)
        try:
            if kind == "firefox":
                sql = ("SELECT url, last_visit_date FROM moz_places WHERE "
                       "last_visit_date > ? ORDER BY last_visit_date "
                       "LIMIT 300")
            else:
                sql = ("SELECT url, last_visit_time FROM urls WHERE "
                       "last_visit_time > ? ORDER BY last_visit_time "
                       "LIMIT 300")
            return con.execute(sql, (cursor,)).fetchall()
        finally:
            con.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def history_files(home):
    """[(path, kind)] of the browser history databases that exist."""
    found = []
    for base in CHROMIUM_BASES:
        root = os.path.join(home, *base.split("\\"))
        candidates = [os.path.join(root, "History")]
        try:
            for name in os.listdir(root):
                if name == "Default" or name.startswith("Profile "):
                    candidates.append(os.path.join(root, name, "History"))
        except OSError:
            pass
        found += [(p, "chromium") for p in candidates if os.path.isfile(p)]
    profiles = os.path.join(home, *FIREFOX_PROFILES.split("\\"))
    try:
        for name in os.listdir(profiles):
            p = os.path.join(profiles, name, "places.sqlite")
            if os.path.isfile(p):
                found.append((p, "firefox"))
    except OSError:
        pass
    return found


def _file_sig(path):
    try:
        st = os.stat(path)
        return (st.st_mtime_ns, st.st_size)
    except OSError:
        return None


def visited_hosts(home, cursors, sigs=None):
    """Websites visited since the last call. `cursors` remembers, per
    history file, how far we have read (starts ten minutes back). `sigs`
    remembers each file's size and time, so a file that has not changed is
    not copied and read again."""
    hosts = []
    now = time.time() - 600
    for path, kind in history_files(home):
        start = (int((now + _WEBKIT_EPOCH) * 1e6) if kind == "chromium"
                 else int(now * 1e6))
        cursor = cursors.setdefault(path, start)
        if sigs is not None:
            sig = (_file_sig(path), _file_sig(path + "-wal"))
            if sigs.get(path) == sig:
                continue
            sigs[path] = sig
        try:
            rows = _read_history(path, kind, cursor)
        except (OSError, sqlite3.Error):
            if sigs is not None:
                sigs.pop(path, None)
            continue
        for url, stamp in rows:
            host = host_from_url(url)
            if host and host not in hosts:
                hosts.append(host)
            if isinstance(stamp, int) and stamp > cursors[path]:
                cursors[path] = stamp
    return hosts


def site_matches(host, name):
    """The website is `name`, or a page-name under it (www.name, m.name...)."""
    return host == name or host.endswith("." + name)


def host_is_decided(host, manual):
    """True if the parent already listed this website (or its main domain)."""
    return any(site_matches(host, n) for n in manual)


def website_decision(host, blocked, allowed):
    """How a website is judged, in this order:
      1. on the parent's blocklist            -> "block"
      2. on the parent's allowlist            -> "allow"
      3. discord.gg / discord.com             -> "always" (never denied)
      4. anything else                        -> "check" (ask SmartSafe)
    `blocked` and `allowed` are the website names the parent listed."""
    if host_is_decided(host, blocked):
        return "block"
    if host_is_decided(host, allowed):
        return "allow"
    if host_is_decided(host, ALWAYS_ALLOWED_SITES):
        return "always"
    return "check"


def parent_site_lists(data):
    """(blocked, allowed): the websites the parent put on each list."""
    out = []
    for rows in (data.blocked, data.allowed):
        names = set()
        for name, kind, _added in rows:
            if kind == "Website":
                site = normalize_site_name(name)
                if site:
                    names.add(site)
        out.append(frozenset(names))
    return out[0], out[1]


def smartsafe_block_rows(data):
    """The SmartSafe Denied websites that are really blocked right now: none
    if SmartSafe is off, and never one the parent allowed or one of the
    always-allowed websites."""
    if not data.smartsafe_enabled:
        return []
    blocked, allowed = parent_site_lists(data)
    return [r for r in data.smart_denied
            if website_decision(r[0], blocked, allowed) == "check"]


class SmartSafe:
    """Looks up newly visited websites in the background. The main loop
    calls tick() to collect results and update Data (all list changes happen
    on the main thread).

    Each website is judged by website_decision(): the parent's blocklist and
    allowlist come first, then the built-in always-allowed websites, and only
    a website that none of them cover is checked with Cloudflare."""

    def __init__(self, home_func=child_home, fetch_json=None):
        self.home_func = home_func
        self.fetch_json = fetch_json
        self.enabled = False
        self.results = collections.deque()
        self.pending = collections.OrderedDict()
        self._seen = {}
        self._cursors = {}
        self._sigs = {}
        self._lists = (frozenset(), frozenset(), frozenset())
        self._last_scan = 0.0
        self.last_error = None
        self._stop = threading.Event()
        self._thread = None

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()

    def tick(self, data, enabled, note):
        """Collects finished checks. Returns True if a list changed."""
        self.enabled = enabled
        blocked, allowed = parent_site_lists(data)
        changed = False
        keep = [r for r in data.smart_denied
                if website_decision(r[0], blocked, allowed) == "check"]
        if len(keep) != len(data.smart_denied):
            data.smart_denied[:] = keep
            changed = True
        smart = {r[0] for r in data.smart_denied} | \
            {r[0] for r in data.smart_approved}
        self._lists = (blocked, allowed, frozenset(smart))
        while self.results:
            host, verdict = self.results.popleft()
            decision = website_decision(host, blocked, allowed)
            if host in smart or decision in ("block", "allow"):
                continue
            row = [host, "Website", today_str()]
            if verdict == "unsafe" and decision == "check":
                data.smart_denied.append(row)
                del data.smart_denied[:-SMART_DENIED_MAX]
                note("SmartSafe denied", host)
                changed = True
            elif verdict == "safe":
                data.smart_approved.append(row)
                del data.smart_approved[:-SMART_APPROVED_MAX]
                changed = True
        return changed

    def _run(self):
        while not self._stop.wait(1):
            try:
                if self.enabled and \
                        time.monotonic() - self._last_scan >= \
                        SMARTSAFE_SCAN_SECONDS:
                    self._last_scan = time.monotonic()
                    self.scan()
            except Exception as exc:
                self.last_error = str(exc)

    def scan(self):
        """One round: read new visits, judge them, look up a few of them."""
        blocked, allowed, smart = self._lists
        now = time.time()
        for host in visited_hosts(self.home_func(), self._cursors,
                                  self._sigs):
            if (host in smart
                    or website_decision(host, blocked, allowed)
                    in ("block", "allow")
                    or now - self._seen.get(host, 0)
                    < SMARTSAFE_RECHECK_SECONDS):
                continue
            self.pending.setdefault(host, True)
        while len(self.pending) > 200:
            self.pending.popitem(last=False)
        for host in list(self.pending)[:SMARTSAFE_PER_SCAN]:
            blocked, allowed, smart = self._lists
            decision = website_decision(host, blocked, allowed)
            if host in smart or decision in ("block", "allow"):
                del self.pending[host]
                continue
            if decision == "always":
                del self.pending[host]
                self.results.append((host, "safe"))
                continue
            try:
                verdict = smartsafe_check(host, self.fetch_json)
            except Exception as exc:
                self.last_error = str(exc)
                return
            del self.pending[host]
            if verdict == "unknown":
                self._seen[host] = now
            else:
                self.results.append((host, verdict))


class InternetPauseGuard:
    """While Pause Internet is on, keeps turning every network adapter off
    (again, if Windows or anyone turns one back on). Turning Pause Internet
    off switches the adapters it disabled back on.

    The adapters it turned off are written to a small file, so they are
    switched back on even if the app was closed or restarted (or the PC
    rebooted) while the internet was paused."""

    def __init__(self, state_path=None):
        self.active = False
        self.disabled = set()
        self.state_path = state_path
        self._last_check = -999.0
        self._retry_at = 0.0
        self._warned = False
        self._load()

    def _load(self):
        if not self.state_path:
            return
        try:
            with open(self.state_path, encoding="utf-8") as f:
                names = [ln.strip() for ln in f if ln.strip()]
        except OSError:
            return
        if names:
            self.disabled = set(names)
            self.active = True

    def _save(self):
        if not self.state_path:
            return
        try:
            if self.disabled:
                os.makedirs(os.path.dirname(self.state_path), exist_ok=True)
                with open(self.state_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(sorted(self.disabled)) + "\n")
            elif os.path.exists(self.state_path):
                os.remove(self.state_path)
        except OSError:
            pass

    @staticmethod
    def parse_interfaces(text):
        """[(name, enabled)] from the output of `netsh interface show
        interface` (English Windows)."""
        lines = text.splitlines()
        start = next((i + 1 for i, ln in enumerate(lines)
                      if ln.strip().startswith("---")), len(lines))
        rows = []
        for line in lines[start:]:
            parts = line.split(None, 3)
            if len(parts) == 4 and parts[2].lower() != "loopback":
                rows.append((parts[3].strip(), parts[0].lower() == "enabled"))
        return rows

    def _interfaces(self):
        try:
            out = subprocess.run(
                ["netsh", "interface", "show", "interface"],
                capture_output=True, text=True, timeout=10,
                creationflags=NO_WINDOW)
        except (OSError, subprocess.SubprocessError):
            return []
        return self.parse_interfaces(out.stdout)

    @staticmethod
    def _set(name, enabled):
        try:
            result = subprocess.run(
                ["netsh", "interface", "set", "interface", name,
                 "admin=" + ("enable" if enabled else "disable")],
                capture_output=True, timeout=10, creationflags=NO_WINDOW)
            return result.returncode == 0
        except (OSError, subprocess.SubprocessError):
            return False

    def tick(self, paused, now, log=None):
        if paused:
            self.active = True
            self._retry_at = 0.0
            if now - self._last_check < 3:
                return
            self._last_check = now
            failed = False
            for name, enabled in self._interfaces():
                if enabled:
                    new = name not in self.disabled
                    self.disabled.add(name)
                    self._save()
                    if self._set(name, False):
                        if new and log:
                            log("Network adapter turned off", name)
                    else:
                        failed = True
                        self.disabled.discard(name)
                        self._save()
            if failed and not self._warned and log:
                self._warned = True
                log("Could not pause the internet",
                    "Needs administrator rights (install with install.bat)")
        elif self.active:
            if now < self._retry_at:
                return
            self._warned = False
            names = sorted(self.disabled)
            failed = {n for n in names if not self._set(n, True)}
            restored = [n for n in names if n not in failed]
            self.disabled = failed
            self._save()
            if restored and log:
                log("Network adapters turned back on", ", ".join(restored))
            if failed:
                self._retry_at = now + 5
            else:
                self.active = False


class _NotifyIconData(ctypes.Structure):
    """NOTIFYICONDATAW from shellapi.h (976 bytes on 64-bit Windows). Text
    fields are arrays of 16-bit numbers so the size is the same everywhere."""
    _fields_ = [
        ("cbSize", ctypes.c_uint32), ("hWnd", ctypes.c_void_p),
        ("uID", ctypes.c_uint32), ("uFlags", ctypes.c_uint32),
        ("uCallbackMessage", ctypes.c_uint32), ("hIcon", ctypes.c_void_p),
        ("szTip", ctypes.c_uint16 * 128), ("dwState", ctypes.c_uint32),
        ("dwStateMask", ctypes.c_uint32), ("szInfo", ctypes.c_uint16 * 256),
        ("uTimeout", ctypes.c_uint32), ("szInfoTitle", ctypes.c_uint16 * 64),
        ("dwInfoFlags", ctypes.c_uint32), ("guidItem", ctypes.c_uint8 * 16),
        ("hBalloonIcon", ctypes.c_void_p),
    ]


def _put_text(field, text):
    """Copies text into a fixed 16-bit array (always ends with a 0)."""
    units = text.encode("utf-16-le")
    codes = [int.from_bytes(units[i:i + 2], "little")
             for i in range(0, len(units), 2)][:len(field) - 1]
    for i in range(len(field)):
        field[i] = codes[i] if i < len(codes) else 0


class Notifier:
    """A real Windows notification (the pop-up in the corner of the screen,
    kept in the notification centre) using the system tray API, which needs
    nothing installed and works for a program running as SYSTEM in the
    child's session. `show` returns False when Windows would not take it."""

    NIM_ADD, NIM_MODIFY, NIM_DELETE = 0, 1, 2
    NIF_ICON, NIF_TIP, NIF_INFO = 0x2, 0x4, 0x10
    NIIF_INFO = 0x1
    IDI_APPLICATION = 32512

    def __init__(self, hwnd_of, shell=None, icon=None):
        self.hwnd_of = hwnd_of
        self.shell = shell
        self.icon = icon
        self._added = False
        if shell is None and sys.platform == "win32":
            try:
                fn = ctypes.WinDLL("shell32", use_last_error=True) \
                    .Shell_NotifyIconW
                fn.argtypes = [ctypes.c_uint32,
                               ctypes.POINTER(_NotifyIconData)]
                fn.restype = ctypes.c_int
                self.shell = lambda msg, data: bool(
                    fn(msg, ctypes.byref(data)))
                user = ctypes.WinDLL("user32", use_last_error=True)
                user.LoadIconW.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
                user.LoadIconW.restype = ctypes.c_void_p
                self.icon = user.LoadIconW(None, self.IDI_APPLICATION)
            except Exception:
                self.shell = None

    def _data(self, title, text):
        d = _NotifyIconData()
        d.cbSize = ctypes.sizeof(d)
        d.hWnd = self.hwnd_of()
        d.uID = 1
        d.uFlags = self.NIF_ICON | self.NIF_TIP | self.NIF_INFO
        d.hIcon = self.icon
        _put_text(d.szTip, APP_NAME)
        _put_text(d.szInfoTitle, title[:63])
        _put_text(d.szInfo, text[:255])
        d.dwInfoFlags = self.NIIF_INFO
        return d

    def show(self, title, text):
        if self.shell is None:
            return False
        try:
            data = self._data(title, text)
            if self._added and self.shell(self.NIM_MODIFY, data):
                return True
            self._added = False
            if self.shell(self.NIM_ADD, data):
                self._added = True
                return True
        except Exception:
            pass
        return False

    def close(self):
        """Removes the tray icon (when the app exits)."""
        if self._added and self.shell is not None:
            try:
                self.shell(self.NIM_DELETE, self._data("", ""))
            except Exception:
                pass
            self._added = False


class LimitGuard:
    """Locks the screen when today's time is used up or during bedtime, and
    locks it again every few seconds if it gets unlocked while that is
    still true. Adding bonus time or turning protection off stops it.

    The screen time alerts are honoured too (up to three): each heads-up is
    shown once, that many minutes before the time limit or before bedtime."""

    RELOCK_SECONDS = 3

    def __init__(self):
        self._last_lock = -999.0
        self._warned = set()

    @staticmethod
    def in_bedtime(bedtime, moment):
        if not bedtime.get("enabled"):
            return False
        cur, start, end = moment.strftime("%H:%M"), bedtime["start"], \
            bedtime["end"]
        if start == end:
            return False
        if start < end:
            return start <= cur < end
        return cur >= start or cur < end

    def reason(self, data, moment=None):
        """Why the screen should be locked right now, or None."""
        if not data.protection_effective:
            return None
        moment = moment or datetime.datetime.now()
        limit = data.limits[DAYS[moment.weekday()]]
        if limit["enabled"] and \
                data.used_today_min >= limit["minutes"] + data.bonus_min:
            return "Time limit reached"
        if self.in_bedtime(data.bedtime, moment):
            return "Bedtime"
        return None

    def warning(self, data, moment=None):
        """Text of a heads-up to show right now, or None. Every alert time is
        shown once (adding bonus time lets the time-limit ones show again)."""
        if not data.protection_effective:
            return None
        moment = moment or datetime.datetime.now()
        alerts = sorted(data.warn_alerts, reverse=True)
        if not alerts:
            return None
        today = moment.date().isoformat()
        limit = data.limits[DAYS[moment.weekday()]]
        if limit["enabled"]:
            total = limit["minutes"] + data.bonus_min
            left = total - data.used_today_sec / 60.0
            due = [a for a in alerts if 0 < left <= a
                   and ("limit", today, total, a) not in self._warned]
            if due:
                for a in due:
                    self._warned.add(("limit", today, total, a))
                return (f"About {max(1, math.ceil(left))} minute(s) of "
                        "screen time left today.")
        bed = data.bedtime
        if (bed.get("enabled") and bed.get("start") != bed.get("end")
                and not self.in_bedtime(bed, moment)):
            try:
                hour, minute = (int(x) for x in bed["start"].split(":"))
            except (ValueError, KeyError):
                return None
            start = moment.replace(hour=hour, minute=minute, second=0,
                                   microsecond=0)
            if start <= moment:
                start += datetime.timedelta(days=1)
            until = (start - moment).total_seconds() / 60.0
            due = [a for a in alerts if 0 < until <= a
                   and ("bed", today, bed["start"], a) not in self._warned]
            if due:
                for a in due:
                    self._warned.add(("bed", today, bed["start"], a))
                return (f"Bedtime starts in about "
                        f"{max(1, math.ceil(until))} minute(s).")
        return None

    def seconds_left(self, data, moment=None):
        """Seconds of screen time left today, or None when there is no
        limit today (or protection is off)."""
        if not data.protection_effective:
            return None
        moment = moment or datetime.datetime.now()
        limit = data.limits[DAYS[moment.weekday()]]
        if not limit["enabled"]:
            return None
        return (limit["minutes"] + data.bonus_min) * 60 - data.used_today_sec

    def countdown_due(self, data, moment=None):
        """True once when the time limit is COUNTDOWN_SECONDS or less away.
        Adding time lets it come round again."""
        moment = moment or datetime.datetime.now()
        left = self.seconds_left(data, moment)
        if left is None or not 0 < left <= COUNTDOWN_SECONDS:
            return False
        limit = data.limits[DAYS[moment.weekday()]]
        key = ("count", moment.date().isoformat(),
               limit["minutes"] + data.bonus_min)
        if key in self._warned:
            return False
        self._warned.add(key)
        return True

    def tick(self, data, now, log=None, warn=None):
        text = self.warning(data)
        if text:
            if log:
                log("Time warning", text)
            if warn:
                warn(text)
        why = self.reason(data)
        if why is None or now - self._last_lock < self.RELOCK_SECONDS:
            return
        first = now - self._last_lock > 60
        self._last_lock = now
        if lock_workstation() and first and log:
            log("Screen locked", why)


class Dialog(tk.Toplevel):
    """Small modal dialog. After construction, read `.result` (None if the
    dialog was cancelled)."""

    initial_focus = None
    ok_text = "OK"

    def __init__(self, parent, title):
        super().__init__(parent)
        self.title(title)
        self.configure(bg=BG)
        self.resizable(False, False)
        self.transient(parent.winfo_toplevel())
        try:
            if parent.winfo_toplevel().attributes("-topmost"):
                self.attributes("-topmost", True)
        except tk.TclError:
            pass
        self.result = None

        body = ttk.Frame(self, padding=16)
        body.pack(fill="both", expand=True)
        self.build(body)

        buttons = ttk.Frame(self, padding=(16, 0, 16, 16))
        buttons.pack(fill="x")
        ttk.Button(buttons, text="Cancel", command=self.destroy).pack(
            side="right")
        ttk.Button(buttons, text=self.ok_text, style="Accent.TButton",
                   command=self._ok).pack(side="right", padx=(0, 8))
        self.bind("<Return>", lambda e: self._ok())
        self.bind("<Escape>", lambda e: self.destroy())

        self.update_idletasks()
        top = parent.winfo_toplevel()
        x = top.winfo_rootx() + (top.winfo_width() - self.winfo_width()) // 2
        y = top.winfo_rooty() + (top.winfo_height() - self.winfo_height()) // 3
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")

        self.wait_visibility()
        self.grab_set()
        if self.initial_focus is not None:
            self.initial_focus.focus_set()
        else:
            self.focus_set()
        self.wait_window(self)

    def build(self, body):
        pass

    def validate(self):
        return True

    def collect(self):
        return None

    def _ok(self):
        if self.validate():
            self.result = self.collect()
            self.destroy()


class PinEntry(tk.Frame):
    """Four big boxes for a 4-digit PIN. Type the digits and the cursor moves
    on by itself, Backspace goes back, and pasting a PIN works. get() returns
    the digits typed so far."""
    LENGTH = 4

    def __init__(self, parent, on_complete=None, on_edit=None):
        super().__init__(parent, bg=BG)
        self.on_complete = on_complete
        self.on_edit = on_edit
        self.boxes = []
        for i in range(self.LENGTH):
            box = tk.Entry(self, width=2, justify="center",
                           font=(FONT, 22, "bold"), show="\u2022",
                           relief="flat", bd=0, bg="white", fg=TEXT,
                           insertwidth=0, highlightthickness=2,
                           highlightbackground=BORDER,
                           highlightcolor=ACCENT)
            box.grid(row=0, column=i, padx=5, ipady=8)
            box.bind("<KeyPress>", lambda e, i=i: self._key(e, i))
            box.bind("<FocusIn>", lambda e, i=i: self._select(i))
            box.bind("<<Paste>>", self._paste)
            self.boxes.append(box)

    def get(self):
        return "".join(b.get() for b in self.boxes)

    def _set(self, i, ch):
        self.boxes[i].delete(0, "end")
        if ch:
            self.boxes[i].insert(0, ch)

    def clear(self):
        for i in range(self.LENGTH):
            self._set(i, "")
        self.focus_first()

    def focus_first(self):
        empty = [b for b in self.boxes if not b.get()]
        (empty[0] if empty else self.boxes[0]).focus_set()

    def set_error(self, bad):
        for b in self.boxes:
            b.configure(highlightbackground=RED if bad else BORDER,
                        highlightcolor=RED if bad else ACCENT)

    def _select(self, i):
        self.boxes[i].after_idle(
            lambda: self.boxes[i].select_range(0, "end"))

    def _edited(self):
        self.set_error(False)
        if self.on_edit:
            self.on_edit()

    def _finished(self):
        if self.on_complete and len(self.get()) == self.LENGTH:
            self.after(120, self.on_complete)

    def _key(self, event, i):
        key, char = event.keysym, event.char
        if key in ("Tab", "ISO_Left_Tab", "Return", "KP_Enter", "Escape"):
            return None
        if key == "BackSpace":
            if self.boxes[i].get():
                self._set(i, "")
            elif i > 0:
                self._set(i - 1, "")
                self.boxes[i - 1].focus_set()
            self._edited()
            return "break"
        if key == "Delete":
            self._set(i, "")
            self._edited()
            return "break"
        if key == "Left" and i > 0:
            self.boxes[i - 1].focus_set()
            return "break"
        if key == "Right" and i < self.LENGTH - 1:
            self.boxes[i + 1].focus_set()
            return "break"
        if char and char.isdigit():
            self._set(i, char)
            self._edited()
            if i < self.LENGTH - 1:
                self.boxes[i + 1].focus_set()
            else:
                self._finished()
            return "break"
        if event.state & 0x4:
            return None
        return "break"

    def _paste(self, event=None):
        try:
            text = self.clipboard_get()
        except tk.TclError:
            return "break"
        digits = [c for c in text if c.isdigit()][:self.LENGTH]
        for i, c in enumerate(digits):
            self._set(i, c)
        if digits:
            self._edited()
            self.boxes[min(len(digits), self.LENGTH - 1)].focus_set()
            self._finished()
        return "break"


class PinDialog(Dialog):
    """Asks for one or more 4-digit codes.

    prompts: label for each PIN. check: optional function that receives the
    list of entered codes and returns an error message, or None if fine.
    With a single PIN the dialog answers by itself when the 4th digit is
    typed; a wrong PIN shakes the window and shows the reason under it.
    """

    def __init__(self, parent, title, prompts, check=None):
        self.prompts = prompts
        self.check = check
        self.entries = []
        super().__init__(parent, title)

    def build(self, body):
        tk.Label(body, text="\U0001F512", bg=BG, fg=ACCENT,
                 font=(FONT, 28)).grid(row=0, column=0, pady=(0, 4))
        count = len(self.prompts)
        for i, text in enumerate(self.prompts):
            tk.Label(body, text=text, bg=BG, fg=TEXT,
                     font=(FONT, 10, "bold")).grid(
                row=1 + 2 * i, column=0, pady=(8, 4))
            entry = PinEntry(
                body, on_complete=lambda i=i: self._entered(i),
                on_edit=lambda: self.error_var.set(""))
            entry.grid(row=2 + 2 * i, column=0)
            self.entries.append(entry)
        self.error_var = tk.StringVar()
        tk.Label(body, textvariable=self.error_var, bg=BG, fg=RED,
                 font=(FONT, 9), wraplength=280, justify="center",
                 height=2).grid(row=2 + 2 * count, column=0, pady=(8, 0))
        self.initial_focus = self.entries[0].boxes[0]

    def _entered(self, i):
        """The 4th digit of PIN number i was typed."""
        try:
            if i + 1 < len(self.entries):
                self.entries[i + 1].focus_first()
            else:
                self._ok()
        except tk.TclError:
            pass

    def _fail(self, message, clear_all):
        self.error_var.set(message)
        for e in self.entries:
            e.set_error(True)
            if clear_all:
                e.clear()
        self.entries[0].focus_first()
        self._shake()

    def _shake(self, step=0, origin=None):
        try:
            origin = origin or (self.winfo_x(), self.winfo_y())
            offsets = (-9, 9, -7, 7, -4, 4, 0)
            self.geometry(f"+{origin[0] + offsets[step]}+{origin[1]}")
            if step + 1 < len(offsets):
                self.after(30, lambda: self._shake(step + 1, origin))
        except tk.TclError:
            pass

    def validate(self):
        values = [e.get() for e in self.entries]
        if any(len(v) != 4 for v in values):
            self._fail("Enter all 4 digits.", clear_all=False)
            return False
        if self.check:
            error = self.check(values)
            if error:
                self._fail(error, clear_all=True)
                return False
        return True

    def collect(self):
        return [e.get() for e in self.entries]


class PauseDialog(Dialog):
    """How long to pause the internet. result = minutes (0 = until it is
    turned back on)."""
    ok_text = "Pause"

    def __init__(self, parent):
        super().__init__(parent, "Pause Internet")

    def build(self, body):
        ttk.Label(body, text="Pause the internet for").grid(
            row=0, column=0, sticky="w")
        self.var = tk.StringVar(value="30 minutes")
        box = ttk.Combobox(body, textvariable=self.var, state="readonly",
                           values=[label for label, _ in PAUSE_CHOICES],
                           width=26)
        box.grid(row=1, column=0, sticky="w", pady=(2, 10))
        ttk.Label(body, text="It turns back on by itself when the time is "
                  "up.", style="Muted.TLabel").grid(row=2, column=0,
                                                    sticky="w")
        self.initial_focus = box

    def collect(self):
        return dict(PAUSE_CHOICES).get(self.var.get(), 30)


class RequestDialog(Dialog):
    """The child asks a parent for something. `submit(kind, detail, minutes,
    note)` saves it and returns an error message, or None when it worked."""
    ok_text = "Send"

    def __init__(self, parent, submit):
        self.submit = submit
        super().__init__(parent, "Ask a Parent")

    def build(self, body):
        ttk.Label(body, text="What would you like to ask for?").grid(
            row=0, column=0, columnspan=2, sticky="w")
        self.kind_var = tk.StringVar(value=REQUEST_KINDS["time"])
        kind = ttk.Combobox(body, textvariable=self.kind_var,
                            state="readonly", width=28,
                            values=list(REQUEST_KINDS.values()))
        kind.grid(row=1, column=0, columnspan=2, sticky="w", pady=(2, 10))
        kind.bind("<<ComboboxSelected>>", lambda e: self._sync())

        ttk.Label(body, text="App or website name").grid(
            row=2, column=0, columnspan=2, sticky="w")
        self.detail_var = tk.StringVar()
        self.detail = ttk.Entry(body, textvariable=self.detail_var, width=32)
        self.detail.grid(row=3, column=0, columnspan=2, sticky="we",
                         pady=(2, 10))

        ttk.Label(body, text="How much more time").grid(
            row=4, column=0, columnspan=2, sticky="w")
        self.min_var = tk.StringVar(value="30 minutes")
        self.minutes = ttk.Combobox(
            body, textvariable=self.min_var, state="readonly", width=14,
            values=[f"{m} minutes" for m in TIME_REQUEST_CHOICES])
        self.minutes.grid(row=5, column=0, sticky="w", pady=(2, 10))

        ttk.Label(body, text="Message for your parent (optional)").grid(
            row=6, column=0, columnspan=2, sticky="w")
        self.note_var = tk.StringVar()
        ttk.Entry(body, textvariable=self.note_var, width=32).grid(
            row=7, column=0, columnspan=2, sticky="we", pady=2)
        self._sync()
        self.initial_focus = kind

    def _kind_key(self):
        text = self.kind_var.get()
        return next((k for k, v in REQUEST_KINDS.items() if v == text),
                    "time")

    def _sync(self):
        is_time = self._kind_key() == "time"
        self.detail.configure(state="disabled" if is_time else "normal")
        self.minutes.configure(state="disabled" if not is_time
                               else "readonly")

    def validate(self):
        kind = self._kind_key()
        try:
            minutes = int(self.min_var.get().split()[0])
        except (ValueError, IndexError):
            minutes = 0
        error = self.submit(kind, self.detail_var.get(), minutes,
                            self.note_var.get())
        if error:
            # Notify
            messagebox.showerror(APP_NAME, error, parent=self)
            return False
        return True

    def collect(self):
        return True


class ReviewDialog(Dialog):
    """Waiting requests, each with Approve / Deny / Decide later. result =
    {request id: "approve" or "deny"} for the ones that were decided."""
    ok_text = "Apply"
    SHOW = 12

    def __init__(self, parent, requests):
        self.requests = requests
        self.choices = {}
        super().__init__(parent, "Review Requests")

    def build(self, body):
        if not self.requests:
            ttk.Label(body, text="No requests are waiting.").pack(padx=20,
                                                                  pady=20)
            return
        ttk.Label(body, text="Choose what to do with each request. The "
                  "child is told the result on their computer.",
                  style="Muted.TLabel", wraplength=520,
                  justify="left").pack(anchor="w", pady=(0, 8))
        holder = ttk.Frame(body)
        holder.pack(fill="both", expand=True)
        canvas = tk.Canvas(holder, bg=BG, highlightthickness=0, width=540,
                           height=min(len(self.requests), self.SHOW) * 74)
        bar = ttk.Scrollbar(holder, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=bar.set)
        inner = ttk.Frame(canvas)
        window = canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: canvas.configure(
            scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfigure(window, width=e.width))
        canvas.pack(side="left", fill="both", expand=True)
        if len(self.requests) > self.SHOW:
            bar.pack(side="right", fill="y")
            canvas.bind("<Enter>", lambda e: canvas.bind_all(
                "<MouseWheel>",
                lambda ev: canvas.yview_scroll(-1 if ev.delta > 0 else 1,
                                               "units")))
            canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))
            self.bind("<Destroy>", lambda e: canvas.unbind_all("<MouseWheel>")
                      if e.widget is self else None)
        for r in self.requests:
            card = ttk.Frame(inner, style="Card.TFrame", padding=10)
            card.pack(fill="x", pady=(0, 6))
            ttk.Label(card, text=Data.describe_request(r),
                      style="H2.TLabel").pack(anchor="w")
            extra = r["created"] + (f"  -  \"{r['note']}\"" if r["note"]
                                    else "")
            ttk.Label(card, text=extra, style="CardText.TLabel",
                      wraplength=480, justify="left").pack(anchor="w")
            row = ttk.Frame(card, style="Inner.TFrame")
            row.pack(anchor="w", pady=(6, 0))
            var = tk.StringVar(value="later")
            self.choices[r["id"]] = var
            for value, text in (("approve", "Approve"), ("deny", "Deny"),
                                ("later", "Decide later")):
                ttk.Radiobutton(row, text=text, value=value, variable=var,
                                style="Card.TRadiobutton").pack(
                    side="left", padx=(0, 14))

    def collect(self):
        return {rid: var.get() for rid, var in self.choices.items()
                if var.get() in ("approve", "deny")}


class CouponPickDialog(Dialog):
    """Pick one unused coupon. result = its code."""
    ok_text = "Redeem"

    def __init__(self, parent, coupons):
        self.coupons = coupons
        super().__init__(parent, "Redeem a coupon")

    def build(self, body):
        ttk.Label(body, text="Choose a coupon to use:").pack(anchor="w",
                                                             pady=(0, 6))
        wrap, self.tree = make_tree(body, [
            ("code", "Code", 170, "w"), ("minutes", "Minutes", 80, "w"),
            ("note", "Note", 200, "w")], height=min(len(self.coupons), 6))
        wrap.pack(fill="both", expand=True)
        self.tree.configure(selectmode="browse")
        for i, c in enumerate(self.coupons):
            self.tree.insert("", "end", iid=str(i),
                             values=(c["code"], c["minutes"], c["note"]))
        if self.coupons:
            self.tree.selection_set("0")
        self.initial_focus = self.tree

    def validate(self):
        if not self.tree.selection():
            # Notify
            messagebox.showinfo(APP_NAME, "Select a coupon first.",
                                parent=self)
            return False
        return True

    def collect(self):
        return self.coupons[int(self.tree.selection()[0])]["code"]


class ParentDialog(Dialog):
    """Username, password and role for a parent account. Pass `username` to
    reset the password of an existing parent (the name is then fixed and no
    role is asked for)."""

    def __init__(self, parent, title, existing_names, username=""):
        self.existing = {n.lower() for n in existing_names}
        self.fixed_name = username
        super().__init__(parent, title)

    def build(self, body):
        ttk.Label(body, text="Username").grid(row=0, column=0, sticky="w")
        self.user_var = tk.StringVar(value=self.fixed_name)
        user = ttk.Entry(body, textvariable=self.user_var, width=30,
                         state="disabled" if self.fixed_name else "normal")
        user.grid(row=1, column=0, sticky="we", pady=(2, 10))
        ttk.Label(body, text="Password (at least 6 characters)").grid(
            row=2, column=0, sticky="w")
        self.pw_var = tk.StringVar()
        pw = ttk.Entry(body, textvariable=self.pw_var, show="\u2022",
                       width=30)
        pw.grid(row=3, column=0, sticky="we", pady=(2, 10))
        ttk.Label(body, text="Confirm password").grid(
            row=4, column=0, sticky="w")
        self.pw2_var = tk.StringVar()
        ttk.Entry(body, textvariable=self.pw2_var, show="\u2022",
                  width=30).grid(row=5, column=0, sticky="we", pady=(2, 4))
        self.role_var = tk.StringVar(value="Complete")
        if not self.fixed_name:
            ttk.Label(body, text="Role").grid(row=6, column=0, sticky="w",
                                              pady=(8, 0))
            box = ttk.Combobox(body, textvariable=self.role_var,
                               values=list(ROLES), state="readonly",
                               width=28)
            box.grid(row=7, column=0, sticky="we", pady=(2, 4))
            self.role_help = tk.StringVar()
            ttk.Label(body, textvariable=self.role_help,
                      style="Muted.TLabel", wraplength=300,
                      justify="left").grid(row=8, column=0, sticky="w")
            box.bind("<<ComboboxSelected>>", self._role_changed)
            self._role_changed()
        self.initial_focus = pw if self.fixed_name else user

    def _role_changed(self, event=None):
        self.role_help.set(ROLE_HELP.get(self.role_var.get(), ""))

    def validate(self):
        name = self.user_var.get().strip()
        if not name:
            # Notify
            messagebox.showerror(APP_NAME, "Enter a username.", parent=self)
            return False
        if not self.fixed_name and name.lower() in self.existing:
            # Notify
            messagebox.showerror(APP_NAME, "That username is already used.",
                                 parent=self)
            return False
        if len(self.pw_var.get()) < 6:
            # Notify
            messagebox.showerror(APP_NAME, "The password must be at least "
                                 "6 characters.", parent=self)
            return False
        if self.pw_var.get() != self.pw2_var.get():
            # Notify
            messagebox.showerror(APP_NAME, "The two passwords don't match.",
                                 parent=self)
            return False
        return True

    def collect(self):
        return (self.user_var.get().strip(), self.pw_var.get(),
                self.role_var.get())


class RoleDialog(Dialog):
    """Pick a new role for a parent. result = 'Lite' / 'Complete' / 'Child'."""

    def __init__(self, parent, name, current):
        self.name, self.current = name, current
        super().__init__(parent, f"Change Role: {name}")

    def build(self, body):
        ttk.Label(body, text="Role").grid(row=0, column=0, sticky="w")
        self.role_var = tk.StringVar(value=self.current)
        box = ttk.Combobox(body, textvariable=self.role_var,
                           values=list(ROLES), state="readonly", width=28)
        box.grid(row=1, column=0, sticky="we", pady=(2, 4))
        self.role_help = tk.StringVar()
        ttk.Label(body, textvariable=self.role_help, style="Muted.TLabel",
                  wraplength=300, justify="left").grid(row=2, column=0,
                                                       sticky="w")
        box.bind("<<ComboboxSelected>>", self._changed)
        self._changed()

    def _changed(self, event=None):
        self.role_help.set(ROLE_HELP.get(self.role_var.get(), ""))

    def collect(self):
        return self.role_var.get()


class ActivateKeyDialog(Dialog):
    """Enter a key to activate. It must be in the key list and not expired
    (the built-in key always works). result = the key string."""
    ok_text = "Activate"

    def __init__(self, parent, data):
        self.data = data
        super().__init__(parent, "Activate Key")

    def build(self, body):
        ttk.Label(body, text="Activation key").grid(row=0, column=0,
                                                     sticky="w")
        self.key_var = tk.StringVar()
        key = ttk.Entry(body, textvariable=self.key_var, width=30)
        key.grid(row=1, column=0, sticky="we", pady=(2, 8))
        ttk.Label(body, text="Keys and their end dates are managed with "
                  "Ctrl+Shift+A on this tab.", style="Muted.TLabel",
                  wraplength=300, justify="left").grid(row=2, column=0,
                                                       sticky="w")
        self.initial_focus = key

    def validate(self):
        ok, _, error = self.data.validate_activation(self.key_var.get())
        if not ok:
            # Notify
            messagebox.showerror(APP_NAME, error or "That key is not "
                                 "correct.", parent=self)
            return False
        return True

    def collect(self):
        return self.key_var.get().strip()


class KeyEntryDialog(Dialog):
    """One key and its end date, for the key manager.
    result = {"key", "expiry"} ("" expiry = no end date)."""

    def __init__(self, parent, key="", expiry=""):
        self._key, self._expiry = key, expiry
        super().__init__(parent, "Key" if key else "New Key")

    def build(self, body):
        ttk.Label(body, text="Key").grid(row=0, column=0, sticky="w")
        self.key_var = tk.StringVar(value=self._key)
        key = ttk.Entry(body, textvariable=self.key_var, width=30)
        key.grid(row=1, column=0, sticky="we", pady=(2, 10))
        self.no_end = tk.BooleanVar(value=not self._expiry)
        ttk.Checkbutton(body, text="No end date (never expires)",
                        variable=self.no_end, command=self._toggle).grid(
            row=2, column=0, sticky="w", pady=(0, 2))
        ttk.Label(body, text="Expires on (YYYY-MM-DD)").grid(
            row=3, column=0, sticky="w")
        self.date_var = tk.StringVar(value=self._expiry or today_str())
        self.date_entry = ttk.Entry(body, textvariable=self.date_var,
                                    width=16)
        self.date_entry.grid(row=4, column=0, sticky="w", pady=(2, 4))
        self._toggle()
        self.initial_focus = key

    def _toggle(self):
        self.date_entry.configure(
            state="disabled" if self.no_end.get() else "normal")

    def validate(self):
        if not self.key_var.get().strip():
            # Notify
            messagebox.showerror(APP_NAME, "Enter a key.", parent=self)
            return False
        if self.no_end.get():
            return True
        try:
            datetime.date.fromisoformat(self.date_var.get().strip())
        except ValueError:
            # Notify
            messagebox.showerror(APP_NAME, "Enter the end date as "
                                 "YYYY-MM-DD, for example 2027-01-31.",
                                 parent=self)
            return False
        return True

    def collect(self):
        return {"key": self.key_var.get().strip(),
                "expiry": "" if self.no_end.get()
                else self.date_var.get().strip()}


class KeyManagerDialog(Dialog):
    """Ctrl+Shift+A: make and edit as many keys and end dates as you like.
    result = the full list of {"key", "expiry"} entries."""
    ok_text = "Save"

    def __init__(self, parent, entries):
        self.entries = [{"key": e.get("key", ""),
                         "expiry": e.get("expiry", "")} for e in entries]
        super().__init__(parent, "Activation Keys")

    def build(self, body):
        ttk.Label(body, text="Each key has its own end date. A key with no "
                  "end date never expires.", style="Muted.TLabel",
                  wraplength=420, justify="left").grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))
        wrap, self.tree = make_tree(body, [
            ("key", "Key", 240, "w"), ("expiry", "Expires", 140, "w")],
            height=7)
        wrap.grid(row=1, column=0, columnspan=3, sticky="nsew")
        ttk.Button(body, text="Add", style="Accent.TButton",
                   command=self._add).grid(row=2, column=0, sticky="w",
                                           pady=(8, 0))
        ttk.Button(body, text="Edit", command=self._edit).grid(
            row=2, column=1, sticky="w", pady=(8, 0), padx=6)
        ttk.Button(body, text="Remove", command=self._remove).grid(
            row=2, column=2, sticky="w", pady=(8, 0))
        self._refresh()

    def _refresh(self):
        rebuild_tree(self.tree, [
            (str(i), (e["key"], e["expiry"] or "No end date"), ())
            for i, e in enumerate(self.entries)])

    def _add(self):
        dlg = KeyEntryDialog(self)
        if dlg.result:
            self.entries.append(dlg.result)
            self._refresh()

    def _edit(self):
        sel = self.tree.selection()
        if len(sel) != 1:
            # Notify
            messagebox.showinfo(APP_NAME, "Select one key first.",
                                parent=self)
            return
        i = int(sel[0])
        dlg = KeyEntryDialog(self, self.entries[i]["key"],
                             self.entries[i]["expiry"])
        if dlg.result:
            self.entries[i] = dlg.result
            self._refresh()

    def _remove(self):
        for i in sorted((int(s) for s in self.tree.selection()),
                        reverse=True):
            del self.entries[i]
        self._refresh()

    def collect(self):
        return self.entries


class AppDialog(Dialog):
    def __init__(self, parent, title, name="", minutes=60, lock_name=False):
        self.init_name = name
        self.init_minutes = minutes
        self.lock_name = lock_name
        super().__init__(parent, title)

    def build(self, body):
        ttk.Label(body, text="App name (for example Game.exe)").grid(
            row=0, column=0, sticky="w")
        self.name_var = tk.StringVar(value=self.init_name)
        name_entry = ttk.Entry(
            body, textvariable=self.name_var, width=32,
            state="disabled" if self.lock_name else "normal")
        name_entry.grid(row=1, column=0, sticky="we", pady=(2, 10))

        ttk.Label(body, text="Daily limit (minutes)").grid(
            row=2, column=0, sticky="w")
        self.min_var = tk.StringVar(value=str(self.init_minutes))
        minutes = ttk.Spinbox(body, from_=5, to=1440, increment=5, width=8,
                              textvariable=self.min_var)
        minutes.grid(row=3, column=0, sticky="w", pady=2)
        self.initial_focus = minutes if self.lock_name else name_entry

    def validate(self):
        if not self.name_var.get().strip():
            # Notify
            messagebox.showerror(APP_NAME, "Enter an app name.", parent=self)
            return False
        try:
            value = int(self.min_var.get())
        except ValueError:
            value = 0
        if not 1 <= value <= 1440:
            # Notify
            messagebox.showerror(
                APP_NAME, "Enter a limit between 1 and 1440 minutes.",
                parent=self)
            return False
        return True

    def collect(self):
        return self.name_var.get().strip(), int(self.min_var.get())


class CouponDialog(Dialog):
    def build(self, body):
        ttk.Label(body, text="Bonus minutes").grid(row=0, column=0,
                                                   sticky="w")
        self.min_var = tk.StringVar(value="15")
        minutes = ttk.Spinbox(body, from_=5, to=480, increment=5, width=8,
                              textvariable=self.min_var)
        minutes.grid(row=1, column=0, sticky="w", pady=(2, 10))

        ttk.Label(body, text="Note (optional)").grid(row=2, column=0,
                                                     sticky="w")
        self.note_var = tk.StringVar()
        ttk.Entry(body, textvariable=self.note_var, width=32).grid(
            row=3, column=0, sticky="we", pady=2)
        self.initial_focus = minutes

    def validate(self):
        try:
            value = int(self.min_var.get())
        except ValueError:
            value = 0
        if not 1 <= value <= 480:
            # Notify
            messagebox.showerror(
                APP_NAME, "Enter between 1 and 480 minutes.", parent=self)
            return False
        return True

    def collect(self):
        return int(self.min_var.get()), self.note_var.get().strip()


class CountdownWindow(tk.Toplevel):
    """Opens by itself, above everything, when about a minute of screen time
    is left. Counts down, and offers One More Minute (a few times a day) or
    redeeming a coupon. It closes itself when time is added."""

    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.title("Time is almost up")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.attributes("-topmost", True)
        body = ttk.Frame(self, padding=(36, 26))
        body.pack()
        ttk.Label(body, text="Time is almost up", style="H1.TLabel").pack()
        self.clock_var = tk.StringVar(value="1:00")
        ttk.Label(body, textvariable=self.clock_var,
                  font=(FONT, 54, "bold"), foreground=OLIVE).pack(pady=6)
        ttk.Label(body, text="Your screen time for today is about to run "
                  "out. Save your work.", style="Muted.TLabel").pack()
        row = ttk.Frame(body)
        row.pack(pady=(18, 4))
        self.more_btn = ttk.Button(row, text="One More Minute",
                                   style="Accent.TButton",
                                   command=self.one_more_minute)
        self.more_btn.pack(side="left", padx=(0, 10))
        ttk.Button(row, text="Redeem a coupon",
                   command=self.redeem).pack(side="left")
        self.note_var = tk.StringVar()
        ttk.Label(body, textvariable=self.note_var,
                  style="Muted.TLabel").pack()
        self._job = None
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.update_idletasks()
        x = (self.winfo_screenwidth() - self.winfo_width()) // 2
        y = (self.winfo_screenheight() - self.winfo_height()) // 3
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        self.deiconify()
        self.bell()
        try:
            self.focus_force()
        except tk.TclError:
            pass
        self._tick()

    def graces_left(self):
        return max(0, GRACE_MINUTES_PER_DAY - self.app.data.grace_used)

    def one_more_minute(self):
        d = self.app.data
        if self.graces_left() <= 0:
            return
        d.grace_used += 1
        d.bonus_min += 1
        d.log("One More Minute", f"+1 min ({self.graces_left()} left today)")
        self.app._on_tab_changed()
        self.close()

    def redeem(self):
        d = self.app.data
        coupons = d.unused_coupons()
        if not coupons:
            # Notify
            messagebox.showinfo(APP_NAME, "You don't have any coupons to "
                                "redeem.", parent=self)
            return
        dlg = CouponPickDialog(self, coupons)
        if dlg.result and d.redeem_coupon(dlg.result) is not None:
            self.app._on_tab_changed()
            self.close()

    def close(self):
        if self._job is not None:
            try:
                self.after_cancel(self._job)
            except tk.TclError:
                pass
            self._job = None
        if self.app.countdown is self:
            self.app.countdown = None
        try:
            self.destroy()
        except tk.TclError:
            pass

    def _tick(self):
        left = self.app.limit_guard.seconds_left(self.app.data)
        if left is None or left > COUNTDOWN_SECONDS + 1:
            self.close()
            return
        secs = max(0, math.ceil(left))
        self.clock_var.set(f"{secs // 60}:{secs % 60:02d}")
        n = self.graces_left()
        if n <= 0:
            self.more_btn.configure(state="disabled")
            self.note_var.set("No extra minutes are left today.")
        else:
            self.note_var.set(f"{n} extra minute(s) left today.")
        if left <= 0:
            self.clock_var.set("0:00")
            self.note_var.set("Time is up.")
            self._job = self.after(2500, self.close)
            return
        if self.grab_current() is None:
            self.attributes("-topmost", True)
            self.lift()
        self._job = self.after(250, self._tick)


SHIELD_GREEN = "#1f8a5b"
SHIELD_GREEN_EDGE = "#12382a"
SHIELD_RED = "#d9534f"
SHIELD_RED_EDGE = "#8b1a1a"
SHIELD_AMBER = "#e8920c"
SHIELD_AMBER_EDGE = "#8a4f00"
SHIELD_STATES = {
    "on": (SHIELD_GREEN, SHIELD_GREEN_EDGE, GREEN),
    "warn": (SHIELD_AMBER, SHIELD_AMBER_EDGE, AMBER_TEXT),
    "ask": (SHIELD_AMBER, SHIELD_AMBER_EDGE, AMBER_TEXT),
    "ask_off": (SHIELD_AMBER, SHIELD_AMBER_EDGE, RED),
    "off": (SHIELD_RED, SHIELD_RED_EDGE, RED),
}
_SHIELD_CORNERS = [(-44, -46), (0, -58), (44, -46), (46, 6), (30, 36),
                   (0, 58), (-30, 36), (-46, 6)]
SHIELD_ROUNDNESS = 0.06


def _tighten(corners, r):
    """Replace each corner with two points close to it so the smoothed
    outline hugs the corner instead of cutting across it."""
    out = []
    n = len(corners)
    for i in range(n):
        px, py = corners[i - 1]
        vx, vy = corners[i]
        nx, ny = corners[(i + 1) % n]
        out.append((vx + (px - vx) * r, vy + (py - vy) * r))
        out.append((vx + (nx - vx) * r, vy + (ny - vy) * r))
    return out


SHIELD_SHAPE = _tighten(_SHIELD_CORNERS, SHIELD_ROUNDNESS)
CHECK_SHAPE = [(-20, 2), (-7, 15), (21, -15)]
CROSS_SHAPE = [[(-15, -15), (15, 15)], [(15, -15), (-15, 15)]]


def _mix(c1, c2, t):
    """Blend two #rrggbb colors; t=0 gives c1, t=1 gives c2."""
    t = max(0.0, min(1.0, t))
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * t)
                                   for x, y in zip(a, b))


def _ease(t):
    return t * t * (3 - 2 * t)


def _back(x):
    """Ease-out with a small overshoot (0 -> 1)."""
    x = max(0.0, min(1.0, x))
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


def _partial(points, fraction):
    """The first `fraction` of a polyline's length, as a list of points."""
    fraction = max(0.0, min(1.0, fraction))
    lengths = [math.dist(points[i], points[i + 1])
               for i in range(len(points) - 1)]
    remaining = fraction * sum(lengths)
    out = [points[0]]
    for (x1, y1), (x2, y2), seg in zip(points, points[1:], lengths):
        if remaining >= seg:
            out.append((x2, y2))
            remaining -= seg
        else:
            k = remaining / seg if seg else 0
            out.append((x1 + (x2 - x1) * k, y1 + (y2 - y1) * k))
            break
    return out


class ShieldWidget(tk.Canvas):
    """Clickable shield. Green with a check mark when protection is on, amber
    with a yellow exclamation mark when a request is waiting for a parent
    (whether protection is on or off), amber with a white exclamation mark
    when it is on but SmartSafe (which the
    subscription includes) is off, red with an X when protection is off.
    Animates when it changes."""

    W, H = 150, 180
    ANIM_SECONDS = 0.7

    def __init__(self, parent, state="on", command=None, captions=True):
        super().__init__(parent, width=self.W,
                         height=self.H if captions else 140, bg="white",
                         highlightthickness=0,
                         cursor="hand2" if command else "arrow",
                         takefocus=1 if command else 0)
        self.captions = captions
        self.state = state
        self.from_state = state
        self.command = command
        self.anim_start = None
        self.shake_start = None
        self.hover = 0.0
        self.hover_target = 0.0
        self._job = None
        self._dirty = True
        self._was_busy = False
        self.bind("<Map>", lambda e: setattr(self, "_dirty", True))
        self.bind("<Button-1>", self._click)
        self.bind("<Key-space>", self._click)
        self.bind("<Return>", self._click)
        self.bind("<Enter>", lambda e: setattr(self, "hover_target", 1.0))
        self.bind("<Leave>", lambda e: setattr(self, "hover_target", 0.0))
        self.bind("<Destroy>", self._stop)
        self._frame()

    def set_state(self, state, animate=True):
        if state == self.state:
            return
        self.from_state = self.state
        self.state = state
        self.anim_start = time.monotonic() if animate else None
        self._dirty = True

    def shake(self):
        """Wiggle sideways (used when a change is refused)."""
        self.shake_start = time.monotonic()

    def _click(self, event=None):
        self.focus_set()
        if self.command:
            self.command()

    def _stop(self, event=None):
        if self._job is not None:
            try:
                self.after_cancel(self._job)
            except tk.TclError:
                pass
            self._job = None

    def _busy(self):
        """True while something is moving and needs smooth frames."""
        return (self.anim_start is not None or self.shake_start is not None
                or abs(self.hover_target - self.hover) > 0.005)

    def _frame(self):
        """Redraws only when something changed or is moving (about 30 times a
        second), and checks again a few times a second otherwise. Nothing is
        drawn while the window is minimized."""
        try:
            busy = self._busy()
            if busy or self._dirty or self._was_busy:
                if self.winfo_viewable():
                    try:
                        self._draw()
                    except tk.TclError:
                        raise
                    except Exception:
                        self.anim_start = self.shake_start = None
                    self._dirty = False
                else:
                    self._dirty = True
            self._was_busy = busy
            self._job = self.after(33 if busy else 250, self._frame)
        except tk.TclError:
            self._job = None

    @staticmethod
    def _points(cx, cy, scale, shape=SHIELD_SHAPE):
        flat = []
        for x, y in shape:
            flat += [cx + x * scale, cy + y * scale]
        return flat

    def _bang(self, cx, cy, s, width, grow, colour, extra):
        """An exclamation mark (a stem and a dot)."""
        bottom = -26 + 34 * min(1.0, grow)
        self.create_line(cx, cy - 26 * s, cx, cy + bottom * s,
                         fill=colour, width=width + 2 + extra,
                         capstyle="round")
        r = (width / 2 + 1.5 + extra / 2) * min(1.0, grow)
        self.create_oval(cx - r, cy + 27 * s - r, cx + r, cy + 27 * s + r,
                         fill=colour, outline=colour)

    def _icon(self, state, cx, cy, s, width, grow):
        if state == "on":
            pts = _partial(CHECK_SHAPE, min(1.0, grow))
            flat = []
            for x, y in pts:
                flat += [cx + x * s, cy + y * s]
            self.create_line(*flat, fill="white", width=width,
                             capstyle="round", joinstyle="round")
        elif state in ("ask", "ask_off"):
            self._bang(cx, cy, s, width, grow, SHIELD_AMBER_EDGE, 5)
            self._bang(cx, cy, s, width, grow, "#ffe14d", 0)
        elif state == "warn":
            self._bang(cx, cy, s, width, grow, "white", 0)
        else:
            for (x1, y1), (x2, y2) in CROSS_SHAPE:
                self.create_line(cx + x1 * s, cy + y1 * s,
                                 cx + x2 * s, cy + y2 * s,
                                 fill="white", width=width,
                                 capstyle="round")

    def _draw(self):
        now = time.monotonic()
        self.delete("all")

        animating, t = False, 1.0
        if self.anim_start is not None:
            t = (now - self.anim_start) / self.ANIM_SECONDS
            if t >= 1.0:
                self.anim_start, t = None, 1.0
            else:
                animating = True
        e = _ease(t) if animating else 1.0

        pop = 1 + 0.12 * math.sin(math.pi * t) if animating else 1.0
        self.hover += (self.hover_target - self.hover) * 0.25
        scale = pop * (1 + 0.05 * self.hover)

        dx = 0.0
        if self.shake_start is not None:
            k = (now - self.shake_start) / 0.45
            if k >= 1.0:
                self.shake_start = None
            else:
                dx = 10 * (1 - k) * math.sin(k * math.pi * 6)

        cx, cy = self.W / 2 + dx, 76
        f_fill, f_edge, f_txt = SHIELD_STATES[self.from_state]
        t_fill, t_edge, t_txt = SHIELD_STATES[self.state]
        fill = _mix(f_fill, t_fill, e)
        edge = _mix(f_edge, t_edge, e)
        caption_colour = _mix(f_txt, t_txt, e)

        self.create_polygon(self._points(cx, cy, scale), smooth=True,
                            fill=fill, outline=edge, width=4,
                            joinstyle="miter")
        self.create_polygon(self._points(cx, cy, scale * 0.8), smooth=True,
                            fill="", outline=_mix(fill, "#ffffff", 0.5),
                            width=2, joinstyle="miter")

        if animating and t < 0.4:
            icon_state, grow = self.from_state, 1 - t / 0.4
        elif animating:
            icon_state, grow = self.state, _back((t - 0.4) / 0.6)
        else:
            icon_state, grow = self.state, 1.0
        s = scale * grow
        width = max(1, round(9 * scale))
        if s > 0.03:
            self._icon(icon_state, cx, cy, s, width, grow)

        if not self.captions:
            return
        label = self.state if (not animating or t >= 0.5) else self.from_state
        self.create_text(self.W / 2, 150,
                         text="PROTECTION OFF"
                         if label in ("off", "ask_off") else "PROTECTION ON",
                         fill=caption_colour, font=(FONT, 11, "bold"))
        self.create_text(self.W / 2, 168,
                         text={"on": "Click to turn off",
                               "ask": "A request is waiting",
                               "ask_off": "A request is waiting",
                               "warn": "SmartSafe is off",
                               "off": "Click to turn on"}[label],
                         fill=MUTED, font=(FONT, 9))


class SlideSwitch(tk.Canvas):
    """A switch you slide with the mouse (clicking does nothing). The track
    fades smoothly from red to green as the knob moves. `command(new_on)`
    is called when you let go on the other side; it returns True to accept
    the change, or False to send the knob back. The track is red when off,
    amber at the halfway point and green when on."""

    W, H, PAD = 170, 40, 4

    def __init__(self, parent, on=False, command=None):
        super().__init__(parent, width=self.W, height=self.H, bg="white",
                         highlightthickness=0, cursor="hand2")
        self.on = on
        self.pos = 1.0 if on else 0.0
        self.target = self.pos
        self.command = command
        self.dragging = False
        self._grab = 0.0
        self._job = None
        self.bind("<Button-1>", self._press)
        self.bind("<B1-Motion>", self._drag)
        self.bind("<ButtonRelease-1>", self._release)
        self.bind("<Destroy>", self._stop)
        self._draw()

    @property
    def _d(self):
        return self.H - 2 * self.PAD

    @property
    def _travel(self):
        return self.W - 2 * self.PAD - self._d

    def _knob_x(self):
        return self.PAD + self._d / 2 + self.pos * self._travel

    def set_value(self, on, animate=True):
        """Match the switch to the real setting (ignored mid-slide)."""
        if self.dragging:
            return
        self.on = on
        self.target = 1.0 if on else 0.0
        if animate:
            self._animate()
        else:
            self.pos = self.target
            self._draw()

    def _press(self, event):
        grab = event.x - self._knob_x()
        if abs(grab) <= self._d / 2 + 3 and abs(event.y - self.H / 2) <= \
                self._d / 2 + 3:
            self.dragging = True
            self._grab = grab
            self._stop()

    def _drag(self, event):
        if not self.dragging:
            return
        x = event.x - self._grab - self.PAD - self._d / 2
        self.pos = min(1.0, max(0.0, x / self._travel))
        self._draw()

    def _release(self, event):
        if not self.dragging:
            return
        self.dragging = False
        new_on = self.pos >= 0.5
        if new_on != self.on:
            accepted = True
            if self.command:
                accepted = bool(self.command(new_on))
            if accepted:
                self.on = new_on
        self.target = 1.0 if self.on else 0.0
        self._animate()

    def _stop(self, event=None):
        if self._job is not None:
            try:
                self.after_cancel(self._job)
            except tk.TclError:
                pass
            self._job = None

    def _animate(self):
        self._stop()
        try:
            self.pos += (self.target - self.pos) * 0.3
            if abs(self.target - self.pos) < 0.005:
                self.pos = self.target
            self._draw()
            if self.pos != self.target:
                self._job = self.after(16, self._animate)
        except tk.TclError:
            self._job = None

    @staticmethod
    def track_colour(pos):
        """Red -> amber (halfway) -> green."""
        if pos < 0.5:
            return _mix(SHIELD_RED, SHIELD_AMBER, pos / 0.5)
        return _mix(SHIELD_AMBER, SHIELD_GREEN, (pos - 0.5) / 0.5)

    def _draw(self):
        self.delete("all")
        w, h = self.W, self.H
        mid = h / 2
        track = self.track_colour(self.pos)
        self.create_oval(1, 1, h - 1, h - 1, fill=track, outline=track)
        self.create_oval(w - h + 1, 1, w - 1, h - 1, fill=track,
                         outline=track)
        self.create_rectangle(h / 2, 1, w - h / 2, h - 1, fill=track,
                              outline=track)
        if self.pos >= 0.5:
            self.create_text(self.PAD + 26, mid, text="ON", fill="white",
                             font=(FONT, 10, "bold"))
        else:
            self.create_text(w - self.PAD - 28, mid, text="OFF",
                             fill="white", font=(FONT, 10, "bold"))
        x, r = self._knob_x(), self._d / 2
        self.create_oval(x - r, mid - r + 2, x + r, mid + r + 2,
                         fill=_mix(track, "#000000", 0.25), outline="")
        self.create_oval(x - r, mid - r, x + r, mid + r, fill="white",
                         outline="")


class Page(ttk.Frame):
    """Base class for notebook pages."""

    def __init__(self, parent, app):
        super().__init__(parent, padding=16)
        self.app = app
        self.data = app.data
        self.build()

    def build(self):
        pass

    def refresh(self):
        pass

    def authorize(self, allow_locked=False):
        return self.app.authorize(allow_locked)


class DashboardPage(Page):
    def build(self):
        ttk.Label(self, text="Dashboard", style="H1.TLabel").grid(
            row=0, column=0, columnspan=4, sticky="w")
        self.limit_note = tk.StringVar()
        ttk.Label(self, textvariable=self.limit_note,
                  style="Muted.TLabel").grid(
            row=1, column=0, columnspan=4, sticky="w", pady=(0, 12))

        self.card_vars = {}
        cards = [("used", "Screen time today"),
                 ("left", "Time remaining"),
                 ("blocked", "Blocked attempts")]
        for i, (key, label) in enumerate(cards):
            card = ttk.Frame(self, style="Card.TFrame", padding=14)
            card.grid(row=2, column=i, sticky="nsew",
                      padx=(0 if i == 0 else 8, 0))
            var = tk.StringVar(value="-")
            ttk.Label(card, textvariable=var, style="CardNum.TLabel").pack(
                anchor="w")
            ttk.Label(card, text=label, style="CardText.TLabel").pack(
                anchor="w")
            self.card_vars[key] = var
            self.columnconfigure(i, weight=1, uniform="cards")

        smart_card = ttk.Frame(self, style="Card.TFrame", padding=14)
        smart_card.grid(row=2, column=3, sticky="nsew", padx=(8, 0))
        self.smart_switch = SlideSwitch(
            smart_card, on=self._smartsafe_on(),
            command=self.set_smartsafe)
        self.smart_switch.pack(anchor="w")
        self.smart_hint = tk.StringVar()
        ttk.Label(smart_card, textvariable=self.smart_hint,
                  style="CardText.TLabel").pack(anchor="w", pady=(6, 0))
        self.columnconfigure(3, weight=1, uniform="cards")

        shield_card = ttk.Frame(self, style="Card.TFrame", padding=10)
        shield_card.grid(row=3, column=0, sticky="nsew", pady=(12, 0))
        self.shield = ShieldWidget(shield_card, state=self._shield_state(),
                                   command=self.toggle_protection)
        self.shield.pack()

        actions = ttk.Frame(self, style="Card.TFrame", padding=14)
        actions.grid(row=3, column=1, columnspan=3, sticky="nsew",
                     padx=(8, 0), pady=(12, 0))
        title_row = ttk.Frame(actions, style="Inner.TFrame")
        title_row.grid(row=0, column=0, columnspan=2, sticky="ew",
                       pady=(0, 8))
        ttk.Label(title_row, text="Quick Actions", style="H2.TLabel").pack(
            side="left")
        self.pause_text = tk.StringVar(value="Pause Internet")
        self.review_text = tk.StringVar(value="Review Requests")
        self.quick_frame = ttk.Frame(actions, style="Inner.TFrame")
        self.quick_frame.grid(row=1, column=0, columnspan=2, sticky="ew")
        self.quick_frame.columnconfigure(0, weight=1, uniform="quick")
        self.quick_frame.columnconfigure(1, weight=1, uniform="quick")
        ttk.Label(actions, text="Bonus time", style="H2.TLabel").grid(
            row=3, column=0, columnspan=2, sticky="w", pady=(16, 8))
        ttk.Button(actions, text="Add 30 min",
                   command=lambda: self.add_time(30)).grid(
            row=4, column=0, sticky="ew", padx=(0, 8))
        ttk.Button(actions, text="Add 1 hour",
                   command=lambda: self.add_time(60)).grid(
            row=4, column=1, sticky="ew")
        self._build_quick()
        actions.columnconfigure(0, weight=1, uniform="act")
        actions.columnconfigure(1, weight=1, uniform="act")

        head = ttk.Frame(self)
        head.grid(row=4, column=0, columnspan=4, sticky="ew", pady=(16, 6))
        ttk.Label(head, text="Recent Activity (see the Log tab for all of it)",
                  style="H1.TLabel", font=(FONT, 12, "bold")).pack(side="left")
        ttk.Button(head, text="Clear Log",
                   command=self.clear_log).pack(side="right")
        ttk.Button(head, text="Refresh", command=self.refresh).pack(
            side="right", padx=(0, 8))

        wrap, self.tree = make_tree(self, [
            ("time", "Time", 90, "w"),
            ("event", "Event", 200, "w"),
            ("target", "App / Website", 320, "w"),
            ("result", "Result", 110, "w"),
        ], height=8)
        wrap.grid(row=5, column=0, columnspan=4, sticky="nsew")
        self.rowconfigure(5, weight=1)

    def _build_quick(self):
        """Creates the (fixed) Quick Actions buttons."""
        for child in self.quick_frame.winfo_children():
            child.destroy()
        buttons = {"pause": (self.pause_text, self.toggle_pause),
                   "coupon": ("Add New Coupon", self.new_coupon),
                   "requests": (self.review_text, self.review_requests)}
        for n, key in enumerate(self.data.quick_actions):
            label, command = buttons[key]
            kw = ({"textvariable": label} if isinstance(label, tk.StringVar)
                  else {"text": label})
            ttk.Button(self.quick_frame, command=command, **kw).grid(
                row=n // 2, column=n % 2, sticky="ew", pady=(0, 8),
                padx=(0, 8) if n % 2 == 0 else 0)

    def new_coupon(self):
        if not self.authorize():
            return
        dlg = CouponDialog(self, "Create Coupon")
        if not dlg.result:
            return
        minutes, note = dlg.result
        code = self.data.add_coupon(minutes, note)
        self.app.set_status(f"Created coupon {code} (+{minutes} minutes).")
        self.refresh()

    def review_requests(self):
        if not self.authorize():
            return
        dlg = ReviewDialog(self, self.data.pending_requests())
        if not dlg.result:
            return
        messages = []
        for rid, choice in dlg.result.items():
            message = self.data.review_request(rid, choice == "approve")
            if message:
                messages.append(message)
        if messages:
            self.app.set_status(f"{len(messages)} request(s) answered. "
                                "The child is told on their computer.")
        self.app._on_tab_changed()

    def _smartsafe_on(self):
        return self.data.smartsafe_enabled

    def _shield_state(self):
        """ask / ask_off = a request is waiting for a parent (amber, whether
        protection is on or off); off = protection off; warn = protection is
        on but SmartSafe is switched off; on = everything running."""
        d = self.data
        if d.pending_requests():
            return "ask" if d.protection_effective else "ask_off"
        if not d.protection_effective:
            return "off"
        if not d.smartsafe_enabled:
            return "warn"
        return "on"

    def set_smartsafe(self, on):
        """Called when the switch is slid across. True = accepted."""
        if not self.authorize():
            return False
        self.data.smartsafe_enabled = on
        self.data.log("SmartSafe " + ("enabled" if on else "disabled"),
                      "All websites")
        self.app.set_status("SmartSafe turned " + ("on" if on else "off")
                            + ".")
        self.shield.set_state(self._shield_state())
        self.refresh()
        return True

    def toggle_protection(self):
        if not self.authorize():
            self.shield.shake()
            return
        on = not self.data.protection_enabled
        self.data.protection_enabled = on
        self.shield.set_state(self._shield_state())
        self.data.log("Protection " + ("enabled" if on else "disabled"),
                      "All devices")
        self.app.update_header()
        self.app.set_status(
            "Protection turned " + ("on" if on else "off") + ".")
        self.refresh()

    def toggle_pause(self):
        if not self.authorize():
            return
        d = self.data
        if d.internet_paused:
            d.internet_paused = False
            d.pause_until = 0.0
            d.log("Internet resumed", "All devices")
            self.app.set_status("Internet resumed.")
            self.refresh()
            return
        dlg = PauseDialog(self)
        if dlg.result is None:
            return
        minutes = dlg.result
        d.internet_paused = True
        d.pause_until = time.time() + minutes * 60 if minutes else 0.0
        span = f"for {minutes} minutes" if minutes else "until resumed"
        d.log("Internet paused", f"All devices ({span})")
        self.app.set_status(
            f"Internet paused {span}." + ("" if minutes else
                                          " Resume it here when ready."))
        self.refresh()

    def add_time(self, minutes):
        if not self.authorize():
            return
        self.data.bonus_min += minutes
        self.data.log("Bonus time added", f"+{minutes} min")
        self.app.set_status(f"Added {minutes} minutes of bonus time.")
        self.refresh()

    def clear_log(self):
        if not self.authorize():
            return
        # Notify
        if messagebox.askyesno(APP_NAME, "Clear the activity log?",
                               parent=self):
            self.data.activity.clear()
            self.app.set_status("Activity log cleared.")
            self.refresh()

    def refresh(self):
        d = self.data
        today = DAYS[datetime.date.today().weekday()]
        limit = d.limits[today]

        self.card_vars["used"].set(fmt_minutes(d.used_today_min))
        if limit["enabled"]:
            left = max(0, limit["minutes"] + d.bonus_min - d.used_today_min)
            self.card_vars["left"].set(fmt_minutes(left))
            note = (f"{today}'s limit: {fmt_minutes(limit['minutes'])}"
                    f"   |   Bonus time today: +{d.bonus_min} min")
        else:
            self.card_vars["left"].set("No limit")
            note = f"No time limit is set for {today}."
        self.limit_note.set(note)
        self.card_vars["blocked"].set(
            str(sum(1 for a in d.visible_activity()
                    if a[3] in ("Blocked", "Limited"))))

        self.shield.set_state(self._shield_state())
        self.smart_switch.set_value(self._smartsafe_on())
        self.smart_hint.set("SmartSafe - slide to turn "
                            + ("off" if d.smartsafe_enabled else "on"))
        if d.internet_paused:
            left = ""
            if d.pause_until:
                mins = max(1, math.ceil((d.pause_until - time.time()) / 60))
                left = f" ({mins} min left)"
            self.pause_text.set("Resume Internet" + left)
        else:
            self.pause_text.set("Pause Internet")
        waiting = len(d.pending_requests())
        self.review_text.set(f"Review Requests ({waiting})" if waiting
                             else "Review Requests")

        today_text = today_str()
        shown = []
        for i, row in enumerate(d.visible_activity()[:100]):
            tag = RESULT_TAGS.get(row[3], "")
            shown.append((str(i), (short_stamp(row[0], today_text),)
                          + tuple(row[1:]), (tag,) if tag else ()))
        rebuild_tree(self.tree, shown)


class TimeLimitsPage(Page):
    def build(self):
        ttk.Label(self, text="Time Limits", style="H1.TLabel").pack(
            anchor="w")
        ttk.Label(self, text="Set how much screen time is allowed each day.",
                  style="Muted.TLabel").pack(anchor="w", pady=(0, 12))

        card = ttk.Frame(self, style="Card.TFrame", padding=16)
        card.pack(fill="x")
        for c, text in enumerate(("Day", "Limit enabled", "Hours",
                                  "Minutes")):
            ttk.Label(card, text=text, style="H2.TLabel").grid(
                row=0, column=c, sticky="w", padx=(0, 28), pady=(0, 8))

        self.rows = {}
        for r, day in enumerate(DAYS, start=1):
            enabled = tk.BooleanVar()
            hours = tk.StringVar()
            mins = tk.StringVar()
            ttk.Label(card, text=day, style="CardBody.TLabel").grid(
                row=r, column=0, sticky="w", pady=3)
            ttk.Checkbutton(
                card, variable=enabled, style="Card.TCheckbutton",
                command=lambda d=day: self._sync_row(d)).grid(
                row=r, column=1, sticky="w")
            sp_h = ttk.Spinbox(card, from_=0, to=24, width=5,
                               textvariable=hours)
            sp_h.grid(row=r, column=2, sticky="w", padx=(0, 28))
            sp_m = ttk.Spinbox(card, from_=0, to=59, increment=5, width=5,
                               textvariable=mins)
            sp_m.grid(row=r, column=3, sticky="w")
            self.rows[day] = (enabled, hours, mins, sp_h, sp_m)

        bed = ttk.Frame(self, style="Card.TFrame", padding=16)
        bed.pack(fill="x", pady=(12, 0))
        ttk.Label(bed, text="Bedtime", style="H2.TLabel").grid(
            row=0, column=0, columnspan=5, sticky="w")
        self.bed_enabled = tk.BooleanVar()
        ttk.Checkbutton(bed, text="Lock the device overnight",
                        variable=self.bed_enabled,
                        style="Card.TCheckbutton").grid(
            row=1, column=0, columnspan=5, sticky="w", pady=6)
        self.bed_start = tk.StringVar()
        self.bed_end = tk.StringVar()
        ttk.Label(bed, text="From", style="CardBody.TLabel").grid(
            row=2, column=0, sticky="w")
        ttk.Entry(bed, textvariable=self.bed_start, width=8).grid(
            row=2, column=1, padx=8)
        ttk.Label(bed, text="to", style="CardBody.TLabel").grid(
            row=2, column=2)
        ttk.Entry(bed, textvariable=self.bed_end, width=8).grid(
            row=2, column=3, padx=8)
        ttk.Label(bed, text="24-hour time, HH:MM",
                  style="CardText.TLabel").grid(row=2, column=4, sticky="w")
        ttk.Label(bed, text="Screen time alerts (up to 3)",
                  style="CardBody.TLabel").grid(
            row=3, column=0, columnspan=2, sticky="w", pady=(10, 0))
        alert_row = ttk.Frame(bed, style="Card.TFrame")
        alert_row.grid(row=3, column=2, columnspan=3, sticky="w", padx=8,
                       pady=(10, 0))
        self.alert_vars = []
        for i in range(MAX_ALERTS):
            var = tk.StringVar()
            box = ttk.Combobox(alert_row, textvariable=var, width=11,
                               state="readonly",
                               values=["Off"] + [alert_label(m)
                                                 for m in ALERT_CHOICES])
            box.grid(row=0, column=i, padx=(0, 6))
            box.bind("<<ComboboxSelected>>", self.alerts_changed)
            self.alert_vars.append(var)
        ttk.Label(bed, text="Shown this long before time runs out. Anyone "
                  "can change these; no PIN needed.",
                  style="CardText.TLabel").grid(
            row=4, column=0, columnspan=5, sticky="w")

        bar = ttk.Frame(self)
        bar.pack(fill="x", pady=(14, 0))
        ttk.Button(bar, text="Copy Monday to All Days",
                   command=self.copy_monday).pack(side="left")
        ttk.Button(bar, text="Reset to Defaults",
                   command=self.reset).pack(side="left", padx=8)
        ttk.Button(bar, text="Save Changes", style="Accent.TButton",
                   command=self.save).pack(side="right")

        self.load()

    def alerts_changed(self, event=None):
        picked = []
        for var in self.alert_vars:
            text = var.get()
            if text and text != "Off":
                picked.append(int(text.split()[0]))
        self.data.warn_alerts = clean_alerts(picked)
        self.load_alerts()
        self.app.set_status(describe_alerts(self.data.warn_alerts))

    def load_alerts(self):
        alerts = self.data.warn_alerts
        for i, var in enumerate(self.alert_vars):
            var.set(alert_label(alerts[i]) if i < len(alerts) else "Off")

    def _sync_row(self, day):
        enabled, _, _, sp_h, sp_m = self.rows[day]
        state = "normal" if enabled.get() else "disabled"
        sp_h.configure(state=state)
        sp_m.configure(state=state)

    def load(self):
        for day, (enabled, hours, mins, _, _) in self.rows.items():
            entry = self.data.limits[day]
            enabled.set(entry["enabled"])
            hours.set(str(entry["minutes"] // 60))
            mins.set(str(entry["minutes"] % 60))
            self._sync_row(day)
        self.bed_enabled.set(self.data.bedtime["enabled"])
        self.bed_start.set(self.data.bedtime["start"])
        self.bed_end.set(self.data.bedtime["end"])
        self.load_alerts()

    def copy_monday(self):
        if not self.authorize():
            return
        enabled, hours, mins, _, _ = self.rows["Monday"]
        for day in DAYS[1:]:
            e, h, m, _, _ = self.rows[day]
            e.set(enabled.get())
            h.set(hours.get())
            m.set(mins.get())
            self._sync_row(day)
        self.app.set_status("Monday's limit copied to all days "
                            "(not saved yet).")

    def reset(self):
        if not self.authorize():
            return
        # Notify
        if messagebox.askyesno(APP_NAME, "Reset all time settings to the "
                               "defaults?", parent=self):
            self.data.reset_time_settings()
            self.load()
            self.app.set_status("Time settings reset to defaults.")

    def save(self):
        if not self.authorize():
            return
        new_limits = {}
        for day, (enabled, hours, mins, _, _) in self.rows.items():
            try:
                h = int(hours.get())
                m = int(mins.get())
            except ValueError:
                # Notify
                messagebox.showerror(
                    APP_NAME, f"Enter whole numbers for {day}.", parent=self)
                return
            if not (0 <= h <= 24 and 0 <= m <= 59) or h * 60 + m > 1440:
                # Notify
                messagebox.showerror(
                    APP_NAME, f"The limit for {day} must be 24 hours or "
                    "less.", parent=self)
                return
            new_limits[day] = {"enabled": enabled.get(),
                               "minutes": h * 60 + m}

        start, end = self.bed_start.get().strip(), self.bed_end.get().strip()
        if not (TIME_RE.match(start) and TIME_RE.match(end)):
            # Notify
            messagebox.showerror(
                APP_NAME, "Bedtime times must look like 21:00 (HH:MM, "
                "24-hour).", parent=self)
            return

        self.data.limits = new_limits
        self.data.bedtime = {"enabled": self.bed_enabled.get(),
                             "start": start, "end": end}
        self.data.log("Time limits saved", "All days")
        self.app.set_status("Time limits saved. The screen locks when "
                            "time runs out or at bedtime.")


class ListPage(Page):
    """Shared page for the Always Blocked / Always Allowed lists."""

    def __init__(self, parent, app, title, blurb, attr, other_attr,
                 other_name, row_tag, move_text):
        self.title_text = title
        self.blurb = blurb
        self.attr = attr
        self.other_attr = other_attr
        self.other_name = other_name
        self.row_tag = row_tag
        self.move_text = move_text
        super().__init__(parent, app)

    def items(self):
        return getattr(self.data, self.attr)

    def build(self):
        ttk.Label(self, text=self.title_text, style="H1.TLabel").pack(
            anchor="w")
        ttk.Label(self, text=self.blurb, style="Muted.TLabel",
                  wraplength=900, justify="left").pack(anchor="w",
                                                       pady=(0, 12))

        add = ttk.Frame(self, style="Card.TFrame", padding=12)
        add.pack(fill="x")
        inner = ttk.Frame(add, style="Inner.TFrame")
        inner.pack(fill="x")
        ttk.Label(inner, text="Name", style="CardBody.TLabel").pack(
            side="left")
        self.name_var = tk.StringVar()
        entry = ttk.Entry(inner, textvariable=self.name_var, width=34)
        entry.pack(side="left", padx=8)
        entry.bind("<Return>", lambda e: self.add_item())
        self.type_var = tk.StringVar(value="App")
        ttk.Combobox(inner, textvariable=self.type_var, state="readonly",
                     values=("App", "Website"), width=10).pack(
            side="left", padx=(0, 8))
        ttk.Button(inner, text="Add", style="Accent.TButton",
                   command=self.add_item).pack(side="left")

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self.refresh())
        ttk.Entry(inner, textvariable=self.search_var, width=20).pack(
            side="right")
        ttk.Label(inner, text="Search", style="CardBody.TLabel").pack(
            side="right", padx=8)

        wrap, self.tree = make_tree(self, [
            ("name", "Name", 340, "w"),
            ("type", "Type", 100, "w"),
            ("added", "Date Added", 120, "w"),
        ])
        wrap.pack(fill="both", expand=True, pady=12)

        bar = ttk.Frame(self)
        bar.pack(fill="x")
        ttk.Button(bar, text="Remove Selected",
                   command=self.remove_selected).pack(side="left")
        ttk.Button(bar, text=self.move_text,
                   command=self.move_selected).pack(side="left", padx=8)
        if self.attr == "allowed":
            ttk.Button(bar, text="Hide Selected",
                       command=self.hide_selected).pack(side="left",
                                                        padx=(0, 8))
        ttk.Button(bar, text="Clear All", style="Danger.TButton",
                   command=self.clear_all).pack(side="left")
        self.count_var = tk.StringVar()
        ttk.Label(bar, textvariable=self.count_var,
                  style="Muted.TLabel").pack(side="right")

        denied = self.attr == "blocked"
        self.smart_attr = "smart_denied" if denied else "smart_approved"
        self.smart_label = ("SmartSafe Denied" if denied
                            else "SmartSafe Approved")
        self.smart_open = False
        self.smart_btn = ttk.Button(self, command=self.toggle_smart)
        self.smart_btn.pack(anchor="w", pady=(10, 0))
        self.smart_frame = ttk.Frame(self)
        ttk.Label(
            self.smart_frame, style="Muted.TLabel", wraplength=900,
            justify="left",
            text=("Websites SmartSafe found unsafe. They are blocked like "
                  "Always Blocked websites." if denied else
                  "Websites SmartSafe checked and found safe.")
        ).pack(anchor="w", pady=(6, 0))
        swrap, self.smart_tree = make_tree(self.smart_frame, [
            ("name", "Name", 340, "w"),
            ("type", "Type", 100, "w"),
            ("added", "Date Added", 120, "w"),
        ], height=5)
        swrap.pack(fill="both", expand=True, pady=(6, 6))
        sbar = ttk.Frame(self.smart_frame)
        sbar.pack(anchor="w")
        ttk.Button(sbar, text=self.move_text,
                   command=self.smart_move_selected).pack(side="left")
        ttk.Button(sbar, text="Remove Selected",
                   command=self.smart_remove_selected).pack(
            side="left", padx=8)

        if self.attr == "allowed":
            self.hidden_open = False
            self.hidden_btn = ttk.Button(self, command=self.toggle_hidden)
            self.hidden_btn.pack(anchor="w", pady=(10, 0))
            self.hidden_frame = ttk.Frame(self)
            hwrap, self.hidden_tree = make_tree(self.hidden_frame, [
                ("name", "Name", 340, "w"),
                ("type", "Type", 100, "w"),
                ("added", "Date Added", 120, "w"),
            ], height=5)
            hwrap.pack(fill="both", expand=True, pady=(6, 6))
            ttk.Button(self.hidden_frame, text="Unhide Selected",
                       command=self.unhide_selected).pack(anchor="w")

    def _protected_message(self, name):
        return (f"'{name}' is needed by Windows or by LeafyGreen itself, "
                "so it can't be blocked.")

    def add_item(self):
        if not self.authorize():
            return
        name = self.name_var.get().strip()
        if not name:
            # Notify
            messagebox.showinfo(APP_NAME, "Type a website or app name "
                                "first.", parent=self)
            return
        kind = self.type_var.get()
        if kind == "Website":
            site = normalize_site_name(name)
            if site is None:
                # Notify
                messagebox.showwarning(
                    APP_NAME, "That doesn't look like a website address. "
                    "Type the full name, such as example.com (no spaces).",
                    parent=self)
                return
            name = site
        else:
            name = normalize_app_name(name)
        if not name:
            # Notify
            messagebox.showinfo(APP_NAME, "Type a website or app name "
                                "first.", parent=self)
            return

        lowered = name.lower()
        if any(row[0].lower() == lowered for row in self.items()):
            # Notify
            messagebox.showinfo(APP_NAME, f"'{name}' is already in this "
                                "list.", parent=self)
            return
        other = getattr(self.data, self.other_attr)
        if any(row[0].lower() == lowered for row in other):
            # Notify
            messagebox.showwarning(
                APP_NAME, f"'{name}' is already in {self.other_name}. "
                "Use the move button to switch it.", parent=self)
            return
        if kind == "App" and self.attr == "blocked" \
                and self.app.is_protected(name):
            # Notify
            messagebox.showwarning(APP_NAME, self._protected_message(name),
                                   parent=self)
            return

        self.items().append([name, kind, today_str()])
        self.data.log(f"Added to {self.title_text}", name)
        self.name_var.set("")
        self.app.set_status(f"Added '{name}' to {self.title_text}.")
        self.refresh()

    def _selected_indexes(self):
        selected = sorted((int(i) for i in self.tree.selection()),
                          reverse=True)
        if not selected:
            # Notify
            messagebox.showinfo(APP_NAME, "Select one or more rows "
                                "first.", parent=self)
        return selected

    def remove_selected(self):
        selected = self._selected_indexes()
        if not selected or not self.authorize():
            return
        items = self.items()
        for index in selected:
            removed = items.pop(index)
            self.data.log(f"Removed from {self.title_text}", removed[0])
        note = ""
        if self.attr == "allowed":
            note = (" An app removed from here is recorded again the next "
                    "time it runs; use the move button to block it.")
        self.app.set_status(f"Removed {len(selected)} item(s).{note}")
        self.refresh()

    def move_selected(self):
        selected = self._selected_indexes()
        if not selected or not self.authorize():
            return
        items = self.items()
        other = getattr(self.data, self.other_attr)
        moved, refused = 0, []
        for index in selected:
            row = items[index]
            if self.other_attr == "blocked" and row[1] == "App" \
                    and self.app.is_protected(row[0]):
                refused.append(row[0])
                continue
            items.pop(index)
            other.append([row[0], row[1], today_str()])
            self.data.log(f"Moved to {self.other_name}", row[0])
            moved += 1
        if refused:
            # Notify
            messagebox.showwarning(
                APP_NAME, self._protected_message(", ".join(refused)),
                parent=self)
        if moved:
            self.app.set_status(f"Moved {moved} item(s) to "
                                f"{self.other_name}.")
        self.refresh()

    def smart_items(self):
        return getattr(self.data, self.smart_attr)

    def toggle_smart(self):
        self.smart_open = not self.smart_open
        if self.smart_open:
            self.smart_frame.pack(fill="x", after=self.smart_btn)
        else:
            self.smart_frame.pack_forget()
        self.refresh()

    def _smart_selected(self):
        selected = sorted((int(i) for i in self.smart_tree.selection()),
                          reverse=True)
        if not selected:
            # Notify
            messagebox.showinfo(APP_NAME, "Select one or more rows "
                                "first.", parent=self)
        return selected

    def smart_move_selected(self):
        selected = self._smart_selected()
        if not selected or not self.authorize():
            return
        items = self.smart_items()
        other = getattr(self.data, self.other_attr)
        for index in selected:
            row = items.pop(index)
            if not any(r[0].lower() == row[0].lower() for r in other):
                other.append([row[0], row[1], today_str()])
            self.data.log(f"Moved to {self.other_name}", row[0])
        self.app.set_status(f"Moved {len(selected)} item(s) to "
                            f"{self.other_name}.")
        self.refresh()

    def smart_remove_selected(self):
        selected = self._smart_selected()
        if not selected or not self.authorize():
            return
        items = self.smart_items()
        for index in selected:
            removed = items.pop(index)
            self.data.log(f"Removed from {self.smart_label}", removed[0])
        self.app.set_status(f"Removed {len(selected)} item(s). SmartSafe "
                            "checks a website again the next time it is "
                            "visited.")
        self.refresh()

    def toggle_hidden(self):
        self.hidden_open = not self.hidden_open
        if self.hidden_open:
            self.hidden_frame.pack(fill="x", after=self.hidden_btn)
        else:
            self.hidden_frame.pack_forget()
        self.refresh()

    def hide_selected(self):
        selected = self._selected_indexes()
        if not selected or not self.authorize():
            return
        items = self.items()
        count = 0
        for index in selected:
            key = items[index][0].lower()
            if key not in self.data.hidden:
                self.data.hidden.append(key)
                count += 1
        self.data.purge_hidden_log()
        self.data.log("Hidden in Always Allowed", f"{count} item(s)")
        self.app.set_status(f"Hid {count} item(s). They stay allowed; open "
                            "Hidden at the bottom to see them.")
        self.refresh()

    def unhide_selected(self):
        selected = self.hidden_tree.selection()
        if not selected:
            # Notify
            messagebox.showinfo(APP_NAME, "Select one or more rows "
                                "first.", parent=self)
            return
        if not self.authorize():
            return
        items = self.items()
        names = {items[int(i)][0].lower() for i in selected}
        self.data.hidden = [h for h in self.data.hidden if h not in names]
        self.app.set_status(f"Unhid {len(names)} item(s).")
        self.refresh()

    def clear_all(self):
        if not self.items():
            return
        if not self.authorize():
            return
        # Notify
        if messagebox.askyesno(APP_NAME, f"Remove everything from "
                               f"{self.title_text}?", parent=self):
            self.items().clear()
            self.data.log(f"Cleared {self.title_text}", "All entries")
            self.app.set_status(f"{self.title_text} cleared.")
            self.refresh()

    def refresh(self):
        query = self.search_var.get().strip().lower()
        if self.attr == "allowed":
            self.data.prune_hidden()
        hidden = set(self.data.hidden) if self.attr == "allowed" else set()
        rows, hidden_rows, hidden_total = [], [], 0
        for i, (name, kind, added) in enumerate(self.items()):
            is_hidden = name.lower() in hidden
            hidden_total += is_hidden
            if query and query not in name.lower():
                continue
            row = (str(i), (name, kind, added), (self.row_tag,))
            (hidden_rows if is_hidden else rows).append(row)
        rebuild_tree(self.tree, rows)
        if self.attr == "allowed":
            rebuild_tree(self.hidden_tree, hidden_rows)
            arrow = "\u25BE" if self.hidden_open else "\u25B8"
            self.hidden_btn.configure(
                text=f"{arrow} Hidden ({hidden_total})")
        self.count_var.set(
            f"{len(rows)} of {len(self.items()) - hidden_total} shown")
        smart = self.smart_items()
        if self.smart_open:
            rebuild_tree(self.smart_tree, [
                (str(i), tuple(r), (self.row_tag,))
                for i, r in enumerate(smart)
                if not query or query in r[0].lower()])
        arrow = "\u25BE" if self.smart_open else "\u25B8"
        self.smart_btn.configure(
            text=f"{arrow} {self.smart_label} ({len(smart)})"
            + ("" if self.data.smartsafe_enabled else "  (off)"))


class LimitedAppsPage(Page):
    def build(self):
        ttk.Label(self, text="Limited Apps", style="H1.TLabel").pack(
            anchor="w")
        ttk.Label(self, text="Give specific apps their own daily time "
                  "limit. Time counts while the app is running; when it "
                  "is used up, the app is closed until tomorrow.",
                  style="Muted.TLabel", wraplength=900, justify="left").pack(anchor="w",
                                                      pady=(0, 12))

        bar = ttk.Frame(self)
        bar.pack(fill="x", pady=(0, 8))
        ttk.Button(bar, text="Add App", style="Accent.TButton",
                   command=self.add_app).pack(side="left")
        ttk.Button(bar, text="Edit Limit", command=self.edit_app).pack(
            side="left", padx=8)
        ttk.Button(bar, text="Remove", command=self.remove_app).pack(
            side="left")
        ttk.Button(bar, text="Reset Today's Usage",
                   command=self.reset_usage).pack(side="right")

        wrap, self.tree = make_tree(self, [
            ("app", "App", 280, "w"),
            ("limit", "Daily Limit (min)", 140, "w"),
            ("used", "Used Today (min)", 140, "w"),
            ("status", "Status", 120, "w"),
        ])
        wrap.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", self._double_click)

        self.count_var = tk.StringVar()
        ttk.Label(self, textvariable=self.count_var,
                  style="Muted.TLabel").pack(anchor="e", pady=(8, 0))

    @staticmethod
    def _status(entry):
        used, limit = entry.get("used_sec", 0), entry["limit"] * 60
        if used >= limit:
            return "Over limit", "blocked"
        if used >= 0.8 * limit:
            return "Near limit", "warn"
        return "OK", "allowed"

    def _selected_index(self):
        selection = self.tree.selection()
        if len(selection) != 1:
            # Notify
            messagebox.showinfo(APP_NAME, "Select a single app first.",
                                parent=self)
            return None
        return int(selection[0])

    def _double_click(self, event):
        if self.tree.identify_region(event.x, event.y) == "cell":
            self.edit_app()

    def add_app(self):
        if not self.authorize():
            return
        dlg = AppDialog(self, "Add Limited App")
        if not dlg.result:
            return
        name, minutes = dlg.result
        name = normalize_app_name(name)
        if self.app.is_protected(name):
            # Notify
            messagebox.showwarning(
                APP_NAME, f"'{name}' is needed by Windows or by "
                "LeafyGreen itself, so it can't be limited.", parent=self)
            return
        if any(a["name"].lower() == name.lower() for a in self.data.limited):
            # Notify
            messagebox.showinfo(APP_NAME, f"'{name}' already has a limit.",
                                parent=self)
            return
        self.data.limited.append({"name": name, "limit": minutes,
                                  "used_sec": 0.0})
        self.data.log("App limit added", f"{name} ({minutes} min)")
        self.app.set_status(f"Added a {minutes}-minute limit for {name}.")
        self.refresh()

    def edit_app(self):
        index = self._selected_index()
        if index is None or not self.authorize():
            return
        entry = self.data.limited[index]
        dlg = AppDialog(self, "Edit Limit", name=entry["name"],
                        minutes=entry["limit"], lock_name=True)
        if not dlg.result:
            return
        entry["limit"] = dlg.result[1]
        self.data.log("App limit changed",
                      f"{entry['name']} ({entry['limit']} min)")
        self.app.set_status(f"Updated the limit for {entry['name']}.")
        self.refresh()

    def remove_app(self):
        index = self._selected_index()
        if index is None or not self.authorize():
            return
        entry = self.data.limited[index]
        # Notify
        if messagebox.askyesno(APP_NAME, f"Remove the limit for "
                               f"{entry['name']}?", parent=self):
            self.data.limited.pop(index)
            self.data.log("App limit removed", entry["name"])
            self.app.set_status(f"Removed the limit for {entry['name']}.")
            self.refresh()

    def reset_usage(self):
        if not self.authorize():
            return
        # Notify
        if messagebox.askyesno(APP_NAME, "Reset today's usage for every "
                               "app?", parent=self):
            for entry in self.data.limited:
                entry["used_sec"] = 0.0
            self.app.set_status("Today's app usage reset.")
            self.refresh()

    def refresh(self):
        rows = []
        for i, entry in enumerate(self.data.limited):
            status, tag = self._status(entry)
            used_min = int(entry.get("used_sec", 0) // 60)
            rows.append((str(i), (entry["name"], entry["limit"], used_min,
                                  status), (tag,)))
        rebuild_tree(self.tree, rows)
        self.count_var.set(f"{len(self.data.limited)} limited app(s)")


class CouponsPage(Page):
    def build(self):
        ttk.Label(self, text="Extra Time Coupons", style="H1.TLabel").pack(
            anchor="w")
        ttk.Label(self, text="Create coupons that grant bonus screen time "
                  "when redeemed.", style="Muted.TLabel").pack(
            anchor="w", pady=(0, 12))

        bar = ttk.Frame(self)
        bar.pack(fill="x", pady=(0, 8))
        ttk.Button(bar, text="Create Coupon", style="Accent.TButton",
                   command=self.create_coupon).pack(side="left")
        ttk.Button(bar, text="Redeem Selected",
                   command=self.redeem).pack(side="left", padx=8)
        ttk.Button(bar, text="Copy Code", command=self.copy_code).pack(
            side="left")
        ttk.Button(bar, text="Delete", style="Danger.TButton",
                   command=self.delete).pack(side="right")

        wrap, self.tree = make_tree(self, [
            ("code", "Code", 190, "w"),
            ("minutes", "Minutes", 90, "w"),
            ("note", "Note", 240, "w"),
            ("created", "Created", 110, "w"),
            ("status", "Status", 100, "w"),
        ])
        wrap.pack(fill="both", expand=True)

        self.summary = tk.StringVar()
        ttk.Label(self, textvariable=self.summary,
                  style="Muted.TLabel").pack(anchor="e", pady=(8, 0))

    def _selected(self):
        return [int(i) for i in self.tree.selection()]

    def create_coupon(self):
        if not self.authorize():
            return
        dlg = CouponDialog(self, "Create Coupon")
        if not dlg.result:
            return
        minutes, note = dlg.result
        code = self.data.add_coupon(minutes, note)
        self.app.set_status(f"Created coupon {code}.")
        self.refresh()

    def redeem(self):
        selected = self._selected()
        if len(selected) != 1:
            # Notify
            messagebox.showinfo(APP_NAME, "Select a single coupon to "
                                "redeem.", parent=self)
            return
        if not self.authorize():
            return
        coupon = self.data.coupons[selected[0]]
        if coupon["status"] != "Unused":
            # Notify
            messagebox.showinfo(APP_NAME, "That coupon was already "
                                "redeemed.", parent=self)
            return
        # Notify
        if messagebox.askyesno(APP_NAME, f"Redeem {coupon['code']} for "
                               f"{coupon['minutes']} extra minutes?",
                               parent=self):
            self.data.redeem_coupon(coupon["code"])
            self.app.set_status(f"Redeemed {coupon['code']}: "
                                f"+{coupon['minutes']} minutes.")
            self.refresh()

    def copy_code(self):
        selected = self._selected()
        if len(selected) != 1:
            # Notify
            messagebox.showinfo(APP_NAME, "Select a single coupon first.",
                                parent=self)
            return
        code = self.data.coupons[selected[0]]["code"]
        self.clipboard_clear()
        self.clipboard_append(code)
        self.app.set_status(f"Copied {code} to the clipboard.")

    def delete(self):
        selected = sorted(self._selected(), reverse=True)
        if not selected:
            # Notify
            messagebox.showinfo(APP_NAME, "Select one or more coupons "
                                "first.", parent=self)
            return
        if not self.authorize():
            return
        # Notify
        if messagebox.askyesno(APP_NAME, f"Delete {len(selected)} "
                               "coupon(s)?", parent=self):
            for index in selected:
                removed = self.data.coupons.pop(index)
                self.data.log("Coupon deleted", removed["code"])
            self.app.set_status(f"Deleted {len(selected)} coupon(s).")
            self.refresh()

    def refresh(self):
        rows = []
        for i, c in enumerate(self.data.coupons):
            tag = "allowed" if c["status"] == "Unused" else "muted"
            rows.append((str(i), (c["code"], c["minutes"], c["note"],
                                  c["created"], c["status"]), (tag,)))
        rebuild_tree(self.tree, rows)
        unused = [c for c in self.data.coupons if c["status"] == "Unused"]
        total = sum(c["minutes"] for c in unused)
        self.summary.set(f"{len(unused)} unused coupon(s), "
                         f"{total} minutes available")


class LogPage(Page):
    """The whole activity log, with filters (day, hour, result, text) and a
    choice of order (newest, oldest, by day, by hour of the day)."""

    ALL_DAYS, ALL_HOURS, ALL_RESULTS = "All days", "All hours", "All results"
    RESULTS = ("Blocked", "Allowed", "Limited", "Failed", "Info")

    @staticmethod
    def hour_label(h):
        return f"{h:02d}:00 - {h:02d}:59"

    def build(self):
        ttk.Label(self, text="Log", style="H1.TLabel").pack(anchor="w")
        ttk.Label(self, text="Everything LeafyGreen has done and every "
                  "change made. Filter it by day, hour or result, and "
                  "choose how it is ordered.", style="Muted.TLabel",
                  wraplength=900, justify="left").pack(anchor="w",
                                                       pady=(0, 12))

        bar = ttk.Frame(self, style="Card.TFrame", padding=12)
        bar.pack(fill="x")
        inner = ttk.Frame(bar, style="Inner.TFrame")
        inner.pack(fill="x")
        self.day_var = tk.StringVar(value=self.ALL_DAYS)
        self.hour_var = tk.StringVar(value=self.ALL_HOURS)
        self.result_var = tk.StringVar(value=self.ALL_RESULTS)
        self.sort_var = tk.StringVar(value=LOG_SORTS[0])
        self.search_var = tk.StringVar()
        self.day_keys = {self.ALL_DAYS: None}

        def box(label, var, values, width):
            ttk.Label(inner, text=label, style="CardBody.TLabel").pack(
                side="left", padx=(0, 4))
            combo = ttk.Combobox(inner, textvariable=var, state="readonly",
                                 values=values, width=width)
            combo.pack(side="left", padx=(0, 12))
            combo.bind("<<ComboboxSelected>>", self._changed)
            return combo

        self.day_box = box("Day", self.day_var, [self.ALL_DAYS], 20)
        self.hour_box = box(
            "Hour", self.hour_var,
            [self.ALL_HOURS] + [self.hour_label(h) for h in range(24)], 14)
        self.result_box = box("Result", self.result_var,
                              [self.ALL_RESULTS] + list(self.RESULTS), 12)
        self.sort_box = box("Sort by", self.sort_var, list(LOG_SORTS), 14)

        row2 = ttk.Frame(bar, style="Inner.TFrame")
        row2.pack(fill="x", pady=(10, 0))
        ttk.Label(row2, text="Search", style="CardBody.TLabel").pack(
            side="left", padx=(0, 4))
        ttk.Entry(row2, textvariable=self.search_var, width=34).pack(
            side="left")
        self.search_var.trace_add("write", lambda *a: self.refresh())
        ttk.Button(row2, text="Reset Filters",
                   command=self.reset_filters).pack(side="left", padx=12)

        wrap, self.tree = make_tree(self, [
            ("day", "Day", 110, "w"),
            ("time", "Time", 80, "w"),
            ("event", "Event", 210, "w"),
            ("target", "App / Website", 290, "w"),
            ("result", "Result", 100, "w"),
        ], height=14)
        wrap.pack(fill="both", expand=True, pady=12)

        foot = ttk.Frame(self)
        foot.pack(fill="x")
        ttk.Button(foot, text="Refresh", command=self.refresh).pack(
            side="left")
        self.count_var = tk.StringVar()
        ttk.Label(foot, textvariable=self.count_var,
                  style="Muted.TLabel").pack(side="right")

    def _changed(self, event=None):
        self.tree._sort_state = None
        self.refresh()

    def reset_filters(self):
        self.day_var.set(self.ALL_DAYS)
        self.hour_var.set(self.ALL_HOURS)
        self.result_var.set(self.ALL_RESULTS)
        self.sort_var.set(LOG_SORTS[0])
        self.search_var.set("")
        self.tree._sort_state = None
        self.refresh()

    def _day_choices(self, rows):
        """Labels for the Day box: every date that has lines in the log."""
        today = datetime.date.today()
        names = {today.isoformat(): " (today)",
                 (today - datetime.timedelta(days=1)).isoformat():
                 " (yesterday)"}
        keys = {self.ALL_DAYS: None}
        dates = sorted({r["date"] for r in rows if r["date"]}, reverse=True)
        for date in dates:
            keys[date + names.get(date, "")] = date
        if any(not r["date"] for r in rows):
            keys["Earlier (no date)"] = ""
        return keys

    def refresh(self):
        all_rows = log_rows(self.data.visible_activity())
        old_key = self.day_keys.get(self.day_var.get())
        self.day_keys = self._day_choices(all_rows)
        label = next((lab for lab, key in self.day_keys.items()
                      if key == old_key), self.ALL_DAYS)
        self.day_var.set(label)
        self.day_box.configure(values=list(self.day_keys))

        hour_text = self.hour_var.get()
        hour = None
        if hour_text != self.ALL_HOURS:
            try:
                hour = int(hour_text[:2])
            except ValueError:
                hour = None
        result = self.result_var.get()
        rows = filter_log(
            all_rows, day=self.day_keys.get(label), hour=hour,
            result=None if result == self.ALL_RESULTS else result,
            text=self.search_var.get())
        rows = sort_log(rows, self.sort_var.get())
        today = today_str()
        shown = []
        for r in rows:
            tag = RESULT_TAGS.get(r["result"], "")
            shown.append((str(r["i"]),
                          (r["date"] or "Earlier", r["time"], r["event"],
                           r["target"], r["result"]),
                          (tag,) if tag else ()))
        rebuild_tree(self.tree, shown)
        self.count_var.set(f"{len(rows)} of {len(all_rows)} entries")


class AccountPage(Page):
    MAX_PARENTS = Data.MAX_PARENTS
    HIDDEN_PIN = "\u2022  \u2022  \u2022  \u2022"

    def build(self):
        ttk.Label(self, text="My Account", style="H1.TLabel").pack(anchor="w")
        ttk.Label(self, text="Parents", style="H2.TLabel",
                  background=BG).pack(anchor="w")
        ttk.Label(self, text="Up to four people can sign in to the Web "
                  "Dashboard, each with their own username, password and "
                  "role (Lite, Complete or Child). Someone who forgets their "
                  "password can reset it on the Web Dashboard sign-in screen "
                  "using the device PIN below.",
                  style="Muted.TLabel", wraplength=900,
                  justify="left").pack(anchor="w", pady=(0, 12))

        bar = ttk.Frame(self)
        bar.pack(fill="x", pady=(0, 8))
        self.add_btn = ttk.Button(bar, text="Add Parent",
                                  style="Accent.TButton",
                                  command=self.add_parent)
        self.add_btn.pack(side="left")
        ttk.Button(bar, text="Change Role",
                   command=self.change_role).pack(side="left", padx=8)
        ttk.Button(bar, text="Reset Password",
                   command=self.reset_password).pack(side="left")
        ttk.Button(bar, text="Remove Selected", style="Danger.TButton",
                   command=self.remove_parent).pack(side="left", padx=8)

        wrap, self.tree = make_tree(self, [
            ("user", "Username", 260, "w"),
            ("role", "Role", 120, "w"),
            ("added", "Added", 140, "w"),
        ], height=5)
        wrap.pack(fill="x")

        card = ttk.Frame(self, style="Card.TFrame", padding=14)
        card.pack(fill="x", pady=(16, 0))
        ttk.Label(card, text="Device PIN", style="H2.TLabel").pack(anchor="w")
        ttk.Label(card, text="The 4-digit code that unlocks changes in this "
                  "app. Use it to reset a forgotten Web Dashboard password.",
                  style="CardText.TLabel", wraplength=860,
                  justify="left").pack(anchor="w", pady=(2, 8))
        row = ttk.Frame(card, style="Inner.TFrame")
        row.pack(anchor="w")
        self.pin_var = tk.StringVar(value=self.HIDDEN_PIN)
        ttk.Label(row, textvariable=self.pin_var, font=(FONT, 20, "bold"),
                  background="white", foreground=NAVY).pack(side="left")
        self.pin_btn = ttk.Button(row, text="Show", command=self.toggle_pin)
        self.pin_btn.pack(side="left", padx=(14, 0))
        self.pin_shown = False

        sub = ttk.Frame(self, style="Card.TFrame", padding=14)
        sub.pack(fill="x", pady=(16, 0))
        ttk.Label(sub, text="Subscription", style="H2.TLabel").pack(
            anchor="w")
        self.sub_status = tk.StringVar()
        ttk.Label(sub, textvariable=self.sub_status, style="CardBody.TLabel",
                  wraplength=860, justify="left").pack(anchor="w",
                                                       pady=(2, 8))
        ttk.Label(sub, text="Protection stays on until the key expires. "
                  "A record of your keys and their end dates is saved in the "
                  "leafygreen folder in the child's user folder.",
                  style="CardText.TLabel", wraplength=860,
                  justify="left").pack(anchor="w", pady=(0, 10))
        warn = ttk.Frame(sub, style="Inner.TFrame")
        warn.pack(anchor="w", pady=(0, 10))
        ttk.Label(warn, text="Show the 'expiring soon' warning this many "
                  "days before it expires:", style="CardBody.TLabel").pack(
            side="left")
        self.warn_var = tk.StringVar()
        ttk.Spinbox(warn, from_=1, to=60, width=5,
                    textvariable=self.warn_var).pack(side="left", padx=8)
        ttk.Button(warn, text="Save", command=self.save_warn_days).pack(
            side="left")
        ttk.Button(sub, text="Renew / Enter New Key", style="Accent.TButton",
                   command=self.renew).pack(anchor="w")

    def renew(self):
        if not self.authorize(allow_locked=True):
            return
        dlg = ActivateKeyDialog(self, self.data)
        if not dlg.result:
            return
        ok, error = self.data.activate(dlg.result)
        if not ok:
            # Notify
            messagebox.showerror(APP_NAME, error or "That key is not "
                                 "correct.", parent=self)
            return
        self.data.log("Subscription activated",
                      self.data.expiry or "no end date")
        self.app.update_header()
        self.app.set_status("Key activated. "
                            + (f"Expires {self.data.expiry}."
                               if self.data.expiry else "No end date."))
        self.refresh()

    def manage_keys(self):
        if not self.authorize(allow_locked=True):
            return
        dlg = KeyManagerDialog(self, self.data.key_log)
        if dlg.result is None:
            return
        self.data.set_key_list(dlg.result)
        self.data.log("Activation key list changed",
                      f"{len(self.data.key_log)} key(s)")
        self.app.set_status("Activation keys saved.")
        self.refresh()

    def save_warn_days(self):
        try:
            days = int(self.warn_var.get())
        except (TypeError, ValueError):
            days = 0
        if not 1 <= days <= 60:
            # Notify
            messagebox.showerror(APP_NAME, "Enter a number of days between "
                                 "1 and 60.", parent=self)
            return
        if not self.authorize():
            return
        self.data.expiry_warn_days = days
        self.data.log("Expiry warning changed", f"{days} days before")
        self.app.set_status(f"The warning will show {days} days before the "
                            "subscription expires.")
        self.refresh()

    def toggle_pin(self):
        if self.pin_shown:
            self._hide_pin()
            return
        if not self.authorize():
            return
        pin = self.data.pin_plain
        self.pin_var.set("  ".join(pin) if pin else
                         "Unknown - change the PIN once to show it here")
        self.pin_btn.configure(text="Hide")
        self.pin_shown = True

    def _hide_pin(self):
        self.pin_var.set(self.HIDDEN_PIN)
        self.pin_btn.configure(text="Show")
        self.pin_shown = False

    def _names(self):
        return [p["username"] for p in self.data.parents]

    def _selected_name(self):
        selected = self.tree.selection()
        if len(selected) != 1:
            # Notify
            messagebox.showinfo(APP_NAME, "Select one parent first.",
                                parent=self)
            return None
        return self.data.parents[int(selected[0])]["username"]

    def add_parent(self):
        if len(self.data.parents) >= self.MAX_PARENTS:
            # Notify
            messagebox.showinfo(APP_NAME, "Only four accounts can be added.",
                                parent=self)
            return
        if not self.authorize():
            return
        dlg = ParentDialog(self, "Add Parent", self._names())
        if not dlg.result:
            return
        name, password, role = dlg.result
        self.data.add_parent(name, password, role)
        self.data.log("Parent added", f"{name} ({role})")
        self.app.set_status(f"Added '{name}' as {role}.")
        self.refresh()

    def change_role(self):
        name = self._selected_name()
        if name is None or not self.authorize():
            return
        dlg = RoleDialog(self, name, self.data.parent_role(name))
        if not dlg.result:
            return
        self.data.set_parent_role(name, dlg.result)
        self.data.log("Parent role changed", f"{name} ({dlg.result})")
        self.app.set_status(f"'{name}' is now {dlg.result}.")
        self.refresh()

    def reset_password(self):
        name = self._selected_name()
        if name is None or not self.authorize():
            return
        dlg = ParentDialog(self, f"Reset Password: {name}", self._names(),
                           username=name)
        if not dlg.result:
            return
        self.data.set_parent_password(name, dlg.result[1])
        self.data.log("Parent password reset", name)
        self.app.set_status(f"Password reset for '{name}'.")
        self.refresh()

    def remove_parent(self):
        name = self._selected_name()
        if name is None or not self.authorize():
            return
        # Notify
        if messagebox.askyesno(APP_NAME, f"Remove parent '{name}'? They "
                               "will no longer be able to sign in to the "
                               "Web Dashboard.", parent=self):
            self.data.remove_parent(name)
            self.data.log("Parent removed", name)
            self.app.set_status(f"Removed parent '{name}'.")
            self.refresh()

    def refresh(self):
        rows = [(str(i), (p["username"], p.get("role", "Complete"),
                          p["added"]), ())
                for i, p in enumerate(self.data.parents)]
        rebuild_tree(self.tree, rows)
        self.add_btn.configure(
            state="disabled" if len(self.data.parents) >= self.MAX_PARENTS
            else "normal")
        self.warn_var.set(str(self.data.expiry_warn_days))
        left = self.data.days_left()
        if left is None:
            self.sub_status.set("No end date is set - protection does not "
                                "expire.")
        elif left > 0:
            self.sub_status.set(f"Expires on {self.data.expiry} "
                                f"({left} day{'' if left == 1 else 's'} "
                                "left).")
        elif left == 0:
            self.sub_status.set(f"Expires today ({self.data.expiry}).")
        else:
            grace = self.data.grace_days_left()
            if grace and grace > 0:
                self.sub_status.set(
                    f"Expired on {self.data.expiry}. Settings are locked; "
                    f"protection turns off in {grace} "
                    f"day{'' if grace == 1 else 's'}. Activate a new key to "
                    "unlock.")
            else:
                self.sub_status.set(
                    f"Expired on {self.data.expiry}. Protection is off and "
                    "settings are locked. Activate a new key to unlock.")
        self._hide_pin()


ROLE_ACTIONS = {"Lite": frozenset({"req_review", "cp_new"}),
                "Child": frozenset({"new_request", "alerts"})}
_MOBILE_AGENT = re.compile(
    r"mobi|android|iphone|ipad|ipod|windows phone|blackberry|opera mini|"
    r"silk|kindle|webos|tablet", re.I)


def is_mobile_agent(user_agent):
    """True for phones and tablets (judged by the browser's User-Agent)."""
    return bool(_MOBILE_AGENT.search(user_agent or ""))


MOBILE_PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>LeafyGreen</title><style>
body{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;background:#f2f6f3;color:#1d2b24;font:16px "Segoe UI",system-ui,sans-serif;text-align:center}
main{max-width:420px;padding:28px}svg{width:150px;height:auto}
p.big{font-size:17px;font-weight:600;color:#12382a;margin:20px 0 12px;line-height:1.4}
p.sm{font-size:13px;color:#617268;margin:0}
</style></head><body><main>
<svg viewBox="-70 -70 140 135" role="img" aria-label="Warning"><polygon points="-44,-46 0,-58 44,-46 46,6 30,36 0,58 -30,36 -46,6" fill="#e8920c" stroke="#8a4f00" stroke-width="4" stroke-linejoin="round"/><polygon points="-44,-46 0,-58 44,-46 46,6 30,36 0,58 -30,36 -46,6" fill="none" stroke="rgba(255,255,255,.5)" stroke-width="2" stroke-linejoin="round" transform="scale(.8)"/><path d="M0 -26V8" stroke="#fff" stroke-width="11" stroke-linecap="round"/><circle cx="0" cy="27" r="6.5" fill="#fff"/></svg>
<p class="big">LeafyGreen is not supported on this device. Please try again on a desktop computer or laptop. If you continue to experience issues, check your internet connection.</p>
<p class="sm">Protection on your child's device is still active.</p>
</main></body></html>
"""

WEB_PAGE = r'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>LeafyGreen</title><style>
:root{--navy:#1b4d36;--navyd:#12382a;--acc:#1f8a5b;--accd:#17704a;--accfg:#fff;--bg:#f2f6f3;--bd:#d3dfd8;--blue:#fff;--hov:#e7f1eb;--tx:#1d2b24;--mu:#617268;--gr:#1a7a4a;--grb:#e3f3ea;--rd:#b3261e;--rdb:#fbeaea;--am:#8a5a00;--amb:#fff4e0}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--tx);font:14px "Segoe UI",system-ui,sans-serif}
header{background:var(--navy);color:#fff;padding:14px 20px;display:flex;justify-content:space-between;align-items:center;gap:12px}
.t{font-size:20px}.s{font-size:12px}header .s{color:#cfe6d9}a{color:var(--navyd)}
nav{display:flex;gap:4px;overflow-x:auto;padding:8px 12px 0}
nav button{background:var(--bd);color:var(--navyd);font-weight:700;border:0;border-radius:4px 4px 0 0;padding:8px 14px;white-space:nowrap}
nav button.on{background:#fff;color:var(--navyd);box-shadow:inset 0 -3px var(--acc)}
main{padding:16px;max-width:1000px;margin:auto}h1{font-size:18px;color:var(--navyd);margin:0 0 4px}h2{font-size:14px;color:var(--navy);margin:0 0 8px}
.mu{color:var(--mu)}.card{background:#fff;border:1px solid var(--bd);padding:14px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px;margin:12px 0}
.num{font-size:26px;font-weight:700;color:var(--navyd)}.row{display:grid;grid-template-columns:200px 1fr;gap:8px}
@media(max-width:560px){.row{grid-template-columns:1fr}}
button{font:inherit;background:var(--blue);color:var(--navy);border:1px solid var(--bd);padding:7px 14px;cursor:pointer}
button:hover{background:var(--hov)}
button,input,select{border-radius:6px}.card{border-radius:10px}
button.a{background:var(--acc);color:var(--accfg);border-color:var(--navy);font-weight:600}button.a:hover{background:var(--accd)}button.d{background:var(--rd);color:#fff;border-color:var(--rd)}
input,select{font:inherit;padding:6px;border:1px solid var(--bd);background:#fff;max-width:100%}input[type=number]{width:70px}
.bar{display:flex;justify-content:space-between;align-items:center;margin:16px 0 6px}.g{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:12px}
.tw{overflow-x:auto;margin-top:10px}table{border-collapse:collapse;width:100%;background:#fff}
th{background:var(--navy);color:#fff;text-align:left;padding:7px 8px}td{padding:6px 8px;border-bottom:1px solid var(--bd)}
tr.blocked{background:var(--rdb);color:var(--rd)}tr.allowed{background:var(--grb);color:var(--gr)}tr.warn{background:var(--amb);color:var(--am)}tr.muted{color:#999}
footer{background:#fff;padding:6px 14px;color:var(--mu);position:sticky;bottom:0}
.banner{color:#fff;font-weight:700;padding:13px 18px;text-align:center;font-size:15px;line-height:1.4}
.banner.lo{background:#f4b350}.banner.or{background:#e8920c}.banner.red{background:var(--rd)}
.qh{display:flex;justify-content:space-between;align-items:center}.qh h2{margin:0}.pen{padding:2px 9px;font-size:16px;line-height:1.2}
.pz{display:flex;gap:6px}.pz select{flex:1;min-width:0}.lf{display:flex;flex-wrap:wrap;gap:10px;align-items:center}.lf label{white-space:nowrap}
.sh{cursor:pointer}.sh.pop{animation:pop .6s}
@keyframes pop{50%{transform:scale(1.12)}}
</style></head><body>
<header><div><div class="t"><b>LeafyGreen</b></div><div class="s">Parental Controls</div></div><div class="s" id="hs"></div></header>
<div id="app"></div><footer id="st">Ready</footer>
<script>
let tok=sessionStorage.getItem('t'),S=null,tab='Dashboard',popNext=false,hidOpen=false,reqOpen=false,lf={day:'',hour:'',res:'',q:'',sort:'Newest first'};
const $=s=>document.querySelector(s),esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const TABS=['Dashboard','Time Limits','Always Blocked','Always Allowed','Limited Apps','Extra Time Coupons','Log'];
const tabs=()=>S&&S.role=='Lite'?['Requests','Extra Time Coupons']:TABS;
function toast(m,bad){$('#st').textContent=m;$('#st').style.color=bad?'#b3261e':'';clearTimeout(toast.t);toast.t=setTimeout(()=>{$('#st').textContent='Ready';$('#st').style.color=''},6000)}
function out(){tok=null;sessionStorage.removeItem('t');S=null;draw()}
async function post(p,b){const r=await fetch(p,{method:'POST',headers:{'X-Token':tok||''},body:JSON.stringify(b||{})});if(r.status==401){out();throw 0}return r.json()}
async function load(){const r=await post('/api/state',{log:tab=='Log'});if(r.state){S=r.state;draw()}}
async function act(a,x){const r=await post('/api/act',Object.assign({},x,{a}));if(r.msg)toast(r.msg,!r.ok);if(r.state){S=r.state;if(tab=='Log')return load();draw()}}
async function login(){const r=await (await fetch('/api/login',{method:'POST',body:JSON.stringify({username:$('#un').value,password:$('#pw').value})})).json();
 if(r.ok){tok=r.token;sessionStorage.setItem('t',tok);await load()}else{$('#err').textContent=r.msg;$('#pw').value=''}}
async function resetpw(){const r=await (await fetch('/api/parent_reset',{method:'POST',body:JSON.stringify({pin:$('#rpin').value,username:$('#run').value,password:$('#rpw').value})})).json();
 $('#err').style.color=r.ok?'#1a7a4a':'#b3261e';$('#err').textContent=r.msg||'';if(r.ok){$('#rpin').value='';$('#rpw').value=''}}
function tbl(h,rows){return `<div class="tw"><table><tr>${h.map(x=>`<th>${x}</th>`).join('')}</tr>${rows.map(r=>`<tr class="${r[0]}">${r[1].map(c=>`<td>${esc(c)}</td>`).join('')}${r[2]?`<td>${r[2]}</td>`:''}</tr>`).join('')}</table></div>`}
let lastSh='';
function shState(){return S.n_pending>0?(S.protect?'ask':'ask_off'):!S.protect?'off':!S.smart?'warn':'on'}
function shield(){const st=shState(),amb=st=='ask'||st=='ask_off'||st=='warn',c=st=='on'?'#1f8a5b':amb?'#e8920c':'#d9534f',e=st=='on'?'#12382a':amb?'#8a4f00':'#8b1a1a',P='-44,-46 0,-58 44,-46 46,6 30,36 0,58 -30,36 -46,6',w='fill="none" stroke="#fff" stroke-width="9" stroke-linecap="round" stroke-linejoin="round"';
 const bang=(col,x)=>`<path d="M0 -26V8" fill="none" stroke="${col}" stroke-width="${11+x}" stroke-linecap="round"/><circle cx="0" cy="27" r="${6.5+x/2}" fill="${col}"/>`;
 const icon=st=='on'?`<polyline points="-20,2 -7,15 21,-15" ${w}/>`:st=='off'?`<path d="M-15 -15L15 15M15 -15L-15 15" ${w}/>`:st=='warn'?bang('#fff',0):bang('#8a4f00',5)+bang('#ffe14d',0);
 const pop=(popNext||(lastSh&&lastSh!=st))?' pop':'';popNext=false;lastSh=st;
 const off=st=='off'||st=='ask_off',tc=st=='on'?'#1a7a4a':off?'#b3261e':'#8a5a00',sub={on:'Tap to turn off',warn:'SmartSafe is off',ask:'A request is waiting',ask_off:'A request is waiting',off:'Tap to turn on'}[st];
 return `<svg viewBox="-70 -70 140 135" width="150" height="145" data-a="protect" class="sh ${st}${pop}"><polygon points="${P}" fill="${c}" stroke="${e}" stroke-width="4" stroke-linejoin="round"/><polygon points="${P}" fill="none" stroke="rgba(255,255,255,.5)" stroke-width="2" stroke-linejoin="round" transform="scale(.8)"/>${icon}</svg>
 <div style="font-weight:700;color:${tc}">PROTECTION ${off?'OFF':'ON'}</div><div class="mu s">${sub}</div>`}
function smartBox(){return `<div style="margin-top:12px;border-top:1px solid var(--bd);padding-top:10px"><label><input type="checkbox" data-a="smartsafe" ${S.smart?'checked':''}> <b>SmartSafe</b></label><div class="mu s">Checks visited websites and blocks unsafe ones</div></div>`}
const TAG={Blocked:'blocked',Allowed:'allowed',Limited:'warn',Failed:'warn'};
const hid=r=>S.hidden.includes(r[0].toLowerCase());
function lst(k){const b=k=='blocked',t=b?'Always Blocked':'Always Allowed',o=b?'Allow':'Block',
 rows=b?S.blocked:S.allowed.filter(r=>!hid(r)),hidden=b?[]:S.allowed.filter(hid),
 btn=r=>`<button data-a="move" data-list="${k}" data-name="${esc(r[0])}">${o}</button> ${b?'':`<button data-a="hide" data-name="${esc(r[0])}">Hide</button> `}<button class="d" data-a="remove" data-list="${k}" data-name="${esc(r[0])}">Remove</button>`;
 return `<h1>${t}</h1><p class="mu">${b?'Apps listed here are closed the moment they start. Websites listed here are blocked on this computer; a browser still showing one is closed.':'Apps are added here automatically the first time they run. Listed apps are never limited or closed. Hide system items you don\'t need to see; they stay allowed.'}</p>
 <div class="card"><input id="nm" placeholder="Name (e.g. Game.exe)"> <select id="ty"><option>App</option><option>Website</option></select> <button class="a" data-a="add" data-list="${k}">Add</button></div>
 ${tbl(['Name','Type','Added',''],rows.map(r=>[b?'blocked':'allowed',r,btn(r)]))}
 ${b?'':`<details id="hid" ${hidOpen?'open':''} style="margin-top:12px"><summary><b>Hidden (${hidden.length})</b></summary>${tbl(['Name','Type','Added',''],hidden.map(r=>['allowed',r,`<button data-a="unhide" data-name="${esc(r[0])}">Unhide</button>`]))}</details>`}`}
function quick(){const x=S;
 return `<div class="g">${x.quick.map(k=>{
  if(k=='pause')return x.paused?`<button data-a="pause">Resume Internet${x.pause_min?' ('+x.pause_min+' min left)':''}</button>`:`<div class="pz"><select id="pz" aria-label="Pause for">${x.pauses.map(p=>`<option value="${p[1]}" ${p[1]==30?'selected':''}>${esc(p[0])}</option>`).join('')}</select><button data-a="pause">Pause Internet</button></div>`;
  if(k=='coupon')return '<button data-a="qcoupon">Add New Coupon</button>';
  return `<button data-a="qreq">Review Requests${x.pending.length?' ('+x.pending.length+')':''}</button>`}).join('')}</div>`}
function reqPanel(lite){const x=S;
 return `<div class="card" style="margin-top:12px"><h2>Review Requests</h2>${x.pending.length?`<p class="mu">Choose what to do with each request. The child is told the result on their computer.</p>
 <div class="tw"><table><tr><th>Request</th><th>Sent</th><th>Message</th><th>Decision</th></tr>${x.pending.map(r=>`<tr><td>${esc(r.text)}</td><td>${esc(r.created)}</td><td>${esc(r.note)}</td><td><select data-req="${esc(r.id)}"><option value="">Decide later</option><option value="approve">Approve</option><option value="deny">Deny</option></select></td></tr>`).join('')}</table></div>
 <p><button class="a" data-a="req_apply">Apply decisions</button> ${lite?'':'<button data-a="qreq">Close</button>'}</p>`:`<p class="mu">No requests are waiting.</p>${lite?'':'<p><button data-a="qreq">Close</button></p>'}`}</div>`}
function askCard(){const x=S;return `<div class="card" data-keep style="margin-top:12px"><h2>Ask a Parent</h2><p class="mu">Send a request. A parent will see it and answer.</p><p><select id="rk">${x.kinds.map(k=>`<option value="${k[0]}">${esc(k[1])}</option>`).join('')}</select> <select id="rm">${x.time_choices.map(m=>`<option value="${m}">${m} min</option>`).join('')}</select> <input id="rd" placeholder="App or website (for an unblock)"> <input id="rn" placeholder="Message (optional)" size="24"> <button class="a" data-a="ask">Send request</button></p>
  ${x.my_requests.length?tbl(['Your requests','Sent','Status'],x.my_requests.map(r=>[r.status=='Approved'?'allowed':r.status=='Denied'?'blocked':'',[r.text,r.created,r.status]])):''}</div>`}
const sp=st=>/^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d/.test(st)?[st.slice(0,10),st.slice(11,19)]:['',st];
const SORTS=['Newest first','Oldest first','By day','By hour of day'];
function logRows(){const rows=S.log.map((a,i)=>{const [d,t]=sp(a[0]);return {i,d,t,h:/^\d\d/.test(t)?+t.slice(0,2):99,e:a[1],g:a[2],r:a[3]}});
 let o=rows.filter(r=>(lf.day===''||(lf.day=='none'?r.d==='':r.d===lf.day))&&(lf.hour===''||r.h==+lf.hour)&&(lf.res===''||r.r===lf.res)&&(!lf.q.trim()||(r.e+' '+r.g+' '+r.r).toLowerCase().includes(lf.q.trim().toLowerCase())));
 if(lf.sort=='Oldest first')o.reverse();
 else if(lf.sort=='By day')o.sort((a,b)=>a.d<b.d?1:a.d>b.d?-1:a.i-b.i);
 else if(lf.sort=='By hour of day')o.sort((a,b)=>a.h-b.h||a.i-b.i);
 return [rows,o]}
function logTable(){const [all,o]=logRows();
 return `<p class="mu">${o.length} of ${all.length} entries</p>${tbl(['Day','Time','Event','App / Website','Result'],o.map(r=>[TAG[r.r]||'',[r.d||'Earlier',r.t,r.e,r.g,r.r]]))}`}
function logPage(){const all=S.log.map(a=>sp(a[0])[0]),days=[...new Set(all.filter(d=>d))].sort().reverse(),none=all.some(d=>!d),
 today=new Date(),iso=d=>d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0'),td=iso(today),yd=iso(new Date(today.getTime()-864e5)),
 dl=d=>d+(d==td?' (today)':d==yd?' (yesterday)':'');
 return `<h1>Log</h1><p class="mu">Everything LeafyGreen has done and every change made. Filter it by day, hour or result, and choose how it is ordered.</p>
 <div class="card lf" data-keep><label>Day <select id="lfd"><option value="">All days</option>${days.map(d=>`<option value="${d}" ${lf.day==d?'selected':''}>${dl(d)}</option>`).join('')}${none?`<option value="none" ${lf.day=='none'?'selected':''}>Earlier (no date)</option>`:''}</select></label>
 <label>Hour <select id="lfh"><option value="">All hours</option>${[...Array(24).keys()].map(h=>{const t=String(h).padStart(2,'0');return `<option value="${h}" ${lf.hour!==''&&+lf.hour==h?'selected':''}>${t}:00 - ${t}:59</option>`}).join('')}</select></label>
 <label>Result <select id="lfr"><option value="">All results</option>${['Blocked','Allowed','Limited','Failed','Info'].map(r=>`<option ${lf.res==r?'selected':''}>${r}</option>`).join('')}</select></label>
 <label>Sort by <select id="lfs">${SORTS.map(r=>`<option ${lf.sort==r?'selected':''}>${r}</option>`).join('')}</select></label>
 <label>Search <input id="lfq" value="${esc(lf.q)}" size="22"></label> <button data-a="lfreset">Reset Filters</button> <button data-a="lfrefresh">Refresh</button></div>
 <div id="logt">${logTable()}</div>`}
const P={
Requests(){return '<h1>Requests</h1><p class="mu">Approve or deny what the child has asked for.</p>'+reqPanel(true)},
Log(){return S.log?logPage():'<p class="mu">Loading...</p>'},
Dashboard(){const x=S;return `<h1>Dashboard</h1><p class="mu">${esc(x.note)}</p>
 <div class="cards">${[[x.used,'Screen time today'],[x.left,'Time remaining'],[x.n_blocked,'Blocked attempts'],[x.n_coupons,'Coupons available']].map(c=>`<div class="card"><div class="num">${esc(c[0])}</div><div class="mu">${c[1]}</div></div>`).join('')}</div>
 <div class="row"><div class="card" style="text-align:center">${shield()}${smartBox()}</div><div class="card"><div class="qh"><h2>Quick Actions</h2></div>
 ${quick()}
 <h2>Bonus time</h2><div class="g"><button data-a="bonus" data-minutes="30">Add 30 min</button><button data-a="bonus" data-minutes="60">Add 1 hour</button></div></div></div>
 ${S.role=='Child'?askCard():''}
 ${reqOpen?reqPanel():''}
 <div class="bar"><h2>Recent Activity</h2><button data-a="clearlog">Clear Log</button></div>
 ${tbl(['Time','Event','App / Website','Result'],x.activity.map(r=>[TAG[r[3]]||'',r]))}`},
'Time Limits'(){const x=S;return `<h1>Time Limits</h1><p class="mu">Set how much screen time is allowed each day.</p>
 <div class="card"><div class="tw"><table><tr><th>Day</th><th>Limit</th><th>Hours</th><th>Minutes</th></tr>${x.days.map(d=>{const l=x.limits[d];return `<tr><td>${d}</td><td><input type="checkbox" id="e${d}" ${l.enabled?'checked':''}></td><td><input type="number" id="h${d}" min="0" max="24" value="${l.minutes/60|0}"></td><td><input type="number" id="m${d}" min="0" max="59" step="5" value="${l.minutes%60}"></td></tr>`}).join('')}</table></div></div>
 <div class="card" style="margin-top:12px"><h2>Bedtime</h2><p><label><input type="checkbox" id="be" ${x.bedtime.enabled?'checked':''}> Lock the device overnight</label></p>
 <p>From <input id="bs" size="5" value="${x.bedtime.start}"> to <input id="bf" size="5" value="${x.bedtime.end}"> <span class="mu">24-hour, HH:MM</span></p>
 <p>Screen time alerts (up to 3) ${[0,1,2].map(i=>`<select class="al"><option value="">Off</option>${x.alert_choices.map(m=>`<option value="${m}" ${x.alerts[i]===m?'selected':''}>${m==1?'1 minute':m+' minutes'}</option>`).join('')}</select>`).join(' ')}</p><p class="mu s">Shown this long before time runs out. Anyone can change these.</p></div>
 <p><button class="a" data-a="limits">Save Changes</button></p>`},
'Always Blocked'(){return lst('blocked')},
'Always Allowed'(){return lst('allowed')},
'Limited Apps'(){return `<h1>Limited Apps</h1><p class="mu">Give specific apps their own daily time limit. When it is used up, the app is closed until tomorrow.</p>
 <div class="card"><input id="nm" placeholder="App (e.g. Game.exe)"> <input type="number" id="mn" value="60" min="1" max="1440"> min <button class="a" data-a="lim_add">Add App</button></div>
 ${tbl(['App','Daily Limit (min)','Used Today (min)','Status',''],S.limited.map(r=>[r.tag,[r.name,r.limit,r.used,r.status],`<button class="d" data-a="lim_remove" data-name="${esc(r.name)}">Remove</button>`]))}`},
'Extra Time Coupons'(){return `<h1>Extra Time Coupons</h1><p class="mu">Create coupons that grant bonus screen time when redeemed.</p>
 <div class="card"><input type="number" id="mn" value="15" min="1" max="480"> min <input id="nt" placeholder="Note (optional)"> <button class="a" data-a="cp_new">Create Coupon</button></div>
 ${tbl(['Code','Minutes','Note','Created','Status',''],S.coupons.map(c=>[c.status=='Unused'?'allowed':'muted',[c.code,c.minutes,c.note,c.created,c.status],S.role=='Lite'?'':(c.status=='Unused'?`<button data-a="cp_redeem" data-code="${c.code}">Redeem</button> `:'')+`<button class="d" data-a="cp_del" data-code="${c.code}">Delete</button>`]))}`}};
function banner(){if(S.days_left==null||S.days_left>S.warn_days)return '';
 const d=S.days_left,g=S.grace==null?5:S.grace;
 const rtail=' Renew it with a new key, and activate it in the accounts tab.';
 const ptail=' Renew by purchasing a new key and activate it in the accounts tab.';
 let cls,msg;
 if(d>1){cls='lo';msg='Your subscription expires in '+d+' days.'+rtail;}
 else if(d===1){cls='or';msg='Your subscription expires in 1 day.'+rtail;}
 else if(d===0){cls='or';msg='Your subscription expires today.'+rtail;}
 else{cls='red';const off=d+g+1;
  if(off>0)msg='Your subscription has expired. Protection will remain active for the next '+off+' day'+(off===1?'':'s')+'.'+ptail;
  else msg="Your subscription has expired. Protection on your child's device is no longer active."+ptail;}
 return `<div class="banner ${cls}">${esc(msg)}</div>`}
function draw(){const el=$('#app');
 if(!tok||!S){$('#hs').textContent='';el.innerHTML=`<main><div class="card" style="max-width:340px;margin:40px auto"><h2>Sign in to the Web Dashboard</h2>
  <p>Username<br><input id="un" autocomplete="username" style="width:100%"></p><p>Password<br><input id="pw" type="password" autocomplete="current-password" style="width:100%"></p>
  <button class="a" data-a="login">Sign in</button><p id="err" style="color:#b3261e"></p><p><a href="#" data-a="forgot" class="s">Forgot your password?</a></p>
  <div id="fg" style="display:none;border-top:1px solid var(--bd);padding-top:10px"><p class="mu s">Enter the device PIN shown on the My Account tab of the LeafyGreen window, then your username and a new password (at least 6 characters). An unused username creates a Complete account if there is room for one.</p>
  <p>Device PIN<br><input id="rpin" type="password" inputmode="numeric" maxlength="4" autocomplete="off" style="width:100px"></p><p>Username<br><input id="run" style="width:100%"></p><p>New password<br><input id="rpw" type="password" autocomplete="new-password" style="width:100%"></p>
  <button class="a" data-a="reset">Set password</button></div></div></main>`;
  const pw=$('#pw');if(pw)pw.addEventListener('keydown',e=>{if(e.key=='Enter')login()});
  const rp=$('#rpw');if(rp)rp.addEventListener('keydown',e=>{if(e.key=='Enter')resetpw()});return}
 if(!tabs().includes(tab))tab=tabs()[0];
 $('#hs').innerHTML=(S.protect?'\u25CF Protection on':'\u25CB Protection off')+' &nbsp; <span class="s">'+esc(S.user)+' ('+esc(S.role)+')</span> &nbsp; <button data-a="out">Sign out</button>';
 el.innerHTML=banner()+`<nav>${tabs().map(t=>`<button data-a="tab" data-t="${t}" class="${t==tab?'on':''}">${t}</button>`).join('')}</nav><main class="${S.role=='Child'?'ro':''}">${P[tab]()}</main>`;
 if(S.role=='Child'){const n=document.createElement('p');n.className='mu s';n.textContent='You can look at all the settings, send requests and change your screen time alerts. Only a parent can change anything else.';$('main').prepend(n)}}
document.addEventListener('change',e=>{if(e.target.classList&&e.target.classList.contains('al'))act('alerts',{times:[...document.querySelectorAll('.al')].map(s=>s.value)})});
document.addEventListener('click',e=>{const b=e.target.closest('[data-a]');if(!b)return;const a=b.dataset.a,x=Object.assign({},b.dataset);
 if(a=='login')return login();if(a=='reset')return resetpw();if(a=='forgot'){e.preventDefault();$('#fg').style.display='block';return}if(a=='out')return out();if(a=='tab'){tab=x.t;if(tab=='Log'){S.log=null;draw();return load().catch(()=>draw())}return draw()}
 if(a=='ask'){x.kind=$('#rk').value;x.minutes=$('#rm').value;x.detail=$('#rd').value;x.note=$('#rn').value;return act('new_request',x)}
 if(a=='qreq'){reqOpen=!reqOpen;return draw()}
 if(a=='req_apply'){const dec={};document.querySelectorAll('[data-req]').forEach(s=>{if(s.value)dec[s.dataset.req]=s.value});return act('req_review',{decisions:dec}).then(()=>{reqOpen=false;draw()})}
 if(a=='qcoupon'){const m=prompt('Bonus minutes for the new coupon?','15');if(m===null)return;return act('cp_new',{minutes:m,note:''})}
 if(a=='lfrefresh')return load().catch(()=>{});
 if(a=='lfreset'){lf={day:'',hour:'',res:'',q:'',sort:'Newest first'};return draw()}
 if(a=='smartsafe')return act('smartsafe',{on:b.checked});
 if(a=='pause'&&$('#pz'))x.minutes=$('#pz').value;
 if(a=='add'){x.name=$('#nm').value;x.kind=$('#ty').value}
 if(a=='lim_add'){x.name=$('#nm').value;x.minutes=$('#mn').value}
 if(a=='cp_new'){x.minutes=$('#mn').value;x.note=$('#nt').value}
 if(a=='limits'){x.limits={};S.days.forEach(d=>x.limits[d]={enabled:$('#e'+d).checked,minutes:Math.round((+$('#h'+d).value||0)*60+(+$('#m'+d).value||0))});x.bedtime={enabled:$('#be').checked,start:$('#bs').value,end:$('#bf').value}}
 if(['clearlog','remove','lim_remove','cp_del'].includes(a)&&!confirm('Are you sure?'))return;
 if(a=='protect')popNext=true;act(a,x)});
document.addEventListener('input',e=>{if(e.target.id=='lfq'){lf.q=e.target.value;$('#logt').innerHTML=logTable()}});
document.addEventListener('change',e=>{const m={lfd:'day',lfh:'hour',lfr:'res',lfs:'sort'}[e.target.id];if(m){lf[m]=e.target.value;$('#logt').innerHTML=logTable()}});
document.addEventListener('toggle',e=>{if(e.target.id=='hid')hidOpen=e.target.open},true);
setInterval(()=>{if(tok&&(tab=='Dashboard'||tab=='Requests')&&!reqOpen&&![...document.querySelectorAll('[data-req]')].some(s=>s.value)&&!/INPUT|SELECT/.test(document.activeElement.tagName))load().catch(()=>{})},10000);
if(tok)load().catch(()=>draw());else draw();
</script></body></html>'''


def local_ip():
    """This computer's address on the Wi-Fi / home network."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


class WebDashboard:
    """Web Dashboard: a small web server so a parent can open
    http://KIDIP:PORT in any browser on the same network.

    Requests are handled on server threads, but every read or change of the
    settings is handed to the Tk main thread (the same thread the app-blocking
    monitor runs on), so nothing is touched from two threads at once.
    Everything except the page itself needs a signed-in session. Parents sign
    in with their own username and password (My Account tab); too many wrong
    tries causes a short lockout.
    """

    def __init__(self, app, port):
        self.app = app
        self.port = port
        self.jobs = queue.Queue()
        self.sessions = {}
        self.tries = 0
        self.lock_until = 0.0
        self.lock = threading.Lock()
        self.httpd = None

    def start(self):
        """Returns an error message, or None when the server is running."""
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def _send(self, code, payload, ctype="application/json"):
                body = payload if isinstance(payload, bytes) \
                    else json.dumps(payload).encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", ctype + "; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Frame-Options", "DENY")
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                path, _, query = self.path.partition("?")
                if path in ("/", "/index.html"):
                    self._send(200, WEB_PAGE.encode("utf-8"), "text/html")
                else:
                    self._send(404, {"ok": False})

            def do_POST(self):
                try:
                    size = int(self.headers.get("Content-Length") or 0)
                    if size > 20000:
                        return self._send(413, {"ok": False})
                    req = json.loads(self.rfile.read(size) or b"{}")
                    if not isinstance(req, dict):
                        raise ValueError
                except (ValueError, OSError):
                    return self._send(400, {"ok": False, "msg": "Bad request."})
                code, body = outer.handle(self.path, req,
                                          self.headers.get("X-Token", ""))
                self._send(code, body)

        try:
            self.httpd = ThreadingHTTPServer(("0.0.0.0", self.port), Handler)
        except OSError as exc:
            return str(exc)
        threading.Thread(target=self.httpd.serve_forever,
                         daemon=True).start()
        self.app.after(100, self._pump)
        return None

    def stop(self):
        if self.httpd is not None:
            self.httpd.shutdown()
            self.httpd.server_close()
            self.httpd = None

    def _pump(self):
        try:
            while True:
                fn, box, done = self.jobs.get_nowait()
                try:
                    box.append(fn())
                except Exception as exc:
                    box.append({"ok": False, "msg": f"Error: {exc}"})
                done.set()
        except queue.Empty:
            pass
        try:
            self.app.after(100, self._pump)
        except tk.TclError:
            pass

    def on_main(self, fn):
        box, done = [], threading.Event()
        self.jobs.put((fn, box, done))
        if not done.wait(8):
            return {"ok": False, "msg": "The app is busy. Try again."}
        return box[0]

    def valid(self, token):
        """The signed-in username for this token, or None."""
        now = time.time()
        with self.lock:
            for t in [t for t, s in self.sessions.items() if s["exp"] < now]:
                del self.sessions[t]
            session = self.sessions.get(token)
            if session is not None:
                session["exp"] = now + UNLOCK_SECONDS
                return session["user"]
        return None

    def _as(self, user, fn):
        """Runs fn(role) on the main thread for this signed-in person. If
        their account was removed meanwhile, they are signed out."""
        role = self.app.data.parent_role(user)
        if role is None:
            with self.lock:
                for t in [t for t, s in self.sessions.items()
                          if s["user"] == user]:
                    del self.sessions[t]
            return {"ok": False, "gone": True,
                    "msg": "This account no longer exists."}
        return fn(role)

    def handle(self, path, req, token):
        if path == "/api/login":
            return 200, self.on_main(lambda: self.login(
                str(req.get("username", "")), str(req.get("password", ""))))
        if path == "/api/parent_reset":
            return 200, self.on_main(lambda: self.parent_reset(
                str(req.get("pin", "")), str(req.get("username", "")),
                str(req.get("password", ""))))
        user = self.valid(token)
        if not user:
            return 401, {"ok": False, "msg": "Please sign in."}
        if path == "/api/state":
            body = self.on_main(lambda: self._as(user, lambda role: {
                "ok": True,
                "state": self.state(bool(req.get("log")), role, user)}))
        elif path == "/api/act":
            body = self.on_main(lambda: self._as(
                user, lambda role: self.act(req, role, user)))
        else:
            return 404, {"ok": False}
        return (401 if body.get("gone") else 200), body

    def _locked(self):
        wait = int(self.lock_until - time.time()) + 1
        return f"Too many tries. Try again in {wait} seconds."

    def _miss(self, what):
        """Count a wrong guess; returns the message to show."""
        self.tries += 1
        if self.tries >= MAX_TRIES:
            self.tries = 0
            self.lock_until = time.time() + LOCKOUT_SECONDS
            return self._locked()
        return f"{what} {MAX_TRIES - self.tries} tries left."

    def login(self, username, password):
        d = self.app.data
        if not d.parents:
            return {"ok": False, "msg": "No parent accounts yet. Add one on "
                    "the My Account tab in the LeafyGreen window."}
        if time.time() < self.lock_until:
            return {"ok": False, "msg": self._locked()}
        if not d.check_parent(username, password):
            return {"ok": False,
                    "msg": self._miss("Wrong username or password.")}
        self.tries = 0
        token = secrets.token_hex(16)
        name = d._find_parent(username)["username"]
        with self.lock:
            self.sessions[token] = {"exp": time.time() + UNLOCK_SECONDS,
                                    "user": name}
        d.log("Web Dashboard sign-in", f"{name} ({d.parent_role(name)})")
        return {"ok": True, "token": token}

    def parent_reset(self, pin, username, password):
        """Forgot password: the device PIN sets a new password, or creates
        a parent account if the name is new and there is room."""
        d = self.app.data
        if time.time() < self.lock_until:
            return {"ok": False, "msg": self._locked()}
        if not d.check_pin(pin):
            return {"ok": False, "msg": self._miss("Wrong device PIN.")}
        self.tries = 0
        username = username.strip()
        if not username:
            return {"ok": False, "msg": "Enter a username."}
        if len(password) < 6:
            return {"ok": False, "msg": "The password must be at least 6 "
                    "characters."}
        if d.set_parent_password(username, password):
            d.log("Parent password reset (web)", username)
            msg = "Password updated. You can sign in now."
        elif d.add_parent(username, password):
            d.log("Parent added (web, device PIN)", username)
            msg = ("Account created with the Complete role. You can sign "
                   "in now.")
        else:
            return {"ok": False, "msg": "Four accounts already exist. "
                    "Use one of their usernames, or remove one on the "
                    "My Account tab."}
        self.app._on_tab_changed()
        return {"ok": True, "msg": msg}

    def state(self, full_log=False, role="Complete", user=""):
        d = self.app.data
        d.prune_hidden()
        today = DAYS[datetime.date.today().weekday()]
        limit = d.limits[today]
        if limit["enabled"]:
            left = fmt_minutes(max(0, limit["minutes"] + d.bonus_min
                                   - d.used_today_min))
            note = (f"{today}'s limit: {fmt_minutes(limit['minutes'])}"
                    f"   |   Bonus time today: +{d.bonus_min} min")
        else:
            left, note = "No limit", f"No time limit is set for {today}."
        limited = []
        for e in d.limited:
            status, tag = LimitedAppsPage._status(e)
            limited.append({"name": e["name"], "limit": e["limit"],
                            "used": int(e.get("used_sec", 0) // 60),
                            "status": status, "tag": tag})
        pause_min = None
        if d.internet_paused and d.pause_until:
            pause_min = max(1, math.ceil((d.pause_until - time.time()) / 60))
        today_text = today_str()
        out = {
            "quick": d.quick_actions,
            "pauses": [[label, m] for label, m in PAUSE_CHOICES],
            "pause_min": pause_min,
            "pending": [{"id": r["id"], "text": Data.describe_request(r),
                         "note": r["note"], "created": r["created"]}
                        for r in d.pending_requests()],
            "protect": d.protection_effective, "paused": d.internet_paused,
            "smart": d.smartsafe_enabled,
            "used": fmt_minutes(d.used_today_min), "left": left, "note": note,
            "n_blocked": sum(1 for a in d.visible_activity()
                             if a[3] in ("Blocked", "Limited")),
            "n_coupons": sum(1 for c in d.coupons if c["status"] == "Unused"),
            "activity": [[short_stamp(a[0], today_text)] + list(a[1:])
                         for a in d.visible_activity()[:50]],
            "days": DAYS, "limits": d.limits, "bedtime": d.bedtime,
            "expiry": d.expiry, "days_left": d.days_left(),
            "warn_days": d.expiry_warn_days, "grace": EXPIRY_GRACE_DAYS,
            "alerts": list(d.warn_alerts),
            "alert_choices": list(ALERT_CHOICES),
            "n_pending": len(d.pending_requests()),
            "blocked": d.blocked, "allowed": d.allowed,
            "hidden": d.hidden,
            "limited": limited, "coupons": d.coupons,
        }
        out["role"], out["user"] = role, user
        out["kinds"] = [[k, v] for k, v in REQUEST_KINDS.items()]
        out["time_choices"] = list(TIME_REQUEST_CHOICES)
        if role == "Lite":
            keep = ("role", "user", "protect", "pending", "coupons",
                    "n_coupons", "n_pending", "expiry", "days_left",
                    "warn_days", "grace")
            return {k: out[k] for k in keep}
        if role == "Child":
            out["pending"] = []
            out["my_requests"] = [
                {"text": Data.describe_request(r), "created": r["created"],
                 "status": r["status"]} for r in d.requests[:8]]
        if full_log:
            out["log"] = [list(a) for a in d.visible_activity()]
        return out

    @staticmethod
    def _int(value, low, high, what="a number"):
        try:
            n = int(value)
        except (TypeError, ValueError):
            raise ValueError(f"Enter {what} as a whole number.")
        if not low <= n <= high:
            raise ValueError(f"Enter {what} between {low} and {high}.")
        return n

    def act(self, req, role="Complete", user=""):
        a = req.get("a")
        allowed = ROLE_ACTIONS.get(role)
        if allowed is not None and a not in allowed:
            return {"ok": False, "state": self.state(False, role, user),
                    "msg": "You have to be a parent to change that."
                    if role == "Child" else
                    f"Your account ({role}) is not allowed to do that."}
        if self.app.data.settings_locked:
            return {"ok": False, "state": self.state(False, role, user),
                    "msg": "The subscription has expired. Settings are "
                    "locked until a new key is activated on the child's "
                    "computer (My Account tab)."}
        try:
            msg = self._do(a, req)
        except ValueError as exc:
            return {"ok": False, "msg": str(exc),
                    "state": self.state(False, role, user)}
        self.app.update_header()
        self.app._on_tab_changed()
        return {"ok": True, "msg": msg,
                "state": self.state(False, role, user)}

    def _do(self, a, req):
        app, d = self.app, self.app.data

        def log(event, target):
            d.log(event + " (web)", target)

        if a == "protect":
            d.protection_enabled = not d.protection_enabled
            on = d.protection_enabled
            log("Protection " + ("enabled" if on else "disabled"),
                "All devices")
            return "Protection turned " + ("on" if on else "off") + "."
        if a == "alerts":
            times = req.get("times")
            if not isinstance(times, list) or len(times) > MAX_ALERTS:
                raise ValueError("Choose up to 3 alert times.")
            picked = []
            for t in times:
                if t in (None, "", "Off"):
                    continue
                try:
                    minutes = int(t)
                except (TypeError, ValueError):
                    minutes = None
                if minutes not in ALERT_CHOICES:
                    raise ValueError("Pick the alert times from the list.")
                picked.append(minutes)
            d.warn_alerts = clean_alerts(picked)
            app.page(TimeLimitsPage).load_alerts()
            log("Screen time alerts changed", describe_alerts(d.warn_alerts))
            return describe_alerts(d.warn_alerts)
        if a == "new_request":
            try:
                minutes = int(req.get("minutes") or 0)
            except (TypeError, ValueError):
                minutes = 0
            ok, message = d.new_request(
                str(req.get("kind", "")), str(req.get("detail", "")),
                minutes, str(req.get("note", "")))
            if not ok:
                raise ValueError(message)
            return message
        if a == "smartsafe":
            on = bool(req.get("on"))
            d.smartsafe_enabled = on
            log("SmartSafe " + ("enabled" if on else "disabled"),
                "All websites")
            return "SmartSafe turned " + ("on" if on else "off") + "."
        if a == "pause":
            if d.internet_paused:
                d.internet_paused = False
                d.pause_until = 0.0
                log("Internet resumed", "All devices")
                return "Internet resumed."
            minutes = self._int(req.get("minutes", 30), 0, 1440, "minutes")
            if minutes not in {m for _, m in PAUSE_CHOICES}:
                raise ValueError("Choose how long to pause the internet.")
            d.internet_paused = True
            d.pause_until = time.time() + minutes * 60 if minutes else 0.0
            span = f"for {minutes} minutes" if minutes else "until resumed"
            log("Internet paused", f"All devices ({span})")
            return (f"Internet paused {span}. This page will not load until "
                    "it is back on."
                    + ("" if minutes else " Resume it from the LeafyGreen "
                       "window."))
        if a == "req_review":
            decisions = req.get("decisions")
            if not isinstance(decisions, dict):
                raise ValueError("Bad choice.")
            done = []
            for rid, choice in decisions.items():
                if choice in ("approve", "deny"):
                    message = d.review_request(str(rid), choice == "approve")
                    if message:
                        done.append(message)
            if not done:
                raise ValueError("Nothing was decided.")
            return (f"{len(done)} request(s) answered. The child is told on "
                    "their computer.")
        if a == "bonus":
            m = self._int(req.get("minutes"), 1, 480, "minutes")
            d.bonus_min += m
            log("Bonus time added", f"+{m} min")
            return f"Added {m} minutes of bonus time."
        if a == "clearlog":
            d.activity.clear()
            return "Activity log cleared."

        if a in ("hide", "unhide"):
            name = str(req.get("name", "")).strip().lower()
            row = next((r for r in d.allowed if r[0].lower() == name), None)
            if row is None:
                raise ValueError("That item is no longer in the list.")
            if a == "hide":
                if name not in d.hidden:
                    d.hidden.append(name)
                d.purge_hidden_log()
                return f"Hid '{row[0]}'. It stays allowed."
            d.hidden = [h for h in d.hidden if h != name]
            return f"Unhid '{row[0]}'."

        if a in ("add", "remove", "move"):
            key = req.get("list")
            if key not in ("blocked", "allowed"):
                raise ValueError("Unknown list.")
            other_key = "allowed" if key == "blocked" else "blocked"
            title = "Always Blocked" if key == "blocked" else "Always Allowed"
            other_title = "Always Allowed" if key == "blocked" \
                else "Always Blocked"
            items, other = getattr(d, key), getattr(d, other_key)
            name = str(req.get("name", "")).strip()
            if a == "add":
                kind = req.get("kind")
                if kind not in ("App", "Website"):
                    raise ValueError("Choose App or Website.")
                if kind == "Website":
                    name = normalize_site_name(name)
                    if name is None:
                        raise ValueError("Enter a full website address such "
                                         "as example.com (no spaces).")
                else:
                    name = normalize_app_name(name)
                if not name:
                    raise ValueError("Type a website or app name first.")
                low = name.lower()
                if any(r[0].lower() == low for r in items):
                    raise ValueError(f"'{name}' is already in this list.")
                if any(r[0].lower() == low for r in other):
                    raise ValueError(f"'{name}' is already in {other_title}. "
                                     "Use the move button to switch it.")
                if kind == "App" and key == "blocked" and app.is_protected(name):
                    raise ValueError(f"'{name}' is needed by Windows or by "
                                     "LeafyGreen itself, so it can't be "
                                     "blocked.")
                items.append([name, kind, today_str()])
                log(f"Added to {title}", name)
                return f"Added '{name}' to {title}."
            row = next((r for r in items if r[0].lower() == name.lower()), None)
            if row is None:
                raise ValueError("That item is no longer in the list.")
            if a == "remove":
                items.remove(row)
                log(f"Removed from {title}", row[0])
                return f"Removed '{row[0]}'."
            if other_key == "blocked" and row[1] == "App" \
                    and app.is_protected(row[0]):
                raise ValueError(f"'{row[0]}' is needed by Windows or by "
                                 "LeafyGreen itself, so it can't be "
                                 "blocked.")
            items.remove(row)
            other.append([row[0], row[1], today_str()])
            log(f"Moved to {other_title}", row[0])
            return f"Moved '{row[0]}' to {other_title}."

        if a == "limits":
            limits = req.get("limits")
            if not isinstance(limits, dict):
                raise ValueError("Bad time limits.")
            new = {}
            for day in DAYS:
                e = limits.get(day)
                minutes = e.get("minutes") if isinstance(e, dict) else None
                if isinstance(minutes, float) and math.isfinite(minutes):
                    minutes = int(round(minutes))
                if not (isinstance(e, dict) and isinstance(e.get("enabled"), bool)
                        and type(minutes) is int and 0 <= minutes <= 1440):
                    raise ValueError(f"The limit for {day} must be 24 hours "
                                     "or less.")
                new[day] = {"enabled": e["enabled"], "minutes": minutes}
            b = req.get("bedtime")
            if not (isinstance(b, dict) and isinstance(b.get("enabled"), bool)
                    and TIME_RE.match(str(b.get("start", "")).strip())
                    and TIME_RE.match(str(b.get("end", "")).strip())):
                raise ValueError("Bedtime times must look like 21:00 "
                                 "(HH:MM, 24-hour).")
            d.limits = new
            d.bedtime = {"enabled": b["enabled"], "start": b["start"].strip(),
                         "end": b["end"].strip()}
            app.page(TimeLimitsPage).load()
            log("Time limits saved", "All days")
            return "Time limits saved. The screen locks when time runs out or at bedtime."

        if a == "lim_add":
            name = normalize_app_name(str(req.get("name", "")))
            minutes = self._int(req.get("minutes"), 1, 1440, "minutes")
            if not name:
                raise ValueError("Enter an app name.")
            if app.is_protected(name):
                raise ValueError(f"'{name}' is needed by Windows or by "
                                 "LeafyGreen itself, so it can't be limited.")
            if any(e["name"].lower() == name.lower() for e in d.limited):
                raise ValueError(f"'{name}' already has a limit.")
            d.limited.append({"name": name, "limit": minutes, "used_sec": 0.0})
            log("App limit added", f"{name} ({minutes} min)")
            return f"Added a {minutes}-minute limit for {name}."
        if a == "lim_remove":
            name = str(req.get("name", "")).lower()
            entry = next((e for e in d.limited
                          if e["name"].lower() == name), None)
            if entry is None:
                raise ValueError("That app is no longer in the list.")
            d.limited.remove(entry)
            log("App limit removed", entry["name"])
            return f"Removed the limit for {entry['name']}."

        if a == "cp_new":
            minutes = self._int(req.get("minutes"), 1, 480, "minutes")
            note = str(req.get("note", "")).strip()[:60]
            code = d.add_coupon(minutes, note)
            return f"Created coupon {code}."
        if a in ("cp_redeem", "cp_del"):
            code = str(req.get("code", ""))
            coupon = next((c for c in d.coupons if c["code"] == code), None)
            if coupon is None:
                raise ValueError("That coupon no longer exists.")
            if a == "cp_del":
                d.coupons.remove(coupon)
                log("Coupon deleted", code)
                return f"Deleted coupon {code}."
            if coupon["status"] != "Unused":
                raise ValueError("That coupon was already redeemed.")
            d.redeem_coupon(code)
            return f"Redeemed {code}: +{coupon['minutes']} minutes."
        raise ValueError("Unknown action.")


EXIT_PARENT_QUIT = 42
EXIT_ALREADY_RUNNING = 43
EXIT_SETTINGS_UNREADABLE = 44
NO_SESSION = 0xFFFFFFFF
RETRY_AFTER_SECONDS = 30

_MUTEX_HANDLES = []


def acquire_single_instance(name):
    """True if this is the only copy running (always True off Windows).
    "Access denied" means a copy running with higher rights (the installed
    SYSTEM one) already owns the name, so that counts as already running."""
    if sys.platform != "win32":
        return True
    try:
        k = ctypes.WinDLL("kernel32", use_last_error=True)
        k.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_int,
                                   ctypes.c_wchar_p]
        k.CreateMutexW.restype = ctypes.c_void_p
        k.CloseHandle.argtypes = [ctypes.c_void_p]
        handle = k.CreateMutexW(None, False, name)
        error = ctypes.get_last_error()
    except Exception:
        return True
    if not handle:
        return error != 5
    if error == 183:
        k.CloseHandle(handle)
        return False
    _MUTEX_HANDLES.append(handle)
    return True


class _StartupInfo(ctypes.Structure):
    """STARTUPINFOW (104 bytes on 64-bit Windows)."""
    _fields_ = [
        ("cb", ctypes.c_uint32), ("lpReserved", ctypes.c_wchar_p),
        ("lpDesktop", ctypes.c_wchar_p), ("lpTitle", ctypes.c_wchar_p),
        ("dwX", ctypes.c_uint32), ("dwY", ctypes.c_uint32),
        ("dwXSize", ctypes.c_uint32), ("dwYSize", ctypes.c_uint32),
        ("dwXCountChars", ctypes.c_uint32),
        ("dwYCountChars", ctypes.c_uint32),
        ("dwFillAttribute", ctypes.c_uint32), ("dwFlags", ctypes.c_uint32),
        ("wShowWindow", ctypes.c_uint16), ("cbReserved2", ctypes.c_uint16),
        ("lpReserved2", ctypes.c_void_p), ("hStdInput", ctypes.c_void_p),
        ("hStdOutput", ctypes.c_void_p), ("hStdError", ctypes.c_void_p),
    ]


class _ProcessInfo(ctypes.Structure):
    _fields_ = [("hProcess", ctypes.c_void_p), ("hThread", ctypes.c_void_p),
                ("dwProcessId", ctypes.c_uint32),
                ("dwThreadId", ctypes.c_uint32)]


ACTIVATION_KEY_SHA256 = (
    "541e973234cd8ef649600290ebf525a1e0f4ef66e691e9255840b54f4447155e")
SETUP_MAX_ACCOUNTS = 3
SETUP_REQUEST_LIMIT = 262144
SETUP_MAX_TRIES = 5
SETUP_LOCKOUT_SECONDS = 300
SETUP_REQUEST_MAX_AGE = 120
SETUP_ID = re.compile(r"[0-9a-f]{32}")


def activation_key_ok(text):
    digest = hashlib.sha256(str(text).strip().encode("utf-8")).hexdigest()
    return secrets.compare_digest(digest, ACTIVATION_KEY_SHA256)


def build_setup_data(cfg):
    """The Data for a finished setup, built from the (untrusted) choices in
    a setup request. Returns (data, None) or (None, "what is wrong")."""
    if not isinstance(cfg, dict):
        return None, "The setup information is missing."
    d = Data()
    d._apply({k: cfg[k] for k in ("limits", "bedtime", "allowed", "blocked",
                                  "limited") if k in cfg})
    allowed = {r[0].lower() for r in d.allowed}
    if any(r[0].lower() in allowed for r in d.blocked):
        return None, "Something is on both the allowed and blocked lists."
    accounts = cfg.get("accounts")
    if (not isinstance(accounts, list)
            or not 1 <= len(accounts) <= SETUP_MAX_ACCOUNTS):
        return None, f"Add between 1 and {SETUP_MAX_ACCOUNTS} accounts."
    roles = set()
    for a in accounts:
        if not isinstance(a, dict):
            return None, "An account is not valid."
        name, password = str(a.get("username", "")).strip(), \
            str(a.get("password", ""))
        role = a.get("role")
        if (not name or len(password) < 6 or role not in ROLES
                or not d.add_parent(name, password, role)):
            return None, f"The account '{name}' is not valid."
        roles.add(role)
    if not {"Complete", "Child"} <= roles:
        return None, "Add at least one Complete and one Child account."
    pin = cfg.get("new_pin")
    if not (isinstance(pin, str) and len(pin) == 4 and pin.isdigit()):
        return None, "The PIN must be 4 digits."
    d.set_pin(pin)
    d.protection_enabled = True
    d.setup_done = True
    d.log("Setup completed", "setup.py")
    return d, None


class SetupService:
    """Runs in the launcher (SYSTEM). poll() answers requests in the inbox."""

    def __init__(self, stop_app=None, directory=None, clock=time.monotonic):
        self.dir = directory or SETTINGS_DIR
        self.inbox = os.path.join(self.dir, "inbox")
        self.outbox = os.path.join(self.dir, "outbox")
        self.settings = os.path.join(self.dir, os.path.basename(SETTINGS_FILE))
        self.stop_app = stop_app
        self.clock = clock
        self.fails = 0
        self.locked_until = 0.0
        self._status = None
        self._status_at = -1e9

    def _failed(self, code, message):
        self.fails += 1
        if self.fails >= SETUP_MAX_TRIES:
            self.fails = 0
            self.locked_until = self.clock() + SETUP_LOCKOUT_SECONDS
            message += " Too many wrong tries: locked for 5 minutes."
        else:
            message += f" {SETUP_MAX_TRIES - self.fails} tries left."
        return {"ok": False, "code": code, "message": message}

    def handle(self, text):
        """Answer for one request (a dict). Never raises."""
        try:
            return self._handle(text)
        except Exception as exc:
            return {"ok": False, "code": "bad",
                    "message": f"The request could not be processed ({exc})."}

    def _handle(self, text):
        if self.clock() < self.locked_until:
            minutes = max(1, int((self.locked_until - self.clock()) // 60) + 1)
            return {"ok": False, "code": "locked",
                    "message": "Too many wrong tries. Wait about "
                    f"{minutes} minute(s) and try again."}
        try:
            req = json.loads(text)
        except ValueError:
            req = None
        if (not isinstance(req, dict) or req.get("v") != 1
                or req.get("type") not in ("check_pin", "setup")):
            return {"ok": False, "code": "bad",
                    "message": "That request could not be read."}
        data = Data.load(self.settings)
        if data.unreadable:
            return {"ok": False, "code": "unreadable", "message":
                    "LeafyGreen's settings file could not be read."}
        if data.setup_done and not data.check_pin(str(req.get("pin") or "")):
            return self._failed("pin", "That PIN is not correct.")
        if req["type"] == "check_pin":
            self.fails = 0
            return {"ok": True, "code": "ok", "setup_done": data.setup_done}
        key = str(req.get("key") or "")
        ok, expiry, kerr = data.validate_activation(key)
        if not ok:
            return self._failed("key", kerr or "That key is not correct.")
        new, error = build_setup_data(req.get("config"))
        if error:
            return {"ok": False, "code": "invalid", "message": error}
        new.key_log = list(data.key_log)
        new.expiry = expiry
        if data.key_entry(key) is None:
            new.key_log.append({"key": Data._key_norm(key), "expiry": expiry,
                                "recorded": today_str()})
        if self.stop_app:
            self.stop_app()
        error = Data.write(json.dumps(new.to_dict(), sort_keys=True),
                           self.settings)
        if error:
            return {"ok": False, "code": "write",
                    "message": f"The settings could not be saved: {error}"}
        self.fails = 0
        self._status_at = -1e9
        return {"ok": True, "code": "done", "message": "Setup saved."}

    def _write_json(self, name, obj):
        path = os.path.join(self.outbox, name)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(obj, f)
        os.replace(tmp, path)

    def _refresh_status(self):
        if self.clock() - self._status_at < 30:
            return
        self._status_at = self.clock()
        done = Data.load(self.settings).setup_done
        if done != self._status:
            self._status = done
        self._write_json("status.json", {"setup_done": done})

    def poll(self):
        """Look at the inbox once. Cheap enough to call every second."""
        if not os.path.isdir(self.inbox):
            return
        os.makedirs(self.outbox, exist_ok=True)
        self._refresh_status()
        now = time.time()
        for name in os.listdir(self.outbox):
            path = os.path.join(self.outbox, name)
            if (name != "status.json" and name.endswith(".json")
                    and now - os.path.getmtime(path) > 120):
                try:
                    os.remove(path)
                except OSError:
                    pass
        for name in sorted(os.listdir(self.inbox)):
            path = os.path.join(self.inbox, name)
            rid = name[:-5]
            if not name.endswith(".json") or not SETUP_ID.fullmatch(rid):
                continue
            try:
                age = now - os.path.getmtime(path)
                if age < 0.7:
                    continue
                with open(path, "rb") as f:
                    raw = f.read(SETUP_REQUEST_LIMIT + 1)
            except OSError:
                continue
            if age > SETUP_REQUEST_MAX_AGE:
                result = {"ok": False, "code": "expired",
                          "message": "That request is too old. Try again."}
            elif len(raw) > SETUP_REQUEST_LIMIT:
                result = {"ok": False, "code": "bad",
                          "message": "That request is too large."}
            else:
                result = self.handle(raw.decode("utf-8", "replace"))
            try:
                self._write_json(rid + ".json", result)
                os.remove(path)
            except OSError:
                pass
            self._status_at = -1e9
            self._refresh_status()


class SessionLauncher:
    """Keeps LeafyGreen running inside the child's Windows session.

    Started at boot by a scheduled task that runs as SYSTEM, so a standard
    (non-admin) account can neither end it nor change its files. Whenever the
    child's account is the one signed in at the console, it starts the app
    in that session with SYSTEM rights, and starts it again if it stops. The
    one exception is a parent closing the window with the PIN (exit code
    EXIT_PARENT_QUIT); then it leaves the app closed until the next sign-in.
    Problems are written to launcher.log in the data folder.
    """

    def __init__(self, child_user):
        self.user = child_user.strip().lower()
        self._last_log = None
        vp, u32, i32 = ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int
        k = ctypes.WinDLL("kernel32", use_last_error=True)
        a = ctypes.WinDLL("advapi32", use_last_error=True)
        w = ctypes.WinDLL("wtsapi32", use_last_error=True)
        e = ctypes.WinDLL("userenv", use_last_error=True)
        k.WTSGetActiveConsoleSessionId.restype = u32
        k.GetCurrentProcess.restype = vp
        k.WaitForSingleObject.argtypes = [vp, u32]
        k.WaitForSingleObject.restype = u32
        k.GetExitCodeProcess.argtypes = [vp, ctypes.POINTER(u32)]
        k.GetExitCodeProcess.restype = i32
        k.CloseHandle.argtypes = [vp]
        k.TerminateProcess.argtypes = [vp, u32]
        k.TerminateProcess.restype = i32
        a.OpenProcessToken.argtypes = [vp, u32, ctypes.POINTER(vp)]
        a.OpenProcessToken.restype = i32
        a.DuplicateTokenEx.argtypes = [vp, u32, vp, u32, u32,
                                       ctypes.POINTER(vp)]
        a.DuplicateTokenEx.restype = i32
        a.SetTokenInformation.argtypes = [vp, u32, vp, u32]
        a.SetTokenInformation.restype = i32
        a.CreateProcessAsUserW.argtypes = [
            vp, ctypes.c_wchar_p, vp, vp, vp, i32, u32, vp,
            ctypes.c_wchar_p, ctypes.POINTER(_StartupInfo),
            ctypes.POINTER(_ProcessInfo)]
        a.CreateProcessAsUserW.restype = i32
        w.WTSQuerySessionInformationW.argtypes = [
            vp, u32, u32, ctypes.POINTER(vp), ctypes.POINTER(u32)]
        w.WTSQuerySessionInformationW.restype = i32
        w.WTSFreeMemory.argtypes = [vp]
        e.CreateEnvironmentBlock.argtypes = [ctypes.POINTER(vp), vp, i32]
        e.CreateEnvironmentBlock.restype = i32
        e.DestroyEnvironmentBlock.argtypes = [vp]
        self.k, self.a, self.w, self.e = k, a, w, e

    def _log(self, message):
        if message == self._last_log:
            return
        self._last_log = message
        path = os.path.join(SETTINGS_DIR, "launcher.log")
        try:
            os.makedirs(SETTINGS_DIR, exist_ok=True)
            if os.path.exists(path) and os.path.getsize(path) > 200000:
                return
            with open(path, "a", encoding="utf-8") as f:
                f.write(f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S}  "
                        f"{message}\n")
        except OSError:
            pass

    def _session_user(self, sid):
        buf, size = ctypes.c_void_p(), ctypes.c_uint32()
        if not self.w.WTSQuerySessionInformationW(
                None, sid, 5, ctypes.byref(buf), ctypes.byref(size)):
            return ""
        try:
            return ctypes.wstring_at(buf.value) if buf.value else ""
        finally:
            self.w.WTSFreeMemory(buf)

    def _command(self):
        if getattr(sys, "frozen", False):
            return f'"{sys.executable}" --minimized --child "{self.user}"'
        return (f'"{sys.executable}" "{os.path.abspath(__file__)}" '
                f'--minimized --child "{self.user}"')

    def _spawn(self, sid):
        """Start the app in session `sid`. Returns a process handle."""
        k, a, e = self.k, self.a, self.e
        vp, u32 = ctypes.c_void_p, ctypes.c_uint32
        token, dup = vp(), vp()
        if not a.OpenProcessToken(k.GetCurrentProcess(), 0xF01FF,
                                  ctypes.byref(token)):
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            if not a.DuplicateTokenEx(token, 0x2000000, None, 2, 1,
                                      ctypes.byref(dup)):
                raise ctypes.WinError(ctypes.get_last_error())
        finally:
            k.CloseHandle(token)
        env = vp()
        have_env = False
        try:
            session = u32(sid)
            if not a.SetTokenInformation(dup, 12, ctypes.addressof(session),
                                         ctypes.sizeof(session)):
                raise ctypes.WinError(ctypes.get_last_error())
            have_env = bool(e.CreateEnvironmentBlock(ctypes.byref(env), dup,
                                                     False))
            info = _StartupInfo()
            info.cb = ctypes.sizeof(info)
            info.lpDesktop = "winsta0\\default"
            proc = _ProcessInfo()
            cmd = ctypes.create_unicode_buffer(self._command())
            ok = a.CreateProcessAsUserW(
                dup, None, cmd, None, None, False,
                0x400 if have_env else 0,
                env if have_env else None,
                os.path.dirname(sys.executable), ctypes.byref(info),
                ctypes.byref(proc))
            if not ok:
                raise ctypes.WinError(ctypes.get_last_error())
            k.CloseHandle(proc.hThread)
            return proc.hProcess
        finally:
            if have_env:
                e.DestroyEnvironmentBlock(env)
            k.CloseHandle(dup)

    def _exit_code(self, handle):
        code = ctypes.c_uint32()
        self.k.GetExitCodeProcess(handle, ctypes.byref(code))
        return code.value

    def cycle(self, st, now):
        """One look at the situation. `st` holds child, child_sid, quit_sid
        and wait_until between calls."""
        k = self.k
        if st["child"] is not None and k.WaitForSingleObject(st["child"], 0) == 0:
            code = self._exit_code(st["child"])
            k.CloseHandle(st["child"])
            st["child"] = None
            if code == EXIT_PARENT_QUIT:
                st["quit_sid"] = st["child_sid"]
            elif code in (EXIT_ALREADY_RUNNING, EXIT_SETTINGS_UNREADABLE):
                st["wait_until"] = now + RETRY_AFTER_SECONDS
                if code == EXIT_SETTINGS_UNREADABLE:
                    self._log("LeafyGreen could not read its settings "
                              "file; retrying in 30 seconds")
        sid = k.WTSGetActiveConsoleSessionId()
        if st["quit_sid"] is not None and sid != st["quit_sid"]:
            st["quit_sid"] = None
        if (st["child"] is None and sid != NO_SESSION
                and sid != st["quit_sid"] and now >= st["wait_until"]
                and self._session_user(sid).lower() == self.user):
            st["child"] = self._spawn(sid)
            st["child_sid"] = sid

    def _stop_app(self, st):
        """Ends the app in the child's session (the next cycle starts it
        again, with the new settings)."""
        if st["child"] is not None:
            self.k.TerminateProcess(st["child"], 1)
            self.k.WaitForSingleObject(st["child"], 5000)

    def run(self):
        st = {"child": None, "child_sid": None, "quit_sid": None,
              "wait_until": 0.0}
        service = SetupService(stop_app=lambda: self._stop_app(st))
        last_cycle = 0.0
        while True:
            try:
                if time.monotonic() - last_cycle >= 3:
                    last_cycle = time.monotonic()
                    self.cycle(st, last_cycle)
            except Exception as exc:
                self._log(f"Launcher error: {exc}")
            try:
                service.poll()
            except Exception as exc:
                self._log(f"Setup inbox error: {exc}")
            time.sleep(1)


class App(tk.Tk):
    def __init__(self, data=None):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("1040x780")
        self.minsize(940, 700)
        self.configure(bg=BG)
        apply_style(self)

        self.data = data if data is not None else Data.load()
        write_activation_keyfile(self.data.key_log)
        self._status_job = None
        self._last_saved = None
        self._last_save_check = 0.0
        self._last_refresh = 0.0
        self._last_error = None
        self._last_write_error = None
        self._last_core = None
        self._last_write_time = -999.0
        self._step_errors = {}
        self._last_ip_check = -999.0
        self._ip = None
        self.unlocked_until = 0.0
        self.lockout_until = 0.0
        self.failed_tries = 0
        self.web_status = tk.StringVar()
        self.web = None
        self.quit_by_parent = False
        self.countdown = None
        self.notifier = None

        header = ttk.Frame(self, style="Header.TFrame", padding=(20, 14))
        header.pack(fill="x")
        left = ttk.Frame(header, style="Header.TFrame")
        left.pack(side="left")
        ttk.Label(left, text=APP_NAME, style="Title.TLabel").pack(anchor="w")
        ttk.Label(left, text=APP_SUBTITLE, style="HeaderSub.TLabel").pack(
            anchor="w")
        right = ttk.Frame(header, style="Header.TFrame")
        right.pack(side="right")
        self.header_status = tk.StringVar()
        ttk.Label(right, textvariable=self.header_status,
                  style="HeaderSub.TLabel").grid(row=0, column=0,
                                                 columnspan=3, sticky="e")
        self.lock_status = tk.StringVar()
        ttk.Label(right, textvariable=self.lock_status,
                  style="HeaderSub.TLabel").grid(row=1, column=0,
                                                 columnspan=3, sticky="e")
        self.lock_btn_text = tk.StringVar(value="Unlock")
        ttk.Button(right, textvariable=self.lock_btn_text,
                   command=self.toggle_lock).grid(row=2, column=0,
                                                  pady=(6, 0), padx=(0, 6))
        ttk.Button(right, text="Change PIN",
                   command=self.change_pin).grid(row=2, column=1,
                                                 pady=(6, 0), padx=(0, 6))
        ttk.Button(right, text="Ask a Parent",
                   command=self.ask_parent).grid(row=2, column=2,
                                                 pady=(6, 0))
        ttk.Label(right, textvariable=self.web_status,
                  style="HeaderSub.TLabel").grid(row=3, column=0,
                                                 columnspan=3, sticky="e")

        bottom = ttk.Frame(self, style="Inner.TFrame")
        bottom.pack(side="bottom", fill="x")
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(bottom, textvariable=self.status_var,
                  style="Status.TLabel").pack(side="left")
        ttk.Label(bottom, text=f"{APP_NAME} {APP_VERSION}",
                  style="Status.TLabel").pack(side="right")

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=12, pady=(8, 0))
        self.pages = [
            ("Dashboard", DashboardPage(self.nb, self)),
            ("Time Limits", TimeLimitsPage(self.nb, self)),
            ("Always Blocked", ListPage(
                self.nb, self, "Always Blocked",
                "Apps listed here are closed the moment they start, and "
                "again if they restart. Websites listed here are blocked "
                "on this computer; a browser still showing one is closed.",
                "blocked", "allowed", "Always Allowed", "blocked",
                "Allow Selected")),
            ("Always Allowed", ListPage(
                self.nb, self, "Always Allowed",
                "Apps are added here automatically the first time they "
                "run. Listed apps are never limited or closed. To stop "
                "one, select it and use Block Selected. Use Hide Selected to tuck "
                "away system items; they stay allowed and are listed under "
                "Hidden at the bottom.",
                "allowed", "blocked", "Always Blocked", "allowed",
                "Block Selected")),
            ("Limited Apps", LimitedAppsPage(self.nb, self)),
            ("Extra Time Coupons", CouponsPage(self.nb, self)),
            ("Log", LogPage(self.nb, self)),
            ("My Account", AccountPage(self.nb, self)),
        ]
        for label, page in self.pages:
            self.nb.add(page, text=label)
        self.nb.bind("<<NotebookTabChanged>>", self._on_tab_changed)
        for seq in ("<Control-Shift-R>", "<Control-Shift-r>"):
            self.bind_all(seq, self._reset_shortcut)
        for seq in ("<Control-Shift-A>", "<Control-Shift-a>"):
            self.bind_all(seq, self._keys_shortcut)

        api = None
        if sys.platform == "win32":
            try:
                api = WindowsProcessApi()
            except Exception as exc:
                self.set_status(f"App blocking could not start: {exc}")
        own_names = {"leafygreen.exe", "snortsecure.exe"}
        if getattr(sys, "frozen", False):
            own_names.add(os.path.basename(sys.executable).lower())
        watcher = None
        if api is not None:
            try:
                watcher = BlockWatcher(
                    CRITICAL_PROCESSES | {n.lower() for n in own_names})
            except Exception as exc:
                self.set_status(f"Fast app blocking could not start: {exc}")
        idle = None
        if sys.platform == "win32":
            try:
                idle = InputMonitor().idle_seconds
            except Exception:
                idle = None
        media = None
        if idle is not None:
            media = MediaMonitor()
        self.media_monitor = media
        self.guard = AppGuard(self.data, api, own_names=own_names,
                              watcher=watcher, idle=idle, media=media)
        if api is not None and not api.has_debug:
            self.set_status("Running without administrator rights: programs "
                            "that run as administrator can't be closed. "
                            "Install with install.bat.")
        self.website_guard = WebsiteGuard(api)
        self.smartsafe = SmartSafe()
        self.smartsafe.start()
        self.pause_guard = InternetPauseGuard(
            os.path.join(SETTINGS_DIR, "paused_adapters.txt"))
        self.limit_guard = LimitGuard()
        if sys.platform == "win32":
            self.notifier = Notifier(self._window_handle)

        if WEB_ENABLED:
            self.web = WebDashboard(self, WEB_PORT)
            error = self.web.start()
            if error:
                self.web = None
                self.web_status.set("Web Dashboard off (port in use?)")
                self.set_status(f"Web Dashboard could not start: {error}")
            else:
                self._refresh_web_address()

        self.update_header()
        self._on_tab_changed()
        self._tick()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.after(200, self.first_run)
        self.after(GUARD_INTERVAL_MS, self._guard_tick)
        if "--minimized" in sys.argv and self.data.pin_hash is not None:
            self.iconify()
        if self.data.load_error:
            # Notify
            self.after(400, lambda: messagebox.showwarning(
                APP_NAME, "The saved settings could not be read, so "
                "LeafyGreen started fresh. The old file was kept as "
                "settings.json.corrupt in the LeafyGreen data folder "
                f"({SETTINGS_DIR}).", parent=self))

    def _refresh_web_address(self):
        """Keeps the address in the header current (Wi-Fi may come up late
        or change)."""
        if self.web is None:
            return
        ip = local_ip()
        if ip != self._ip:
            self._ip = ip
            self.web_status.set(f"Web Dashboard: http://{ip}:{WEB_PORT}")

    def page(self, cls):
        """The notebook page that is an instance of `cls`."""
        return next(p for _, p in self.pages if isinstance(p, cls))

    def _window_handle(self):
        try:
            return int(self.wm_frame(), 16)
        except (tk.TclError, ValueError):
            return self.winfo_id()

    def notify(self, text, title=APP_NAME):
        shown = self.notifier is not None and self.notifier.show(title, text)
        if not shown:
            self.show_warning(text)
        return shown

    def show_warning(self, text):
        win = tk.Toplevel(self)
        win.title(APP_NAME)
        win.attributes("-topmost", True)
        win.resizable(False, False)
        ttk.Label(win, text=text, font=(FONT, 12),
                  padding=(24, 18)).pack()
        ttk.Button(win, text="OK", command=win.destroy).pack(pady=(0, 16))
        win.update_idletasks()
        x = win.winfo_screenwidth() - win.winfo_width() - 30
        y = win.winfo_screenheight() - win.winfo_height() - 90
        win.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        win.bell()
        win.after(20000, lambda: win.winfo_exists() and win.destroy())

    def notify_box(self, text, title=APP_NAME):
        try:
            self.attributes("-topmost", True)
            self.lift()
        except tk.TclError:
            pass
        try:
            # Notify
            messagebox.showinfo(title, text, parent=self)
        except tk.TclError:
            # Notify
            _message_box(text)
        try:
            self.attributes("-topmost", False)
        except tk.TclError:
            pass

    def _guard_tick(self):
        now = time.monotonic()
        note = lambda event, target: self.data.log(event, target)

        def redraw():
            if self.guard.changed or now - self._last_refresh > 15:
                self.guard.changed = False
                self._last_refresh = now
                self._on_tab_changed()

        def address():
            if now - self._last_ip_check >= 30:
                self._last_ip_check = now
                self._refresh_web_address()

        def pause_step():
            if self.data.pause_expired(time.time()):
                self.data.log("Internet resumed", "Timer ended")
                self.guard.changed = True
            self.pause_guard.tick(self.data.internet_paused, now, note)

        steps = (
            ("App monitor", lambda: self.guard.tick(now)),
            ("SmartSafe", self._smartsafe_step),
            ("Website blocking", lambda: self.website_guard.tick(
                self.data.blocked + smartsafe_block_rows(self.data),
                self.data, now)),
            ("Pause Internet", pause_step),
            ("Time limits", lambda: self.limit_guard.tick(
                self.data, now, note, self.notify)),
            ("Countdown", self._countdown_step),
            ("Request results", self._results_step),
            ("Screen update", redraw),
            ("Web address", address),
            ("Saving", self._autosave),
        )
        try:
            for label, step in steps:
                try:
                    step()
                    self._step_errors.pop(label, None)
                except Exception as exc:
                    message = f"{label} error: {exc}"
                    if self._step_errors.get(label) != message:
                        self._step_errors[label] = message
                        self.set_status(message)
        finally:
            self.after(GUARD_INTERVAL_MS, self._guard_tick)

    def _smartsafe_step(self):
        enabled = (self.data.protection_effective
                   and self.data.smartsafe_enabled)
        if self.smartsafe.tick(self.data, enabled,
                               lambda event, target: self.data.log(
                                   event, target, "Blocked")):
            self.guard.changed = True

    def _countdown_step(self):
        if self.countdown is None and self.limit_guard.countdown_due(
                self.data):
            self.countdown = CountdownWindow(self)

    def _results_step(self):
        """Tells the child how their requests were answered, as soon as
        they are at the computer (so a result is never missed)."""
        results = self.data.untold_results()
        if not results:
            return
        idle = self.guard.idle
        if idle is not None and idle() > NOTICE_IDLE_SECONDS:
            return
        lines = [("Approved: " if r["status"] == "Approved" else "Denied: ")
                 + Data.describe_request(r) for r in results[:3]]
        if len(results) > 3:
            lines.append(f"...and {len(results) - 3} more.")
        for r in results:
            r["told"] = True
        self.notify_box("\n".join(lines), "Your requests")
        self.data.log("Request results shown", f"{len(results)} result(s)")

    def ask_parent(self):
        def submit(kind, detail, minutes, note):
            ok, message = self.data.new_request(kind, detail, minutes, note)
            return None if ok else message

        dlg = RequestDialog(self, submit)
        if dlg.result:
            self.set_status("Your request was sent to a parent.")
            self._on_tab_changed()

    def _autosave(self, force=False):
        """Saves when something changed. Settings changes are saved within a
        few seconds; the running time counters (which change constantly) at
        most once a minute, and always on exit."""
        now = time.monotonic()
        if not force and now - self._last_save_check < 5:
            return
        self._last_save_check = now
        state = self.data.to_dict()
        core_state = dict(state)
        core_state.pop("used_today_sec", None)
        core_state["limited"] = [{k: v for k, v in e.items() if k != "used_sec"}
                                 for e in state["limited"]]
        core = json.dumps(core_state, sort_keys=True)
        snapshot = json.dumps(state, sort_keys=True)
        if not force:
            if snapshot == self._last_saved:
                return
            if core == self._last_core and \
                    now - self._last_write_time < COUNTER_SAVE_SECONDS:
                return
        error = Data.write(snapshot)
        if error is None:
            self._last_saved = snapshot
            self._last_core = core
            self._last_write_time = now
            self._last_write_error = None
        elif error != self._last_write_error:
            self._last_write_error = error
            self.set_status(f"Could not save settings: {error}")

    def on_close(self):
        if self.data.pin_hash is not None and not self.authorize():
            self.set_status("Enter the PIN to close LeafyGreen.")
            return
        self._autosave(force=True)
        if self.pause_guard.active:
            self.data.internet_paused = False
            try:
                self.pause_guard.tick(False, time.monotonic())
            except Exception:
                pass
        if self.web is not None:
            self.web.stop()
        if self.notifier is not None:
            self.notifier.close()
        self.quit_by_parent = True
        if self.guard.watcher is not None:
            self.guard.watcher.stop()
        if self.media_monitor is not None:
            self.media_monitor.stop()
        self.destroy()

    def is_protected(self, name):
        return self.guard.is_protected(name)

    def is_unlocked(self):
        return time.time() < self.unlocked_until

    def _lockout_message(self):
        wait = int(self.lockout_until - time.time()) + 1
        return f"Too many wrong PINs. Try again in {wait} seconds."

    def _verify(self, pin):
        """Returns an error message, or None if the PIN is correct."""
        if time.time() < self.lockout_until:
            return self._lockout_message()
        if self.data.check_pin(pin):
            self.failed_tries = 0
            return None
        self.failed_tries += 1
        if self.failed_tries >= MAX_TRIES:
            self.failed_tries = 0
            self.lockout_until = time.time() + LOCKOUT_SECONDS
            return self._lockout_message()
        left = MAX_TRIES - self.failed_tries
        return f"Wrong PIN. {left} tries left."

    def _unlock(self):
        self.unlocked_until = time.time() + UNLOCK_SECONDS
        self._tick(reschedule=False)

    def first_run(self):
        if self.data.pin_hash is not None:
            return

        def check(values):
            if values[0] != values[1]:
                return "The two PINs don't match."
            return None

        dlg = PinDialog(self, "Create Your PIN",
                        ["Create a 4-digit PIN", "Confirm PIN"], check)
        if not dlg.result:
            self.quit_by_parent = True
            self.destroy()
            return
        self.data.set_pin(dlg.result[0])
        self._unlock()
        self._autosave(force=True)
        self.set_status("PIN created. Changes are unlocked for "
                        f"{UNLOCK_SECONDS // 60} minutes.")

    def authorize(self, allow_locked=False):
        """Ask for the PIN unless recently unlocked. True if allowed.
        When the subscription has expired everything is locked except
        activating a new key, so most callers are refused until then."""
        if not allow_locked and self.data.settings_locked:
            # Notify
            messagebox.showwarning(
                APP_NAME, "The subscription has expired, so settings are "
                "locked. Activate a new key on the My Account tab to unlock "
                "them (press Ctrl+Shift+A there to manage keys).",
                parent=self)
            return False
        if self.is_unlocked():
            self.unlocked_until = time.time() + UNLOCK_SECONDS
            return True
        if time.time() < self.lockout_until:
            # Notify
            messagebox.showwarning(APP_NAME, self._lockout_message(),
                                   parent=self)
            return False
        dlg = PinDialog(self, "Enter PIN", ["Enter your 4-digit PIN"],
                        lambda v: self._verify(v[0]))
        if not dlg.result:
            return False
        self._unlock()
        return True

    def _reset_shortcut(self, event=None):
        if self.grab_current() is not None:
            return
        if self.nb.tab(self.nb.select(), "text") == "My Account":
            self.reset_everything()

    def _keys_shortcut(self, event=None):
        if self.grab_current() is not None:
            return
        if self.nb.tab(self.nb.select(), "text") == "My Account":
            self.page(AccountPage).manage_keys()

    def reset_everything(self):
        """Ctrl+Shift+R: asks for the PIN, then asks if they are sure, then
        puts everything back to how it was when first installed."""
        if time.time() < self.lockout_until:
            # Notify
            messagebox.showwarning(APP_NAME, self._lockout_message(),
                                   parent=self)
            return
        if self.data.pin_hash is not None:
            dlg = PinDialog(self, "Enter PIN",
                            ["Enter your 4-digit PIN"],
                            lambda v: self._verify(v[0]))
            if not dlg.result:
                return
        # Notify
        if not messagebox.askyesno(
                APP_NAME, "Are you sure you want to reset everything?\n\n"
                "This removes the PIN, all Web Dashboard accounts, time "
                "limits, bedtime, the blocked and allowed lists, SmartSafe "
                "lists, coupons, requests and the log, and turns protection "
                "OFF. LeafyGreen stays installed.", icon="warning",
                default="no", parent=self):
            return
        self.factory_reset()

    def factory_reset(self):
        fresh = Data()
        fresh.protection_enabled = False
        fresh.setup_done = self.data.setup_done
        self.data.__dict__.update(fresh.__dict__)
        self.unlocked_until = 0.0
        self.failed_tries = 0
        self.lockout_until = 0.0
        self.smartsafe.pending.clear()
        if self.web is not None:
            with self.web.lock:
                self.web.sessions.clear()
        self.data.log("Reset everything", "All settings")
        self._autosave(force=True)
        self.update_header()
        self._tick(reschedule=False)
        self._on_tab_changed()
        self.first_run()
        if not self.quit_by_parent:
            self.set_status("Everything was reset. Protection is OFF: turn "
                            "it on with the shield on the Dashboard.")

    def toggle_lock(self):
        if self.is_unlocked():
            self.unlocked_until = 0.0
            self._tick(reschedule=False)
            self.set_status("Locked. A PIN is needed to make changes.")
        elif self.authorize():
            self.set_status("Unlocked.")

    def change_pin(self):
        def check(values):
            error = self._verify(values[0])
            if error:
                return error
            if values[1] != values[2]:
                return "The new PINs don't match."
            return None

        dlg = PinDialog(self, "Change PIN",
                        ["Current PIN", "New PIN", "Confirm new PIN"], check)
        if dlg.result:
            self.data.set_pin(dlg.result[1])
            self.data.log("PIN changed", "Parent account")
            self._unlock()
            self.set_status("PIN changed.")
            self._on_tab_changed()

    def _tick(self, reschedule=True):
        remaining = int(self.unlocked_until - time.time())
        if remaining > 0:
            mins, secs = divmod(remaining, 60)
            self.lock_status.set(f"\U0001F513 Unlocked ({mins}:{secs:02d})")
            self.lock_btn_text.set("Lock Now")
        else:
            self.lock_status.set("\U0001F512 Locked")
            self.lock_btn_text.set("Unlock")
        if reschedule:
            self.after(1000, self._tick)

    def _on_tab_changed(self, event=None):
        page = self.nametowidget(self.nb.select())
        page.refresh()

    def update_header(self):
        if self.guard.api is None:
            self.header_status.set("Preview mode (app blocking needs "
                                   "Windows)")
        elif self.data.protection_effective:
            self.header_status.set("\u25CF Protection on")
        else:
            self.header_status.set("\u25CB Protection off")

    def set_status(self, message):
        self.status_var.set(message)
        if self._status_job is not None:
            self.after_cancel(self._status_job)
        self._status_job = self.after(
            6000, lambda: self.status_var.set("Ready"))


def _message_box(text):
    """A plain Windows message box (works before any window exists)."""
    try:
        ctypes.windll.user32.MessageBoxW(None, text, APP_NAME, 0x10)
    except Exception:
        print(text)


SETUP_MESSAGE = ("Complete setup fully before running this application. If "
                 "the problem persists, contact support.")


class SetupNeededWindow(tk.Tk):
    """Opens instead of the app until setup.py has been completed: a red
    shield and a message, and nothing else (no blocking, no web dashboard)."""

    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.configure(bg=BG)
        self.geometry("560x460")
        self.minsize(480, 420)
        apply_style(self)
        header = tk.Frame(self, bg=NAVY)
        header.pack(fill="x")
        tk.Label(header, text=APP_NAME, bg=NAVY, fg="white",
                 font=(FONT, 20, "bold")).pack(anchor="w", padx=22,
                                               pady=(16, 0))
        tk.Label(header, text="Parental Controls", bg=NAVY, fg="#cfe6d9",
                 font=(FONT, 10)).pack(anchor="w", padx=22, pady=(0, 14))
        card = ttk.Frame(self, style="Card.TFrame", padding=24)
        card.pack(expand=True, padx=28, pady=24)
        self.shield = ShieldWidget(card, state="off", captions=False)
        self.shield.pack()
        tk.Label(card, text=SETUP_MESSAGE, bg="white", fg=TEXT,
                 font=(FONT, 12), wraplength=400,
                 justify="center").pack(pady=(14, 0))


def _pin_command(args):
    """--has-pin: exit code 0 if a PIN exists, 1 if not.
    --set-pin 1234: store that PIN (install.bat uses both, as administrator).
    Exit code 2 = settings can't be read, 3 = bad PIN, 4 = couldn't save."""
    data = Data.load()
    if data.unreadable:
        return 2
    if "--has-pin" in args:
        return 0 if data.pin_hash is not None else 1
    try:
        pin = args[args.index("--set-pin") + 1]
    except IndexError:
        return 3
    if not (len(pin) == 4 and pin.isdigit()):
        return 3
    data.set_pin(pin)
    data.log("PIN set", "Installer")
    error = Data.write(json.dumps(data.to_dict(), sort_keys=True))
    return 0 if error is None else 4


def main():
    args = sys.argv[1:]
    if "--has-pin" in args or "--set-pin" in args:
        sys.exit(_pin_command(args))
    if "--launcher" in args:
        if sys.platform != "win32":
            print("The launcher only runs on Windows.")
            return
        try:
            user = args[args.index("--user") + 1]
        except (ValueError, IndexError):
            print("Usage: --launcher --user ACCOUNT_NAME")
            return
        if not acquire_single_instance("Global\\LeafyGreenLauncher"):
            return
        SessionLauncher(user).run()
        return

    background = "--minimized" in args
    global CHILD_USER
    if "--child" in args:
        try:
            CHILD_USER = args[args.index("--child") + 1].strip() or None
        except IndexError:
            CHILD_USER = None
    if not acquire_single_instance("Global\\LeafyGreen"):
        if not background:
            # Notify
            _message_box("LeafyGreen is already running. Only one copy "
                         "can run at a time; open it from the taskbar.")
        sys.exit(EXIT_ALREADY_RUNNING)
    data = Data.load()
    if data.unreadable:
        if not background:
            # Notify
            _message_box("LeafyGreen can't open its settings, so it will "
                         "not start. It is meant to run from the startup "
                         "task that install.bat sets up, not by opening the "
                         "program directly.")
        sys.exit(EXIT_SETTINGS_UNREADABLE)
    if not data.setup_done:
        SetupNeededWindow().mainloop()
        sys.exit(0)
    app = App(data)
    app.mainloop()
    sys.exit(EXIT_PARENT_QUIT if app.quit_by_parent else 0)


if __name__ == "__main__":
    main()
