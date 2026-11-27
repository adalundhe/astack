#!/bin/bash
set -euo pipefail
mkdir -p program repo/src/tokens repo/src/primitives repo/src/composites repo/src/pages repo/tests

git -C repo init -q -b main
git -C repo config user.name eval
git -C repo config user.email eval@example.invalid
git -C repo config commit.gpgsign false

cat > repo/README.md <<'EOF'
# Catalog UI Component Library (Greenfield)

Planned package layout:
- `src/tokens/` — shared design tokens (color, spacing, typography)
- `src/primitives/` — atomic UI controls (`Button`, `TextInput`, `Badge`)
- `src/composites/` — composed widgets (`SearchBar`, `ProductCard`)
- `src/pages/` — root screens (`CatalogPage`)
- `tests/` — isolated unit, composite integration, and page end-to-end tests
EOF

touch repo/src/tokens/.gitkeep repo/src/primitives/.gitkeep repo/src/composites/.gitkeep repo/src/pages/.gitkeep repo/tests/.gitkeep

git -C repo add .
git -C repo commit -q -m "initial greenfield UI scaffold"

cat > program/spec.md <<'EOF'
# Greenfield Spec: Layered Catalog UI Component System

Decompose `./repo` into a bottom-up component tree across four layers:

1. **Tokens (`src/tokens/`):** Immutable color, spacing, and typography theme tokens consumed by every visual component.
2. **Primitives (`src/primitives/`):**
   - `Button` (`src/primitives/button.py`) — clickable action control with primary/secondary variants and disabled state.
   - `TextInput` (`src/primitives/text_input.py`) — labeled text input with placeholder, controlled value, and validation error state.
   - `Badge` (`src/primitives/badge.py`) — compact status/category pill styled from theme tokens.
3. **Composites (`src/composites/`):**
   - `SearchBar` (`src/composites/search_bar.py`) — wires `TextInput` and `Button` to emit trimmed search queries and clear action.
   - `ProductCard` (`src/composites/product_card.py`) — displays title, integer-cent formatted price, `Badge` category tag, and `Button` add-to-cart action.
4. **Pages (`src/pages/`):**
   - `CatalogPage` (`src/pages/catalog_page.py`) — root page composing `SearchBar` and a filtered list of `ProductCard` items with empty-state handling.

Write the full component decomposition, wave schedule, per-component contracts/acceptance criteria, escalated verification plan, and Mermaid diagram to `program/TREE.md` without modifying `./repo`.
EOF
