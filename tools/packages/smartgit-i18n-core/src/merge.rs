use std::collections::BTreeSet;
use std::path::Path;

use crate::formatting::sort_document;
use crate::po::{parse_document, write_document, PoDocument, PoEntry, SmartgitKey};
use crate::Error;

pub fn import_unknown_content(
    pot_path: &Path,
    pot_content: &str,
    unknown_path: &Path,
    unknown_content: &str,
) -> Result<String, Error> {
    let mut pot = parse_document(pot_path, pot_content)?;
    let unknown = parse_document(unknown_path, unknown_content)?;

    import_unknown(&mut pot, &unknown);
    sort_document(&mut pot);

    Ok(write_document(&pot))
}

pub fn import_mismatch_content(
    pot_path: &Path,
    pot_content: &str,
    mismatch_path: &Path,
    mismatch_content: &str,
) -> Result<String, Error> {
    let mut pot = parse_document(pot_path, pot_content)?;
    let mismatch = parse_document(mismatch_path, mismatch_content)?;

    import_mismatch(&mut pot, &mismatch);
    sort_document(&mut pot);

    Ok(write_document(&pot))
}

pub fn import_pot_content(
    po_path: &Path,
    po_content: &str,
    pot_path: &Path,
    pot_content: &str,
) -> Result<String, Error> {
    let mut po = parse_document(po_path, po_content)?;
    let pot = parse_document(pot_path, pot_content)?;

    import_pot(&mut po, &pot);
    sort_document(&mut po);

    Ok(write_document(&po))
}

pub fn import_unknown(pot: &mut PoDocument, unknown: &PoDocument) {
    for unknown_entry in smartgit_entries(unknown) {
        if find_by_key(
            pot,
            unknown_entry.msgctxt.as_deref(),
            Some(&unknown_entry.msgid),
        )
        .is_none()
        {
            pot.entries.push(unknown_entry.clone());
        }
    }
}

pub fn import_mismatch(pot: &mut PoDocument, mismatch: &PoDocument) {
    for mismatch_entry in smartgit_entries(mismatch) {
        if let Some(index) = find_by_key(
            pot,
            mismatch_entry.msgctxt.as_deref(),
            Some(&mismatch_entry.msgid),
        ) {
            let pot_entry = &mut pot.entries[index];
            if pot_entry.msgid != mismatch_entry.msgid {
                pot_entry.previous_msgid = Some(pot_entry.msgid.clone());
                pot_entry.msgid = mismatch_entry.msgid.clone();
            }
        } else {
            pot.entries.push(mismatch_entry.clone());
        }
    }
}

pub fn import_pot(po: &mut PoDocument, pot: &PoDocument) {
    let po_keys = smartgit_key_set(po);
    let pot_keys = smartgit_key_set(pot);

    for key in pot_keys.difference(&po_keys) {
        if let Some(entry) = find_by_smartgit_key(pot, key) {
            po.entries.push(entry.clone());
        }
    }

    for key in po_keys.difference(&pot_keys) {
        if let Some(index) = find_by_smartgit_key_index(po, key) {
            po.entries[index].obsolete = true;
        }
    }

    for po_entry in po.active_entries_mut() {
        let Some(msgctxt) = po_entry.msgctxt.as_deref() else {
            continue;
        };
        if msgctxt.ends_with(':') {
            continue;
        }
        let Some(pot_index) = find_by_key(pot, Some(msgctxt), None) else {
            continue;
        };
        let pot_entry = &pot.entries[pot_index];
        if po_entry.msgid != pot_entry.msgid {
            po_entry.previous_msgid = Some(po_entry.msgid.clone());
            po_entry.msgid = pot_entry.msgid.clone();
            po_entry.flags = vec!["fuzzy".to_string()];
        }
    }
}

fn smartgit_entries(document: &PoDocument) -> impl Iterator<Item = &PoEntry> {
    document
        .active_entries()
        .filter(|entry| entry.msgctxt.is_some())
}

fn smartgit_key_set(document: &PoDocument) -> BTreeSet<SmartgitKey> {
    smartgit_entries(document)
        .map(PoEntry::smartgit_key)
        .collect()
}

