#!/usr/bin/bash

# Copy fanctrl.py to /usr/local/bin and creates a service to run it
# Adapted from https://gist.github.com/ahmedsadman/2c1f118a02190c868b33c9c71835d706

if [ "$EUID" -ne 0 ]
  then echo "Please run as root"
  exit
fi

SERVICE_NAME="fw-fanctrl"

if [ "$1" = "remove" ]; then

    sudo systemctl stop ${SERVICE_NAME//'.service'/} # remove the extension
    sudo systemctl disable ${SERVICE_NAME//'.service'/}
    rm /usr/local/bin/fanctrl.py
    ectool --interface=lpc autofanctrl # restore default fan manager
    rm /usr/local/bin/ectool
    rm -rf /home/$(logname)/.config/fw-fanctrl

    echo "fw-fanctrl has been removed successfully from system"
else

    cp ./bin/ectool /usr/local/bin
    cp ./fanctrl.py /usr/local/bin
    mkdir -p /home/$(logname)/.config/fw-fanctrl
    cp config.json /home/$(logname)/.config/fw-fanctrl/

    # check if service is active
    IS_ACTIVE=$(sudo systemctl is-active  $SERVICE_NAME)
    if [ "$IS_ACTIVE" == "active" ]; then
        # restart the service
        echo "Service is running"
        echo "Restarting service"
        sudo systemctl restart $SERVICE_NAME
        echo "Service restarted"
    else
        # create service file
        echo "Creating service file"
        sudo cat > /etc/systemd/system/${SERVICE_NAME//'"'/}.service << EOF
[Unit]
Description=FrameWork Fan Controller
After=multi-user.target
[Service]
Type=simple
Restart=always
ExecStart=/usr/bin/python3 /usr/local/bin/fanctrl.py --config /home/$(logname)/.config/fw-fanctrl/config.json --no-log
[Install]
WantedBy=multi-user.target

EOF
        # restart daemon, enable and start service
        echo "Reloading daemon and enabling service"
        sudo systemctl daemon-reload
        sudo systemctl enable ${SERVICE_NAME//'.service'/} # remove the extension
        sudo systemctl start ${SERVICE_NAME//'.service'/}
        echo "Service Started"
    fi

fi
exit 0