from unittest.mock import MagicMock
import re
import unittest

from agent_manager.core.event_bus import EventBusService
from agent_manager.core.prompt_service import PromptService
from agent_manager.orchestrator import OrchestratorManager

class TestSpecializedAgents(unittest.TestCase):
    def setUp(self):
        self.prompt_service = PromptService()
        self.event_bus = EventBusService()
        self.model_client = MagicMock()
        self.orchestrator = OrchestratorManager(
            event_bus=self.event_bus,
            model_client=self.model_client,
            prompt_service=self.prompt_service
        )

    def test_prompt_service_roles(self):
        roles = self.prompt_service.list_roles()
        self.assertIn("Lead Orchestrator", roles)
        self.assertIn("Test Engineer", roles)
        self.assertIn("Documentarian", roles)

        prompt = self.prompt_service.get_prompt("Documentarian")
        self.assertIn("Firefly Documentarian", prompt)
        self.assertIn("<thought>", prompt)

    def test_task_decomposition_parsing(self):
        plan_text = """
        I will decompose this task.
        <plan>
        - [ ] Write tests (Test Engineer)
        - [ ] Update README (Documentarian)
        </plan>
        """
        # Mock delegate_task
        self.orchestrator.delegate_task = MagicMock()

        self.orchestrator._handle_plans(plan_text, "test_session")

        self.assertEqual(self.orchestrator.delegate_task.call_count, 2)
        args = [call.args for call in self.orchestrator.delegate_task.call_args_list]
        self.assertEqual(args[0][0], "Test Engineer")
        self.assertEqual(args[1][0], "Documentarian")

    def test_orchestrator_uses_prompt_service(self):
        # Trigger an async process
        self.model_client.generate.return_value = MagicMock(text="<thought>OK</thought> <message>Done</message>")

        # We need to run the async method
        import asyncio
        async def run_req():
            await self.orchestrator.process_request_async("Hello", "terminal")

        asyncio.run(run_req())

        # Verify that prompt_service was called (indirectly through system_prompt)
        sys_prompt = self.model_client.generate.call_args[1]['system_prompt']
        self.assertIn("Firefly Lead Orchestrator", sys_prompt)

if __name__ == "__main__":
    unittest.main()
