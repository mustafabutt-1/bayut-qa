"""ADB wrapper: device discovery, app state, locale, deep links, proxy, capture.

Every command that needs a device fails loudly with an actionable message rather than
returning a default. ``--dry-run`` prints the exact adb invocations without executing
them, so the whole surface is inspectable with no hardware attached.

CLI
---
    python tools/adb.py devices
    python tools/adb.py info --serial R5CT10 --package com.bayut.app
    python tools/adb.py prepare --serial R5CT10
    python tools/adb.py reset-app --package com.bayut.app
    python tools/adb.py deeplink --url "bayut://search?purpose=rent"
    python tools/adb.py set-proxy --host 192.168.1.20 --port 8080
    python tools/adb.py logcat start --output runs/r1/logcat.txt
    python tools/adb.py screenrecord start --output runs/r1/video.mp4
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path

__all__ = ["AdbError", "Adb", "Device"]

DEFAULT_TIMEOUT = 60


class AdbError(RuntimeError):
    """Raised when adb is missing, no device is available, or a command fails."""


@dataclass
class Device:
    serial: str
    state: str
    model: str = ""
    product: str = ""
    android_release: str = ""
    sdk: str = ""
    screen_size: str = ""
    density: str = ""
    locale: str = ""

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


class Adb:
    """Thin, explicit wrapper around the adb binary."""

    def __init__(self, serial: str | None = None, *, dry_run: bool = False,
                 adb_path: str | None = None, timeout: int = DEFAULT_TIMEOUT) -> None:
        self.serial = serial or os.environ.get("ANDROID_SERIAL") or None
        self.dry_run = dry_run
        self.timeout = timeout
        self.adb_path = adb_path or os.environ.get("ADB_PATH") or shutil.which("adb") or "adb"

    # -- plumbing --------------------------------------------------------

    def _argv(self, args: list[str]) -> list[str]:
        base = [self.adb_path]
        if self.serial:
            base += ["-s", self.serial]
        return base + args

    def run(self, args: list[str], *, check: bool = True, timeout: int | None = None) -> str:
        argv = self._argv(args)
        if self.dry_run:
            print("  [dry-run] " + " ".join(argv))
            return ""
        try:
            proc = subprocess.run(
                argv, capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=timeout or self.timeout,
            )
        except FileNotFoundError as exc:
            raise AdbError(
                f"adb not found at {self.adb_path!r}. Install platform-tools and put adb on "
                f"PATH, or set ADB_PATH in .env."
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise AdbError(f"adb timed out after {timeout or self.timeout}s: {' '.join(argv)}") from exc
        out = (proc.stdout or "").strip()
        err = (proc.stderr or "").strip()
        if check and proc.returncode != 0:
            raise AdbError(f"adb failed ({proc.returncode}): {' '.join(argv)}\n{err or out}")
        if err and "daemon" not in err.lower() and check:
            # adb writes some benign notices to stderr; surface anything else.
            print(f"  adb stderr: {err}", file=sys.stderr)
        return out

    def shell(self, command: str, *, check: bool = True, timeout: int | None = None) -> str:
        return self.run(["shell", command], check=check, timeout=timeout)

    def popen(self, args: list[str], *, stdout_path: Path | None = None) -> subprocess.Popen:
        argv = self._argv(args)
        if self.dry_run:
            print("  [dry-run background] " + " ".join(argv))
            raise AdbError("cannot start a background process in --dry-run mode")
        stdout = open(stdout_path, "wb") if stdout_path else subprocess.DEVNULL
        return subprocess.Popen(argv, stdout=stdout, stderr=subprocess.STDOUT)

    # -- discovery -------------------------------------------------------

    def list_devices(self, *, detailed: bool = True) -> list[Device]:
        out = self.run(["devices", "-l"], check=True)
        devices: list[Device] = []
        for line in out.splitlines()[1:]:
            line = line.strip()
            if not line or line.startswith("*"):
                continue
            parts = line.split()
            serial, state = parts[0], parts[1]
            attrs = dict(p.split(":", 1) for p in parts[2:] if ":" in p)
            dev = Device(
                serial=serial, state=state,
                model=attrs.get("model", ""), product=attrs.get("product", ""),
            )
            if detailed and state == "device":
                probe = Adb(serial, dry_run=self.dry_run, adb_path=self.adb_path)
                dev.android_release = probe.getprop("ro.build.version.release")
                dev.sdk = probe.getprop("ro.build.version.sdk")
                dev.locale = probe.get_locale()
                size = probe.shell("wm size", check=False)
                density = probe.shell("wm density", check=False)
                dev.screen_size = size.split(":")[-1].strip() if size else ""
                dev.density = density.split(":")[-1].strip() if density else ""
            devices.append(dev)
        return devices

    def require_device(self) -> Device:
        """Resolve exactly one usable device or fail with a specific reason."""
        if self.dry_run:
            # --dry-run exists to inspect the commands with no hardware attached, so the
            # device gate must not be the thing that stops it.
            return Device(serial=self.serial or "DRY-RUN", state="device", model="(dry-run)")
        devices = [d for d in self.list_devices(detailed=False)]
        usable = [d for d in devices if d.state == "device"]
        if not devices:
            raise AdbError("no devices seen by adb. Check the USB cable, USB debugging, and "
                           "that you accepted the RSA prompt on the device.")
        unauthorised = [d for d in devices if d.state == "unauthorized"]
        if unauthorised and not usable:
            raise AdbError(f"device {unauthorised[0].serial} is unauthorized — accept the "
                           f"'Allow USB debugging' prompt on the device screen.")
        offline = [d for d in devices if d.state == "offline"]
        if offline and not usable:
            raise AdbError(f"device {offline[0].serial} is offline — reconnect it or run "
                           f"`adb kill-server && adb start-server`.")
        if self.serial:
            match = [d for d in usable if d.serial == self.serial]
            if not match:
                raise AdbError(f"serial {self.serial!r} not among connected devices: "
                               f"{[d.serial for d in usable]}")
            return match[0]
        if len(usable) > 1:
            raise AdbError(f"{len(usable)} devices connected; pass --serial to choose one: "
                           f"{[d.serial for d in usable]}")
        return usable[0]

    def getprop(self, prop: str) -> str:
        return self.shell(f"getprop {prop}", check=False)

    # -- app state -------------------------------------------------------

    def app_version(self, package: str) -> dict[str, str]:
        out = self.shell(f"dumpsys package {package}", check=False)
        if not out or "Unable to find package" in out:
            raise AdbError(f"package {package!r} is not installed on this device.")
        version_name = re.search(r"versionName=(\S+)", out)
        version_code = re.search(r"versionCode=(\d+)", out)
        first_install = re.search(r"firstInstallTime=(.+)", out)
        last_update = re.search(r"lastUpdateTime=(.+)", out)
        return {
            "package": package,
            "version_name": version_name.group(1) if version_name else "UNKNOWN",
            "version_code": version_code.group(1) if version_code else "UNKNOWN",
            "first_install": first_install.group(1).strip() if first_install else "UNKNOWN",
            "last_update": last_update.group(1).strip() if last_update else "UNKNOWN",
        }

    def reset_app(self, package: str) -> None:
        """`pm clear` — wipes app data so a crawl or test starts from a known state."""
        out = self.shell(f"pm clear {package}")
        if self.dry_run:
            return
        if "Success" not in out:
            raise AdbError(f"pm clear did not report Success for {package}: {out!r}")

    def stop_app(self, package: str) -> None:
        self.shell(f"am force-stop {package}")

    def launch_app(self, package: str, activity: str | None = None) -> None:
        if activity:
            component = activity if "/" in activity else f"{package}/{activity}"
            self.shell(f"am start -n {component}")
        else:
            self.shell(f"monkey -p {package} -c android.intent.category.LAUNCHER 1", check=False)

    def current_activity(self) -> str:
        out = self.shell("dumpsys window | grep -E 'mCurrentFocus|mFocusedApp'", check=False)
        return out or "UNKNOWN"

    def deeplink(self, url: str, package: str | None = None) -> str:
        cmd = f'am start -a android.intent.action.VIEW -d "{url}"'
        if package:
            cmd += f" {package}"
        out = self.shell(cmd, check=False)
        if not self.dry_run and ("Error" in out or "does not have a handler" in out.lower()):
            raise AdbError(f"deep link not handled: {url}\n{out}")
        return out

    def grant(self, package: str, permission: str) -> None:
        self.shell(f"pm grant {package} {permission}", check=False)

    def revoke(self, package: str, permission: str) -> None:
        self.shell(f"pm revoke {package} {permission}", check=False)

    # -- device preparation ----------------------------------------------

    def prepare(self) -> list[str]:
        """Settings that remove a large share of Appium flake. Idempotent."""
        applied = []
        for desc, cmd in (
            ("window animation off", "settings put global window_animation_scale 0"),
            ("transition animation off", "settings put global transition_animation_scale 0"),
            ("animator duration off", "settings put global animator_duration_scale 0"),
            ("stay awake while charging", "settings put global stay_on_while_plugged_in 7"),
            ("screen timeout 30 min", "settings put system screen_off_timeout 1800000"),
            ("disable soft keyboard autocorrect", "settings put secure show_ime_with_hard_keyboard 0"),
        ):
            self.shell(cmd, check=False)
            applied.append(desc)
        return applied

    # -- locale ----------------------------------------------------------

    def get_locale(self) -> str:
        for prop in ("persist.sys.locale", "ro.product.locale", "persist.sys.language"):
            val = self.getprop(prop)
            if val:
                return val
        return self.shell("settings get system system_locales", check=False) or "UNKNOWN"

    def has_root(self) -> bool:
        out = self.shell("su -c id", check=False)
        return "uid=0" in out

    def set_locale(self, locale: str, *, method: str = "auto",
                   helper_package: str = "net.sanapeli.adbchangelanguage") -> str:
        """Switch device locale. Returns the method actually used.

        Honest limitation: there is **no reliable pure-adb locale switch** on a
        non-rooted modern Android device. Three paths, in order of reliability:

        1. ``root``   — persist.sys.locale + framework restart. Needs a rooted device.
        2. ``helper`` — the ADB Change Language helper APK, granted
           android.permission.CHANGE_CONFIGURATION over adb. Works unrooted, but the
           helper must be installed first.
        3. ``in-app`` — the app's own language setting. Most faithful to what a real
           user does, but it is a UI action, so ``crawler.py`` performs it, not this
           module. Prefer this for the Arabic suite unless the app follows the
           system locale.

        ``settings put system system_locales`` is deliberately not offered: it appears
        to succeed and frequently does nothing until reboot, which would silently
        produce an English crawl labelled as Arabic.
        """
        if "-" not in locale and "_" not in locale:
            raise AdbError(f"locale must be language-COUNTRY, e.g. ar-AE (got {locale!r})")
        locale = locale.replace("_", "-")

        if method in ("auto", "root") and self.has_root():
            self.shell(f'su -c "setprop persist.sys.locale {locale}"')
            self.shell('su -c "stop; start"')
            time.sleep(5)
            return "root"
        if method == "root":
            raise AdbError("root method requested but `su -c id` did not return uid=0.")

        if method in ("auto", "helper"):
            installed = self.shell(f"pm list packages {helper_package}", check=False)
            if helper_package in installed:
                lang, country = locale.split("-", 1)
                self.grant(helper_package, "android.permission.CHANGE_CONFIGURATION")
                self.shell(
                    f"am start -n {helper_package}/.AdbChangeLanguage "
                    f'-e language {lang} -e country {country}'
                )
                time.sleep(3)
                return "helper"
            if method == "helper":
                raise AdbError(f"helper package {helper_package} is not installed.")

        raise AdbError(
            f"cannot switch locale to {locale} on this device.\n"
            f"  - device is not rooted, and\n"
            f"  - helper APK {helper_package} is not installed.\n"
            f"Options: install the helper APK, use a rooted test device, or switch locale "
            f"inside the app's own settings (crawler.py --locale-method in-app). "
            f"Do NOT assume the locale changed — verify with `adb.py get-locale`."
        )

    # -- proxy (mitmproxy) ------------------------------------------------

    def set_proxy(self, host: str, port: int) -> None:
        self.shell(f"settings put global http_proxy {host}:{port}")

    def clear_proxy(self) -> None:
        self.shell("settings put global http_proxy :0")
        self.shell("settings delete global http_proxy", check=False)

    def get_proxy(self) -> str:
        return self.shell("settings get global http_proxy", check=False) or "(none)"

    # -- capture ----------------------------------------------------------

    @staticmethod
    def _pid_file(output: Path, kind: str) -> Path:
        return output.with_suffix(output.suffix + f".{kind}.pid")

    def logcat_clear(self) -> None:
        self.run(["logcat", "-c"], check=False)

    def logcat_start(self, output: Path, *, clear: bool = True) -> int:
        output.parent.mkdir(parents=True, exist_ok=True)
        if clear:
            self.logcat_clear()
        proc = self.popen(["logcat", "-v", "threadtime"], stdout_path=output)
        self._pid_file(output, "logcat").write_text(str(proc.pid), encoding="utf-8")
        return proc.pid

    def logcat_stop(self, output: Path) -> None:
        pid_file = self._pid_file(output, "logcat")
        if not pid_file.is_file():
            raise AdbError(f"no logcat pid file at {pid_file}; was logcat started for this output?")
        pid = int(pid_file.read_text(encoding="utf-8").strip())
        _terminate(pid)
        pid_file.unlink(missing_ok=True)

    def logcat_dump(self, output: Path, *, buffer: str = "main,system,crash") -> Path:
        output.parent.mkdir(parents=True, exist_ok=True)
        text = self.run(["logcat", "-d", "-b", buffer, "-v", "threadtime"], check=False,
                        timeout=self.timeout * 2)
        output.write_text(text, encoding="utf-8")
        return output

    def screenshot(self, output: Path) -> Path:
        output.parent.mkdir(parents=True, exist_ok=True)
        if self.dry_run:
            self.run(["exec-out", "screencap", "-p"])
            return output
        argv = self._argv(["exec-out", "screencap", "-p"])
        proc = subprocess.run(argv, capture_output=True, timeout=self.timeout)
        if proc.returncode != 0 or not proc.stdout:
            raise AdbError(f"screencap failed: {proc.stderr.decode('utf-8', 'replace')}")
        output.write_bytes(proc.stdout)
        return output

    def screenrecord_start(self, output: Path, *, time_limit: int = 180,
                           size: str | None = None, bit_rate: str = "4M") -> str:
        """Start on-device recording. Returns the device-side path."""
        output.parent.mkdir(parents=True, exist_ok=True)
        device_path = f"/sdcard/{output.stem}-{int(time.time())}.mp4"
        cmd = ["shell", "screenrecord", "--bit-rate", bit_rate,
               "--time-limit", str(min(time_limit, 180))]
        if size:
            cmd += ["--size", size]
        cmd.append(device_path)
        proc = self.popen(cmd)
        self._pid_file(output, "screenrecord").write_text(
            json.dumps({"pid": proc.pid, "device_path": device_path}), encoding="utf-8")
        return device_path

    def screenrecord_stop(self, output: Path) -> Path:
        pid_file = self._pid_file(output, "screenrecord")
        if not pid_file.is_file():
            raise AdbError(f"no screenrecord pid file at {pid_file}")
        meta = json.loads(pid_file.read_text(encoding="utf-8"))
        _terminate(meta["pid"])
        # screenrecord needs a moment to finalise the MP4 container after SIGINT.
        time.sleep(3)
        self.run(["pull", meta["device_path"], str(output)], check=False)
        self.shell(f"rm -f {meta['device_path']}", check=False)
        pid_file.unlink(missing_ok=True)
        if not self.dry_run and not output.is_file():
            raise AdbError(f"screenrecord produced no file at {output}; the device may have "
                           f"killed the recorder or /sdcard may be unwritable.")
        return output

    def dumpsys(self, service: str, output: Path | None = None) -> str:
        text = self.shell(f"dumpsys {service}", check=False, timeout=self.timeout * 2)
        if output:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(text, encoding="utf-8")
        return text

    def page_source(self, output: Path) -> Path:
        """UiAutomator dump without Appium — useful for a fast structural snapshot."""
        output.parent.mkdir(parents=True, exist_ok=True)
        self.shell("uiautomator dump /sdcard/window_dump.xml", check=False)
        self.run(["pull", "/sdcard/window_dump.xml", str(output)], check=False)
        return output


def _terminate(pid: int) -> None:
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"],
                           capture_output=True, check=False)
        else:
            os.kill(pid, signal.SIGINT)
    except (ProcessLookupError, PermissionError) as exc:
        print(f"warning: could not stop pid {pid}: {exc}", file=sys.stderr)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _adb(args: argparse.Namespace) -> Adb:
    return Adb(args.serial, dry_run=args.dry_run, adb_path=args.adb_path, timeout=args.timeout)


def _cmd_devices(args: argparse.Namespace) -> int:
    devices = _adb(args).list_devices(detailed=not args.quick)
    if args.json:
        print(json.dumps([d.to_dict() for d in devices], indent=2))
        return 0
    if not devices:
        print("No devices connected.")
        return 1
    print(f"{'serial':<22} {'state':<14} {'model':<20} {'android':<9} {'sdk':<5} {'locale':<8} size")
    print("-" * 100)
    for d in devices:
        print(f"{d.serial:<22} {d.state:<14} {d.model:<20} {d.android_release:<9} "
              f"{d.sdk:<5} {d.locale:<8} {d.screen_size}")
    return 0


def _cmd_info(args: argparse.Namespace) -> int:
    a = _adb(args)
    dev = a.require_device()
    info: dict[str, object] = {"device": dev.to_dict(), "locale": a.get_locale(),
                               "proxy": a.get_proxy(), "rooted": a.has_root()}
    if args.package:
        info["app"] = a.app_version(args.package)
    info["current_focus"] = a.current_activity()
    print(json.dumps(info, indent=2))
    return 0


def _cmd_prepare(args: argparse.Namespace) -> int:
    a = _adb(args)
    a.require_device()
    for line in a.prepare():
        print(f"  applied: {line}")
    print("\nStill to do manually: disable screen lock/PIN, exempt the app from battery "
          "optimisation, and confirm the device stays on the test Wi-Fi.")
    return 0


def _cmd_reset_app(args: argparse.Namespace) -> int:
    a = _adb(args)
    a.require_device()
    a.reset_app(args.package)
    print(f"cleared app data: {args.package}")
    if args.launch:
        a.launch_app(args.package, args.activity)
        print("relaunched")
    return 0


def _cmd_launch(args: argparse.Namespace) -> int:
    a = _adb(args)
    a.require_device()
    a.launch_app(args.package, args.activity)
    print(a.current_activity())
    return 0


def _cmd_deeplink(args: argparse.Namespace) -> int:
    a = _adb(args)
    a.require_device()
    print(a.deeplink(args.url, args.package))
    print(a.current_activity())
    return 0


def _cmd_get_locale(args: argparse.Namespace) -> int:
    print(_adb(args).get_locale())
    return 0


def _cmd_set_locale(args: argparse.Namespace) -> int:
    a = _adb(args)
    a.require_device()
    used = a.set_locale(args.locale, method=args.method)
    actual = a.get_locale()
    print(f"method used : {used}")
    print(f"locale now  : {actual}")
    if args.locale.replace("_", "-").lower() not in actual.lower():
        print("WARNING: device locale does not report the requested value. Do not run the "
              "Arabic suite until this is resolved.", file=sys.stderr)
        return 1
    return 0


def _cmd_proxy(args: argparse.Namespace) -> int:
    a = _adb(args)
    a.require_device()
    if args.action == "set":
        if not args.host:
            raise AdbError("--host is required for `proxy set` (MITM_HOST in .env)")
        a.set_proxy(args.host, args.port)
    elif args.action == "clear":
        a.clear_proxy()
    print(f"http_proxy = {a.get_proxy()}")
    return 0


def _cmd_logcat(args: argparse.Namespace) -> int:
    a = _adb(args)
    a.require_device()
    out = Path(args.output)
    if args.action == "start":
        pid = a.logcat_start(out, clear=not args.no_clear)
        print(f"logcat streaming to {out} (pid {pid})")
    elif args.action == "stop":
        a.logcat_stop(out)
        print(f"logcat stopped; {out} ({out.stat().st_size if out.is_file() else 0} bytes)")
    else:
        a.logcat_dump(out)
        print(f"logcat buffer dumped to {out}")
    return 0


def _cmd_screenrecord(args: argparse.Namespace) -> int:
    a = _adb(args)
    a.require_device()
    out = Path(args.output)
    if args.action == "start":
        path = a.screenrecord_start(out, time_limit=args.time_limit, size=args.size)
        print(f"recording to device path {path}; stop within {min(args.time_limit, 180)}s "
              f"(screenrecord has a hard 180s cap)")
    else:
        a.screenrecord_stop(out)
        print(f"video pulled to {out}")
    return 0


def _cmd_screenshot(args: argparse.Namespace) -> int:
    a = _adb(args)
    a.require_device()
    print(a.screenshot(Path(args.output)))
    return 0


def _cmd_dumpsys(args: argparse.Namespace) -> int:
    a = _adb(args)
    a.require_device()
    text = a.dumpsys(args.service, Path(args.output) if args.output else None)
    if not args.output:
        print(text[:4000])
    else:
        print(f"wrote {args.output}")
    return 0


def _cmd_page_source(args: argparse.Namespace) -> int:
    a = _adb(args)
    a.require_device()
    print(a.page_source(Path(args.output)))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="adb.py",
        description="ADB operations for the Bayut QA system: device discovery, app state, "
                    "locale, deep links, proxy, and artifact capture.",
        epilog="Use --dry-run to print the adb commands without a device attached.",
    )
    p.add_argument("--serial", default=None, help="device serial (default: ANDROID_SERIAL, or the only device)")
    p.add_argument("--adb-path", default=None, help="path to adb (default: ADB_PATH or PATH lookup)")
    p.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="per-command timeout in seconds")
    p.add_argument("--dry-run", action="store_true", help="print commands instead of running them")
    sub = p.add_subparsers(dest="command", required=True)

    d = sub.add_parser("devices", help="list connected devices with OS, size, locale")
    d.add_argument("--quick", action="store_true", help="skip per-device property probes")
    d.add_argument("--json", action="store_true")
    d.set_defaults(func=_cmd_devices)

    i = sub.add_parser("info", help="device + app + proxy + locale snapshot as JSON")
    i.add_argument("--package", default=os.environ.get("BAYUT_APP_PACKAGE"))
    i.set_defaults(func=_cmd_info)

    pr = sub.add_parser("prepare", help="apply the anti-flake device settings")
    pr.set_defaults(func=_cmd_prepare)

    r = sub.add_parser("reset-app", help="pm clear the app under test")
    r.add_argument("--package", required=True)
    r.add_argument("--launch", action="store_true", help="relaunch after clearing")
    r.add_argument("--activity", default=os.environ.get("BAYUT_APP_ACTIVITY"))
    r.set_defaults(func=_cmd_reset_app)

    la = sub.add_parser("launch", help="launch the app")
    la.add_argument("--package", required=True)
    la.add_argument("--activity", default=os.environ.get("BAYUT_APP_ACTIVITY"))
    la.set_defaults(func=_cmd_launch)

    dl = sub.add_parser("deeplink", help="open a deep link and report the resulting activity")
    dl.add_argument("--url", required=True)
    dl.add_argument("--package", default=None, help="restrict the intent to this package")
    dl.set_defaults(func=_cmd_deeplink)

    gl = sub.add_parser("get-locale", help="print the device locale")
    gl.set_defaults(func=_cmd_get_locale)

    sl = sub.add_parser("set-locale", help="switch device locale (root or helper APK required)")
    sl.add_argument("--locale", required=True, help="e.g. ar-AE or en-AE")
    sl.add_argument("--method", choices=["auto", "root", "helper"], default="auto")
    sl.set_defaults(func=_cmd_set_locale)

    px = sub.add_parser("proxy", help="set/clear/show the global HTTP proxy for mitmproxy")
    px.add_argument("action", choices=["set", "clear", "show"])
    px.add_argument("--host", default=os.environ.get("MITM_HOST"))
    px.add_argument("--port", type=int, default=int(os.environ.get("MITM_PORT", "8080")))
    px.set_defaults(func=_cmd_proxy)

    lc = sub.add_parser("logcat", help="stream, stop, or dump logcat")
    lc.add_argument("action", choices=["start", "stop", "dump"])
    lc.add_argument("--output", required=True)
    lc.add_argument("--no-clear", action="store_true", help="do not clear the buffer on start")
    lc.set_defaults(func=_cmd_logcat)

    sr = sub.add_parser("screenrecord", help="start/stop on-device screen recording")
    sr.add_argument("action", choices=["start", "stop"])
    sr.add_argument("--output", required=True)
    sr.add_argument("--time-limit", type=int, default=180)
    sr.add_argument("--size", default=None, help="e.g. 720x1280 to shrink the file")
    sr.set_defaults(func=_cmd_screenrecord)

    ss = sub.add_parser("screenshot", help="capture a PNG")
    ss.add_argument("--output", required=True)
    ss.set_defaults(func=_cmd_screenshot)

    ds = sub.add_parser("dumpsys", help="capture a dumpsys service snapshot")
    ds.add_argument("--service", required=True, help="e.g. activity, window, package, connectivity")
    ds.add_argument("--output", default=None)
    ds.set_defaults(func=_cmd_dumpsys)

    ps = sub.add_parser("page-source", help="uiautomator dump without Appium")
    ps.add_argument("--output", required=True)
    ps.set_defaults(func=_cmd_page_source)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except AdbError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
