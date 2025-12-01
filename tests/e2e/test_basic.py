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
        test_page.fill("#html_content", "<p>Hello E2E!</p>")

        # Submit
        test_page.click("#submit-btn")

        # Wait for success message
        expect(test_page.locator("#message")).to_contain_text("を作成しました")

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
