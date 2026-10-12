//! Historical reliability from real accumulated `dbt` run history.
//!
//! Input is the tool's own append-only history file: one JSON object per line,
//! each the real outcome of one `dbt test`/`dbt build` run (see
//! `model::RunHistorySnapshot`). Everything produced here is computed from
//! those real outcomes — pass rate, volatility/transitions, flakiness, streaks,
//! mean-time-between-failures (in runs), and a first-half-vs-second-half trend.

use crate::error::{Error, Result};
use crate::model::RunHistorySnapshot;
use serde::Serialize;

#[derive(Debug, Clone, Serialize)]
pub struct TestHistory {
    pub test_id: String,
    pub runs: usize,
    pub passes: usize,
    pub failures: usize,
    pub pass_rate: f64,
    pub transitions: usize,
    pub flaky: bool,
    pub longest_pass_streak: usize,
    pub current_pass_streak: usize,
    pub last_run_failed: Option<bool>,
    /// Mean runs between failures, if the test has ever failed.
    pub mtbf_runs: Option<f64>,
    pub trend: String,
}

#[derive(Debug, Clone, Serialize)]
pub struct HistoryReport {
    pub total_runs: usize,
    pub total_tests: usize,
    pub flaky_count: usize,
    pub tests: Vec<TestHistory>,
}

/// Parse the accumulated history file into per-test chronological outcome
/// vectors. `skipped` runs and runs where the test is absent are omitted; a
/// test only accumulates a data point when dbt actually reported pass or fail.
pub fn parse(history_jsonl: &str) -> Result<Vec<(String, Vec<bool>)>> {
    let mut order: Vec<String> = Vec::new();
    let mut history: std::collections::HashMap<String, Vec<bool>> =
        std::collections::HashMap::new();

    for (idx, raw) in history_jsonl.lines().enumerate() {
        let line = raw.trim();
        if line.is_empty() {
            continue;
        }
        let snapshot: RunHistorySnapshot =
            serde_json::from_str(line).map_err(|source| Error::HistoryParse {
                line: idx + 1,
                source,
            })?;

        for (test_id, status) in snapshot.results {
            let outcome = match status.as_str() {
                "pass" => Some(false),
                "fail" | "error" => Some(true),
                _ => None, // skipped / unknown: not a real pass or fail
            };
            if let Some(failed) = outcome {
                if !history.contains_key(&test_id) {
                    order.push(test_id.clone());
                }
                history.entry(test_id).or_default().push(failed);
            }
        }
    }

    Ok(order
        .into_iter()
        .filter_map(|id| history.remove(&id).map(|h| (id, h)))
        .collect())
}

/// Summarize one test's real outcome history.
pub fn summarize(test_id: &str, history: &[bool]) -> TestHistory {
    let runs = history.len();
    let failures = history.iter().filter(|&&f| f).count();
    let passes = runs - failures;
    let pass_rate = if runs == 0 {
        0.0
    } else {
        passes as f64 / runs as f64
    };

    let transitions = history.windows(2).filter(|w| w[0] != w[1]).count();
    let has_both = failures > 0 && passes > 0;
    let flaky = has_both && transitions >= 2;

    let mut longest = 0usize;
    let mut run = 0usize;
    for &failed in history {
        if failed {
            run = 0;
        } else {
            run += 1;
            longest = longest.max(run);
        }
    }
    let current = run;

    let mtbf_runs = if failures > 0 {
        Some(runs as f64 / failures as f64)
    } else {
        None
    };

    TestHistory {
        test_id: test_id.to_string(),
        runs,
        passes,
        failures,
        pass_rate,
        transitions,
        flaky,
        longest_pass_streak: longest,
        current_pass_streak: current,
        last_run_failed: history.last().copied(),
        mtbf_runs,
        trend: trend(history),
    }
}

/// Compare the failure rate of the first half of the history against the
/// second half. Needs at least 4 runs to say anything; otherwise "stable".
fn trend(history: &[bool]) -> String {
    if history.len() < 4 {
        return "stable".to_string();
    }
    let mid = history.len() / 2;
    let (first, second) = history.split_at(mid);
    let rate = |s: &[bool]| {
        if s.is_empty() {
            0.0
        } else {
            s.iter().filter(|&&f| f).count() as f64 / s.len() as f64
        }
    };
    let (a, b) = (rate(first), rate(second));
    if b > a + 0.05 {
        "degrading".to_string()
    } else if a > b + 0.05 {
        "improving".to_string()
    } else {
        "stable".to_string()
    }
}

/// Build the full history report from the accumulated history file.
pub fn analyze(history_jsonl: &str) -> Result<HistoryReport> {
    let parsed = parse(history_jsonl)?;
    let total_runs = history_jsonl
        .lines()
        .filter(|l| !l.trim().is_empty())
        .count();

    let mut tests: Vec<TestHistory> = parsed.iter().map(|(id, h)| summarize(id, h)).collect();

    tests.sort_by(|a, b| {
        b.transitions
            .cmp(&a.transitions)
            .then_with(|| b.failures.cmp(&a.failures))
            .then_with(|| a.test_id.cmp(&b.test_id))
    });

    Ok(HistoryReport {
        total_runs,
        total_tests: tests.len(),
        flaky_count: tests.iter().filter(|t| t.flaky).count(),
        tests,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    const HISTORY: &str = r#"{"generated_at":"2026-01-01T00:00:00Z","results":{"test.pkg.a":"fail","test.pkg.b":"pass"}}
{"generated_at":"2026-01-02T00:00:00Z","results":{"test.pkg.a":"pass","test.pkg.b":"pass"}}
{"generated_at":"2026-01-03T00:00:00Z","results":{"test.pkg.a":"fail","test.pkg.b":"skipped"}}
{"generated_at":"2026-01-04T00:00:00Z","results":{"test.pkg.a":"pass","test.pkg.b":"pass"}}
{"generated_at":"2026-01-05T00:00:00Z","results":{"test.pkg.a":"fail","test.pkg.b":"pass"}}"#;

    #[test]
    fn accumulates_real_outcomes_and_skips_skipped() {
        let parsed = parse(HISTORY).unwrap();
        let a = parsed.iter().find(|(id, _)| id == "test.pkg.a").unwrap();
        assert_eq!(a.1, vec![true, false, true, false, true]);
        let b = parsed.iter().find(|(id, _)| id == "test.pkg.b").unwrap();
        assert_eq!(b.1, vec![false, false, false, false]); // skipped omitted
    }

    #[test]
    fn detects_flaky_and_streaks() {
        let report = analyze(HISTORY).unwrap();
        assert_eq!(report.total_runs, 5);
        let a = report
            .tests
            .iter()
            .find(|t| t.test_id == "test.pkg.a")
            .unwrap();
        assert!(a.flaky);
        assert_eq!(a.failures, 3);
        assert_eq!(a.passes, 2);
        assert_eq!(a.transitions, 4);
        assert_eq!(a.longest_pass_streak, 1);
        assert_eq!(a.current_pass_streak, 0);
        assert_eq!(a.last_run_failed, Some(true));
    }

    #[test]
    fn malformed_line_reports_line_number() {
        let err = parse("{\"results\":{}}\nnot json").unwrap_err();
        assert!(matches!(err, Error::HistoryParse { line: 2, .. }));
    }

    #[test]
    fn empty_history_is_empty_report() {
        let report = analyze("").unwrap();
        assert_eq!(report.total_runs, 0);
        assert_eq!(report.total_tests, 0);
    }
}
