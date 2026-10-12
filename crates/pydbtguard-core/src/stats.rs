//! Failure prediction and reliability scoring, driven entirely by real,
//! accumulated `dbt test` outcomes (a `Vec<bool>` per test, oldest first,
//! where `true` means the test genuinely failed in that run).
//!
//! This is deliberately simple and fully documented: it is *not* machine
//! learning. `failure_probability` is the observed failure rate over the real
//! recorded runs, `confidence` is a step function of sample size, and the
//! reliability score is `100 - failure_rate*100`, downgraded to DANGEROUS if
//! the most recent run failed.

use serde::Serialize;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum RiskLevel {
    Unknown,
    Stable,
    AtRisk,
    Dangerous,
}

#[derive(Debug, Clone, Serialize)]
pub struct Prediction {
    pub failure_probability: Option<f64>,
    pub confidence: Option<f64>,
    pub reliability_score: Option<u8>,
    pub risk_level: RiskLevel,
    pub runs: usize,
    pub failures: usize,
    pub last_run_failed: Option<bool>,
    /// True when the test has both passed and failed, with at least two
    /// pass/fail transitions (i.e. genuinely flaky, not just always-passing
    /// or always-failing).
    pub flaky: bool,
    pub note: String,
}

/// Confidence is a documented step function of how many real runs were
/// observed; a single run is weak evidence, 30+ is treated as strong.
fn confidence_for(runs: usize) -> f64 {
    match runs {
        0 => unreachable!(),
        1..=6 => 0.50,
        7..=13 => 0.65,
        14..=29 => 0.80,
        _ => 0.95,
    }
}

fn is_flaky(history: &[bool]) -> bool {
    let mut transitions = 0usize;
    for pair in history.windows(2) {
        if pair[0] != pair[1] {
            transitions += 1;
        }
    }
    let has_fail = history.iter().any(|&f| f);
    let has_pass = history.iter().any(|&f| !f);
    transitions >= 2 && has_pass && has_fail
}

/// Predict failure for a single test from its real pass/fail history.
pub fn predict(history: &[bool]) -> Prediction {
    let runs = history.len();
    let failures = history.iter().filter(|&&failed| failed).count();

    if runs == 0 {
        return Prediction {
            failure_probability: None,
            confidence: None,
            reliability_score: None,
            risk_level: RiskLevel::Unknown,
            runs: 0,
            failures: 0,
            last_run_failed: None,
            flaky: false,
            note: "No recorded dbt runs for this test yet; run 'dbt test' \
                   (or 'dbt build') and re-run analyze to accumulate history."
                .to_string(),
        };
    }

    let failure_rate = failures as f64 / runs as f64;
    let score = (100.0 - failure_rate * 100.0).round() as u8;
    let last_run_failed = history.last().copied();

    let risk_level = if last_run_failed == Some(true) || score < 50 {
        RiskLevel::Dangerous
    } else if score < 80 {
        RiskLevel::AtRisk
    } else {
        RiskLevel::Stable
    };

    let mut note = format!(
        "Based on {runs} recorded run(s): {failures} failure(s), failure rate {:.0}%.",
        failure_rate * 100.0
    );
    if last_run_failed == Some(true) {
        note.push_str(" The most recent recorded run FAILED.");
    }

    Prediction {
        failure_probability: Some(failure_rate),
        confidence: Some(confidence_for(runs)),
        reliability_score: Some(score),
        risk_level,
        runs,
        failures,
        last_run_failed,
        flaky: is_flaky(history),
        note,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn empty_history_is_unknown_not_fabricated() {
        let p = predict(&[]);
        assert_eq!(p.risk_level, RiskLevel::Unknown);
        assert!(p.failure_probability.is_none());
        assert!(p.reliability_score.is_none());
        assert!(p.note.contains("No recorded dbt runs"));
    }

    #[test]
    fn all_passing_is_stable() {
        let p = predict(&[false, false, false, false]);
        assert_eq!(p.failure_probability, Some(0.0));
        assert_eq!(p.reliability_score, Some(100));
        assert_eq!(p.risk_level, RiskLevel::Stable);
        assert!(!p.flaky);
    }

    #[test]
    fn last_run_failure_is_dangerous_even_with_low_rate() {
        let mut history = vec![false; 19];
        history.push(true);
        let p = predict(&history);
        assert!((p.failure_probability.unwrap() - 0.05).abs() < 1e-9);
        assert_eq!(p.last_run_failed, Some(true));
        assert_eq!(p.risk_level, RiskLevel::Dangerous);
    }

    #[test]
    fn flaky_requires_transitions_and_both_outcomes() {
        assert!(predict(&[true, false, true, false]).flaky);
        assert!(!predict(&[false, false, false, false]).flaky);
        assert!(!predict(&[true, true, true]).flaky);
    }

    #[test]
    fn confidence_steps_with_sample_size() {
        assert_eq!(predict(&[false]).confidence, Some(0.50));
        assert_eq!(predict(&[false; 15]).confidence, Some(0.80));
        assert_eq!(predict(&[false; 40]).confidence, Some(0.95));
    }
}
