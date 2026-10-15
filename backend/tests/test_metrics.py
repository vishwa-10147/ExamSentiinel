"""CloudWatch Embedded Metric Format output (app/core/metrics.py)."""

import json

from httpx import AsyncClient

from app.core.metrics import NAMESPACE, Metrics, metrics


def test_snapshot_is_a_valid_emf_document_and_resets():
    m = Metrics(service="api")
    for status, ms in ((200, 10), (200, 30), (404, 5), (429, 2), (503, 40), (500, 50), (202, 900)):
        m.record_request(status, ms, "/api/practice/problems/x/submit" if status == 202 else "/x")
    m.record_verdict("ACCEPTED", 0.4)
    m.record_verdict("SYSTEM_ERROR", 2.0)
    doc = m.snapshot({"JudgeBacklog": 3, "JudgeOldestPendingSeconds": 12.5})

    directive = doc["_aws"]["CloudWatchMetrics"][0]
    assert directive["Namespace"] == NAMESPACE and directive["Dimensions"] == [["Service"]]
    assert isinstance(doc["_aws"]["Timestamp"], int) and doc["Service"] == "api"
    names = {d["Name"]: d["Unit"] for d in directive["Metrics"]}
    for name in names:  # every declared metric has a numeric value at the top level
        assert isinstance(doc[name], float), name
    assert names["LatencyP95"] == "Milliseconds" and names["Requests"] == "Count" and names["JudgeOldestPendingSeconds"] == "Seconds"
    assert (doc["Requests"], doc["Responses4xx"], doc["Responses5xx"]) == (7, 2, 2)
    assert (doc["RateLimited"], doc["DatabaseBusy"], doc["SubmissionsQueued"]) == (1, 1, 1)
    assert (doc["Verdicts"], doc["JudgeSystemErrors"], doc["JudgeBacklog"]) == (2, 1, 3)
    assert doc["LatencyMax"] == 900 and doc["LatencyP50"] == 30
    json.dumps(doc)  # one JSON line

    empty = m.snapshot()
    assert empty["Requests"] == 0 and empty["LatencyP95"] == 0


async def test_requests_are_counted_by_the_middleware(async_client: AsyncClient):
    metrics.snapshot()  # start from zero
    await async_client.get("/api/health/live")
    await async_client.get("/api/practice/problems")  # 401: not signed in
    doc = metrics.snapshot()
    assert doc["Requests"] == 2 and doc["Responses4xx"] == 1
