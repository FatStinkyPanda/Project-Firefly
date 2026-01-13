from unittest.mock import MagicMock
import json
import os
import sys
import time

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent_manager.triggers.ide_control import IDEControlService

def test_ide_control():
    mock_bus = MagicMock()
    service = IDEControlService(mock_bus)

    # We need to mock stdin for this test
    import io
    fake_stdin = io.StringIO('{"type": "set_mode", "autonomous": true}\n{"type": "intent", "id": "test_cmd", "args": [1, 2]}\n')
    sys.stdin = fake_stdin

    print("Starting IDE Control Service test...")
    service.start()

    # Give it a moment to process
    time.sleep(1)

    service.stop()

    # Verify events were published
    print(f"Call count: {mock_bus.publish.call_count}")
    for call in mock_bus.publish.call_args_list:
        print(f"Published: {call}")

    assert mock_bus.publish.call_count >= 2
    print("Test passed!")

if __name__ == "__main__":
    test_ide_control()
