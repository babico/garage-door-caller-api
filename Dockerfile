FROM python:3.12-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    android-tools-adb \
    usbutils \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /root/.android && \
    openssl genrsa -out /root/.android/adbkey 4096 && \
    python3 -c "
import base64, re, struct, subprocess
mod_hex = subprocess.check_output(['openssl', 'rsa', '-in', '/root/.android/adbkey', '-noout', '-modulus']).decode().split('=')[1].strip()
if len(mod_hex) % 2: mod_hex = '0' + mod_hex
mod = bytes.fromhex(mod_hex)
text = subprocess.check_output(['openssl', 'rsa', '-in', '/root/.android/adbkey', '-text', '-noout']).decode()
m = re.search(r'publicExponent:\s*(\d+)', text)
e_int = int(m.group(1))
exp = e_int.to_bytes((e_int.bit_length() + 7) // 8, 'big')
pub = struct.pack('<I', len(mod)) + mod + struct.pack('<I', len(exp)) + exp
with open('/root/.android/adbkey.pub', 'w') as f:
    f.write(base64.b64encode(pub).decode() + ' unknown@unknown\n')
" && \
    printf "0x12d1\n0x04e8\n0x18d1\n0x22b8\n0x2717\n0x2a70\n0x0bb4\n0x1004\n0x05c6\n0x17ef\n" > /root/.android/adb_usb.ini

ENV ADB_VENDOR_KEYS=/root/.android

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
