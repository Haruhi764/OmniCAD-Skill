"""Product identity, installed-host discovery and conservative capability negotiation."""
from dataclasses import asdict, dataclass
import re
import sys
from pathlib import Path

PRODUCTS = ("autocad", "lt", "unknown")
BACKENDS = ("auto", "com", "exchange")

@dataclass(frozen=True)
class Host:
    product: str
    year: int | None
    platform: str
    version: str = ""
    executable: str = ""
    evidence: str = "unknown"

    def __post_init__(self):
        if self.product not in PRODUCTS:
            raise ValueError("Unknown product identity")
        if self.year is not None and not 1982 <= self.year <= 2100:
            raise ValueError("Invalid release year")

    @property
    def interfaces(self):
        windows = self.platform == "win32"
        full = self.product == "autocad"
        lite = self.product == "lt"
        known_version = self.year is not None
        return {
            "external_com": windows and full,
            "autolisp": (full and self.platform in {"win32", "darwin"}) or
                        (lite and windows and known_version and self.year >= 2024),
            "visual_lisp": "full" if full and windows else
                           "limited" if lite and windows and known_version and self.year >= 2024 else "unknown",
            "scr": self.product in {"autocad", "lt"},
            "dxf_exchange": True,
            "native_runtime_verified": False,
        }

    def report(self):
        return {**asdict(self), "interfaces": self.interfaces,
                "runtime_status": "pending_native_test"}

def identity(text):
    normalized = str(text or "").casefold().strip()
    if re.search(r"\bautocad\s*lt\b|\bacadlt\b|\baclt\b", normalized):
        return "lt"
    if re.search(r"\bautocad\b|\bacad\b", normalized):
        return "autocad"
    return "unknown"

def release_year(*texts):
    for text in texts:
        match = re.search(r"(?<!\d)(20\d{2})(?!\d)", str(text or ""))
        if match:
            return int(match.group(1))
    return None

def acadver_year(version):
    # Autodesk ACADVER (product version), not DXF database $ACADVER.
    # Unknown releases remain unknown rather than extrapolating the sequence.
    match = re.match(r"R?(\d+\.\d+)", str(version or ""))
    return {"24.0":2021,"24.1":2022,"24.2":2023,"24.3":2024,
            "25.0":2025,"25.1":2026,"26.0":2027}.get(match.group(1)) if match else None

def installed_windows():
    """Read registered product information; no COM attach, launch or registry writes."""
    if sys.platform != "win32":
        return []
    import winreg
    found = {}
    def children(key):
        count = winreg.QueryInfoKey(key)[0]
        return [winreg.EnumKey(key, i) for i in range(count)]

    def value(key, *names):
        for n in names:
            try:
                data = winreg.QueryValueEx(key, n)[0]
                if isinstance(data, str) and data:
                    return data
            except OSError:
                continue
        return ""

    for root in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        for family in ("AutoCAD", "AutoCAD LT"):
            prefix = r"SOFTWARE\Autodesk" + "\\" + family
            try:
                with winreg.OpenKey(root, prefix) as top:
                    releases = children(top)
                for release in releases:
                    with winreg.OpenKey(root, prefix+"\\"+release) as group:
                        names = children(group)
                    for sku in names:
                        with winreg.OpenKey(root, prefix+"\\"+release+"\\"+sku) as key:
                            title = value(key, "ProductName", "DisplayName")
                            loc = value(key, "AcadLocation", "InstallLocation", "InstallPath")
                        # SKU prefixes are checked as well because shared registries
                        # can contain LT registrations under the AutoCAD family.
                        kind = identity("acadlt" if sku.upper().startswith(("ACADLT-", "ACLT-")) else family)
                        explicit = identity(title)
                        if explicit != "unknown":
                            kind = explicit
                        if not loc:
                            continue
                        exe = Path(loc) / ("acadlt.exe" if kind == "lt" else "acad.exe")
                        if Path(loc).suffix.casefold() == ".exe":
                            exe = Path(loc)
                        if not exe.is_file() or identity(exe.stem) != kind:
                            continue
                        year = release_year(title, loc) or (
                            acadver_year(release) if kind=="autocad" else
                            {"R29":2023,"R30":2024,"R31":2025,"R32":2026}.get(release.upper()))
                        host = Host(kind, year, "win32", release,
                                    str(exe), "registry_and_executable")
                        found[(kind, str(exe).casefold())] = host
            except OSError:
                continue
    return list(found.values())

