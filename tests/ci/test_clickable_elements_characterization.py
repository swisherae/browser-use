"""
Characterization tests for ClickableElementDetector.is_interactive.

This decides which elements the agent is allowed to click or type into, so every action
the agent takes depends on it. It had no tests before this file.

These tests describe what the code does today, not what it arguably should do. Where the
current behaviour looks surprising, the test name says so rather than asserting a fix.
"""

from browser_use.dom.serializer.clickable_elements import ClickableElementDetector
from browser_use.dom.views import DOMRect, EnhancedAXNode, EnhancedAXProperty, EnhancedDOMTreeNode, EnhancedSnapshotNode, NodeType


def make_node(
	tag: str = 'div',
	*,
	node_type: NodeType = NodeType.ELEMENT_NODE,
	attributes: dict[str, str] | None = None,
	children: list[EnhancedDOMTreeNode] | None = None,
	bounds: DOMRect | None = None,
	cursor_style: str | None = None,
	ax_role: str | None = None,
	ax_properties: list[EnhancedAXProperty] | None = None,
	has_js_click_listener: bool = False,
) -> EnhancedDOMTreeNode:
	"""Build the smallest node the detector will accept, so each test varies one thing."""
	snapshot_node = None
	if bounds is not None or cursor_style is not None:
		snapshot_node = EnhancedSnapshotNode(
			is_clickable=None,
			cursor_style=cursor_style,
			bounds=bounds,
			clientRects=None,
			scrollRects=None,
			computed_styles=None,
			paint_order=None,
			stacking_contexts=None,
		)

	ax_node = None
	if ax_role is not None or ax_properties is not None:
		ax_node = EnhancedAXNode(
			ax_node_id='1',
			ignored=False,
			role=ax_role,
			name=None,
			description=None,
			properties=ax_properties,
			child_ids=None,
		)

	return EnhancedDOMTreeNode(
		node_id=1,
		backend_node_id=1,
		node_type=node_type,
		node_name=tag.upper(),
		node_value='',
		attributes=attributes or {},
		is_scrollable=None,
		is_visible=True,
		absolute_position=None,
		target_id='target-1',
		frame_id=None,
		session_id=None,
		content_document=None,
		shadow_root_type=None,
		shadow_roots=None,
		parent_node=None,
		children_nodes=children or [],
		ax_node=ax_node,
		snapshot_node=snapshot_node,
		has_js_click_listener=has_js_click_listener,
	)


class TestInteractiveTags:
	"""The normal case: ordinary interactive and non-interactive elements."""

	def test_isInteractive_whenTagIsButton_returnsTrue(self):
		assert ClickableElementDetector.is_interactive(make_node('button')) is True

	def test_isInteractive_whenTagIsPlainDiv_returnsFalse(self):
		assert ClickableElementDetector.is_interactive(make_node('div')) is False

	def test_isInteractive_whenTagIsAnchor_returnsTrueEvenWithoutHref(self):
		"""Every <a> counts, href or not: the check is on the tag alone."""
		assert ClickableElementDetector.is_interactive(make_node('a')) is True

	def test_isInteractive_whenTagIsHtmlOrBody_returnsFalse(self):
		assert ClickableElementDetector.is_interactive(make_node('html')) is False
		assert ClickableElementDetector.is_interactive(make_node('body')) is False

	def test_isInteractive_whenNodeIsNotAnElement_returnsFalse(self):
		"""Text nodes exit before any heuristic runs."""
		text_node = make_node('button', node_type=NodeType.TEXT_NODE)
		assert ClickableElementDetector.is_interactive(text_node) is False


class TestIframeSizeBoundary:
	"""An iframe must be strictly larger than 100x100 to be interactive."""

	def test_isInteractive_whenIframeLargerThan100Square_returnsTrue(self):
		node = make_node('iframe', bounds=DOMRect(x=0, y=0, width=101, height=101))
		assert ClickableElementDetector.is_interactive(node) is True

	def test_isInteractive_whenIframeExactly100Square_returnsFalse(self):
		"""The boundary is exclusive: 100 is not 'larger than 100'."""
		node = make_node('iframe', bounds=DOMRect(x=0, y=0, width=100, height=100))
		assert ClickableElementDetector.is_interactive(node) is False

	def test_isInteractive_whenIframeHasNoBounds_returnsFalse(self):
		assert ClickableElementDetector.is_interactive(make_node('iframe')) is False


