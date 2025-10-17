/**
 * Tests for apiService
 * Verifies that upload methods correctly use apiClient
 */
import { apiService } from '../apiService';
import { apiClient } from '../apiClient';

// Mock the apiClient module
jest.mock('../apiClient', () => ({
  apiClient: {
    get: jest.fn(),
    post: jest.fn(),
    put: jest.fn(),
    delete: jest.fn(),
    upload: jest.fn(),
  },
}));

describe('apiService', () => {
  beforeEach(() => {
    // Clear all mocks before each test
    jest.clearAllMocks();
  });

  describe('uploadDatasetInChat', () => {
    it('should call apiClient.upload with correct path and formData', async () => {
      // Setup mock
      const mockUploadResponse = {
        status: 'success',
        dataset: {
          dataset_id: 'test-123',
          original_filename: 'test.csv',
        },
      };
      (apiClient.upload as jest.Mock).mockResolvedValue(mockUploadResponse);

      // Create test FormData
      const formData = new FormData();
      const blob = new Blob(['test content'], { type: 'text/csv' });
      formData.append('file', blob, 'test.csv');
      formData.append('plan_id', 'plan-123');

      // Call the method
      const result = await apiService.uploadDatasetInChat(formData);

      // Verify apiClient.upload was called with correct arguments
      expect(apiClient.upload).toHaveBeenCalledWith(
        '/v3/datasets/upload_in_chat',
        formData
      );
      expect(apiClient.upload).toHaveBeenCalledTimes(1);

      // Verify result
      expect(result).toEqual(mockUploadResponse);
    });

    it('should propagate errors from apiClient.upload', async () => {
      // Setup mock to throw error
      const mockError = new Error('Upload failed: Network error');
      (apiClient.upload as jest.Mock).mockRejectedValue(mockError);

      // Create test FormData
      const formData = new FormData();
      const blob = new Blob(['test'], { type: 'text/csv' });
      formData.append('file', blob);

      // Call should throw error
      await expect(apiService.uploadDatasetInChat(formData)).rejects.toThrow(
        'Upload failed: Network error'
      );
    });

    it('should handle FormData with multiple fields', async () => {
      // Setup mock
      (apiClient.upload as jest.Mock).mockResolvedValue({ status: 'success' });

      // Create FormData with multiple fields
      const formData = new FormData();
      formData.append('file', new Blob(['data'], { type: 'text/csv' }), 'data.csv');
      formData.append('plan_id', 'plan-456');
      formData.append('metadata', JSON.stringify({ source: 'chat' }));

      // Call the method
      await apiService.uploadDatasetInChat(formData);

      // Verify formData was passed as-is
      expect(apiClient.upload).toHaveBeenCalledWith(
        '/v3/datasets/upload_in_chat',
        formData
      );
    });
  });
});


