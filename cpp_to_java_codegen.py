import re

INPUT_FILE = "input_header.h"
OUTPUT_FILE = "GeneratedRegisters.java"


def extract_macro_block(text, macro_name):
    lines = text.splitlines()
    start_idx = None

    for i, line in enumerate(lines):
        if f"#define {macro_name}" in line:
            start_idx = i
            break

    if start_idx is None:
        raise RuntimeError(f"{macro_name} not found")

    brace_count = 0
    collecting = False
    block_lines = []

    for line in lines[start_idx:]:
        if "{\\" in line and not collecting:
            collecting = True

        if collecting:
            block_lines.append(line)

        brace_count += line.count("{")
        brace_count -= line.count("}")

        if collecting and brace_count == 0:
            break

    return "\n".join(block_lines)


def parse_default_value(val):
    val = val.strip()
    inner = val[1:-1].strip()

    if not inner:
        return "new long[]{0x0L}", None

    parts = [p.strip() for p in inner.split(",") if p.strip()]
    longs = []

    for p in parts:
        if not p.startswith("0x"):
            return "null", inner
        hexpart = p[2:]
        if len(hexpart) > 16:
            return "null", inner
        longs.append(f"0x{hexpart}L")

    return f"new long[]{{{', '.join(longs)}}}", None


def parse_entry(entry, index):
    if ".name" not in entry:
        return f"// 0x{index:02X}\nnull,"

    name = re.search(r'\.name\s*=\s*"([^"]+)"', entry).group(1)
    addr = re.search(r'\.regAddr\s*=\s*(0x[0-9a-fA-F]+)', entry).group(1)
    length = re.search(r'\.len\s*=\s*(0x[0-9a-fA-F]+)', entry).group(1)

    rom = re.search(r'\.romDefault\s*=\s*({[^}]*})', entry, re.S)
    rom_val = rom.group(1) if rom else "{0x0}"

    rom_java, rom_hex = parse_default_value(rom_val)

    if rom_hex is None:
        return f'new Register("{name}",{addr},{length},{rom_java}),'
    else:
        return f'new Register("{name}",{addr},{length},null,"{rom_hex}"),'


def main():
    with open(INPUT_FILE, "r") as f:
        text = f.read()

    block = extract_macro_block(text, "REGISTER_TABLE")
    entries = block.split("},")

    java_entries = [
        parse_entry(e, idx) for idx, e in enumerate(entries)
    ]

    java_body = "\n".join(java_entries)

    java_code = f"""
public final class GeneratedRegisters {{

    public static final class Register {{
        public final String name;
        public final int address;
        public final int length;
        public final long[] defaultValue;
        public final String rawHex;

        public Register(String name,int address,int length,long[] defaultValue){{
            this(name,address,length,defaultValue,null);
        }}

        public Register(String name,int address,int length,long[] defaultValue,String rawHex){{
            this.name = name;
            this.address = address;
            this.length = length;
            this.defaultValue = defaultValue;
            this.rawHex = rawHex;
        }}
    }}

    public static final Register[] REGISTERS = {{
{java_body}
    }};
}}
"""

    with open(OUTPUT_FILE, "w") as f:
        f.write(java_code)

    print("Generated:", OUTPUT_FILE)


if __name__ == "__main__":
    main()
