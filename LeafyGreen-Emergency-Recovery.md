# LeafyGreen — Emergency Recovery Plan

Keep a printed copy of this **off the child's computer** (print it, or save it on
your phone / a USB stick). It explains how to get a child unstuck and how to
remove LeafyGreen completely, even if you have forgotten the PIN or the
subscription has expired.

---

## 0. Set this up IN ADVANCE (do it now, while things work)

Recovery depends on these. Without them it is much harder.

1. **Keep a second Windows account that is an Administrator**, with a password
   only you know. The child's account must be a *Standard* user; your admin
   account is separate. **This is the master key to recovery.**
2. **Keep the installer folder** (`setup.py`, `install.bat`, `uninstall.bat`,
   `leafygreen.py`) on a USB stick or in your admin account. `uninstall.bat`
   is the clean removal tool.
3. **Write down the 4‑digit PIN** and the **activation key(s)** and store them
   with this sheet.
4. Make sure Python is still installed (only needed if you use `setup.py`;
   the manual steps in Section 4 do **not** need Python).

> Why it matters: LeafyGreen runs as the SYSTEM account from a scheduled task
> called **LeafyGreen** that restarts itself (up to 999 times, once a minute),
> and its settings folder is locked to SYSTEM/Administrators. Only an
> administrator can take it down.

---

## 1. First, understand what "locked out" means here

LeafyGreen **does not** use a custom lock screen. At bedtime or when the daily
time limit is reached it calls the **normal Windows lock** and re‑applies it
every ~3 seconds while the rule is active. That is good news for recovery:

- **You can always "Switch user" at the Windows sign‑in screen and log into
  your Administrator account.** LeafyGreen only re‑locks the *child's* session,
  not yours.

So the universal escape is: **get to your Administrator session, then act.**

Get there with: `Ctrl`+`Alt`+`Del` → **Switch user** (or **Sign out**) → choose
your admin account. If the screen keeps locking, that's fine — your admin
session is a different session and stays open.

---

## 2. Fastest fixes (child is stuck right now)

### A. Temporarily stop LeafyGreen (keeps settings, lets the child back in)
Sign in as **Administrator**, open **Command Prompt (Run as administrator)** and run:

```
schtasks /End    /TN "LeafyGreen"
schtasks /Change /TN "LeafyGreen" /DISABLE
taskkill  /F /IM LeafyGreen.exe
```

The order matters: disabling the task first stops it respawning, then the
`taskkill` sticks. The child can now use the computer. To turn protection back
on later:

```
schtasks /Change /TN "LeafyGreen" /ENABLE
schtasks /Run    /TN "LeafyGreen"
```

### B. Fix a bad setting instead of removing it
If the problem is a wrong bedtime or a 0‑minute limit, sign in as Administrator
and run `setup.py` → **Redo Setup** (needs the PIN), or open LeafyGreen in the
child's session and enter the PIN to change the rule.

---

## 3. Remove LeafyGreen completely (the clean way)

Sign in as **Administrator**.

- **Option 1 — the bundled tool:** run `setup.py`, approve the admin prompt,
  and choose **Uninstall**.
- **Option 2 — the uninstaller:** right‑click `uninstall.bat` → **Run as
  administrator**, type `YES` when asked.

Either one stops and deletes the **LeafyGreen** task, kills the process,
removes the blocked‑website entries from the `hosts` file, flushes DNS,
re‑enables any network adapter that "Pause Internet" turned off, and deletes
the program files. It will ask whether to also delete the saved settings/PIN.

---

## 4. Manual teardown (no installer files, no Python)

Use this if you only have an Administrator account and a Command Prompt.
Run **Command Prompt as administrator** and run these in order:

```
:: 1) Stop and remove the background task, then kill the app
schtasks /End    /TN "LeafyGreen"
schtasks /Delete /TN "LeafyGreen" /F
taskkill  /F /IM LeafyGreen.exe

:: 2) Turn the network back on (only needed if "Pause Internet" was on)
powershell -Command "Get-NetAdapter | Enable-NetAdapter -Confirm:$false"

:: 3) Remove blocked-website lines from the hosts file
powershell -Command "$h=\"$env:SystemRoot\System32\drivers\etc\hosts\"; $t=[IO.File]::ReadAllText($h); $n=[regex]::Replace($t,'(?s)\r?\n?# >>> (?:LeafyGreen|Snort Secure) blocked websites.*?# <<< (?:LeafyGreen|Snort Secure) blocked websites <<<',''); [IO.File]::WriteAllText($h,$n)"
ipconfig /flushdns

:: 4) Delete the program and (optionally) the locked settings folder
rmdir /s /q "%ProgramFiles%\LeafyGreen"
takeown /f "%ProgramData%\LeafyGreen" /r /d y
icacls  "%ProgramData%\LeafyGreen" /grant administrators:F /t
rmdir /s /q "%ProgramData%\LeafyGreen"
```

Then restart the computer. If a step says "access denied," you are not running
as administrator — close the window and reopen Command Prompt with **Run as
administrator**.

---

## 5. If you have NO administrator account available

This is the hard case — prevent it by doing Section 0 now.

1. **Safe Mode with Command Prompt:** hold `Shift` while clicking Restart →
   *Troubleshoot → Advanced options → Startup Settings → Restart*, then pick
   **Safe Mode with Command Prompt**. If you can reach an admin prompt there,
   run the Section 4 commands.
2. If there is genuinely no administrator login anywhere, you are into Windows
   account‑recovery / password‑reset territory, which is outside LeafyGreen.
   This is exactly why Section 0 step 1 matters.

---

## 6. The subscription / expiry case (not a child lockout)

- While a subscription is **valid**, protection runs normally.
- When it **expires**: the **parent's settings are locked** (you cannot change
  limits), but **protection stays on for 5 more days**, then turns off on its
  own. The child is *not* locked out by expiry itself.
- To unlock settings again: open LeafyGreen (child session) or `setup.py` →
  Redo, enter the **PIN**, and **activate a valid, non‑expired key** on the
  **My Account** tab. Keys are managed there with **Ctrl+Shift+A**.
- If you have lost the PIN and need to change things while expired, use the
  removal steps in Section 3 or 4 instead.

---

## Quick reference

| Situation | Do this |
|---|---|
| Child locked out now, keep settings | §2A disable the task (admin) |
| Wrong bedtime/limit | §2B Redo Setup or PIN in the app |
| Remove everything, have the files | §3 `setup.py` → Uninstall, or `uninstall.bat` |
| Remove everything, no files | §4 manual commands (admin) |
| No admin account | §5 Safe Mode — and set up §0 next time |
| Expired, settings locked | §6 activate a new key (PIN), or remove it |

Task name: **LeafyGreen** · Process: **LeafyGreen.exe** · Program: `C:\Program Files\LeafyGreen` · Settings: `C:\ProgramData\LeafyGreen`
