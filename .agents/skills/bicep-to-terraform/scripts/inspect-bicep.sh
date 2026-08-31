#!/usr/bin/env bash
# ============================================================================
# inspect-bicep.sh — read-only discovery of a Bicep entrypoint for a 1:1
# Terraform port. Compiles the entrypoint to ARM JSON (reliable structure) and
# emits a single JSON object (bicep-facts.json). Makes NO changes to the repo
# and deploys nothing.
#
# What it reports:
#   scope           deployment scope (resourceGroup | subscription | ...)
#   parameters[]    name, type, hasDefault, default, allowed[]
#   outputs[]       name (THE CONTRACT — none may be dropped), type, arm_value
#   resource_types[] every distinct Microsoft.* type in the compiled tree
#   modules[]       direct module references in THIS entrypoint (id + source path)
#
# Run it on the router (infra/main.bicep) for the full picture, then again on
# the chosen flavor's entrypoint (e.g. infra/bicep/main.bicep) to scope the
# resource inventory and module tree to that flavor.
#
# Portable Bash (macOS Bash 3.2 + Windows Git Bash/WSL). Requires: az, jq.
# Usage: inspect-bicep.sh [entrypoint.bicep] > .agent/tmp/bicep-facts.json
# ============================================================================
set -euo pipefail

ENTRY="${1:-infra/main.bicep}"

command -v az >/dev/null 2>&1 || { echo "ERROR: az CLI required" >&2; exit 1; }
command -v jq >/dev/null 2>&1 || { echo "ERROR: jq required" >&2; exit 1; }
[ -f "$ENTRY" ] || { echo "ERROR: entrypoint '$ENTRY' not found" >&2; exit 1; }

# --- Compile to ARM JSON (structure is reliable; values are ARM expressions) --
ARM="$(az bicep build --file "$ENTRY" --stdout 2>/dev/null)" || {
  echo "ERROR: 'az bicep build --file $ENTRY' failed. Fix the Bicep or check the az bicep install." >&2
  exit 1
}

# --- Scope from the template $schema ----------------------------------------
SCOPE="$(printf '%s' "$ARM" | jq -r '
  (.["$schema"] // "") as $s
  | if   ($s | test("subscriptionDeploymentTemplate";  "i")) then "subscription"
    elif ($s | test("managementGroupDeploymentTemplate";"i")) then "managementGroup"
    elif ($s | test("tenantDeploymentTemplate";        "i")) then "tenant"
    elif ($s | test("deploymentTemplate";              "i")) then "resourceGroup"
    else "unknown" end')"

# --- Parameters, outputs, resource types (recursive over nested templates) ---
PARAMS="$(printf '%s' "$ARM" | jq '
  (.parameters // {}) | to_entries | map({
    name: .key,
    type: (.value.type // "unknown"),
    hasDefault: (.value | has("defaultValue")),
    default: (.value.defaultValue // null),
    allowed: (.value.allowedValues // [])
  })')"

OUTPUTS="$(printf '%s' "$ARM" | jq '
  (.outputs // {}) | to_entries | map({
    name: .key,
    type: (.value.type // "unknown"),
    arm_value: (.value.value // null)
  })')"

# Walk the whole compiled document (including nested deployment templates) and
# collect every object that looks like a resource (has both type + apiVersion).
RESOURCE_TYPES="$(printf '%s' "$ARM" | jq '
  [ .. | objects | select(has("type") and has("apiVersion")) | .type ]
  | unique')"

# --- Direct module references, parsed from the Bicep source of THIS file -----
# Matches:  module <id> '<path>' = {   (single-line form used by these repos)
MODULES="$(grep -nE "^[[:space:]]*module[[:space:]]+[A-Za-z_][A-Za-z0-9_]*[[:space:]]+'[^']+'" "$ENTRY" 2>/dev/null \
  | sed -E "s/^[0-9]+:[[:space:]]*module[[:space:]]+([A-Za-z_][A-Za-z0-9_]*)[[:space:]]+'([^']+)'.*/\1\t\2/" \
  | jq -R -s 'split("\n") | map(select(length>0) | split("\t") | {id: .[0], source: .[1]})')"
[ -n "$MODULES" ] || MODULES="[]"

# --- Assemble facts.json -----------------------------------------------------
jq -n \
  --arg entrypoint "$ENTRY" \
  --arg scope "$SCOPE" \
  --argjson parameters "$PARAMS" \
  --argjson outputs "$OUTPUTS" \
  --argjson resource_types "$RESOURCE_TYPES" \
  --argjson modules "$MODULES" \
  '{
    entrypoint: $entrypoint,
    scope: $scope,
    counts: {
      parameters: ($parameters | length),
      outputs: ($outputs | length),
      resource_types: ($resource_types | length),
      modules: ($modules | length)
    },
    parameters: $parameters,
    outputs: $outputs,
    resource_types: $resource_types,
    modules: $modules
  }'
