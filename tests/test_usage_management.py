import unittest
from unittest.mock import MagicMock
from agent_manager.models.manager import ModelClientManager
from agent_manager.models.base import ModelResponse, BaseModelService
from agent_manager.core.event_bus import EventBusService

class MockProvider(BaseModelService):
    def validate_config(self):
        return True
    
    def generate(self, prompt: str, system_prompt=None):
        return ModelResponse(
            text="Mock response",
            prompt_tokens=10,
            completion_tokens=20,
            model_name="mock-model",
            cost_usd=0.01
        )

class TestUsageManagement(unittest.TestCase):
    def setUp(self):
        self.bus = EventBusService()
        self.provider = MockProvider()
        self.manager = ModelClientManager([self.provider], event_bus=self.bus)

    def test_usage_tracking(self):
        # Subscribe to usage events
        self.event_received = False
        def on_usage(event_type, payload):
            self.event_received = True
            self.payload = payload
        
        self.bus.subscribe("usage_report", on_usage)
        
        # Generate
        response = self.manager.generate("Hello")
        
        # Verify response
        self.assertEqual(response.text, "Mock response")
        self.assertEqual(response.prompt_tokens, 10)
        
        # Verify ledger
        self.assertEqual(self.manager.usage_ledger["total_prompt_tokens"], 10)
        self.assertEqual(self.manager.usage_ledger["total_cost_usd"], 0.01)
        
        # Verify event
        self.assertTrue(self.event_received)
        self.assertEqual(self.payload["current_response"]["model"], "mock-model")

if __name__ == "__main__":
    unittest.main()
