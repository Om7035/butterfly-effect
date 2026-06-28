/**
 * ModelQualityPanel - Display Tier 1+2 credibility metrics
 *
 * Shows:
 * - Brier score (probabilistic accuracy)
 * - Calibration error (stated vs actual accuracy)
 * - Model limitations and transparency notes
 */

import { AlertCircle, TrendingUp, Info } from "lucide-react";

interface ModelQualityData {
  brier_score: number;
  brier_rating: string;
  calibration_error: number;
  confidence_note: string;
}

interface CredibilityMetadata {
  tier_1_enabled: boolean;
  tier_2_enabled: boolean;
  chain_confidence_method: string;
  interval_basis: string;
}

interface ModelQualityPanelProps {
  modelQuality?: ModelQualityData;
  credibility?: CredibilityMetadata;
}

export default function ModelQualityPanel({
  modelQuality,
  credibility,
}: ModelQualityPanelProps) {
  if (!modelQuality && !credibility) return null;

  const brierRating = modelQuality?.brier_rating || "UNKNOWN";
  const brierColor =
    brierRating === "EXCELLENT" ? "text-green-600" :
    brierRating === "GOOD" ? "text-blue-600" :
    brierRating === "FAIR" ? "text-amber-600" :
    "text-red-600";

  const calibrationPercent = modelQuality
    ? Math.round(modelQuality.calibration_error * 100)
    : 0;

  return (
    <div className="mt-6 p-4 bg-slate-900 border border-slate-700 rounded-lg">
      {/* Header */}
      <div className="flex items-center gap-2 mb-4">
        <Info size={18} className="text-slate-400" />
        <h3 className="font-semibold text-slate-200">Model Quality & Transparency</h3>
      </div>

      {/* Brier Score */}
      {modelQuality && (
        <div className="mb-4 p-3 bg-slate-800 rounded border border-slate-700">
          <div className="flex items-start justify-between mb-2">
            <div>
              <p className="text-sm text-slate-400">Brier Score (Probabilistic Accuracy)</p>
              <p className={`text-2xl font-bold ${brierColor}`}>
                {modelQuality.brier_score.toFixed(3)}
              </p>
            </div>
            <span className={`px-2 py-1 text-xs font-semibold rounded ${brierColor} bg-slate-900`}>
              {brierRating}
            </span>
          </div>
          <p className="text-xs text-slate-400">
            Lower is better (0 = perfect, 1 = worst). Random guessing = 0.25.
          </p>
        </div>
      )}

      {/* Calibration Error */}
      {modelQuality && (
        <div className="mb-4 p-3 bg-slate-800 rounded border border-slate-700">
          <div className="flex items-center gap-2 mb-2">
            <AlertCircle size={16} className="text-amber-500" />
            <p className="text-sm text-slate-400">Calibration Error</p>
          </div>
          <p className="text-2xl font-bold text-amber-500 mb-2">
            ±{calibrationPercent}%
          </p>
          <p className="text-xs text-slate-400">
            When we say "90% confident", we're actually right ~{Math.max(20, 90 - calibrationPercent)}% of the time.
          </p>
        </div>
      )}

      {/* Confidence Note */}
      {modelQuality && (
        <div className="mb-4 p-3 bg-blue-950 rounded border border-blue-800">
          <p className="text-sm text-blue-200">
            ℹ️ {modelQuality.confidence_note}
          </p>
        </div>
      )}

      {/* Credibility Features */}
      {credibility && (
        <div className="space-y-2">
          <p className="text-sm font-semibold text-slate-300 mb-3">Credibility Features Enabled:</p>

          {credibility.tier_1_enabled && (
            <div className="flex items-start gap-2 text-sm">
              <TrendingUp size={16} className="text-green-500 mt-0.5 flex-shrink-0" />
              <div>
                <p className="font-medium text-slate-200">Tier 1: Calibration & Honesty</p>
                <p className="text-xs text-slate-400">
                  Shows alternative chains, compound confidence decay, explicit uncertainty ranges
                </p>
              </div>
            </div>
          )}

          {credibility.tier_2_enabled && (
            <div className="flex items-start gap-2 text-sm">
              <TrendingUp size={16} className="text-blue-500 mt-0.5 flex-shrink-0" />
              <div>
                <p className="font-medium text-slate-200">Tier 2: Feedback Loops & Intervals</p>
                <p className="text-xs text-slate-400">
                  Detects cycles in causality, shows confidence intervals instead of point estimates
                </p>
              </div>
            </div>
          )}

          <div className="mt-3 pt-3 border-t border-slate-700">
            <p className="text-xs text-slate-500">
              <strong>Chain confidence:</strong> {credibility.chain_confidence_method}
            </p>
            <p className="text-xs text-slate-500">
              <strong>Intervals:</strong> {credibility.interval_basis}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
