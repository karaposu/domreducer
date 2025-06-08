from .reducer import HtmlReducer
import sys, textwrap, pathlib


_EXTRA_PIPE = [
    "parse_the_full_dom_into_a_dom_tree",
    "strip_out_non_structural_nodes",
    "strip_out_non_visual_nodes",
    "simplify_attributes",
    "strip_tailwind_utility_classes",          # ← NEW
    "collapse_deeply_nested_container_with_one_child",
    "prune_repetitive_and_boilerplate_navigation_items",
    "preserve_tables_as_markdown",             # ← NEW  (or top-N variant)
    "drop_row_ids_inside_large_tables",        # ← NEW
    "reduce_large_inline_SVGs_or_images_to_lightweight_placeholders",
    "minify_whitespace",                       # ← optional
]

# sample_html = pathlib.Path(__file__).with_suffix(".html").read_text() if len(sys.argv) > 1 else """
#     <html><head><style>.x{display:none}</style></head>
#     <body>
#         <div><div><span id='t' style="display:none">invisible</span>
#             <svg width="800" height="600"><circle cx="50" cy="50" r="40"/></svg>
#             <nav><ul><li>home</li><li>about</li></ul></nav>
#             <nav><ul><li>home</li><li>about</li></ul></nav>
#         </div></div>
#     </body></html>
# """


html_file = 'domreducer/testdoms/html/budgety-ai.html'  
# html_file = 'domreducer/testdoms/html/allaboutcircuits-article.html'  
# html_file = 'domreducer/testdoms/html/eetech.html'
# html_file = 'domreducer/testdoms/html/worldometers-world-population.html'

sample_html = pathlib.Path(html_file).read_text()  


reducer = HtmlReducer(sample_html).reduce(_EXTRA_PIPE)

reduced_version=reducer.to_html()

print("here is reduced version: ")
print(reduced_version)
print(" reduced version finihed ")
print("total_char_len: ", reducer.total_char_len, "total toke: ",reducer.raw_token_size )
print("reduced len: ", reducer.reduced_char_len, "reduced token size:", reducer.reduced_token_size)



for step, stats in reducer.reducement_details.items():
        print(f" • {step:40s}  Δchars={stats['char_delta']:5d}, Δtokens={stats['token_delta']:5d}")





print( "  ")
print( "here is raw version: ")
print( "  ")

print( reducer.raw_html)
print( "  ")

print( "here is reduced version: ")
print( "  ")

# print( cleaner.to_html())