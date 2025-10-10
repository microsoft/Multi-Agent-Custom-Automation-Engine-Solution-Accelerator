import { apiClient } from '@/api/apiClient';

const ANALYTICS_BASE_ENDPOINT = '/v3/analytics';

export interface KPIData {
  revenue_forecast: {
    value: string;
    change: number;
    change_label: string;
  };
  customer_retention: {
    value: string;
    change: number;
    change_label: string;
  };
  avg_order_value: {
    value: string;
    change: number;
    change_label: string;
  };
  forecast_accuracy: {
    value: string;
    change: number;
    change_label: string;
  };
}

export interface ForecastSummary {
  method: string;
  periods: number;
  data_points: {
    period: string;
    actual?: number;
    forecast?: number;
    lower_bound?: number;
    upper_bound?: number;
  }[];
}

export interface Activity {
  id: string;
  type: string;
  description: string;
  timestamp: string;
}

export interface ModelComparison {
  methods: {
    name: string;
    mae: number;
    rmse: number;
    mape: number;
    rank: number;
  }[];
}

export interface HealthCheck {
  status: string;
  timestamp: string;
  services: {
    mcp_server: string;
    database: string;
    cache: string;
  };
}

export class AnalyticsService {
  /**
   * Get KPI summary data for the dashboard
   */
  static async getKPIs(): Promise<KPIData> {
    try {
      const response = await apiClient.get(`${ANALYTICS_BASE_ENDPOINT}/kpis`);
      return response as KPIData;
    } catch (error) {
      console.error('Failed to fetch KPIs', error);
      throw error;
    }
  }

  /**
   * Get forecast summary for charts
   */
  static async getForecastSummary(): Promise<ForecastSummary> {
    try {
      const response = await apiClient.get(`${ANALYTICS_BASE_ENDPOINT}/forecast-summary`);
      return response as ForecastSummary;
    } catch (error) {
      console.error('Failed to fetch forecast summary', error);
      throw error;
    }
  }

  /**
   * Get recent activity log
   */
  static async getRecentActivity(): Promise<Activity[]> {
    try {
      const response = await apiClient.get(`${ANALYTICS_BASE_ENDPOINT}/recent-activity`);
      return response.activities as Activity[];
    } catch (error) {
      console.error('Failed to fetch recent activity', error);
      throw error;
    }
  }

  /**
   * Get model comparison data
   */
  static async getModelComparison(): Promise<ModelComparison> {
    try {
      const response = await apiClient.get(`${ANALYTICS_BASE_ENDPOINT}/model-comparison`);
      return response as ModelComparison;
    } catch (error) {
      console.error('Failed to fetch model comparison', error);
      throw error;
    }
  }

  /**
   * Health check for analytics API
   */
  static async checkHealth(): Promise<HealthCheck> {
    try {
      const response = await apiClient.get(`${ANALYTICS_BASE_ENDPOINT}/health`);
      return response as HealthCheck;
    } catch (error) {
      console.error('Failed to check analytics health', error);
      throw error;
    }
  }
}

