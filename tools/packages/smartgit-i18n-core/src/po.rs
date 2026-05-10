use std::path::Path;

use crate::Error;

#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct PoEntry {
    pub(crate) line: usize,
    pub(crate) msgctxt: Option<String>,
    pub(crate) msgid: String,
    pub(crate) msgstr: String,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Field {
    Msgctxt,
    Msgid,
    Msgstr,
}

#[derive(Debug, Default)]
struct EntryBuilder {
    line: usize,
    msgctxt: Option<String>,
    msgid: Option<String>,
    msgstr: Option<String>,
    current_field: Option<Field>,
}

impl EntryBuilder {
    fn has_content(&self) -> bool {
        self.msgctxt.is_some() || self.msgid.is_some() || self.msgstr.is_some()
    }

    fn push(&mut self, path: &Path, field: Field, value: String, line: usize) -> Result<(), Error> {
        if !self.has_content() {
            self.line = line;
        }

        self.current_field = Some(field);
        match field {
            Field::Msgctxt => {
                if self.msgctxt.is_some() {
                    return Err(Error::parse(
                        path,
                        format!("duplicate msgctxt at line {line}"),
                    ));
                }
                self.msgctxt = Some(value);
            }
            Field::Msgid => {
                if self.msgid.is_some() {
                    return Err(Error::parse(
                        path,
                        format!("duplicate msgid at line {line}"),
                    ));
                }
                self.msgid = Some(value);
            }
            Field::Msgstr => {
                if self.msgstr.is_some() {
                    return Err(Error::parse(
                        path,
                        format!("duplicate msgstr at line {line}"),
                    ));
                }
                self.msgstr = Some(value);
            }
        }

        Ok(())
    }

    fn append(&mut self, path: &Path, value: String, line: usize) -> Result<(), Error> {
        match self.current_field {
            Some(Field::Msgctxt) => {
                self.msgctxt
                    .get_or_insert_with(String::new)
                    .push_str(&value);
            }
            Some(Field::Msgid) => {
                self.msgid.get_or_insert_with(String::new).push_str(&value);
            }
            Some(Field::Msgstr) => {
                self.msgstr.get_or_insert_with(String::new).push_str(&value);
            }
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

        let entry = PoEntry {
            line: self.line,
            msgctxt: self.msgctxt.take(),
            msgid: self.msgid.take().unwrap_or_default(),
            msgstr: self.msgstr.take().unwrap_or_default(),
        };
        self.line = 0;
        self.current_field = None;
        Some(entry)
    }
}

pub(crate) fn parse_po(path: &Path, content: &str) -> Result<Vec<PoEntry>, Error> {
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

        if line.starts_with('#') {
            continue;
        }

        if let Some(value) = parse_field(line, "msgctxt", path, line_number)? {
            builder.push(path, Field::Msgctxt, value, line_number)?;
        } else if let Some(value) = parse_field(line, "msgid", path, line_number)? {
            builder.push(path, Field::Msgid, value, line_number)?;
        } else if let Some(value) = parse_field(line, "msgstr", path, line_number)? {
            builder.push(path, Field::Msgstr, value, line_number)?;
        } else if line.starts_with('"') {
            let value = parse_quoted(line, path, line_number)?;
            builder.append(path, value, line_number)?;
        }
    }

    if let Some(entry) = builder.finish() {
        entries.push(entry);
    }

    Ok(entries)
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
}
