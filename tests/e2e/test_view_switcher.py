"""E2E tests for view switcher functionality."""

import re

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.e2e
class TestViewSwitcher:
    """Tests for view switcher (list/card/grid) functionality."""

    def test_view_buttons_exist(self, test_page: Page) -> None:
        """View switcher buttons should be visible."""
        expect(test_page.locator("#view-list")).to_be_visible()
        expect(test_page.locator("#view-card")).to_be_visible()
        expect(test_page.locator("#view-grid")).to_be_visible()

    def test_list_view_default(self, test_page: Page) -> None:
        """List view should be the default view."""
        # List button should be active by default
        list_btn = test_page.locator("#view-list")
        expect(list_btn).to_have_class(re.compile(r"active"))
        expect(list_btn).to_have_attribute("aria-pressed", "true")

    def test_switch_to_card_view(self, test_page: Page, live_server: str) -> None:
        """Clicking card view button should switch to card view."""
        # Create a test tool first
        self._create_test_tool(test_page, live_server)

        # Navigate back to home
        test_page.goto(live_server)

        # Click card view button
        card_btn = test_page.locator("#view-card")
        card_btn.click()

        # Card view container should be visible
        expect(test_page.locator(".tools-card-view")).to_be_visible()
        expect(card_btn).to_have_class(re.compile(r"active"))
        expect(card_btn).to_have_attribute("aria-pressed", "true")

    def test_switch_to_grid_view(self, test_page: Page, live_server: str) -> None:
        """Clicking grid view button should switch to grid view."""
        # Create a test tool first
        self._create_test_tool(test_page, live_server)

        # Navigate back to home
        test_page.goto(live_server)

        # Click grid view button
        grid_btn = test_page.locator("#view-grid")
        grid_btn.click()

        # Grid view container should be visible
        expect(test_page.locator(".tools-grid-view")).to_be_visible()
        expect(grid_btn).to_have_class(re.compile(r"active"))
        expect(grid_btn).to_have_attribute("aria-pressed", "true")

    def test_view_persists_in_localstorage(self, test_page: Page, live_server: str) -> None:
        """View preference should be saved in localStorage."""
        # Create a test tool first
        self._create_test_tool(test_page, live_server)

        # Navigate back to home
        test_page.goto(live_server)

        # Switch to card view
        test_page.locator("#view-card").click()
        expect(test_page.locator(".tools-card-view")).to_be_visible()

        # Reload page
        test_page.reload()

        # Card view should still be selected
        expect(test_page.locator(".tools-card-view")).to_be_visible()
        expect(test_page.locator("#view-card")).to_have_class(re.compile(r"active"))

    def test_grid_item_keyboard_navigation(self, test_page: Page, live_server: str) -> None:
        """Grid items should be keyboard accessible."""
        # Create a test tool first
        self._create_test_tool(test_page, live_server)

        # Navigate back to home
        test_page.goto(live_server)

        # Switch to grid view
        test_page.locator("#view-grid").click()
        expect(test_page.locator(".tools-grid-view")).to_be_visible()

        # Grid item should have tabindex
        grid_item = test_page.locator(".tool-grid-item").first
        expect(grid_item).to_have_attribute("tabindex", "0")
        expect(grid_item).to_have_attribute("role", "button")

    def test_select_all_in_card_view(self, test_page: Page, live_server: str) -> None:
        """Select all checkbox should work in card view."""
        # Create a test tool first
        self._create_test_tool(test_page, live_server)

        # Navigate back to home
        test_page.goto(live_server)

        # Show tool operations
        test_page.locator("#toggle-tool-operations").click()

        # Switch to card view
        test_page.locator("#view-card").click()
        expect(test_page.locator(".tools-card-view")).to_be_visible()

        # Select all checkbox should be visible
        select_all = test_page.locator("#select-all-tools")
        expect(select_all).to_be_visible()

        # Click select all
        select_all.click()

        # Tool checkboxes should be checked
        tool_checkbox = test_page.locator(".tool-checkbox").first
        expect(tool_checkbox).to_be_checked()

    def test_select_all_in_grid_view(self, test_page: Page, live_server: str) -> None:
        """Select all checkbox should work in grid view."""
        # Create a test tool first
        self._create_test_tool(test_page, live_server)

        # Navigate back to home
        test_page.goto(live_server)

        # Show tool operations
        test_page.locator("#toggle-tool-operations").click()

        # Switch to grid view
        test_page.locator("#view-grid").click()
        expect(test_page.locator(".tools-grid-view")).to_be_visible()

        # Select all checkbox should be visible
        select_all = test_page.locator("#select-all-tools")
        expect(select_all).to_be_visible()

        # Click select all
        select_all.click()

        # Tool checkboxes should be checked
        tool_checkbox = test_page.locator(".tool-checkbox").first
        expect(tool_checkbox).to_be_checked()

    def _create_test_tool(self, page: Page, live_server: str) -> None:
        """Create a test tool for testing."""
        page.goto(f"{live_server}/tools/create")
        page.fill("#name", "View Test Tool")
        page.fill("#description", "Test Description")

        ace_textarea = page.locator("#code-editor textarea.ace_text-input")
        ace_textarea.focus()
        page.keyboard.type("<p>Hello!</p>")

        page.click("#submit-btn")
        expect(page.locator("#message")).to_contain_text("作成しました")
