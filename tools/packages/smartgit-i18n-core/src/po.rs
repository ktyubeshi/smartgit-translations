use std::path::Path;

use crate::Error;

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

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Field {
    Msgctxt,
    Msgid,
    Msgstr,
    PreviousMsgctxt,
    PreviousMsgid,
    PreviousMsgstr,
}

#[derive(Debug, Default)]
struct EntryBuilder {
    entry: PoEntry,
    current_field: Option<Field>,
}

impl EntryBuilder {
    fn has_content(&self) -> bool {
        self.has_metadata()
            || self.entry.msgctxt.is_some()
            || !self.entry.msgid.is_empty()
            || !self.entry.msgstr.is_empty()
            || self.entry.previous_msgctxt.is_some()
            || self.entry.previous_msgid.is_some()
            || self.entry.previous_msgstr.is_some()
            || self.entry.obsolete
    }

    fn has_metadata(&self) -> bool {
        !self.entry.translator_comments.is_empty()
            || !self.entry.extracted_comments.is_empty()
            || !self.entry.references.is_empty()
            || !self.entry.flags.is_empty()
    }

    fn set_line_if_empty(&mut self, line: usize) {
        if self.entry.line == 0 {
            self.entry.line = line;
        }
    }

    fn add_translator_comment(&mut self, comment: String, line: usize) {
        self.set_line_if_empty(line);
        self.entry.translator_comments.push(comment);
        self.current_field = None;
    }

    fn add_extracted_comment(&mut self, comment: String, line: usize) {
        self.set_line_if_empty(line);
        self.entry.extracted_comments.push(comment);
        self.current_field = None;
    }

    fn add_reference(&mut self, reference: String, line: usize) {
        self.set_line_if_empty(line);
        self.entry.references.push(reference);
        self.current_field = None;
    }

    fn add_flags(&mut self, flags: String, line: usize) {
        self.set_line_if_empty(line);
        self.entry.flags = flags
            .split(',')
            .map(str::trim)
            .filter(|flag| !flag.is_empty())
            .map(ToOwned::to_owned)
            .collect();
        self.current_field = None;
    }

    fn push(
        &mut self,
        path: &Path,
        field: Field,
        value: String,
        line: usize,
        obsolete: bool,
    ) -> Result<(), Error> {
        self.set_line_if_empty(line);
        self.entry.obsolete |= obsolete;
        self.current_field = Some(field);

        let target = match field {
            Field::Msgctxt => &mut self.entry.msgctxt,
            Field::PreviousMsgctxt => &mut self.entry.previous_msgctxt,
            Field::Msgid => {
                if !self.entry.msgid.is_empty() {
                    return Err(Error::parse(
                        path,
                        format!("duplicate msgid at line {line}"),
                    ));
                }
                self.entry.msgid = value;
                return Ok(());
            }
            Field::Msgstr => {
                if !self.entry.msgstr.is_empty() {
                    return Err(Error::parse(
                        path,
                        format!("duplicate msgstr at line {line}"),
                    ));
                }
                self.entry.msgstr = value;
                return Ok(());
            }
            Field::PreviousMsgid => &mut self.entry.previous_msgid,
            Field::PreviousMsgstr => &mut self.entry.previous_msgstr,
        };

        if target.is_some() {
            return Err(Error::parse(
                path,
                format!("duplicate field at line {line}"),
            ));
        }
        *target = Some(value);
        Ok(())
    }

    fn append(&mut self, path: &Path, value: String, line: usize) -> Result<(), Error> {
        match self.current_field {
            Some(Field::Msgctxt) => self
                .entry
                .msgctxt
                .get_or_insert_with(String::new)
                .push_str(&value),
            Some(Field::Msgid) => self.entry.msgid.push_str(&value),
            Some(Field::Msgstr) => self.entry.msgstr.push_str(&value),
            Some(Field::PreviousMsgctxt) => self
                .entry
                .previous_msgctxt
                .get_or_insert_with(String::new)
                .push_str(&value),
            Some(Field::PreviousMsgid) => self
                .entry
                .previous_msgid
                .get_or_insert_with(String::new)
                .push_str(&value),
            Some(Field::PreviousMsgstr) => self
                .entry
                .previous_msgstr
                .get_or_insert_with(String::new)
                .push_str(&value),
            None => {
                return Err(Error::parse(
                    path,
                    format!("continued string without a field at line {line}"),
                ));
            }
        }

        Ok(())
    }

