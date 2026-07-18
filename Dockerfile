FROM python:3.12-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    android-tools-adb \
    usbutils \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY scripts/ /app/scripts/

RUN mkdir -p /root/.android && \
    python3 /app/scripts/adb_keygen.py /root/.android && \
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
