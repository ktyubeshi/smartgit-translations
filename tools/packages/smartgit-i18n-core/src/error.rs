use std::fmt;
use std::io;
use std::path::PathBuf;

#[derive(Debug)]
pub enum Error {
    Io { path: PathBuf, source: io::Error },
    InvalidInput(String),
    Parse { path: PathBuf, message: String },
}

impl Error {
    pub(crate) fn io(path: impl Into<PathBuf>, source: io::Error) -> Self {
        Self::Io {
            path: path.into(),
            source,
        }
    }

    pub(crate) fn parse(path: impl Into<PathBuf>, message: impl Into<String>) -> Self {
        Self::Parse {
            path: path.into(),
            message: message.into(),
        }
    }
}

impl fmt::Display for Error {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Error::Io { path, source } => {
                write!(f, "I/O error for {}: {source}", path.display())
            }
            Error::InvalidInput(message) => write!(f, "{message}"),
            Error::Parse { path, message } => {
                write!(f, "parse error in {}: {message}", path.display())
            }
        }
    }
}

impl std::error::Error for Error {}
