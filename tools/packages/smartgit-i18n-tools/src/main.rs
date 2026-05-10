use std::env;
use std::path::PathBuf;
use std::process;

use smartgit_i18n_core::{validate_translations, ValidationError, ValidationOptions};

fn main() {
    match run() {
        Ok(Exit::Success) => process::exit(0),
        Ok(Exit::ValidationFailed) => process::exit(1),
        Err(message) => {
            eprintln!("error: {message}");
            process::exit(2);
        }
    }
}

enum Exit {
    Success,
    ValidationFailed,
}

fn run() -> Result<Exit, String> {
    let args = env::args().skip(1).collect::<Vec<_>>();
    if args.first().map(String::as_str) != Some("validate") {
        return Err(usage());
    }

    let options = parse_validate_args(&args[1..])?;
    let report = validate_translations(&options).map_err(|error| error.to_string())?;

    if report.is_success() {
        println!("validation passed");
        return Ok(Exit::Success);
    }

    for error in &report.errors {
        print_error(error);
    }
    eprintln!("validation failed: {} error(s)", report.errors.len());

    Ok(Exit::ValidationFailed)
}

fn parse_validate_args(args: &[String]) -> Result<ValidationOptions, String> {
    let mut pot_path = None;
    let mut po_dir = None;
    let mut index = 0;

    while index < args.len() {
        match args[index].as_str() {
            "--pot" => {
                index += 1;
                let Some(value) = args.get(index) else {
                    return Err("--pot requires a path".to_string());
                };
                pot_path = Some(PathBuf::from(value));
            }
            "--po-dir" => {
                index += 1;
                let Some(value) = args.get(index) else {
                    return Err("--po-dir requires a path".to_string());
                };
                po_dir = Some(PathBuf::from(value));
            }
            "-h" | "--help" => return Err(usage()),
            unknown => return Err(format!("unknown argument: {unknown}\n\n{}", usage())),
        }
        index += 1;
    }

    Ok(ValidationOptions {
        pot_path: pot_path.ok_or_else(|| "--pot is required".to_string())?,
        po_dir: po_dir.ok_or_else(|| "--po-dir is required".to_string())?,
    })
}

fn print_error(error: &ValidationError) {
    eprintln!("error: {:?}", error.kind);
    eprintln!("  file: {}", error.file.display());
    if let Some(line) = error.line {
        eprintln!("  line: {line}");
    }
    if let Some(msgctxt) = &error.msgctxt {
        eprintln!("  msgctxt: {msgctxt}");
    }
    if let Some(msgid) = &error.msgid {
        eprintln!("  msgid: {msgid}");
    }
    eprintln!("  detail: {}", error.detail);
}

fn usage() -> String {
    "usage: smartgit-i18n-tools validate --pot <messages.pot> --po-dir <po-dir>".to_string()
}
