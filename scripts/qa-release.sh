#!/usr/bin/env bash
# ES: Ejecuta el flujo operativo «qa release» con fallos controlados y sin ocultar errores.
# EN: Runs the «qa release» operational flow with controlled failures and visible errors.
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/vinova-qa.sh" release
