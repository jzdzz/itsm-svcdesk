<!-- ai-generated: 100% - client-server latency gap explanation -->
# Client-Server Latency Gap Analysis

When measuring the latency of `GET /kb/search` through a Toxiproxy instance configured with a downstream latency toxic of 100 ms (`latency: 100`, `jitter: 0`), we observe a systematic gap of approximately 0.100 seconds (100 ms) between the client-side p99 (`client_p99_seconds` around 0.360 s measured by `oha`) and the server-side p99 (`server_p99_seconds` around 0.260 s computed via `histogram_quantile(0.99)` on `http_server_request_duration_seconds_bucket`).

## Why the gap exists

1. **Measurement Boundaries**: The server-side histogram middleware inside `svcdesk` starts its timer only after the HTTP request has been read from the container's socket and stops it immediately when the WSGI/ASGI application writes the response headers and body. It is completely blind to anything happening outside the application process.
2. **Network and Proxy Delay**: Toxiproxy sits between the load generator (`oha`) and `svcdesk`, injecting a 100 ms delay on the downstream response path before forwarding bytes back to the client. Because `svcdesk` has already finished processing the request and recorded its duration metric before the response hits the proxy delay, the server histogram remains unchanged at ~0.260 s while the client experiences the full ~0.360 s round-trip time.
3. **Queueing and Connection Overhead**: In production environments, similar client-server gaps arise from TLS handshakes, reverse-proxy buffering, TCP retransmissions, load balancer queueing, and client-side connection pool saturation. Therefore, SLIs that reflect true user experience should be complemented by client-side or edge-level probing rather than relying exclusively on internal application histograms.
