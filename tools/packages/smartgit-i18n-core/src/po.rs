use std::collections::HashMap;
use std::path::Path;

use rspolib::{
    pofile, FileOptions, POEntry as RspPoEntry, POFile as RspPoFile,
};

use crate::Error;

const WRAP_WIDTH: usize = 9999;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PoDocument {
    pub entries: Vec<PoEntry>,
}

impl PoDocument {
    pub fn active_entries(&self) -> impl Iterator<Item = &PoEntry> {
        self.entries.iter().filter(|entry| !entry.obsolete)
    }

    pub fn active_entries_mut(&mut self) -> impl Iterator<Item = &mut PoEntry> {
        self.entries.iter_mut().filter(|entry| !entry.obsolete)
    }

    pub fn header_mut(&mut self) -> Option<&mut PoEntry> {
        self.entries
            .iter_mut()
            .find(|entry| entry.is_header() && !entry.obsolete)
    }

    pub fn ensure_header(&mut self) -> &mut PoEntry {
        if self.header_mut().is_none() {
            self.entries.insert(
                0,
                PoEntry {
                    line: 1,
                    translator_comments: vec![String::new()],
                    ..PoEntry::default()
                },
            );
        }

        self.header_mut().expect("header was just inserted")
    }
}

#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct PoEntry {
    pub line: usize,
    pub translator_comments: Vec<String>,
    pub extracted_comments: Vec<String>,
    pub references: Vec<String>,
    pub flags: Vec<String>,
    pub previous_msgctxt: Option<String>,
    pub previous_msgid: Option<String>,
    pub previous_msgstr: Option<String>,
    pub msgctxt: Option<String>,
    pub msgid: String,
    pub msgstr: String,
    pub obsolete: bool,
}

impl PoEntry {
    pub fn is_header(&self) -> bool {
        self.msgctxt.is_none() && self.msgid.is_empty()
    }

