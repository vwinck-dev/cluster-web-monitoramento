#!/bin/sh
set -eu
install -d -m 0755 /etc/apt/keyrings /etc/grafana/provisioning/datasources /etc/grafana/provisioning/dashboards /var/lib/grafana/dashboards /etc/systemd/system/grafana-server.service.d
wget -qO /etc/apt/keyrings/grafana.asc https://apt.grafana.com/gpg-full.key
chmod 0644 /etc/apt/keyrings/grafana.asc
echo 'deb [signed-by=/etc/apt/keyrings/grafana.asc] https://apt.grafana.com stable main' > /etc/apt/sources.list.d/grafana.list
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y grafana
cp /opt/cluster-web-monitoramento/prometheus.yml /etc/prometheus/prometheus.yml
cp /opt/cluster-web-monitoramento/grafana-datasource.yml /etc/grafana/provisioning/datasources/cluster.yml
cp /opt/cluster-web-monitoramento/grafana-dashboard-provider.yml /etc/grafana/provisioning/dashboards/cluster.yml
cp /opt/cluster-web-monitoramento/dashboard.json /var/lib/grafana/dashboards/cluster.json
cp /opt/cluster-web-monitoramento/grafana.env /etc/grafana/cluster.env
chmod 0600 /etc/grafana/cluster.env
printf '[Service]\nEnvironmentFile=/etc/grafana/cluster.env\n' > /etc/systemd/system/grafana-server.service.d/cluster.conf
systemctl daemon-reload
systemctl enable --now prometheus grafana-server
systemctl restart prometheus