fn find_by_smartgit_key<'a>(document: &'a PoDocument, key: &SmartgitKey) -> Option<&'a PoEntry> {
    let msgid = key.msgid.as_deref();
    find_by_key(document, Some(&key.msgctxt), msgid).map(|index| &document.entries[index])
}

fn find_by_smartgit_key_index(document: &PoDocument, key: &SmartgitKey) -> Option<usize> {
    find_by_key(document, Some(&key.msgctxt), key.msgid.as_deref())
}

fn find_by_key(document: &PoDocument, msgctxt: Option<&str>, msgid: Option<&str>) -> Option<usize> {
    let msgctxt = msgctxt?;
    document
        .entries
        .iter()
        .enumerate()
        .filter(|(_, entry)| !entry.obsolete)
        .find_map(|(index, entry)| {
            let entry_msgctxt = entry.msgctxt.as_deref()?;
            if entry_msgctxt.ends_with(':') {
                (entry_msgctxt == msgctxt && Some(entry.msgid.as_str()) == msgid).then_some(index)
            } else {
                (entry_msgctxt == msgctxt).then_some(index)
            }
        })
}

#[cfg(test)]
mod tests {
    use std::fs;
    use std::path::{Path, PathBuf};

    use super::*;

    fn fixture_path(parts: &[&str]) -> PathBuf {
        let mut path = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
        path.pop();
        path.push("smartgit-i18n-scripts");
        path.push("tests");
        path.push("data");
        path.push("test_sgpo");
        for part in parts {
            path.push(part);
        }
        path
    }

    fn read_fixture(parts: &[&str]) -> (PathBuf, String) {
        let path = fixture_path(parts);
        let content = fs::read_to_string(&path).unwrap();
        (path, content)
    }

    fn fixture_unicode(path: &Path, text: &str) -> String {
        let document = parse_document(path, text).unwrap();
        write_document(&document)
    }

    fn assert_import_unknown(case_prefix: &str) {
        let (pot_path, pot) =
            read_fixture(&["import_unknown", &format!("{case_prefix}_messages.pot")]);
        let (unknown_path, unknown) =
            read_fixture(&["import_unknown", &format!("{case_prefix}_unknown.24_1")]);
        let (expected_path, expected) = read_fixture(&[
            "import_unknown",
            &format!("{case_prefix}_expected_result.pot"),
        ]);

        let actual = import_unknown_content(&pot_path, &pot, &unknown_path, &unknown).unwrap();

        assert_eq!(fixture_unicode(&expected_path, &expected), actual);
    }

    #[test]
    fn imports_unknown_case_1() {
        assert_import_unknown("case_1");
    }

    #[test]
    fn imports_unknown_case_2() {
        assert_import_unknown("case_2");
    }

    #[test]
    fn imports_unknown_case_3() {
        assert_import_unknown("case_3");
    }

    #[test]
    fn imports_mismatch_case_1() {
        let (pot_path, pot) = read_fixture(&["import_mismatch", "case_1_messages.pot"]);
        let (mismatch_path, mismatch) = read_fixture(&["import_mismatch", "case_1_mismatch.24_1"]);
        let (expected_path, expected) =
            read_fixture(&["import_mismatch", "case_1_expected_result.pot"]);

        let actual = import_mismatch_content(&pot_path, &pot, &mismatch_path, &mismatch).unwrap();

        assert_eq!(fixture_unicode(&expected_path, &expected), actual);
    }

    fn assert_import_pot(case_prefix: &str) {
        let (pot_path, pot) = read_fixture(&["import_pot", &format!("{case_prefix}_messages.pot")]);
        let (po_path, po) = read_fixture(&["import_pot", &format!("{case_prefix}_language.po")]);
        let (expected_path, expected) =
            read_fixture(&["import_pot", &format!("{case_prefix}_expected_result.po")]);

        let actual = import_pot_content(&po_path, &po, &pot_path, &pot).unwrap();

        assert_eq!(fixture_unicode(&expected_path, &expected), actual);
    }

    #[test]
    fn imports_pot_case_1() {
        assert_import_pot("case_1");
    }

    #[test]
    fn imports_pot_case_2() {
        assert_import_pot("case_2");
    }

    #[test]
    fn imports_pot_case_3() {
        assert_import_pot("case_3");
    }
}
