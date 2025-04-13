import os
import yaml
from jinja2 import Template

INVENTORY_PATH = "/opt/netdevops/uploads/inventory.yaml"
NAPALM_CONFIG_OUTPUT = "/opt/netdevops/config.yaml"
NAPALM_TEMPLATE_PATH = "/opt/netdevops/templates/config.yaml.j2"
PROMETHEUS_TEMPLATE_PATH = "/opt/netdevops/templates/prometheus.yml.j2"
PROMETHEUS_OUTPUT_PATH = "/etc/prometheus/prometheus.yml"  # this should be writable inside the container
OBSERVER_IP = os.getenv("OBSERVER_TOWER_IP", "192.168.100.24")  # default fallback

def load_inventory():
    with open(INVENTORY_PATH) as f:
        data = yaml.safe_load(f)
    hosts = data.get("all", {}).get("hosts", {})
    return [
        {
            "hostname": v["ansible_host"],
            "driver": v["ansible_network_os"],
            "username": v["ansible_user"],
            "password": v["ansible_password"]
        }
        for v in hosts.values()
    ]

def load_router_ips():
    with open(INVENTORY_PATH) as f:
        data = yaml.safe_load(f)
    hosts = data.get("all", {}).get("hosts", {})
    return [v["ansible_host"] for v in hosts.values()]

def render_napalm_config(targets):
    with open(NAPALM_TEMPLATE_PATH) as f:
        template = Template(f.read())
    rendered = template.render(targets=targets)
    with open(NAPALM_CONFIG_OUTPUT, "w") as f:
        f.write(rendered)

def render_prometheus_config():
    with open(PROMETHEUS_TEMPLATE_PATH) as f:
        template = Template(f.read())
    rendered = template.render(observer_ip=OBSERVER_IP)
    with open(PROMETHEUS_OUTPUT_PATH, "w") as f:
        f.write(rendered)

if __name__ == "__main__":
    targets = load_inventory()
    router_ips = load_router_ips()

    print("📄 Loaded targets:", targets)
    print("🌐 Router IPs:", router_ips)

    print("🛠️ Rendering NAPALM Exporter config...")
    render_napalm_config(targets)
    print("✅ NAPALM Exporter config generated.")

    print("🛠️ Rendering Prometheus scrape config...")
    render_prometheus_config()
    print(f"✅ Prometheus config written to {PROMETHEUS_OUTPUT_PATH}")
