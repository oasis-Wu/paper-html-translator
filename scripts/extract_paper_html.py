#!/usr/bin/env python3
"""Extract a browser-saved scholarly HTML page into Markdown with local assets."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import mimetypes
import re
import shutil
import sys
from pathlib import Path
from urllib.parse import unquote, unquote_to_bytes, urlparse

try:
    from lxml import etree, html
except ImportError as exc:  # pragma: no cover - environment guard
    raise SystemExit(
        "This extractor requires lxml. Run it with the bundled Codex Python runtime."
    ) from exc


WINDOWS_RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}
NOISE_TAGS = {"script", "style", "noscript", "template", "nav", "form", "button"}
NOISE_WORDS = {
    "advert", "banner", "breadcrumb", "cookie", "consent", "footer", "masthead",
    "login", "menu", "metrics", "modal", "navbar", "newsletter", "popup",
    "recommend", "related", "share", "signin", "social", "subscribe", "toolbar",
}
BLOCK_TAGS = {
    "article", "aside", "blockquote", "div", "dl", "figure", "figcaption", "footer",
    "form", "h1", "h2", "h3", "h4", "h5", "h6", "header", "hr", "main", "nav",
    "ol", "p", "pre", "section", "table", "ul",
}


def decode_html(data: bytes) -> str:
    if data.startswith(b"\xef\xbb\xbf"):
        return data.decode("utf-8-sig")
    probe = data[:4096].decode("ascii", errors="ignore")
    match = re.search(r"charset\s*=\s*[\"']?([A-Za-z0-9._-]+)", probe, re.I)
    encodings = [match.group(1)] if match else []
    encodings += ["utf-8", "gb18030", "windows-1252"]
    for encoding in encodings:
        try:
            return data.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            pass
    return data.decode("utf-8", errors="replace")


def clean_space(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def safe_name(value: str, fallback: str = "paper", max_len: int = 120) -> str:
    value = clean_space(value)
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value).rstrip(" .")
    if not value:
        value = fallback
    if value.upper() in WINDOWS_RESERVED:
        value = f"_{value}"
    if len(value) > max_len:
        value = value[:max_len].rstrip(" .")
    return value


def meta_values(root, key: str) -> list[str]:
    nodes = root.xpath(
        "//meta[translate(@name,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz')=$key "
        "or translate(@property,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz')=$key]/@content",
        key=key.lower(),
    )
    return [clean_space(v) for v in nodes if clean_space(v)]


def first(values: list[str], default: str = "") -> str:
    return values[0] if values else default


def extract_metadata(root, input_path: Path) -> dict[str, object]:
    visible_h1 = [clean_space(" ".join(n.itertext())) for n in root.xpath("//article//h1 | //main//h1 | //h1")]
    document_title = clean_space(" ".join(root.xpath("//title/text()")))
    title = first(meta_values(root, "citation_title"))
    title = title or first(meta_values(root, "dc.title")) or first(meta_values(root, "og:title"))
    title = title or first([v for v in visible_h1 if v]) or document_title or input_path.stem
    return {
        "title": title,
        "authors": meta_values(root, "citation_author"),
        "journal": first(meta_values(root, "citation_journal_title")),
        "year": first(meta_values(root, "citation_publication_date")) or first(meta_values(root, "citation_date")),
        "doi": first(meta_values(root, "citation_doi")),
        "url": first(meta_values(root, "citation_public_url")) or first(meta_values(root, "og:url")),
    }


def noise_signature(node) -> str:
    return " ".join([node.get("id", ""), node.get("class", "")]).lower()


def remove_noise(root) -> None:
    for node in list(root.iter()):
        if not isinstance(node.tag, str):
            continue
        tag = node.tag.lower()
        signature = noise_signature(node)
        hidden = node.get("aria-hidden", "").lower() == "true" or "display:none" in node.get("style", "").replace(" ", "").lower()
        noisy = tag in NOISE_TAGS or hidden
        if not noisy and tag in {"aside", "div", "section", "header"}:
            noisy = any(word in signature for word in NOISE_WORDS)
        if noisy and node.getparent() is not None:
            node.drop_tree()


def candidate_score(node) -> int:
    text = clean_space(" ".join(node.itertext()))
    paragraphs = node.xpath(".//p")
    headings = node.xpath(".//h1 | .//h2 | .//h3 | .//h4")
    scholarly = sum(
        1 for h in headings
        if re.search(r"abstract|introduction|methods?|results?|discussion|conclusion|references", clean_space(" ".join(h.itertext())), re.I)
    )
    figures = len(node.xpath(".//figure | .//img"))
    tables = len(node.xpath(".//table"))
    penalty = 2500 if any(word in noise_signature(node) for word in NOISE_WORDS) else 0
    return len(text) + 240 * len(paragraphs) + 180 * scholarly + 80 * figures + 80 * tables - penalty


def select_main(root):
    candidates = root.xpath("//article | //main | //*[@role='main']")
    if not candidates:
        candidates = root.xpath(
            "//*[contains(translate(@class,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'article') "
            "or contains(translate(@class,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'fulltext') "
            "or contains(translate(@id,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'article')]"
        )
    if not candidates:
        candidates = root.xpath("//body") or [root]
    return max(candidates, key=candidate_score)


def best_from_srcset(srcset: str) -> str:
    if srcset:
        choices = []
        for item in srcset.split(","):
            parts = item.strip().split()
            if not parts:
                continue
            score = 0.0
            if len(parts) > 1:
                descriptor = parts[-1].lower()
                try:
                    score = float(descriptor[:-1]) * (1000 if descriptor.endswith("x") else 1)
                except ValueError:
                    score = 0.0
            choices.append((score, parts[0]))
        if choices:
            return max(choices)[1]
    return ""


def best_src(node) -> str:
    for attr in ("data-hires", "data-original"):
        value = clean_space(node.get(attr, ""))
        if value and not value.lower().startswith("javascript:"):
            return value
    own_srcset = best_from_srcset(clean_space(node.get("srcset", "")))
    if own_srcset:
        return own_srcset
    parent = node.getparent()
    if parent is not None and isinstance(parent.tag, str) and parent.tag.lower() == "picture":
        source_values = [best_from_srcset(clean_space(value)) for value in parent.xpath("./source/@srcset")]
        source_values = [value for value in source_values if value]
        if source_values:
            return source_values[-1]
    for attr in ("data-src", "data-lazy-src", "src"):
        value = clean_space(node.get(attr, ""))
        if value and not value.lower().startswith("javascript:"):
            return value
    return ""


class AssetManager:
    def __init__(self, html_path: Path, assets_dir: Path):
        self.html_path = html_path
        self.assets_dir = assets_dir
        self.counter = 0
        self.hash_to_name: dict[str, str] = {}
        self.warnings: list[str] = []

    def _save_bytes(self, payload: bytes, suffix: str) -> str:
        digest = hashlib.sha256(payload).hexdigest()
        if digest in self.hash_to_name:
            return self.hash_to_name[digest]
        self.counter += 1
        suffix = suffix.lower() if re.fullmatch(r"\.[a-zA-Z0-9]{1,8}", suffix or "") else ".bin"
        name = f"figure-{self.counter:03d}{suffix}"
        (self.assets_dir / name).write_bytes(payload)
        self.hash_to_name[digest] = name
        return name

    def localize(self, src: str) -> str:
        src = src.strip()
        if not src:
            return ""
        if src.startswith("data:"):
            try:
                header, encoded = src.split(",", 1)
                mime_match = re.match(r"data:([^;,]+)", header, re.I)
                mime = mime_match.group(1) if mime_match else "application/octet-stream"
                payload = base64.b64decode(encoded) if ";base64" in header.lower() else unquote_to_bytes(encoded)
                suffix = mimetypes.guess_extension(mime) or ".bin"
                return f"assets/{self._save_bytes(payload, suffix)}"
            except Exception as exc:  # noqa: BLE001
                self.warnings.append(f"Could not decode embedded image: {exc}")
                return src
        parsed = urlparse(src)
        if parsed.scheme in {"http", "https", "//"} or src.startswith("//"):
            self.warnings.append(f"Remote image not localized: {src}")
            return src
        if parsed.scheme == "file":
            local = Path(unquote(parsed.path.lstrip("/")))
            if re.match(r"^[A-Za-z]\|", str(local)):
                local = Path(str(local).replace("|", ":", 1))
        else:
            clean_path = unquote(src.split("?", 1)[0].split("#", 1)[0])
            path_value = Path(clean_path)
            local = path_value.resolve() if path_value.is_absolute() else (self.html_path.parent / path_value).resolve()
        if not local.is_file():
            self.warnings.append(f"Local image missing: {src}")
            return src
        try:
            return f"assets/{self._save_bytes(local.read_bytes(), local.suffix or '.bin')}"
        except OSError as exc:
            self.warnings.append(f"Could not copy image {src}: {exc}")
            return src


def escape_md(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "")
    return re.sub(r"([\\`*_{}\[\]])", r"\\\1", text)


class MarkdownConverter:
    def __init__(self, assets: AssetManager):
        self.assets = assets

    def inline(self, node) -> str:
        if not isinstance(node.tag, str):
            return ""
        tag = node.tag.lower()
        if tag == "img":
            src = self.assets.localize(best_src(node))
            alt = escape_md(node.get("alt", "") or node.get("title", "") or "Figure").strip()
            return f"![{alt}]({src})" if src else ""
        if tag in {"math", "svg"}:
            return etree.tostring(node, encoding="unicode", method="html")
        content = escape_md(node.text or "")
        for child in node:
            content += self.convert_node(child, inline_context=True)
            content += escape_md(child.tail or "")
        if tag in {"strong", "b"} and content.strip():
            return f"**{content.strip()}**"
        if tag in {"em", "i"} and content.strip():
            return f"*{content.strip()}*"
        if tag == "code":
            return f"`{clean_space(''.join(node.itertext()))}`"
        if tag == "a":
            href = node.get("href", "").strip()
            label = content.strip() or href
            return f"[{label}]({href})" if href and not href.lower().startswith("javascript:") else label
        if tag == "br":
            return "  \n"
        if tag == "sup" and content.strip():
            return f"<sup>{content.strip()}</sup>"
        if tag == "sub" and content.strip():
            return f"<sub>{content.strip()}</sub>"
        return content

    def children(self, node) -> str:
        result = escape_md(node.text or "")
        for child in node:
            result += self.convert_node(child, inline_context=child.tag not in BLOCK_TAGS if isinstance(child.tag, str) else True)
            result += escape_md(child.tail or "")
        return result

    def table(self, node) -> str:
        if node.xpath(".//*[@rowspan or @colspan]"):
            return "\n\n" + etree.tostring(node, encoding="unicode", method="html") + "\n\n"
        rows = []
        for row in node.xpath(".//tr"):
            cells = [clean_space(" ".join(cell.itertext())).replace("|", "\\|") for cell in row.xpath("./th | ./td")]
            if cells:
                rows.append(cells)
        if not rows:
            return ""
        caption_nodes = node.xpath("./caption")
        caption = clean_space(" ".join(caption_nodes[0].itertext())) if caption_nodes else ""
        width = max(len(row) for row in rows)
        rows = [row + [""] * (width - len(row)) for row in rows]
        lines = ["| " + " | ".join(rows[0]) + " |", "| " + " | ".join(["---"] * width) + " |"]
        lines += ["| " + " | ".join(row) + " |" for row in rows[1:]]
        prefix = f"*{escape_md(caption).strip()}*\n\n" if caption else ""
        return "\n\n" + prefix + "\n".join(lines) + "\n\n"

    def convert_node(self, node, inline_context: bool = False) -> str:
        if not isinstance(node.tag, str):
            return ""
        tag = node.tag.lower()
        if tag in NOISE_TAGS:
            return ""
        if tag in {"img", "a", "strong", "b", "em", "i", "code", "br", "sup", "sub", "math", "svg"}:
            return self.inline(node)
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            level = int(tag[1])
            return f"\n\n{'#' * level} {clean_space(self.children(node))}\n\n"
        if tag == "p":
            content = self.children(node).strip()
            return f"\n\n{content}\n\n" if content else ""
        if tag == "blockquote":
            content = clean_space(self.children(node))
            return "\n\n" + "\n".join(f"> {line}" for line in content.splitlines()) + "\n\n"
        if tag == "pre":
            content = "".join(node.itertext()).strip("\n")
            return f"\n\n```\n{content}\n```\n\n"
        if tag in {"ul", "ol"}:
            lines = []
            for index, item in enumerate(node.xpath("./li"), 1):
                marker = f"{index}." if tag == "ol" else "-"
                lines.append(f"{marker} {clean_space(self.children(item))}")
            return "\n\n" + "\n".join(lines) + "\n\n" if lines else ""
        if tag == "figure":
            parts = [self.convert_node(child) for child in node if isinstance(child.tag, str)]
            return "\n\n" + "\n\n".join(part.strip() for part in parts if part.strip()) + "\n\n"
        if tag == "figcaption":
            content = clean_space(self.children(node))
            return f"*{content}*" if content else ""
        if tag == "table":
            return self.table(node)
        if tag == "hr":
            return "\n\n---\n\n"
        content = self.children(node)
        if inline_context:
            return content
        return f"\n\n{content}\n\n" if tag in BLOCK_TAGS else content

    def convert(self, node) -> str:
        text = self.children(node)
        text = re.sub(r"[ \t]+\n", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()


def metadata_block(metadata: dict[str, object]) -> str:
    lines = ["## Metadata", ""]
    authors = metadata.get("authors") or []
    fields = [
        ("Authors", "; ".join(authors) if isinstance(authors, list) else str(authors)),
        ("Journal", str(metadata.get("journal") or "")),
        ("Publication date", str(metadata.get("year") or "")),
        ("DOI", str(metadata.get("doi") or "")),
        ("Source URL", str(metadata.get("url") or "")),
    ]
    lines.extend(f"- {label}: {value}" for label, value in fields if value)
    return "\n".join(lines).rstrip()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("html_file", type=Path, help="Browser-saved HTML file")
    parser.add_argument("--output-root", type=Path, help="Parent directory for the title-named output folder")
    parser.add_argument("--folder-name", help="Override the output folder/English Markdown filename")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    input_path = args.html_file.resolve()
    if not input_path.is_file():
        raise SystemExit(f"Input file not found: {input_path}")
    if input_path.suffix.lower() not in {".html", ".htm"}:
        raise SystemExit("Input must be a .html or .htm file; use a different workflow for MHTML or PDF.")

    source = decode_html(input_path.read_bytes())
    root = html.fromstring(source)
    metadata = extract_metadata(root, input_path)
    remove_noise(root)
    main_node = select_main(root)

    display_title = str(metadata["title"])
    folder_name = safe_name(args.folder_name or display_title, fallback=input_path.stem)
    output_root = (args.output_root or input_path.parent).resolve()
    output_dir = output_root / folder_name
    if output_dir.exists() and any(output_dir.iterdir()):
        raise SystemExit(f"Refusing to overwrite non-empty output folder: {output_dir}")
    assets_dir = output_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    assets = AssetManager(input_path, assets_dir)
    body = MarkdownConverter(assets).convert(main_node)
    title_pattern = re.compile(r"^#\s+" + re.escape(display_title) + r"\s*$", re.I | re.M)
    if title_pattern.search(body):
        body = title_pattern.sub("", body, count=1).strip()
    markdown = f"# {display_title}\n\n{metadata_block(metadata)}\n\n{body}\n"
    english_path = output_dir / f"{folder_name}.md"
    english_path.write_text(markdown, encoding="utf-8")

    report = {
        "input": str(input_path),
        "output": str(output_dir),
        "english_markdown": str(english_path),
        "localized_assets": len(assets.hash_to_name),
        "warnings": assets.warnings,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
