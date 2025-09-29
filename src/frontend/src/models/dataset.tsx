export interface DatasetPreviewRow {
  [column: string]: unknown;
}

export interface DatasetMetadata {
  dataset_id: string;
  user_id?: string;
  original_filename: string;
  stored_filename: string;
  content_type: string;
  size_bytes: number;
  uploaded_at: string;
  columns: string[];
  preview: DatasetPreviewRow[];
  numeric_columns?: string[];
}

export interface DatasetUploadResponse {
  status: string;
  dataset: DatasetMetadata;
}

export interface DatasetListResponse {
  datasets: DatasetMetadata[];
}