    pub fn smartgit_key(&self) -> SmartgitKey {
        if self
            .msgctxt
            .as_deref()
            .is_some_and(|msgctxt| msgctxt.ends_with(':'))
        {
            SmartgitKey {
                msgctxt: self.msgctxt.clone().unwrap_or_default(),
                msgid: Some(self.msgid.clone()),
            }
        } else {
            SmartgitKey {
                msgctxt: self.msgctxt.clone().unwrap_or_default(),
                msgid: None,
            }
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
pub struct SmartgitKey {
    pub msgctxt: String,
    pub msgid: Option<String>,
}

pub fn parse_document(path: &Path, content: &str) -> Result<PoDocument, Error> {
    let file = pofile(FileOptions::from((content, WRAP_WIDTH)))
        .map_err(|error| Error::parse(path, error.to_string()))?;
    Ok(from_rsp_file(file, content))
}

pub(crate) fn parse_po(path: &Path, content: &str) -> Result<Vec<PoEntry>, Error> {
    parse_document(path, content).map(|document| document.entries)
}

pub fn write_document(document: &PoDocument) -> String {
    if !document
        .entries
        .iter()
        .any(|entry| entry.is_header() && !entry.obsolete)
    {
        return write_entries(document);
    }

    let file = to_rsp_file(document);
    file.to_string().trim_end_matches('\n').to_string()
}

fn write_entries(document: &PoDocument) -> String {
    let mut output = String::new();
    let active_entries = document.entries.iter().filter(|entry| !entry.obsolete);
    let obsolete_entries = document.entries.iter().filter(|entry| entry.obsolete);

    for entry in active_entries.chain(obsolete_entries) {
        if !output.is_empty() {
            output.push('\n');
        }
        output.push_str(to_rsp_entry(entry).to_string().trim_end_matches('\n'));
    }

    output
}

fn from_rsp_file(file: RspPoFile, content: &str) -> PoDocument {
    let mut entries = Vec::new();
    let first_entry_comments = if file.metadata.is_empty() {
        leading_entry_translator_comments(content)
    } else {
        None
    };

    if !file.metadata.is_empty() {
        entries.push(PoEntry {
            line: 1,
            translator_comments: vec![String::new()],
            msgid: String::new(),
            msgstr: render_metadata(&file.metadata),
            obsolete: file.metadata_is_fuzzy,
            ..PoEntry::default()
        });
    }

    entries.extend(file.entries.iter().enumerate().map(|(index, entry)| {
        let mut entry = from_rsp_entry(entry);
        if index == 0 {
            if let Some(comments) = &first_entry_comments {
                entry.translator_comments = comments.clone();
            }
        }
        entry
    }));

    PoDocument { entries }
}

fn from_rsp_entry(entry: &RspPoEntry) -> PoEntry {
    PoEntry {
        line: entry.linenum,
        translator_comments: split_comment(entry.tcomment.as_deref()),
        extracted_comments: split_comment(entry.comment.as_deref()),
        references: entry
            .occurrences
            .iter()
            .map(|(file, line)| {
                if line.is_empty() {
                    file.clone()
                } else {
                    format!("{file}:{line}")
                }
            })
            .collect(),
        flags: entry.flags.clone(),
        previous_msgctxt: entry.previous_msgctxt.clone(),
        previous_msgid: entry.previous_msgid.clone(),
        previous_msgstr: None,
        msgctxt: entry.msgctxt.clone(),
        msgid: entry.msgid.clone(),
        msgstr: entry.msgstr.clone().unwrap_or_default(),
        obsolete: entry.obsolete,
    }
}

fn to_rsp_file(document: &PoDocument) -> RspPoFile {
    let mut file = RspPoFile::new(FileOptions::from(("", WRAP_WIDTH)));

    for entry in &document.entries {
        if entry.is_header() && !entry.obsolete {
            file.metadata = parse_metadata(&entry.msgstr);
            continue;
        }

        file.entries.push(to_rsp_entry(entry));
    }

    file
}

fn to_rsp_entry(entry: &PoEntry) -> RspPoEntry {
    RspPoEntry {
        msgid: entry.msgid.clone(),
        msgstr: Some(entry.msgstr.clone()),
        msgid_plural: None,
        msgstr_plural: Vec::new(),
        msgctxt: entry.msgctxt.clone(),
        obsolete: entry.obsolete,
        comment: join_comment(&entry.extracted_comments),
        tcomment: join_comment(&entry.translator_comments),
        occurrences: entry.references.iter().map(|value| split_reference(value)).collect(),
        flags: entry.flags.clone(),
        previous_msgid: entry.previous_msgid.clone(),
        previous_msgid_plural: None,
        previous_msgctxt: entry.previous_msgctxt.clone(),
        linenum: entry.line,
    }
}

fn split_comment(comment: Option<&str>) -> Vec<String> {
    comment
        .map(|comment| comment.lines().map(ToOwned::to_owned).collect())
        .unwrap_or_default()
}

fn join_comment(lines: &[String]) -> Option<String> {
    if lines.is_empty() {
        None
    } else {
        Some(lines.join("\n"))
    }
}

fn leading_entry_translator_comments(content: &str) -> Option<Vec<String>> {
    let mut comments = Vec::new();
    let mut saw_comment = false;

    for line in content.lines() {
        let trimmed = line.trim_start();
        if trimmed.is_empty() {
            return None;
        }

        if let Some(comment) = translator_comment(trimmed) {
            saw_comment = true;
            comments.push(comment.to_string());
            continue;
        }

        return saw_comment.then_some(comments);
    }

    None
}

fn translator_comment(line: &str) -> Option<&str> {
    let comment = line.strip_prefix('#')?;
    if matches!(
        comment.chars().next(),
        Some('.') | Some(':') | Some(',') | Some('|') | Some('~')
    ) {
        return None;
    }

    Some(comment.strip_prefix(' ').unwrap_or(comment))
}

fn split_reference(reference: &str) -> (String, String) {
    reference
        .rsplit_once(':')
        .map(|(file, line)| (file.to_string(), line.to_string()))
        .unwrap_or_else(|| (reference.to_string(), String::new()))
}

fn parse_metadata(text: &str) -> HashMap<String, String> {
    let mut metadata = HashMap::new();
    for line in text.lines() {
        if let Some((key, value)) = line.split_once(':') {
            metadata.insert(key.to_string(), value.trim_start().to_string());
        }
    }
    metadata
}

fn render_metadata(metadata: &HashMap<String, String>) -> String {
    let mut keys = metadata.keys().collect::<Vec<_>>();
    keys.sort();

    let mut rendered = String::new();
    for key in keys {
        rendered.push_str(key);
        rendered.push_str(": ");
        rendered.push_str(&metadata[key]);
        rendered.push('\n');
    }
    rendered
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_multiline_entry() {
        let entries = parse_po(
            Path::new("sample.po"),
            r#"
msgctxt "ctx:"
msgid ""
"Hello "
"$1"
msgstr "こんにちは $1"
"!"
"#,
        )
        .unwrap();

        assert_eq!(entries.len(), 1);
        assert_eq!(entries[0].msgctxt.as_deref(), Some("ctx:"));
        assert_eq!(entries[0].msgid, "Hello $1");
        assert_eq!(entries[0].msgstr, "こんにちは $1!");
    }

    #[test]
    fn preserves_extended_entry_information() {
        let document = parse_document(
            Path::new("sample.po"),
            r#"# translator
#. extracted
#: source.java:10
#, fuzzy
#| msgid "old"
msgctxt "ctx"
msgid "new"
msgstr "translated"

#~ msgctxt "gone"
#~ msgid "Gone"
#~ msgstr "Translated gone"
"#,
        )
        .unwrap();

        assert_eq!(document.entries.len(), 2);
        assert_eq!(document.entries[0].translator_comments, ["translator"]);
        assert_eq!(document.entries[0].extracted_comments, ["extracted"]);
        assert_eq!(document.entries[0].references, ["source.java:10"]);
        assert_eq!(document.entries[0].flags, ["fuzzy"]);
        assert_eq!(document.entries[0].previous_msgid.as_deref(), Some("old"));
        assert!(document.entries[1].obsolete);

        let rendered = write_document(&document);
        let reparsed = parse_document(Path::new("sample.po"), &rendered).unwrap();
        assert_entries_eq_without_lines(&document, &reparsed);
    }

    fn assert_entries_eq_without_lines(left: &PoDocument, right: &PoDocument) {
        assert_eq!(left.entries.len(), right.entries.len());
        for (left, right) in left.entries.iter().zip(&right.entries) {
            let mut left = left.clone();
            let mut right = right.clone();
            left.line = 0;
            right.line = 0;
            assert_eq!(left, right);
        }
    }
}
