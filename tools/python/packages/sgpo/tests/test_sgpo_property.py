import importlib.util
import string
import unittest

import pytest
from hypothesis import given, settings, strategies as st

import sgpo
from sgpo.sgpo import Key_tuple


SAFE_TEXT_CHARS = string.ascii_letters + string.digits + " ._-/"
SAFE_CTX_CHARS = SAFE_TEXT_CHARS.replace(":", "")


def _build_po_text(msgctxt: str, msgid: str, msgstr: str) -> str:
    return f'msgctxt "{msgctxt}"\nmsgid "{msgid}"\nmsgstr "{msgstr}"\n'


@settings(max_examples=50, deadline=None)
@given(
    ctx=st.text(alphabet=SAFE_CTX_CHARS, min_size=1, max_size=20),
    msgid=st.text(alphabet=SAFE_TEXT_CHARS, min_size=1, max_size=20),
    msgstr=st.text(alphabet=SAFE_TEXT_CHARS, min_size=1, max_size=20),
)
def test_polib_backend_roundtrip(ctx: str, msgid: str, msgstr: str) -> None:
    msgctxt = f"{ctx}:"
    content = _build_po_text(msgctxt, msgid, msgstr)

    po = sgpo.pofile_from_text(content, backend=sgpo.PolibBackend())
    entry = po.find_by_key(msgctxt, msgid)

    assert entry is not None
    assert entry.msgstr == msgstr
    assert Key_tuple(msgctxt=msgctxt, msgid=msgid) in po.get_key_list()


@unittest.skipUnless(importlib.util.find_spec("rspolib"), "rspolib not installed")
@settings(max_examples=50, deadline=None)
@given(
    ctx=st.text(alphabet=SAFE_CTX_CHARS, min_size=1, max_size=20),
    msgid=st.text(alphabet=SAFE_TEXT_CHARS, min_size=1, max_size=20),
    msgstr=st.text(alphabet=SAFE_TEXT_CHARS, min_size=1, max_size=20),
)
def test_rspolib_backend_roundtrip(ctx: str, msgid: str, msgstr: str) -> None:
    msgctxt = f"{ctx}:"
    content = _build_po_text(msgctxt, msgid, msgstr)

    po = sgpo.pofile_from_text(content, backend=sgpo.RspolibBackend())
    entry = po.find_by_key(msgctxt, msgid)

    assert entry is not None
    assert entry.msgstr == msgstr
    assert Key_tuple(msgctxt=msgctxt, msgid=msgid) in po.get_key_list()


@unittest.skipUnless(importlib.util.find_spec("rspolib"), "rspolib not installed")
@settings(max_examples=25, deadline=None)
@given(
    ctx=st.text(alphabet=SAFE_CTX_CHARS, min_size=1, max_size=20),
    msgid=st.text(alphabet=SAFE_TEXT_CHARS, min_size=1, max_size=20),
    msgstr=st.text(alphabet=SAFE_TEXT_CHARS, min_size=1, max_size=20),
)
def test_rspolib_rejects_unterminated_msgid(ctx: str, msgid: str, msgstr: str) -> None:
    msgctxt = f"{ctx}:"
    content = f'msgctxt "{msgctxt}"\nmsgid "{msgid}\nmsgstr "{msgstr}"\n'

    with pytest.raises(BaseException):
        sgpo.pofile_from_text(content, backend=sgpo.RspolibBackend())
