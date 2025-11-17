#!/usr/bin/env python3
"""
STEP 1: Run Il2CppDumper with LIVE LOGS
- Auto-creates config.json next to .exe
- Cleans old output
- Shows every line of progress
- Takes 5–15 minutes
"""

import sys, os, json, subprocess, shutil
from pathlib import Path

# === CONFIG ===
DLL    = Path("GameAssembly.dll")
META   = Path("global-metadata.dat")
DUMPER = Path("Il2CppDumper.exe")

# === VALIDATE FILES ===
for name, p in [("DLL", DLL), ("META", META), ("DUMPER", DUMPER)]:
    if not p.is_file():
        print(f"[ERROR] {name} not found: {p.resolve()}")
        sys.exit(1)
print("[OK] All 3 files found")

# === AUTO-CREATE config.json NEXT TO EXE ===
cfg_path = DUMPER.parent / "config.json"
if not cfg_path.is_file():
    print(f"[INFO] Creating config.json at {cfg_path}")
    cfg = {
        "ForceIl2CppVersion": True,
        "ForceVersion": 27.2,
        "DumpMethodOffset": True,
        "DumpFieldOffset": True,
        "DumpPropertyOffset": True,
        "OutputDirectory": "il2cppdumper"
    }
    cfg_path.write_text(json.dumps(cfg, indent=2))
else:
    print(f"[OK] config.json found")

# === CLEAN OLD OUTPUT ===
out_dir = Path("il2cppdumper")
if out_dir.exists():
    print("[INFO] Removing old il2cppdumper/ folder")
    shutil.rmtree(out_dir)

# === RUN WITH LIVE LOGS ===
print("\n" + "="*70)
print("STARTING Il2CppDumper – LIVE OUTPUT BELOW")
print("This will take 5–15 minutes. DO NOT CLOSE.")
print("="*70 + "\n")

try:
    proc = subprocess.Popen(
        [str(DUMPER), str(DLL), str(META)],
        cwd=DUMPER.parent,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    for line in proc.stdout:
        print(line, end="")

    if proc.wait() != 0:
        print("\n[ERROR] Il2CppDumper crashed!")
        sys.exit(1)

except KeyboardInterrupt:
    print("\n[STOP] User interrupted.")
    sys.exit(1)

print("\n" + "="*70)
print("Il2CppDumper FINISHED!")
print("="*70)

# === VERIFY OUTPUT ===
dump_cs = out_dir / "dump.cs"
script_json = out_dir / "script.json"

if not dump_cs.is_file():
    print("[ERROR] dump.cs was not created!")
    sys.exit(1)

print(f"[OK] dump.cs: {dump_cs.stat().st_size // 1024 // 1024} MB")
print(f"[OK] script.json: {script_json.stat().st_size // 1024} KB")
print("\nNEXT STEP: Run → python dumper_smart.py")