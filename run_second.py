#!/usr/bin/env python3
"""
STEP 2: Parse dump.cs + script.json → external + internal offsets
- external_offsets.h → ESP, Aimbot, No Recoil (~40 lines)
- internal_offsets.h → Full dump for hooks (~3000+ lines)
"""

import re, json
from pathlib import Path

# === LOAD FILES ===
DUMP_CS = Path("il2cppdumper/dump.cs")
SCRIPT_JSON = Path("il2cppdumper/script.json")

if not DUMP_CS.is_file() or not SCRIPT_JSON.is_file():
    print("[ERROR] Run dumper_final.py first!")
    exit(1)

dump_cs = DUMP_CS.read_text(encoding="utf-8")
script = json.loads(SCRIPT_JSON.read_text(encoding="utf-8"))

# === CRITICAL CLASSES & FIELDS ===
EXTERNAL_CLASSES = {
    "BasePlayer", "PlayerInventory", "BaseEntity", "BaseCombatEntity",
    "BaseProjectile", "BaseProjectile.Magazine", "Item", "ConVar_Graphics",
    "MainCamera", "BaseNetworkable", "PlayerEyes", "PlayerModel",
    "RecoilProperties", "ItemDefinition", "HeldEntity"
}

EXTERNAL_FIELDS = {
    "BasePlayer": ["_health", "playerFlags", "clActiveItem", "inventory", "model", "eyes", "movement", "playerName"],
    "PlayerInventory": ["containerMain", "containerWear", "containerBelt"],
    "BaseEntity": ["_name", "prefabID", "transform"],
    "BaseCombatEntity": ["_health", "_maxHealth"],
    "BaseProjectile": ["primaryMagazine", "recoil", "aimcone", "automatic", "repeatDelay"],
    "Item": ["info", "amount", "uid"],
    "PlayerEyes": ["viewOffset", "bodyRotation"],
    "PlayerModel": ["position", "rotation"],
    "RecoilProperties": ["recoilYawMin", "recoilYawMax", "recoilPitchMin", "recoilPitchMax"]
}

# === REGEX ===
FIELD_RE = re.compile(r"\s*(public|private|protected|internal|static)\s+[\w<>, \[\]]+\s+(\w+).*=.*?;\s*//\s*(0x[0-9a-fA-F]+)")
METHOD_RE = re.compile(r"\s*(?:public|private|protected|internal|static|virtual|override)?\s*[\w<>, \[\]]+\s+(\w+)\s*\(.*\)\s*(?:\{|//)\s*(0x[0-9a-fA-F]+)")

# === PARSE ===
external = {}
internal = {}
current_class = ""

for line in dump_cs.splitlines():
    line = line.strip()
    if not line or line.startswith("//"): continue

    if m := re.match(r"class\s+(\w+)", line):
        current_class = m.group(1)
        continue
    if line == "}":
        current_class = ""
        continue

    if fm := FIELD_RE.search(line):
        name, offset = fm.group(2), fm.group(3)
        key = f"{current_class}_{name}"
        if current_class in EXTERNAL_CLASSES:
            if any(p in name for p in EXTERNAL_FIELDS.get(current_class, [])):
                external[key] = offset
            internal[key] = offset
        else:
            internal[key] = offset
        continue

    if mm := METHOD_RE.search(line):
        name, offset = mm.group(1), mm.group(2)
        internal[f"{current_class}_{name}"] = offset

# === script.json class pointers ===
for entry in script.get("ScriptMetadata", []):
    name = entry.get("Name", "")
    addr = entry.get("Address")
    if name and addr:
        key = f"{name}_c"
        external[key] = hex(int(addr))
        internal[key] = hex(int(addr))

# === WRITE HEADERS ===
def write_h(path, data, title):
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"// {title}\n")
        f.write("// Auto-generated – DO NOT EDIT\n\n")
        f.write("#pragma once\n#include <cstdint>\n#define roffset static uintptr_t\n\n")
        f.write("namespace rust {\n\n")
        for k, v in sorted(data.items()):
            f.write(f"\troffset {k} = {v};\n")
        f.write("\n} // namespace rust\n")

print(f"\nWriting {len(external)} external offsets → external_offsets.h")
write_h("external_offsets.h", external, "EXTERNAL OFFSETS – ESP, Aimbot, No Recoil")

print(f"Writing {len(internal)} internal offsets → internal_offsets.h")
write_h("internal_offsets.h", internal, "INTERNAL OFFSETS – Full Hook Dump")

print("\nSUCCESS! Files created:")
print("   • external_offsets.h")
print("   • internal_offsets.h")