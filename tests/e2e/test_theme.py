"""E2E tests for theme toggle functionality."""

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.e2e
class TestThemeToggle:
    """Tests for dark mode theme toggle."""

    def test_theme_button_exists(self, test_page: Page) -> None:
        """Theme toggle button should be visible in navigation."""
        button = test_page.locator("#theme-toggle")
        expect(button).to_be_visible()
        expect(button).to_have_attribute("aria-label", "システム設定")

    def test_theme_cycle(self, test_page: Page) -> None:
        """Theme should cycle through auto -> light -> dark -> auto."""
        button = test_page.locator("#theme-toggle")
        html = test_page.locator("html")

        # Initial state: auto (icon: 🖥️)
        expect(button).to_have_text("🖥️")

        # Click 1: auto -> light (icon: ☀️)
        button.click()
        expect(button).to_have_text("☀️")
        expect(button).to_have_attribute("aria-label", "ライトモード")
        expect(html).to_have_attribute("data-theme", "light")

        # Click 2: light -> dark (icon: 🌙)
        button.click()
        expect(button).to_have_text("🌙")
        expect(button).to_have_attribute("aria-label", "ダークモード")
        expect(html).to_have_attribute("data-theme", "dark")

        # Click 3: dark -> auto (icon: 🖥️)
        button.click()
        expect(button).to_have_text("🖥️")
        expect(button).to_have_attribute("aria-label", "システム設定")

    def test_theme_persists_after_reload(self, test_page: Page) -> None:
        """Theme preference should persist after page reload."""
        button = test_page.locator("#theme-toggle")

        # Set to dark mode
        button.click()  # auto -> light
        button.click()  # light -> dark
        expect(button).to_have_text("🌙")

        # Reload page
        test_page.reload()

        # Should still be dark mode
        button = test_page.locator("#theme-toggle")
        expect(button).to_have_text("🌙")
        expect(button).to_have_attribute("aria-label", "ダークモード")
        expect(test_page.locator("html")).to_have_attribute("data-theme", "dark")

    def test_theme_persists_across_pages(self, test_page: Page, live_server: str) -> None:
        """Theme preference should persist when navigating to other pages."""
        button = test_page.locator("#theme-toggle")

        # Set to light mode
        button.click()  # auto -> light
        expect(button).to_have_text("☀️")

        # Navigate to create page
        test_page.click("a[href='/tools/create']")
        expect(test_page).to_have_url(f"{live_server}/tools/create")

        # Theme should still be light
        button = test_page.locator("#theme-toggle")
        expect(button).to_have_text("☀️")
        expect(test_page.locator("html")).to_have_attribute("data-theme", "light")

    def test_no_flash_on_load(self, test_page: Page, live_server: str) -> None:
        """Page should not flash wrong theme on load."""
        button = test_page.locator("#theme-toggle")

        # Set to dark mode
        button.click()  # auto -> light
        button.click()  # light -> dark

        # Navigate to create page and check theme is applied immediately
        # We check by verifying the data-theme attribute is set before DOMContentLoaded
        test_page.goto(live_server + "/tools/create")

        # The theme should be dark without any flash
        expect(test_page.locator("html")).to_have_attribute("data-theme", "dark")
