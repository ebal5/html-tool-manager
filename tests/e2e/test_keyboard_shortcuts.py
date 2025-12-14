"""E2E tests for keyboard shortcuts."""

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.e2e
class TestCommandPalette:
    """Tests for command palette."""

    def test_ctrl_k_opens_command_palette(self, test_page: Page) -> None:
        """Ctrl+K should open command palette."""
        test_page.keyboard.press("Control+k")
        expect(test_page.locator("#command-palette")).to_be_visible()

    def test_escape_closes_command_palette(self, test_page: Page) -> None:
        """Escape should close command palette."""
        test_page.keyboard.press("Control+k")
        expect(test_page.locator("#command-palette")).to_be_visible()
        test_page.keyboard.press("Escape")
        expect(test_page.locator("#command-palette")).not_to_be_visible()

    def test_close_button_closes_command_palette(self, test_page: Page) -> None:
        """Close button should close command palette."""
        test_page.keyboard.press("Control+k")
        expect(test_page.locator("#command-palette")).to_be_visible()
        test_page.click("#command-palette [data-close-modal]")
        expect(test_page.locator("#command-palette")).not_to_be_visible()

    def test_command_palette_search(self, test_page: Page, live_server: str) -> None:
        """Command palette should search tools."""
        # First create a tool
        test_page.click("a[href='/tools/create']")
        test_page.fill("#name", "Searchable Tool")
        ace_textarea = test_page.locator("#code-editor textarea.ace_text-input")
        ace_textarea.focus()
        test_page.keyboard.type("<p>Content</p>")
        test_page.click("#submit-btn")
        expect(test_page.locator("#message")).to_contain_text("作成しました")

        # Go back to home
        test_page.goto(live_server)

        # Open command palette and search
        test_page.keyboard.press("Control+k")
        expect(test_page.locator("#command-palette")).to_be_visible()
        test_page.fill("#command-palette-search", "Searchable")

        # Wait for search results
        expect(test_page.locator("#command-palette-results li .tool-name")).to_contain_text("Searchable Tool")

    def test_command_palette_keyboard_navigation(self, test_page: Page, live_server: str) -> None:
        """Command palette should support keyboard navigation."""
        import re

        # Create two tools for navigation test
        for name in ["Nav Tool One", "Nav Tool Two"]:
            test_page.goto(f"{live_server}/tools/create")
            test_page.fill("#name", name)
            ace_textarea = test_page.locator("#code-editor textarea.ace_text-input")
            ace_textarea.focus()
            test_page.keyboard.type("<p>Content</p>")
            test_page.click("#submit-btn")
            expect(test_page.locator("#message")).to_contain_text("作成しました")

        # Go back to home
        test_page.goto(live_server)

        # Open command palette and search
        test_page.keyboard.press("Control+k")
        expect(test_page.locator("#command-palette")).to_be_visible()
        test_page.fill("#command-palette-search", "Nav Tool")

        # Wait for results
        expect(test_page.locator("#command-palette-results li")).to_have_count(2)

        # Navigate down with arrow key
        test_page.keyboard.press("ArrowDown")
        expect(test_page.locator("#command-palette-results li").first).to_have_attribute("aria-selected", "true")

        # Navigate down again
        test_page.keyboard.press("ArrowDown")
        expect(test_page.locator("#command-palette-results li").nth(1)).to_have_attribute("aria-selected", "true")

        # Navigate up
        test_page.keyboard.press("ArrowUp")
        expect(test_page.locator("#command-palette-results li").first).to_have_attribute("aria-selected", "true")

        # Press Enter to navigate to the tool
        test_page.keyboard.press("Enter")
        expect(test_page).to_have_url(re.compile(r"/tools/view/\d+"))

    def test_command_palette_shows_hint_when_empty(self, test_page: Page) -> None:
        """Command palette should show hint when search is empty."""
        test_page.keyboard.press("Control+k")
        expect(test_page.locator("#command-palette")).to_be_visible()

        # Should show hint message
        expect(test_page.locator("#command-palette-results li.hint")).to_be_visible()
        expect(test_page.locator("#command-palette-results li.hint")).to_contain_text("キーワードを入力して検索")


