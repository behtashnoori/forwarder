#!/usr/bin/env bash
# Open ports 8080 (frontend) and 5001 (backend) for external access on Linux (ufw)
# Run: sudo ./scripts/open-firewall-ports.sh   or: sudo bash scripts/open-firewall-ports.sh

set -e
PORTS="8080/tcp 5001/tcp"

if ! command -v ufw &>/dev/null; then
  echo "ufw not found. Install with: sudo apt install ufw   (Debian/Ubuntu)"
  exit 1
fi

echo "Opening firewall ports for Forwarder (8080 frontend, 5001 backend)..."
for spec in $PORTS; do
  sudo ufw allow "$spec" 2>/dev/null || true
done
sudo ufw status | grep -E "8080|5001" || true
echo "Done. From outside use: http://YOUR_SERVER_IP:8080 and http://YOUR_SERVER_IP:5001"
