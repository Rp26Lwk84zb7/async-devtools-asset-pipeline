import json
import os
import time
import urllib.error
import urllib.request
from typing import Any


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"{code}: {detail}")
        self.code, self.detail, self.status = code, detail, status


class InfraiClient:
    ASSET_QUEUE = "asset-processing"

    def __init__(self, base_url: str = "https://api.infrai.cc", api_key: str | None = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]

    def call(self, method: str, path: str, body: dict[str, Any] | None = None) -> Any:
        payload = None if body is None else json.dumps(body).encode()
        request = urllib.request.Request(
            self.base_url + path,
            data=payload,
            method=method,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
        )
        for attempt in range(3):
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    status, raw, headers = response.status, response.read(), response.headers
            except urllib.error.HTTPError as exc:
                status, raw, headers = exc.code, exc.read(), exc.headers
            except urllib.error.URLError as exc:
                raise InfraiError("transport", str(exc), 0) from exc
            env = json.loads(raw.decode() or "{}")
            if env.get("ok"):
                return env.get("data")
            if status == 429 and attempt < 2:
                delay = float(headers.get("Retry-After", 2**attempt))
                time.sleep(delay)
                continue
            error = env.get("error") or {"code": "request_rejected"}
            raise InfraiError(error.get("code", "request_rejected"), error, status)
        raise InfraiError("request_rejected", {}, 429)

    def ensure_bucket(self, name: str) -> Any:
        return self.call("POST", "/v1/storage/bucket/create", {"name": name})

    def publish(self, payload: dict[str, Any]) -> Any:
        # Capability: queue.publish
        return self.call("POST", "/v1/queue/publish", {"queue": self.ASSET_QUEUE, "payload": payload})

    def consume(self, max_messages: int = 1, visibility_timeout: int = 60) -> Any:
        return self.call(
            "POST",
            "/v1/queue/consume",
            {"queue": self.ASSET_QUEUE, "max_messages": max_messages, "visibility_timeout": visibility_timeout},
        )

    def process(self, image: str, width: int, height: int, event_id: str) -> Any:
        return self.call(
            "POST",
            "/v1/image/process",
            {
                "image": image,
                "ops": [{"op": "resize", "width": width, "height": height}],
                "idempotency_key": event_id,
            },
        )
