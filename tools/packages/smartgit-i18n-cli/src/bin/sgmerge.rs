use std::env;
use std::fs;
use std::path::{Path, PathBuf};
use std::process;

use smartgit_i18n_core::{import_mismatch_content, import_pot_content, import_unknown_content};

fn main() {
    match run() {
        Ok(()) => process::exit(0),
        Err(message) => {
            eprintln!("error: {message}");
            process::exit(2);
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
enum Destination {
    Stdout,
    Write,
    Output(PathBuf),
}

fn run() -> Result<(), String> {
    let args = env::args().skip(1).collect::<Vec<_>>();
    match args.first().map(String::as_str) {
        Some("unknown") => run_unknown(&args[1..]),
        Some("mismatch") => run_mismatch(&args[1..]),
        Some("po") => run_po(&args[1..]),
        Some("-h" | "--help") | None => {
            println!("{}", usage());
            Ok(())
        }
        Some(command) => Err(format!("unknown command: {command}\n\n{}", usage())),
    }
}

fn run_unknown(args: &[String]) -> Result<(), String> {
    let options = parse_input_merge_args(args, unknown_usage())?;
    let pot_content = read_to_string(&options.pot)?;
    let input_content = read_to_string(&options.input)?;
    let merged = import_unknown_content(&options.pot, &pot_content, &options.input, &input_content)
        .map_err(|error| error.to_string())?;

    write_single_result(&options.pot, &options.destination, &merged)
}

fn run_mismatch(args: &[String]) -> Result<(), String> {
    let options = parse_input_merge_args(args, mismatch_usage())?;
    let pot_content = read_to_string(&options.pot)?;
    let input_content = read_to_string(&options.input)?;
    let merged =
        import_mismatch_content(&options.pot, &pot_content, &options.input, &input_content)
            .map_err(|error| error.to_string())?;

    write_single_result(&options.pot, &options.destination, &merged)
}

fn run_po(args: &[String]) -> Result<(), String> {
    let options = parse_po_args(args)?;
    let pot_content = read_to_string(&options.pot)?;
    let po_files = collect_po_files(&options.po_dir)?;

    if po_files.is_empty() {
        return Err(format!("no PO files found in {}", options.po_dir.display()));
    }

    for po_path in po_files {
        let po_content = read_to_string(&po_path)?;
        let merged = import_pot_content(&po_path, &po_content, &options.pot, &pot_content)
            .map_err(|error| error.to_string())?;
        write_po_result(&po_path, &options.destination, &merged)?;
    }

    Ok(())
}

#[derive(Debug, Clone)]
struct InputMergeOptions {
    pot: PathBuf,
    input: PathBuf,
    destination: Destination,
}

#[derive(Debug, Clone)]
struct PoOptions {
    pot: PathBuf,
    po_dir: PathBuf,
    destination: Destination,
}

fn parse_input_merge_args(args: &[String], usage: String) -> Result<InputMergeOptions, String> {
    if args.iter().any(|arg| arg == "-h" || arg == "--help") {
        println!("{usage}");
        process::exit(0);
    }

    let mut pot = None;
    let mut input = None;
    let mut destination = Destination::Stdout;
    let mut index = 0;

    while index < args.len() {
        match args[index].as_str() {
            "--pot" => {
                index += 1;
                pot = Some(required_value(args, index, "--pot")?);
            }
            "--input" => {
                index += 1;
                input = Some(required_value(args, index, "--input")?);
            }
            "--write" => {
                ensure_stdout_destination(&destination)?;
                destination = Destination::Write;
            }
            "--output" => {
                ensure_stdout_destination(&destination)?;
                index += 1;
                destination = Destination::Output(required_value(args, index, "--output")?);
            }
            unknown => return Err(format!("unknown argument: {unknown}\n\n{usage}")),
        }
        index += 1;
    }

    Ok(InputMergeOptions {
        pot: pot.ok_or_else(|| "--pot is required".to_string())?,
        input: input.ok_or_else(|| "--input is required".to_string())?,
        destination,
    })
}

fn parse_po_args(args: &[String]) -> Result<PoOptions, String> {
    if args.iter().any(|arg| arg == "-h" || arg == "--help") {
        println!("{}", po_usage());
        process::exit(0);
    }

    let mut pot = None;
    let mut po_dir = None;
    let mut destination = Destination::Stdout;
    let mut index = 0;

    while index < args.len() {
        match args[index].as_str() {
            "--pot" => {
                index += 1;
                pot = Some(required_value(args, index, "--pot")?);
            }
            "--po-dir" => {
                index += 1;
                po_dir = Some(required_value(args, index, "--po-dir")?);
            }
            "--write" => {
                ensure_stdout_destination(&destination)?;
                destination = Destination::Write;
            }
            "--output" => {
                ensure_stdout_destination(&destination)?;
                index += 1;
                destination = Destination::Output(required_value(args, index, "--output")?);
            }
            unknown => return Err(format!("unknown argument: {unknown}\n\n{}", po_usage())),
        }
        index += 1;
    }

    Ok(PoOptions {
        pot: pot.ok_or_else(|| "--pot is required".to_string())?,
        po_dir: po_dir.ok_or_else(|| "--po-dir is required".to_string())?,
        destination,
    })
}

fn ensure_stdout_destination(destination: &Destination) -> Result<(), String> {
    if *destination == Destination::Stdout {
        Ok(())
    } else {
        Err("--write and --output are mutually exclusive".to_string())
    }
}

fn required_value(args: &[String], index: usize, name: &str) -> Result<PathBuf, String> {
    args.get(index)
        .map(PathBuf::from)
        .ok_or_else(|| format!("{name} requires a path"))
}

fn read_to_string(path: &Path) -> Result<String, String> {
    fs::read_to_string(path).map_err(|source| format!("I/O error for {}: {source}", path.display()))
}

fn write_single_result(
    path: &Path,
    destination: &Destination,
    content: &str,
) -> Result<(), String> {
    match destination {
        Destination::Stdout => {
            println!("{content}");
            Ok(())
        }
        Destination::Write => write_file(path, content),
        Destination::Output(output) => write_file(output, content),
    }
}

fn write_po_result(path: &Path, destination: &Destination, content: &str) -> Result<(), String> {
    match destination {
        Destination::Stdout => {
            println!("--- {} ---", path.display());
            println!("{content}");
            Ok(())
        }
        Destination::Write => write_file(path, content),
        Destination::Output(output_dir) => {
            fs::create_dir_all(output_dir)
                .map_err(|source| format!("I/O error for {}: {source}", output_dir.display()))?;
            let file_name = path
                .file_name()
                .ok_or_else(|| format!("missing file name for {}", path.display()))?;
            write_file(&output_dir.join(file_name), content)
        }
    }
}

fn write_file(path: &Path, content: &str) -> Result<(), String> {
    fs::write(path, content).map_err(|source| format!("I/O error for {}: {source}", path.display()))
}

fn collect_po_files(po_dir: &Path) -> Result<Vec<PathBuf>, String> {
    let mut files = Vec::new();
    let entries = fs::read_dir(po_dir)
        .map_err(|source| format!("I/O error for {}: {source}", po_dir.display()))?;

    for entry in entries {
        let entry =
            entry.map_err(|source| format!("I/O error for {}: {source}", po_dir.display()))?;
        let path = entry.path();
        if path.extension().and_then(|value| value.to_str()) == Some("po") {
            files.push(path);
        }
    }

    files.sort();
    Ok(files)
}

fn usage() -> String {
    [
        "usage: sgmerge <command>",
        "",
        "commands:",
        "  unknown --pot <messages.pot> --input <unknown-file> [--write|--output <path>]",
        "  mismatch --pot <messages.pot> --input <mismatch-file> [--write|--output <path>]",
        "  po --pot <messages.pot> --po-dir <po-dir> [--write|--output <dir>]",
    ]
    .join("\n")
}

fn unknown_usage() -> String {
    "usage: sgmerge unknown --pot <messages.pot> --input <unknown-file> [--write|--output <path>]"
        .to_string()
}

fn mismatch_usage() -> String {
    "usage: sgmerge mismatch --pot <messages.pot> --input <mismatch-file> [--write|--output <path>]"
        .to_string()
}

fn po_usage() -> String {
    "usage: sgmerge po --pot <messages.pot> --po-dir <po-dir> [--write|--output <dir>]".to_string()
}
