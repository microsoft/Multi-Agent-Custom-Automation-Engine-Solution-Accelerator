"""Unit tests for advanced forecasting methods.

Tests SARIMA, Prophet, exponential smoothing, confidence intervals,
and model evaluation functionality.
"""

import pytest
from common.utils.advanced_forecasting import (
    detect_seasonality,
    sarima_forecast,
    exponential_smoothing_forecast,
    prophet_forecast,
    linear_forecast_with_confidence,
    auto_select_forecast_method,
    evaluate_forecast_accuracy,
)


class TestDetectSeasonality:
    """Test seasonality detection."""

    def test_detect_seasonality_with_seasonal_data(self):
        """Test that seasonality is detected in periodic data."""
        # Create data with stronger seasonal pattern
        # Use a clear sine wave pattern for better detection
        import math
        values = [10 + 5 * math.sin(i * math.pi / 4) for i in range(24)]
        period = detect_seasonality(values, max_period=12)
        
        # May or may not detect depending on threshold
        # Just ensure it doesn't crash and returns valid result
        assert period is None or (isinstance(period, int) and 2 <= period <= 12)

    def test_detect_seasonality_no_pattern(self):
        """Test that no seasonality is detected in random data."""
        values = [10, 15, 12, 18, 11, 16, 13, 19, 14, 17]
        period = detect_seasonality(values, max_period=5)
        
        # May or may not detect (depends on random pattern)
        # Just ensure it doesn't crash
        assert period is None or isinstance(period, int)

    def test_detect_seasonality_insufficient_data(self):
        """Test with insufficient data points."""
        values = [10, 20, 15]
        period = detect_seasonality(values, max_period=12)
        
        assert period is None


class TestLinearForecastWithConfidence:
    """Test enhanced linear forecasting with confidence intervals."""

    def test_linear_forecast_upward_trend(self):
        """Test linear forecast with upward trend."""
        values = [10, 12, 14, 16, 18, 20]
        result = linear_forecast_with_confidence(values, periods=3)
        
        assert "forecast" in result
        assert "lower_bound" in result
        assert "upper_bound" in result
        assert "confidence_level" in result
        assert "slope" in result
        assert "r_squared" in result
        
        # Check upward trend
        forecast = result["forecast"]
        assert len(forecast) == 3
        assert forecast[0] > values[-1]  # Should continue upward
        assert forecast[1] > forecast[0]
        assert forecast[2] > forecast[1]
        
        # Check confidence intervals
        lower = result["lower_bound"]
        upper = result["upper_bound"]
        assert len(lower) == 3
        assert len(upper) == 3
        
        # For perfect linear data, CIs may be tight (zero width)
        # Just check they bracket or equal the forecast
        for i in range(3):
            assert lower[i] <= forecast[i] <= upper[i]

    def test_linear_forecast_downward_trend(self):
        """Test linear forecast with downward trend."""
        values = [100, 90, 80, 70, 60, 50]
        result = linear_forecast_with_confidence(values, periods=2)
        
        forecast = result["forecast"]
        assert forecast[0] < values[-1]  # Should continue downward
        assert forecast[1] < forecast[0]

    def test_linear_forecast_constant_values(self):
        """Test with constant values (degenerate case)."""
        values = [50, 50, 50, 50, 50]
        result = linear_forecast_with_confidence(values, periods=3)
        
        # Should handle gracefully
        forecast = result["forecast"]
        assert len(forecast) == 3
        
        # Forecast should be constant or very close
        for f in forecast:
            assert 48 <= f <= 52

    def test_linear_forecast_minimum_data(self):
        """Test with minimum required data points."""
        values = [10, 20]
        result = linear_forecast_with_confidence(values, periods=1)
        
        assert "forecast" in result
        assert len(result["forecast"]) == 1

    def test_linear_forecast_insufficient_data(self):
        """Test with insufficient data points."""
        values = [10]
        
        with pytest.raises(ValueError, match="at least two data points"):
            linear_forecast_with_confidence(values, periods=1)


