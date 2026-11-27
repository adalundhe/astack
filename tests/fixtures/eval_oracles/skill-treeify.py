"""Separated offline oracle for `skill-treeify`."""
from __future__ import annotations

from pathlib import Path

TREE_CONTENT = """# Component Build Tree: Layered Catalog UI

## Goal & Out of Scope
Deliver a layered catalog UI built bottom-up from frozen tokens through atomic primitives and composed widgets to `CatalogPage`. Out of scope: backend HTTP fetching and checkout persistence.

## Component Dependency Diagram

```mermaid
flowchart BT
  Tokens[Wave 0: Tokens] --> Button[Wave 1: Button]
  Tokens --> TextInput[Wave 1: TextInput]
  Tokens --> Badge[Wave 1: Badge]
  TextInput --> SearchBar[Wave 2: SearchBar]
  Button --> SearchBar
  Badge --> ProductCard[Wave 2: ProductCard]
  Button --> ProductCard
  SearchBar --> CatalogPage[Wave 3: CatalogPage]
  ProductCard --> CatalogPage
```

## Wave 0 — Foundation Leaf: `tokens`

### Tokens (`src/tokens/theme.py`)
- **Layer:** Wave 0 foundation leaf (must clear review and merge before Wave 1 starts so primitives share one frozen schema).
- **Writable paths:** `src/tokens/theme.py`, `tests/test_tokens.py`
- **Contract:** Frozen `ThemeTokens` dataclass exposing `colors`, `spacing`, and `typography` immutable mappings.
- **Acceptance criteria:** All token groups are immutable, non-empty, and validated at construction; invalid hex colors or negative spacing raise `ValueError`.
- **Tests:** Isolated unit and boundary checks validating immutability and rejection of malformed token values.

## Wave 1 — Atomic Leaves: `primitives` (parallel)

### Button (`src/primitives/button.py`)
- **Layer:** Leaf primitive (parallel with `TextInput` and `Badge`).
- **Writable paths:** `src/primitives/button.py`, `tests/test_button.py`
- **Contract:** `render_button(label, variant="primary", disabled=False, theme=DEFAULT_THEME)` returning a structured render node.
- **Acceptance criteria:** Supports `"primary"` and `"secondary"` variants styled from `ThemeTokens`; disabled buttons suppress click handler dispatch; unknown variants raise `ValueError`.
- **Tests:** Isolated unit tests covering variant styling, disabled click suppression, and invalid variant error handling.

### TextInput (`src/primitives/text_input.py`)
- **Layer:** Leaf primitive (parallel with `Button` and `Badge`).
- **Writable paths:** `src/primitives/text_input.py`, `tests/test_text_input.py`
- **Contract:** `render_text_input(label, value="", placeholder="", error=None, theme=DEFAULT_THEME)`.
- **Acceptance criteria:** Renders controlled value, binds label metadata, applies error styling when `error` is set, and rejects blank labels with `ValueError`.
- **Tests:** Isolated unit tests covering controlled values, placeholder fallback, error state rendering, and empty-label rejection.

### Badge (`src/primitives/badge.py`)
- **Layer:** Leaf primitive (parallel with `Button` and `TextInput`).
- **Writable paths:** `src/primitives/badge.py`, `tests/test_badge.py`
- **Contract:** `render_badge(text, tone="neutral", theme=DEFAULT_THEME)`.
- **Acceptance criteria:** Maps valid tones (`neutral`, `info`, `accent`) to theme palette entries and rejects empty text or unknown tones with `ValueError`.
- **Tests:** Isolated unit tests covering valid tones, empty text rejection, and token binding.

## Wave 2 — Middle Layer: `composites` (parallel after Wave 1 merges)

### SearchBar (`src/composites/search_bar.py`)
- **Layer:** Composite (depends on merged `TextInput` and `Button`; parallel with `ProductCard`).
- **Writable paths:** `src/composites/search_bar.py`, `tests/test_search_bar.py`
- **Contract:** `SearchBar(on_search, on_clear)` composing `render_text_input` and `render_button` without re-implementing primitive controls.
- **Acceptance criteria:** Submitting whitespace-padded input emits a trimmed query; submitting empty input sets a validation error on `TextInput` instead of calling `on_search`; clicking clear resets the value and calls `on_clear`.
- **Tests:** Integration tests across `TextInput` and `Button` seams verifying query trimming, empty submission guard, and clear state reset.

### ProductCard (`src/composites/product_card.py`)
- **Layer:** Composite (depends on merged `Badge` and `Button`; parallel with `SearchBar`).
- **Writable paths:** `src/composites/product_card.py`, `tests/test_product_card.py`
- **Contract:** `ProductCard(item, on_add_to_cart)` composing `render_badge` for category and `render_button` for cart actions.
- **Acceptance criteria:** Formats integer `price_cents` accurately (e.g. `1999` -> `"$19.99"`), disables the add-to-cart `Button` when `in_stock` is `False`, and forwards `item.sku` when active.
- **Tests:** Integration tests across `Badge` and `Button` seams covering integer-cent formatting, out-of-stock button disablement, and action callbacks.

## Wave 3 — Root: `pages` (after Wave 2 merges)

### CatalogPage (`src/pages/catalog_page.py`)
- **Layer:** Root page (depends on merged `SearchBar` and `ProductCard`).
- **Writable paths:** `src/pages/catalog_page.py`, `tests/test_catalog_page.py`
- **Contract:** `CatalogPage(items, on_add_to_cart)` composing `SearchBar` and filtered `ProductCard` children.
- **Acceptance criteria:** Searching filters visible `ProductCard` nodes case-insensitively by title or category; zero matches display an explicit empty state; clearing restores the full catalog; add-to-cart events propagate item SKUs.
- **Tests:** End-to-end tests exercising the full token -> primitive -> composite -> page stack across search filtering, empty states, clearing, and cart selection.
"""


def apply(ws: Path) -> dict[str, object]:
    """Write program/TREE.md with bottom-up waves, per-component acceptance criteria, and Mermaid diagram."""
    (ws / "program" / "TREE.md").write_text(TREE_CONTENT, encoding="utf-8")
    return {
        "final_text": (
            "Wrote the bottom-up component tree to `program/TREE.md` ordered Wave 0 (`tokens`) -> "
            "Wave 1 (`primitives`) -> Wave 2 (`composites`) -> Wave 3 (`pages`), with disjoint "
            "writable paths, per-component acceptance criteria, escalated testing, and a Mermaid diagram. "
            "Left `./repo` untouched."
        ),
    }
