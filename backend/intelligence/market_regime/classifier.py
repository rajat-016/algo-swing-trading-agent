import pandas as pd
from typing import Dict, List, Optional, Tuple

from intelligence.market_regime.config import RegimeConfig
from intelligence.market_regime.regimes import (
    RegimeType,
    RegimeOutput,
    VolatilityContext,
    TrendContext,
    BreadthContext,
    VolumeContext,
    REGIME_METADATA,
)
from intelligence.market_regime.confidence import ConfidenceScorer
from intelligence.market_regime.indicators import (
    compute_trend_indicators,
    compute_volatility_indicators,
    compute_volume_indicators,
    compute_breadth_indicators,
    compute_momentum_indicators,
)


class RegimeClassifier:
    def __init__(self, config: RegimeConfig):
        self.config = config
        self.confidence_scorer = ConfidenceScorer(config)

    def classify(
        self,
        df: pd.DataFrame,
        recent_regimes: Optional[List[str]] = None,
    ) -> RegimeOutput:
        trend = compute_trend_indicators(df, self.config.ema_short, self.config.ema_long)
        volatility = compute_volatility_indicators(df, self.config.high_vol_atr_pct, self.config.low_vol_atr_pct)
        volume = compute_volume_indicators(df, self.config.breakout_volume_ratio, self.config.event_volume_spike_ratio)
        breadth = compute_breadth_indicators(df, self.config.ema_long)
        momentum = compute_momentum_indicators(df)

        vc = self._build_volatility_context(volatility)
        tc = self._build_trend_context(trend)
        bc = self._build_breadth_context(breadth)
        voc = self._build_volume_context(volume)

        regime_signals = self._compute_regime_signals(trend, volatility, volume, momentum, vc)
        regime = self._select_regime(regime_signals)

        signal_strengths = self._compute_signal_strengths(trend, volatility, volume, momentum)
        confidence = self.confidence_scorer.compute(
            regime_signals, signal_strengths, recent_regimes or []
        )

        if recent_regimes and len(recent_regimes) >= self.config.stability_lookback:
            stability = self._determine_stability(regime.value, recent_regimes)
        else:
            stability = "moderate"

        metadata = REGIME_METADATA.get(regime, REGIME_METADATA[RegimeType.UNKNOWN])

        return RegimeOutput(
            regime=regime,
            confidence=confidence,
            risk_level=metadata["risk_level"],
            stability=stability,
            volatility_context=vc,
            trend_context=tc,
            breadth_context=bc,
            volume_context=voc,
            suggested_behavior=metadata["suggested_behavior"],
            signal_breakdown=dict(sorted(regime_signals.items(), key=lambda x: -x[1])),
        )

    def _compute_regime_signals(
        self,
        trend: dict,
        volatility: dict,
        volume: dict,
        momentum: dict,
        vc: VolatilityContext,
    ) -> Dict[str, float]:
        signals: Dict[str, float] = {}

        bull_score = self._compute_bull_score(trend, volatility, volume)
        if bull_score > 0:
            signals[RegimeType.BULL_TREND.value] = bull_score

        bear_score = self._compute_bear_score(trend, volatility, volume)
        if bear_score > 0:
            signals[RegimeType.BEAR_TREND.value] = bear_score

        sideways_score = self._compute_sideways_score(trend, volatility)
        if sideways_score > 0:
            signals[RegimeType.SIDEWAYS.value] = sideways_score

        breakout_score = self._compute_breakout_score(trend, volatility, volume)
        if breakout_score > 0:
            signals[RegimeType.BREAKOUT.value] = breakout_score

        mean_rev_score = self._compute_mean_reversion_score(trend, volatility, momentum)
        if mean_rev_score > 0:
            signals[RegimeType.MEAN_REVERSION.value] = mean_rev_score

        high_vol_score = self._compute_high_volatility_score(volatility, vc)
        if high_vol_score > 0:
            signals[RegimeType.HIGH_VOLATILITY.value] = high_vol_score

        low_vol_score = self._compute_low_volatility_score(volatility, vc)
        if low_vol_score > 0:
            signals[RegimeType.LOW_VOLATILITY.value] = low_vol_score

        event_score = self._compute_event_driven_score(volatility, volume)
        if event_score > 0:
            signals[RegimeType.EVENT_DRIVEN.value] = event_score

        return signals

    def _compute_bull_score(self, trend: dict, volatility: dict, volume: dict) -> float:
        score = 0.0
        count = 0

        ema_diff = trend.get("ema_diff_pct")
        if ema_diff is not None:
            if ema_diff > self.config.trend_bull_separation_pct:
                score += min(ema_diff / 0.05, 1.0)
                count += 1

        adx = trend.get("adx")
        if adx is not None:
            if adx > self.config.adx_trend_threshold:
                score += min((adx - self.config.adx_trend_threshold) / 20, 1.0)
                count += 1

        macd = trend.get("macd_histogram")
        if macd is not None:
            if macd > 0:
                score += min(macd / 0.01, 1.0)
                count += 1

        price_vs_ema = trend.get("price_vs_ema")
        if price_vs_ema is not None:
            if price_vs_ema > 0:
                score += min(price_vs_ema / 0.05, 1.0)
                count += 1

        if count == 0:
            return 0.0
        raw = score / count
        if raw < 0.15:
            return 0.0
        return raw

    def _compute_bear_score(self, trend: dict, volatility: dict, volume: dict) -> float:
        score = 0.0
        count = 0

        ema_diff = trend.get("ema_diff_pct")
        if ema_diff is not None:
            if ema_diff < self.config.trend_bear_separation_pct:
                score += min(abs(ema_diff) / 0.05, 1.0)
                count += 1

        adx = trend.get("adx")
        if adx is not None:
            if adx > self.config.adx_trend_threshold:
                score += min((adx - self.config.adx_trend_threshold) / 20, 1.0)
                count += 1

        macd = trend.get("macd_histogram")
        if macd is not None:
            if macd < 0:
                score += min(abs(macd) / 0.01, 1.0)
                count += 1

        price_vs_ema = trend.get("price_vs_ema")
        if price_vs_ema is not None:
            if price_vs_ema < 0:
                score += min(abs(price_vs_ema) / 0.05, 1.0)
                count += 1

        if count == 0:
            return 0.0
        raw = score / count
        if raw < 0.15:
            return 0.0
        return raw

    def _compute_sideways_score(self, trend: dict, volatility: dict) -> float:
        score = 0.0
        count = 0

        ema_diff = trend.get("ema_diff_pct")
        if ema_diff is not None:
            if abs(ema_diff) <= self.config.sideways_threshold_pct:
                score += 1.0 - (abs(ema_diff) / self.config.sideways_threshold_pct)
                count += 1

        adx = trend.get("adx")
        if adx is not None:
            if adx < self.config.adx_trend_threshold:
                score += 1.0 - (adx / self.config.adx_trend_threshold)
                count += 1

        macd = trend.get("macd_histogram")
        if macd is not None:
            if abs(macd) < 0.005:
                score += 1.0 - (abs(macd) / 0.005)
                if score > 1.0:
                    score = 1.0
                count += 1

        if count == 0:
            return 0.0
        raw = score / count
        if raw < 0.2:
            return 0.0
        return raw

    def _compute_breakout_score(self, trend: dict, volatility: dict, volume: dict) -> float:
        score = 0.0
        count = 0

        volume_ratio = volume.get("volume_ratio")
        if volume_ratio is not None and volume_ratio >= self.config.breakout_volume_ratio:
            score += min((volume_ratio - 1.0) / 2.0, 1.0)
            count += 1

        ema_diff = trend.get("ema_diff_pct")
        if ema_diff is not None:
            if abs(ema_diff) > self.config.sideways_threshold_pct:
                score += 0.5
                count += 1

        bb_width_ratio = volatility.get("bb_width_ratio")
        if bb_width_ratio is not None and bb_width_ratio > 1.0:
            score += min((bb_width_ratio - 1.0) / 0.5, 1.0)
            count += 1

        if count == 0:
            return 0.0
        raw = score / count
        if raw < 0.25:
            return 0.0
        return raw

    def _compute_mean_reversion_score(
        self, trend: dict, volatility: dict, momentum: dict
    ) -> float:
        score = 0.0
        count = 0

        rsi = momentum.get("rsi_14")
        if rsi is not None:
            if rsi >= self.config.mean_reversion_rsi_overbought:
                score += min((rsi - self.config.mean_reversion_rsi_overbought) / 15.0, 1.0)
                count += 1
            elif rsi <= self.config.mean_reversion_rsi_oversold:
                score += min((self.config.mean_reversion_rsi_oversold - rsi) / 15.0, 1.0)
                count += 1

        price_vs_ema = trend.get("price_vs_ema")
        if price_vs_ema is not None:
            if abs(price_vs_ema) > 0.05:
                score += min((abs(price_vs_ema) - 0.05) / 0.1, 1.0)
                count += 1

        ema_diff = trend.get("ema_diff_pct")
        if ema_diff is not None and price_vs_ema is not None:
            if (price_vs_ema > 0 and ema_diff < 0) or (price_vs_ema < 0 and ema_diff > 0):
                score += 0.7
                count += 1

        if count == 0:
            return 0.0
        raw = score / count
        if raw < 0.2:
            return 0.0
        return raw

    def _compute_high_volatility_score(self, volatility: dict, vc: VolatilityContext) -> float:
        score = 0.0
        count = 0

        atr_pct = volatility.get("atr_pct")
        if atr_pct is not None:
            if atr_pct >= self.config.high_vol_atr_pct:
                score += min((atr_pct - self.config.high_vol_atr_pct) / 0.03, 1.0)
                count += 1

        bb_width_ratio = volatility.get("bb_width_ratio")
        if bb_width_ratio is not None:
            if bb_width_ratio >= self.config.bb_high_vol_multiplier:
                score += min((bb_width_ratio - 1.0) / 1.0, 1.0)
                count += 1

        if vc.vix_level is not None:
            if vc.vix_level >= self.config.vix_high_threshold:
                score += min((vc.vix_level - self.config.vix_high_threshold) / 20.0, 1.0)
                count += 1

        if count == 0:
            return 0.0
        raw = score / count
        if raw < 0.2:
            return 0.0
        return raw

    def _compute_low_volatility_score(self, volatility: dict, vc: VolatilityContext) -> float:
        score = 0.0
        count = 0

        atr_pct = volatility.get("atr_pct")
        if atr_pct is not None:
            if atr_pct <= self.config.low_vol_atr_pct:
                score += 1.0 - (atr_pct / self.config.low_vol_atr_pct)
                count += 1

        bb_width_ratio = volatility.get("bb_width_ratio")
        if bb_width_ratio is not None:
            if bb_width_ratio <= self.config.bb_low_vol_multiplier:
                score += 1.0 - (bb_width_ratio / self.config.bb_low_vol_multiplier)
                count += 1

        if vc.vix_level is not None:
            if vc.vix_level <= self.config.vix_low_threshold:
                score += 1.0 - (vc.vix_level / self.config.vix_low_threshold)
                count += 1

        if count == 0:
            return 0.0
        raw = score / count
        if raw < 0.2:
            return 0.0
        return raw

    def _compute_event_driven_score(self, volatility: dict, volume: dict) -> float:
        score = 0.0
        count = 0

        is_spike = volume.get("is_spike", False)
        if is_spike:
            score += 1.0
            count += 1

        volume_ratio = volume.get("volume_ratio")
        if volume_ratio is not None and volume_ratio >= self.config.event_volume_spike_ratio:
            score += min((volume_ratio - 2.0) / 3.0, 1.0)
            count += 1

        atr_change = volatility.get("atr_pct")
        if atr_change is not None and count == 0:
            if atr_change > self.config.high_vol_atr_pct * 1.5:
                score += 0.5
                count += 1

        if count == 0:
            return 0.0
        raw = score / count
        if raw < 0.3:
            return 0.0
        return raw

    def _select_regime(self, regime_signals: Dict[str, float]) -> RegimeType:
        if not regime_signals:
            return RegimeType.UNKNOWN
        best = max(regime_signals, key=regime_signals.get)
        try:
            return RegimeType(best)
        except ValueError:
            return RegimeType.UNKNOWN

    def _determine_stability(self, current_regime: str, recent_regimes: List[str]) -> str:
        if not recent_regimes:
            return "moderate"

        changes = sum(1 for i in range(1, len(recent_regimes)) if recent_regimes[i] != recent_regimes[i - 1])
        total = len(recent_regimes) - 1

        if total == 0:
            return "stable"

        change_rate = changes / total
        if change_rate <= 0.1:
            return "stable"
        elif change_rate <= 0.3:
            return "moderate"
        else:
            return "unstable"

    def _signal_weights(self, signal: str) -> float:
        weights = {
            "bull_trend": 1.0,
            "bear_trend": 1.0,
            "sideways": 0.7,
            "breakout": 0.8,
            "mean_reversion": 0.6,
            "high_volatility": 0.9,
            "low_volatility": 0.7,
            "event_driven": 0.5,
        }
        return weights.get(signal, 0.5)

    def _compute_signal_strengths(
        self, trend: dict, volatility: dict, volume: dict, momentum: dict
    ) -> Dict[str, float]:
        strengths = {}
        if trend.get("adx"):
            strengths["adx"] = min(trend["adx"] / 50.0, 1.0)
        if trend.get("ema_diff_pct"):
            strengths["ema_diff"] = min(abs(trend["ema_diff_pct"]) / 0.05, 1.0)
        if volatility.get("atr_pct"):
            strengths["atr"] = min(volatility["atr_pct"] / 0.05, 1.0)
        if volume.get("volume_ratio"):
            strengths["volume_ratio"] = min(volume["volume_ratio"] / 3.0, 1.0)
        if momentum.get("rsi_14"):
            rsi_extreme = abs(momentum["rsi_14"] - 50) / 50.0
            strengths["rsi_extreme"] = min(rsi_extreme, 1.0)
        return strengths

    def _build_volatility_context(self, volatility: dict) -> VolatilityContext:
        return VolatilityContext(
            atr_pct=volatility.get("atr_pct"),
            bb_width=volatility.get("bb_width"),
            bb_width_ratio=volatility.get("bb_width_ratio"),
        )

    def _build_trend_context(self, trend: dict) -> TrendContext:
        return TrendContext(
            ema_diff_pct=trend.get("ema_diff_pct"),
            adx=trend.get("adx"),
            macd_histogram=trend.get("macd_histogram"),
            price_vs_ema=trend.get("price_vs_ema"),
        )

    def _build_breadth_context(self, breadth: dict) -> BreadthContext:
        return BreadthContext(
            pct_above_ma50=breadth.get("pct_above_ma200"),
        )

    def _build_volume_context(self, volume: dict) -> VolumeContext:
        return VolumeContext(
            volume_ratio=volume.get("volume_ratio"),
            is_spike=volume.get("is_spike", False),
        )
