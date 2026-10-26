"""Auto-loaded sandbox shim: experiments have no network access by default.

Installed into the isolated experiment workspace by the autonomous agent.
Set AUTONOMOUS_ALLOW_NETWORK=1 only for explicitly reviewed commands.
"""
import os
import socket

if os.environ.get("AUTONOMOUS_ALLOW_NETWORK", "0") != "1":
    _real_connect = socket.socket.connect
    _real_connect_ex = socket.socket.connect_ex
    _real_create = socket.create_connection

    def _deny(*args, **kwargs):
        raise PermissionError(
            "Network access is disabled for autonomous experiments "
            "(autonomous_agent.hardening). This command must not reach "
            "brokerage, credential, or external services.")

    socket.socket.connect = _deny
    socket.socket.connect_ex = _deny
    socket.create_connection = _deny
    socket.getaddrinfo = _deny
