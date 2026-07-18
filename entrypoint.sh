#!/bin/sh
adb start-server 2>/dev/null || true
exec "$@"
