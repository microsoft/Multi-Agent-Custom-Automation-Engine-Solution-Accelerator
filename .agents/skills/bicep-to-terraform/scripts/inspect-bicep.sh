#!/usr/bin/env bash
# Recursively inventory a Bicep implementation entrypoint and its local modules.
# Compiles each reachable file independently and emits one JSON manifest. The
# script is read-only and deploys nothing.
#
# Requires: Bash, Azure CLI with Bicep, jq.
# Usage:
#   inspect-bicep.sh [implementation-entrypoint.bicep]
#   inspect-bicep.sh --no-recursive [contract-entrypoint.bicep]
set -euo pipefail

RECURSIVE=true
if [ "${1:-}" = "--no-recursive" ]; then
  RECURSIVE=false
  shift
fi
ENTRY="${1:-infra/main.bicep}"
WORKSPACE="$(pwd -P)"

command -v az >/dev/null 2>&1 || { echo "ERROR: az CLI required" >&2; exit 1; }
command -v jq >/dev/null 2>&1 || { echo "ERROR: jq required" >&2; exit 1; }
[ -f "$ENTRY" ] || { echo "ERROR: entrypoint '$ENTRY' not found" >&2; exit 1; }

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT
FILES_NDJSON="$TMP_DIR/files.ndjson"
EDGES_NDJSON="$TMP_DIR/edges.ndjson"
: > "$FILES_NDJSON"
: > "$EDGES_NDJSON"

absolute_path() {
  local path="$1"
  local directory
  directory="$(dirname "$path")"
  printf '%s/%s\n' "$(cd "$directory" && pwd -P)" "$(basename "$path")"
}

