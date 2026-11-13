---
# ai-generated: 100% - assistant generated draft, verdicts by author
lab3_slo:
  service: svcdesk
  route: /kb/search
  window: 28d
  slis:
    availability:
      good: sum(rate(http_server_request_duration_seconds_count{http_route="/kb/search", http_response_status_code!~"5.."}[28d]))
      valid: sum(rate(http_server_request_duration_seconds_count{http_route="/kb/search"}[28d]))
      total: sum(rate(http_server_request_duration_seconds_count{http_route="/kb/search"}[28d]))
      objective: 0.995
      error_budget: {fraction: 0.005, minutes: 201.6}
    latency:
      threshold_seconds: 0.3
      good: sum(rate(http_server_request_duration_seconds_bucket{http_route="/kb/search", le="0.3"}[28d]))
      valid: sum(rate(http_server_request_duration_seconds_count{http_route="/kb/search"}[28d]))
      total: sum(rate(http_server_request_duration_seconds_count{http_route="/kb/search"}[28d]))
      objective: 0.995
      error_budget: {fraction: 0.005, minutes: 201.6}
  alerts:
    - alert: KbSearchLatencyHigh_FastBurn
      sli: latency
      burn_rate: 14.4
      long_window: 1h
      short_window: 5m
    - alert: KbSearchLatencyHigh_SlowBurn
      sli: latency
      burn_rate: 6.0
      long_window: 6h
      short_window: 30m
---