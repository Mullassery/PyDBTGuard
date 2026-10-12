use thiserror::Error;

/// Errors produced while reading dbt artifacts or building a report.
#[derive(Debug, Error)]
pub enum Error {
    #[error("failed to parse {artifact} JSON: {source}")]
    Parse {
        artifact: &'static str,
        #[source]
        source: serde_json::Error,
    },

    #[error("failed to parse run-history line {line}: {source}")]
    HistoryParse {
        line: usize,
        #[source]
        source: serde_json::Error,
    },

    #[error("failed to serialize report: {source}")]
    Serialize {
        #[source]
        source: serde_json::Error,
    },

    #[error("model not found in manifest: {0}")]
    ModelNotFound(String),

    #[error("invalid argument: {0}")]
    Invalid(String),
}

pub type Result<T> = std::result::Result<T, Error>;

impl Error {
    pub(crate) fn parse(artifact: &'static str, source: serde_json::Error) -> Self {
        Error::Parse { artifact, source }
    }
}
