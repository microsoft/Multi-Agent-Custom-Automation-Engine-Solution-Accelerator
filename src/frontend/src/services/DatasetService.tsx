import { apiClient } from '@/api/apiClient';
import { getApiUrl } from '@/api/config';
import {
  DatasetListResponse,
  DatasetMetadata,
  DatasetUploadResponse,
} from '@/models';

const DATASET_UPLOAD_ENDPOINT = '/v3/datasets/upload';
const DATASET_LIST_ENDPOINT = '/v3/datasets';

export class DatasetService {
  static async uploadDataset(file: File): Promise<DatasetMetadata> {
    const formData = new FormData();
    formData.append('file', file);

    const response = (await apiClient.upload(
      DATASET_UPLOAD_ENDPOINT,
      formData,
    )) as DatasetUploadResponse;

    return response.dataset;
  }

  static async getDatasets(): Promise<DatasetMetadata[]> {
    const response = (await apiClient.get(
      DATASET_LIST_ENDPOINT,
    )) as DatasetListResponse;

    return response.datasets || [];
  }

  static async deleteDataset(datasetId: string): Promise<void> {
    await apiClient.delete(`${DATASET_LIST_ENDPOINT}/${datasetId}`);
  }

  static getDownloadUrl(datasetId: string): string {
    const baseUrl = getApiUrl();
    return `${baseUrl}/v3/datasets/${datasetId}/download`;
  }
}
