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
   that the `/mopidy/rpc` endpoint is reachable. The quickest way is to add the
   following to your `mopidy.conf` (or verify it already exists) and then restart
   Mopidy:

   ```ini
   [http]
   enabled = true
   hostname = 0.0.0.0   ; or 127.0.0.1 if you only need local access
   port = 6680
   ```

   After Mopidy restarts, confirm JSON-RPC is available with a curl request while
   Mopidy is running:

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
   service is responding without a DIAL client. It also shows the **TV code**
   used for manual pairing (see step 3).

3. Open the YouTube Music app on your phone and look for the cast target named
   after the Mopidy instance (defaults to **Mopidy YouTube Music**). The cast
   target appears automatically when discovery works—there is no link or pairing
   code required for automatic discovery. A few tips if it does not show up:

   - The phone must be on the same layer-2 network (no guest/VLAN isolation) so
     it can send SSDP multicast probes (UDP/1900) to find the receiver.
   - Ensure the host running this service allows inbound UDP/1900 and
     TCP/8009 from the phone.
   - Discovery relies on the YouTube **Music** app’s DIAL support; the regular
     YouTube video app will not list this receiver.
   - You can manually confirm discovery by issuing an SSDP M-SEARCH from a
     machine on the same network:

     ```bash
     python - <<'PY'
     import socket
     message = '\r\n'.join([
         'M-SEARCH * HTTP/1.1',
         'HOST:239.255.255.250:1900',
         'MAN:"ssdp:discover"',
         'MX:1',
         'ST: urn:dial-multiscreen-org:service:dial:1',
         '',
         ''
     ])
     sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
     sock.settimeout(2)
     sock.sendto(message.encode(), ('239.255.255.250', 1900))
     try:
         data, _ = sock.recvfrom(2048)
         print(data.decode())
     except socket.timeout:
         print('No SSDP response received (check firewall or network isolation).')
     PY
     ```

     Seeing an HTTP/200 response that includes `yt-cast-receiver` confirms the
     SSDP broadcast is reachable.

   If automatic discovery is blocked on your network, you can pair manually
   using the TV code shown on the receiver's root page or via the API at
   `/pairing/code`:

   - In YouTube Music on your phone, open **Settings → Link with TV code** and
     enter the 12-digit code displayed by the receiver (formatted like
     `123-456-789-012`).
   - When you start the service, the code is also logged and you can supply your
     own static code with `--pairing-code`.
   - To force clients to present the correct code on every launch request, start
     the receiver with `--require-pairing-code`. This makes the DIAL POST to
     `/apps/YouTube` return HTTP 403 unless the `pairingCode=` parameter matches
     the configured TV code.

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
