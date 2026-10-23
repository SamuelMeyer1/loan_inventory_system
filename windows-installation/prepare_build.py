"""Fail before packaging if user-visible versions or build inputs drift."""
import platform
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app_version import VERSION

if sys.platform != "win32" or platform.machine() not in ("AMD64", "x86_64"):
    raise SystemExit("Build requires Windows x64 Python.")
if f"Version {VERSION}" not in (ROOT / "frontend" / "index.html").read_text(encoding="utf-8"):
    raise SystemExit("Frontend version differs from app_version.py.")
if f"Nuvarande version: V{VERSION}" not in (ROOT / "uppdates").read_text(encoding="utf-8"):
    raise SystemExit("uppdates version differs from app_version.py.")
version_tuple = tuple(int(part) for part in VERSION.split(".")) + (0,)
text = f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers={version_tuple!r}, prodvers={version_tuple!r},
                   mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[StringFileInfo([StringTable('040904B0', [
    StringStruct('CompanyName', 'Samuel Meyer'),
    StringStruct('FileDescription', 'Loan Inventory'),
    StringStruct('FileVersion', '{VERSION}'),
    StringStruct('ProductName', 'Loan Inventory'),
    StringStruct('ProductVersion', '{VERSION}')
  ])]), VarFileInfo([VarStruct('Translation', [1033, 1200])])]
)
"""
(ROOT / "windows-installation" / "version-info.txt").write_text(text, encoding="utf-8")
