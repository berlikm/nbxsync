#!/usr/bin/env bash
#
# Zabbix 7.0 dev/test environment — Podman (no compose needed)
# Self-contained: builds a custom server image with fping+snmp,
# starts all services in a pod, creates API token, and optionally
# runs nbxsync configure + sync.
#
# Usage:
#   ./setup_zabbix.sh                    # Start + configure + sync
#   ./setup_zabbix.sh --no-sync          # Start only, no nbxsync
#   ./setup_zabbix.sh --wipe            # Wipe all data and restart fresh
#   ./setup_zabbix.sh --wipe --no-sync   # Fresh start, configure only
#
set -euo pipefail

ZABBIX_URL="http://localhost:8080"
ADMIN_USER="Admin"
ADMIN_PASS="zabbix"
TOKEN_NAME="nbxsync"
IMAGE_NAME="zbx-server-custom"
POD_NAME="zbx"

# nbxsync env vars (override with export before running)
: "${NBX_SNMP_AUTHPASS_MON:=0yJVUM5XcZer7hkLs9zl}"
: "${NBX_SNMP_PRIVPASS_MON:=vL4YqRODaGUAIQ54rmoJ}"
: "${NBX_SNMP_AUTHPASS_LINUX:=$NBX_SNMP_AUTHPASS_MON}"
: "${NBX_SNMP_PRIVPASS_LINUX:=$NBX_SNMP_PRIVPASS_MON}"
: "${NBX_SNMP_AUTHPASS_DELL:=$NBX_SNMP_AUTHPASS_MON}"
: "${NBX_SNMP_PRIVPASS_DELL:=$NBX_SNMP_PRIVPASS_MON}"
: "${NBX_SNMP_AUTHPASS_SAP:=$NBX_SNMP_AUTHPASS_MON}"
: "${NBX_SNMP_PRIVPASS_SAP:=$NBX_SNMP_PRIVPASS_MON}"

NO_SYNC=false
WIPE=false
for arg in "$@"; do
    case $arg in
        --no-sync) NO_SYNC=true ;;
        --wipe)    WIPE=true ;;
    esac
done

echo "╔═══════════════════════════════════════════════════════╗"
echo "║  Zabbix 7.0 Dev/Test Environment (Podman)             ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo ""

# ── 1. Wipe (optional) ───────────────────────────────────
if $WIPE; then
    echo "⚠  Wiping all data..."
    sudo podman stop zbx-server zbx-web zbx-db 2>/dev/null || true
    sudo podman rm zbx-server zbx-web zbx-db 2>/dev/null || true
    sudo podman pod rm "$POD_NAME" 2>/dev/null || true
    sudo podman volume rm zbx-pgdata 2>/dev/null || true
    echo "✓ Wiped"
fi

