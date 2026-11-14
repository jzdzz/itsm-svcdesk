---
lab4_postmortem:
  ticket: "1224ad8d-06a8-4ae3-865a-da2015a4ddb5"
  detecting_alert: ShopCheckoutErrors
  onset: 2026-10-12T07:05:45Z
  detection: 2026-10-12T07:09:19Z
  acknowledgement: 2026-10-12T07:10:07Z
  recovery: 2026-10-12T07:12:19Z
  mttd_seconds: 214
  mtta_seconds: 48
  mttr_seconds: 394
  identified_flags: [productCatalogFailure, adManualGc]
---
<!-- ai-generated: 30% - structure and wording drafted with Claude from the course template; numbers read from incident/tsdb-snapshot.tar.gz and incident/ticket.json -->

# Postmortem: Some shop orders failed and the ad service slowed down for about 6.5 minutes

## Date

The incident happened on 2026-10-12; this postmortem was written on 2026-11-14.

## Authors

jzdzz, who worked the incident as the on-call (recorded incident lab4-rec-3).

## Status

Complete; the action items below are in progress and tracked under the Bug ids in the table.

## Summary

Between 07:05:45 and 07:12:19 UTC the product catalog failed a few percent of product lookups and the ad service answered about 280 times slower, so a small share of checkouts failed for 394 seconds.

## Impact

Between 07:05:45 and 07:12:19 UTC, 2 of 46 PlaceOrder calls failed (4.3 %), and 44 succeeded; the other requests of checkout were not lost. The product catalog failed 38 of 742 GetProduct calls (5.1 %). The ad service's GetAds averaged about 567 ms instead of about 2 ms. Counts come from the span metrics, which are pushed once a minute, so they are approximate; the queries are in Supporting information.

## Root Causes

Two faults were active at the same time. productCatalogFailure made ProductCatalogService return errors for a share of GetProduct calls, and when a checkout needed an affected product, PlaceOrder failed with it. adManualGc made the ad service pause for garbage collection, so GetAds became slow and the frontend's data route slowed with it. A third fault of the pool was not identified: email and recommendation memory stayed flat during the incident.

## Trigger

Both faults became active at 07:05:45 UTC (the onset), when the injector switched the failing feature flags on. The first failed PlaceOrder calls appear in the metrics at about 07:09.

## Resolution

The failing flags were switched off, after which GetProduct errors stopped growing (the error counter stayed at 38 from 07:10:17 on) and the alert resolved. The recovery instant is 07:12:19 UTC, the end of the first firing run of ShopCheckoutErrors.

## Detection

The alert ShopCheckoutErrors fired at 07:09:19 UTC, 214 seconds after the onset (MTTD), on the symptom of failing checkout requests. The on-call acknowledged the ticket at 07:10:07 UTC, 48 seconds after detection (MTTA). The slow ad service raised a separate P2 alert and would otherwise have been noticed only by users.

## Action Items

| Action Item | Type | Owner | Bug |
|---|---|---|---|
| Retry or fall back when GetProduct fails inside PlaceOrder | mitigate | jzdzz | ITSM-101 |
| Add a latency alert on the ad service's GetAds and the frontend data route | prevent | jzdzz | ITSM-102 |
| Shorten the evaluation delay of ShopCheckoutErrors to lower MTTD | process | jzdzz | ITSM-103 |

## Lessons Learned

### What went well

The alert fired and paged the on-call, the ticket was created and acknowledged within a minute of detection, and checkout kept serving most orders during the incident.

### What went wrong

Detection took 214 seconds, two faults overlapped so one symptom hid the other, and the checkout had no fallback when the catalog failed a lookup.

### Where we got lucky

The catalog failed only a few percent of lookups and the fault lasted 394 seconds, so only 2 orders were lost.

## Timeline

All times are UTC, on 2026-10-12.

- 07:05:45 - onset: both faults become active.
- 07:09:19 - detection: ShopCheckoutErrors fires and pages the on-call.
- 07:09:37 - ticket 1224ad8d-06a8-4ae3-865a-da2015a4ddb5 created, priority P1.
- 07:10:07 - acknowledgement of the ticket by the on-call.
- 07:12:19 - recovery: the alert's firing run ends and checkout answers normally.

## Supporting information

Evidence: the output of `itsmlab incident 4` (run fe6ecd21acce7a08), incident/ticket.json, the snapshot incident/tsdb-snapshot.tar.gz, and the ledger ai-rca-eval.json with its transcript in ai-rca/. Queries behind the numbers, at 07:12:19 over the window 07:05:45 to 07:12:19: failed orders `increase(traces_span_metrics_calls_total{service_name="checkout", span_kind="SPAN_KIND_SERVER", span_name="oteldemo.CheckoutService/PlaceOrder", status_code="STATUS_CODE_ERROR"}[7m])` (2, against 44 without the status filter); failed lookups `increase(traces_span_metrics_calls_total{service_name="product-catalog", span_name="oteldemo.ProductCatalogService/GetProduct", status_code="STATUS_CODE_ERROR"}[7m])` (38); ad latency `rate(traces_span_metrics_duration_milliseconds_sum{service_name="ad", span_name="oteldemo.AdService/GetAds"}[5m]) / rate(traces_span_metrics_duration_milliseconds_count{service_name="ad", span_name="oteldemo.AdService/GetAds"}[5m])` (about 567 ms during, 2 ms before).

## Problem record

- Incident record: 1224ad8d-06a8-4ae3-865a-da2015a4ddb5
- Root cause: productCatalogFailure (GetProduct errors) and adManualGc (slow ad service), with no fallback in checkout.
- Known error: when the product catalog fails a lookup, the PlaceOrder call that needs that product fails until the fault is removed.
- Workaround: switch the failing feature flags off, which stops the errors within minutes.
