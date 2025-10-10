"""Advanced time-series forecasting methods for finance and retail analytics.

This module provides production-ready forecasting algorithms beyond simple linear regression,
including SARIMA, exponential smoothing, and Prophet with confidence intervals.
"""

from __future__ import annotations

import logging
import warnings
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from statistics import mean, stdev

LOGGER = logging.getLogger(__name__)

# Suppress warnings from statsmodels/prophet during model fitting
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)


def detect_seasonality(
    values: List[float], max_period: int = 12
) -> Optional[int]:
    """Auto-detect seasonality period using autocorrelation.
    
    Args:
        values: Time series data
        max_period: Maximum period to check (e.g., 12 for monthly)
    
    Returns:
        Detected period or None if no clear seasonality
    """
    if len(values) < 2 * max_period:
        return None
    
    try:
        from statsmodels.tsa.stattools import acf
        
        # Calculate autocorrelation
        autocorr = acf(values, nlags=max_period, fft=True)
        
        # Find first significant peak after lag 1
        for lag in range(2, max_period + 1):
            if autocorr[lag] > 0.5:  # Threshold for significance
                return lag
        
        return None
    except Exception as exc:
        LOGGER.warning("Seasonality detection failed: %s", exc)
        return None


def sarima_forecast(
    values: List[float],
    periods: int = 3,
    seasonal_period: Optional[int] = None,
    confidence_level: float = 0.95,
) -> Dict[str, Any]:
    """Seasonal ARIMA forecasting with auto-parameter selection.
    
    Args:
        values: Historical time series data
        periods: Number of periods to forecast
        seasonal_period: Seasonality period (auto-detected if None)
        confidence_level: Confidence level for intervals (0-1)
    
    Returns:
        Dict with forecast, confidence bounds, and model info
    """
    if len(values) < 10:
        raise ValueError("SARIMA requires at least 10 data points")
    
    try:
        from statsmodels.tsa.statespace.sarimax import SARIMAX
        from statsmodels.tsa.stattools import adfuller
        
        # Auto-detect seasonality if not provided
        if seasonal_period is None:
            seasonal_period = detect_seasonality(values) or 1
        
        # Test for stationarity
        adf_result = adfuller(values)
        is_stationary = adf_result[1] < 0.05
        
        # Auto-select SARIMA parameters (simplified heuristic)
        p, d, q = (1, 0 if is_stationary else 1, 1)
        if seasonal_period > 1:
            P, D, Q, s = (1, 1, 1, seasonal_period)
        else:
            P, D, Q, s = (0, 0, 0, 0)
        
        # Fit SARIMAX model
        model = SARIMAX(
            values,
            order=(p, d, q),
            seasonal_order=(P, D, Q, s),
            enforce_stationarity=False,
            enforce_invertibility=False,
        )
        
        fitted = model.fit(disp=False, maxiter=100)
        
        # Generate forecast
        forecast_result = fitted.get_forecast(steps=periods)
        forecast_mean = forecast_result.predicted_mean.tolist()
        
        # Calculate confidence intervals
        alpha = 1 - confidence_level
        conf_int = forecast_result.conf_int(alpha=alpha)
        
        # Handle both DataFrame and numpy array return types
        if hasattr(conf_int, 'iloc'):
            # DataFrame (older statsmodels)
            lower_bound = conf_int.iloc[:, 0].tolist()
            upper_bound = conf_int.iloc[:, 1].tolist()
        else:
            # Numpy array (newer statsmodels)
            lower_bound = conf_int[:, 0].tolist() if conf_int.ndim > 1 else conf_int.tolist()
            upper_bound = conf_int[:, 1].tolist() if conf_int.ndim > 1 else conf_int.tolist()
        
        return {
            "method": "SARIMA",
            "forecast": forecast_mean,
            "lower_bound": lower_bound,
            "upper_bound": upper_bound,
            "confidence_level": confidence_level,
            "seasonal_period": seasonal_period,
            "model_params": {"p": p, "d": d, "q": q, "P": P, "D": D, "Q": Q, "s": s},
            "aic": float(fitted.aic),
        }
    
    except ImportError:
        raise ImportError("SARIMA requires statsmodels. Install with: pip install statsmodels")
    except Exception as exc:
        LOGGER.exception("SARIMA forecast failed")
        raise ValueError(f"SARIMA forecasting failed: {exc}") from exc


