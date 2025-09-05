import socket

def get_machine_hostname() -> str:
    """
    Retrieves the hostname of the current machine.
    """
    return socket.gethostname()