#!/usr/bin/env bash
set -euo pipefail

host=${1:-}
port=${2:-}
server_name=${3:-$host}

if [[ -z "$host" || ! "$port" =~ ^[0-9]+$ || "$port" -lt 1 || "$port" -gt 65535 ]]; then
    printf 'usage: tls_certificate_expiry.sh <host> <port> [server-name]\n' >&2
    exit 2
fi

not_after=$(
    timeout 15 openssl s_client \
        -connect "${host}:${port}" \
        -servername "$server_name" \
        -showcerts </dev/null 2>/dev/null \
    | openssl x509 -noout -enddate \
    | sed -n 's/^notAfter=//p'
)

if [[ -z "$not_after" ]]; then
    printf 'no leaf certificate returned by %s:%s\n' "$host" "$port" >&2
    exit 1
fi

LC_ALL=C date -u -d "$not_after" +%s
