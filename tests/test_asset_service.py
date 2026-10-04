from asset_service import AssetPipeline


class FakeClient:
    def __init__(self):
        self.published = []

    def ensure_bucket(self, name):
        self.bucket = name

    def publish(self, payload):
        self.published.append(payload)

    def process(self, image, width, height, event_id):
        return {"image": image, "width": width, "height": height}


def test_upload_is_queued_before_processing():
    client = FakeClient()
    pipeline = AssetPipeline(client)
    event = pipeline.enqueue_upload("releases/version-1/hero.png", 800, 450)
    assert event.state == "queued"
    assert client.published[0]["object_key"] == "releases/version-1/hero.png"
    assert pipeline.handle_job(event).state == "processed"
