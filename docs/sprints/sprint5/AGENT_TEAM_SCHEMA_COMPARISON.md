# Agent Team Schema Comparison

**Date**: October 10, 2025  
**Finding**: Built-in agent teams use older schema; Sprint 3+ teams use complete schema

---

## 📊 Schema Comparison

### Built-In Teams (HR, Marketing, Retail)

**Agent Fields Present:**
```json
{
  "input_key": "",
  "type": "",
  "name": "AgentName",
  "deployment_name": "gpt-4.1-mini",
  "icon": "",
  "system_message": "...",
  "description": "...",
  "use_rag": false,
  "use_mcp": true,
  "use_bing": false,
  "use_reasoning": false,
  "index_name": "",
  "index_endpoint": "",      ← Has this
  "coding_tools": false
}
```

**Missing Field:**
- ❌ `index_foundry_name` - Not present in built-in teams

### Sprint 3+ Teams (Customer Intelligence, Retail Operations, etc.)

**Agent Fields Present:**
```json
{
  "input_key": "",
  "type": "",
  "name": "AgentName",
  "deployment_name": "gpt-4.1-mini",
  "icon": "",
  "system_message": "...",
  "description": "...",
  "use_rag": false,
  "use_mcp": true,
  "use_bing": false,
  "use_reasoning": false,
  "index_name": "",
  "index_foundry_name": "",  ← Has this
  "index_endpoint": "",      ← Has this
  "coding_tools": false
}
```

**Complete Schema:**
- ✅ All fields present
- ✅ Matches latest platform expectations
- ✅ Forward compatible

---

## 🤔 Why The Difference?

### Root Cause
The built-in agent teams (HR, Marketing, Retail, Finance Forecasting) were created with an **earlier version of the platform schema** that didn't include the `index_foundry_name` field.

### When Was This Added?
The `index_foundry_name` field was added to support **Azure AI Foundry index naming conventions**, which differ from the direct `index_endpoint` approach.

**Use Cases:**
- `index_endpoint` - Direct URL to Azure AI Search index
- `index_foundry_name` - Logical name within Azure AI Foundry project
- Both fields allow flexibility in how agents connect to search indexes

---

## ✅ Current Status

### Built-In Teams (4 teams)
| Team | Schema Version | Missing Fields |
|------|----------------|----------------|
| HR (team-1) | v1 (older) | `index_foundry_name` |
| Product Marketing (team-2) | v1 (older) | `index_foundry_name` |
| Retail (team-3) | v1 (older) | `index_foundry_name` |
| Financial Forecasting (team-forecasting) | v1 (older) | `index_foundry_name` |

### Sprint 3+ Teams (4 teams)
| Team | Schema Version | Missing Fields |
|------|----------------|----------------|
| Customer Intelligence (team-customer-intelligence) | v2 (current) | None ✅ |
| Retail Operations (team-retail-operations) | v2 (current) | None ✅ |
| Revenue Optimization (team-revenue-optimization) | v2 (current) | None ✅ |
| Marketing Intelligence (team-marketing-intelligence) | v2 (current) | None ✅ |

---

## 🔧 Should We Update Built-In Teams?

### Option 1: Leave As-Is ✅ RECOMMENDED

**Pros:**
- Built-in teams work correctly
- No risk of breaking existing functionality
- `index_foundry_name` not required if not using Foundry indexes
- Minimal disruption

**Cons:**
- Schema inconsistency across teams
- May confuse developers

**Recommendation:** ✅ **Leave built-in teams unchanged**
- They work fine without `index_foundry_name`
- Field is optional, not required
- Updating could introduce regression bugs

### Option 2: Add Missing Field

**Pros:**
- Schema consistency across all teams
- Future-proof
- Better developer experience

**Cons:**
- Risk of breaking existing deployments
- Requires testing all built-in team workflows
- May need to update backend parsing logic

**Implementation:**
```json
// Add to each agent in built-in teams
{
  "index_foundry_name": "",  // Empty string (not used)
}
```

---

## 🎯 Recommendation

### Keep Current State ✅

