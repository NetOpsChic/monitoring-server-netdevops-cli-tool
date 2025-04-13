
# 🛰️ NetDevOps Observe-Tower

The **Observer Tower** is a lightweight monitoring stack for GNS3-based NetDevOps labs. Tested on Arista EOS

It uses:
- **NAPALM** to fetch real-time router metrics over SSH
- **Prometheus** to scrape the metrics
- **Grafana** to visualize everything in one dashboard

## Usage

Build the docker and run it on GNS3

## 📥 Input

- A standard `inventory.yaml` (Ansible inventory format)
- Devices must support SSH access (no SNMP or eAPI required)

Example `inventory.yaml`:

```yaml
all:
  hosts:
    R1:
      ansible_host: 192.168.100.x
      ansible_user: admin
      ansible_password: admin
      ansible_network_os: eos
    R2:
      ansible_host: 192.168.100.x
      ansible_user: admin
      ansible_password: admin
      ansible_network_os: eos
```

## 🚀 How It Works

1. Upload `inventory.yaml` to the Observer Tower API:
   ```bash
   curl -F 'file=@inventory.yaml' http://<observer-ip>:5000/upload
   ```

2. Prometheus scrapes `/metrics`:
   ```
   http://<observer-ip>:5000/metrics
   ```

3. Grafana shows dashboards:
   ```
   http://<observer-ip>:3000
   ```

---

## 📊 Metrics Collected

- Interface status, speed, and enabled state
- Device model + OS version
- OSPF neighbors (if supported)
- BGP peers (if supported)
- Route count

---

## 🔧 Deployment

```bash
docker build -t observer-tower .
docker run -d --net=host --name observer observer-tower
```

Make sure:
- Router SSH is enabled
- Port 5000 (API), 9090 (Prometheus), and 3000 (Grafana) are reachable

---

## 📈 Grafana Dashboard

- Use the included `dashboard.json` to import into Grafana
- All metrics auto-refresh from Prometheus

---

## 🧪 Test It

```bash
curl http://<observer-ip>:5000/metrics
Navigate to Grafana Dashboard http://<observer-ip>:3000
```
---

## 🧠 Minimal, Powerful, Open

Just bring:
- 🧾 An inventory file
- 🔐 SSH access

Let Observer Tower handle the rest.