def session_identity(application):
    """Inspect a full COM object after attach, never infer LT support from its version."""
    facts = []
    version = ""
    exe = ""
    for getter in (lambda: application.Name, lambda: application.FullName,
                   lambda: application.ActiveDocument.GetVariable("PROGRAM")):
        try:
            item = str(getter())
            facts.append(identity(item))
            if item.casefold().endswith(".exe"):
                exe = item
        except AttributeError:
            continue
        except Exception as exc:
            # Busy or disconnected is not an identity result.
            if (getattr(exc, "hresult", 0) or 0) & 0xffffffff in {
                0x800706BA, 0x800706BE, 0x80010108, 0x80010001, 0x8001010A}:
                raise
    try:
        version = str(application.Version)
    except AttributeError:
        pass
    known = set(facts) - {"unknown"}
    product = next(iter(known)) if len(known) == 1 else "unknown"
    return Host(product, release_year(exe) or acadver_year(version), sys.platform, version, exe, "live_com_identity")

def probe_session_file(path):
    """Read a native in-application diagnostic; treat it as user-supplied evidence."""
    fields = dict(line.split("=", 1) for line in Path(path).read_text(encoding="utf-8-sig").splitlines()
                  if "=" in line)
    program = fields.get("PROGRAM", "").casefold()
    if program not in {"acad", "acadlt"} or not fields.get("ACADVER"):
        raise ValueError("Expected PROGRAM and ACADVER from a CAD session")
    # PLATFORM can be localized; the script emits WINDOWS or OTHER.
    platform = "win32" if fields.get("OS") == "WINDOWS" else "unknown"
    return Host(identity(program), acadver_year(fields["ACADVER"]), platform,
                fields["ACADVER"], evidence="user_supplied_native_session_probe")

def choose(hosts, backend="auto", product="auto", year=None, platform=None):
    if backend not in BACKENDS or product not in ("auto", "autocad", "lt"):
        raise ValueError("Invalid backend/product preference")
    platform = platform or sys.platform
    options = [h for h in hosts if product == "auto" or h.product == product]
    if year is not None:
        options = [h for h in options if h.year == year]
    options = list({(h.product, h.year, h.executable.casefold()): h for h in options}.values())
    host = options[0] if len(options) == 1 else Host(
        product if product != "auto" else "unknown", year, platform,
        evidence="requested_unverified" if product != "auto" else "ambiguous_or_absent")
    if backend == "com":
        if not host.interfaces["external_com"] or len(options) > 1 or (hosts and not options):
            raise ValueError("COM requires an identified full Windows AutoCAD; use exchange for LT or an ambiguous host")
        return host, "com"
    if backend == "auto" and host.interfaces["external_com"] and len(options) == 1:
        return host, "com"
    return host, "exchange"


def publication_route(hosts, backend, product, year, experimental_lt, platform=None):
    """Keep the established COM entry point and require explicit LT opt-in."""
    platform = platform or sys.platform
    if backend == "exchange" or product == "lt" or experimental_lt:
        if (backend, product, experimental_lt) != ("exchange", "lt", True):
            raise ValueError("Experimental LT requires --backend exchange --product lt --experimental-lt")
        return choose(hosts, "exchange", "lt", year, platform)
    if platform != "win32":
        raise ValueError("Full AutoCAD native publication requires Windows")
    if hosts and not any(host.product == "autocad" for host in hosts):
        raise ValueError("Full AutoCAD was not found. LT exchange requires explicit Experimental opt-in")
    # A full installation can be unregistered or coexist with other full versions.
    # The worker confirms the live product and any explicitly requested year.
    return Host("autocad", year, platform, evidence="live_full_product_check_required"), "com"
