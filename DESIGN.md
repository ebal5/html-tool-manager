# Design Document: HTML Tool Manager

## 1. Introduction

This document outlines the design principles, visual style, and component architecture for the HTML Tool Manager application. The goal is to maintain a clean, consistent, and user-friendly interface.

The application's core concept is a no-frills internal dashboard for developers to quickly manage and use single-page HTML/JS tools. The design prioritizes functionality and ease of use over complex visual flair.

## 2. Design Principles

- **Simplicity:** The UI is built upon a class-less CSS framework ([Pico.css](https://picocss.com/)) to keep the HTML structure clean and semantic. We avoid complex, custom CSS wherever possible.
- **Consistency:** All pages share a common layout, navigation structure, and component styling. Buttons, forms, and tables look and behave predictably across the application.
- **Responsiveness:** The design is fluid and adapts gracefully to various screen sizes, from mobile devices to large desktop monitors, thanks to Pico.css's responsive grid system and components.

## 3. Color Scheme

The color palette is inherited directly from Pico.css's default theme (in its auto-switching light/dark mode).

- **Primary Color:** A neutral, typically dark grey or blue, used for primary actions and highlights.
- **Secondary Color:** A lighter grey, used for secondary actions.
- **Contrast Color:** A distinct color used for destructive actions (e.g., the "Delete" button) to draw user attention.
- **Text Color:** High-contrast dark grey (light mode) or light grey (dark mode) for readability.
- **Background Color:** A light off-white (light mode) or a very dark grey (dark mode).

## 4. Typography

- **Font Family:** The application uses a system font stack, which defaults to the native font of the user's operating system (e.g., San Francisco on macOS, Segoe UI on Windows). This ensures fast loading times and a familiar look and feel.
- **Hierarchy:**
  - `<h1>`, `<h2>`: Used for main page titles and section headers.
  - `<p>`, `<td>`: Standard body text.
  - `<label>`, `<small>`: Used in forms to label inputs and provide help text.
  - `<code>`: Used to display tags and code-like text in a monospaced font.

## 5. Components

### Navigation Bar (`<nav>`)
A simple, persistent header containing the application title and primary navigation links ("Home", "Create New Tool").

### Buttons (`<button>`, `<a role="button">`)
- **Primary Action (Default Button):** Used for the main submission action on a page (e.g., "Create Tool", "Update Tool").
- **Secondary (`.secondary`):** Used for less critical, non-disruptive actions (e.g., "Edit").
- **Secondary Outline (`.secondary.outline`):** Used for the most common, non-primary action, like "Use".
- **Contrast (`.contrast.outline` or `.contrast`):** Reserved for potentially destructive actions. In this app, it is used for the "Delete" button trigger (`⋮`) and the button itself.

### Forms
Standard HTML form elements (`<input>`, `<textarea>`, `<select>`, `<fieldset>`) are styled by Pico.css to be clean and legible. Labels are placed above their corresponding inputs.

### Table (`<table>`)
The tool list is displayed in a standard table, providing a structured and scannable overview of all tools.

### Dropdown / Accordion (`<details>`)
The `<details>` and `<summary>` elements are used to create a compact dropdown menu for "Edit" and "Delete" actions, cleaning up the UI in the actions column of the tool list.

### Article (`<article>`)
Content-heavy pages like the "Create" and "Edit" forms are wrapped in an `<article>` tag, which provides a visually distinct container with a subtle border and padding.

## 6. Layout

- **Main Container (`<main class="container">`):** The primary layout container, which centers the content and constrains its maximum width for better readability on large screens.
- **Grid (`<div class="grid">`):** Used to create simple, responsive column layouts, such as for the search/sort bar and the action buttons.

## 7. Future Improvements

- **Custom Logo:** A simple logo could be added to the navigation bar to give the application a unique identity.
- **Theme Toggle:** While Pico.css supports auto-switching, an explicit light/dark mode toggle could be added for user convenience.
- **Tag Cloud:** The previously-discussed tag cloud feature could be implemented with a design that fits the minimalist aesthetic (e.g., a simple list of `<code>` tags).
