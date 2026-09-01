terraform {
  required_version = ">= 1.6.0"

  required_providers {
    // Declare every provider referenced by this module and remove unused
    // entries. Provider authentication/configuration remains in the root.
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }

    // azapi = {
    //   source  = "Azure/azapi"
    //   version = "~> 2.0"
    // }

    // random = {
    //   source  = "hashicorp/random"
    //   version = "~> 3.6"
    // }
  }
}
