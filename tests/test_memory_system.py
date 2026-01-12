import unittest
import shutil
import os
from pathlib import Path
from unittest.mock import MagicMock
from agent_manager.core.memory_service import MemoryService

class TestMemoryService(unittest.TestCase):
    def setUp(self):
        self.test_path = Path("test_memory")
        if self.test_path.exists():
            shutil.rmtree(self.test_path)
            
        self.model_client = MagicMock()
        # Mock embedding [0.1, 0.2, ...] with dimension 1536
        self.model_client.embed.return_value = [0.1] * 1536
        
        self.service = MemoryService(self.model_client, memory_path=str(self.test_path))

    def tearDown(self):
        if self.test_path.exists():
            shutil.rmtree(self.test_path)

    def test_upsert_and_query(self):
        text = "Firefly uses FAISS for semantic memory."
        meta = {"test": True}
        
        success = self.service.upsert(text, meta)
        self.assertTrue(success)
        self.assertEqual(len(self.service.metadata), 1)
        
        # Query
        results = self.service.query("vector search", top_k=1)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["text"], text)
        self.assertTrue("score" in results[0])

    def test_persistence(self):
        self.service.upsert("Persistent thought", {"p": 1})
        self.service.save()
        
        # Create a new service instance pointing to same path
        new_service = MemoryService(self.model_client, memory_path=str(self.test_path))
        self.assertEqual(len(new_service.metadata), 1)
        self.assertEqual(new_service.metadata[0]["text"], "Persistent thought")

if __name__ == "__main__":
    unittest.main()
