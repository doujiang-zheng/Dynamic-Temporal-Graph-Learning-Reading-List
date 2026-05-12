#!/usr/bin/env python3
"""
Filter dynamic/temporal graph papers from the Awesome Graph Learning Papers List
and merge them into the current repo's README.md, avoiding duplicates.

Source: ../Awesome-Graph-Learning-Papers-List/README.md
Target: ./README.md
"""

import re
import os
from typing import Dict, List, Set, Tuple

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

AWESOME_README = os.path.join(
    os.path.dirname(__file__),
    "..",
    "Awesome-Graph-Learning-Papers-List",
    "README.md",
)
TARGET_README = os.path.join(os.path.dirname(__file__), "README.md")

# Keywords to search for in paper titles (case-insensitive regex)
KEYWORD_PATTERNS = [
    r"temporal\s+graph",
    r"temporal\s+network",
    r"dynamic\s+graph",
    r"dynamic\s+network",
    r"temporal\s+knowledge\s+graph",
    r"dynamic\s+hypergraph",
    r"temporal\s+hypergraph",
    r"continuous.time\s+dynamic\s+graph",
    r"temporal\s+heterogeneous\s+graph",
    r"dynamic\s+heterogeneous\s+graph",
]

# Conferences in the order they should appear
CONFERENCE_ORDER = [
    "IJCAI", "ICML", "KDD", "SIGIR", "NeurIPS", "CIKM",
    "AAAI", "ICLR", "WSDM", "WWW", "ICDE", "SIGMOD",
]

# Years that already exist in the current README (checked during dedup)
# We'll detect existing sections dynamically.

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def matches_keyword(title: str) -> bool:
    """Return True if the paper title matches any dynamic-graph keyword.

    Excludes papers that only match because "temporal graph" appears inside
    "spatio-temporal graph" / "spatial-temporal graph" (a different research area),
    unless they also contain "dynamic graph" or "dynamic network".
    """
    title_lower = title.lower()
    matched = False
    for pat in KEYWORD_PATTERNS:
        if re.search(pat, title_lower):
            matched = True
            break
    if not matched:
        return False

    # If the title contains spatio-/spatial-temporal phrasing, check whether
    # it has a genuine dynamic-graph keyword beyond the coincidental substring match.
    has_spatio = bool(re.search(r"spati[ao].?\-?temporal\s+(graph|hypergraph|network|knowledge\s+graph)", title_lower))
    has_dynamic = bool(re.search(r"dynamic\s+(graph|network|hypergraph)", title_lower))
    if has_spatio and not has_dynamic:
        return False

    return True


def normalize_title(title: str) -> str:
    """Normalize a paper title for dedup comparison."""
    return title.strip().lower()


def parse_papers(readme_path: str) -> Dict[str, List[Tuple[str, str]]]:
    """
    Parse a README.md into a dict:
        { "CONF-YEAR": [("Paper Title", "Author Line"), ...] }

    Sections are identified by `### [CONF-YEAR](#contents)` headers.
    Paper entries are lines matching `1. **Title**` followed by an indented
    author line.
    """
    with open(readme_path, "r", encoding="utf-8") as f:
        text = f.read()

    sections = {}
    current_section = None
    current_papers = []

    lines = text.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]

        # Detect section header: ### [CONF-YEAR](#contents)
        section_match = re.match(r"^###\s+\[([A-Za-z]+-\d{4})\]\(#contents\)", line)
        if section_match:
            if current_section is not None:
                sections[current_section] = current_papers
            current_section = section_match.group(1)
            current_papers = []
            i += 1
            continue

        # Detect paper entry: 1. **Title**
        paper_match = re.match(r"^1\.\s+\*\*(.+?)\*\*\.?\s*$", line)
        if paper_match and current_section is not None:
            title = paper_match.group(1).strip()
            # Next non-empty line should be the author line
            author_line = ""
            j = i + 1
            while j < len(lines) and lines[j].strip() == "":
                j += 1
            if j < len(lines):
                author_candidate = lines[j].strip()
                # Author line typically starts with * and is indented
                if author_candidate.startswith("*"):
                    author_line = author_candidate.strip("*").strip()
            current_papers.append((title, author_line))
            i = j + 1 if j < len(lines) else i + 1
            continue

        i += 1

    if current_section is not None:
        sections[current_section] = current_papers

    return sections


