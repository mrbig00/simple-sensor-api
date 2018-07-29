# simple-sensor-api
Simple, ugly and spaghetti Raspberry PI sensor API reader

# systemd config file

Place this file into /etc/systemd/system/my_daemon.service and enable it using systemctl daemon-reload && systemctl enable my_daemon && systemctl start my_daemon --no-block.

To view logs:

systemctl status my_daemon

```
[Unit]
Description=Sensor API Service

[Service]
Type=simple
ExecStart=/usr/bin/python /home/pi/WebProjects/sensor-api/app.py
WorkingDirectory=/home/pi/WebProjects/sensor-api
Restart=always
RestartSec=2

[Install]
WantedBy=sysinit.target

```
