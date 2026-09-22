---
name: paper-html-translator
description: Extract a browser-saved scholarly article HTML and its local resources into an image-complete English Markdown document, then produce a faithful Chinese translation in a title-named folder. Use for saved paper webpages; do not use for PDF-only inputs or ordinary web-page summarization.
metadata:
  short-description: Convert saved paper HTML into bilingual Markdown
---

# Paper HTML Translator

Turn a user-provided, browser-saved paper HTML into a self-contained bilingual Markdown package. Preserve the paper's evidence structure and never silently omit unavailable resources.

## Required output

Create one folder named from the normalized original paper title:

```text
<Original paper title>/
|-- <Original paper title>.md
|-- <Chinese translated title>.md
`-- assets/
```

Use relative image links such as `assets/figure-001.png`. Sanitize Windows-invalid filename characters, trim trailing dots/spaces, and shorten an excessively long title without changing the title shown inside either document.

## Workflow

1. Inspect the input before writing. A browser "Webpage, Complete" save normally requires both the `.html` file and its companion resource directory. If referenced local resources are missing, continue with recoverable content and report every unresolved item.
2. Read [references/extraction-rules.md](references/extraction-rules.md), then run `scripts/extract_paper_html.py` with the input HTML and an appropriate output root. Use the bundled Codex Python runtime when ordinary `python` lacks `lxml`.
3. Review the generated English Markdown against the HTML. Correct main-content selection, heading hierarchy, formulas, tables, captions, footnotes, and references when the deterministic extraction is imperfect. Do not paraphrase the English original.
4. Read [references/translation-style.md](references/translation-style.md), determine a faithful Chinese title, and create `<Chinese translated title>.md` beside the English document. Translate the full article while preserving structure and all asset paths.
5. Run `scripts/validate_package.py <paper-folder>`. Resolve broken local assets, missing deliverables, duplicated title headings, and obvious extraction residue. Treat remote-only images as warnings rather than pretending they were localized.
6. Report the output folder, document names, unresolved resources, and any content that could not be preserved exactly.

## Operational boundaries

- Work only from user-provided files and resources already in scope. Do not download remote images or supplementary files without authorization.
- Never invent missing paragraphs, metadata, equations, captions, or references.
- Preserve raw MathML, LaTeX delimiters, and complex HTML tables when a Markdown conversion would lose meaning.
- Keep citations and bibliography entries in their original language unless the user explicitly requests bibliography translation.
- Do not overwrite a non-empty paper folder silently. Use a separate output root or obtain explicit permission before replacing prior results.
- For `.mhtml`, PDF, DOCX, or a live JavaScript-only page, use a format-appropriate workflow instead of forcing this extractor.

