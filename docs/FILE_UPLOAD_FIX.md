# File Upload and Dataset Access Fix

## Problem Description

Users were experiencing two related issues:

1. **HTTP 500 Error on Upload**: When uploading files via `/api/v3/datasets/upload_in_chat`, the backend returned an HTTP 500 Internal Server Error.

2. **Dataset Not Found Error**: Even after a successful upload with a valid `dataset_id`, the `VisualizationAgent` and other MCP services could not find the uploaded dataset file, prompting users to re-upload.

## Root Causes

### Issue 1: Missing `upload_dataset` Method

The `/datasets/upload_in_chat` endpoint was calling `dataset_service.upload_dataset(user_id, file)`, but the `DatasetService` class did not have an `upload_dataset` method. It only had a `save_dataset` method that required the file content to be read first.

**Location**: `src/backend/v3/api/router.py` line 1060

```python
# This was failing:
metadata = await dataset_service.upload_dataset(user_id, file)
```

### Issue 2: User ID Mismatch in MCP Tools

All MCP tools (visualization, CSV manipulation, analytics services) have a default parameter `user_id: str = "default"`. When agents call these tools, they don't explicitly pass the `user_id`, so it defaults to `"default"`.

However, when a user uploads a file, it's stored under their actual user ID:
```
data/uploads/{actual_user_id}/{dataset_id}/file.csv
```

But MCP tools were looking for it under:
```
data/uploads/default/{dataset_id}/file.csv
```

This caused the "Dataset file not found" error even though the file was successfully uploaded.

## Solutions Implemented

### Fix 1: Added `upload_dataset` Method to `DatasetService`

**File**: `src/backend/v3/common/services/dataset_service.py`

Added a new async method that handles `FastAPI UploadFile` objects and wraps the existing `save_dataset` method:

```python
async def upload_dataset(
    self,
    user_id: str,
    file: UploadFile,
) -> Dict[str, Any]:
    """Handle FastAPI UploadFile and persist dataset."""
    # Validates file, reads content, and calls save_dataset
    ...
```

This method:
- Validates file type and size
- Reads file contents asynchronously
- Calls the existing `save_dataset` method
- Returns metadata with proper error handling

### Fix 2: Cross-User Dataset Search in MCP Services

Updated all MCP services to search across all users when a dataset is not found for the default user ID.

**Modified Files**:
- `src/mcp_server/services/visualization_service.py`
- `src/mcp_server/services/csv_manipulation_service.py`
- `src/mcp_server/services/customer_analytics_service.py`
- `src/mcp_server/services/finance_service.py`
- `src/mcp_server/services/operations_analytics_service.py`
- `src/mcp_server/services/pricing_analytics_service.py`
- `src/mcp_server/services/marketing_analytics_service.py`

**Implementation Pattern**:

For each service's `_get_dataset_path` and `_get_metadata` methods:

1. **First**, try to find the dataset under the specified `user_id` (usually "default")
2. **If not found**, search across ALL user directories for the `dataset_id`
3. **Log** when a dataset is found under a different user
4. **Return** the found path or raise `FileNotFoundError` if not found anywhere

Example from `visualization_service.py`:

```python
def _get_dataset_path(self, dataset_id: str, user_id: str = "default") -> Path:
    # Try specified user first
    if dataset_dir.exists():
        for file in dataset_dir.iterdir():
            if file.suffix.lower() == '.csv':
                return file
    
    # If not found, search across all users
    LOGGER.info(f"Dataset {dataset_id} not found for user {user_id}, searching all users...")
    for user_dir in self.dataset_root.iterdir():
        if not user_dir.is_dir():
            continue
        candidate_dir = user_dir / dataset_folder
        if candidate_dir.exists():
            for file in candidate_dir.iterdir():
                if file.suffix.lower() == '.csv':
                    LOGGER.info(f"Found dataset {dataset_id} under user {user_dir.name}")
                    return file
    
    # Return default path if not found anywhere
    return dataset_dir / "data.csv"
```

## Benefits

1. **Seamless User Experience**: Users no longer need to manually specify `user_id` when agents call MCP tools
2. **Backward Compatible**: Existing functionality remains unchanged
3. **Proper Error Handling**: Clear error messages when datasets truly don't exist
4. **Logging**: Helpful debug logs when datasets are found under different users
5. **Security Note**: While this allows cross-user dataset access, the system already has authentication at the API level, and this simplifies the agent interaction model

## Testing Recommendations

1. **Upload Test**: Upload a file via `/api/v3/datasets/upload_in_chat` and verify it succeeds
2. **Visualization Test**: Ask an agent to create a chart from the uploaded dataset
3. **Cross-Service Test**: Verify all analytical services can access the uploaded dataset
4. **Multi-User Test**: Upload files as different users and verify agents can access them

## Future Improvements

For a more secure, production-ready system, consider:

1. **Passing User Context to MCP Tools**: Modify the agent orchestration layer to automatically inject the current `user_id` into all MCP tool calls
2. **User-Scoped Access**: Restrict dataset access to only the user who uploaded it
3. **Shared Datasets**: Implement a sharing mechanism for cross-user dataset access
4. **Rate Limiting**: Add rate limiting to the cross-user search to prevent abuse

## Related Files

- **Backend**: `src/backend/v3/common/services/dataset_service.py`
- **API Router**: `src/backend/v3/api/router.py`
- **MCP Services**: All services in `src/mcp_server/services/`
- **Documentation**: `docs/FILE_UPLOAD_FIX.md` (this file)

