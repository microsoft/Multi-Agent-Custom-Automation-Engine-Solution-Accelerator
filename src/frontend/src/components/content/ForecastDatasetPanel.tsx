import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Button,
  Caption1,
  Card,
  Divider,
  Link,
  Spinner,
  Text,
  Tooltip,
} from '@fluentui/react-components';
import {
  ArrowDownload20Regular,
  Delete20Regular,
  DocumentData20Regular,
  Upload20Regular,
} from '@fluentui/react-icons';

import { DatasetMetadata } from '@/models';
import { DatasetService } from '@/services';

import '../../styles/ForecastDatasetPanel.css';

const ACCEPTED_TYPES = '.csv,.xlsx';

const formatSize = (bytes: number): string => {
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

const ForecastDatasetPanel: React.FC = () => {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [datasets, setDatasets] = useState<DatasetMetadata[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [uploading, setUploading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState<boolean>(false);

  const loadDatasets = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const items = await DatasetService.getDatasets();
      setDatasets(items);
    } catch (err) {
      console.error('Failed to load datasets', err);
      setError('Unable to load datasets');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadDatasets();
  }, [loadDatasets]);

  const handleFiles = useCallback(
    async (files: FileList | null) => {
      if (!files || files.length === 0) {
        return;
      }

      const file = files[0];
      setUploading(true);
      setError(null);

      try {
        await DatasetService.uploadDataset(file);
        await loadDatasets();
      } catch (err: unknown) {
        console.error('Failed to upload dataset', err);
        const message = err instanceof Error ? err.message : 'Upload failed';
        setError(message);
      } finally {
        setUploading(false);
      }
    },
    [loadDatasets],
  );

  const handleFileChange = useCallback(
    async (event: React.ChangeEvent<HTMLInputElement>) => {
      await handleFiles(event.target.files);
      if (event.target) {
        event.target.value = '';
      }
    },
    [handleFiles],
  );

  const handleDrop = useCallback(
    async (event: React.DragEvent<HTMLDivElement>) => {
      event.preventDefault();
      event.stopPropagation();
      setIsDragging(false);
      await handleFiles(event.dataTransfer?.files ?? null);
    },
    [handleFiles],
  );

  const handleDragOver = useCallback((event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.stopPropagation();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.stopPropagation();
    setIsDragging(false);
  }, []);

  const handleDelete = useCallback(
    async (datasetId: string) => {
      try {
        await DatasetService.deleteDataset(datasetId);
        await loadDatasets();
      } catch (err) {
        console.error('Failed to delete dataset', err);
        setError('Failed to delete dataset');
      }
    },
    [loadDatasets],
  );

  const datasetCountLabel = useMemo(() => {
    if (datasets.length === 0) {
      return 'No datasets yet';
    }
    if (datasets.length === 1) {
      return '1 dataset available';
    }
    return `${datasets.length} datasets available`;
  }, [datasets.length]);

  return (
    <Card className="forecast-dataset-panel" shadow>
      <div className="forecast-dataset-panel__header">
        <div>
          <Text weight="semibold">Financial datasets</Text>
          <Caption1 className="forecast-dataset-panel__caption">
            Upload CSV or Excel files for the forecasting agents to reference.
          </Caption1>
        </div>
        <Tooltip content="Upload dataset" relationship="label">
          <Button
            appearance="secondary"
            icon={<Upload20Regular />}
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
          >
            Upload
          </Button>
        </Tooltip>
      </div>

      <input
        ref={fileInputRef}
        type="file"
        accept={ACCEPTED_TYPES}
        onChange={handleFileChange}
        hidden
      />

      <div
        className={`forecast-dataset-panel__dropzone ${
          isDragging ? 'forecast-dataset-panel__dropzone--dragging' : ''
        }`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        role="presentation"
      >
        {uploading ? (
          <div className="forecast-dataset-panel__uploading">
            <Spinner size="small" label="Uploading dataset" />
          </div>
        ) : (
          <div className="forecast-dataset-panel__instructions">
            <DocumentData20Regular />
            <Text weight="semibold">Drag & drop dataset</Text>
            <Caption1>Accepted formats: CSV, XLSX</Caption1>
          </div>
        )}
      </div>

      {error && (
        <Text role="alert" className="forecast-dataset-panel__error">
          {error}
        </Text>
      )}

      <Divider className="forecast-dataset-panel__divider" />

      <div className="forecast-dataset-panel__list-header">
        <Text weight="semibold">{datasetCountLabel}</Text>
      </div>

      <div className="forecast-dataset-panel__list">
        {loading ? (
          <div className="forecast-dataset-panel__loading">
            <Spinner size="small" label="Loading datasets" />
          </div>
        ) : datasets.length === 0 ? (
          <Text>Upload a dataset to get started.</Text>
        ) : (
          datasets.map((dataset) => {
            const downloadHref = DatasetService.getDownloadUrl(dataset.dataset_id);
            return (
              <Card key={dataset.dataset_id} className="forecast-dataset-panel__item">
                <div className="forecast-dataset-panel__item-header">
                  <Text weight="semibold">{dataset.original_filename}</Text>
                  <div className="forecast-dataset-panel__item-actions">
                    <Tooltip content="Download" relationship="label">
                      <Link
                        appearance="subtle"
                        href={downloadHref}
                        target="_blank"
                        rel="noopener noreferrer"
                        aria-label={`Download ${dataset.original_filename}`}
                      >
                        <ArrowDownload20Regular />
                      </Link>
                    </Tooltip>
                    <Tooltip content="Remove" relationship="label">
                      <Button
                        appearance="subtle"
                        icon={<Delete20Regular />}
                        onClick={() => handleDelete(dataset.dataset_id)}
                      />
                    </Tooltip>
                  </div>
                </div>

                <Caption1>{formatSize(dataset.size_bytes)}</Caption1>

                {dataset.preview?.length ? (
                  <div className="forecast-dataset-panel__preview">
                    <Caption1>Sample rows</Caption1>
                    <table>
                      <thead>
                        <tr>
                          {dataset.columns.map((column) => (
                            <th key={column}>{column}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {dataset.preview.map((row, index) => (
                          <tr key={`${dataset.dataset_id}-row-${index}`}>
                            {dataset.columns.map((column) => (
                              <td key={`${dataset.dataset_id}-${column}-${index}`}>
                                {row[column] as React.ReactNode}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <Caption1>No preview available</Caption1>
                )}
              </Card>
            );
          })
        )}
      </div>
    </Card>
  );
};

export default ForecastDatasetPanel;
