#!/usr/bin/env python3

import re
import json
from pathlib import Path

# === CONFIGURATION ===
DUMP_CS = Path("il2cppdumper/dump.cs")
SCRIPT_JSON = Path("il2cppdumper/script.json")

if not DUMP_CS.is_file() or not SCRIPT_JSON.is_file():
    print("[ERROR] Missing dump.cs or script.json! Run Il2CppDumper first.")
    exit(1)

dump_cs = DUMP_CS.read_text(encoding="utf-8", errors="ignore")
script = json.loads(SCRIPT_JSON.read_text(encoding="utf-8"))

# === CRITICAL CLASSES FOR EXTERNAL CHEAT (ESP, Aimbot, No Recoil, etc.) ===
EXTERNAL_CLASSES = {
    "EFT.Player",
    "EFT.LocalPlayer",
    "EFT.PlayerBody",
    "EFT.InventoryController",
    "EFT.Weapon",
    "EFT.FirearmController",
    "EFT.BallisticsCalculator",
    "EFT.CameraManager",
    "EFT.GameWorld",
    "EFT.ObservedPlayerView",
    "EFT.Inventory",
    "EFT.ProceduralWeaponAnimation",
    "EFT.HandsController",
    "EFT.PlayerBones",
    "EFT.HealthController",
    "EFT.MovementContext",
    "E.CameraClass",  # Main camera
}

# === FIELDS WE CARE ABOUT FOR EXTERNAL FEATURES ===
EXTERNAL_FIELDS = {
    "EFT.Player": [
        "_healthController", "Profile", "PlayerBody", "MovementContext",
        "HandsController", "IsLocalPlayer", "Side", "RegistrationDate"
    ],
    "EFT.PlayerBody": ["SkeletonRootJoint", "BodySkeletons"],
    "EFT.HealthController": ["_health"],
    "EFT.LocalPlayer": ["_handsController", "_proceduralWeaponAnimation"],
    "EFT.ProceduralWeaponAnimation": ["Breath", "MotionReact", "Recoil", "Shootingg"],
    "EFT.FirearmController": ["Weapon", "CurrentOperation"],
    "EFT.Weapon": ["Template", "CurrentMagazine"],
    "EFT.MovementContext": ["Rotation", "Position", "CharacterMovementSpeed"],
    "EFT.PlayerBones": ["Bones"],  # Dictionary of bone transforms
    "EFT.InventoryController": ["Inventory"],
    "E.CameraClass": ["Camera"],  # Main camera instance
    "EFT.GameWorld": ["RegisteredPlayers", "LocalPlayer", "AllPlayers"],
}

# Optional extra
    "EFT.ObservedPlayerView": [],  # For observed/coop players
}

# regex
FIELD_RE = re.compile(
    r"\s*(?:public|private|protected|internal)?\s+"
    r"[\w<>\[\],.]+?\s+(\w+)\s*=.*?;\s*//\s*(0x[0-9a-fA-F]+)"
)

METHOD_RE = re.compile(
    r"\s*(?:public|private|protected|internal|virtual|override)?\s+"
    r"[\w<>\[\],.]+\s+(\w+)\s*\(.*?\)\s*(?:{|;//)\s*(0x[0-9a-fA-F]+)"
)

TYPEDEF_RE = re.compile(r"class\s+(\w+(?:\.\w+)?)")

external = {}
internal = {}
current_class = ""

print("[+] Parsing dump.cs...")

for line in dump_cs.splitlines():
    line = line.strip()
    if not line or line.startswith("//"):
        continue

    # Detect class
    if m := TYPEDEF_RE.search(line):
        current_class = m.group(1)
        continue
    if line == "}":
        current_class = ""
        continue

    # Field offset
    if fm := FIELD_RE.search(line):
        field_name = fm.group(1)
        offset = fm.group(2)
        key = f"{current_class}::{field_name}"

        # Add to internal always
        internal[key] = offset

        # Add to external if class is important and field matches
        if current_class in EXTERNAL_CLASSES:
            wanted = EXTERNAL_FIELDS.get(current_class, [])
            if not wanted or any(pat in field_name for pat in wanted):
                external[key] = offset

    if mm := METHOD_RE.search(line):
        method_name = mm.group(1)
        offset = mm.group(2)
        key = f"{current_class}::{method_name}"
        internal[key] = offset

print("[+] Adding ScriptMetadata class pointers...")
for entry in script.get("ScriptMetadata", []):
    name = entry.get("Name")
    addr = entry.get("Address")
    if name and addr and addr != "0x0":
        clean_name = name.replace(".", "_")  # EFT.GameWorld → EFT_GameWorld_c maybe? i aint too sure personally
        key = f"{clean_name}_c"
        hex_addr = hex(int(addr, 16) + 0x0)  
        external[key] = hex_addr
        internal[key] = hex_addr


MUST_HAVE = {
    "EFT_GameWorld_c": None,
    "EFT_LocalPlayer_c": None,
    "E.CameraClass_c": None,
}

for k in MUST_HAVE:
    if k not in external:
        print(f"[!] Warning: {k} not found in ScriptMetadata – you may need to find it manually")

# === WRITE HEADERS ===
def write_header(path: str, data: dict, title: str):
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"// {title}\n")
        f.write("// as much as i hate ai, i love using my own model to scrape and collect stuff for me\n")
        f.write("// Generated on: 2025\n\n")
        f.write("#pragma once\n")
        f.write("#include <cstdint>\n\n")
        f.write("#define roffset static uintptr_t\n\n")
        f.write("namespace eft {\n\n")

        for key, value in sorted(data.items()):
            f.write(f"\troffset {key} = {value};\n")

        f.write("\n} // namespace eft\n")

    print(f"[+] Wrote {len(data)} offsets → {path}")

# output ig? may need some tweaking 
write_header("external_offsets.h", external, "EXTERNAL OFFSETS – ESP, Aimbot, No Recoil, Loot")
write_header("internal_offsets.h", internal, "INTERNAL OFFSETS – Full Hook Dump")

print("   • external_offsets.h  → Use for ESP/Aimbot/NoRecoil")
print("   • internal_offsets.h  → Use for memory hooks, triggers, etc.")
print("\nTip: Always verify GameWorld, LocalPlayer, and Camera offsets manually after wipe!")