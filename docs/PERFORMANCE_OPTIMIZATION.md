# Performance Optimization Guide

**Multi-Agent Custom Automation Engine Solution Accelerator**  
**Version:** 1.0  
**Last Updated:** October 10, 2025

---

## Overview

This guide provides strategies and best practices for optimizing the performance of the Multi-Agent Custom Automation Engine in production environments.

**Target Performance Metrics:**
- API Response Time: p95 < 500ms, p99 < 1s
- Forecast Generation: < 5s for 12-month forecasts
- Dataset Upload: < 10s for 50MB files
- Agent Execution: < 30s for standard workflows
- Concurrent Users: 100+ without degradation

---

## Table of Contents

1. [Backend API Optimization](#backend-api-optimization)
2. [Cosmos DB Performance](#cosmos-db-performance)
3. [Azure OpenAI Optimization](#azure-openai-optimization)
4. [Frontend Performance](#frontend-performance)
5. [MCP Server Optimization](#mcp-server-optimization)
6. [Caching Strategies](#caching-strategies)
7. [Network & CDN](#network--cdn)
8. [Monitoring & Profiling](#monitoring--profiling)

---

## Backend API Optimization

### 1. Async Operations

**Use async/await for I/O operations:**

```python
# ✅ Good - Async I/O
async def get_dataset(dataset_id: str):
    async with cosmos_client.get_database_client("macae-db") as db:
        container = db.get_container_client("datasets")
        return await container.read_item(item=dataset_id, partition_key=dataset_id)

# ❌ Bad - Blocking I/O
def get_dataset_sync(dataset_id: str):
    db = cosmos_client.get_database_client("macae-db")
    container = db.get_container_client("datasets")
    return container.read_item(item=dataset_id, partition_key=dataset_id)
```

### 2. Connection Pooling

**Configure connection limits:**

```python
# backend/app_kernel.py
from fastapi import FastAPI
import uvicorn

app = FastAPI()

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        workers=4,  # Number of worker processes
        limit_concurrency=1000,  # Max concurrent connections
        backlog=2048  # Connection queue size
    )
```

### 3. Response Compression

**Enable gzip compression:**

```python
from fastapi.middleware.gzip import GZipMiddleware

app.add_middleware(GZipMiddleware, minimum_size=1000)
```

### 4. Pagination

**Implement pagination for large result sets:**

```python
@app.get("/api/v3/datasets")
async def list_datasets(skip: int = 0, limit: int = 50):
    # Limit max page size
    limit = min(limit, 100)
    
    query = "SELECT * FROM c OFFSET @skip LIMIT @limit"
    items = container.query_items(
        query=query,
        parameters=[
            {"name": "@skip", "value": skip},
            {"name": "@limit", "value": limit}
        ],
        enable_cross_partition_query=True
    )
    return {"items": list(items), "skip": skip, "limit": limit}
```

### 5. Background Tasks

**Use FastAPI background tasks for non-critical operations:**

```python
from fastapi import BackgroundTasks

def send_notification_email(user_id: str, message: str):
    # Send email (slow operation)
    pass

@app.post("/api/v3/forecast")
async def generate_forecast(request: ForecastRequest, background_tasks: BackgroundTasks):
    # Generate forecast (critical path)
    forecast = await forecaster.generate(request)
    
    # Send notification in background (non-critical)
    background_tasks.add_task(send_notification_email, request.user_id, "Forecast complete")
    
    return forecast
```

---

## Cosmos DB Performance

### 1. Partition Key Design

**Use effective partition keys:**

```json
// ✅ Good - High cardinality, evenly distributed
{
  "id": "dataset_123",
  "customerId": "customer_456",  // Partition key
  "name": "sales_data.csv"
}

// ❌ Bad - Low cardinality, hot partitions
{
  "id": "dataset_123",
  "dataType": "csv",  // Only a few unique values
  "name": "sales_data.csv"
}
```

**Best practices:**
- **High cardinality**: Many unique values (customer_id, user_id, plan_id)
- **Even distribution**: No hot partitions
- **Query alignment**: Most queries include partition key

### 2. Indexing Strategy

**Optimize indexing policy:**

```json
{
  "indexingMode": "consistent",
  "automatic": true,
  "includedPaths": [
    {
      "path": "/customerId/?",
      "indexes": [
        {
          "kind": "Range",
          "dataType": "String"
        }
      ]
    },
    {
      "path": "/createdAt/?",
      "indexes": [
        {
          "kind": "Range",
          "dataType": "Number"
        }
      ]
    }
  ],
  "excludedPaths": [
    {
      "path": "/content/*"  // Don't index large blob content
    },
    {
      "path": "/metadata/*"  // Don't index metadata
    }
  ]
}
```

**Apply indexing policy:**

```bash
az cosmosdb sql container update \
  --account-name your-cosmos-account \
  --resource-group rg-macae-prod \
  --database-name macae-db \
  --name datasets \
  --idx @indexing-policy.json
```

### 3. Point Reads

**Use point reads when possible (1 RU vs 2.3+ RU for queries):**

```python
# ✅ Good - Point read (1 RU)
item = container.read_item(
    item="dataset_123",
    partition_key="customer_456"
)

# ❌ Suboptimal - Query (2.3+ RU)
query = "SELECT * FROM c WHERE c.id = 'dataset_123'"
items = list(container.query_items(query=query, partition_key="customer_456"))
item = items[0] if items else None
```

### 4. Autoscale Throughput

**Configure autoscale for variable workloads:**

```bash
az cosmosdb sql container throughput update \
  --account-name your-cosmos-account \
  --resource-group rg-macae-prod \
  --database-name macae-db \
  --name datasets \
  --max-throughput 4000  # Autoscale 400-4000 RU/s
```

**Cost optimization:**
- Use autoscale for variable traffic
- Use manual provisioning for steady traffic
- Monitor RU consumption via Application Insights

### 5. Batch Operations

**Use batch operations for bulk inserts:**

```python
from azure.cosmos import PartitionKey

# ✅ Good - Batch operations
async def bulk_insert_datasets(datasets: list):
    operations = [
        ("create", (dataset,)) 
        for dataset in datasets
        if dataset["customerId"] == partition_key_value
    ]
    
    result = await container.execute_item_batch(
        batch_operations=operations,
        partition_key=partition_key_value
    )
    return result

# ❌ Suboptimal - Individual inserts
async def insert_datasets_one_by_one(datasets: list):
    for dataset in datasets:
        await container.create_item(dataset)
```

---

## Azure OpenAI Optimization

### 1. Token Management

**Minimize token usage:**

```python
# ✅ Good - Concise prompts
prompt = f"Forecast revenue for next 12 months. Data: {summary_stats}"

# ❌ Wasteful - Verbose prompts
prompt = f"""
Please analyze the following complete dataset and generate a comprehensive 
financial forecast for the next 12 months, taking into consideration all 
historical trends, seasonal patterns, and any anomalies you might detect...

Complete Data: {full_dataset_string}  # Thousands of rows
"""
```

**Use summarization:**
- Send summary statistics instead of raw data
- Use embeddings for large documents
- Cache frequent prompts

### 2. Request Batching

**Batch multiple requests when possible:**

```python
# ✅ Good - Single request with multiple questions
async def analyze_multiple_datasets(dataset_ids: list):
    summaries = [get_dataset_summary(id) for id in dataset_ids]
    prompt = f"Analyze these datasets: {summaries}"
    response = await openai_client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return response

# ❌ Suboptimal - Multiple sequential requests
async def analyze_datasets_separately(dataset_ids: list):
    results = []
    for dataset_id in dataset_ids:
        summary = get_dataset_summary(dataset_id)
        response = await openai_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": f"Analyze: {summary}"}]
        )
        results.append(response)
    return results
```

### 3. Model Selection

**Use appropriate models:**

| Use Case | Model | TPM Quota | Cost |
|----------|-------|-----------|------|
| Complex analytics | GPT-4 Turbo | 50K | $$$ |
| Simple forecasts | GPT-3.5 Turbo | 100K | $ |
| Embeddings | text-embedding-ada-002 | 150K | $ |
| Quick summaries | GPT-3.5 Turbo | 100K | $ |

### 4. Retry Logic with Exponential Backoff

**Handle rate limits gracefully:**

```python
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
async def call_openai_with_retry(prompt: str):
    try:
        response = await openai_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        return response
    except RateLimitError as e:
        # Will automatically retry with exponential backoff
        raise e
```

### 5. Response Streaming

**Stream responses for better UX:**

```python
@app.post("/api/v3/forecast/stream")
async def generate_forecast_stream(request: ForecastRequest):
    async def generate():
        stream = await openai_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": request.prompt}],
            stream=True
        )
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield f"data: {chunk.choices[0].delta.content}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")
```

---

## Frontend Performance

### 1. Code Splitting

**Use React lazy loading:**

```typescript
// ✅ Good - Lazy load heavy components
import { lazy, Suspense } from 'react';

const AnalyticsDashboard = lazy(() => import('./pages/AnalyticsDashboard'));
const ForecastChart = lazy(() => import('./components/ForecastChart'));

function App() {
  return (
    <Suspense fallback={<LoadingSpinner />}>
      <Routes>
        <Route path="/analytics" element={<AnalyticsDashboard />} />
      </Routes>
    </Suspense>
  );
}
```

### 2. Memoization

**Optimize renders with React.memo:**

```typescript
// ✅ Good - Memoized component
import { memo } from 'react';

interface ForecastChartProps {
  data: number[];
  labels: string[];
}

export const ForecastChart = memo(({ data, labels }: ForecastChartProps) => {
  return <LineChart data={data} labels={labels} />;
});

// ❌ Suboptimal - Re-renders on every parent update
export const ForecastChart = ({ data, labels }: ForecastChartProps) => {
  return <LineChart data={data} labels={labels} />;
};
```

### 3. Virtualization

**Virtualize large lists:**

```typescript
import { FixedSizeList } from 'react-window';

function DatasetList({ datasets }: { datasets: Dataset[] }) {
  const Row = ({ index, style }: { index: number; style: React.CSSProperties }) => (
    <div style={style}>
      <DatasetItem dataset={datasets[index]} />
    </div>
  );

  return (
    <FixedSizeList
      height={600}
      itemCount={datasets.length}
      itemSize={80}
      width="100%"
    >
      {Row}
    </FixedSizeList>
  );
}
```

### 4. Image Optimization

**Use WebP format and lazy loading:**

```typescript
<img
  src="/images/chart.webp"
  alt="Forecast Chart"
  loading="lazy"
  width={800}
  height={400}
/>
```

### 5. Bundle Optimization

**Configure Vite for production builds:**

```typescript
// vite.config.ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
          'ui-vendor': ['@fluentui/react-components'],
          'chart-vendor': ['recharts']
        }
      }
    },
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true  // Remove console.log in production
      }
    }
  }
});
```

---

## MCP Server Optimization

### 1. Tool Execution Timeout

**Set appropriate timeouts:**

```python
import asyncio

async def execute_tool_with_timeout(tool_func, *args, timeout=300):
    try:
        return await asyncio.wait_for(tool_func(*args), timeout=timeout)
    except asyncio.TimeoutError:
        return {"error": f"Tool execution exceeded {timeout}s timeout"}
```

### 2. Parallel Tool Execution

**Execute independent tools in parallel:**

```python
import asyncio

async def run_analytics_suite(dataset_id: str):
    # ✅ Good - Parallel execution
    results = await asyncio.gather(
        analyze_churn(dataset_id),
        calculate_clv(dataset_id),
        segment_customers(dataset_id)
    )
    return {
        "churn": results[0],
        "clv": results[1],
        "segments": results[2]
    }

# ❌ Suboptimal - Sequential execution
async def run_analytics_suite_sequential(dataset_id: str):
    churn = await analyze_churn(dataset_id)
    clv = await calculate_clv(dataset_id)
    segments = await segment_customers(dataset_id)
    return {"churn": churn, "clv": clv, "segments": segments}
```

### 3. Result Streaming

**Stream large results:**

```python
async def stream_forecast_results(dataset_id: str):
    forecast = await generate_forecast(dataset_id)
    
    # Stream results in chunks
    chunk_size = 100
    for i in range(0, len(forecast), chunk_size):
        yield forecast[i:i+chunk_size]
        await asyncio.sleep(0)  # Allow other tasks to run
```

---

## Caching Strategies

### 1. Redis Cache (Recommended for Production)

**Setup Azure Cache for Redis:**

```bash
az redis create \
  --name macae-cache \
  --resource-group rg-macae-prod \
  --location eastus \
  --sku Basic \
  --vm-size C0
```

**Implement caching:**

```python
import redis.asyncio as redis

redis_client = redis.from_url("redis://macae-cache.redis.cache.windows.net:6380")

async def get_dataset_with_cache(dataset_id: str):
    # Check cache first
    cached = await redis_client.get(f"dataset:{dataset_id}")
    if cached:
        return json.loads(cached)
    
    # Cache miss - fetch from Cosmos DB
    dataset = await cosmos_container.read_item(
        item=dataset_id,
        partition_key=dataset_id
    )
    
    # Store in cache (1 hour TTL)
    await redis_client.setex(
        f"dataset:{dataset_id}",
        3600,
        json.dumps(dataset)
    )
    
    return dataset
```

### 2. In-Memory Caching (Simple Scenarios)

**Use functools.lru_cache:**

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def get_team_config(team_name: str):
    # Expensive operation - fetch and parse team config
    return load_team_config_from_cosmos(team_name)
```

### 3. HTTP Caching Headers

**Set cache headers for static responses:**

```python
from fastapi import Response

@app.get("/api/v3/teams")
async def list_teams(response: Response):
    teams = await get_all_teams()
    
    # Cache for 5 minutes
    response.headers["Cache-Control"] = "public, max-age=300"
    
    return teams
```

---

## Network & CDN

### 1. Azure Front Door

**Setup CDN for global distribution:**

```bash
az afd profile create \
  --profile-name macae-cdn \
  --resource-group rg-macae-prod \
  --sku Premium_AzureFrontDoor

az afd endpoint create \
  --endpoint-name macae-frontend \
  --profile-name macae-cdn \
  --resource-group rg-macae-prod \
  --enabled-state Enabled
```

**Benefits:**
- Global edge caching
- SSL/TLS termination
- DDoS protection
- Web Application Firewall

### 2. Compression

**Enable response compression in frontend:**

```nginx
# Add to App Service configuration
location / {
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;
    gzip_min_length 1000;
}
```

---

## Monitoring & Profiling

### 1. Application Insights Performance Monitoring

**Query slow requests:**

```kusto
requests
| where timestamp > ago(1h)
| where duration > 1000  // Slower than 1 second
| summarize count(), avg(duration), max(duration) by operation_Name
| order by avg_duration desc
```

**Identify expensive dependencies:**

```kusto
dependencies
| where timestamp > ago(1h)
| summarize count(), avg(duration), percentile(duration, 95) by target
| order by avg_duration desc
```

### 2. Python Profiling

**Profile slow endpoints:**

```python
import cProfile
import pstats
import io

def profile_endpoint():
    profiler = cProfile.Profile()
    profiler.enable()
    
    # Run your code
    result = expensive_function()
    
    profiler.disable()
    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s).sort_stats('cumulative')
    ps.print_stats()
    print(s.getvalue())
    
    return result
```

### 3. Load Testing

**Run load tests with Locust:**

```python
# locustfile.py
from locust import HttpUser, task, between

class MacaeUser(HttpUser):
    wait_time = between(1, 3)
    
    @task(3)
    def list_datasets(self):
        self.client.get("/api/v3/datasets")
    
    @task(1)
    def generate_forecast(self):
        self.client.post("/api/v3/forecast", json={
            "dataset_id": "test_dataset",
            "periods": 12
        })

# Run: locust -f locustfile.py --host https://your-backend.azurecontainerapps.io
```

---

## Performance Checklist

### Backend
- [ ] All I/O operations use async/await
- [ ] Connection pooling configured
- [ ] Response compression enabled
- [ ] Pagination implemented for large lists
- [ ] Background tasks used for non-critical operations
- [ ] Appropriate logging level (WARNING/ERROR in prod)

### Database
- [ ] Partition keys optimized for queries
- [ ] Indexing policy tuned (exclude unused paths)
- [ ] Point reads used when possible
- [ ] Autoscale throughput configured
- [ ] Batch operations for bulk inserts

### Azure OpenAI
- [ ] Token usage minimized
- [ ] Prompts cached when possible
- [ ] Appropriate model selected for use case
- [ ] Retry logic with exponential backoff
- [ ] Response streaming for long outputs

### Frontend
- [ ] Code splitting enabled
- [ ] Components memoized
- [ ] Large lists virtualized
- [ ] Images optimized (WebP, lazy loading)
- [ ] Production builds minified

### Caching
- [ ] Redis cache configured (production)
- [ ] Cache TTLs set appropriately
- [ ] Cache invalidation strategy defined
- [ ] HTTP caching headers set

### Monitoring
- [ ] Application Insights dashboards created
- [ ] Performance alerts configured
- [ ] Slow query alerts enabled
- [ ] Load tests executed monthly

---

**Performance Guide Version:** 1.0  
**Last Updated:** October 10, 2025

For questions: performance@yourcompany.com



