# Mopidy YouTube Cast Receiver

A lightweight Python implementation of a YouTube Music cast receiver for Mopidy
using the DIAL protocol. The service exposes a DIAL HTTP endpoint and SSDP
discovery so that the YouTube app on a phone can find and launch playback on a
Mopidy server.

## Features

- SSDP responder for DIAL discovery
- HTTP DIAL endpoints compatible with the YouTube app namespace
- Launch handling that forwards YouTube identifiers to Mopidy via JSON-RPC
- Configurable host/port settings for both HTTP and SSDP services

## Getting started

1. Install dependencies (for development):

   ```bash
   pip install -e .[development]
   ```

2. Run the service pointing at your Mopidy HTTP JSON-RPC endpoint:

   ```bash
   python -m mopidy_yt_cast_receiver --rpc-url http://127.0.0.1:6680/mopidy/rpc
   ```

   Make sure Mopidy's built-in HTTP extension is enabled (it is by default) so
   that the `/mopidy/rpc` endpoint is reachable. You can confirm with a quick
   curl request while Mopidy is running:

   ```bash
   curl http://127.0.0.1:6680/mopidy/rpc -d '{"jsonrpc":"2.0","id":1,"method":"core.playback.get_state"}' -H "Content-Type: application/json"
   ```

   A JSON response indicates Mopidy is exposing JSON-RPC correctly. If the
   request fails, ensure `http/enabled = true` in your Mopidy configuration and
   restart Mopidy.

   By default the DIAL HTTP server binds to `0.0.0.0:8009` and the SSDP service
   listens on port `1900`. Both values can be overridden with command-line
   options.

   Visiting the root page (e.g. `http://localhost:8009/`) returns a brief text
   response listing the important DIAL endpoints if you want to verify the
   service is responding without a DIAL client.

3. Open the YouTube Music app on your phone and look for the cast target named
   after the Mopidy instance (defaults to **Mopidy YouTube Music**).

## Development

Run the test suite with pytest:

```bash
pytest
```

The project is intentionally small and avoids third-party runtime dependencies.
The core logic lives in `mopidy_yt_cast_receiver/`:

- `dial.py`: HTTP DIAL endpoints and wiring
- `ssdp.py`: SSDP responder used for discovery
- `youtube.py`: YouTube-specific DIAL application state
- `mopidy.py`: JSON-RPC client that translates launch parameters into Mopidy
  playback commands