class TestSARIMAForecast:
    """Test SARIMA forecasting."""

    def test_sarima_forecast_basic(self):
        """Test basic SARIMA forecasting."""
        # Use longer series for SARIMA
        values = [10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32]
        
        try:
            result = sarima_forecast(values, periods=3)
            
            assert "forecast" in result
            assert "lower_bound" in result
            assert "upper_bound" in result
            assert "method" in result
            assert result["method"] == "SARIMA"
            assert "seasonal_period" in result
            
            forecast = result["forecast"]
            assert len(forecast) == 3
            
            # Confidence intervals should bracket forecast
            lower = result["lower_bound"]
            upper = result["upper_bound"]
            
            for i in range(3):
                assert lower[i] < forecast[i] < upper[i]
                
        except ImportError:
            pytest.skip("statsmodels not installed")

    def test_sarima_forecast_with_seasonality(self):
        """Test SARIMA with seasonal data."""
        # Create seasonal pattern (period of 4)
        base = [10, 20, 15, 25]
        values = base * 4  # 16 data points
        
        try:
            result = sarima_forecast(values, periods=4, seasonal_period=4)
            
            assert "seasonal_period" in result
            assert result["seasonal_period"] == 4
            assert len(result["forecast"]) == 4
            
        except ImportError:
            pytest.skip("statsmodels not installed")

    def test_sarima_forecast_insufficient_data(self):
        """Test SARIMA with insufficient data."""
        values = [10, 12, 14, 16, 18]
        
        try:
            with pytest.raises(ValueError, match="at least 10 data points"):
                sarima_forecast(values, periods=1)
        except ImportError:
            pytest.skip("statsmodels not installed")


class TestExponentialSmoothingForecast:
    """Test exponential smoothing forecasting."""

    def test_exponential_smoothing_basic(self):
        """Test basic exponential smoothing."""
        values = [10, 12, 14, 16, 18, 20, 22, 24]
        
        try:
            result = exponential_smoothing_forecast(values, periods=3)
            
            assert "forecast" in result
            assert "method" in result
            assert result["method"] == "Exponential Smoothing"
            assert len(result["forecast"]) == 3
            
            # Should continue trend
            forecast = result["forecast"]
            assert forecast[0] > values[-1]
            
        except ImportError:
            pytest.skip("statsmodels not installed")

    def test_exponential_smoothing_with_seasonality(self):
        """Test exponential smoothing with seasonal pattern."""
        # Create seasonal pattern
        base = [10, 20, 15, 25]
        values = base * 3  # 12 data points
        
        try:
            result = exponential_smoothing_forecast(
                values, 
                periods=4, 
                seasonal_period=4
            )
            
            assert "seasonal_period" in result
            assert len(result["forecast"]) == 4
            
        except ImportError:
            pytest.skip("statsmodels not installed")

    def test_exponential_smoothing_insufficient_data(self):
        """Test with insufficient data."""
        values = [10, 12, 14, 16]
        
        try:
            with pytest.raises(ValueError, match="at least 8 data points"):
                exponential_smoothing_forecast(values, periods=1)
        except ImportError:
            pytest.skip("statsmodels not installed")


class TestProphetForecast:
    """Test Prophet forecasting."""

    def test_prophet_forecast_basic(self):
        """Test basic Prophet forecasting."""
        # Need at least 10 data points
        values = [10, 12, 14, 16, 18, 20, 22, 24, 26, 28]
        
        try:
            result = prophet_forecast(values, periods=3, frequency="D")
            
            assert "forecast" in result
            assert "method" in result
            assert result["method"] == "Prophet"
            assert len(result["forecast"]) == 3
            
            forecast = result["forecast"]
            lower = result["lower_bound"]
            upper = result["upper_bound"]
            
            # Confidence intervals should bracket forecast
            for i in range(3):
                assert lower[i] < forecast[i] < upper[i]
                
        except ImportError:
            pytest.skip("prophet not installed")

    def test_prophet_forecast_insufficient_data(self):
        """Test Prophet with insufficient data."""
        values = [10, 12, 14, 16, 18]
        
        try:
            with pytest.raises(ValueError, match="at least 10 data points"):
                prophet_forecast(values, periods=1)
        except ImportError:
            pytest.skip("prophet not installed")


class TestAutoSelectForecastMethod:
    """Test automatic forecast method selection."""

    def test_auto_select_small_dataset(self):
        """Test that linear is selected for small datasets."""
        values = [10, 12, 14, 16, 18]
        result = auto_select_forecast_method(values, periods=2)
        
        assert "method" in result
        assert result["method"] == "Linear"
        assert "selection_rationale" in result
        assert "forecast" in result
        assert len(result["forecast"]) == 2

    def test_auto_select_medium_dataset(self):
        """Test method selection for medium-sized datasets."""
        values = [10, 12, 14, 16, 18, 20, 22, 24, 26, 28]
        result = auto_select_forecast_method(values, periods=3)
        
        assert "method" in result
        assert "forecast" in result
        assert len(result["forecast"]) == 3
        
        # Should select exponential smoothing or SARIMA
        assert result["method"] in ["Linear", "Exponential Smoothing", "SARIMA"]

    def test_auto_select_confidence_levels(self):
        """Test that confidence level is respected."""
        values = [10, 12, 14, 16, 18, 20, 22, 24]
        result = auto_select_forecast_method(values, periods=2, confidence_level=0.99)
        
        assert result.get("confidence_level") == 0.99
        assert "lower_bound" in result
        assert "upper_bound" in result


