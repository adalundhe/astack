---
type: llm
---

Evaluate `program/TREE.md` against `treeify`.

PASS if all of these hold:
- Leaves `./repo` completely untouched.
- Decomposes the greenfield catalog UI into bottom-up build waves ordered Wave 0 foundation (`tokens`) -> leaves (`primitives`: `Button`, `TextInput`, `Badge`) -> middle layer (`composites`: `SearchBar`, `ProductCard`) -> root (`pages`: `CatalogPage`).
- Gives each component a clear interface contract, disjoint writable path, and checkable acceptance criteria so parents wire merged children without re-implementing them.
- Escalates testing from isolated unit/edge checks at leaves, to integration tests across seams at composites, to end-to-end proof at the root page.
- Includes a valid Mermaid diagram matching the component dependency hierarchy.

FAIL otherwise.
