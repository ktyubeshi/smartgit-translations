use std::collections::{BTreeMap, BTreeSet};
use std::fs;
use std::path::{Path, PathBuf};

use crate::po::{parse_po, PoEntry};
use crate::Error;

#[derive(Debug, Clone)]
pub struct ValidationOptions {
    pub pot_path: PathBuf,
    pub po_dir: PathBuf,
}

#[derive(Debug, Default, Clone)]
pub struct ValidationReport {
    pub errors: Vec<ValidationError>,
    pub warnings: Vec<ValidationWarning>,
}

impl ValidationReport {
    pub fn is_success(&self) -> bool {
        self.errors.is_empty()
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ValidationError {
    pub kind: ValidationErrorKind,
    pub file: PathBuf,
    pub line: Option<usize>,
    pub msgctxt: Option<String>,
    pub msgid: Option<String>,
    pub detail: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ValidationErrorKind {
    DuplicateMessage,
    MsgctxtSuffix,
    PlaceholderMismatch,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ValidationWarning {
    pub file: PathBuf,
    pub detail: String,
}

pub fn validate_translations(options: &ValidationOptions) -> Result<ValidationReport, Error> {
    if !options.pot_path.is_file() {
        return Err(Error::InvalidInput(format!(
            "POT file does not exist: {}",
            options.pot_path.display()
        )));
    }

    if !options.po_dir.is_dir() {
        return Err(Error::InvalidInput(format!(
            "PO directory does not exist: {}",
            options.po_dir.display()
        )));
    }

    let mut files = collect_po_files(&options.po_dir)?;
    files.push(options.pot_path.clone());
    files.sort();
    files.dedup();

    let mut report = ValidationReport::default();
    for file in files {
        let content = fs::read_to_string(&file).map_err(|source| Error::io(&file, source))?;
        let entries = parse_po(&file, &content)?;
        validate_entries(&mut report, &file, &entries);
    }

    Ok(report)
}

fn collect_po_files(po_dir: &Path) -> Result<Vec<PathBuf>, Error> {
    let mut files = Vec::new();
    let entries = fs::read_dir(po_dir).map_err(|source| Error::io(po_dir, source))?;

    for entry in entries {
        let entry = entry.map_err(|source| Error::io(po_dir, source))?;
        let path = entry.path();
        if path.extension().and_then(|value| value.to_str()) == Some("po") {
            files.push(path);
        }
    }

    if files.is_empty() {
        return Err(Error::InvalidInput(format!(
            "No PO files found in {}",
            po_dir.display()
        )));
    }

    files.sort();
    Ok(files)
}

fn validate_entries(report: &mut ValidationReport, file: &Path, entries: &[PoEntry]) {
    let mut seen: BTreeMap<(Option<String>, String), usize> = BTreeMap::new();

    for entry in entries {
        let key = (entry.msgctxt.clone(), entry.msgid.clone());
        if let Some(first_line) = seen.insert(key, entry.line) {
            report.errors.push(ValidationError {
                kind: ValidationErrorKind::DuplicateMessage,
                file: file.to_path_buf(),
                line: Some(entry.line),
                msgctxt: entry.msgctxt.clone(),
                msgid: Some(entry.msgid.clone()),
                detail: format!("duplicate msgctxt/msgid pair; first seen at line {first_line}"),
            });
        }

        if let Some(msgctxt) = &entry.msgctxt {
            if looks_like_unoptimized_msgctxt(msgctxt) {
                report.errors.push(ValidationError {
                    kind: ValidationErrorKind::MsgctxtSuffix,
                    file: file.to_path_buf(),
                    line: Some(entry.line),
                    msgctxt: Some(msgctxt.clone()),
                    msgid: Some(entry.msgid.clone()),
                    detail: "msgctxt containing quoted SmartGit text should end with ':'"
                        .to_string(),
                });
            }
        }

        if !entry.msgstr.is_empty() {
            let msgid_placeholders = placeholders(&entry.msgid);
            let msgstr_placeholders = placeholders(&entry.msgstr);
            if msgid_placeholders != msgstr_placeholders {
                report.errors.push(ValidationError {
                    kind: ValidationErrorKind::PlaceholderMismatch,
                    file: file.to_path_buf(),
                    line: Some(entry.line),
                    msgctxt: entry.msgctxt.clone(),
                    msgid: Some(entry.msgid.clone()),
                    detail: format!(
                        "msgid placeholders: {}; msgstr placeholders: {}",
                        format_set(&msgid_placeholders),
                        format_set(&msgstr_placeholders)
                    ),
                });
            }
        }
    }
}

fn looks_like_unoptimized_msgctxt(msgctxt: &str) -> bool {
    msgctxt.contains('"') && !msgctxt.ends_with(':')
}

fn placeholders(text: &str) -> BTreeSet<String> {
    let mut placeholders = BTreeSet::new();
    let chars: Vec<char> = text.chars().collect();
    let mut index = 0;

    while index < chars.len() {
        if chars[index] == '$' {
            let start = index;
            index += 1;
            let digit_start = index;
            while index < chars.len() && chars[index].is_ascii_digit() {
                index += 1;
            }
            if index > digit_start {
                placeholders.insert(chars[start..index].iter().collect());
            }
        } else {
            index += 1;
        }
    }

    placeholders
}

fn format_set(values: &BTreeSet<String>) -> String {
    if values.is_empty() {
        return "<none>".to_string();
    }

    values.iter().cloned().collect::<Vec<_>>().join(", ")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn detects_placeholder_mismatch() {
        let entries = vec![PoEntry {
            line: 1,
            msgctxt: Some("ctx:".to_string()),
            msgid: "Hello $1 $2".to_string(),
            msgstr: "こんにちは $1".to_string(),
            ..PoEntry::default()
        }];
        let mut report = ValidationReport::default();

        validate_entries(&mut report, Path::new("sample.po"), &entries);

        assert_eq!(report.errors.len(), 1);
        assert_eq!(
            report.errors[0].kind,
            ValidationErrorKind::PlaceholderMismatch
        );
    }

    #[test]
    fn ignores_untranslated_placeholder_mismatch() {
        let entries = vec![PoEntry {
            line: 1,
            msgctxt: Some("ctx:".to_string()),
            msgid: "Hello $1".to_string(),
            msgstr: String::new(),
            ..PoEntry::default()
        }];
        let mut report = ValidationReport::default();

        validate_entries(&mut report, Path::new("sample.po"), &entries);

        assert!(report.errors.is_empty());
    }
}
