# Garage Door Caller API

FastAPI REST API that opens a garage door via ADB-connected Android phone by automating calls and dialer keypad input.

## Requirements

- Python 3.11+
- ADB installed and in PATH
- Android phone connected via USB with USB debugging enabled
- Android phone with active SIM card (calls go over cellular network)
- Server / PC / homelab always powered on with phone attached via USB

## Prerequisites

### SIM Card

The Android phone MUST have an active SIM card with calling capability. The API uses `android.intent.action.CALL` which places a regular cellular call — no VoIP, no internet calling. Without a SIM, calls fail silently.

### Always-On Host

The phone must stay physically connected to the host machine 24/7. The API does not wake the host or reattach USB — it expects the phone to already be plugged in, USB debugging authorized, and the ADB daemon running.

Recommended setup:

| Component | Suggestion                                           |
| --------- | ---------------------------------------------------- |
| Host      | Raspberry Pi, old laptop, home server, NAS           |
| Phone     | Cheap Android, SIM-only plan, auto-start on boot     |
| Power     | Phone plugged into host USB (keeps charged)          |
| ADB       | Run `adb devices` after each phone reboot to confirm |

After connecting the phone, verify ADB sees it:

```bash
adb devices
# List of devices attached
# qwerty123456qwerty123456    device
```

## Environment Variables

| Variable            | Required | Default              | Description                         |
| ------------------- | -------- | -------------------- | ----------------------------------- |
| `PHONE_NUMBER`      | YES      | —                    | Garage door phone number            |
| `DOOR_CODE`         | YES      | —                    | Digits to type (e.g. `*`, `4`)      |
| `PHONE_SERIAL`      | YES      | —                    | ADB device serial + phones.yaml key |
| `WAIT_AFTER_DIAL_S` | NO       | `0`                  | Seconds to wait after dialing       |
| `CONFIG_PATH`       | NO       | `config/phones.yaml` | Path to phone config YAML           |
| `ADB_PATH`          | NO       | `adb`                | Path to adb binary                  |

## Phone Config (config/phones.yaml)

Schema per phone serial:

```yaml
serials:
  qwerty123456qwerty123456:
    manufacturer: HUAWEI
    screen:
      width: 1080
      height: 2340
    wake_up: true
    phone_pin: "123456"
    keypad_tap:
      x: 228
      y: 1937
```

| Field            | Type    | Default    | Description                                                                                                |
| ---------------- | ------- | ---------- | ---------------------------------------------------------------------------------------------------------- |
| `manufacturer`   | str     | required   | Human-readable brand name                                                                                  |
| `screen`         | dict    | required   | `{width, height}` in pixels                                                                                |
| `wake_up`        | bool    | `false`    | Send KEYCODE_WAKEUP before unlock                                                                          |
| `phone_pin`      | str     | `""`       | Phone unlock PIN digits                                                                                    |
| `swipe_unlock`   | dict    | `null`     | Explicit `{start_x, start_y, end_x, end_y, duration_ms}`. If omitted, auto-computed from screen dimensions |
| `keypad_tap`     | dict    | `null`     | `{x, y}` to tap the dialer keypad button during call. If null, call is made but no keypad/door-code entry  |

Keyevent codes (0-9, *, #) are hardcoded in `app/adb_service.py` as `KEYCODE_MAP` (universal Android constants).

## Architecture

```plaintext
garage-door-caller/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app, lifespan, route registration
│   ├── config.py            # Settings (env vars) + PhoneConfigLoader (YAML)
│   ├── models.py            # Pydantic schemas: PhoneConfig, responses
│   ├── adb_service.py       # ADB subprocess calls, KEYCODE_MAP, workflow
│   └── routes/
│       ├── __init__.py
│       ├── health.py        # GET /health
│       └── call.py          # POST /call
├── config/
│   └── phones.yaml          # Per-phone-serial ADB parameters
├── tests/                   # 64 tests (pytest)
├── .env.example             # Required env var template
├── requirements.txt
└── .gitignore
```

## Workflow

```plaintext
is_device_locked()?  (dumpsys trust → deviceLocked=1/0)
  ├─ deviceLocked=0  → skip unlock steps
  └─ deviceLocked=1  → unlock:
       ├─ wake_up?  → KEYCODE_WAKEUP
       ├─ swipe_unlock? → explicit coords
       │   └─ or auto: center X, bottom-100px → top 20%, 300ms
       └─ type phone_pin digits via KEYCODE_MAP

keypad_tap set?
  ├─ yes → start_call() → sleep(wait_after_dial_s) → tap(keypad) → type door_code
  └─ no  → skip (phone config has no keypad support)
```

## Endpoints

| Method | Path     | Purpose                                        |
|--------|----------|------------------------------------------------|
| GET    | `/`      | Redirect to Swagger docs                       |
| GET    | `/health`| ADB daemon, device, and config status          |
| POST   | `/call`  | Execute full call workflow (open garage door)  |

### GET /health

```json
{
  "status": "ok",
  "adb": {
    "available": true,
    "daemon_running": true,
    "devices": [{"serial": "qwerty123456qwerty123456", "state": "device", "model": "SNE-LX1"}]
  },
    "config": {
    "phone_serial": "qwerty123456qwerty123456",
    "config_loaded": true
  }
}
```

### POST /call

```json
{"status": "ok", "message": "Call initiated", "phone_number": "4441444", "door_code": "*", "duration_ms": 19765}
```

## Error Codes

| Code                   | HTTP | Meaning                            |
| ---------------------- | ---- | ---------------------------------- |
| `PHONE_SERIAL_UNKNOWN` | 400  | Serial not found in phones.yaml    |
| `CALL_FAILED`          | 502  | `am start CALL` returned non-zero  |
| `DEVICE_NOT_FOUND`     | 503  | No ADB device connected            |
| `DEVICE_UNAUTHORIZED`  | 503  | USB debugging not authorized       |

## Run

```bash
# Set env vars
export PHONE_NUMBER=4441444 DOOR_CODE="*" PHONE_SERIAL=qwerty123456qwerty123456 WAIT_AFTER_DIAL_S=16

# Install
pip install -r requirements.txt

# Run
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Reverse Proxy

```nginx
server {
    listen 443 ssl;
    server_name garage.example.com;

    location / {
        proxy_pass http://192.168.21.2:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

Or Caddy:

```caddy
garage.example.com {
    reverse_proxy 192.168.21.2:8000
}
```

### Tests

```bash
pytest tests/   # 64 tests
```
