# Standard lib imports
import json
import logging
import os
from enum import Enum
from typing import Union

from flask import Flask, Response, request  # type: ignore
from flask_cors import CORS  # type: ignore


class UpdateStatus(str, Enum):
    idle = "idle"
    updating = "updating"


update_status = UpdateStatus.idle


def create_app() -> Flask:
    """Create the app

    Returns:
        Flask: The server
    """
    logger = logging.getLogger(__name__)
    logger.info("Create the app")

    app = Flask(__name__)
    # enable CORS
    CORS(app)  # Enable CORS for all routes

    # Set static data
    @app.context_processor
    def set_static_data() -> dict:
        os_version = os.popen(  # nosec
            "cat /etc/os-release | grep PRETTY_NAME | awk -F'\"' '{print $2}'"  # nosec
        ).read()  # nosec

        return {
            "os_version": os_version,
        }

    @app.route("/status", methods=["POST", "GET"])
    def status() -> dict:
        """Main page for configuration wizard

        Returns:
            str: The homepage page to select different actions
        """
        return {"status": update_status}

    @app.route("/version", methods=["GET"])
    def version() -> dict:
        """Main page for configuration wizard

        Returns:
            str: The homepage page to select different actions
        """
        # os_version = "Mapio OS distribution 1.1 (kirkstone)"
        os_version = os.popen(  # nosec
            "cat /etc/os-release | grep PRETTY_NAME | awk -F'\"' '{print $2}'"  # nosec
        ).read()  # nosec

        return {
            "os_version": os_version,
        }

    @app.route("/wifi", methods=["POST", "GET"])
    def wifi() -> Response:
        """Wifi setup page

        Returns:
            str: The setup wifi page
        """
        if request.method == "POST":
            logger.info("Setup WIFI network")
            data = request.get_json()
            selected_wifi = data.get("selectedWifi")
            set_password = data.get("password")
            ssid = f'  ssid="{selected_wifi}"\n'
            password = f'  psk="{set_password}"\n'
            logger.info(f"ssid {ssid}")
            logger.info(f"password {password}")

            if password != "":  # nosec
                # Replace existing file
                file = open(  # nosec
                    "/etc/wpa_supplicant/wpa_supplicant-wlan0.conf", "w"  # nosec
                )
                file.writelines(
                    [
                        "ctrl_interface=/var/run/wpa_supplicant\n",
                        "ctrl_interface_group=0\n" "update_config=1\n",
                        "\n",
                        "network={\n",
                        ssid,
                        password,
                        "  key_mgmt=WPA-PSK\n",
                        "  proto=WPA2\n",
                        "  pairwise=CCMP TKIP\n",
                        "  group=CCMP TKIP\n",
                        "  scan_ssid=1\n",
                        "}\n",
                    ]
                )

                # Start wlan0 service
                os.popen("systemctl daemon-reload").read()  # nosec
                os.popen(  # nosec
                    "systemctl stop wpa_supplicant-ap.service"  # nosec
                ).read()  # nosec
                os.popen(  # nosec
                    "systemctl restart wpa_supplicant@wlan0.service"  # nosec
                ).read()  # nosec
                os.popen(  # nosec
                    "systemctl enable wpa_supplicant@wlan0.service"  # nosec
                ).read()  # nosec

        return Response(response="wifi", status=200)

    @app.route("/getScan")
    def getScan() -> str:
        """Wifi setup page

        Returns:
            str: The setup wifi page
        """
        # scan with
        logger.info("getScan")
        output = os.popen(  # nosec
            "iw wlan0 scan | grep SSID: | awk '{print $2}' | sed '/^$/d'"  # nosec
        ).read()  # nosec
        ssids: list = []
        for line in output.splitlines():
            line = line.rstrip("\n")
            parsed_line = line.split(";")
            ssid: dict = dict()
            ssid["name"] = parsed_line[0]
            ssids.append(ssid)

        logger.info(f"SSIDs : {ssids}")
        return json.dumps(ssids)

    @app.route("/docker", methods=["POST", "GET"])
    def docker() -> Union[str, Response]:
        """Docker setup page

        Returns:
            str: The setup docker page
        """
        if request.method == "POST":
            data = request.form.to_dict(flat=False)
            extract_data = json.loads(data.popitem()[0]) if data else None

            logger.info(f"data extract is {extract_data}")
            # Get asked action
            action = None
            for item in iter(extract_data):
                if item.get("action") is not None:
                    action = item.get("action")
                    logger.info(f"Asked action is : {action}")

            # Exectute the action if needed
            for item in iter(extract_data):
                service = item.get("service")
                if service is not None:
                    if item.get("selected"):
                        if action == "restart":
                            os.popen(  # nosec
                                f"docker-compose -f /home/root/{service.lower()}/docker-compose.yml\
 restart"
                            ).read()  # nosec
                        elif action == "stop":
                            os.popen(  # nosec
                                f"docker-compose -f /home/root/{service.lower()}/docker-compose.yml\
 stop"
                            ).read()  # nosec
                        elif action == "update":
                            os.popen(  # nosec
                                f"docker-compose -f /home/root/{service.lower()}/docker-compose.yml\
 pull && docker-compose -f /home/root/{service.lower()}/docker-compose.yml up -d --force-recreate"
                            ).read()  # nosec
                        else:
                            logger.error("Unknown action")
            return Response(response="docker", status=200)

        elif request.method == "GET":
            logger.info("getScan")
            output = os.popen("docker ps --format '{{.Names}}'").read()  # nosec
            containers: list = []
            for line in output.splitlines():
                line = line.rstrip("\n")
                container: dict = dict()
                container["name"] = line
                containers.append(container)
            logger.info(f"Containers : {containers}")
            return json.dumps(containers)

        else:
            return Response(response="docker", status=404)

    @app.route("/update", methods=["POST", "GET"])
    def update() -> Response:
        """Update endpoint

        Returns:
            Response: 200 if success, 404 otherwise
        """
        if request.method == "POST":
            logger.info(f"{request.files}")
            f = request.files["bundle"]
            global update_status
            update_status = UpdateStatus.updating
            if f != "":
                f.save("/tmp/bundle.raucb")  # nosec
                os.popen("rauc install /tmp/bundle.raucb").read()  # nosec
                os.popen("rm /boot/first_boot_done").read()  # nosec
                os.popen("reboot").read()  # nosec

        return Response(response="update", status=200)

    @app.route("/ssh-setkey", methods=["POST", "GET"])
    def ssh_setkey() -> Response:
        """SSH add key endpoint

        Returns:
            Response: 200 if success, 404 otherwise
        """
        if request.method == "POST":
            logger.info(f"{request.values}")
            key = request.values.get("userkey")
            if key != "":
                logger.info(f"Key is {key}")
                os.popen("mkdir -p ~/.ssh").read()  # nosec
                os.popen(f"echo {key} >> ~/.ssh/authorized_keys").read()  # nosec
                os.popen("chmod 600 ~/.ssh/authorized_keys").read()  # nosec

                return Response(response="ssh-setkey", status=200)

        return Response(response="ssh-setkey", status=404)

    return app