def get_existing_titles(readme_path: str) -> Set[str]:
    """Extract all normalized paper titles already in the target README."""
    sections = parse_papers(readme_path)
    titles = set()
    for papers in sections.values():
        for title, _ in papers:
            titles.add(normalize_title(title))
    return titles


def build_contents_line(year: str, existing_confs: Set[str]) -> str:
    """Build one contents line for a given year, e.g.:
    '  - [IJCAI-2023](#ijcai-2023) [ICML-2023](#icml-2023) ...'
    """
    parts = []
    for conf in CONFERENCE_ORDER:
        tag = f"{conf}-{year}"
        if tag in existing_confs:
            parts.append(f"[{tag}](#{tag.lower()})")
    if parts:
        return "  - " + " ".join(parts)
    return ""


def build_section_markdown(tag: str, papers: List[Tuple[str, str]]) -> str:
    """Build a markdown section block for a conference-year."""
    conf, year = tag.split("-")
    lines = [f"### [{conf}-{year}](#contents)"]
    for title, authors in papers:
        lines.append(f"1. **{title}**")
        lines.append("")
        lines.append(f"    *{authors}*")
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    # 1. Parse source and target
    print(f"Parsing source: {AWESOME_README}")
    awesome_sections = parse_papers(AWESOME_README)
    print(f"  Found {len(awesome_sections)} sections, "
          f"{sum(len(v) for v in awesome_sections.values())} papers total")

    print(f"Parsing target: {TARGET_README}")
    existing_titles = get_existing_titles(TARGET_README)
    existing_sections = parse_papers(TARGET_README)
    print(f"  Found {len(existing_titles)} existing papers")

    # 2. Filter papers matching keywords
    new_by_tag = {}  # type: Dict[str, List[Tuple[str, str]]]
    total_matched = 0
    total_new = 0

    for tag, papers in awesome_sections.items():
        for title, authors in papers:
            if matches_keyword(title):
                total_matched += 1
                nt = normalize_title(title)
                if nt not in existing_titles:
                    if tag not in new_by_tag:
                        new_by_tag[tag] = []
                    new_by_tag[tag].append((title, authors))
                    total_new += 1

    print(f"  Matched {total_matched} papers, {total_new} new (not already in target)")

    if total_new == 0:
        print("No new papers to add. Exiting.")
        return

    # 3. Determine all years that have papers (old + new)
    all_tags = set()
    for tag in set(existing_sections.keys()) | set(new_by_tag.keys()):
        existing = existing_sections.get(tag, [])
        new = new_by_tag.get(tag, [])
        if existing or new:
            all_tags.add(tag)
    years = sorted(set(tag.split("-")[1] for tag in all_tags), reverse=True)

    # 4. Build updated README
    # Read the original target README to extract the header (before first ###)
    with open(TARGET_README, "r", encoding="utf-8") as f:
        original_text = f.read()

    # Find the ## [Contents] line to stop the header
    contents_match = re.search(r"^##\s+\[Contents\]", original_text, re.MULTILINE)
    if contents_match:
        header = original_text[:contents_match.start()].rstrip()
    else:
        header = original_text.strip()

    # Build the new contents and body
    output_lines = [header, ""]

    # Contents section
    output_lines.append("## [Contents](#contents)")
    for year in years:
        tag_set = set()
        for conf in CONFERENCE_ORDER:
            tag = f"{conf}-{year}"
            if tag in all_tags:
                tag_set.add(tag)
        if tag_set:
            line = build_contents_line(year, tag_set)
            if line:
                output_lines.append(line)
    output_lines.append("")

    # Body: each section, sorted by year desc then conference order
    for year in years:
        for conf in CONFERENCE_ORDER:
            tag = f"{conf}-{year}"
            papers = new_by_tag.get(tag, [])
            if tag in existing_sections:
                # Merge: existing papers first, then new ones
                papers = existing_sections[tag] + papers
            if not papers:
                continue
            section_md = build_section_markdown(tag, papers)
            output_lines.append(section_md)

    new_readme = "\n".join(output_lines) + "\n"

    # 5. Write
    with open(TARGET_README, "r", encoding="utf-8") as f:
        old_content = f.read()

    # Only write if changed
    if new_readme == old_content:
        print("No changes needed (content is identical).")
        return

    with open(TARGET_README, "w", encoding="utf-8") as f:
        f.write(new_readme)
    print(f"Updated {TARGET_README}")
    print(f"  Added {total_new} new papers across {len(new_by_tag)} sections")


if __name__ == "__main__":
    main()
