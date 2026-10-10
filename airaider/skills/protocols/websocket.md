---
name: websocket
description: WebSocket security testing — Cross-Site WebSocket Hijacking (CSWSH), origin/auth validation, message-level authorization and injection, and tunneled protocol abuse
---

# WebSocket

Security testing for WebSocket (`ws://` / `wss://`) endpoints. The classic, high-impact
bug is **Cross-Site WebSocket Hijacking (CSWSH)** — the handshake is a normal HTTP request
subject to CSRF, and many servers authenticate with cookies but never check `Origin` or a
CSRF token. After the handshake, treat each message like its own request.

## Attack Surface

- **Handshake**: `GET` upgrade with `Origin`, `Cookie`, `Sec-WebSocket-Key/Protocol`.
- **Authentication**: cookie/session vs token-in-message; origin validation; CSRF token.
- **Messages**: JSON/binary frames — each one an action that needs authorization + input validation.
- **Subprotocols**: `Sec-WebSocket-Protocol` (e.g. graphql-ws, STOMP, MQTT-over-WS, SignalR).
- **Infra**: proxies/load balancers, compression (`permessage-deflate`), smuggling via upgrade.

## Reconnaissance

```bash
# Inspect the handshake; note whether Origin is validated and what auth is used
curl -s -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" \
  -H "Sec-WebSocket-Version: 13" -H "Sec-WebSocket-Key: $(openssl rand -base64 16)" \
  -H "Origin: https://evil.example" "$TARGET"     # does a foreign Origin still upgrade?

# Interactive testing
# websocat 'wss://target/ws'      # send/receive frames manually
# In Burp: use the WebSocket history + repeater to replay/modify frames.
```

- Capture a legitimate session's handshake and messages from the app, then replay/modify.
- Check whether auth rides on cookies alone (CSWSH-prone) or a per-connection token.

## Key Vulnerabilities

### Cross-Site WebSocket Hijacking (CSWSH)
The handshake is cross-site-forgeable. If the server authenticates with cookies and does
**not** validate `Origin` (or require a CSRF token), a malicious page opens a socket as the
victim and reads/sends data.
- Test: connect with a foreign/absent `Origin` using the victim's cookies → success = CSWSH.
- PoC: an HTML page that opens the socket and exfiltrates messages to the attacker.

### Missing / broken message-level authorization
- One interceptor authorizes the handshake, but individual messages aren't checked.
- Swap resource IDs / channel names in frames → IDOR/BOLA (other users' data/streams).
- Subscribe to channels/topics you shouldn't (STOMP/SignalR/graphql-ws subscriptions).

### Input injection via frames
- Message fields reach SQL/NoSQL/command/template sinks without validation (no WAF on WS).
- Reflected/stored XSS when message content is rendered to other clients.

### Origin / auth design flaws
- Token in the URL query (`wss://host/ws?token=...`) → logged, leaked via Referer/history.
- Weak/again-usable handshake tokens; no per-connection expiry.

### Tunneled subprotocols
- graphql-ws → run the GraphQL pack over the socket (subscriptions, auth).
- STOMP/MQTT/SignalR → topic authorization, wildcard subscriptions, command injection.

### DoS
- No message-size/rate limits; decompression amplification via `permessage-deflate`.

## Testing Methodology

1. Capture a real handshake + message flow; identify the auth mechanism and subprotocol.
2. Test CSWSH: upgrade with foreign/absent `Origin` + victim cookies; confirm data access.
3. Replay each message type with low-priv / no auth; swap IDs and channel names (IDOR/BOLA).
4. Fuzz message fields into injection sinks; check rendering to other clients (XSS).
5. For tunneled subprotocols, apply that protocol's pack (e.g. graphql).
6. Probe size/rate limits and compression (bounded, non-abusive).

## Validation Requirements

- CSWSH: provide a working cross-origin PoC page (or the raw cross-origin handshake) that
  reads/sends the victim's data, and show the same blocked with a correct origin check.
- Message authz: show a frame succeeding without the required privilege (data/action for
  another user).
- Injection/XSS: show the payload reaching the sink or rendering to another client.
- Capture reproductions as concrete frames (websocat/Burp) so they re-run.
