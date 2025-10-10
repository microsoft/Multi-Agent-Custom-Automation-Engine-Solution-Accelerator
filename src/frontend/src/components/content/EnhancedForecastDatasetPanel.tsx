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
  SearchBox,
  Menu,
  MenuTrigger,
  MenuPopover,
  MenuList,
  MenuItem,
  Badge,
} from '@fluentui/react-components';
import {
  ArrowDownload20Regular,
  Delete20Regular,
  DocumentData20Regular,
  ArrowUpload20Regular,
  ChartMultiple20Regular,
  Filter20Regular,
  DataUsage20Regular,
} from '@fluentui/react-icons';

import { DatasetMetadata } from '@/models';
import { DatasetService } from '@/services';

import '../../styles/EnhancedForecastDatasetPanel.css';

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

type FilterType = 'all' | 'csv' | 'xlsx';

const EnhancedForecastDatasetPanel: React.FC = () => {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [datasets, setDatasets] = useState<DatasetMetadata[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [uploading, setUploading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [filterType, setFilterType] = useState<FilterType>('all');

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

      setUploading(true);
      setError(null);

      try {
        // Support multiple file uploads
        const uploadPromises = Array.from(files).map((file) =>
          DatasetService.uploadDataset(file)
        );
        
        await Promise.all(uploadPromises);
        await loadDatasets();
      } catch (err: unknown) {
        console.error('Failed to upload dataset(s)', err);
        const message = err instanceof Error ? err.message : 'Upload failed';
        setError(message);
      } finally {
        setUploading(false);
      }
    },
    [loadDatasets]
  );

  const handleFileChange = useCallback(
    async (event: React.ChangeEvent<HTMLInputElement>) => {
      await handleFiles(event.target.files);
      if (event.target) {
        event.target.value = '';
      }
    },
    [handleFiles]
  );

  const handleDrop = useCallback(
    async (event: React.DragEvent<HTMLDivElement>) => {
      event.preventDefault();
      event.stopPropagation();
      setIsDragging(false);
      await handleFiles(event.dataTransfer?.files ?? null);
    },
    [handleFiles]
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
      if (!window.confirm('Are you sure you want to delete this dataset?')) {
        return;
      }
      
      try {
        await DatasetService.deleteDataset(datasetId);
        await loadDatasets();
      } catch (err) {
        console.error('Failed to delete dataset', err);
        setError('Failed to delete dataset');
      }
    },
    [loadDatasets]
  );

  // Filter datasets based on search and filter type
  const filteredDatasets = useMemo(() => {
    return datasets.filter((dataset) => {
      const matchesSearch = dataset.original_filename
        .toLowerCase()
        .includes(searchTerm.toLowerCase());
      
      const matchesType =
        filterType === 'all' ||
        (filterType === 'csv' && dataset.content_type.includes('csv')) ||
        (filterType === 'xlsx' && dataset.content_type.includes('xlsx'));
      
      return matchesSearch && matchesType;
    });
  }, [datasets, searchTerm, filterType]);

  const datasetCountLabel = useMemo(() => {
    const count = filteredDatasets.length;
    if (count === 0) {
      return searchTerm || filterType !== 'all' ? 'No matching datasets' : 'No datasets yet';
    }
    if (count === 1) {
      return '1 dataset';
    }
    return `${count} datasets`;
  }, [filteredDatasets.length, searchTerm, filterType]);

  return (
    <Card className="enhanced-forecast-dataset-panel" shadow>
      <div className="enhanced-forecast-dataset-panel__header">
        <div>
          <Text weight="semibold">Financial Datasets</Text>
          <Caption1 className="enhanced-forecast-dataset-panel__caption">
            Upload CSV or Excel files for analytics agents. Supports multi-file upload.
          </Caption1>
        </div>
        <Tooltip content="Upload dataset(s)" relationship="label">
          <Button
            appearance="primary"
            icon={<ArrowUpload20Regular />}
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
        multiple
        hidden
      />

      <div
        className={`enhanced-forecast-dataset-panel__dropzone ${
          isDragging ? 'enhanced-forecast-dataset-panel__dropzone--dragging' : ''
        }`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        role="presentation"
      >
        {uploading ? (
          <div className="enhanced-forecast-dataset-panel__uploading">
            <Spinner size="small" label="Uploading dataset(s)..." />
          </div>
        ) : (
          <div className="enhanced-forecast-dataset-panel__instructions">
            <DocumentData20Regular />
            <Text weight="semibold">Drag & drop datasets (multiple files supported)</Text>
            <Caption1>Accepted formats: CSV, XLSX</Caption1>
          </div>
        )}
      </div>

      {error && (
        <Text role="alert" className="enhanced-forecast-dataset-panel__error">
          {error}
        </Text>
      )}

      <Divider className="enhanced-forecast-dataset-panel__divider" />

      {/* Search and Filter Controls */}
      <div className="enhanced-forecast-dataset-panel__controls">
        <SearchBox
          placeholder="Search datasets..."
          value={searchTerm}
          onChange={(_, data) => setSearchTerm(data.value)}
          style={{ flex: 1 }}
        />
        
        <Menu>
          <MenuTrigger disableButtonEnhancement>
            <Button icon={<Filter20Regular />} appearance="subtle">
              {filterType === 'all' ? 'All Types' : filterType.toUpperCase()}
            </Button>
          </MenuTrigger>
          <MenuPopover>
            <MenuList>
              <MenuItem onClick={() => setFilterType('all')}>All Types</MenuItem>
              <MenuItem onClick={() => setFilterType('csv')}>CSV Only</MenuItem>
              <MenuItem onClick={() => setFilterType('xlsx')}>XLSX Only</MenuItem>
            </MenuList>
          </MenuPopover>
        </Menu>
      </div>

      <div className="enhanced-forecast-dataset-panel__list-header">
        <Text weight="semibold">{datasetCountLabel}</Text>
      </div>

      <div className="enhanced-forecast-dataset-panel__list">
        {loading ? (
          <div className="enhanced-forecast-dataset-panel__loading">
            <Spinner size="small" label="Loading datasets" />
          </div>
        ) : filteredDatasets.length === 0 ? (
          <Text>
            {searchTerm || filterType !== 'all'
              ? 'No datasets match your filters.'
              : 'Upload a dataset to get started.'}
          </Text>
        ) : (
          filteredDatasets.map((dataset) => {
            const downloadHref = DatasetService.getDownloadUrl(dataset.dataset_id);
            const isCSV = dataset.content_type.includes('csv');
            
            return (
              <Card key={dataset.dataset_id} className="enhanced-dataset-card">
                <div className="enhanced-dataset-card__header">
                  <div className="enhanced-dataset-card__title">
                    <Text weight="semibold">{dataset.original_filename}</Text>
                    <Badge appearance="outline" color={isCSV ? 'success' : 'brand'}>
                      {isCSV ? 'CSV' : 'XLSX'}
                    </Badge>
                  </div>
                  
                  <div className="enhanced-dataset-card__actions">
                    <Tooltip content="View statistics" relationship="label">
                      <Button
                        appearance="subtle"
                        icon={<DataUsage20Regular />}
                        size="small"
                      />
                    </Tooltip>
                    <Tooltip content="Visualize" relationship="label">
                      <Button
                        appearance="subtle"
                        icon={<ChartMultiple20Regular />}
                        size="small"
                      />
                    </Tooltip>
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
                        size="small"
                      />
                    </Tooltip>
                  </div>
                </div>

                <div className="enhanced-dataset-card__meta">
                  <Caption1>{formatSize(dataset.size_bytes)}</Caption1>
                  <Caption1>•</Caption1>
                  <Caption1>{dataset.columns.length} columns</Caption1>
                  {dataset.numeric_columns && dataset.numeric_columns.length > 0 && (
                    <>
                      <Caption1>•</Caption1>
                      <Caption1>{dataset.numeric_columns.length} numeric</Caption1>
                    </>
                  )}
                </div>

                {dataset.preview?.length ? (
                  <div className="enhanced-dataset-card__preview">
                    <Caption1 weight="semibold">Sample Rows</Caption1>
                    <div className="preview-table-wrapper">
                      <table className="preview-table">
                        <thead>
                          <tr>
                            {dataset.columns.slice(0, 5).map((column) => (
                              <th key={column}>{column}</th>
                            ))}
                            {dataset.columns.length > 5 && <th>...</th>}
                          </tr>
                        </thead>
                        <tbody>
                          {dataset.preview.slice(0, 3).map((row, index) => (
                            <tr key={`${dataset.dataset_id}-row-${index}`}>
                              {dataset.columns.slice(0, 5).map((column) => (
                                <td key={`${dataset.dataset_id}-${column}-${index}`}>
                                  {String(row[column] || '')}
                                </td>
                              ))}
                              {dataset.columns.length > 5 && <td>...</td>}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
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

export default EnhancedForecastDatasetPanel;