@pytest.mark.e2e
class TestHelpModal:
    """Tests for help modal."""

    def test_ctrl_slash_opens_help(self, test_page: Page) -> None:
        """Ctrl+/ should open help modal."""
        test_page.keyboard.press("Control+/")
        expect(test_page.locator("#help-modal")).to_be_visible()

    def test_escape_closes_help(self, test_page: Page) -> None:
        """Escape should close help modal."""
        test_page.keyboard.press("Control+/")
        expect(test_page.locator("#help-modal")).to_be_visible()
        test_page.keyboard.press("Escape")
        expect(test_page.locator("#help-modal")).not_to_be_visible()

    def test_ctrl_slash_toggles_help(self, test_page: Page) -> None:
        """Ctrl+/ should toggle help modal."""
        # Open
        test_page.keyboard.press("Control+/")
        expect(test_page.locator("#help-modal")).to_be_visible()
        # Close
        test_page.keyboard.press("Control+/")
        expect(test_page.locator("#help-modal")).not_to_be_visible()

    def test_help_modal_shows_shortcuts(self, test_page: Page) -> None:
        """Help modal should display shortcut list."""
        test_page.keyboard.press("Control+/")
        expect(test_page.locator("#help-modal")).to_be_visible()
        expect(test_page.locator("#shortcut-list")).to_be_visible()
        # Check for at least one shortcut entry
        expect(test_page.locator("#shortcut-list tr").first).to_be_visible()


@pytest.mark.e2e
class TestNavigationShortcuts:
    """Tests for navigation shortcuts."""

    def test_ctrl_n_navigates_to_create(self, test_page: Page, live_server: str) -> None:
        """Ctrl+N should navigate to create page."""
        test_page.keyboard.press("Control+n")
        expect(test_page).to_have_url(f"{live_server}/tools/create")

    def test_ctrl_e_navigates_to_edit_from_view(self, test_page: Page, live_server: str) -> None:
        """Ctrl+E should navigate to edit page from view page."""
        import re

        # First create a tool
        test_page.click("a[href='/tools/create']")
        test_page.fill("#name", "Edit Test Tool")
        ace_textarea = test_page.locator("#code-editor textarea.ace_text-input")
        ace_textarea.focus()
        test_page.keyboard.type("<p>Content</p>")
        test_page.click("#submit-btn")
        expect(test_page.locator("#message")).to_contain_text("作成しました")

        # Navigate to view page
        test_page.click("#message a[href^='/tools/view/']")
        expect(test_page).to_have_url(re.compile(r"/tools/view/\d+"))

        # Use Ctrl+E to go to edit
        test_page.keyboard.press("Control+e")
        expect(test_page).to_have_url(re.compile(r"/tools/edit/\d+"))


@pytest.mark.e2e
class TestFormShortcuts:
    """Tests for form shortcuts."""

    def test_ctrl_s_submits_form(self, test_page: Page, live_server: str) -> None:
        """Ctrl+S should submit the form on create page."""
        test_page.goto(f"{live_server}/tools/create")

        # Fill form
        test_page.fill("#name", "Shortcut Save Tool")
        test_page.fill("#description", "Created with Ctrl+S")
        ace_textarea = test_page.locator("#code-editor textarea.ace_text-input")
        ace_textarea.focus()
        test_page.keyboard.type("<p>Saved with shortcut</p>")

        # Use Ctrl+S to submit
        test_page.keyboard.press("Control+s")

        # Wait for success message
        expect(test_page.locator("#message")).to_contain_text("作成しました")

    def test_ctrl_n_blocked_on_create_page(self, test_page: Page, live_server: str) -> None:
        """Ctrl+N should not navigate away from create page."""
        test_page.goto(f"{live_server}/tools/create")
        test_page.keyboard.press("Control+n")
        # Should still be on create page
        expect(test_page).to_have_url(f"{live_server}/tools/create")
