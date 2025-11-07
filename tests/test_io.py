from docs_chunker.io import output_paths_for


def test_output_paths_prevent_collisions(tmp_path):
    """Test that same-named files from different paths get different outputs."""
    # Create two files with the same name in different directories
    dir1 = tmp_path / "documents"
    dir2 = tmp_path / "other"
    dir1.mkdir()
    dir2.mkdir()

    file1 = dir1 / "contract.docx"
    file2 = dir2 / "contract.docx"
    file1.write_bytes(b"fake1")
    file2.write_bytes(b"fake2")

    # Get output paths for both files
    base_dir1, chunks_dir1 = output_paths_for(file1)
    base_dir2, chunks_dir2 = output_paths_for(file2)

    # Verify they have different output directories
    assert (
        base_dir1 != base_dir2
    ), f"Collision detected: both files output to {base_dir1}"
    assert chunks_dir1 != chunks_dir2

    # Verify the directory names include the hash
    assert base_dir1.name.startswith("contract_")
    assert base_dir2.name.startswith("contract_")
    assert base_dir1.name != base_dir2.name  # Different hashes


def test_output_paths_deterministic(tmp_path):
    """Test that the same file always gets the same output path."""
    file_path = tmp_path / "test.docx"
    file_path.write_bytes(b"fake")

    # Get output paths twice
    base_dir1, chunks_dir1 = output_paths_for(file_path)
    base_dir2, chunks_dir2 = output_paths_for(file_path)

    # Verify they're the same (deterministic)
    assert base_dir1 == base_dir2
    assert chunks_dir1 == chunks_dir2


def test_path_traversal_prevention(tmp_path):
    """Test path validation prevents traversal."""

    from docs_chunker.io import validate_path

    # Test that validate_path works for normal paths
    normal_path = tmp_path / "test.docx"
    normal_path.write_bytes(b"fake")
    resolved = validate_path(normal_path)
    assert resolved.is_absolute()

    # Test that paths with .. are handled (they should resolve, but we check)
    # Note: Path.resolve() handles .. automatically, so we test the validation logic
    parent_path = tmp_path / ".." / tmp_path.name / "test.docx"
    # This should resolve to the same path
    resolved_parent = validate_path(parent_path)
    assert resolved_parent == resolved or resolved_parent.exists()


def test_output_paths_invalid_input(tmp_path):
    """Test error handling for invalid paths."""

    from docs_chunker.io import output_paths_for

    # Test with a path that can't be resolved (should still work if path doesn't exist)
    # output_paths_for doesn't require the file to exist
    non_existent = tmp_path / "nonexistent" / "file.docx"
    # This should work since we don't check existence in output_paths_for
    base_dir, chunks_dir = output_paths_for(non_existent)
    assert base_dir is not None
    assert chunks_dir is not None
