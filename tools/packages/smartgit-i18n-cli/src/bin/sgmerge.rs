use std::env;
use std::process;

fn main() {
    match run() {
        Ok(()) => process::exit(0),
        Err(message) => {
            eprintln!("error: {message}");
            process::exit(2);
        }
    }
}

fn run() -> Result<(), String> {
    let args = env::args().skip(1).collect::<Vec<_>>();
    match args.first().map(String::as_str) {
        Some("-h" | "--help") | None => {
            println!("{}", usage());
            Ok(())
        }
        Some(command) => Err(format!(
            "sgmerge {command} is not implemented yet\n\n{}",
            usage()
        )),
    }
}

fn usage() -> String {
    [
        "usage: sgmerge <command>",
        "",
        "commands:",
        "  unknown   not implemented yet",
        "  mismatch  not implemented yet",
        "  po        not implemented yet",
    ]
    .join("\n")
}