display_path() {
  local path="$1"
  case "$path" in
    "$WORKSPACE"/*) printf '%s\n' "${path#"$WORKSPACE"/}" ;;
    *) printf '%s\n' "$path" ;;
  esac
}

terraform_module_path() {
  local source_path="$1"
  local relative
  if [[ "$source_path" == *"/modules/"* ]]; then
    relative="${source_path#*"/modules/"}"
  else
    relative="$(basename "$source_path")"
  fi
  relative="${relative%.bicep}"
  printf 'infra_tf/modules/%s\n' "$relative"
}

scope_from_arm() {
  jq -r '
    (.["$schema"] // "") as $schema
    | if   ($schema | test("subscriptionDeploymentTemplate"; "i")) then "subscription"
      elif ($schema | test("managementGroupDeploymentTemplate"; "i")) then "managementGroup"
      elif ($schema | test("tenantDeploymentTemplate"; "i")) then "tenant"
      elif ($schema | test("deploymentTemplate"; "i")) then "resourceGroup"
      else "unknown"
      end
  ' "$1"
}

# Emits: line-number<TAB>symbolic-name<TAB>source
module_declarations() {
  local file="$1"
  grep -nE "^[[:space:]]*module[[:space:]]+[A-Za-z_][A-Za-z0-9_]*[[:space:]]+['\"][^'\"]+['\"]" "$file" 2>/dev/null \
    | sed -E "s|^([0-9]+):[[:space:]]*module[[:space:]]+([A-Za-z_][A-Za-z0-9_]*)[[:space:]]+['\"]([^'\"]+)['\"].*|\1\t\2\t\3|" \
    || true
}

ENTRY_ABS="$(absolute_path "$ENTRY")"
QUEUE=("$ENTRY_ABS")
VISITED="|"
INDEX=0

while [ "$INDEX" -lt "${#QUEUE[@]}" ]; do
  FILE="${QUEUE[$INDEX]}"
  INDEX=$((INDEX + 1))

  case "$VISITED" in
    *"|$FILE|"*) continue ;;
  esac
  VISITED="${VISITED}${FILE}|"

  SOURCE_PATH="$(display_path "$FILE")"
  echo "Inspecting $SOURCE_PATH..." >&2
  ARM_FILE="$TMP_DIR/arm-$INDEX.json"
  if ! az bicep build --file "$FILE" --stdout > "$ARM_FILE" 2>"$TMP_DIR/build-$INDEX.log"; then
    echo "ERROR: 'az bicep build --file $SOURCE_PATH' failed:" >&2
    cat "$TMP_DIR/build-$INDEX.log" >&2
    exit 1
  fi

  SCOPE="$(scope_from_arm "$ARM_FILE")"
  PARAMS="$(jq '
    (.parameters // {}) | to_entries | map({
      name: .key,
      type: (.value.type // "unknown"),
      secure: ((.value.type // "") | test("^secure"; "i")),
      nullable: (.value.nullable // false),
      hasDefault: (.value | has("defaultValue")),
      default: (if .value | has("defaultValue") then .value.defaultValue else null end),
      allowed: (.value.allowedValues // []),
      minLength: (.value.minLength // null),
      maxLength: (.value.maxLength // null),
      minValue: (.value.minValue // null),
      maxValue: (.value.maxValue // null),
      description: (.value.metadata.description // null),
      metadata: (.value.metadata // {})
    })
  ' "$ARM_FILE")"

  OUTPUTS="$(jq '
    (.outputs // {}) | to_entries | map({
      name: .key,
      type: (.value.type // "unknown"),
      secure: ((.value.type // "") | test("^secure"; "i")),
      value: (if .value | has("value") then .value.value else null end),
      description: (.value.metadata.description // null),
      metadata: (.value.metadata // {})
    })
  ' "$ARM_FILE")"

  RESOURCES="$(jq '
    [(.resources // [])[] | {
      symbolicName: (.symbolicName // null),
      name: (.name // null),
      type: (.type // "unknown"),
      apiVersion: (.apiVersion // null),
      condition: (.condition // null),
      copy: (.copy // null),
      dependsOn: (.dependsOn // [])
    }]
  ' "$ARM_FILE")"

  RESOURCE_TYPES="$(printf '%s' "$RESOURCES" | jq '[.[].type] | unique')"

  # Source variables are recorded as navigation aids. Complex multiline
  # expressions still require reading the source file during conversion.
  VARIABLES="$(
    sed -nE 's/^[[:space:]]*var[[:space:]]+([A-Za-z_][A-Za-z0-9_]*)[[:space:]]*=[[:space:]]*(.*)$/\1\t\2/p' "$FILE" \
      | jq -R -s '
          split("\n")
          | map(select(length > 0) | split("\t") | {
              name: .[0],
              firstLineExpression: (.[1:] | join("\t"))
            })
        '
  )"

  MODULES_FILE="$TMP_DIR/modules-$INDEX.ndjson"
  : > "$MODULES_FILE"
  while IFS=$'\t' read -r LINE MODULE_ID MODULE_SOURCE; do
    [ -n "${MODULE_ID:-}" ] || continue

    IS_LOCAL=true
    RESOLVED_SOURCE=null
    TF_PATH=null
    case "$MODULE_SOURCE" in
      br:*|br/*|ts:*|ts/*|templateSpec:*)
        IS_LOCAL=false
        ;;
      *)
        CANDIDATE="$(absolute_path "$(dirname "$FILE")/$MODULE_SOURCE")"
        [ -f "$CANDIDATE" ] || {
          echo "ERROR: local module '$MODULE_SOURCE' referenced by '$SOURCE_PATH' was not found" >&2
          exit 1
        }
        RESOLVED_SOURCE="$(display_path "$CANDIDATE")"
        TF_PATH="$(terraform_module_path "$RESOLVED_SOURCE")"
        if [ "$RECURSIVE" = true ]; then
          QUEUE+=("$CANDIDATE")
        fi
        ;;
    esac

    jq -nc \
      --arg id "$MODULE_ID" \
      --arg source "$MODULE_SOURCE" \
      --argjson line "$LINE" \
      --argjson local "$IS_LOCAL" \
      --arg resolved_source "$RESOLVED_SOURCE" \
      --arg terraform_path "$TF_PATH" \
      '{
        id: $id,
        source: $source,
        sourceLine: $line,
        local: $local,
        resolvedSource: (if $resolved_source == "null" then null else $resolved_source end),
        terraformModulePath: (if $terraform_path == "null" then null else $terraform_path end)
      }' >> "$MODULES_FILE"

    if [ "$IS_LOCAL" = true ]; then
      jq -nc \
        --arg parent "$SOURCE_PATH" \
        --arg id "$MODULE_ID" \
        --arg child "$RESOLVED_SOURCE" \
        --arg terraform_path "$TF_PATH" \
        '{parent: $parent, id: $id, child: $child, terraformModulePath: $terraform_path}' \
        >> "$EDGES_NDJSON"
    fi
  done < <(module_declarations "$FILE")
  MODULES_JSON="$TMP_DIR/modules-array-$INDEX.json"
  jq -s '.' "$MODULES_FILE" > "$MODULES_JSON"

  IS_ENTRYPOINT=false
  TF_MODULE_PATH=null
  if [ "$FILE" = "$ENTRY_ABS" ]; then
    IS_ENTRYPOINT=true
  else
    TF_MODULE_PATH="$(terraform_module_path "$SOURCE_PATH")"
  fi

  PROVIDER_HINTS_JSON="$TMP_DIR/provider-hints-$INDEX.json"
  printf '%s' "$RESOURCES" | jq '
    [
      .[]
      | select(.type != "Microsoft.Resources/deployments")
      | if ((.apiVersion // "") | test("preview"; "i"))
        then "azapi_candidate"
        else "azurerm_or_azapi"
        end
    ] | unique
  ' > "$PROVIDER_HINTS_JSON"

  PARAMS_JSON="$TMP_DIR/parameters-$INDEX.json"
  VARIABLES_JSON="$TMP_DIR/variables-$INDEX.json"
  RESOURCES_JSON="$TMP_DIR/resources-$INDEX.json"
  RESOURCE_TYPES_JSON="$TMP_DIR/resource-types-$INDEX.json"
  OUTPUTS_JSON="$TMP_DIR/outputs-$INDEX.json"
  printf '%s' "$PARAMS" > "$PARAMS_JSON"
  printf '%s' "$VARIABLES" > "$VARIABLES_JSON"
  printf '%s' "$RESOURCES" > "$RESOURCES_JSON"
  printf '%s' "$RESOURCE_TYPES" > "$RESOURCE_TYPES_JSON"
  printf '%s' "$OUTPUTS" > "$OUTPUTS_JSON"

  jq -nc \
    --arg source "$SOURCE_PATH" \
    --arg scope "$SCOPE" \
    --argjson entrypoint "$IS_ENTRYPOINT" \
    --arg terraform_path "$TF_MODULE_PATH" \
    --slurpfile parameters "$PARAMS_JSON" \
    --slurpfile variables "$VARIABLES_JSON" \
    --slurpfile resources "$RESOURCES_JSON" \
    --slurpfile resource_types "$RESOURCE_TYPES_JSON" \
    --slurpfile modules "$MODULES_JSON" \
    --slurpfile outputs "$OUTPUTS_JSON" \
    --slurpfile provider_hints "$PROVIDER_HINTS_JSON" \
    '{
      source: $source,
      entrypoint: $entrypoint,
      terraformModulePath: (if $terraform_path == "null" then null else $terraform_path end),
      scope: $scope,
      counts: {
        parameters: ($parameters[0] | length),
        variables: ($variables[0] | length),
        resources: ($resources[0] | length),
        modules: ($modules[0] | length),
        outputs: ($outputs[0] | length)
      },
      parameters: $parameters[0],
      variables: $variables[0],
      resources: $resources[0],
      resourceTypes: $resource_types[0],
      modules: $modules[0],
      outputs: $outputs[0],
      providerHints: $provider_hints[0]
    }' >> "$FILES_NDJSON"
done

PATH_COLLISIONS="$(jq -s '
  [
    map(select(.entrypoint | not))
    | sort_by(.terraformModulePath)
    | group_by(.terraformModulePath)[]
    | select(length > 1)
    | {
        terraformModulePath: .[0].terraformModulePath,
        sources: map(.source)
      }
  ]
' "$FILES_NDJSON")"
if [ "$(printf '%s' "$PATH_COLLISIONS" | jq 'length')" -ne 0 ]; then
  echo "ERROR: multiple Bicep files map to the same Terraform module path:" >&2
  printf '%s\n' "$PATH_COLLISIONS" | jq . >&2
  exit 1
fi

jq -s \
  --arg entrypoint "$(display_path "$ENTRY_ABS")" \
  --slurpfile edges "$EDGES_NDJSON" \
  '{
    schemaVersion: 2,
    implementationEntrypoint: $entrypoint,
    scope: (map(select(.entrypoint))[0].scope),
    counts: {
      files: length,
      childModules: (map(select(.entrypoint | not)) | length),
      parameters: (map(.counts.parameters) | add // 0),
      variables: (map(.counts.variables) | add // 0),
      resources: (map(.counts.resources) | add // 0),
      outputs: (map(.counts.outputs) | add // 0)
    },
    resourceTypes: ([.[].resourceTypes[]] | unique),
    moduleEdges: $edges,
    files: .
  }' "$FILES_NDJSON"
