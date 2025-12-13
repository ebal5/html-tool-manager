"""Basic E2E tests for HTML Tool Manager."""

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.e2e
class TestToolList:
    """Tests for tool list page."""

    def test_page_loads(self, test_page: Page) -> None:
        """Page should load with the navigation header."""
        expect(test_page.locator("nav li strong")).to_have_text("HTML Tool Manager")

    def test_empty_state(self, test_page: Page) -> None:
        """Empty state message should be displayed when no tools exist."""
        expect(test_page.locator("text=ツールが見つかりませんでした。")).to_be_visible()

    def test_create_link_exists(self, test_page: Page) -> None:
        """Create link should exist in navigation."""
        expect(test_page.locator("a[href='/tools/create']")).to_be_visible()


@pytest.mark.e2e
class TestToolCRUD:
    """Tests for CRUD operations."""

    def test_create_tool(self, test_page: Page, live_server: str) -> None:
        """Tool creation flow should work correctly."""
        # Navigate to create page
        test_page.click("a[href='/tools/create']")
        expect(test_page).to_have_url(f"{live_server}/tools/create")

        # Fill form
        test_page.fill("#name", "Test Tool")
        test_page.fill("#description", "Test Description")
        test_page.fill("#tags", "test, e2e")

        # Wait for Ace Editor and type code
        ace_textarea = test_page.locator("#code-editor textarea.ace_text-input")
        ace_textarea.focus()
        test_page.keyboard.type("<p>Hello E2E!</p>")

        # Submit
        test_page.click("#submit-btn")

        # Wait for success message (includes auto-detected type)
        expect(test_page.locator("#message")).to_contain_text("作成しました")

        # Navigate back to home
        test_page.click("#message a[href='/']")

        # Verify tool appears in list
        expect(test_page.locator("text=Test Tool")).to_be_visible()
        expect(test_page.locator("text=Test Description")).to_be_visible()


@pytest.mark.e2e
class TestNavigation:
    """Tests for navigation."""

    def test_home_link(self, test_page: Page, live_server: str) -> None:
        """Home link should navigate to root."""
        # Navigate to create page first
        test_page.click("a[href='/tools/create']")
        expect(test_page).to_have_url(f"{live_server}/tools/create")

        # Click home link
        test_page.click("a[href='/']")
        expect(test_page).to_have_url(f"{live_server}/")


@pytest.mark.e2e
class TestAceEditor:
    """Tests for Ace Editor integration."""

    def test_editor_loads_on_create_page(self, test_page: Page, live_server: str) -> None:
        """Ace Editor should load on create page."""
        test_page.click("a[href='/tools/create']")
        expect(test_page).to_have_url(f"{live_server}/tools/create")

        # Wait for Ace Editor to initialize
        editor = test_page.locator("#code-editor")
        expect(editor).to_be_visible()

        # Ace Editor creates a specific class structure
        ace_content = test_page.locator("#code-editor .ace_content")
        expect(ace_content).to_be_visible()

    def test_editor_syntax_highlight(self, test_page: Page, live_server: str) -> None:
        """Ace Editor should provide syntax highlighting."""
        test_page.click("a[href='/tools/create']")

        # Wait for editor to be ready
        editor = test_page.locator("#code-editor")
        expect(editor).to_be_visible()

        # Type HTML code into the editor
        ace_textarea = test_page.locator("#code-editor textarea.ace_text-input")
        ace_textarea.focus()
        test_page.keyboard.type("<div>Hello</div>")

        # Check for syntax highlighting (ace adds specific classes)
        expect(test_page.locator("#code-editor .ace_tag-name").first).to_be_visible()

    def test_editor_mode_switch(self, test_page: Page, live_server: str) -> None:
        """Editor mode should switch when tool type changes."""
        test_page.click("a[href='/tools/create']")

        # Wait for editor to be ready
        editor = test_page.locator("#code-editor")
        expect(editor).to_be_visible()

        # Select React type
        test_page.select_option("#tool_type", "react")

        # Type JSX code
        ace_textarea = test_page.locator("#code-editor textarea.ace_text-input")
        ace_textarea.focus()
        test_page.keyboard.type("const App = () => <div>Hello</div>")

        # JSX mode should highlight const as keyword
        expect(test_page.locator("#code-editor .ace_keyword")).to_be_visible()

    def test_editor_loads_on_edit_page(self, test_page: Page, live_server: str) -> None:
        """Ace Editor should load on edit page with existing content."""
        # First create a tool
        test_page.click("a[href='/tools/create']")
        test_page.fill("#name", "Editor Test Tool")
        ace_textarea = test_page.locator("#code-editor textarea.ace_text-input")
        ace_textarea.focus()
        test_page.keyboard.type("<h1>Test Content</h1>")
        test_page.click("#submit-btn")
        expect(test_page.locator("#message")).to_contain_text("作成しました")

        # Navigate to edit page
        test_page.click("#message a[href^='/tools/view/']")
        test_page.click("a[href^='/tools/edit/']")

        # Wait for Ace Editor to initialize on edit page
        editor = test_page.locator("#code-editor-edit")
        expect(editor).to_be_visible()

        # Verify existing content is loaded (check for syntax highlighting)
        expect(test_page.locator("#code-editor-edit .ace_tag-name").first).to_be_visible()
