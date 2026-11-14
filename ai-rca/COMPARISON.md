<!-- ai-generated: 100% - Gemini, reviewed by me -->

# Comparison of AI RCA Investigators

## Overview of Investigators

In this root cause analysis evaluation for incident `1224ad8d-06a8-4ae3-865a-da2015a4ddb5` (onset at `2026-10-12T07:05:45Z`, paged by `ShopCheckoutErrors` at `2026-10-12T07:09:19Z`), two investigator configurations were evaluated:

1. **Investigator 1 (`ai-rca-eval.json`)**: `CustomAgent` powered by `qwen3:4b-instruct` querying Prometheus span metrics via MCP tools (`list_metrics`, `label_values`, `query_range`).
2. **Investigator 2 (`ai-rca-eval-2.json`)**: `CustomAgent` powered by `llama3` evaluated against the same telemetry window (`07:00Z` to `07:20Z`).

## Comparison of Hypotheses and Accuracy

* **Hypothesis H1 (`product-catalog` - `correct`)**: Both investigators correctly identified that downstream errors in `oteldemo.ProductCatalogService/GetProduct` propagated to `CheckoutService` during order placement. This matched the active `productCatalogFailure` fault flag in the snapshot.
* **Hypothesis H2 (`checkout` - `partially_correct`)**: Both investigators noted the 2 erroneous calls in `oteldemo.CheckoutService/PlaceOrder`. While factually true in the metric `traces_span_metrics_calls_total{service_name="checkout", status_code="STATUS_CODE_ERROR"}`, this describes the symptom rather than the underlying root cause.
* **Hypothesis H3 (`payment` - `hallucinated`)**: Both models proposed a speculative hypothesis blaming `oteldemo.PaymentService/Charge` without supporting error counts in the Prometheus time series (`result: false`).

## Conclusion

Both models achieved a precision of 1/3 strict root-cause hits (or 2/3 when counting symptom identification in `checkout`), demonstrating that small local models can locate failing spans via `query_range`, but still require human verification to filter out hallucinated downstream dependencies like `PaymentService` and to spot latency faults such as `adManualGc`.