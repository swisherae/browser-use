"""
Characterization tests for browser_use/dom/enhanced_snapshot.py.

This module turns a raw CDP snapshot into the data the agent sees. Two pieces matter most:
_is_sensitive_input decides whether an input's live value is withheld so it cannot reach logs
or the model, and _parse_computed_styles maps style indices onto named CSS properties that
later drive visibility and clickability decisions. Neither had tests before this file.

The functions take plain CDP structures, so these tests need no browser.
"""

from browser_use.dom.enhanced_snapshot import (
	REQUIRED_COMPUTED_STYLES,
	_is_sensitive_input,
	_parse_computed_styles,
	_parse_rare_boolean_data,
	build_snapshot_lookup,
)


def nodes_with_attributes(*attribute_rows: list[int]) -> dict:
	"""CDP stores attributes as a flat [name_index, value_index, ...] list per node."""
	return {'attributes': list(attribute_rows)}


class TestIsSensitiveInput:
	"""Which inputs get their live value withheld from serialization."""

	def test_isSensitiveInput_whenTypeIsPassword_returnsTrue(self):
		strings = ['type', 'password']
		assert _is_sensitive_input(strings, nodes_with_attributes([0, 1]), 0) is True

	def test_isSensitiveInput_whenTypeIsText_returnsFalse(self):
		strings = ['type', 'text']
		assert _is_sensitive_input(strings, nodes_with_attributes([0, 1]), 0) is False

	def test_isSensitiveInput_whenTypeIsFileOrHidden_returnsTrue(self):
		for sensitive in ('file', 'hidden'):
			strings = ['type', sensitive]
			assert _is_sensitive_input(strings, nodes_with_attributes([0, 1]), 0) is True, sensitive

	def test_isSensitiveInput_whenAutocompleteIsPaymentCard_returnsTrue(self):
		strings = ['autocomplete', 'cc-number']
		assert _is_sensitive_input(strings, nodes_with_attributes([0, 1]), 0) is True

	def test_isSensitiveInput_whenAutocompleteIsOneTimeCode_returnsTrue(self):
		strings = ['autocomplete', 'one-time-code']
		assert _is_sensitive_input(strings, nodes_with_attributes([0, 1]), 0) is True

	def test_isSensitiveInput_whenAutocompleteIsEmail_returnsFalse(self):
		"""Only payment and one-time-code prefixes count; ordinary autofill does not."""
		strings = ['autocomplete', 'email']
		assert _is_sensitive_input(strings, nodes_with_attributes([0, 1]), 0) is False

	def test_isSensitiveInput_whenAttributeCaseIsUpper_returnsTrue(self):
		"""Names and values are lowercased before comparison, so markup casing does not matter."""
		strings = ['TYPE', 'PASSWORD']
		assert _is_sensitive_input(strings, nodes_with_attributes([0, 1]), 0) is True

	def test_isSensitiveInput_whenSensitiveAttributeIsNotFirst_returnsTrue(self):
		"""Boundary: every name/value pair in the row is examined, not just the first."""
		strings = ['id', 'field1', 'type', 'password']
		assert _is_sensitive_input(strings, nodes_with_attributes([0, 1, 2, 3]), 0) is True

	def test_isSensitiveInput_whenIndexBeyondAttributeRows_returnsFalse(self):
		"""Boundary: an out-of-range snapshot index is treated as not sensitive."""
		strings = ['type', 'password']
		assert _is_sensitive_input(strings, nodes_with_attributes([0, 1]), 5) is False

	def test_isSensitiveInput_whenNodesHaveNoAttributesKey_returnsFalse(self):
		assert _is_sensitive_input(['type', 'password'], {}, 0) is False

	def test_isSensitiveInput_whenStringIndexOutOfRange_skipsPairWithoutRaising(self):
		"""Failure path: a corrupt index is skipped rather than raising IndexError."""
		strings = ['type']
		assert _is_sensitive_input(strings, nodes_with_attributes([0, 99]), 0) is False

	def test_isSensitiveInput_whenAttributeRowHasOddLength_ignoresTrailingName(self):
		"""Failure path: an unpaired trailing name is dropped by the pairwise walk."""
		strings = ['id', 'field1', 'type']
		assert _is_sensitive_input(strings, nodes_with_attributes([0, 1, 2]), 0) is False

	def test_isSensitiveInput_whenDefaultsAreNotMutated_passwordStillDetectedAfterOtherCalls(self):
		"""The frozenset of sensitive types is shared, so confirm it is not being mutated."""
		_is_sensitive_input(['type', 'text'], nodes_with_attributes([0, 1]), 0)
		assert _is_sensitive_input(['type', 'password'], nodes_with_attributes([0, 1]), 0) is True


class TestParseComputedStyles:
	"""Style indices are mapped onto the fixed REQUIRED_COMPUTED_STYLES list by position."""

	def test_parseComputedStyles_whenIndicesValid_mapsByPosition(self):
		strings = ['block', 'visible']
		result = _parse_computed_styles(strings, [0, 1])
		assert result[REQUIRED_COMPUTED_STYLES[0]] == 'block'
		assert result[REQUIRED_COMPUTED_STYLES[1]] == 'visible'

	def test_parseComputedStyles_whenMoreIndicesThanKnownProperties_ignoresExtras(self):
		"""Boundary: positions past the known property list are dropped silently."""
		strings = ['v'] * 50
		result = _parse_computed_styles(strings, list(range(len(REQUIRED_COMPUTED_STYLES) + 5)))
		assert len(result) == len(REQUIRED_COMPUTED_STYLES)

	def test_parseComputedStyles_whenIndexOutOfRange_skipsThatProperty(self):
		"""Failure path: a bad index yields a missing key rather than an exception."""
		result = _parse_computed_styles(['block'], [99])
		assert REQUIRED_COMPUTED_STYLES[0] not in result

	def test_parseComputedStyles_whenNoIndices_returnsEmptyDict(self):
		assert _parse_computed_styles(['block'], []) == {}


class TestSnapshotLookupAndRareData:
	"""The entry point's empty case, and the rare-data membership helper."""

	def test_buildSnapshotLookup_whenNoDocuments_returnsEmptyLookup(self):
		assert build_snapshot_lookup({'documents': [], 'strings': []}) == {}

	def test_parseRareBooleanData_whenIndexPresent_returnsTrue(self):
		assert _parse_rare_boolean_data({1, 4, 7}, 4) is True

	def test_parseRareBooleanData_whenIndexAbsent_returnsFalse(self):
		"""Despite the bool | None return type, absence gives False, never None."""
		assert _parse_rare_boolean_data({1, 4, 7}, 2) is False
