from flask import Flask, request, jsonify, Response
import yaml
import os
import argparse
from napalm import get_network_driver

app = Flask(__name__)

UPLOAD_DIR = "/opt/netdevops/uploads"
TARGETS_FILE = "/opt/netdevops/targets.json"
INVENTORY_PATH = os.path.join(UPLOAD_DIR, "inventory.yaml")

os.makedirs(UPLOAD_DIR, exist_ok=True)

# POST /upload (upload YAML inventory)
@app.route('/upload', methods=['POST'])
def upload_inventory_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']
    path = INVENTORY_PATH
    file.save(path)

    with open(path) as f:
        try:
            data = yaml.safe_load(f)
        except Exception as e:
            return jsonify({"error": f"Failed to parse YAML: {str(e)}"}), 400

    # Parse IPs
    hosts = data.get("all", {}).get("hosts", {})
    targets = [v.get("ansible_host") for v in hosts.values() if "ansible_host" in v]

    # Save targets in Prometheus file_sd format
    with open(TARGETS_FILE, "w") as out:
        yaml.dump([{"targets": targets, "labels": {"job": "gns3"}}], out)

    return jsonify({"status": "ok", "targets": targets})


# GET /targets (for Prometheus file_sd or http_sd)
@app.route('/targets', methods=['GET'])
def get_targets():
    if os.path.exists(TARGETS_FILE):
        with open(TARGETS_FILE) as f:
            return f.read(), 200, {'Content-Type': 'application/x-yaml'}
    else:
        return jsonify([])


# Health check
@app.route('/')
def index():
    return "NetDevOps Observer API is running"


# GET /metrics for Prometheus
@app.route('/metrics', methods=['GET'])
def get_metrics():
    try:
        if not os.path.exists(INVENTORY_PATH):
            return Response("# No inventory file found\n", mimetype='text/plain')

        with open(INVENTORY_PATH) as f:
            inventory = yaml.safe_load(f)

        hosts = inventory.get("all", {}).get("hosts", {})
        metrics_output = []

        for name, props in hosts.items():
            ip = props.get("ansible_host")
            username = props.get("ansible_user", "admin")
            password = props.get("ansible_password", "admin")
            os_type = props.get("ansible_network_os", "eos")

            try:
                print(f"🔌 Connecting to {name} at {ip} with OS {os_type} via HTTP...")
                driver = get_network_driver(os_type)
                optional_args = {"protocol": "http", "port": 80, "transport": "http"}
                device = driver(hostname=ip, username=username, password=password, optional_args=optional_args)
                device.open()

                # ✅ Interface Metrics
                interfaces = device.get_interfaces()
                for intf, data in interfaces.items():
                    up = 1 if data.get("is_up") else 0
                    enabled = 1 if data.get("is_enabled") else 0
                    speed = data.get("speed", 0)
                    metrics_output.append(f'router_interface_status{{device="{name}", interface="{intf}"}} {up}')
                    metrics_output.append(f'router_interface_enabled{{device="{name}", interface="{intf}"}} {enabled}')
                    metrics_output.append(f'router_interface_speed{{device="{name}", interface="{intf}"}} {speed}')

                # ✅ Device Facts
                facts = device.get_facts()
                uptime = facts.get("uptime", 0)
                model = facts.get("model", "unknown")
                version = facts.get("os_version", "unknown")
                metrics_output.append(f'router_uptime_seconds{{device="{name}"}} {uptime}')
                metrics_output.append(f'router_info{{device="{name}", model="{model}", version="{version}"}} 1')

                # ✅ BGP Neighbors
                try:
                    bgp = device.get_bgp_neighbors()
                    for afi in bgp.values():
                        for peer, pdata in afi.get("peers", {}).items():
                            up = 1 if pdata.get("is_up") else 0
                            remote_as = pdata.get("remote_as", 0)
                            metrics_output.append(f'bgp_peer_up{{device="{name}", peer="{peer}"}} {up}')
                            metrics_output.append(f'bgp_peer_as{{device="{name}", peer="{peer}"}} {remote_as}')
                except Exception as e:
                    metrics_output.append(f'# WARNING: Failed to fetch BGP metrics for {name}: {e}')

                # ✅ OSPF Neighbors
                try:
                    if os_type == "eos":
                        ospf_output = device.cli(["show ip ospf neighbor"])
                        lines = ospf_output["show ip ospf neighbor"].splitlines()
                        neighbor_count = sum(1 for line in lines if "Full" in line or "2WAY" in line)
                        metrics_output.append(f'router_ospf_neighbors_total{{device="{name}"}} {neighbor_count}')
                    else:
                        ospf = device.get_ospf_neighbors()
                        total_ospf = sum(len(area.get("neighbors", {})) for area in ospf.values())
                        metrics_output.append(f'router_ospf_neighbors_total{{device="{name}"}} {total_ospf}')
                except Exception as e:
                    metrics_output.append(f'# WARNING: Failed to fetch OSPF metrics for {name}: {e}')
                    metrics_output.append(f'router_ospf_neighbors_total{{device="{name}"}} 0')

                # ✅ Route Count
                try:
                    routes = device.get_route_to()
                    metrics_output.append(f'router_routes_total{{device="{name}"}} {len(routes)}')
                except Exception as e:
                    metrics_output.append(f'# WARNING: Failed to fetch routes for {name}: {e}')
                    metrics_output.append(f'router_routes_total{{device="{name}"}} 0')

                device.close()

            except Exception as e:
                err_msg = f"# ERROR fetching metrics for {name}: {e}"
                print(f"❌ {err_msg}")
                metrics_output.append(err_msg)

        return Response("\n".join(metrics_output), mimetype='text/plain')

    except Exception as e:
        return Response(f"# 💥 Global error in /metrics: {e}\n", mimetype='text/plain')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=5000)
    args = parser.parse_args()
    app.run(host='0.0.0.0', port=args.port)
