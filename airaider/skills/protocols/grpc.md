---
name: grpc
description: gRPC and Protobuf API security testing covering reflection exposure, per-method authorization, metadata/JWT handling, gRPC-Web, transcoding, and message-level attacks
---

# gRPC

Security testing for gRPC / Protobuf APIs. Focus on per-method authorization, server
reflection exposure, metadata (auth) handling, transcoding/gRPC-Web gateways, and
message-level manipulation. Many gRPC services assume the client is trusted (generated
stubs) and skip the per-method checks a REST API would have — that gap is the core target.

## Attack Surface

**Call types**
- Unary, server-streaming, client-streaming, bidirectional streaming

**Transports / exposure**
- HTTP/2 native (`h2`, `h2c` cleartext), TLS / mTLS
- gRPC-Web (base64 or binary) behind Envoy/grpc-web proxy — reachable from browsers
- JSON transcoding (google.api.http, grpc-gateway, Envoy): REST → gRPC, re-exposing methods over HTTP/JSON
- Server reflection service (`grpc.reflection.v1alpha.ServerReflection`)
- Health (`grpc.health.v1.Health`), channelz, server metrics

**Message layer**
- Protobuf messages: scalar/message/`repeated`/`map`/`oneof`/`Any`
- Metadata (headers/trailers): `authorization`, custom `x-*`, binary `-bin` keys
- Status codes + `google.rpc.Status` error details (can leak internals)

## Reconnaissance

```bash
# List services/methods via reflection
grpcurl -plaintext target:50051 list
grpcurl -plaintext target:50051 describe package.Service
grpcurl -plaintext target:50051 describe package.Request   # message shape

# Call a method (reflection-based)
grpcurl -plaintext -d '{"id":"1"}' target:50051 package.Service/GetItem

# No reflection? supply the .proto or a FileDescriptorSet
grpcurl -import-path ./proto -proto api.proto -d '{...}' target:50051 package.Service/Method
grpcurl -protoset api.protoset -d '{...}' target:50051 package.Service/Method

# gRPC-Web / transcoding over HTTP (reachable with a normal HTTP client / Burp)
curl -s https://target/package.Service/Method -H 'content-type: application/grpc-web+proto' --data-binary @payload.bin
```

- Pull `.proto` from the repo, mobile app, JS bundle (gRPC-Web stubs), or `buf`/`protoset`.
- `grpcui` gives an interactive browser client over reflection.
- Check whether reflection/health/channelz are exposed in production (they often should not be).

## Key Vulnerabilities

### Missing / Per-Method Authorization
The dominant gRPC bug. Auth is often enforced by a single interceptor or only on the
"public" methods; internal/admin methods are reachable if you can name them.
- Enumerate every method (reflection or leaked `.proto`) and call each with a low-priv or no token.
- Admin/debug services (`*.Admin`, `*.Internal`, `Debug*`) frequently lack checks.
- Streaming methods may skip the interceptor applied to unary calls.
- Transcoding/gRPC-Web gateways may expose methods the native port firewalls off.

### Metadata & Token Handling
- Does the server trust client-supplied metadata (`x-user-id`, `x-role`, `x-tenant`) for authz? → spoof it.
- JWT in `authorization` metadata: test `alg=none`, weak secret, missing audience/expiry, cross-service token reuse.
- Trailer/initial-metadata injection; binary `-bin` metadata parsing.

### Resource Access (IDOR / BOLA)
- Message fields carry resource IDs — swap them to access other tenants/users.
- `repeated`/`map` fields let you request many objects in one call; check per-item authz.

### Reflection & Info Exposure
- Reflection enabled in prod reveals the full API (attack map).
- `google.rpc.Status` / error `details` leaking stack traces, SQL, internal hosts.
- channelz/health exposing topology.

### Denial of Service
- Decompression bombs (gzip) and oversized messages when `MaxRecvMsgSize` is unbounded.
- Deeply nested / recursive messages exhausting the parser.
- Long-lived streams, no per-call deadline/timeout, no concurrency limit.

### Deserialization / Type Confusion
- `Any` fields unpacked into unexpected types; unvalidated type URLs.
- `oneof` handling bugs; unknown-field retention leaking data back.

### Transport
- `h2c` cleartext or `-plaintext` accepted where TLS is expected.
- mTLS not enforced / client-cert not verified.
- gRPC-Web CORS: permissive `Access-Control-Allow-Origin` + credentials.

## Testing Methodology

1. Obtain the schema: reflection → else `.proto`/`protoset` from client/app/repo.
2. Enumerate every service and method, including streaming and admin/internal ones.
3. For each method, test unauthenticated, then with a low-privilege token (authz matrix).
4. Manipulate message fields (IDs, roles, tenant, `repeated`/`map`) for IDOR/BOLA.
5. Attack metadata: spoof trust headers, tamper JWT, replay tokens across services.
6. Reach methods via gRPC-Web / transcoding when the native port is filtered.
7. Probe DoS limits (message size, compression, nesting, deadlines) — carefully, non-destructively.
8. Check reflection/health/channelz exposure and error-detail leakage.

## Validation Requirements

- Prove each finding with a concrete call: the exact method, metadata, request message,
  and the response/status that shows the impact (e.g., data for another tenant, an admin
  action performed, a leaked internal detail).
- For authz bypass, show the same call failing with proper creds and succeeding without
  (or with spoofed metadata).
- Record the reproduction as a `grpcurl` command (or raw gRPC-Web request) so it re-runs.
- Do not run destructive or resource-exhausting payloads against production; demonstrate
  DoS potential with a bounded, safe proof.
