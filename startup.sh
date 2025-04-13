#!/bin/bash

set -e

echo "🧠 Assigning static IP to eth0..."
ip addr flush dev eth0
ip addr add 192.168.100.24/24 dev eth0
ip link set eth0 up

echo "🚀 Starting NetDevOps API server on port 5000..."
python3 /opt/netdevops/api.py --port 5000 &
API_PID=$!

# Optional: wait for the API to come up fully
sleep 2

echo "⏳ Waiting for inventory.yaml to be uploaded..."
while [ ! -f /opt/netdevops/uploads/inventory.yaml ]; do
    sleep 1
done

export OBSERVER_TOWER_IP=192.168.100.24
echo "📄 inventory.yaml found! Generating monitoring targets..."
python3 /opt/netdevops/generate_monitoring.py

echo "📈 Starting Prometheus quietly..."
prometheus --config.file=/etc/prometheus/prometheus.yml --web.listen-address=":9090" > /dev/null 2>&1 &

echo "📊 Starting Grafana quietly..."
grafana-server --homepath=/usr/share/grafana --config=/etc/grafana/grafana.ini > /dev/null 2>&1 &

wait $API_PID
