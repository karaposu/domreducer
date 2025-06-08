# domreducer

`domreducer` is a Python library for programmatically stripping down and sanitizing HTML documents into a minimal, text-focused form. It’s perfect for preparing web pages for LLM ingestion, text analysis, or any context where you only need the essential structural content.

---

## Features

* **Parse** a full HTML document into a DOM tree.
* **Strip** out non-structural nodes (scripts, style blocks, comments).
* **Strip** out non-visual nodes (invisible elements, metadata).
* **Simplify** attributes (remove inline styles, classes, IDs where possible).
* **Collapse** deeply nested single-child containers.
* **Prune** repetitive or boilerplate navigation/footer elements.
* **Reduce** large inline SVGs or images to lightweight placeholders.
* **Preserve** tables, definition lists, lists, figures, and CSS-styled tables as Markdown.
* **Detect** single-page app “JS shells” and abort reduction so you can fall back to a JS-enabled fetch.
* **Minify** remaining whitespace.

All steps are tracked in a `ReduceOperation` result, which includes before/after sizes, token counts, and any reasons for aborting.

---

## Installation

```bash
pip install domreducer
```

---

## Quickstart

```python
from domreducer import HtmlReducer

raw_html = "<html>…your full page…</html>"

# Run the full reduction pipeline (aborts if a JS shell is detected)
op = HtmlReducer(raw_html).reduce()

if not op.success:
    print("Reduction aborted:", op.error or op.js_method_needed)
else:
    print("Original size:", op.total_char, "chars")
    print("Reduced size:", op.reduced_char, "chars")
    print("Steps details:", op.reduction_details)
    clean_html = op.reduced_data
    # …use clean_html…
```

### Custom Pipeline

Choose only the steps you want or disable JS-shell abort:

```python
op = HtmlReducer(raw_html).reduce(
    order=[
        "parse_the_full_dom_into_a_dom_tree",
        "strip_out_non_structural_nodes",
        "simplify_attributes",
        "minify_whitespace",
    ],
    abort_on_js_shell=False,
)
```

---

## API Reference

### `HtmlReducer(html: str)`

Constructor takes your raw HTML string.

#### `.reduce(order: List[str] = None, abort_on_js_shell: bool = True) → ReduceOperation`

* **order**: list of step names (in the order to apply). Defaults to the full pipeline.
* **abort\_on\_js\_shell**: if `True`, calls `.is_probably_js_shell()` after parsing and returns an aborted `ReduceOperation`.

Available steps (in pipeline order):

1. `parse_the_full_dom_into_a_dom_tree`
2. `strip_out_non_structural_nodes`
3. `strip_out_non_visual_nodes`
4. `simplify_attributes`
5. `collapse_deeply_nested_container_with_one_child`
6. `prune_repetitive_and_boilerplate_navigation_items`
7. `reduce_large_inline_SVGs_or_images_to_lightweight_placeholders`
8. `preserve_tables_as_markdown`
9. `preserve_deflists_as_markdown`
10. `preserve_lists_as_markdown`
11. `preserve_figures_as_markdown`
12. `preserve_css_tables_as_markdown`
13. `strip_tailwind_utility_classes`
14. `drop_row_ids_inside_large_tables`
15. `minify_whitespace`

---

### `ReduceOperation`

The object returned by `.reduce()`, with attributes:

* `success: bool` — `True` if reduction ran through; `False` if aborted (e.g. JS shell) or error.
* `error: Optional[str]` — any error message.
* `js_method_needed: bool` — `True` if aborted due to JS-shell detection.
* `total_char: int` — character length before reduction.
* `total_token: int` — approximate token count before reduction.
* `reduced_char: int` — character length after reduction.
* `reduced_token: int` — approximate token count after reduction.
* `raw_data: str` — original HTML.
* `reduced_data: str` — the cleaned, reduced HTML.
* `reduction_details: dict` — per-step Δchars/Δtokens, and any flags like `"aborted": "js_shell_detected"`.

---

## Contributing

1. Fork the repo
2. Create your feature branch (`git checkout -b my-feature`)
3. Commit your changes (`git commit -am 'Add feature'`)
4. Push to the branch (`git push origin my-feature`)
5. Open a Pull Request

---

