use std::collections::BTreeMap;
use std::fs;
use std::path::Path;

use crate::po::{parse_document, write_document, PoDocument, PoEntry};
use crate::Error;

const METADATA_BASE: &[(&str, &str)] = &[
    ("Project-Id-Version", "SmartGit"),
    (
        "Report-Msgid-Bugs-To",
        "https://github.com/syntevo/smartgit-translations",
    ),
    ("POT-Creation-Date", ""),
    ("PO-Revision-Date", ""),
    ("Last-Translator", ""),
    ("Language-Team", ""),
    ("Language", ""),
    ("MIME-Version", "1.0"),
    ("Content-Type", "text/plain; charset=UTF-8"),
    ("Content-Transfer-Encoding", "8bit"),
    ("Plural-Forms", "nplurals=1; plural=0;"),
];

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum FormatMode {
    Check,
    Write,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FormatReport {
    pub changed_files: Vec<String>,
}

impl FormatReport {
    pub fn is_success(&self) -> bool {
        self.changed_files.is_empty()
    }
}

pub fn format_paths(paths: &[impl AsRef<Path>], mode: FormatMode) -> Result<FormatReport, Error> {
    let mut changed_files = Vec::new();

    for path in paths {
        let path = path.as_ref();
        let content = fs::read_to_string(path).map_err(|source| Error::io(path, source))?;
        let formatted = format_content(path, &content)?;
        if formatted != content {
            changed_files.push(path.display().to_string());
            if mode == FormatMode::Write {
                fs::write(path, formatted).map_err(|source| Error::io(path, source))?;
            }
        }
    }

    Ok(FormatReport { changed_files })
}

pub fn format_content(path: &Path, content: &str) -> Result<String, Error> {
    let mut document = parse_document(path, content)?;
    format_document(&mut document);
    Ok(write_document(&document))
}

pub fn format_document(document: &mut PoDocument) {
    normalize_header(document);
    sort_document(document);
}

pub fn sort_document(document: &mut PoDocument) {
    let mut header = Vec::new();
    let mut active = Vec::new();
    let mut obsolete = Vec::new();

    for entry in document.entries.drain(..) {
        if entry.is_header() && !entry.obsolete {
            if header.is_empty() {
                header.push(entry);
            } else {
                active.push(entry);
            }
        } else if entry.obsolete {
            obsolete.push(entry);
        } else {
            active.push(entry);
        }
    }

    active.sort_by_key(sort_key);
    obsolete.sort_by_key(sort_key);

    document.entries = header;
    document.entries.extend(active);
    document.entries.extend(obsolete);
}

fn normalize_header(document: &mut PoDocument) {
    let header = document.ensure_header();
    let metadata = parse_metadata(&header.msgstr);
    header.translator_comments = vec![String::new()];
    header.extracted_comments.clear();
    header.references.clear();
    header.flags.clear();
    header.previous_msgctxt = None;
    header.previous_msgid = None;
    header.previous_msgstr = None;
    header.msgctxt = None;
    header.msgid.clear();
    header.msgstr = render_metadata(&metadata);
    header.obsolete = false;
}

fn parse_metadata(text: &str) -> BTreeMap<String, String> {
    let mut metadata = BTreeMap::new();
    for line in text.lines() {
        if let Some((key, value)) = line.split_once(':') {
            metadata.insert(key.to_string(), value.trim_start().to_string());
        }
    }
    metadata
}

fn render_metadata(metadata: &BTreeMap<String, String>) -> String {
    let mut rendered = String::new();
    for (key, default_value) in METADATA_BASE {
        let value = if default_value.is_empty() {
            metadata.get(*key).map(String::as_str).unwrap_or("")
        } else {
            default_value
        };
        rendered.push_str(key);
        rendered.push_str(": ");
        rendered.push_str(value);
        rendered.push('\n');
    }
    rendered
}

fn sort_key(entry: &PoEntry) -> String {
    let legacy_key = legacy_key(entry);
    if entry
        .msgctxt
        .as_deref()
        .is_some_and(|msgctxt| msgctxt.starts_with('*'))
    {
        format!("\u{1}{legacy_key}")
    } else {
        multi_keys_filter(&legacy_key)
    }
}

fn legacy_key(entry: &PoEntry) -> String {
    match entry.msgctxt.as_deref() {
        Some(msgctxt) if msgctxt.ends_with(':') => {
            format!("{}\"{}\"", msgctxt.trim_end_matches(':'), entry.msgid)
        }
        Some(msgctxt) => msgctxt.to_string(),
        None => String::new(),
    }
}

fn multi_keys_filter(text: &str) -> String {
    let chars = text.chars().collect::<Vec<_>>();
    let mut output = String::new();
    let mut index = 0;

    while index < chars.len() {
        if chars[index] == '(' && !is_escaped(&chars, index) {
            if let Some(close) = find_unescaped_close_paren(&chars, index + 1) {
                output.push_str("ZZZ");
                for ch in &chars[index + 1..close] {
                    output.push(*ch);
                }
                index = close + 1;
                continue;
            }
        }
        output.push(chars[index]);
        index += 1;
    }

    output
}

fn find_unescaped_close_paren(chars: &[char], start: usize) -> Option<usize> {
    (start..chars.len()).find(|&index| chars[index] == ')' && !is_escaped(chars, index))
}

fn is_escaped(chars: &[char], index: usize) -> bool {
    let mut slash_count = 0;
    let mut cursor = index;
    while cursor > 0 && chars[cursor - 1] == '\\' {
        slash_count += 1;
        cursor -= 1;
    }
    slash_count % 2 == 1
}

#[cfg(test)]
mod tests {
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

    fn assert_formats_to(input: &[&str], expected: &[&str]) {
        let input_path = fixture_path(input);
        let expected_path = fixture_path(expected);
        let input_content = fs::read_to_string(&input_path).unwrap();
        let expected_content = normalize_newlines(&fs::read_to_string(&expected_path).unwrap());

        let actual = format_content(&input_path, &input_content).unwrap();

        assert_eq!(expected_content, actual);
    }

    #[test]
    fn formats_header_less_fixture() {
        assert_formats_to(&["format", "header_less.po"], &["format", "formatted.po"]);
    }

    #[test]
    fn formats_unnecessary_header_fixture() {
        assert_formats_to(
            &["format", "unnecessary_header.po"],
            &["format", "formatted.po"],
        );
    }

    #[test]
    fn formats_abnormal_header_order_fixture() {
        assert_formats_to(
            &["format", "abnormal_order_header.po"],
            &["format", "formatted.po"],
        );
    }

    #[test]
    fn sorts_like_python_sgpo() {
        let normal_path = fixture_path(&["sort", "normal_order.po"]);
        let reverse_path = fixture_path(&["sort", "reverse_order.po"]);
        let normal_content = normalize_newlines(&fs::read_to_string(&normal_path).unwrap());
        let reverse_content = fs::read_to_string(&reverse_path).unwrap();

        let actual = format_content(&reverse_path, &reverse_content).unwrap();

        assert_eq!(normal_content, actual);
    }

    #[test]
    fn keeps_star_prefixed_keys_first() {
        let actual = format_content(
            Path::new("sample.po"),
            r#"#
msgid ""
msgstr ""

msgctxt "z"
msgid "z"
msgstr ""

msgctxt "*special"
msgid "special"
msgstr ""
"#,
        )
        .unwrap();

        assert!(actual.find("*special").unwrap() < actual.find("z").unwrap());
    }

    fn normalize_newlines(text: &str) -> String {
        text.replace("\r\n", "\n")
    }
}
