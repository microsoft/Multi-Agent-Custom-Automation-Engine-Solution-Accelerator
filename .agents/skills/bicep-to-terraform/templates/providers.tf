terraform {
  required_version = ">= 1.6.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
    # Uncomment only if the source uses the corresponding constructs:
    # azapi = {                          # preview Microsoft.* resource types (e.g. AI Foundry)
    #   source  = "Azure/azapi"
    #   version = "~> 2.0"
    # }
    # random = {                         # replacement for Bicep uniqueString()
    #   source  = "hashicorp/random"
    #   version = "~> 3.6"
    # }
  }

  # Partial backend: init values (resource_group_name / storage_account_name /
  # container_name / key) are supplied by the CI/CD pipeline via
  # `terraform init -backend-config=backend.ci.hcl` from vars.TF_BACKEND_*.
  # Never commit those values here.
  backend "azurerm" {
    use_oidc         = true
    use_azuread_auth = true
  }
}

data "azurerm_client_config" "current" {}

provider "azurerm" {
  subscription_id = var.subscription_id

  features {}

  # Required where the tenant disables shared-key access on storage accounts.
  storage_use_azuread = true
}
