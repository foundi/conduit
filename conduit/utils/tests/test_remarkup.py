"""Tests for conduit.utils.remarkup."""

import pytest

from conduit.utils.remarkup import (
    append_file_references,
    has_file_reference,
    parse_file_id_from_monogram,
    resolve_file_identifiers,
)


class TestParseFileIdFromMonogram:
    def test_valid_monogram(self):
        assert parse_file_id_from_monogram("F1234") == 1234

    def test_single_digit(self):
        assert parse_file_id_from_monogram("F1") == 1

    def test_invalid_lowercase(self):
        assert parse_file_id_from_monogram("f1234") is None

    def test_empty_string(self):
        assert parse_file_id_from_monogram("") is None

    def test_no_digits(self):
        assert parse_file_id_from_monogram("F") is None

    def test_trailing_chars(self):
        assert parse_file_id_from_monogram("F1234x") is None

    def test_phid_is_not_a_monogram(self):
        assert parse_file_id_from_monogram("PHID-FILE-abc") is None


class TestHasFileReference:
    def test_simple_ref(self):
        assert has_file_reference("see {F1234}", 1234) is True

    def test_with_layout_attr(self):
        assert has_file_reference("see {F1234, layout=link}", 1234) is True

    def test_with_space_attr(self):
        assert has_file_reference("see {F1234 size=full}", 1234) is True

    def test_absent(self):
        assert has_file_reference("see {F1234}", 9999) is False

    def test_prefix_id_does_not_match_longer(self):
        # {F12345} must NOT register as a reference to F1234.
        assert has_file_reference("see {F12345}", 1234) is False

    def test_longer_id_correctly_detected(self):
        assert has_file_reference("see {F12345}", 12345) is True

    def test_empty_text(self):
        assert has_file_reference("", 1234) is False

    def test_has_file_reference_ignores_inline_code(self):
        """Inline code-span mentions must not count as active references."""
        assert not has_file_reference(
            "see `{F1234}` for example", 1234
        )

    def test_has_file_reference_ignores_fenced_code_triple_backtick(self):
        text = "example:\n```\n{F1234}\n```"
        assert not has_file_reference(text, 1234)

    def test_has_file_reference_ignores_fenced_code_tilde(self):
        text = "example:\n~~~\n{F1234}\n~~~"
        assert not has_file_reference(text, 1234)

    def test_has_file_reference_ignores_phorge_monospace_literal(self):
        """Phorge's %%%...%%% monospace literal also bypasses remarkup."""
        text = "see %%%{F1234}%%% literally"
        assert not has_file_reference(text, 1234)

    def test_has_file_reference_still_detects_real_reference(self):
        """Real {F1234} outside any code region is still detected."""
        assert has_file_reference("see {F1234} attached", 1234)

    def test_has_file_reference_mixed_code_and_real_reference(self):
        """Real ref outside code is detected even when code span also
        contains a literal mention of the same id."""
        text = "the `{F1234}` token, e.g. {F1234} below"
        assert has_file_reference(text, 1234)


class TestAppendFileReferences:
    def test_empty_text_single_id(self):
        assert append_file_references("", [1234]) == "{F1234}"

    def test_empty_text_multiple_ids(self):
        assert (
            append_file_references("", [1234, 5678])
            == "{F1234}\n{F5678}"
        )

    def test_appends_to_existing_text(self):
        result = append_file_references("hello world", [1234])
        assert result == "hello world\n\n{F1234}"

    def test_text_ending_with_newline_still_produces_blank_line(self):
        # Whether or not the existing text ends with a newline, the result
        # should leave exactly one blank line before the references.
        result = append_file_references("hello\n", [1234])
        assert result == "hello\n\n{F1234}"

    def test_idempotent_when_already_present(self):
        text = "see {F1234}"
        assert append_file_references(text, [1234]) == text

    def test_idempotent_with_attr_variant(self):
        text = "see {F1234, layout=link}"
        assert append_file_references(text, [1234]) == text

    def test_appends_only_missing(self):
        text = "see {F1234}"
        result = append_file_references(text, [1234, 5678])
        assert result == "see {F1234}\n\n{F5678}"

    def test_empty_ids_returns_text_unchanged(self):
        assert append_file_references("hello", []) == "hello"

    def test_all_ids_already_present_unchanged(self):
        text = "{F1} and {F2}"
        assert append_file_references(text, [1, 2]) == text

    def test_appends_when_only_in_code_span(self):
        """If the only mention is inside backticks, must still append the
        real attachment ref at the end."""
        text = "use the `{F1234}` token to attach"
        out = append_file_references(text, [1234])
        assert out.endswith("{F1234}")
        assert out != text

    def test_idempotent_when_real_ref_outside_code(self):
        """Skip append when a real ref outside code already exists."""
        text = "see {F1234} attached"
        assert append_file_references(text, [1234]) == text

    def test_appends_when_id_only_in_fenced_block(self):
        """Fenced code block mention is not a real reference either."""
        text = "example:\n```\n{F42}\n```"
        out = append_file_references(text, [42])
        assert out.endswith("{F42}")
        assert out != text


class TestResolveFileIdentifiers:
    def test_monogram_fast_path_no_callback(self):
        calls = []

        def fetch(_phid):
            calls.append(_phid)
            return {}

        result = resolve_file_identifiers(["F1234", "F5678"], fetch)
        assert result == [1234, 5678]
        assert calls == []

    def test_phid_resolved_via_callback(self):
        def fetch(phid):
            return {"PHID-FILE-abc": {"id": 42}}[phid]

        assert resolve_file_identifiers(["PHID-FILE-abc"], fetch) == [42]

    def test_mixed_inputs(self):
        def fetch(phid):
            return {"PHID-FILE-xyz": {"id": 99}}[phid]

        result = resolve_file_identifiers(
            ["F1", "PHID-FILE-xyz", "F2"], fetch
        )
        assert result == [1, 99, 2]

    def test_invalid_identifier_raises(self):
        with pytest.raises(ValueError, match="invalid file identifier"):
            resolve_file_identifiers(["not-a-file-id"], lambda _: {})

    def test_phid_missing_id_field_raises(self):
        def fetch(_phid):
            return {"phid": "PHID-FILE-abc"}  # no 'id'

        with pytest.raises(ValueError, match="missing 'id'"):
            resolve_file_identifiers(["PHID-FILE-abc"], fetch)

    def test_empty_input(self):
        assert resolve_file_identifiers([], lambda _: {}) == []