    fn finish(&mut self) -> Option<PoEntry> {
        if !self.has_content() {
            return None;
        }

        self.current_field = None;
        Some(std::mem::take(&mut self.entry))
    }
}

pub fn parse_document(path: &Path, content: &str) -> Result<PoDocument, Error> {
    let mut entries = Vec::new();
    let mut builder = EntryBuilder::default();

    for (index, raw_line) in content.lines().enumerate() {
        let line_number = index + 1;
        let line = raw_line.trim_start();

        if line.is_empty() {
            if let Some(entry) = builder.finish() {
                entries.push(entry);
            }
            continue;
        }

        if let Some(comment) = line.strip_prefix("#.") {
            builder.add_extracted_comment(trim_comment(comment), line_number);
            continue;
        }
        if let Some(reference) = line.strip_prefix("#:") {
            builder.add_reference(trim_comment(reference), line_number);
            continue;
        }
        if let Some(flags) = line.strip_prefix("#,") {
            builder.add_flags(trim_comment(flags), line_number);
            continue;
        }
        if let Some(previous) = line.strip_prefix("#|") {
            parse_field_line(
                path,
                previous.trim_start(),
                line_number,
                false,
                &mut builder,
                true,
            )?;
            continue;
        }
        if let Some(obsolete) = line.strip_prefix("#~") {
            parse_field_line(
                path,
                obsolete.trim_start(),
                line_number,
                true,
                &mut builder,
                false,
            )?;
            continue;
        }
        if let Some(comment) = line.strip_prefix('#') {
            builder.add_translator_comment(trim_comment(comment), line_number);
            continue;
        }

        parse_field_line(path, line, line_number, false, &mut builder, false)?;
    }

    if let Some(entry) = builder.finish() {
        entries.push(entry);
    }

    Ok(PoDocument { entries })
}

pub(crate) fn parse_po(path: &Path, content: &str) -> Result<Vec<PoEntry>, Error> {
    parse_document(path, content).map(|document| document.entries)
}

pub fn write_document(document: &PoDocument) -> String {
    let mut output = String::new();
    let active_entries = document.entries.iter().filter(|entry| !entry.obsolete);
    let obsolete_entries = document.entries.iter().filter(|entry| entry.obsolete);

    for entry in active_entries.chain(obsolete_entries) {
        if !output.is_empty() {
            output.push('\n');
        }
        write_entry(&mut output, entry);
    }

    output
}

fn write_entry(output: &mut String, entry: &PoEntry) {
    for comment in &entry.translator_comments {
        if comment.is_empty() {
            output.push_str("#\n");
        } else {
            output.push_str("# ");
            output.push_str(comment);
            output.push('\n');
        }
    }
    for comment in &entry.extracted_comments {
        output.push_str("#. ");
        output.push_str(comment);
        output.push('\n');
    }
    for reference in &entry.references {
        output.push_str("#: ");
        output.push_str(reference);
        output.push('\n');
    }
    if !entry.flags.is_empty() {
        output.push_str("#, ");
        output.push_str(&entry.flags.join(", "));
        output.push('\n');
    }
    if let Some(msgctxt) = &entry.previous_msgctxt {
        write_field(output, "#| ", "msgctxt", msgctxt);
    }
    if let Some(msgid) = &entry.previous_msgid {
        write_field(output, "#| ", "msgid", msgid);
    }
    if let Some(msgstr) = &entry.previous_msgstr {
        write_field(output, "#| ", "msgstr", msgstr);
    }

    let prefix = if entry.obsolete { "#~ " } else { "" };
    if let Some(msgctxt) = &entry.msgctxt {
        write_field(output, prefix, "msgctxt", msgctxt);
    }
    write_field(output, prefix, "msgid", &entry.msgid);
    write_field(output, prefix, "msgstr", &entry.msgstr);
}

