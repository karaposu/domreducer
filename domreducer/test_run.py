# test_run.py
# to run: python -m domreducer.test_run

from .reducer import HtmlReducer
import sys, pathlib

# a custom pipeline that includes all the new stages
_EXTRA_PIPE = [
    "parse_the_full_dom_into_a_dom_tree",
    "strip_out_non_structural_nodes",
    "strip_out_non_visual_nodes",
    "simplify_attributes",
    "strip_tailwind_utility_classes",
    "collapse_deeply_nested_container_with_one_child",
    "prune_repetitive_and_boilerplate_navigation_items",
    "preserve_tables_as_markdown",
    "drop_row_ids_inside_large_tables",
    "reduce_large_inline_SVGs_or_images_to_lightweight_placeholders",
    "minify_whitespace",
]

def main():
    # choose one of your test files here
    html_file = 'domreducer/testdoms/html/budgety-ai.html'
    sample_html = pathlib.Path(html_file).read_text()
    
    # create the reducer and run the pipeline
    reducer = HtmlReducer(sample_html)
    op = reducer.reduce(_EXTRA_PIPE)

    # always show the raw input
    print("\n=== RAW HTML ===\n")
    print(op.raw_data)

    # handle abort / error
    if not op.success:
        if op.js_method_needed:
            print("\n⚠️  Detected a JS-only shell; you’ll need to fetch with a browser-enabled reducer.")
        else:
            print("\n❌ Reduction error:", op.error)
        sys.exit(1)

    # otherwise, show the reduced output
    reduced = op.reduced_data or ""
    print("\n=== REDUCED HTML ===\n")
    print(reduced)

    # summary stats
    print("\n=== SUMMARY ===")
    print(f" original chars: {op.total_char}")
    print(f" original tokens: {op.total_token}")
    reduced_chars = len(reduced)
    reduced_tokens = len(reducer.encoding.encode(reduced))
    print(f" reduced chars : {reduced_chars}")
    print(f" reduced tokens: {reduced_tokens}")

    # per-step deltas
    print("\n=== PER-STEP Δchars / Δtokens ===")
    for step, stats in op.reducement_details.items():
        dc = stats["delta_chars"]
        dt = stats["delta_tokens"]
        print(f" • {step:40s}  Δchars={dc:5d}, Δtokens={dt:5d}")

if __name__ == "__main__":
    main()
