import pytest

from docs_chunker.structure import (
    DocumentStructure,
    extract_structure,
    get_heading_hierarchy,
    get_section_preview,
)


def test_extract_structure_basic():
    md = "# Title\n\n## Section 1\nContent\n\n## Section 2\nMore"
    structure = extract_structure(md)
    assert len(structure.headings) == 3
    assert structure.headings[0].level == 1
    assert structure.headings[0].title == "Title"
    assert structure.min_level == 1
    assert structure.max_level == 2
    assert structure.has_structure is True


def test_section_token_counts():
    md = "# Title\n\nContent here\n\n## Section\nMore content"
    structure = extract_structure(md)
    assert structure.headings[0].token_count > 0
    assert structure.headings[1].token_count > 0


def test_nested_headings():
    md = "# Title\n\n## Section\n\n### Subsection\nContent"
    structure = extract_structure(md)
    assert structure.max_level == 3
    assert structure.min_level == 1


def test_unstructured_document():
    md = "Just some text without headings."
    structure = extract_structure(md)
    assert structure.has_structure is False
    assert len(structure.headings) == 0
    assert structure.min_level == 0
    assert structure.max_level == 0


def test_hebrew_headings():
    md = "# כותרת\n\n## סעיף\nתוכן"
    structure = extract_structure(md)
    assert structure.headings[0].title == "כותרת"
    assert structure.headings[1].title == "סעיף"


def test_last_section_boundaries():
    md = "# Title\n\n## Section\nContent at end"
    structure = extract_structure(md)
    last_heading = structure.headings[-1]
    assert last_heading.section_end == len(md.splitlines())


def test_heading_hierarchy_format():
    md = "# Title\n\n## Section\nContent"
    structure = extract_structure(md)
    hierarchy = get_heading_hierarchy(structure)
    assert "# Title" in hierarchy
    assert "## Section" in hierarchy


def test_get_heading_hierarchy_without_headings():
    structure = DocumentStructure(
        headings=[],
        total_tokens=10,
        total_lines=1,
        min_level=0,
        max_level=0,
        has_structure=False,
    )
    hierarchy = get_heading_hierarchy(structure)
    assert "No headings" in hierarchy


def test_section_preview():
    md = "## Section\n" + "Content " * 100
    structure = extract_structure(md)
    preview = get_section_preview(md, structure.headings[0], max_chars=50)
    assert len(preview) <= 51  # allow ellipsis
    assert "Content" in preview


def test_section_preview_zero_chars():
    md = "# Title\nContent"
    structure = extract_structure(md)
    preview = get_section_preview(md, structure.headings[0], max_chars=0)
    assert preview == ""


def test_section_preview_invalid_max_chars():
    md = "# Title\nContent"
    structure = extract_structure(md)
    with pytest.raises(ValueError):
        get_section_preview(md, structure.headings[0], max_chars=-1)


@pytest.mark.skip(reason="Requires real document fixture")
def test_real_document_structure():
    assert True
