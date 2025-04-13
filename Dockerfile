FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# ------------------------------------------
# Base packages and utilities
# ------------------------------------------
RUN apt-get update && apt-get install -y \
    iproute2 \
    iputils-ping \
    net-tools \
    curl \
    python3 python3-pip \
    wget unzip \
    software-properties-common \
    git \
    && apt-get clean

# ------------------------------------------
# Install Prometheus
# ------------------------------------------
RUN apt-get update && apt-get install -y prometheus && apt-get clean

# ------------------------------------------
# Install Grafana
# ------------------------------------------
RUN wget -q -O - https://packages.grafana.com/gpg.key | apt-key add - && \
    add-apt-repository "deb https://packages.grafana.com/oss/deb stable main" && \
    apt-get update && \
    apt-get install -y grafana && \
    apt-get clean

# ------------------------------------------
# Install Python dependencies
# ------------------------------------------
RUN pip3 install flask pyyaml jinja2 napalm

# ------------------------------------------
# Create directory structure
# ------------------------------------------
RUN mkdir -p /opt/netdevops/templates /opt/netdevops/uploads /opt/napalm_exporter

# ------------------------------------------
# Copy scripts and templates
# ------------------------------------------
COPY startup.sh /startup.sh
COPY api.py /opt/netdevops/api.py
COPY generate_monitoring.py /opt/netdevops/generate_monitoring.py
COPY templates/prometheus.yml.j2 /opt/netdevops/templates/prometheus.yml.j2

# ------------------------------------------
# Copy Grafana provisioning
# ------------------------------------------
COPY grafana/provisioning/datasources/prometheus.yml /usr/share/grafana/conf/provisioning/datasources/prometheus.yml
COPY grafana/provisioning/dashboards/default.yaml /usr/share/grafana/conf/provisioning/dashboards/default.yaml
COPY grafana/provisioning/dashboards/napalm-dashboard.json /usr/share/grafana/conf/provisioning/dashboards/napalm-dashboard.json
COPY templates/config.yaml.j2 /opt/netdevops/templates/config.yaml.j2
# ------------------------------------------
# Set permissions
# ------------------------------------------
RUN chmod +x /startup.sh

# ------------------------------------------
# Expose ports
# ------------------------------------------
EXPOSE 9090 3000 5000 9273

# ------------------------------------------
# Start everything
# ------------------------------------------
CMD ["/startup.sh"]