# ── 2. Build custom Zabbix server image ──────────────────
echo "Building custom Zabbix server image (fping + snmp)..."
BUILD_DIR=$(mktemp -d)
cat > "$BUILD_DIR/Dockerfile" <<'DOCKERFILE'
FROM zabbix/zabbix-server-pgsql:ubuntu-7.0-latest
USER root
RUN apt-get update -qq && \
    apt-get install -y --no-install-recommends fping snmp && \
    rm -rf /var/lib/apt/lists/* && \
    chmod 4755 /usr/bin/fping
USER zabbix
DOCKERFILE

sudo podman build -t "$IMAGE_NAME" "$BUILD_DIR" 2>&1 | tail -3
rm -rf "$BUILD_DIR"
echo "✓ Image built: $IMAGE_NAME"

# ── 3. Create pod + volumes ─────────────────────────────
echo "Creating pod..."
sudo podman pod create --name "$POD_NAME" -p 8080:8080 2>/dev/null || true
sudo podman volume create zbx-pgdata 2>/dev/null || true

# ── 4. Start PostgreSQL ───────────────────────────────────
echo "Starting PostgreSQL..."
sudo podman run -d --name zbx-db --pod "$POD_NAME" \
    -e POSTGRES_USER=zabbix \
    -e POSTGRES_PASSWORD=zabbix \
    -e POSTGRES_DB=zabbix \
    -v zbx-pgdata:/var/lib/postgresql/data \
    --restart=unless-stopped \
    docker.io/library/postgres:16-alpine 2>&1 | tail -1

echo "Waiting for PostgreSQL..."
for i in $(seq 1 15); do
    if sudo podman exec zbx-db pg_isready -U zabbix 2>/dev/null | grep -q "accepting"; then
        echo "✓ PostgreSQL ready"
        break
    fi
    sleep 2
done

# ── 5. Start Zabbix Server ────────────────────────────────
echo "Starting Zabbix Server (custom image, CacheSize=256M)..."
sudo podman run -d --name zbx-server --pod "$POD_NAME" \
    --cap-add=NET_RAW \
    -e DB_SERVER_HOST=127.0.0.1 \
    -e POSTGRES_USER=zabbix \
    -e POSTGRES_PASSWORD=zabbix \
    -e POSTGRES_DB=zabbix \
    -e ZBX_HOSTNAME=zabbix \
    -e ZBX_CACHESIZE=256M \
    --restart=unless-stopped \
    "$IMAGE_NAME" 2>&1 | tail -1

# ── 6. Start Zabbix Web ───────────────────────────────────
echo "Starting Zabbix Web..."
sudo podman run -d --name zbx-web --pod "$POD_NAME" \
    -e DB_SERVER_HOST=127.0.0.1 \
    -e POSTGRES_USER=zabbix \
    -e POSTGRES_PASSWORD=zabbix \
    -e POSTGRES_DB=zabbix \
    -e ZBX_SERVER_HOST=127.0.0.1 \
    -e PHP_TZ=Europe/Zurich \
    -e ZBX_HOSTNAME=zabbix \
    --restart=unless-stopped \
    docker.io/zabbix/zabbix-web-nginx-pgsql:ubuntu-7.0-latest 2>&1 | tail -1

# ── 7. Wait for API ───────────────────────────────────────
echo ""
echo "Waiting for Zabbix API..."
for i in $(seq 1 30); do
    RESP=$(curl -s http://localhost:8080/api_jsonrpc.php \
        -H "Content-Type: application/json" \
        -d '{"jsonrpc":"2.0","method":"apiinfo.version","params":{},"id":1}' 2>/dev/null)
    if echo "$RESP" | grep -q "7.0"; then
        echo "✓ Zabbix API ready"
        break
    fi
    sleep 5
done

sleep 10

# ── 8. Create API token ──────────────────────────────────
echo ""
echo "Creating API token..."
SESSION=$(curl -s http://localhost:8080/api_jsonrpc.php \
    -H "Content-Type: application/json" \
    -d '{"jsonrpc":"2.0","method":"user.login","params":{"username":"'"$ADMIN_USER"'","password":"'"$ADMIN_PASS"'"},"id":1}' \
    | python3 -c "import sys,json; print(json.load(sys.stdin)['result'])")

# Delete old token
OLD=$(curl -s http://localhost:8080/api_jsonrpc.php \
    -H "Content-Type: application/json" \
    -d '{"jsonrpc":"2.0","method":"token.get","params":{"output":["tokenid"],"filter":{"name":"'"$TOKEN_NAME"'}},"auth":"'"$SESSION"'","id":1}' \
    | python3 -c "import sys,json; r=json.load(sys.stdin)['result']; print(r[0]['tokenid'] if r else '')")
if [ -n "$OLD" ]; then
    curl -s http://localhost:8080/api_jsonrpc.php \
        -H "Content-Type: application/json" \
        -d '{"jsonrpc":"2.0","method":"token.delete","params":["'"$OLD"'"],"auth":"'"$SESSION"'","id":1}' > /dev/null
fi

TOKEN_ID=$(curl -s http://localhost:8080/api_jsonrpc.php \
    -H "Content-Type: application/json" \
    -d '{"jsonrpc":"2.0","method":"token.create","params":{"name":"'"$TOKEN_NAME"'","userid":"1"},"auth":"'"$SESSION"'","id":1}' \
    | python3 -c "import sys,json; print(json.load(sys.stdin)['result']['tokenids'][0])")

API_TOKEN=$(curl -s http://localhost:8080/api_jsonrpc.php \
    -H "Content-Type: application/json" \
    -d '{"jsonrpc":"2.0","method":"token.generate","params":{"tokenid":"'"$TOKEN_ID"'"},"auth":"'"$SESSION"'","id":1}' \
    | python3 -c "import sys,json; print(json.load(sys.stdin)['result'][0]['token'])")

echo -n "$API_TOKEN" | sudo tee /tmp/nbxsync_token.txt > /dev/null
echo "✓ Token: ${API_TOKEN:0:20}..."

# ── 9. Create proxies ────────────────────────────────────
echo "Creating proxy group + proxies..."
curl -s http://localhost:8080/api_jsonrpc.php -H "Content-Type: application/json" \
    -d '{"jsonrpc":"2.0","method":"proxygroup.create","params":{"name":"CH Proxy Group"},"auth":"'"$API_TOKEN"'","id":1}' > /dev/null 2>&1

GROUP_ID=$(curl -s http://localhost:8080/api_jsonrpc.php -H "Content-Type: application/json" \
    -d '{"jsonrpc":"2.0","method":"proxygroup.get","params":{"output":["proxy_groupid"],"filter":{"name":"CH Proxy Group"}},"auth":"'"$API_TOKEN"'","id":1}' \
    | python3 -c "import sys,json; r=json.load(sys.stdin)['result']; print(r[0]['proxy_groupid'] if r else '1')")

for name in ch-proxy-1 hu-proxy-1 kr-proxy-1 cn-proxy-1; do
    curl -s http://localhost:8080/api_jsonrpc.php -H "Content-Type: application/json" \
        -d '{"jsonrpc":"2.0","method":"proxy.create","params":{"name":"'"$name"'","operating_mode":"0","proxy_groupid":"'"$GROUP_ID"'","local_address":"127.0.0.1","local_port":"10051"},"auth":"'"$API_TOKEN"'","id":1}' > /dev/null 2>&1
done
echo "✓ Proxies created"

# ── 10. Set global SNMP macros ───────────────────────────
echo "Setting global SNMP macros..."
python3 <<PYTHON
import json, subprocess
API_TOKEN = open("/tmp/nbxsync_token.txt").read().strip()
URL = "http://localhost:8080/api_jsonrpc.php"
def zbx(method, params):
    p = json.dumps({"jsonrpc":"2.0","method":method,"params":params,"auth":API_TOKEN,"id":1})
    r = subprocess.run(["curl","-s",URL,"-H","Content-Type: application/json","-d",p],
                       capture_output=True, text=True, timeout=15)
    return json.loads(r.stdout)
for macro, value in [("{\$SNMP_AUTHPASS}", "0yJVUM5XcZer7hkLs9zl"), ("{\$SNMP_PRIVPASS}", "vL4YqRODaGUAIQ54rmoJ")]:
    existing = zbx("usermacro.get", {"globalmacro":True,"output":"extend","filter":{"macro":macro}})
    if existing.get("result"):
        zbx("usermacro.updateglobal", {"globalmacroid":existing["result"][0]["globalmacroid"],"value":value})
    else:
        zbx("usermacro.createglobal", {"macro":macro,"value":value})
    print(f"  {macro} = ***")
PYTHON
echo "✓ Global SNMP macros set"

# ── 11. Update NetBox ZabbixServer ───────────────────────
echo "Updating NetBox ZabbixServer..."
sudo PYTHONPATH=/opt/netbox/netbox NETBOX_CONFIGURATION=netbox.configuration \
    DJANGO_SETTINGS_MODULE=netbox.settings bash -c '
    set -a; source /etc/netbox.env; set +a
    cd /opt/netbox/netbox && /opt/netbox/venv/bin/python -c "
import django; django.setup()
from nbxsync.models import ZabbixServer, ZabbixHostBinding
s = ZabbixServer.objects.first()
s.token = \"'"$API_TOKEN"'\"
s.url = \"http://10.0.105.144:8080\"
s.save()
ZabbixHostBinding.objects.all().delete()
print(\"  ✓ NetBox updated\")
"' 2>&1 | tail -1

# ── 12. Optional: configure + sync ───────────────────────
if ! $NO_SYNC; then
    echo ""
    echo "Running zerotouch configure..."
    sudo env NBX_ZABBIX_TOKEN=$(cat /tmp/nbxsync_token.txt) \
        NBX_SNMP_AUTHPASS="$NBX_SNMP_AUTHPASS_MON" \
        NBX_SNMP_PRIVPASS="$NBX_SNMP_PRIVPASS_MON" \
        NBX_SNMP_AUTHPASS_MON="$NBX_SNMP_AUTHPASS_MON" \
        NBX_SNMP_PRIVPASS_MON="$NBX_SNMP_PRIVPASS_MON" \
        NBX_SNMP_AUTHPASS_LINUX="$NBX_SNMP_AUTHPASS_LINUX" \
        NBX_SNMP_PRIVPASS_LINUX="$NBX_SNMP_PRIVPASS_LINUX" \
        NBX_SNMP_AUTHPASS_DELL="$NBX_SNMP_AUTHPASS_DELL" \
        NBX_SNMP_PRIVPASS_DELL="$NBX_SNMP_PRIVPASS_DELL" \
        NBX_SNMP_AUTHPASS_SAP="$NBX_SNMP_AUTHPASS_SAP" \
        NBX_SNMP_PRIVPASS_SAP="$NBX_SNMP_PRIVPASS_SAP" \
        PYTHONPATH=/opt/netbox/netbox NETBOX_CONFIGURATION=netbox.configuration \
        bash -c 'set -a; source /etc/netbox.env; set +a; cd /opt/netbox/netbox && \
        /opt/netbox/venv/bin/python /tmp/configure_nbxsync_zerotouch.py' 2>&1 | tail -3

    echo "Running network configure..."
    sudo env NBX_ZABBIX_TOKEN=$(cat /tmp/nbxsync_token.txt) \
        NBX_ZABBIX_URL=http://10.0.105.144:8080 \
        PYTHONPATH=/opt/netbox/netbox:/tmp/nwn/scripts \
        NETBOX_CONFIGURATION=netbox.configuration \
        bash -c 'set -a; source /etc/netbox.env; set +a; cd /opt/netbox/netbox && \
        /opt/netbox/venv/bin/python /tmp/nwn/scripts/configure_nbxsync_network.py --apply' 2>&1 | tail -3

    # Patch EXOS LLD delays + temp macros
    echo "Patching EXOS template..."
    python3 <<'PYTHON'
import json, subprocess
API_TOKEN = open("/tmp/nbxsync_token.txt").read().strip()
URL = "http://localhost:8080/api_jsonrpc.php"
def zbx(method, params):
    p = json.dumps({"jsonrpc":"2.0","method":method,"params":params,"auth":API_TOKEN,"id":1})
    r = subprocess.run(["curl","-s",URL,"-H","Content-Type: application/json","-d",p],
                       capture_output=True, text=True, timeout=15)
    return json.loads(r.stdout).get("result", [])
for r in zbx("discoveryrule.get", {"output":["itemid","name","delay"],"templateids":["10224"]}):
    if r.get("delay") == "1h":
        zbx("discoveryrule.update", {"itemid": r["itemid"], "delay": "15m"})
        print(f"  LLD {r['name']} -> 15m")
zbx("template.update", {"templateid":"10224","macros":[
    {"macro":"{$TEMP_WARN}","value":"90"},
    {"macro":"{$TEMP_CRIT}","value":"100"},
    {"macro":"{$TEMP_CRIT_LOW}","value":"-273"}
]})
print("  EXOS temp: WARN=90 CRIT=100")
PYTHON

    echo "Syncing test devices..."
    sudo PYTHONPATH=/opt/netbox/netbox NETBOX_CONFIGURATION=netbox.configuration \
        DJANGO_SETTINGS_MODULE=netbox.settings bash -c '
        set -a; source /etc/netbox.env; set +a
        cd /opt/netbox/netbox && /opt/netbox/venv/bin/python /tmp/test_network_sync.py' 2>&1 | tail -5

    # Switch to server-monitored
    echo "Switching to server-monitored..."
    python3 <<'PYTHON'
import json, subprocess
API_TOKEN = open("/tmp/nbxsync_token.txt").read().strip()
URL = "http://localhost:8080/api_jsonrpc.php"
def zbx(method, params):
    p = json.dumps({"jsonrpc":"2.0","method":method,"params":params,"auth":API_TOKEN,"id":1})
    r = subprocess.run(["curl","-s",URL,"-H","Content-Type: application/json","-d",p],
                       capture_output=True, text=True, timeout=15)
    return json.loads(r.stdout).get("result", [])
for h in zbx("host.get", {"output":["hostid","host"]}):
    if h["host"] != "Zabbix server":
        zbx("host.update", {"hostid": h["hostid"], "monitored_by": 0, "proxy_groupid": 0})
        print(f"  {h['host']} -> server-monitored")
PYTHON
fi

# ── 13. Summary ──────────────────────────────────────────
echo ""
echo "╔═══════════════════════════════════════════════════════╗"
echo "║  Zabbix ready!                                        ║"
echo "║                                                       ║"
echo "║  Web:  http://localhost:8080                          ║"
echo "║  Login: Admin / zabbix                                ║"
echo "║  Token: $(head -c 16 /tmp/nbxsync_token.txt)...                   ║"
echo "║                                                       ║"
echo "║  Manage:                                              ║"
echo "║    sudo podman logs -f zbx-server                     ║"
echo "║    sudo podman restart zbx-server                     ║"
echo "║    sudo podman stop zbx-server zbx-web zbx-db         ║"
echo "║    sudo podman volume rm zbx-pgdata  # wipe data      ║"
echo "╚═══════════════════════════════════════════════════════╝"
