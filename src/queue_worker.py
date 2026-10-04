from asset_service import AssetPipeline, BuildEvent
from infrai_client import InfraiClient


def run_once() -> None:
    client = InfraiClient()
    pipeline = AssetPipeline(client)
    batch = client.consume(max_messages=1, visibility_timeout=60)
    for message in batch.get("items", []):
        event = BuildEvent(**message["payload"])
        diagnostic = pipeline.handle_job(event)
        print(f"{diagnostic.event_id} {diagnostic.state} {diagnostic.detail}")


if __name__ == "__main__":
    run_once()
