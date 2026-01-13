
# 🌐 Grounding with Bing Search — Quick Setup

This guide walks you through setting up Grounding with Bing Search and connecting it to your Azure AI Foundry project. This tool enables your AI agents to retrieve real-time public web data, enhancing responses with up-to-date information.

---

## ✅ Prerequisites

- An active **Azure subscription**  
- **Azure CLI** installed and logged in (`az login`)  
- A **resource group** created  
- Register the Bing provider (one-time setup):  

  ```bash
  az provider register --namespace Microsoft.Bing

⚠️ **Important:**
Bing Search Grounding only supports **API key authentication**.
Ensure your **Azure AI Foundry account has Local Authentication enabled**.
If local auth is disabled, you will not be able to connect Bing Search.

---

## 🚀 Step 1: Create a Bing Search Grounding Resource

### Option A — Azure Portal

1. In the [Azure Portal](https://portal.azure.com), search for **Bing Search (Grounding)**.
2. Click **Create**.
3. Select your **Subscription** and **Resource Group**.
4. Enter a **Resource Name** and choose a **Pricing Tier (SKU)**.
5. At the bottom of the form, tick the required checkbox:
   ✅ *“I confirm I have read and understood the notice above.”*
   (You cannot proceed without this.)
6. Click **Review + Create** → **Create**.

---

### Option B — Azure CLI

Set your variables (replace with your own values):

```bash
RESOURCE_GROUP="<your-resource-group>"
ACCOUNT_NAME="<unique-bing-resource-name>"
LOCATION="global"   # must be 'global'
SKU="G1"
KIND="Bing.Grounding"

SUBSCRIPTION_ID=$(az account show --query id --output tsv)
RESOURCE_ID="/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/microsoft.bing/accounts/$ACCOUNT_NAME"
```

Create the resource:

```bash
az rest --method put \
  --url "https://management.azure.com$RESOURCE_ID?api-version=2020-06-10" \
  --body '{
    "location": "'$LOCATION'",
    "kind": "'$KIND'",
    "sku": { "name": "'$SKU'" },
    "properties": {}
  }'
```

Verify creation:

```bash
az resource show --ids "$RESOURCE_ID" --api-version 2020-06-10 -o table
```

---

## 🔗 Step 2: Connect Bing Search to Azure AI Foundry

1. Open your **Azure AI Foundry project** in the [AI Studio portal](https://ai.azure.com).
2. Go to **Management center** → **Connected resources**.
3. Click **+ Add connection**.
4. Select **Grounding with Bing Search**.
5. Choose the Bing resource you created and click **Create**.

---

## 💡 Why Use Bing Search Grounding?

* Provides **real-time information** to enrich AI responses.
* Helps LLMs give answers with **up-to-date knowledge** beyond training data.
* Useful for scenarios like **news, research, or dynamic queries**.

---

## 📚 Additional Resources

* [Grounding with Bing Search (overview)](https://learn.microsoft.com/en-us/azure/ai-foundry/agents/how-to/tools/bing-grounding) — Learn how the tool works, pricing, privacy notes, and how real-time search is integrated. ([Microsoft Learn][1])
* [Grounding with Bing Search code samples](https://learn.microsoft.com/en-us/azure/ai-foundry/agents/how-to/tools/bing-code-samples?source=recommendations&pivots=portal) — SDK and REST examples for using Bing grounding. ([Microsoft Learn][2])

---