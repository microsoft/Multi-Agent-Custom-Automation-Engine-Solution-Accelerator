"""
Test script for Analytics API endpoints.

Tests the new analytics API endpoints to ensure they return expected data structures.
This can be run against a local backend server for integration testing.
"""

import sys
from pathlib import Path

# Add backend path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src" / "backend"))

from fastapi import FastAPI
from fastapi.testclient import TestClient
from v3.api.analytics_endpoints import router

# Create a minimal FastAPI app for testing
app = FastAPI()
app.include_router(router)

# Create test client
client = TestClient(app)


def test_health_check():
    """Test analytics API health check."""
    response = client.get("/analytics/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "analytics-api"
    print("✅ Health check passed")


def test_kpi_metrics():
    """Test KPI metrics endpoint."""
    response = client.get("/analytics/kpis")
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "success"
    assert "data" in data
    
    kpis = data["data"]
    assert "total_revenue" in kpis
    assert "active_customers" in kpis
    assert "forecast_accuracy" in kpis
    assert "avg_order_value" in kpis
    
    # Verify KPI structure
    for kpi_name, kpi_data in kpis.items():
        assert "value" in kpi_data
        assert "trend" in kpi_data
        assert "label" in kpi_data
        assert "format" in kpi_data
    
    print("✅ KPI metrics endpoint passed")
    print(f"   Sample KPI: {kpis['total_revenue']['label']} = ${kpis['total_revenue']['value']:,.2f}")


def test_forecast_summary():
    """Test forecast summary endpoint."""
    response = client.get("/analytics/forecast-summary?periods=12")
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "success"
    forecast_data = data["data"]
    
    assert "historical" in forecast_data
    assert "forecast" in forecast_data
    assert "lower_bound" in forecast_data
    assert "upper_bound" in forecast_data
    assert "method" in forecast_data
    assert "confidence_level" in forecast_data
    
    assert len(forecast_data["historical"]) == 12
    assert len(forecast_data["forecast"]) == 12
    assert len(forecast_data["lower_bound"]) == 12
    assert len(forecast_data["upper_bound"]) == 12
    
    print("✅ Forecast summary endpoint passed")
    print(f"   Historical months: {len(forecast_data['historical'])}")
    print(f"   Forecast periods: {len(forecast_data['forecast'])}")


def test_recent_activity():
    """Test recent activity endpoint."""
    response = client.get("/analytics/recent-activity?limit=5")
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "success"
    assert "data" in data
    assert len(data["data"]) <= 5
    
    # Verify activity structure
    for activity in data["data"]:
        assert "id" in activity
        assert "type" in activity
        assert "title" in activity
        assert "description" in activity
        assert "timestamp" in activity
        assert "status" in activity
    
    print("✅ Recent activity endpoint passed")
    print(f"   Activities returned: {len(data['data'])}")
    if data["data"]:
        print(f"   Latest: {data['data'][0]['title']}")


def test_model_comparison():
    """Test model comparison endpoint."""
    response = client.get("/analytics/model-comparison")
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "success"
    comparison_data = data["data"]
    
    assert "models" in comparison_data
    assert "best_model" in comparison_data
    assert len(comparison_data["models"]) == 4
    
    # Verify model structure
    for model in comparison_data["models"]:
        assert "method" in model
        assert "mae" in model
        assert "rmse" in model
        assert "mape" in model
        assert "rank" in model
        assert "selected" in model
    
    # Verify best model is selected
    selected_models = [m for m in comparison_data["models"] if m["selected"]]
    assert len(selected_models) == 1
    assert selected_models[0]["method"] == comparison_data["best_model"]
    
    print("✅ Model comparison endpoint passed")
    print(f"   Best model: {comparison_data['best_model']}")
    print(f"   Models compared: {len(comparison_data['models'])}")


def run_all_tests():
    """Run all analytics API tests."""
    print("\n" + "=" * 70)
    print("Testing Analytics API Endpoints")
    print("=" * 70 + "\n")
    
    try:
        test_health_check()
        test_kpi_metrics()
        test_forecast_summary()
        test_recent_activity()
        test_model_comparison()
        
        print("\n" + "=" * 70)
        print("✅ All Analytics API Tests Passed!")
        print("=" * 70 + "\n")
        return 0
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())

