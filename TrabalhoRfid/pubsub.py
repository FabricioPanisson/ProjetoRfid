
from pubnub.pnconfiguration import PNConfiguration
from pubnub.pubnub import PubNub

class AsyncConn:
    def __init__(self, id: str, channel_name: str) -> None:
        config = PNConfiguration()
        config.subscribe_key = 'sub-c-92e05891-c623-4c0e-8275-6e3354e088a1'
        config.publish_key = 'pub-c-756fcfb1-1c6f-413d-81c4-de608b5afe7e'
        config.user_id = id
        config.enable_subscribe = True
        config.daemon = True

        self.pubnub = PubNub(config)
        self.channel_name = channel_name

        subscription = self.pubnub.channel(self.channel_name).subscription()
        subscription.subscribe()

    def publish(self, data: dict):
        self.pubnub.publish().channel(self.channel_name).message(data).sync()
