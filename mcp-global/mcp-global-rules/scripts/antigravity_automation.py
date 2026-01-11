#!/usr/bin/env python3
"""
Antigravity IDE Automation Bridge
Automates typing messages into the Antigravity IDE chat interface using Playwright.

This module integrates with telegram_bridge.py and agent_comms.py to enable
Telegram → Antigravity → Telegram message flow.
"""

from pathlib import Path
from typing import Optional
import json
import os
import sys
import time

# Playwright will be imported dynamically to handle installation
try:
    from playwright.sync_api import sync_playwright, Page, Browser, TimeoutError as PlaywrightTimeoutError
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("[WARNING] Playwright not installed. Run: pip install playwright && playwright install chromium")

# MCP Path Resolution
SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.append(str(SCRIPTS_DIR))

try:
    import agent_comms
except ImportError:
    agent_comms = None


class AntigravityBridge:
    """Manages automation of Antigravity IDE chat interface."""

    def __init__(self, workspace_path: Optional[str] = None):
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.playwright = None
        self.conversation_active = False

        # Workspace paths for Quasar (Windows) and WizardPanda (Linux)
        if workspace_path:
            self.workspace_path = Path(workspace_path)
        else:
            # Auto-detect based on hostname
            if os.name == 'nt':  # Windows - Quasar
                self.workspace_path = Path("C:/Users/dbiss/Desktop/Projects/_BLANK_")
            else:  # Linux - WizardPanda
                self.workspace_path = Path("/home/p4nd4pr0t0c01/Projects/_BLANK_")

        print(f"[INFO] Workspace path set to: {self.workspace_path}")

    def connect_to_antigravity(self) -> bool:
        """
        Attempts to connect to a running Antigravity IDE instance.

        Antigravity is an Electron app, so we'll use Playwright's Chromium DevTools Protocol
        to connect to the existing instance.

        Returns:
            bool: True if successfully connected, False otherwise
        """
        if not PLAYWRIGHT_AVAILABLE:
            print("[FAIL] Playwright is not installed.")
            return False

        try:
            self.playwright = sync_playwright().start()

            # Antigravity IDE typically runs on a CDP endpoint
            # We need to find the CDP debugging port
            # Default for Electron apps is often http://localhost:9222

            # Try common debugging ports for Electron apps
            debugging_ports = [9222, 9223, 9224, 8315, 8316]

            for port in debugging_ports:
                try:
                    cdp_url = f"http://localhost:{port}"
                    print(f"[INFO] Attempting to connect to Antigravity at {cdp_url}...")

                    # Connect to existing browser instance
                    self.browser = self.playwright.chromium.connect_over_cdp(cdp_url)
                    contexts = self.browser.contexts

                    if contexts:
                        # Get the first context (main Antigravity window)
                        context = contexts[0]
                        pages = context.pages

                        if pages:
                            # Find the page with the workspace (not Launchpad)
                            workspace_page = None
                            for page in pages:
                                title = page.title()
                                print(f"[DEBUG] Found page with title: {title}")
                                # Skip Launchpad pages, look for workspace
                                if "Launchpad" not in title:
                                    workspace_page = page
                                    print(f"[INFO] Selected page: {title}")
                                    break

                            # Use workspace page if found, otherwise use first page
                            self.page = workspace_page if workspace_page else pages[0]
                            print(f"[OK] Connected to Antigravity on port {port}")

                            # Verify and set workspace directory (non-blocking)
                            if not self.verify_workspace():
                                print("[WARNING] Antigravity may not be in correct workspace")
                                print("[INFO] Attempting to switch workspace...")
                                self.open_workspace()  # Try to switch, but don't fail if it doesn't work
                                print("[INFO] Proceeding with connection anyway...")

                            return True
                except Exception as e:
                    continue

            print("[FAIL] Could not connect to Antigravity. Ensure it's running with remote debugging enabled.")
            print("[INFO] Start Antigravity with: antigravity --remote-debugging-port=9222")
            return False

        except Exception as e:
            print(f"[ERROR] Connection failed: {e}")
            return False

    def verify_workspace(self) -> bool:
        """
        Verifies that Antigravity is open in the correct workspace directory.

        Returns:
            bool: True if in correct workspace, False otherwise
        """
        if not self.page:
            return False

        try:
            # Check if title bar or status bar shows the correct workspace path
            # Method 1: Check window title
            title = self.page.title()
            workspace_name = str(self.workspace_path.name)

            print(f"[DEBUG] Window title: {title}")
            print(f"[DEBUG] Expected workspace: {workspace_name} or {self.workspace_path}")

            if workspace_name in title or str(self.workspace_path) in title:
                print(f"[OK] Antigravity is in correct workspace: {workspace_name}")
                return True

            # Method 2: Execute JavaScript to get workspace path from VS Code API
            try:
                current_workspace = self.page.evaluate("""
                    () => {
                        if (typeof vscode !== 'undefined' && vscode.workspace) {
                            const folders = vscode.workspace.workspaceFolders;
                            if (folders && folders.length > 0) {
                                return folders[0].uri.fsPath;
                            }
                        }
                        return null;
                    }
                """)

                if current_workspace:
                    current_path = Path(current_workspace)
                    if current_path == self.workspace_path or current_path.name == self.workspace_path.name:
                        print(f"[OK] Workspace verified: {current_workspace}")
                        return True

            except Exception as e:
                print(f"[INFO] Could not verify workspace via JS: {e}")

            print(f"[WARNING] Antigravity not in correct workspace (expected: {self.workspace_path})")
            return False

        except Exception as e:
            print(f"[ERROR] Workspace verification failed: {e}")
            return False

    def open_workspace(self) -> bool:
        """
        Opens the correct workspace directory in Antigravity.

        Returns:
            bool: True if workspace opened successfully, False otherwise
        """
        if not self.page:
            return False

        try:
            print(f"[INFO] Opening workspace: {self.workspace_path}")

            # First, press Escape to close any open dialogs
            self.page.keyboard.press("Escape")
            time.sleep(0.5)

            # Click "Open Folder" button if on Launchpad
            try:
                open_folder_button = self.page.query_selector('text="Open Folder"')
                if open_folder_button:
                    print("[INFO] Clicking 'Open Folder' button on Launchpad")
                    open_folder_button.click()
                    time.sleep(2)
                else:
                    # Try keyboard shortcut: Ctrl+K Ctrl+O
                    print("[INFO] Using Ctrl+K Ctrl+O to open folder")
                    self.page.keyboard.press("Control+K")
                    time.sleep(0.2)
                    self.page.keyboard.press("Control+O")
                    time.sleep(2)
            except:
                # Fallback to keyboard shortcut
                print("[INFO] Using Ctrl+K Ctrl+O to open folder")
                self.page.keyboard.press("Control+K")
                time.sleep(0.2)
                self.page.keyboard.press("Control+O")
                time.sleep(2)

            # File dialog should now be open
            # Type the workspace path
            workspace_str = str(self.workspace_path)
            print(f"[INFO] Typing workspace path: {workspace_str}")
            self.page.keyboard.type(workspace_str, delay=50)  # Slower typing
            time.sleep(1)

            # Press Enter to open
            print("[INFO] Pressing Enter to open workspace")
            self.page.keyboard.press("Enter")
            time.sleep(5)  # Wait longer for workspace to load

            # Verify the workspace was opened
            if self.verify_workspace():
                print("[OK] Workspace opened successfully")
                return True
            else:
                print("[WARNING] Workspace may not have opened correctly")
                return False

        except Exception as e:
            print(f"[ERROR] Failed to open workspace: {e}")
            import traceback
            traceback.print_exc()
            return False

    def send_message_to_agent(self, message: str, timeout_seconds: int = 30) -> Optional[str]:
        """
        Types a message into Antigravity's agent chat interface and retrieves the response.

        Args:
            message: The message text to send
            timeout_seconds: Maximum time to wait for response

        Returns:
            str: The agent's response, or None if failed
        """
        if not self.page:
            if not self.connect_to_antigravity():
                return None

        try:
            # Click the "Open Agent Manager" button to open the agent panel
            print("[INFO] Looking for 'Open Agent Manager' button...")
            try:
                # Try to find and click the Open Agent Manager button
                agent_button = self.page.query_selector('text="Open Agent Manager"')
                if agent_button and agent_button.is_visible():
                    print("[INFO] Clicking 'Open Agent Manager' button...")
                    agent_button.click()
                    time.sleep(2)  # Wait for panel to open
                else:
                    # Agent panel might already be open, or button not found
                    print("[INFO] Agent Manager button not found or not visible (panel may already be open)")
            except Exception as e:
                print(f"[DEBUG] Could not click Agent Manager button: {e}")

            # Take a screenshot for debugging
            screenshot_path = Path(__file__).parent / "antigravity_screenshot.png"
            self.page.screenshot(path=str(screenshot_path))
            print(f"[DEBUG] Screenshot saved to: {screenshot_path}")

            # Now find the agent panel input field
            print("[INFO] Looking for agent panel input...")
            # Search for the input with "Ask anything" placeholder
            agent_input = None
            try:
                # Try multiple selectors for the agent input
                selectors = [
                    'textarea[placeholder*="Ask anything"]',
                    'input[placeholder*="Ask anything"]',
                    '[placeholder*="Ask anything"]'
                ]
                for sel in selectors:
                    elements = self.page.query_selector_all(sel)
                    if elements:
                        agent_input = elements[0]
                        print(f"[OK] Found agent input with selector: {sel}")
                        break
            except:
                pass

            if not agent_input:
                print("[FAIL] Could not locate agent panel input")
                print("[INFO] Check screenshot. Agent panel may need to be opened manually first.")
                return None

            # Click the input to focus it
            print("[INFO] Clicking agent input to focus...")
            agent_input.click()
            time.sleep(0.5)

            # Type the message
            print(f"[INFO] Typing message: {message[:50]}...")
            agent_input.fill(message)
            time.sleep(0.3)

            # Send with Enter
            print("[INFO] Sending message with Enter key")
            agent_input.press("Enter")
            time.sleep(0.2)

            # If Enter alone doesn't work, try Ctrl+Enter as fallback
            # (Some chat interfaces require Ctrl+Enter instead of Enter)
            # Commenting this out for now since Enter is standard for Antigravity
            # If testing shows Enter doesn't work, uncomment the line below:
            # input_element.press("Control+Enter")

            # Wait for agent response
            print(f"[INFO] Waiting for agent response (timeout: {timeout_seconds}s)...")

            # Wait briefly for the message to be sent and agent to start processing
            time.sleep(2)

            # Take screenshot showing message was sent
            screenshot_path_after = Path(__file__).parent / "antigravity_screenshot_after.png"
            self.page.screenshot(path=str(screenshot_path_after))
            print(f"[DEBUG] Screenshot after send saved to: {screenshot_path_after}")

            # Poll for agent response with timeout
            # The agent panel typically shows a thinking indicator, then the response
            start_time = time.time()
            response_text = None

            print("[INFO] Polling for agent response...")
            while (time.time() - start_time) < timeout_seconds:
                try:
                    # Look for text content in the agent panel
                    # The agent panel is on the right side with heading "_BLANK_"

                    # Try to find the agent panel container
                    agent_panel_selectors = [
                        'div[class*="agent"]',
                        'div[class*="chat-panel"]',
                        'div[class*="assistant"]',
                        '.monaco-workbench'  # Fallback to workbench
                    ]

                    for panel_selector in agent_panel_selectors:
                        try:
                            panels = self.page.query_selector_all(panel_selector)
                            for panel in panels:
                                # Check if this panel contains messages
                                text = panel.inner_text()

                                # Filter out UI noise and look for actual content
                                # Exclude common UI text like "Ask anything", "Drag a view"
                                if text and len(text.strip()) > 20:
                                    # Check if it contains our sent message (indicates we're in the right panel)
                                    if "test message" in text.lower() or "telegram" in text.lower():
                                        # Look for response after our message
                                        lines = text.split('\n')
                                        # Try to extract meaningful response (skip UI chrome)
                                        meaningful_lines = [
                                            line.strip() for line in lines
                                            if line.strip()
                                            and not line.strip().startswith('Ask anything')
                                            and not line.strip().startswith('Drag a view')
                                            and len(line.strip()) > 10
                                        ]
                                        if len(meaningful_lines) > 0:
                                            response_text = '\n'.join(meaningful_lines)
                                            print(f"[OK] Found response in agent panel ({len(response_text)} chars)")
                                            break
                            if response_text:
                                break
                        except Exception as e:
                            continue

                    if response_text:
                        break

                    # Wait before next poll
                    time.sleep(1)
                    elapsed = int(time.time() - start_time)
                    if elapsed % 5 == 0:  # Progress update every 5 seconds
                        print(f"[INFO] Still waiting... ({elapsed}s elapsed)")

                except Exception as e:
                    print(f"[DEBUG] Polling error: {e}")
                    time.sleep(1)

            # Take final screenshot
            screenshot_final = Path(__file__).parent / "antigravity_screenshot_final.png"
            self.page.screenshot(path=str(screenshot_final))
            print(f"[DEBUG] Final screenshot saved to: {screenshot_final}")

            if response_text:
                print(f"[SUCCESS] Captured response: {response_text[:150]}...")
                return response_text
            else:
                print(f"[WARNING] No response captured after {timeout_seconds}s timeout")
                print("[INFO] The agent may still be processing. Check screenshots for status.")
                return "[TIMEOUT] Agent did not respond within timeout period. Check Antigravity UI."

        except Exception as e:
            print(f"[ERROR] Failed to send message: {e}")
            import traceback
            traceback.print_exc()
            return None

    def close(self):
        """Cleanup resources."""
        if self.browser:
            try:
                self.browser.close()
            except:
                pass
        if self.playwright:
            try:
                self.playwright.stop()
            except:
                pass