**Reasoning:**
1. **Backward Compatibility**: Built-in teams are production-tested and stable
2. **Optional Field**: `index_foundry_name` is not required by the platform
3. **No Functional Impact**: Agents work correctly without it
4. **Sprint 3+ Correct**: New teams use complete schema going forward

### Best Practice Going Forward

**For New Agent Teams:**
- ✅ Always include both `index_endpoint` and `index_foundry_name`
- ✅ Use complete v2 schema as shown in Sprint 3+ teams
- ✅ Copy from `customer_intelligence.json` as template

**For Existing Teams:**
- ⚠️ Leave built-in teams unchanged unless platform explicitly requires update
- ✅ Document schema version in team config comments if needed
- ✅ Test thoroughly if updating

---

## 📝 Field Definitions

### index_endpoint
**Purpose**: Direct URL to Azure AI Search index  
**Format**: `https://your-search.search.windows.net/indexes/your-index`  
**Required**: Only if `use_rag: true`  
**Example Use**: Direct connection to Azure Cognitive Search

### index_foundry_name
**Purpose**: Logical name of index within Azure AI Foundry project  
**Format**: `"my-index-name"` (string identifier)  
**Required**: Only if using Azure AI Foundry index management  
**Example Use**: Foundry-managed search indexes

### Relationship
- **Mutually Exclusive**: Use one or the other, not both
- **Platform Decides**: Backend determines which to use based on configuration
- **Empty Values**: Empty string `""` means field not used

---

## 🧪 Compatibility Test

### Test Case: Built-In Team Without index_foundry_name

```json
// HR Team Agent (works correctly)
{
  "name": "HRHelperAgent",
  "use_rag": false,
  "index_name": "",
  "index_endpoint": "",
  // ❌ index_foundry_name not present
  "coding_tools": false
}
```

**Result**: ✅ Works correctly
- Agent loads without errors
- MCP tools accessible
- No RAG features used (use_rag: false)
- Empty index fields ignored

### Test Case: Sprint 3 Team With index_foundry_name

```json
// Customer Intelligence Agent (works correctly)
{
  "name": "ChurnPredictionAgent",
  "use_rag": false,
  "index_name": "",
  "index_foundry_name": "",  // ✅ Present but empty
  "index_endpoint": "",
  "coding_tools": false
}
```

**Result**: ✅ Works correctly
- Agent loads without errors
- MCP tools accessible
- Extra field harmlessly ignored
- Forward compatible

---

## 📊 Platform Parsing Logic

### How Backend Handles Schema Differences

```python
# Simplified backend logic
def create_agent_from_config(agent_obj):
    # Get optional fields with defaults
    index_name = getattr(agent_obj, 'index_name', '')
    index_endpoint = getattr(agent_obj, 'index_endpoint', '')
    index_foundry_name = getattr(agent_obj, 'index_foundry_name', '')  # Safe
    
    # Determine search config
    if agent_obj.use_rag:
        if index_foundry_name:
            # Use Foundry index
            search_config = SearchConfig.from_foundry(index_foundry_name)
        elif index_endpoint:
            # Use direct endpoint
            search_config = SearchConfig.from_endpoint(index_endpoint)
    else:
        search_config = None  # No RAG
    
    return create_agent(search_config=search_config)
```

**Key Points:**
- `getattr()` with default handles missing fields gracefully
- Missing `index_foundry_name` defaults to empty string
- Empty fields are safely ignored
- Both schemas work correctly

---

## 🎯 Summary

### Current State
- ✅ Built-in teams: v1 schema (working correctly)
- ✅ Sprint 3+ teams: v2 schema (working correctly)
- ✅ Both schemas compatible with platform
- ✅ No breaking changes needed

### Why Built-In Teams Have Fewer Fields
- Created with earlier platform version
- `index_foundry_name` added later for Foundry support
- Backward compatibility maintained
- Optional field, safe to omit

### Recommended Action
**✅ NO ACTION REQUIRED**
- Leave built-in teams as-is
- Use complete v2 schema for new teams
- Document schema versions for reference
- Platform handles both versions gracefully

### For Future Development
- **Template**: Use Sprint 3 teams as reference
- **Fields**: Include all fields from v2 schema
- **Testing**: Test with both schema versions
- **Documentation**: Note schema version in team description

