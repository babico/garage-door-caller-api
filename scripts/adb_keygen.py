import base64
import re
import struct
import subprocess
import sys


def generate_adb_keys(out_dir: str) -> None:
    priv_path = f"{out_dir}/adbkey"
    pub_path = f"{out_dir}/adbkey.pub"

    subprocess.run(
        ["openssl", "genrsa", "-out", priv_path, "4096"],
        check=True, capture_output=True,
    )

    mod_hex = subprocess.check_output(
        ["openssl", "rsa", "-in", priv_path, "-noout", "-modulus"],
    ).decode().split("=")[1].strip()
    if len(mod_hex) % 2:
        mod_hex = "0" + mod_hex
    mod = bytes.fromhex(mod_hex)

    text = subprocess.check_output(
        ["openssl", "rsa", "-in", priv_path, "-text", "-noout"],
    ).decode()
    m = re.search(r"publicExponent:\s*(\d+)", text)
    e_int = int(m.group(1))
    exp = e_int.to_bytes((e_int.bit_length() + 7) // 8, "big")

    pub = struct.pack("<I", len(mod)) + mod + struct.pack("<I", len(exp)) + exp

    with open(pub_path, "w") as f:
        f.write(base64.b64encode(pub).decode() + " unknown@unknown\n")


if __name__ == "__main__":
    generate_adb_keys(sys.argv[1])
