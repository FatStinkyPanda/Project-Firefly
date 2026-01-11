from unittest.mock import MagicMock
import unittest

from agent_manager.models.base import BaseModelService
from agent_manager.models.manager import ModelClientManager

class MockFailingService(BaseModelService):
    def validate_config(self): return True
    def generate(self, prompt, system_prompt=None): raise Exception("Simulated Failure")

class MockSuccessService(BaseModelService):
    def validate_config(self): return True
    def generate(self, prompt, system_prompt=None): return "Success Response"

class TestModelClient(unittest.TestCase):
    def test_failover_logic(self):
        """Test that the manager fails over from a bad service to a good one."""
        bad_provider = MockFailingService(model_name="bad")
        good_provider = MockSuccessService(model_name="good")

        manager = ModelClientManager(providers=[bad_provider, good_provider])

        # Should succeed despite the first provider failing
        response = manager.generate("Hello")
        self.assertEqual(response, "Success Response")

    def test_all_fail(self):
        """Test strict failure when all providers fail."""
        bad1 = MockFailingService(model_name="bad1")
        bad2 = MockFailingService(model_name="bad2")

        manager = ModelClientManager(providers=[bad1, bad2])

        with self.assertRaises(RuntimeError):
            manager.generate("Hello")

if __name__ == "__main__":
    unittest.main()