fn write_field(output: &mut String, prefix: &str, name: &str, value: &str) {
    if value.contains('\n') {
        output.push_str(prefix);
        output.push_str(name);
        output.push_str(" \"\"\n");
        for line in value.split_inclusive('\n') {
            output.push_str(prefix);
            output.push('"');
            output.push_str(&escape_string(line));
            output.push_str("\"\n");
        }
    } else {
        output.push_str(prefix);
        output.push_str(name);
        output.push(' ');
        output.push('"');
        output.push_str(&escape_string(value));
        output.push_str("\"\n");
    }
}

fn parse_field_line(
    path: &Path,
    line: &str,
    line_number: usize,
    obsolete: bool,
    builder: &mut EntryBuilder,
    previous: bool,
) -> Result<(), Error> {
    if let Some(value) = parse_field(line, "msgctxt", path, line_number)? {
        builder.push(
            path,
            if previous {
                Field::PreviousMsgctxt
            } else {
                Field::Msgctxt
            },
            value,
            line_number,
            obsolete,
        )?;
    } else if let Some(value) = parse_field(line, "msgid", path, line_number)? {
        builder.push(
            path,
            if previous {
                Field::PreviousMsgid
            } else {
                Field::Msgid
            },
            value,
            line_number,
            obsolete,
        )?;
    } else if let Some(value) = parse_field(line, "msgstr", path, line_number)? {
        builder.push(
            path,
            if previous {
                Field::PreviousMsgstr
            } else {
                Field::Msgstr
            },
            value,
            line_number,
            obsolete,
        )?;
    } else if line.starts_with('"') {
        let value = parse_quoted(line, path, line_number)?;
        builder.append(path, value, line_number)?;
    }

    Ok(())
}

fn parse_field(
    line: &str,
    name: &str,
    path: &Path,
    line_number: usize,
) -> Result<Option<String>, Error> {
    let Some(rest) = line.strip_prefix(name) else {
        return Ok(None);
    };

    let rest = rest.trim_start();
    if !rest.starts_with('"') {
        return Ok(None);
    }

    parse_quoted(rest, path, line_number).map(Some)
}

fn parse_quoted(line: &str, path: &Path, line_number: usize) -> Result<String, Error> {
    let mut chars = line.chars();
    if chars.next() != Some('"') {
        return Err(Error::parse(
            path,
            format!("expected string at line {line_number}"),
        ));
    }

    let mut value = String::new();
    let mut escaped = false;
    for ch in chars {
        if escaped {
            match ch {
                'n' => value.push('\n'),
                'r' => value.push('\r'),
                't' => value.push('\t'),
                '\\' => value.push('\\'),
                '"' => value.push('"'),
                other => value.push(other),
            }
            escaped = false;
        } else if ch == '\\' {
            escaped = true;
        } else if ch == '"' {
            return Ok(value);
        } else {
            value.push(ch);
        }
    }

    Err(Error::parse(
        path,
        format!("unterminated string at line {line_number}"),
    ))
}

fn escape_string(value: &str) -> String {
    let mut escaped = String::new();
    for ch in value.chars() {
        match ch {
            '\n' => escaped.push_str("\\n"),
            '\r' => escaped.push_str("\\r"),
            '\t' => escaped.push_str("\\t"),
            '\\' => escaped.push_str("\\\\"),
            '"' => escaped.push_str("\\\""),
            other => escaped.push(other),
        }
    }
    escaped
}

fn trim_comment(comment: &str) -> String {
    comment.strip_prefix(' ').unwrap_or(comment).to_string()
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
        assert_eq!(document, reparsed);
    }
}