def exponential_smoothing_forecast(
    values: List[float],
    periods: int = 3,
    seasonal_period: Optional[int] = None,
    confidence_level: float = 0.95,
) -> Dict[str, Any]:
    """Exponential smoothing (Holt-Winters) forecasting.
    
    Args:
        values: Historical time series data
        periods: Number of periods to forecast
        seasonal_period: Seasonality period (auto-detected if None)
        confidence_level: Confidence level for intervals (0-1)
    
    Returns:
        Dict with forecast, confidence bounds, and model info
    """
    if len(values) < 8:
        raise ValueError("Exponential smoothing requires at least 8 data points")
    
    try:
        from statsmodels.tsa.holtwinters import ExponentialSmoothing
        
        # Auto-detect seasonality
        if seasonal_period is None:
            seasonal_period = detect_seasonality(values)
        
        # Determine model type
        if seasonal_period and len(values) >= 2 * seasonal_period:
            seasonal = "add"
            seasonal_periods = seasonal_period
        else:
            seasonal = None
            seasonal_periods = None
        
        # Fit model
        model = ExponentialSmoothing(
            values,
            seasonal=seasonal,
            seasonal_periods=seasonal_periods,
            trend="add",
        )
        
        fitted = model.fit(optimized=True, use_brute=False)
        
        # Generate forecast
        forecast_mean = fitted.forecast(steps=periods).tolist()
        
        # Bootstrap confidence intervals (simplified)
        residuals = fitted.resid
        std_error = np.std(residuals) if len(residuals) > 0 else 0
        z_score = 1.96 if confidence_level == 0.95 else 2.576  # 95% or 99%
        
        lower_bound = [f - z_score * std_error for f in forecast_mean]
        upper_bound = [f + z_score * std_error for f in forecast_mean]
        
        return {
            "method": "Exponential Smoothing",
            "forecast": forecast_mean,
            "lower_bound": lower_bound,
            "upper_bound": upper_bound,
            "confidence_level": confidence_level,
            "seasonal_period": seasonal_period,
            "seasonal_type": seasonal,
            "aic": float(fitted.aic) if hasattr(fitted, "aic") else None,
        }
    
    except ImportError:
        raise ImportError("Exponential smoothing requires statsmodels. Install with: pip install statsmodels")
    except Exception as exc:
        LOGGER.exception("Exponential smoothing failed")
        raise ValueError(f"Exponential smoothing failed: {exc}") from exc


def prophet_forecast(
    values: List[float],
    periods: int = 3,
    frequency: str = "D",
    confidence_level: float = 0.95,
) -> Dict[str, Any]:
    """Facebook Prophet forecasting with retail-specific settings.
    
    Args:
        values: Historical time series data
        periods: Number of periods to forecast
        frequency: Frequency ('D' for daily, 'W' for weekly, 'M' for monthly)
        confidence_level: Confidence level for intervals (0-1)
    
    Returns:
        Dict with forecast, confidence bounds, and model info
    """
    if len(values) < 10:
        raise ValueError("Prophet requires at least 10 data points")
    
    try:
        from prophet import Prophet
        import pandas as pd
        
        # Prepare data for Prophet (requires 'ds' and 'y' columns)
        df = pd.DataFrame({
            "ds": pd.date_range(start="2023-01-01", periods=len(values), freq=frequency),
            "y": values,
        })
        
        # Initialize Prophet with retail-friendly settings
        model = Prophet(
            interval_width=confidence_level,
            seasonality_mode="multiplicative",
            daily_seasonality=False,
            weekly_seasonality=(frequency == "D"),
            yearly_seasonality=True,
        )
        
        # Fit model
        model.fit(df)
        
        # Create future dataframe
        future = model.make_future_dataframe(periods=periods, freq=frequency)
        
        # Generate forecast
        forecast_df = model.predict(future)
        
        # Extract forecast values (last 'periods' rows)
        forecast_mean = forecast_df["yhat"].tail(periods).values.tolist()
        lower_bound = forecast_df["yhat_lower"].tail(periods).values.tolist()
        upper_bound = forecast_df["yhat_upper"].tail(periods).values.tolist()
        
        return {
            "method": "Prophet",
            "forecast": forecast_mean,
            "lower_bound": lower_bound,
            "upper_bound": upper_bound,
            "confidence_level": confidence_level,
            "frequency": frequency,
            "trend": forecast_df["trend"].tail(periods).mean(),
        }
    
    except ImportError:
        raise ImportError("Prophet requires prophet package. Install with: pip install prophet")
    except Exception as exc:
        LOGGER.exception("Prophet forecast failed")
        raise ValueError(f"Prophet forecasting failed: {exc}") from exc