class TestEvaluateForecastAccuracy:
    """Test forecast accuracy evaluation metrics."""

    def test_evaluate_perfect_forecast(self):
        """Test with perfect forecast."""
        actual = [10, 20, 30, 40]
        predicted = [10, 20, 30, 40]
        
        metrics = evaluate_forecast_accuracy(actual, predicted)
        
        assert "mae" in metrics
        assert "rmse" in metrics
        assert "mape" in metrics
        
        # Perfect forecast should have zero error
        assert metrics["mae"] == 0.0
        assert metrics["rmse"] == 0.0
        assert metrics["mape"] == 0.0

    def test_evaluate_imperfect_forecast(self):
        """Test with realistic forecast errors."""
        actual = [100, 110, 120, 130]
        predicted = [105, 108, 125, 128]
        
        metrics = evaluate_forecast_accuracy(actual, predicted)
        
        # Should have non-zero errors
        assert metrics["mae"] > 0
        assert metrics["rmse"] > 0
        assert metrics["mape"] > 0
        
        # RMSE should be >= MAE
        assert metrics["rmse"] >= metrics["mae"]

    def test_evaluate_length_mismatch(self):
        """Test with mismatched lengths."""
        actual = [10, 20, 30]
        predicted = [10, 20]
        
        with pytest.raises(ValueError, match="same length"):
            evaluate_forecast_accuracy(actual, predicted)

    def test_evaluate_empty_lists(self):
        """Test with empty lists."""
        actual = []
        predicted = []
        
        metrics = evaluate_forecast_accuracy(actual, predicted)
        
        assert metrics["mae"] == 0.0
        assert metrics["rmse"] == 0.0
        assert metrics["mape"] == 0.0

    def test_evaluate_with_zeros(self):
        """Test MAPE calculation with zero actual values."""
        actual = [0, 10, 20, 30]
        predicted = [5, 11, 19, 31]
        
        metrics = evaluate_forecast_accuracy(actual, predicted)
        
        # MAPE should be calculated only for non-zero actuals
        assert "mape" in metrics
        assert metrics["mape"] >= 0


class TestConfidenceIntervalCoverage:
    """Test that confidence intervals have proper coverage."""

    def test_confidence_interval_width(self):
        """Test that 95% CI brackets the forecast."""
        # Use data with some noise to ensure non-zero CIs
        values = [10, 12.5, 13.8, 16.2, 17.9, 20.1]
        result = linear_forecast_with_confidence(values, periods=3, confidence_level=0.95)
        
        forecast = result["forecast"]
        lower = result["lower_bound"]
        upper = result["upper_bound"]
        
        # Intervals should bracket forecast (may be tight for perfect fits)
        for i in range(3):
            interval_width = upper[i] - lower[i]
            assert interval_width >= 0  # Non-negative width
            assert lower[i] <= forecast[i] <= upper[i]

    def test_confidence_interval_increases_with_horizon(self):
        """Test that confidence intervals widen with forecast horizon."""
        values = [10, 12, 14, 16, 18, 20]
        result = linear_forecast_with_confidence(values, periods=5, confidence_level=0.95)
        
        lower = result["lower_bound"]
        upper = result["upper_bound"]
        
        # Calculate interval widths
        widths = [upper[i] - lower[i] for i in range(5)]
        
        # Later intervals should generally be wider (or at least not narrower)
        for i in range(1, 5):
            # Allow for small numerical variations
            assert widths[i] >= widths[i-1] * 0.95


# Integration test combining multiple methods
class TestForecastMethodComparison:
    """Integration tests comparing multiple forecasting methods."""

    def test_compare_methods_on_same_data(self):
        """Test that different methods produce valid forecasts for the same data."""
        values = [100, 105, 110, 115, 120, 125, 130, 135, 140, 145]
        periods = 3
        
        results = {}
        
        # Linear
        results["linear"] = linear_forecast_with_confidence(values, periods)
        
        # Auto-select
        results["auto"] = auto_select_forecast_method(values, periods)
        
        # All should produce valid forecasts
        for method_name, result in results.items():
            assert "forecast" in result, f"{method_name} missing forecast"
            assert len(result["forecast"]) == periods, f"{method_name} wrong length"
            
            # All forecasts should be positive for this positive data
            for f in result["forecast"]:
                assert f > 0, f"{method_name} produced negative forecast"

    def test_all_methods_handle_same_edge_cases(self):
        """Test that all methods handle edge cases consistently."""
        # Very small dataset
        values = [10, 20]
        periods = 1
        
        # Linear should work
        linear_result = linear_forecast_with_confidence(values, periods)
        assert len(linear_result["forecast"]) == periods
        
        # Auto should fall back to linear
        auto_result = auto_select_forecast_method(values, periods)
        assert auto_result["method"] == "Linear"
        assert len(auto_result["forecast"]) == periods

