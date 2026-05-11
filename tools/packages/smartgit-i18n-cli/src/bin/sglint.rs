use std::env;
use std::path::PathBuf;
use std::process;

use smartgit_i18n_core::{
    format_paths, validate_translations, FormatMode, ValidationError, ValidationOptions,
};

fn main() {
    match run() {
        Ok(Exit::Success) => process::exit(0),
        Ok(Exit::LintFailed) => process::exit(1),
        Err(message) => {
            eprintln!("error: {message}");
            process::exit(2);
        }
    }
}

enum Exit {
    Success,
    LintFailed,
}

fn run() -> Result<Exit, String> {
    let args = env::args().skip(1).collect::<Vec<_>>();
    match args.first().map(String::as_str) {
        Some("check") => run_check(&args[1..]),
        Some("fmt") => run_fmt(&args[1..]),
        Some("-h" | "--help") => {
            println!("{}", usage());
            Ok(Exit::Success)
        }
        Some(command) => Err(format!("unknown command: {command}\n\n{}", usage())),
        None => Err(usage()),
    }
}

fn run_fmt(args: &[String]) -> Result<Exit, String> {
    if args.iter().any(|arg| arg == "-h" || arg == "--help") {
        println!("{}", fmt_usage());
        return Ok(Exit::Success);
    }

    let (mode, paths) = parse_fmt_args(args)?;
    let report = format_paths(&paths, mode).map_err(|error| error.to_string())?;

    if report.is_success() {
        println!("format check passed");
        return Ok(Exit::Success);
    }

    for path in &report.changed_files {
        eprintln!("needs formatting: {path}");
    }

    if mode == FormatMode::Write {
        eprintln!("formatted {} file(s)", report.changed_files.len());
        Ok(Exit::Success)
    } else {
        eprintln!(
            "format check failed: {} file(s)",
            report.changed_files.len()
        );
        Ok(Exit::LintFailed)
    }
}

fn run_check(args: &[String]) -> Result<Exit, String> {
    if args.iter().any(|arg| arg == "-h" || arg == "--help") {
        println!("{}", check_usage());
        return Ok(Exit::Success);
    }

    let options = parse_check_args(args)?;
    let report = validate_translations(&options).map_err(|error| error.to_string())?;

    if report.is_success() {
        println!("lint passed");
        return Ok(Exit::Success);
    }

    for error in &report.errors {
        print_error(error);
    }
    eprintln!("lint failed: {} error(s)", report.errors.len());

    Ok(Exit::LintFailed)
}

fn parse_fmt_args(args: &[String]) -> Result<(FormatMode, Vec<PathBuf>), String> {
    let mut mode = None;
    let mut paths = Vec::new();

    for arg in args {
        match arg.as_str() {
            "--check" => {
                if mode.replace(FormatMode::Check).is_some() {
                    return Err("only one of --check or --write may be specified".to_string());
                }
            }
            "--write" => {
                if mode.replace(FormatMode::Write).is_some() {
                    return Err("only one of --check or --write may be specified".to_string());
                }
            }
            unknown if unknown.starts_with('-') => {
                return Err(format!("unknown argument: {unknown}\n\n{}", fmt_usage()));
            }
            path => paths.push(PathBuf::from(path)),
        }
    }

    if paths.is_empty() {
        return Err(format!("at least one file is required\n\n{}", fmt_usage()));
    }

    Ok((
        mode.ok_or_else(|| "one of --check or --write is required".to_string())?,
        paths,
    ))
}

fn parse_check_args(args: &[String]) -> Result<ValidationOptions, String> {
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
            unknown => return Err(format!("unknown argument: {unknown}\n\n{}", check_usage())),
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
    format!(
        "{}\n\n{}",
        "usage: sglint <command>",
        "commands:\n  check --pot <messages.pot> --po-dir <po-dir>\n  fmt (--check|--write) <files...>"
    )
}

fn check_usage() -> String {
    "usage: sglint check --pot <messages.pot> --po-dir <po-dir>".to_string()
}

fn fmt_usage() -> String {
    "usage: sglint fmt (--check|--write) <files...>".to_string()
}
