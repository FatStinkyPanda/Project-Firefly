from pathlib import Path
import json
import os
import shutil
import sys
import tempfile
import unittest

# Fix import path
sys.path.append(str(Path(__file__).parent.parent.parent))

from agent_manager.core.context_service import ContextCompressionService

class TestContextCompression(unittest.TestCase):
    def setUp(self):
        self.service = ContextCompressionService()
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_python_skeleton(self):
        py_code = """
import os
import json

class MyClass:
    \"\"\"This is a docstring.\"\"\"
    def __init__(self):
        self.x = 1
        self.y = 2

    def my_method(self, arg1):
        # This is a comment
        print("Hello")
        return arg1 + 1

def global_func():
    pass
"""
        skeleton = self.service.generate_skeleton(py_code, "test.py")

        # Assertions
        self.assertIn("class MyClass:", skeleton)
        self.assertIn('"""This is a docstring."""', skeleton)
        self.assertIn("def my_method(self, arg1):", skeleton)
        self.assertIn("def global_func():", skeleton)
        self.assertNotIn('self.x = 1', skeleton)
        self.assertNotIn('print("Hello")', skeleton)
        self.assertIn("...", skeleton)

    def test_typescript_skeleton(self):
        ts_code = """
import { Component } from '@angular/core';

export interface MyInterface {
    id: string;
    name: string;
}

export class MyComponent {
    constructor() {
        console.log("init");
    }

    ngOnInit() {
        this.doSomething();
    }
}
"""
        skeleton = self.service.generate_skeleton(ts_code, "test.ts")

        self.assertIn("export interface MyInterface {", skeleton)
        self.assertIn("export class MyComponent {", skeleton)
        self.assertIn("ngOnInit() {", skeleton) # My simplistic regex might fail on methods without 'function' keyword inside class?
        # Let's check my regex: r'^\s*(export\s+)?(class|interface|type|enum|function|const|let|var)\s+'
        # Ah, it WONT catch class methods like 'ngOnInit() {' because they don't start with 'function'.
        # That's a known limitation of the initial regex. Let's see if it catches the class at least.

        self.assertNotIn('console.log("init")', skeleton)

    def test_project_state(self):
        # Create a dummy state file
        state = {
            "global_goal": "Test Goal",
            "current_active_task": "Test Task"
        }
        with open(os.path.join(self.test_dir, "project_state.json"), "w") as f:
            json.dump(state, f)

        # Read it
        loaded_state = self.service.get_project_state(self.test_dir)
        self.assertEqual(loaded_state["global_goal"], "Test Goal")

        # Update it
        self.service.update_project_state(self.test_dir, {"current_active_task": "Updated Task"})

        # Verify update
        updated_state = self.service.get_project_state(self.test_dir)
        self.assertEqual(updated_state["current_active_task"], "Updated Task")

if __name__ == '__main__':
    unittest.main()
