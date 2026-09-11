import time

from data_fetcher.modbus_fetcher import run_fetcher, stop_event, stop_fetcher


if __name__ == "__main__":
    run_fetcher()
    try:
        while not stop_event.is_set():
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        # Closes all gateway sockets with RST so the single-slot SELC converters
        # release their connection immediately instead of blocking the next run.
        stop_fetcher()
