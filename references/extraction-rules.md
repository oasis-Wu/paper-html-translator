# Extraction rules

## Input assessment

- Confirm the input is an HTML file, not an `.mhtml` file renamed to `.html`.
- Check whether sibling directories contain the page resources. Common names include `<stem>_files`, `<stem>.files`, and publisher-generated resource folders.
- Record whether images are local files, `data:` URIs, remote URLs, inline SVG, or CSS backgrounds.
- Treat a login wall, CAPTCHA, abstract-only page, or JavaScript shell as incomplete input and disclose that limitation.

## Metadata precedence

Prefer metadata in this order:

1. Highwire/Google Scholar tags such as `citation_title`, `citation_author`, `citation_doi`, and `citation_journal_title`.
2. Schema.org or JSON-LD scholarly article metadata.
3. Open Graph metadata.
4. Visible article heading and byline.
5. The HTML `<title>` only as a fallback.

Never infer absent bibliographic facts from a filename or website branding.

## Main-content selection

Prefer semantic `article` or `main` elements that contain substantial paragraph text. When several candidates exist, favor the candidate with the strongest combination of paragraph count, text length, figures, tables, and scholarly section headings.

Exclude navigation, headers, footers, consent banners, advertisements, recommendation widgets, metrics panels, share controls, sign-in prompts, and unrelated supplementary navigation. Be conservative when a class name such as `content` could refer to either the paper or the site shell.

## Content preservation

Preserve, in original order:

- Title, authors, affiliations, abstract, and keywords.
- Heading hierarchy and paragraph boundaries.
- Lists, block quotes, code, equations, footnotes, and endnotes.
- Figures, subfigure labels, figure captions, and image alternative text.
- Tables, captions, header rows, and explanatory notes.
- Acknowledgements, funding, conflicts of interest, data/code availability, appendices, and references.

Use raw HTML inside Markdown when converting MathML, inline SVG, or a complex table would discard semantics. Do not replace an equation or table with a prose description.

## Image handling

- Inspect `src`, lazy-load attributes, `<picture>/<source>`, and `srcset`; select the highest-resolution available source.
- Decode `data:` images into `assets/`.
- Copy local images into `assets/` and use stable names such as `figure-001.png`.
- Deduplicate byte-identical images while retaining all references.
- Do not upscale or recompress images.
- Preserve SVG when possible.
- Do not fetch remote images without authorization. Keep the remote URL in the English Markdown and report it as not localized.
- Do not treat logos, social icons, avatars, trackers, or decorative spacers as paper figures.

## Output review

Compare the generated English Markdown with the source HTML, focusing on the beginning and end of every major section, all figure/table positions, mathematical expressions, and the transition into references. Search for residue such as `Cookie`, `Sign in`, `Share`, `Recommended`, and repeated publisher navigation, but remove it only after confirming it is not article text.