def handle_antigravity_message(message_text: str) -> str:
    """
    Main handler for processing Telegram messages destined for Antigravity.

    Args:
        message_text: The instruction from Telegram

    Returns:
        str: The response from Antigravity agent
    """
    print(f"[ANTIGRAVITY] Processing message: {message_text}")

    bridge = AntigravityBridge()

    try:
        response = bridge.send_message_to_agent(message_text, timeout_seconds=60)

        if response:
            return response
        else:
            return "[ERROR] Failed to get response from Antigravity. Ensure the IDE is running with remote debugging enabled."

    finally:
        bridge.close()


def install_playwright():
    """Helper function to install Playwright if needed."""
    import subprocess

    print("[INFO] Installing Playwright...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "playwright"], check=True)
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
        print("[OK] Playwright installed successfully")
        return True
    except Exception as e:
        print(f"[FAIL] Failed to install Playwright: {e}")
        return False


def test_connection():
    """Test the connection to Antigravity IDE."""
    print("=== Antigravity Connection Test ===")

    if not PLAYWRIGHT_AVAILABLE:
        print("[INFO] Playwright not available. Attempting to install...")
        if install_playwright():
            print("[INFO] Please restart this script after installation completes.")
            return

    bridge = AntigravityBridge()

    if bridge.connect_to_antigravity():
        print("[OK] Successfully connected to Antigravity IDE")

        # Test sending a simple message
        test_msg = "Hello! This is a test message from the Telegram bridge."
        print(f"\n[TEST] Sending test message: {test_msg}")

        response = bridge.send_message_to_agent(test_msg, timeout_seconds=30)

        if response:
            print(f"\n[SUCCESS] Received response:\n{response}")
        else:
            print("\n[FAIL] No response received")
    else:
        print("[FAIL] Could not connect to Antigravity")
        print("\nTroubleshooting:")
        print("1. Ensure Antigravity IDE is running")
        print("2. Start Antigravity with remote debugging:")
        print("   antigravity --remote-debugging-port=9222")
        print("3. Or add to Antigravity settings:")
        print('   "args": ["--remote-debugging-port=9222"]')

    bridge.close()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test_connection()
    elif len(sys.argv) > 1 and sys.argv[1] == "install":
        install_playwright()
    else:
        print("Antigravity IDE Automation Bridge")
        print("\nUsage:")
        print("  python antigravity_automation.py test       # Test connection to Antigravity")
        print("  python antigravity_automation.py install    # Install Playwright dependencies")
        print("\nThis module is typically called by agent_comms.py to handle Telegram messages.")
