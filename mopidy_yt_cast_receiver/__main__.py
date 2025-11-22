"""Entry-point script to run the DIAL cast receiver."""

from __future__ import annotations

import argparse
import logging
import time

from .dial import DialService

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="YouTube Music DIAL receiver for Mopidy")
    parser.add_argument("--host", default="0.0.0.0", help="HTTP bind address")
    parser.add_argument("--port", type=int, default=8009, help="HTTP port for DIAL endpoints")
    parser.add_argument("--ssdp-port", type=int, default=1900, help="UDP port used for SSDP responses")
    parser.add_argument(
        "--friendly-name",
        default="Mopidy YouTube Music",
        help="Name that appears in YouTube's cast target list",
    )
    parser.add_argument(
        "--rpc-url",
        default="http://127.0.0.1:6680/mopidy/rpc",
        help="Mopidy HTTP JSON-RPC endpoint",
    )

    args = parser.parse_args()
    service = DialService(
        host=args.host,
        port=args.port,
        friendly_name=args.friendly_name,
        mopidy_rpc_url=args.rpc_url,
        ssdp_port=args.ssdp_port,
    )
    service.start()
    LOGGER.info("DIAL service available at %s", service.application_url)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        LOGGER.info("Stopping receiver...")
    finally:
        service.stop()


if __name__ == "__main__":
    main()
