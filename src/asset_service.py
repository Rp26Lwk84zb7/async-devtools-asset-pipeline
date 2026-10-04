import json
import uuid
from dataclasses import asdict, dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

from infrai_client import InfraiClient


@dataclass
class BuildEvent:
    event_id: str
    object_key: str
    width: int
    height: int
    state: str = "queued"


@dataclass
class Diagnostic:
    event_id: str
    state: str
    detail: str


class AssetPipeline:
    def __init__(self, client: InfraiClient, bucket: str = "devtools-assets"):
        self.client, self.bucket = client, bucket
        self.client.ensure_bucket(bucket)

    def enqueue_upload(self, object_key: str, width: int = 1200, height: int = 630) -> BuildEvent:
        event = BuildEvent(str(uuid.uuid4()), object_key, width, height)
        self.client.publish(asdict(event))
        return event

    def handle_job(self, event: BuildEvent) -> Diagnostic:
        result = self.client.process(event.object_key, event.width, event.height, event.event_id)
        return Diagnostic(event.event_id, "processed", json.dumps(result, separators=(",", ":")))


class Handler(BaseHTTPRequestHandler):
    pipeline: AssetPipeline

    def do_POST(self) -> None:
        if self.path != "/uploads":
            self.send_error(404)
            return
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
        event = self.pipeline.enqueue_upload(body["object_key"], body.get("width", 1200), body.get("height", 630))
        encoded = json.dumps({"event": asdict(event)}).encode()
        self.send_response(202)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def serve() -> None:
    handler = Handler
    handler.pipeline = AssetPipeline(InfraiClient())
    HTTPServer(("127.0.0.1", 8080), handler).serve_forever()


if __name__ == "__main__":
    serve()

