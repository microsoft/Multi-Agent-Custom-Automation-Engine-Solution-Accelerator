# Skeleton child module. One per Bicep module. Replace with the ported resources.
#
# main.tf     — the resources this module creates (from the matching *.bicep module)
# variables.tf — one variable per input the Bicep module declared (snake_case)
# outputs.tf   — one output per value the Bicep module returned (snake_case)
#
# Wire from the root exactly as the Bicep root wired the module:
#   module "<name>" {
#     source = "./modules/<name>"
#     <input> = <root expression>
#   }
