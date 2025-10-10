import React, { useState } from 'react';
import {
  Card,
  Text,
  Button,
  Spinner,
  Badge,
  Table,
  TableHeader,
  TableRow,
  TableHeaderCell,
  TableBody,
  TableCell,
} from '@fluentui/react-components';
import { ForecastChart } from './ForecastChart';

import '../../styles/ModelComparisonPanel.css';

export interface ModelMetrics {
  model_name: string;
  mae: number;
  rmse: number;
  mape: number;
  forecast: number[];
  lower_bound?: number[];
  upper_bound?: number[];
}

export interface ModelComparisonProps {
  models: ModelMetrics[];
  historical: number[];
  periods: (string | number)[];
  loading?: boolean;
  onSelectModel?: (modelName: string) => void;
}

export const ModelComparisonPanel: React.FC<ModelComparisonProps> = ({
  models,
  historical,
  periods,
  loading = false,
  onSelectModel,
}) => {
  const [selectedModel, setSelectedModel] = useState<string | null>(
    models.length > 0 ? models[0].model_name : null
  );

  if (loading) {
    return (
      <Card className="model-comparison">
        <div className="model-comparison__loading">
          <Spinner size="large" label="Evaluating forecast models..." />
        </div>
      </Card>
    );
  }

  if (models.length === 0) {
    return (
      <Card className="model-comparison">
        <Text>No models to compare. Run forecast evaluation first.</Text>
      </Card>
    );
  }

  // Find best model (lowest MAPE)
  const bestModel = models.reduce((best, current) =>
    current.mape < best.mape ? current : best
  , models[0]);

  const handleSelectModel = (modelName: string) => {
    setSelectedModel(modelName);
    onSelectModel?.(modelName);
  };

  // Prepare data for selected model chart
  const selectedModelData = selectedModel
    ? models.find((m) => m.model_name === selectedModel)
    : null;

  const chartData = periods.map((period, i) => ({
    period,
    actual: i < historical.length ? historical[i] : undefined,
    forecast: selectedModelData?.forecast[i],
    lower_bound: selectedModelData?.lower_bound?.[i],
    upper_bound: selectedModelData?.upper_bound?.[i],
  }));

  return (
    <div className="model-comparison">
      {/* Summary Card */}
      <Card className="model-comparison__summary">
        <Text weight="semibold" size={500}>
          Model Performance Comparison
        </Text>
        <Text>
          Evaluated {models.length} forecasting model{models.length !== 1 ? 's' : ''}. 
          Best performer: <strong>{bestModel.model_name}</strong> (MAPE: {bestModel.mape.toFixed(2)}%)
        </Text>
      </Card>

      {/* Metrics Table */}
      <Card className="model-comparison__table">
        <Text weight="semibold" size={400} style={{ marginBottom: '1rem' }}>
          Accuracy Metrics
        </Text>

        <Table>
          <TableHeader>
            <TableRow>
              <TableHeaderCell>Model</TableHeaderCell>
              <TableHeaderCell>MAE</TableHeaderCell>
              <TableHeaderCell>RMSE</TableHeaderCell>
              <TableHeaderCell>MAPE</TableHeaderCell>
              <TableHeaderCell>Rank</TableHeaderCell>
              <TableHeaderCell>Action</TableHeaderCell>
            </TableRow>
          </TableHeader>
          <TableBody>
            {models
              .sort((a, b) => a.mape - b.mape)
              .map((model, index) => (
                <TableRow key={model.model_name}>
                  <TableCell>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      {model.model_name}
                      {model.model_name === bestModel.model_name && (
                        <Badge appearance="filled" color="success">
                          Best
                        </Badge>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>{model.mae.toFixed(2)}</TableCell>
                  <TableCell>{model.rmse.toFixed(2)}</TableCell>
                  <TableCell>{model.mape.toFixed(2)}%</TableCell>
                  <TableCell>#{index + 1}</TableCell>
                  <TableCell>
                    <Button
                      size="small"
                      appearance={
                        selectedModel === model.model_name ? 'primary' : 'secondary'
                      }
                      onClick={() => handleSelectModel(model.model_name)}
                    >
                      {selectedModel === model.model_name ? 'Selected' : 'Select'}
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
          </TableBody>
        </Table>
      </Card>

      {/* Visual Comparison */}
      {selectedModel && (
        <ForecastChart
          data={chartData}
          title={`${selectedModel} Forecast`}
          showConfidenceInterval={true}
          height={350}
        />
      )}
    </div>
  );
};

export default ModelComparisonPanel;



