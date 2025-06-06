from __future__ import annotations
from bs4 import BeautifulSoup, Comment
import hashlib
import re
from typing import List, Callable, Optional


class HtmlReducer:
    """
    A lightweight, chain-friendly utility that whittles down raw HTML while
    preserving layout-critical structure.  Each mutator returns `self`.
    """

    # --- life-cycle ---------------------------------------------------------

    def __init__(self, raw_html: str) -> None:
        self.raw_html: str = raw_html
        self.dom_tree: Optional[BeautifulSoup] = None

    # --- helpers -----------------------------------------------------------

    def _assert_parsed(self) -> None:
        if self.dom_tree is None:
            raise RuntimeError("Call parse_the_full_dom_into_a_dom_tree() first")

    def _walk(self):
        """Generator that yields every tag in document order."""
        for tag in self.dom_tree.find_all(True):      # True == any tag
            yield tag

    def to_html(self) -> str:
        """Return the current HTML as a compact string."""
        self._assert_parsed()
        return self.dom_tree.encode(formatter="html").decode()

    # --- pipeline stages ---------------------------------------------------

    def parse_the_full_dom_into_a_dom_tree(self) -> "HtmlReducer":
        """Parse raw HTML and attach BeautifulSoup DOM."""
        self.dom_tree = BeautifulSoup(self.raw_html, "lxml")
        return self

    # ----------------------------------------------------------------------

    def strip_out_non_structural_nodes(self) -> "HtmlReducer":
        """
        Remove obvious non-structural clutter (comments, script/style etc.).
        These rarely matter for visual spatial reasoning.
        """
        self._assert_parsed()

        # Comments
        for comment in self.dom_tree.find_all(text=lambda txt: isinstance(txt, Comment)):
            comment.extract()

        # Tags that never affect layout directly
        for tag in self.dom_tree(["script", "noscript", "style", "iframe", "meta", "link"]):
            tag.decompose()

        return self

    # ----------------------------------------------------------------------

    def strip_out_non_visual_nodes(self) -> "HtmlReducer":
        """
        Remove tags that are invisible and have no box (e.g. empty spans, elements
        with display:none or hidden attributes).
        """
        self._assert_parsed()

        css_hidden = re.compile(r"display\s*:\s*none", re.I)

        for tag in list(self._walk()):
            hidden_attr = (
                tag.has_attr("hidden")
                or tag.has_attr("aria-hidden") and tag["aria-hidden"] == "true"
                or tag.has_attr("style") and css_hidden.search(tag["style"] or "")
            )
            if hidden_attr and not tag.find_all(True):   # keep container if it has children
                tag.decompose()

        # Drop empty text-less inline containers
        for tag in list(self._walk()):
            if not tag.contents and tag.name in {"span", "b", "i", "u"}:
                tag.decompose()

        return self

    # ----------------------------------------------------------------------

    _ALLOWED_ATTRS = {"id", "class", "href", "src", "alt", "title", "role"}

    def simplify_attributes(self) -> "HtmlReducer":
        """
        Delete noisy attributes (tracking data-* props, inline event handlers etc.) but
        keep those required for spatial or semantic clues (class/id/src/…).
        """
        self._assert_parsed()

        for tag in self._walk():
            for attr in list(tag.attrs):
                if attr not in self._ALLOWED_ATTRS:
                    del tag[attr]

            # Trim class list if extremely long
            if "class" in tag.attrs and len(tag["class"]) > 6:
                tag["class"] = tag["class"][:6] + ["…"]

        return self

    # ----------------------------------------------------------------------

    def collapse_deeply_nested_container_with_one_child(self) -> "HtmlReducer":
        """
        Flatten chains of single-child containers (e.g., <div><div>…).
        Run a BFS and hoist grandchildren up when it’s safe.
        """
        self._assert_parsed()

        for tag in list(self._walk()):
            # Keep collapsing while current tag has exactly one element child
            while (
                len(tag.find_all(True, recursive=False)) == 1 and
                not tag.attrs and
                tag.name in {"div", "section", "article", "span"}
            ):
                only_child = tag.find(True, recursive=False)
                tag.unwrap()              # replace tag by its children
                tag = only_child          # continue collapsing downwards

        return self

    # ----------------------------------------------------------------------

    def prune_repetitive_and_boilerplate_navigation_items(self) -> "HtmlReducer":
        """
        Detect nav/ul lists repeated verbatim (e.g., footer + header menus) and
        keep only the first instance.
        """
        self._assert_parsed()
        seen_hashes = set()

        for nav in self.dom_tree.find_all(["nav", "ul", "ol"]):
            text_fingerprint = re.sub(r"\s+", " ", nav.get_text(strip=True).lower())
            h = hashlib.md5(text_fingerprint.encode()).hexdigest()
            if h in seen_hashes:
                nav.decompose()
            else:
                seen_hashes.add(h)

        return self

    # ----------------------------------------------------------------------

    _SVG_PLACEHOLDER = "<svg data-placeholder='1' width='{w}' height='{h}'></svg>"
    _IMG_PLACEHOLDER = "<img data-placeholder='1' width='{w}' height='{h}'/>"

    def reduce_large_inline_SVGs_or_images_to_lightweight_placeholders(self) -> "HtmlReducer":
        """
        Replace heavy <svg> or huge <img> payloads with stub elements containing
        only size metadata.
        """
        self._assert_parsed()

        # SVGs
        for svg in self.dom_tree.find_all("svg"):
            w = svg.get("width", "100%")
            h = svg.get("height", "100%")
            placeholder = BeautifulSoup(
                self._SVG_PLACEHOLDER.format(w=w, h=h), "lxml"
            )
            svg.replace_with(placeholder)

        # Images over a threshold (e.g. >100 kB via data URI or big dims)
        for img in self.dom_tree.find_all("img"):
            big_data_uri = img.get("src", "").startswith("data:image") and len(img["src"]) > 1500
            big_dims = (
                int(img.get("width", 0) or 0) * int(img.get("height", 0) or 0) > 512 * 512
            )
            if big_data_uri or big_dims:
                w = img.get("width", "auto")
                h = img.get("height", "auto")
                placeholder = BeautifulSoup(
                    self._IMG_PLACEHOLDER.format(w=w, h=h), "lxml"
                )
                img.replace_with(placeholder)

        return self
    

        def preserve_tables_as_markdown(self) -> "HtmlReducer":
        """
        Convert <table> elements into Markdown‐style tables, wrapped in a <pre data-table="1">…</pre> placeholder.
        """
        self._assert_parsed()
        from bs4 import NavigableString, Tag

        for table in list(self.dom_tree.find_all("table")):
            rows = table.find_all("tr")
            if not rows:
                continue

            # Extract cell texts into a 2D list
            table_data: List[List[str]] = []
            for tr in rows:
                cells = tr.find_all(["th", "td"])
                row_data = [
                    " ".join(cell.get_text(strip=True).split())
                    for cell in cells
                ]
                table_data.append(row_data)

            if not table_data:
                continue

            # Ensure all rows have the same number of columns
            max_cols = max(len(r) for r in table_data)
            for row in table_data:
                if len(row) < max_cols:
                    row.extend([""] * (max_cols - len(row)))

            md_lines: List[str] = []
            # If the first <tr> contains any <th>, treat it as the header row
            first_row_has_th = bool(rows[0].find_all("th"))
            if first_row_has_th:
                header = table_data[0]
                sep = ["---"] * max_cols
                md_lines.append("| " + " | ".join(header) + " |")
                md_lines.append("| " + " | ".join(sep) + " |")
                data_rows = table_data[1:]
            else:
                # No <th> detected: still treat the first row as header for Markdown
                header = table_data[0]
                sep = ["---"] * max_cols
                md_lines.append("| " + " | ".join(header) + " |")
                md_lines.append("| " + " | ".join(sep) + " |")
                data_rows = table_data[1:]

            for row in data_rows:
                md_lines.append("| " + " | ".join(row) + " |")

            md_blob = "\n".join(md_lines)
            pre = self.dom_tree.new_tag("pre", **{"data-table": "1"})
            pre.string = NavigableString(md_blob)
            table.replace_with(pre)

        return self


    def preserve_deflists_as_markdown(self) -> "HtmlReducer":
        """
        Turn <dl>…</dl> into a Markdown definition‐list stub, wrapped in <pre data-dl="1">…</pre>.
        Example:
            <dl>
              <dt>Foo</dt><dd>Bar</dd>
              <dt>Baz</dt><dd>Qux</dd>
            </dl>
        →
            <pre data-dl="1">
            Foo  
            :  Bar  
            
            Baz  
            :  Qux
            </pre>
        """
        self._assert_parsed()
        from bs4 import NavigableString, Tag

        for dl in list(self.dom_tree.find_all("dl")):
            lines: List[str] = []
            for child in dl.children:
                if not isinstance(child, Tag):
                    continue
                if child.name == "dt":
                    term = " ".join(child.get_text(strip=True).split())
                    lines.append(f"{term}  ")
                elif child.name == "dd":
                    definition = " ".join(child.get_text(strip=True).split())
                    lines.append(f":  {definition}  ")
            if not lines:
                continue

            md_text = "\n".join(lines).rstrip()
            pre = self.dom_tree.new_tag("pre", **{"data-dl": "1"})
            pre.string = NavigableString(md_text)
            dl.replace_with(pre)

        return self


    def preserve_lists_as_markdown(self) -> "HtmlReducer":
        """
        Convert <ul> and <ol> into Markdown‐style bullets/numbers (with nesting), wrapped in <pre data-list="1">…</pre>.
        """
        self._assert_parsed()
        from bs4 import NavigableString, Tag

        def walk_list(lst: Tag, depth: int = 0) -> List[str]:
            lines: List[str] = []
            is_ordered = lst.name == "ol"
            idx = 1
            for li in lst.find_all("li", recursive=False):
                prefix = ("  " * depth) + (f"{idx}. " if is_ordered else "- ")
                # Grab only direct text nodes under this <li> (ignore nested <ul>/<ol> for now)
                direct_text = "".join(
                    t for t in li.find_all(text=True, recursive=False)
                ).strip()
                content = " ".join(direct_text.split())
                lines.append(f"{prefix}{content}")
                # Recurse into any nested <ul> or <ol>
                for child in li.find_all(["ul", "ol"], recursive=False):
                    lines.extend(walk_list(child, depth + 1))
                idx += 1
            return lines

        for lst in list(self.dom_tree.find_all(["ul", "ol"])):
            md_lines = walk_list(lst)
            if not md_lines:
                continue
            md_blob = "\n".join(md_lines)
            pre = self.dom_tree.new_tag("pre", **{"data-list": "1"})
            pre.string = NavigableString(md_blob)
            lst.replace_with(pre)

        return self


    def preserve_figures_as_markdown(self) -> "HtmlReducer":
        """
        Convert <figure><img …><figcaption>…</figcaption></figure> into a Markdown image line,
        wrapped in <pre data-figure="1">…</pre>.
        Example:
            <figure>
              <img src="foo.png" alt="Foo">
              <figcaption>Caption text</figcaption>
            </figure>
        →
            <pre data-figure="1">![Caption text](foo.png)</pre>
        """
        self._assert_parsed()
        from bs4 import NavigableString, Tag

        for fig in list(self.dom_tree.find_all("figure")):
            img = fig.find("img")
            if not img:
                continue
            src = img.get("src", "").strip()
            alt = img.get("alt", "").strip()
            cap = fig.find("figcaption")
            caption_text = cap.get_text(" ", strip=True) if cap else alt or ""
            # Fallback: if caption is empty but alt is present, use alt
            if not caption_text and alt:
                caption_text = alt

            md = f"![{caption_text}]({src})"
            pre = self.dom_tree.new_tag("pre", **{"data-figure": "1"})
            pre.string = NavigableString(md)
            fig.replace_with(pre)

        return self


    def preserve_css_tables_as_markdown(self) -> "HtmlReducer":
        """
        Detect “CSS table” layouts (e.g. <div style="display:table"> with
        children styled as table-row/table-cell) and convert them into Markdown tables,
        wrapped in <pre data-csstable="1">…</pre>.
        """
        self._assert_parsed()
        from bs4 import NavigableString, Tag
        import re

        css_table = re.compile(r"display\s*:\s*table", re.I)
        css_row = re.compile(r"display\s*:\s*table-row", re.I)
        css_cell = re.compile(r"display\s*:\s*table-cell", re.I)

        # Find any element whose inline style includes “display:table”
        for elem in list(self.dom_tree.find_all(style=css_table)):
            # Find direct children (or descendants at one level) styled as table-row
            rows = [
                row for row in elem.find_all(True)
                if row.has_attr("style") and css_row.search(row["style"] or "")
            ]
            if not rows:
                continue

            table_data: List[List[str]] = []
            for row in rows:
                # For each row, look at its direct children that are “display:table-cell”
                cells = [
                    cell for cell in row.find_all(True, recursive=False)
                    if cell.has_attr("style") and css_cell.search(cell["style"] or "")
                ]
                row_data = [
                    " ".join(cell.get_text(strip=True).split())
                    for cell in cells
                ]
                table_data.append(row_data)

            if not table_data:
                continue

            # Normalize column counts
            max_cols = max(len(r) for r in table_data)
            for r in table_data:
                if len(r) < max_cols:
                    r.extend([""] * (max_cols - len(r)))

            md_lines: List[str] = []
            # Treat first row as header
            header = table_data[0]
            sep = ["---"] * max_cols
            md_lines.append("| " + " | ".join(header) + " |")
            md_lines.append("| " + " | ".join(sep) + " |")
            for data_row in table_data[1:]:
                md_lines.append("| " + " | ".join(data_row) + " |")

            md_blob = "\n".join(md_lines)
            pre = self.dom_tree.new_tag("pre", **{"data-csstable": "1"})
            pre.string = NavigableString(md_blob)
            elem.replace_with(pre)

        return self

    # ----------------------------------------------------------------------

    _DEFAULT_PIPE = [
        "parse_the_full_dom_into_a_dom_tree",
        "strip_out_non_structural_nodes",
        "strip_out_non_visual_nodes",
        "simplify_attributes",
        "collapse_deeply_nested_container_with_one_child",
        "prune_repetitive_and_boilerplate_navigation_items",
        "reduce_large_inline_SVGs_or_images_to_lightweight_placeholders",
    ]

    def reduce(self, order: Optional[List[str]] = None) -> "HtmlReducer":
        """
        Run an entire reduction pipeline.  Pass a list of *method names* (strings)
        to customize ordering / selection; otherwise the default full pipeline
        is executed.
        """
        steps: List[str] = order or self._DEFAULT_PIPE
        for name in steps:
            fn: Callable[[], HtmlReducer] = getattr(self, name)
            fn()                       # each returns self, so chaining implicit
        return self


# --- quick demo (remove when importing as a library) -----------------------
if __name__ == "__main__":
    import sys, textwrap, pathlib
    sample_html = pathlib.Path(__file__).with_suffix(".html").read_text() if len(sys.argv) > 1 else """
        <html><head><style>.x{display:none}</style></head>
        <body>
            <div><div><span id='t' style="display:none">invisible</span>
                <svg width="800" height="600"><circle cx="50" cy="50" r="40"/></svg>
                <nav><ul><li>home</li><li>about</li></ul></nav>
                <nav><ul><li>home</li><li>about</li></ul></nav>
            </div></div>
        </body></html>
    """
    cleaner = HtmlReducer(sample_html).reduce()
    print(textwrap.shorten(cleaner.to_html(), width=120, placeholder=" …"))
