import datetime

def get_current_timestamp() -> str:
    """
    Generates a timestamp string for the current date and time.
    """
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")