def linear_forecast_with_confidence(
    values: List[float],
    periods: int = 3,
    confidence_level: float = 0.95,
) -> Dict[str, Any]:
    """Enhanced linear forecast with bootstrap confidence intervals.
    
    Args:
        values: Historical time series data
        periods: Number of periods to forecast
        confidence_level: Confidence level for intervals (0-1)
    
    Returns:
        Dict with forecast, confidence bounds, and model info
    """
    if len(values) < 2:
        raise ValueError("Need at least two data points to generate a forecast")
    
    n = len(values)
    x_values = list(range(n))
    
    # Calculate linear regression parameters
    sum_x = sum(x_values)
    sum_y = sum(values)
    sum_xy = sum(x * y for x, y in zip(x_values, values))
    sum_x2 = sum(x * x for x in x_values)
    
    denominator = (n * sum_x2) - (sum_x ** 2)
    if denominator == 0:
        # Degenerate case: return last value with no confidence interval
        forecast_mean = [values[-1] for _ in range(periods)]
        return {
            "method": "Linear (Constant)",
            "forecast": forecast_mean,
            "lower_bound": forecast_mean,
            "upper_bound": forecast_mean,
            "confidence_level": confidence_level,
        }
    
    slope = ((n * sum_xy) - (sum_x * sum_y)) / denominator
    intercept = (sum_y - slope * sum_x) / n
    
    # Generate point forecast
    forecast_mean = []
    for step in range(1, periods + 1):
        future_index = n - 1 + step
        forecast_mean.append(slope * future_index + intercept)
    
    # Calculate residual standard error
    fitted = [slope * x + intercept for x in x_values]
    residuals = [y - f for y, f in zip(values, fitted)]
    mse = sum(r ** 2 for r in residuals) / (n - 2) if n > 2 else 0
    std_error = np.sqrt(mse) if mse > 0 else 0
    
    # Confidence intervals using t-distribution approximation
    z_score = 1.96 if confidence_level == 0.95 else 2.576
    
    lower_bound = []
    upper_bound = []
    for step, f in enumerate(forecast_mean, start=1):
        # Standard error increases with forecast horizon
        forecast_std = std_error * np.sqrt(1 + 1/n + ((n + step - 1 - sum_x/n) ** 2) / sum([(x - sum_x/n) ** 2 for x in x_values]))
        lower_bound.append(f - z_score * forecast_std)
        upper_bound.append(f + z_score * forecast_std)
    
    # Calculate R-squared
    ss_tot = sum((y - mean(values)) ** 2 for y in values)
    ss_res = sum(r ** 2 for r in residuals)
    r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
    
    return {
        "method": "Linear",
        "forecast": forecast_mean,
        "lower_bound": lower_bound,
        "upper_bound": upper_bound,
        "confidence_level": confidence_level,
        "slope": slope,
        "intercept": intercept,
        "r_squared": r_squared,
        "std_error": std_error,
    }


def auto_select_forecast_method(
    values: List[float],
    periods: int = 3,
    confidence_level: float = 0.95,
) -> Dict[str, Any]:
    """Automatically select the best forecasting method based on data characteristics.
    
    Args:
        values: Historical time series data
        periods: Number of periods to forecast
        confidence_level: Confidence level for intervals (0-1)
    
    Returns:
        Dict with forecast from best method and rationale
    """
    n = len(values)
    
    # Rule-based method selection
    if n < 10:
        # Use linear for small datasets
        result = linear_forecast_with_confidence(values, periods, confidence_level)
        result["selection_rationale"] = f"Linear selected: only {n} data points available"
        return result
    
    # Detect seasonality
    seasonal_period = detect_seasonality(values)
    
    if seasonal_period and n >= 2 * seasonal_period:
        # Try SARIMA for seasonal data
        try:
            result = sarima_forecast(values, periods, seasonal_period, confidence_level)
            result["selection_rationale"] = f"SARIMA selected: seasonal pattern detected (period={seasonal_period})"
            return result
        except Exception as exc:
            LOGGER.warning("SARIMA failed, falling back: %s", exc)
    
    # Try exponential smoothing for moderate-sized datasets
    if n >= 8:
        try:
            result = exponential_smoothing_forecast(values, periods, seasonal_period, confidence_level)
            result["selection_rationale"] = "Exponential Smoothing selected: good for trend + seasonality"
            return result
        except Exception as exc:
            LOGGER.warning("Exponential smoothing failed, falling back: %s", exc)
    
    # Fallback to linear
    result = linear_forecast_with_confidence(values, periods, confidence_level)
    result["selection_rationale"] = "Linear selected: fallback method"
    return result


def evaluate_forecast_accuracy(
    actual: List[float],
    predicted: List[float],
) -> Dict[str, float]:
    """Calculate forecast accuracy metrics.
    
    Args:
        actual: Actual observed values
        predicted: Predicted/forecasted values
    
    Returns:
        Dict with MAE, RMSE, MAPE metrics
    """
    if len(actual) != len(predicted):
        raise ValueError("actual and predicted must have same length")
    
    n = len(actual)
    if n == 0:
        return {"mae": 0.0, "rmse": 0.0, "mape": 0.0}
    
    # Mean Absolute Error
    mae = sum(abs(a - p) for a, p in zip(actual, predicted)) / n
    
    # Root Mean Squared Error
    mse = sum((a - p) ** 2 for a, p in zip(actual, predicted)) / n
    rmse = np.sqrt(mse)
    
    # Mean Absolute Percentage Error
    non_zero_actuals = [(a, p) for a, p in zip(actual, predicted) if a != 0]
    if non_zero_actuals:
        mape = (sum(abs((a - p) / a) for a, p in non_zero_actuals) / len(non_zero_actuals)) * 100
    else:
        mape = 0.0
    
    return {
        "mae": float(mae),
        "rmse": float(rmse),
        "mape": float(mape),
    }

