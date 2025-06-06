# API Service Documentation

## Overview

The `apiService` is a unified service for interacting with the backend `app_kernel.py`. It provides a centralized interface for all API calls, with additional features like caching, request tracking, and utility methods.

## Features

- **Unified Interface**: All API endpoints are accessible from a single service.
- **Caching**: Automatic caching of responses for improved performance.
- **Request Tracking**: Prevents duplicate requests for the same resource.
- **Error Handling**: Consistent error handling across all endpoints.
- **Utility Methods**: Helper methods for common operations.

## Usage

### Basic Usage

```tsx
import { apiService } from "../api/apiService";

// Get all plans
const plans = await apiService.getPlans();

// Submit a new task
const response = await apiService.submitInputTask({
  description: "My new task",
});
```

### Caching

The service includes built-in caching for improved performance. By default, cached data expires after 30 seconds.

```tsx
// Use cached data if available (default)
const plans = await apiService.getPlans(sessionId, true);

// Force fresh data from server
const freshPlans = await apiService.getPlans(sessionId, false);

// Clear all cached data
apiService.clearCache();
```

### Utility Methods

The service provides utility methods for common operations:

```tsx
// Check if a plan is complete
const isComplete = apiService.isPlanComplete(plan);

// Get steps awaiting feedback
const pendingSteps = apiService.getStepsAwaitingFeedback(plan);

// Get plan completion percentage
const progress = apiService.getPlanCompletionPercentage(plan);
```

## API Reference

### Task Methods

- `submitInputTask(inputTask: InputTask): Promise<InputTaskResponse>`

### Plan Methods

- `getPlans(sessionId?: string, useCache = true): Promise<PlanWithSteps[]>`
- `getPlanWithSteps(sessionId: string, planId: string, useCache = true): Promise<PlanWithSteps>`
- `getSteps(planId: string, useCache = true): Promise<Step[]>`
- `updateStep(sessionId: string, planId: string, stepId: string, update: {...}): Promise<Step>`

### Feedback Methods

- `provideStepFeedback(stepId: string, planId: string, sessionId: string, approved: boolean, ...): Promise<...>`
- `approveSteps(planId: string, sessionId: string, approved: boolean, ...): Promise<{ status: string }>`
- `submitClarification(planId: string, sessionId: string, clarification: string): Promise<...>`

### Message Methods

- `getAgentMessages(sessionId: string, useCache = true): Promise<AgentMessage[]>`
- `deleteAllMessages(): Promise<{ status: string }>`
- `getAllMessages(useCache = true): Promise<any[]>`

### Utility Methods

- `isPlanComplete(plan: PlanWithSteps): boolean`
- `getStepsAwaitingFeedback(plan: PlanWithSteps): Step[]`
- `getStepsForAgent(plan: PlanWithSteps, agentType: AgentType): Step[]`
- `clearCache(): void`
- `getPlanProgressStatus(plan: PlanWithSteps): Record<StepStatus, number>`
- `getPlanCompletionPercentage(plan: PlanWithSteps): number`

## Architecture

The service is built on top of the `apiClient` which handles the HTTP requests and error handling. The service layer adds additional functionality like caching and request tracking.

### Caching

Responses are cached using a simple in-memory cache with expiration. Cache keys are based on the endpoint and parameters.

### Request Tracking

The service tracks in-progress requests to prevent duplicate requests for the same resource, which helps avoid race conditions and unnecessary network traffic.

## Migration Guide

If you're migrating from the individual services (taskService, planService, etc.), here's how to update your code:

Before:

```tsx
import { planService } from "../api";

const plans = await planService.getPlans(sessionId);
```

After:

```tsx
import { apiService } from "../api";

const plans = await apiService.getPlans(sessionId);
```

Most methods have compatible signatures, so migration should be straightforward.
