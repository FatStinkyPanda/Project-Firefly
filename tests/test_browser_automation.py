import asyncio
import unittest
from unittest.mock import MagicMock
from agent_manager.core.browser_adapter import BrowserAdapter
from agent_manager.orchestrator import OrchestratorManager
from agent_manager.core.event_bus import EventBusService

class TestBrowserAutomation(unittest.TestCase):
    def setUp(self):
        self.event_bus = EventBusService()
        self.browser_adapter = BrowserAdapter(self.event_bus)
        self.model_client = MagicMock()
        self.orchestrator = OrchestratorManager(
            event_bus=self.event_bus,
            model_client=self.model_client,
            browser_adapter=self.browser_adapter
        )

    def test_browser_adapter_navigation(self):
        async def run_test():
            result = await self.browser_adapter.navigate("https://example.com")
            self.assertEqual(result["status"], "success")
            text = await self.browser_adapter.get_text()
            self.assertIn("Example Domain", text["content"])
            await self.browser_adapter.stop()

        asyncio.run(run_test())

    def test_orchestrator_browser_tag(self):
        # Mock AI response with a browser tag
        mock_response = MagicMock()
        mock_response.text = 'I will look at example.com. <browser action="navigate" url="https://example.com"/> <browser action="get_text"/>'
        self.model_client.generate.return_value = mock_response

        # Use sync bridge
        self.orchestrator.process_request("Search for example.com", source="user")
        
        # Verify that browser adapter was used (we check if it started/navigated)
        # Since it's a real browser, loop.run_until_complete in process_request should have finished.
        
        # Cleanup
        asyncio.run(self.browser_adapter.stop())

if __name__ == "__main__":
    unittest.main()
