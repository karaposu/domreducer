# reducer.py

# to run python -m domreducer.reducer

from __future__ import annotations
import re
import hashlib
from typing import List, Callable, Optional, Dict

from bs4 import BeautifulSoup, Comment, Tag, NavigableString
import tiktoken
from .schemes import ReduceOperation


class HtmlReducer:
    """
    A chainable utility that reduces raw HTML while preserving key structure.
    Methods return `self` so they can be chained.  The `reduce` method
    returns a `ReduceOperation` summary.
    """

    _DEFAULT_PIPE = [
        "parse_the_full_dom_into_a_dom_tree",
        "strip_out_non_structural_nodes",
        "strip_out_non_visual_nodes",
        "simplify_attributes",
        "collapse_deeply_nested_container_with_one_child",
        "prune_repetitive_and_boilerplate_navigation_items",
        "reduce_large_inline_SVGs_or_images_to_lightweight_placeholders",
    ]
    
    _ALLOWED_ATTRS = {"id", "class", "href", "src", "alt", "title", "role"}
    _SVG_PLACEHOLDER = "<svg data-placeholder='1' width='{w}' height='{h}'></svg>"
    _IMG_PLACEHOLDER = "<img data-placeholder='1' width='{w}' height='{h}'/>"

    def __init__(self, raw_html: str) -> None:
        self.raw_html: str = raw_html
        self.dom_tree: Optional[BeautifulSoup] = None

        # token encoder
        self.encoding = tiktoken.encoding_for_model("gpt-4o-mini")
        # stats
        self.total_char_len = len(raw_html)
        self.raw_token_size = len(self.encoding.encode(raw_html))
        self.reducement_details: Dict[str, Dict[str, int]] = {}

    def _assert_parsed(self) -> None:
        if self.dom_tree is None:
            raise RuntimeError("Call parse_the_full_dom_into_a_dom_tree() first")

    def _walk(self):
        """Yield every tag in document order."""
        for tag in self.dom_tree.find_all(True):
            yield tag

    def to_html(self) -> str:
        """Return the current HTML as a compact string."""
        self._assert_parsed()
        return self.dom_tree.encode(formatter="html").decode()

    # --- pipeline stages ---------------------------------------------------

    def parse_the_full_dom_into_a_dom_tree(self) -> HtmlReducer:
        """Parse raw HTML into a BeautifulSoup DOM."""
        self.dom_tree = BeautifulSoup(self.raw_html, "lxml")
        return self

    def strip_out_non_structural_nodes(self) -> HtmlReducer:
        """
        Remove comments, <script>, <style>, <iframe>, <meta>, <link>, etc.
        """
        self._assert_parsed()
        # Comments
        for comment in self.dom_tree.find_all(text=lambda t: isinstance(t, Comment)):
            comment.extract()
        # Non‐layout tags
        for tag in self.dom_tree(["script", "noscript", "style", "iframe", "meta", "link"]):
            tag.decompose()
        return self

    def strip_out_non_visual_nodes(self) -> HtmlReducer:
        """
        Remove invisible elements (display:none, hidden, empty inline spans).
        """
        self._assert_parsed()
        css_hidden = re.compile(r"display\s*:\s*none", re.I)
        # remove hidden leaf nodes
        for tag in list(self._walk()):
            hidden = (
                tag.has_attr("hidden")
                or tag.get("aria-hidden") == "true"
                or (tag.has_attr("style") and css_hidden.search(tag["style"] or ""))
            )
            if hidden and not tag.find_all(True):
                tag.decompose()
        # remove empty inline containers
        for tag in list(self._walk()):
            if not tag.contents and tag.name in {"span", "b", "i", "u"}:
                tag.decompose()
        return self

    def simplify_attributes(self) -> HtmlReducer:
        """
        Keep only id/class/href/src/alt/title/role, trim long class lists.
        """
        self._assert_parsed()
        for tag in self._walk():
            for attr in list(tag.attrs):
                if attr not in self._ALLOWED_ATTRS:
                    del tag[attr]
            if "class" in tag.attrs and len(tag["class"]) > 6:
                tag["class"] = tag["class"][:6] + ["…"]
        return self

    def collapse_deeply_nested_container_with_one_child(self) -> HtmlReducer:
        """
        Unwrap chains of single‐child <div>, <section>, <article>, <span>.
        """
        self._assert_parsed()
        for tag in list(self._walk()):
            while (
                len(tag.find_all(True, recursive=False)) == 1
                and not tag.attrs
                and tag.name in {"div", "section", "article", "span"}
            ):
                only_child = tag.find(True, recursive=False)
                tag.unwrap()
                tag = only_child
        return self

    def prune_repetitive_and_boilerplate_navigation_items(self) -> HtmlReducer:
        """
        Drop duplicate <nav>, <ul>, <ol> blocks (by text fingerprint).
        """
        self._assert_parsed()
        seen = set()
        for nav in self.dom_tree.find_all(["nav", "ul", "ol"]):
            fp = re.sub(r"\s+", " ", nav.get_text(strip=True).lower())
            h = hashlib.md5(fp.encode()).hexdigest()
            if h in seen:
                nav.decompose()
            else:
                seen.add(h)
        return self

    def reduce_large_inline_SVGs_or_images_to_lightweight_placeholders(self) -> HtmlReducer:
        """
        Stub out <svg> and oversized <img> with size‐only placeholders.
        """
        self._assert_parsed()
        # SVGs
        for svg in self.dom_tree.find_all("svg"):
            w = svg.get("width", "100%"); h = svg.get("height", "100%")
            placeholder = BeautifulSoup(
                self._SVG_PLACEHOLDER.format(w=w, h=h), "lxml"
            )
            svg.replace_with(placeholder)
        # large images
        for img in self.dom_tree.find_all("img"):
            src = img.get("src", "")
            big_data = src.startswith("data:image") and len(src) > 1500
            big_dims = (
                int(img.get("width") or 0) * int(img.get("height") or 0) > 512 * 512
            )
            if big_data or big_dims:
                w = img.get("width", "auto"); h = img.get("height", "auto")
                placeholder = BeautifulSoup(
                    self._IMG_PLACEHOLDER.format(w=w, h=h), "lxml"
                )
                img.replace_with(placeholder)
        return self

    def preserve_tables_as_markdown(self) -> HtmlReducer:
        """
        Convert <table> into a <pre data-table="1">…</pre> holding Markdown.
        """
        self._assert_parsed()
        for table in list(self.dom_tree.find_all("table")):
            rows = table.find_all("tr")
            if not rows: continue
            data = [[
                " ".join(cell.get_text(strip=True).split())
                for cell in tr.find_all(["th", "td"])
            ] for tr in rows]
            if not data: continue
            maxc = max(len(r) for r in data)
            for r in data:
                r.extend([""] * (maxc - len(r)))
            md = []
            hdr = data[0]
            sep = ["---"] * maxc
            md.append("| " + " | ".join(hdr) + " |")
            md.append("| " + " | ".join(sep) + " |")
            for r in data[1:]:
                md.append("| " + " | ".join(r) + " |")
            pre = self.dom_tree.new_tag("pre", **{"data-table": "1"})
            pre.string = NavigableString("\n".join(md))
            table.replace_with(pre)
        return self

    def preserve_deflists_as_markdown(self) -> HtmlReducer:
        """
        Convert <dl>…</dl> into a Markdown‐style definition list in <pre data-dl>.
        """
        self._assert_parsed()
        for dl in list(self.dom_tree.find_all("dl")):
            lines: List[str] = []
            for child in dl.children:
                if not isinstance(child, Tag): continue
                text = " ".join(child.get_text(strip=True).split())
                if child.name == "dt":
                    lines.append(f"{text}  ")
                elif child.name == "dd":
                    lines.append(f":  {text}  ")
            if not lines: continue
            pre = self.dom_tree.new_tag("pre", **{"data-dl": "1"})
            pre.string = NavigableString("\n".join(lines).rstrip())
            dl.replace_with(pre)
        return self

    def preserve_lists_as_markdown(self) -> HtmlReducer:
        """
        Convert <ul>/<ol> into nested Markdown lists in a <pre data-list>.
        """
        self._assert_parsed()

        def walk(lst: Tag, depth: int = 0) -> List[str]:
            out: List[str] = []
            ordered = lst.name == "ol"; idx = 1
            for li in lst.find_all("li", recursive=False):
                prefix = ("  " * depth) + (f"{idx}. " if ordered else "- ")
                txt = " ".join(
                    t for t in li.find_all(text=True, recursive=False)
                ).strip()
                out.append(prefix + txt)
                for sub in li.find_all(["ul", "ol"], recursive=False):
                    out.extend(walk(sub, depth + 1))
                idx += 1
            return out

        for lst in list(self.dom_tree.find_all(["ul", "ol"])):
            md = walk(lst)
            if not md: continue
            pre = self.dom_tree.new_tag("pre", **{"data-list": "1"})
            pre.string = NavigableString("\n".join(md))
            lst.replace_with(pre)
        return self

    def preserve_figures_as_markdown(self) -> HtmlReducer:
        """
        Convert <figure><img><figcaption> into Markdown image in <pre data-figure>.
        """
        self._assert_parsed()
        for fig in list(self.dom_tree.find_all("figure")):
            img = fig.find("img")
            if not img: continue
            src = img.get("src", "").strip()
            alt = img.get("alt", "").strip()
            cap = fig.find("figcaption")
            caption = cap.get_text(" ", strip=True) if cap else alt
            md = f"![{caption}]({src})"
            pre = self.dom_tree.new_tag("pre", **{"data-figure": "1"})
            pre.string = NavigableString(md)
            fig.replace_with(pre)
        return self

    def preserve_css_tables_as_markdown(self) -> HtmlReducer:
        """
        Convert CSS‐display:table layouts into Markdown in <pre data-csstable>.
        """
        self._assert_parsed()
        css_table = re.compile(r"display\s*:\s*table", re.I)
        css_row = re.compile(r"display\s*:\s*table-row", re.I)
        css_cell = re.compile(r"display\s*:\s*table-cell", re.I)

        for tbl in list(self.dom_tree.find_all(style=css_table)):
            rows = [
                r for r in tbl.find_all(True)
                if r.has_attr("style") and css_row.search(r["style"] or "")
            ]
            if not rows: continue
            data: List[List[str]] = []
            for r in rows:
                cells = [
                    c for c in r.find_all(True, recursive=False)
                    if c.has_attr("style") and css_cell.search(c["style"] or "")
                ]
                data.append([
                    " ".join(c.get_text(strip=True).split())
                    for c in cells
                ])
            if not data: continue
            maxc = max(len(r) for r in data)
            for r in data:
                r.extend([""] * (maxc - len(r)))
            md = []
            hdr = data[0]; sep = ["---"] * maxc
            md.append("| " + " | ".join(hdr) + " |")
            md.append("| " + " | ".join(sep) + " |")
            for r in data[1:]:
                md.append("| " + " | ".join(r) + " |")
            pre = self.dom_tree.new_tag("pre", **{"data-csstable": "1"})
            pre.string = NavigableString("\n".join(md))
            tbl.replace_with(pre)
        return self

    def strip_tailwind_utility_classes(self) -> HtmlReducer:
        """
        Remove classes containing digits (common Tailwind utilities).
        """
        self._assert_parsed()
        for tag in self._walk():
            if not tag.has_attr("class"): continue
            new_cls = [c for c in tag["class"] if not re.search(r"\d", c)]
            if new_cls:
                tag["class"] = new_cls
            else:
                del tag["class"]
        return self

    def drop_row_ids_inside_large_tables(self) -> HtmlReducer:
        """
        For tables with more than 10 rows, drop any id on <tr>.
        """
        self._assert_parsed()
        for table in self.dom_tree.find_all("table"):
            rows = table.find_all("tr")
            if len(rows) <= 10:
                continue
            for tr in rows:
                if tr.has_attr("id"):
                    del tr["id"]
        return self

    def minify_whitespace(self) -> HtmlReducer:
        """
        Collapse whitespace in all text nodes to single spaces.
        """
        self._assert_parsed()
        for txt in self.dom_tree.find_all(string=True):
            if isinstance(txt, NavigableString):
                collapsed = " ".join(txt.split())
                txt.replace_with(collapsed)
        return self

    def is_probably_js_shell(self) -> bool:
        """
        Heuristic: an SPA shell often has exactly a <noscript> plus
        an empty <div id="main"> in the body.
        """
        self._assert_parsed()
        body = self.dom_tree.body
        if not body:
            return False
        children = [c for c in body.find_all(recursive=False) if isinstance(c, Tag)]
        return (
            len(children) == 2
            and children[0].name == "noscript"
            and children[1].name == "div"
            and children[1].get("id") == "main"
        )

    def reduce(
        self,
        order: Optional[List[str]] = None,
        abort_on_js_shell: bool = True,
    ) -> ReduceOperation:
        """
        Run the reduction pipeline (or custom steps).  Return a ReduceOperation.

        • If abort_on_js_shell is True and we detect an SPA shell, we stop
          right after parsing and return success=False, js_method_needed=True.
        """
        steps = order or self._DEFAULT_PIPE
        if steps[0] != "parse_the_full_dom_into_a_dom_tree":
            steps = ["parse_the_full_dom_into_a_dom_tree", *steps]

        self.reducement_details = {}

        try:
            # parse
            getattr(self, steps[0])()
            
            # abort if JS shell
            if abort_on_js_shell and self.is_probably_js_shell():
                return ReduceOperation(
                    success=False,
                    total_char=self.total_char_len,
                    total_token=self.raw_token_size,
                    raw_data=self.raw_html,
                    reduced_data=None,
                    js_method_needed=True,
                    reducement_details=self.reducement_details,
                )

            # run each mutator and record deltas
            for name in steps[1:]:
                before = self.to_html()
                b_chars = len(before)
                b_tokens = len(self.encoding.encode(before))

                getattr(self, name)()

                after = self.to_html()
                a_chars = len(after)
                a_tokens = len(self.encoding.encode(after))

                self.reducement_details[name] = {
                    "delta_chars": a_chars - b_chars,
                    "delta_tokens": a_tokens - b_tokens,
                }

            reduced_html = self.to_html()
            reduced_chars = len(reduced_html)
            reduced_tokens = len(self.encoding.encode(reduced_html))
            pct = (
                (self.raw_token_size - reduced_tokens) / self.raw_token_size * 100
                if self.raw_token_size else 0.0
            )   
            
            return ReduceOperation(
                success=True,
                js_method_needed=False,
                total_char=self.total_char_len,
                total_token=self.raw_token_size,
                reduced_data=reduced_html,
                reduced_total_char=reduced_chars,
                reduced_total_token=reduced_tokens,
                token_reducement_percentage=round(pct, 3),
                raw_data=self.raw_html,
                reducement_details=self.reducement_details,
            )

            # return ReduceOperation(
            #     success=True,
            #     total_char=self.total_char_len,
            #     total_token=self.raw_token_size,
            #     raw_data=self.raw_html,
            #     reduced_data=self.to_html(),
            #     js_method_needed=False,
            #     reducement_details=self.reducement_details,
            # )

        except Exception as e:
            return ReduceOperation(
                success=False,
                total_char=self.total_char_len,
                total_token=self.raw_token_size,
                raw_data=self.raw_html,
                reduced_data=None,
                js_method_needed=False,
                reducement_details=self.reducement_details,
                error=str(e),
            )


# --- quick demo (remove when importing as a library) -----------------------
if __name__ == "__main__":
    import sys, pathlib
    sample_html = (
        pathlib.Path(__file__).with_suffix(".html").read_text()
        if len(sys.argv) > 1
        else """
        <html><head><style>.x{display:none}</style></head>
        <body>
            <div><div><span id='t' style="display:none">invisible</span>
                <svg width="800" height="600"><circle cx="50" cy="50" r="40"/></svg>
                <nav><ul><li>home</li><li>about</li></ul></nav>
                <nav><ul><li>home</li><li>about</li></ul></nav>
            </div></div>
        </body></html>
        """
    )
    reducer = HtmlReducer(sample_html)
    op = reducer.reduce()

    if op.success and op.reduced_data is not None:
        print(op.reduced_data)
        print("")
        print("token_reducement_percentage: ", op.token_reducement_percentage)
    else:
        print("Reduction failed or JS shell detected:", op)
