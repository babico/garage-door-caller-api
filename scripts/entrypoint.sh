#!/bin/sh
adb kill-server 2>/dev/null || true
adb start-server 2>/dev/null || true
exec "$@"
