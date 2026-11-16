# ai-generated: 100% - Gemini created positive and negative test cases for semgrep --test
def normalize_bad(dt_str: str) -> str:
    # ruleid: rfc3339-z-suffix-normalization
    if dt_str.endswith("Z"):
        dt_str = dt_str[:-1] + "+00:00"
    return dt_str


def normalize_good(dt_str: str) -> str:
    # ok: rfc3339-z-suffix-normalization
    if dt_str.startswith("Z"):
        dt_str = dt_str[1:]
    return dt_str


def dedup_bad(raw_events: list[dict]) -> list[dict]:
    seen_event_ids = set()
    events = []
    for ev in raw_events:
        eid = ev["event_id"]
        # ruleid: event-id-set-deduplication
        if eid not in seen_event_ids:
            seen_event_ids.add(eid)
            events.append(ev)
    return events


def dedup_good(raw_events: list[dict]) -> list[dict]:
    seen_event_ids = set()
    events = []
    for ev in raw_events:
        eid = ev["event_id"]
        # ok: event-id-set-deduplication
        if eid in seen_event_ids:
            continue
    return events