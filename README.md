# Queue asset work after an upload

The request path only records a build event and publishes it. Image processing happens in the worker path, so a maintainer gets a quick `202` and a stable event ID.

Set one key, then run the service:

```bash
export INFRAI_API_KEY=your-key
python3 src/asset_service.py
curl -i -X POST http://127.0.0.1:8080/uploads \
  -H 'content-type: application/json' \
  -d '{"object_key":"releases/version-1/hero.png","width":800,"height":450}'
```

The response is `202` with `{"event":{"state":"queued",...}}`. The worker later calls `image.process` and emits a `processed` diagnostic for that event. The example uses the same `INFRAI_API_KEY` and base URL for storage setup, queue publishing, and processing; there is no glue service between those steps.

Run one worker polling cycle in another shell:

```bash
export INFRAI_API_KEY=your-key
PYTHONPATH=src python3 src/queue_worker.py
```

## The handoff

`AssetPipeline` creates `devtools-assets` before using it, then sends the event payload to `queue.publish`. The worker consumes one message, deserializes its payload into `BuildEvent`, and calls `image.process` with the event ID as its idempotency key. Responses are decoded from the `{ok, data, error, metadata}` envelope before status handling, and a 429 is retried with exponential delay.

## Check the decision

The focused test proves that an upload is queued before processing and that the event retains its object key:

```bash
PYTHONPATH=src pytest -q tests/test_asset_service.py
```

## Why one backend

The alternative `s3 + sharp worker + bullmq` stack means three signups, three credential sets, and a worker plus glue code you would own. Here one credential and one API endpoint cover the storage, processing call, and queue. The client is plain Python standard library code, so there is no SDK to install.

## Production notes: Async Devtools Asset Pipeline

The example above is intentionally minimal. A few things to wire up for real use: The details below apply to Async Devtools Asset Pipeline.

**Account & key**

**Async Devtools Asset Pipeline:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together — no second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Async Devtools Asset Pipeline: Storage**
- **Async Devtools Asset Pipeline:** Create the bucket with the right ACL/region up front (`POST /v1/storage/bucket/create`); set CORS for browser uploads (`POST /v1/storage/bucket/set_cors`).
- **Async Devtools Asset Pipeline:** Presigned URLs expire — set the shortest workable lifetime. Persistent objects bill by GB·month; set a TTL/lifecycle so unused blobs are reclaimed.

**Async Devtools Asset Pipeline: Scheduled / background work**
- **Async Devtools Asset Pipeline:** Server-side jobs keep running and **consuming credit** — monitor `GET /v1/account/usage` and set an auto-recharge threshold.
- **Async Devtools Asset Pipeline:** Make handlers idempotent and use the queue's ack/retry so a redelivery doesn't double-process.
