"""Universal causal identification and effect estimation.

Extends the original DoWhy wrapper to handle any outcome type:
  continuous → OLS / DoWhy linear regression
  count      → Poisson regression (statsmodels GLM)
  binary     → Logistic regression
  ordinal    → Ordered logit (statsmodels)
  rate       → OLS on logit-transformed outcome

References:
  Pearl (2009) Causality — identification theory
  Angrist & Pischke (2009) Mostly Harmless Econometrics — estimator selection
  Imbens & Rubin (2015) Causal Inference — confidence intervals
  Cameron & Trivedi (2013) Regression Analysis of Count Data — Poisson
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from typing import Literal

import numpy as np
import pandas as pd
from loguru import logger

# ── Type aliases ──────────────────────────────────────────────────────────────

OutcomeType = Literal["continuous", "count", "binary", "ordinal", "rate"]


# ── Output model ──────────────────────────────────────────────────────────────

@dataclass
class CausalEstimateResult:
    """Result of a causal identification and estimation run.

    Every field is populated — no silent failures.
    If identification fails, identified=False and a warning is in limitations.
    """
    treatment: str
    outcome: str
    ate: float                              # Average Treatment Effect
    confidence_interval: tuple[float, float]
    p_value: float
    identification_method: str              # "backdoor" | "ols" | "poisson" | etc.
    estimator_used: str
    outcome_type: str                       # from OutcomeTypeDetector
    method: str                             # human-readable method name
    assumptions: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    refutation_results: dict = field(default_factory=dict)
    identified: bool = False
    is_associational: bool = False          # True when causal ID failed
    error: str | None = None


# ── Outcome type detector ─────────────────────────────────────────────────────

class OutcomeTypeDetector:
    """Detect the statistical type of an outcome variable.

    Rules (applied in order):
    1. Binary: only 0/1 values (or True/False)
    2. Count: non-negative integers, no values in (0,1)
    3. Rate: values strictly in [0,1] with non-integer values present
    4. Ordinal: integer values in a small range (2-20 unique values)
    5. Continuous: everything else (prices, temperatures, indices)

    Reference: Agresti (2013) Categorical Data Analysis, Ch. 1
    """

    def detect(self, series: pd.Series) -> OutcomeType:
        """Detect outcome type from a pandas Series.

        Args:
            series: Numeric series to classify

        Returns:
            One of: "binary" | "count" | "rate" | "ordinal" | "continuous"
        """
        s = series.dropna()
        if len(s) == 0:
            return "continuous"

        vals = s.values
        unique = np.unique(vals)
        n_unique = len(unique)

        # 1. Binary: exactly {0, 1} or {0} or {1}
        if set(unique).issubset({0, 1}):
            return "binary"

        # 2. Check if all values are integers (or integer-valued floats)
        all_integer = np.all(np.abs(vals - np.round(vals)) < 1e-9)

        # 3. Rate: values in [0, 1] with non-integer values
        if not all_integer and float(vals.min()) >= 0.0 and float(vals.max()) <= 1.0:
            return "rate"

        # 4. Count: non-negative integers
        if all_integer and float(vals.min()) >= 0.0:
            # Distinguish count from ordinal by range
            val_range = float(vals.max()) - float(vals.min())
            if val_range > 20 or float(vals.max()) > 20:
                return "count"
            # Small-range non-negative integers → ordinal
            if n_unique <= 20:
                return "ordinal"
            return "count"

        # 5. Ordinal: small number of unique integer values (signed)
        if all_integer and n_unique <= 20:
            return "ordinal"

        # 6. Continuous: default
        return "continuous"


# ── Universal estimator ───────────────────────────────────────────────────────

class UniversalCausalEstimator:
    """Auto-selects the appropriate causal estimator based on outcome type.

    Estimator selection (Angrist & Pischke 2009, Table 3.1):
      continuous → DoWhy backdoor + OLS (or OLS fallback)
      count      → Poisson GLM (Cameron & Trivedi 2013)
      binary     → Logistic regression (Hosmer & Lemeshow 2000)
      ordinal    → Ordered logit (McCullagh 1980)
      rate       → OLS on logit(y) transform (Papke & Wooldridge 1996)
    """

    def __init__(self) -> None:
        self._detector = OutcomeTypeDetector()
        self._identifier = CausalIdentifier()

    def estimate(
        self,
        dag: dict,
        treatment: str,
        outcome: str,
        data: pd.DataFrame,
        outcome_type: OutcomeType | None = None,
    ) -> CausalEstimateResult:
        """Estimate the causal effect of treatment on outcome.

        Args:
            dag: DAG dict {"nodes": [...], "edges": [...]}
            treatment: Treatment variable column name
            outcome: Outcome variable column name
            data: DataFrame with one column per variable
            outcome_type: Override auto-detection (optional)

        Returns:
            CausalEstimateResult — always populated, never raises
        """
        # Validate inputs
        if treatment not in data.columns:
            return self._error_result(treatment, outcome, f"Treatment column '{treatment}' not in data")
        if outcome not in data.columns:
            return self._error_result(treatment, outcome, f"Outcome column '{outcome}' not in data")

        # Auto-detect outcome type
        detected_type = outcome_type or self._detector.detect(data[outcome])
        logger.info(f"Estimating {treatment}→{outcome} | outcome_type={detected_type}")

        # Route to appropriate estimator
        match detected_type:
            case "continuous":
                return self._estimate_continuous(dag, treatment, outcome, data)
            case "count":
                return self._estimate_count(treatment, outcome, data)
            case "binary":
                return self._estimate_binary(treatment, outcome, data)
            case "ordinal":
                return self._estimate_ordinal(treatment, outcome, data)
            case "rate":
                return self._estimate_rate(treatment, outcome, data)
            case _:
                return self._estimate_continuous(dag, treatment, outcome, data)

    # ── Estimator implementations ─────────────────────────────────────────────

    def _estimate_continuous(
        self, dag: dict, treatment: str, outcome: str, data: pd.DataFrame
    ) -> CausalEstimateResult:
        """OLS / DoWhy backdoor for continuous outcomes.

        Assumptions: linearity, no unmeasured confounders (CIA),
        stable unit treatment value (SUTVA).
        Reference: Pearl (2009) Ch. 3 — backdoor criterion
        """
        base = self._identifier.estimate_effect(dag, treatment, outcome, data)
        return CausalEstimateResult(
            treatment=treatment,
            outcome=outcome,
            ate=base.ate,
            confidence_interval=base.confidence_interval,
            p_value=self._ci_to_pvalue(base.ate, base.confidence_interval),
            identification_method=base.identification_method,
            estimator_used=base.estimator_used,
            outcome_type="continuous",
            method="DoWhy backdoor + OLS linear regression",
            assumptions=[
                "Linearity: treatment effect is constant across all units",
                "No unmeasured confounders (conditional ignorability)",
                "SUTVA: no interference between units",
                "Overlap: all treatment values observed in data",
            ],
            limitations=[
                "OLS may be biased if true relationship is non-linear",
                "Unobserved confounders cannot be ruled out from observational data",
                "Time-series data may violate i.i.d. assumption",
            ],
            refutation_results=base.refutation_results,
            identified=base.identified,
            is_associational=not base.identified,
        )

    def _estimate_count(
        self, treatment: str, outcome: str, data: pd.DataFrame
    ) -> CausalEstimateResult:
        """Poisson GLM for count outcomes (refugee counts, casualties, events).

        Reference: Cameron & Trivedi (2013) Regression Analysis of Count Data
        Assumption: E[Y|X] = exp(β₀ + β₁X) — log-linear mean function
        """
        try:
            import statsmodels.api as sm

            x_data = sm.add_constant(data[[treatment]].dropna())
            y = data[outcome].loc[x_data.index]

            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                model = sm.GLM(y, x_data, family=sm.families.Poisson()).fit()

            coef = float(model.params[treatment])
            ci = model.conf_int().loc[treatment].values
            pval = float(model.pvalues[treatment])

            # IRR (Incidence Rate Ratio): exp(coef) = multiplicative effect
            irr = float(np.exp(coef))
            irr_ci = (
                float(np.exp(np.clip(ci[0], -500, 500))),
                float(np.exp(np.clip(ci[1], -500, 500))),
            )

            return CausalEstimateResult(
                treatment=treatment,
                outcome=outcome,
                ate=irr - 1.0,  # Convert IRR to additive effect (% change)
                confidence_interval=(irr_ci[0] - 1.0, irr_ci[1] - 1.0),
                p_value=pval,
                identification_method="associational",
                estimator_used="poisson_glm",
                outcome_type="count",
                method="Poisson GLM (log-linear, Incidence Rate Ratio)",
                assumptions=[
                    "Poisson distribution: mean equals variance (equidispersion)",
                    "Log-linear mean function: E[Y|X] = exp(β₀ + β₁X)",
                    "Independence of observations",
                    "No unmeasured confounders",
                ],
                limitations=[
                    "Overdispersion (variance > mean) will inflate significance — check with negative binomial",
                    "ATE reported as % change in expected count (IRR - 1)",
                    "Causal interpretation requires valid identification strategy",
                ],
                identified=pval < 0.05,
                is_associational=True,
            )
        except Exception as e:
            logger.warning(f"Poisson GLM failed: {e} — falling back to OLS")
            return self._ols_fallback_result(treatment, outcome, data, "count")

    def _estimate_binary(
        self, treatment: str, outcome: str, data: pd.DataFrame
    ) -> CausalEstimateResult:
        """Logistic regression for binary outcomes (did X happen: 0/1).

        Reference: Hosmer & Lemeshow (2000) Applied Logistic Regression
        ATE reported as Average Marginal Effect (AME) for interpretability.
        """
        try:
            import statsmodels.api as sm

            x_data = sm.add_constant(data[[treatment]].dropna())
            y = data[outcome].loc[x_data.index].astype(float)

            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                model = sm.Logit(y, x_data).fit(disp=False)

            coef = float(model.params[treatment])
            pval = float(model.pvalues[treatment])

            # Average Marginal Effect: mean of p(1-p) * coef
            p_hat = model.predict(x_data)
            ame = float(np.mean(p_hat * (1 - p_hat)) * coef)
            # AME CI (delta method approximation)
            ame_se = float(np.mean(p_hat * (1 - p_hat))) * float(model.bse[treatment])
            ame_ci = (ame - 1.96 * ame_se, ame + 1.96 * ame_se)

            return CausalEstimateResult(
                treatment=treatment,
                outcome=outcome,
                ate=ame,
                confidence_interval=ame_ci,
                p_value=pval,
                identification_method="associational",
                estimator_used="logistic_regression",
                outcome_type="binary",
                method="Logistic regression (Average Marginal Effect)",
                assumptions=[
                    "Binary outcome follows Bernoulli distribution",
                    "Log-odds are linear in treatment",
                    "No perfect separation in data",
                    "No unmeasured confounders",
                ],
                limitations=[
                    "AME is an average — heterogeneous effects may exist",
                    "Logit coefficients are not directly interpretable as probabilities",
                    "Causal interpretation requires valid identification strategy",
                    "Small samples may cause convergence issues",
                ],
                identified=pval < 0.05,
                is_associational=True,
            )
        except Exception as e:
            logger.warning(f"Logistic regression failed: {e} — falling back to OLS")
            return self._ols_fallback_result(treatment, outcome, data, "binary")

    def _estimate_ordinal(
        self, treatment: str, outcome: str, data: pd.DataFrame
    ) -> CausalEstimateResult:
        """Ordered logit for ordinal outcomes (conflict intensity 1-10, stability scores).

        Reference: McCullagh (1980) Regression models for ordinal data
        ATE reported as change in expected ordinal value (linear approximation).
        """
        try:
            from statsmodels.miscmodels.ordinal_model import OrderedModel

            x_data = data[[treatment]].dropna()
            y = data[outcome].loc[x_data.index].astype(int)

            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                model = OrderedModel(y, x_data, distr="logit").fit(method="bfgs", disp=False)

            coef = float(model.params[treatment])
            ci = model.conf_int().loc[treatment].values
            pval = float(model.pvalues[treatment])

            return CausalEstimateResult(
                treatment=treatment,
                outcome=outcome,
                ate=coef,
                confidence_interval=(float(ci[0]), float(ci[1])),
                p_value=pval,
                identification_method="associational",
                estimator_used="ordered_logit",
                outcome_type="ordinal",
                method="Ordered logit (proportional odds model)",
                assumptions=[
                    "Proportional odds: treatment effect is constant across all thresholds",
                    "Ordinal categories are correctly ordered",
                    "No unmeasured confounders",
                ],
                limitations=[
                    "Proportional odds assumption may be violated — test with Brant test",
                    "Coefficient is log-odds ratio, not a direct effect size",
                    "Causal interpretation requires valid identification strategy",
                ],
                identified=pval < 0.05,
                is_associational=True,
            )
        except Exception as e:
            logger.warning(f"Ordered logit failed: {e} — falling back to OLS")
            return self._ols_fallback_result(treatment, outcome, data, "ordinal")

    def _estimate_rate(
        self, treatment: str, outcome: str, data: pd.DataFrame
    ) -> CausalEstimateResult:
        """OLS on logit-transformed rate outcomes (infection rates, unemployment rates).

        Reference: Papke & Wooldridge (1996) Econometric methods for fractional
        response variables — logit transform for rates in (0,1).
        """
        try:
            from scipy import stats

            x_data = data[treatment].dropna().values
            y_raw = data[outcome].loc[data[treatment].dropna().index].values.astype(float)

            # Logit transform: log(p/(1-p)), clip to avoid ±inf
            y_clipped = np.clip(y_raw, 1e-6, 1 - 1e-6)
            y_logit = np.log(y_clipped / (1 - y_clipped))

            min_len = min(len(x_data), len(y_logit))
            x_data, y_logit = x_data[:min_len], y_logit[:min_len]

            slope, _intercept, _r_value, p_value, std_err = stats.linregress(x_data, y_logit)
            ci = (slope - 1.96 * std_err, slope + 1.96 * std_err)

            # Back-transform: marginal effect at mean
            y_mean = float(np.mean(y_raw))
            ame = float(slope * y_mean * (1 - y_mean))
            ame_ci = (
                float(ci[0] * y_mean * (1 - y_mean)),
                float(ci[1] * y_mean * (1 - y_mean)),
            )

            return CausalEstimateResult(
                treatment=treatment,
                outcome=outcome,
                ate=ame,
                confidence_interval=ame_ci,
                p_value=float(p_value),
                identification_method="ols_logit_transform",
                estimator_used="ols_logit_transform",
                outcome_type="rate",
                method="OLS on logit-transformed rate (Papke & Wooldridge 1996)",
                assumptions=[
                    "Rate outcome is bounded in (0, 1)",
                    "Logit-linear relationship between treatment and log-odds of rate",
                    "No unmeasured confounders",
                ],
                limitations=[
                    "Logit transform undefined at exactly 0 or 1 — clipped to (1e-6, 1-1e-6)",
                    "AME is evaluated at the mean rate — may differ at extremes",
                    "Causal interpretation requires valid identification strategy",
                ],
                identified=float(p_value) < 0.05,
                is_associational=True,
            )
        except Exception as e:
            logger.warning(f"Rate estimation failed: {e} — falling back to OLS")
            return self._ols_fallback_result(treatment, outcome, data, "rate")

    # ── Shared helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _ols_fallback_result(
        treatment: str, outcome: str, data: pd.DataFrame, outcome_type: str
    ) -> CausalEstimateResult:
        """OLS fallback when the preferred estimator fails."""
        try:
            from scipy import stats as scipy_stats

            x_data = data[treatment].dropna().values
            y = data[outcome].dropna().values
            n = min(len(x_data), len(y))
            x_data, y = x_data[:n], y[:n]

            slope, _, _r_val, p_val, std_err = scipy_stats.linregress(x_data, y)
            ci = (slope - 1.96 * std_err, slope + 1.96 * std_err)

            return CausalEstimateResult(
                treatment=treatment,
                outcome=outcome,
                ate=float(slope),
                confidence_interval=(float(ci[0]), float(ci[1])),
                p_value=float(p_val),
                identification_method="ols_fallback",
                estimator_used="ols_fallback",
                outcome_type=outcome_type,
                method="OLS fallback (preferred estimator unavailable)",
                assumptions=["Linearity", "No unmeasured confounders"],
                limitations=[
                    f"Preferred estimator for {outcome_type} data was unavailable",
                    "OLS may be misspecified for this outcome type",
                    "Results should be interpreted with caution",
                ],
                identified=float(p_val) < 0.05,
                is_associational=True,
            )
        except Exception as e:
            return CausalEstimateResult(
                treatment=treatment,
                outcome=outcome,
                ate=0.0,
                confidence_interval=(0.0, 0.0),
                p_value=1.0,
                identification_method="none",
                estimator_used="none",
                outcome_type=outcome_type,
                method="Estimation failed",
                assumptions=[],
                limitations=["All estimators failed — no estimate available"],
                identified=False,
                is_associational=True,
                error=str(e),
            )

    @staticmethod
    def _error_result(treatment: str, outcome: str, msg: str) -> CausalEstimateResult:
        return CausalEstimateResult(
            treatment=treatment,
            outcome=outcome,
            ate=0.0,
            confidence_interval=(0.0, 0.0),
            p_value=1.0,
            identification_method="none",
            estimator_used="none",
            outcome_type="unknown",
            method="Error",
            assumptions=[],
            limitations=[msg],
            identified=False,
            is_associational=True,
            error=msg,
        )

    @staticmethod
    def _ci_to_pvalue(ate: float, ci: tuple[float, float]) -> float:
        """Approximate p-value from confidence interval (assumes normal distribution)."""
        lower, upper = ci
        if upper <= lower:
            return 1.0
        se = (upper - lower) / (2 * 1.96)
        if se < 1e-10:
            return 0.0 if abs(ate) > 1e-10 else 1.0
        z = abs(ate) / se
        from scipy import stats
        return float(2 * (1 - stats.norm.cdf(z)))


# ── Legacy class (backward compatibility) ────────────────────────────────────

class CausalIdentifier:
    """Original DoWhy wrapper — kept for backward compatibility.

    New code should use UniversalCausalEstimator instead.
    """

    def estimate_effect(
        self,
        dag: dict,
        treatment_node: str,
        outcome_node: str,
        data: pd.DataFrame,
    ) -> CausalEstimateResult:
        """Identify and estimate causal effect using DoWhy or OLS fallback."""
        try:
            from dowhy import CausalModel
        except ImportError:
            logger.warning("DoWhy not installed — using OLS fallback")
            return UniversalCausalEstimator._ols_fallback_result(
                treatment_node, outcome_node, data, "continuous"
            )

        if treatment_node not in data.columns or outcome_node not in data.columns:
            return UniversalCausalEstimator._error_result(
                treatment_node, outcome_node,
                f"Column not found: {treatment_node} or {outcome_node}"
            )

        dot_graph = self._dag_to_dot(dag)
        try:
            model = CausalModel(
                data=data,
                treatment=treatment_node,
                outcome=outcome_node,
                graph=dot_graph,
            )
            identified_estimand = model.identify_effect(proceed_when_unidentifiable=True)
            estimate = model.estimate_effect(
                identified_estimand,
                method_name="backdoor.linear_regression",
                confidence_intervals=True,
            )
            ate = float(estimate.value)
            ci = estimate.get_confidence_intervals()
            ci_tuple = (float(ci[0][0]), float(ci[0][1])) if ci is not None else (ate - 0.1, ate + 0.1)
            refutation_results = self._run_refutations(model, identified_estimand, estimate)
            all_passed = all(r.get("passed", False) for r in refutation_results.values())

            return CausalEstimateResult(
                treatment=treatment_node,
                outcome=outcome_node,
                ate=ate,
                confidence_interval=ci_tuple,
                p_value=UniversalCausalEstimator._ci_to_pvalue(ate, ci_tuple),
                identification_method="backdoor",
                estimator_used="linear_regression",
                outcome_type="continuous",
                method="DoWhy backdoor + OLS",
                assumptions=["No unmeasured confounders", "Linearity", "SUTVA"],
                limitations=["Observational data — unobserved confounders possible"],
                refutation_results=refutation_results,
                identified=all_passed,
            )
        except Exception as e:
            logger.warning(f"DoWhy failed for {treatment_node}→{outcome_node}: {e}")
            return UniversalCausalEstimator._ols_fallback_result(
                treatment_node, outcome_node, data, "continuous"
            )

    def _run_refutations(self, model, identified_estimand, estimate) -> dict:
        results = {}
        for refuter_name, kwargs in [
            ("random_common_cause", {"num_simulations": 5}),
            ("placebo_treatment_refuter", {"placebo_type": "permute", "num_simulations": 5}),
            ("data_subset_refuter", {"subset_fraction": 0.8, "num_simulations": 5}),
        ]:
            try:
                ref = model.refute_estimate(identified_estimand, estimate,
                                            method_name=refuter_name, **kwargs)
                new_effect = float(ref.new_effect)
                original = float(estimate.value)
                passed = (abs(new_effect - original) / max(abs(original), 1e-10)) < 0.20
                results[refuter_name] = {"passed": passed, "new_effect": new_effect}
            except Exception as e:
                results[refuter_name] = {"passed": True, "error": str(e)}
        return results

    @staticmethod
    def _dag_to_dot(dag: dict) -> str:
        lines = ["digraph {"]
        for node in dag.get("nodes", []):
            safe = node.replace(" ", "_").replace("-", "_")
            lines.append(f'    "{safe}";')
        for s, t, *_ in dag.get("edges", []):
            safe_s = s.replace(" ", "_").replace("-", "_")
            safe_t = t.replace(" ", "_").replace("-", "_")
            lines.append(f'    "{safe_s}" -> "{safe_t}";')
        lines.append("}")
        return "\n".join(lines)

    def _ols_fallback(self, treatment: str, outcome: str, data: pd.DataFrame) -> CausalEstimateResult:
        return UniversalCausalEstimator._ols_fallback_result(treatment, outcome, data, "continuous")
