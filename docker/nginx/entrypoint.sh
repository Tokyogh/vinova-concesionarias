#!/bin/sh
# ES: Ejecuta el flujo operativo «entrypoint» con fallos controlados y sin ocultar errores.
# EN: Runs the «entrypoint» operational flow with controlled failures and visible errors.
# Renders the selected HTTP/HTTPS Nginx template from explicit environment values.
set -eu


TRUSTED_PROXY_CIDR=${NGINX_TRUSTED_PROXY_CIDR:-}
TRUSTED_PROXY_FILE=/etc/nginx/conf.d/00-trusted-proxy.conf
rm -f "$TRUSTED_PROXY_FILE"
if [ -n "$TRUSTED_PROXY_CIDR" ]; then
  case "$TRUSTED_PROXY_CIDR" in
# ES: La sección siguiente define precondiciones, límites y propagación explícita de fallos.
# EN: The following section defines preconditions, limits, and explicit failure propagation.
    *[!0-9A-Fa-f:./]*)
      echo "NGINX_TRUSTED_PROXY_CIDR debe ser una IP o CIDR literal." >&2
      exit 1
      ;;
  esac
  cat > "$TRUSTED_PROXY_FILE" <<EOF
set_real_ip_from $TRUSTED_PROXY_CIDR;
real_ip_header X-Forwarded-For;
real_ip_recursive on;
EOF
fi

NGINX_SERVER_NAME=${NGINX_SERVER_NAME:-_}
NGINX_CLIENT_MAX_BODY_SIZE=${NGINX_CLIENT_MAX_BODY_SIZE:-25m}
NGINX_PROXY_READ_TIMEOUT=${NGINX_PROXY_READ_TIMEOUT:-120s}
NGINX_FORWARDED_PROTO=${NGINX_FORWARDED_PROTO:-http}
NGINX_LOGIN_RATE=${NGINX_LOGIN_RATE:-10r/m}
NGINX_LOGIN_BURST=${NGINX_LOGIN_BURST:-10}
NGINX_SSL_CERTIFICATE=${NGINX_SSL_CERTIFICATE:-/etc/nginx/certs/fullchain.pem}
NGINX_SSL_CERTIFICATE_KEY=${NGINX_SSL_CERTIFICATE_KEY:-/etc/nginx/certs/privkey.pem}

if ! printf '%s' "$NGINX_LOGIN_RATE" | grep -Eq '^[1-9][0-9]*r/(s|m)$'; then
  echo "NGINX_LOGIN_RATE invalido: use un valor como 10r/m o 5r/s." >&2
  exit 1
fi
if ! printf '%s' "$NGINX_LOGIN_BURST" | grep -Eq '^[1-9][0-9]*$'; then
  echo "NGINX_LOGIN_BURST debe ser un entero positivo." >&2
  exit 1
fi

export NGINX_SERVER_NAME NGINX_CLIENT_MAX_BODY_SIZE NGINX_PROXY_READ_TIMEOUT
export NGINX_FORWARDED_PROTO NGINX_LOGIN_RATE NGINX_LOGIN_BURST
export NGINX_SSL_CERTIFICATE NGINX_SSL_CERTIFICATE_KEY

TLS_ENABLED=$(printf '%s' "${NGINX_TLS_ENABLED:-false}" | tr '[:upper:]' '[:lower:]')
if [ "$TLS_ENABLED" = "true" ] || [ "$TLS_ENABLED" = "1" ] || [ "$TLS_ENABLED" = "yes" ]; then
  TEMPLATE=/opt/vinova/templates/https.conf.template
  test -r "$NGINX_SSL_CERTIFICATE"
  test -r "$NGINX_SSL_CERTIFICATE_KEY"
else
  TEMPLATE=/opt/vinova/templates/http.conf.template
fi

envsubst '${NGINX_SERVER_NAME} ${NGINX_CLIENT_MAX_BODY_SIZE} ${NGINX_PROXY_READ_TIMEOUT} ${NGINX_FORWARDED_PROTO} ${NGINX_LOGIN_RATE} ${NGINX_LOGIN_BURST} ${NGINX_SSL_CERTIFICATE} ${NGINX_SSL_CERTIFICATE_KEY}' \
  < "$TEMPLATE" > /etc/nginx/conf.d/default.conf

if grep -Eq '[$][{]NGINX_[A-Z0-9_]+[}]' /etc/nginx/conf.d/default.conf; then
  echo "La configuracion Nginx contiene variables NGINX sin resolver." >&2
  grep -En '[$][{]NGINX_[A-Z0-9_]+[}]' /etc/nginx/conf.d/default.conf >&2 || true
  exit 1
fi

nginx -t
exec "$@"