class TestLabelAndSpanWrappers:
	"""Labels and spans are interactive only when they wrap a form control."""

	def test_isInteractive_whenLabelWrapsInputDirectly_returnsTrue(self):
		node = make_node('label', children=[make_node('input')])
		assert ClickableElementDetector.is_interactive(node) is True

	def test_isInteractive_whenLabelWrapsInputTwoLevelsDeep_returnsTrue(self):
		"""label > span > input is within the two-level search depth."""
		node = make_node('label', children=[make_node('span', children=[make_node('input')])])
		assert ClickableElementDetector.is_interactive(node) is True

	def test_isInteractive_whenLabelWrapsInputThreeLevelsDeep_returnsFalse(self):
		"""Boundary: the descendant search stops at depth two, so this input is missed."""
		deep = make_node('label', children=[make_node('span', children=[make_node('span', children=[make_node('input')])])])
		assert ClickableElementDetector.is_interactive(deep) is False

	def test_isInteractive_whenLabelHasForAttribute_returnsFalseEvenWrappingAnInput(self):
		"""Documented trade-off: a 'for' label is skipped so it cannot double-activate its input."""
		node = make_node('label', attributes={'for': 'email'}, children=[make_node('input')])
		assert ClickableElementDetector.is_interactive(node) is False


class TestAccessibilityProperties:
	"""Accessibility properties are consulted before the tag name is."""

	def test_isInteractive_whenAxDisabled_returnsFalseEvenForButton(self):
		"""A disabled button is not interactive: the ax check runs before the tag check."""
		node = make_node('button', ax_properties=[EnhancedAXProperty(name='disabled', value=True)])
		assert ClickableElementDetector.is_interactive(node) is False

	def test_isInteractive_whenAxHidden_returnsFalseEvenForButton(self):
		node = make_node('button', ax_properties=[EnhancedAXProperty(name='hidden', value=True)])
		assert ClickableElementDetector.is_interactive(node) is False

	def test_isInteractive_whenAxCheckedPropertyPresentButFalse_returnsTrue(self):
		"""Surprising but current: presence of 'checked' counts, its value is not read."""
		node = make_node('div', ax_properties=[EnhancedAXProperty(name='checked', value=False)])
		assert ClickableElementDetector.is_interactive(node) is True

	def test_isInteractive_whenAxRoleIsButton_returnsTrue(self):
		assert ClickableElementDetector.is_interactive(make_node('div', ax_role='button')) is True


class TestAttributeHeuristics:
	"""Search hints, event handlers and roles each make an otherwise plain element clickable."""

	def test_isInteractive_whenClassContainsSearch_returnsTrue(self):
		node = make_node('div', attributes={'class': 'header search-btn'})
		assert ClickableElementDetector.is_interactive(node) is True

	def test_isInteractive_whenIdContainsSearch_returnsTrue(self):
		assert ClickableElementDetector.is_interactive(make_node('div', attributes={'id': 'siteSearch'})) is True

	def test_isInteractive_whenOnclickAttributePresent_returnsTrue(self):
		assert ClickableElementDetector.is_interactive(make_node('div', attributes={'onclick': 'go()'})) is True

	def test_isInteractive_whenTabindexPresentWithAnyValue_returnsTrue(self):
		"""Even tabindex="-1", which removes an element from tab order, counts."""
		assert ClickableElementDetector.is_interactive(make_node('div', attributes={'tabindex': '-1'})) is True

	def test_isInteractive_whenRoleIsPresentational_returnsFalse(self):
		assert ClickableElementDetector.is_interactive(make_node('div', attributes={'role': 'presentation'})) is False

	def test_isInteractive_whenJsClickListenerDetected_returnsTrue(self):
		assert ClickableElementDetector.is_interactive(make_node('div', has_js_click_listener=True)) is True


class TestIconSizeBoundary:
	"""Icon-sized elements with any identifying attribute are treated as interactive."""

	def test_isInteractive_whenIconSizedWithClass_returnsTrue(self):
		node = make_node('i', attributes={'class': 'icon'}, bounds=DOMRect(x=0, y=0, width=24, height=24))
		assert ClickableElementDetector.is_interactive(node) is True

	def test_isInteractive_whenJustOverIconSizeWithClass_returnsFalse(self):
		"""Boundary: the icon band is 10 to 50 inclusive, so 51 falls out of it."""
		node = make_node('i', attributes={'class': 'icon'}, bounds=DOMRect(x=0, y=0, width=51, height=51))
		assert ClickableElementDetector.is_interactive(node) is False

	def test_isInteractive_whenIconSizedWithNoAttributes_returnsFalse(self):
		node = make_node('i', bounds=DOMRect(x=0, y=0, width=24, height=24))
		assert ClickableElementDetector.is_interactive(node) is False


class TestCursorFallback:
	"""The last resort: a pointer cursor."""

	def test_isInteractive_whenCursorIsPointer_returnsTrue(self):
		assert ClickableElementDetector.is_interactive(make_node('div', cursor_style='pointer')) is True

	def test_isInteractive_whenCursorIsDefault_returnsFalse(self):
		assert ClickableElementDetector.is_interactive(make_node('div', cursor_style='default')) is False
