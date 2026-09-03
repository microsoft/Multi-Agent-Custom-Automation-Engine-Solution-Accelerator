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
PARAMETER_FILES_NDJSON="$TMP_DIR/parameter-files.ndjson"
: > "$FILES_NDJSON"
: > "$EDGES_NDJSON"
: > "$PARAMETER_FILES_NDJSON"

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

# Emits: line-number<TAB>symbolic-name<TAB>type@apiVersion
#
# `existing` resources are compile-time lookups: Bicep resolves them into
# reference()/resourceId() expressions and emits NOTHING into the ARM
# `resources` collection. They are therefore invisible to every ARM-based
# query below, yet each one must become a Terraform `data` source. Like module
# paths, this information survives only in the Bicep source text.
existing_declarations() {
  local file="$1"
  grep -nE "^[[:space:]]*resource[[:space:]]+[A-Za-z_][A-Za-z0-9_]*[[:space:]]+['\"][^'\"]+['\"][[:space:]]+existing([[:space:]]|=)" "$file" 2>/dev/null \
    | sed -E "s|^([0-9]+):[[:space:]]*resource[[:space:]]+([A-Za-z_][A-Za-z0-9_]*)[[:space:]]+['\"]([^'\"]+)['\"][[:space:]]+existing.*|\1\t\2\t\3|" \
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

  # Symbolic names of *local* module calls. Bicep inlines every module — local
  # and registry alike — into the compiled ARM as a nested
  # Microsoft.Resources/deployments resource carrying the full child template.
  #
  # Local modules are visited independently by this BFS, so expanding their
  # inlined templates here would double-count their resources. Registry modules
  # (br:/ts:) are never visited, so expanding theirs is the only way to see what
  # they create -- without it an AVM wrapper reports zero resources.
  LOCAL_MODULE_IDS_JSON="$TMP_DIR/local-module-ids-$INDEX.json"
  jq '[.[] | select(.local) | .id]' "$MODULES_JSON" > "$LOCAL_MODULE_IDS_JSON"

  # ARM emits `resources` in two shapes:
  #   * languageVersion 2.0 -> an OBJECT keyed by symbolic name
  #   * otherwise           -> an ARRAY
  # In the object form the symbolic name is the key, not a field, so it must be
  # re-attached; dependsOn refers to resources *by* that name, and dropping it
  # severs the whole dependency graph.
  RESOURCES_JSON="$TMP_DIR/resources-$INDEX.json"
  jq --slurpfile local_ids "$LOCAL_MODULE_IDS_JSON" '
    def normalize:
      if   type == "object" then (to_entries | map(.value + {symbolicName: .key}))
      elif type == "array"  then .
      else [] end;

    def expand($local; $via):
      normalize
      | map(
          . as $r
          | if ($r.type == "Microsoft.Resources/deployments")
            then (
              if (($r.symbolicName // null) == null)
                 or (($via | length) == 0 and ($local | index($r.symbolicName)))
              then []
              else (($r.properties.template.resources // {})
                    | expand($local; $via + [$r.symbolicName]))
              end
            )
            else [ $r + {viaModules: $via} ]
            end
        )
      | flatten(1);

    ($local_ids[0] // []) as $local
    | ((.resources // []) | expand($local; []))
    | map({
        symbolicName: (.symbolicName // null),
        name: (.name // null),
        type: (.type // "unknown"),
        apiVersion: (.apiVersion // null),
        condition: (.condition // null),
        copy: (.copy // null),
        dependsOn: (.dependsOn // []),
        nested: (((.viaModules // []) | length) > 0),
        viaModules: (.viaModules // [])
      })
  ' "$ARM_FILE" > "$RESOURCES_JSON"

  RESOURCE_TYPES_JSON="$TMP_DIR/resource-types-$INDEX.json"
  jq '[.[].type] | unique' "$RESOURCES_JSON" > "$RESOURCE_TYPES_JSON"

  # `existing` resources -- recovered from source, since ARM discards them.
  EXISTING_NDJSON="$TMP_DIR/existing-$INDEX.ndjson"
  EXISTING_JSON="$TMP_DIR/existing-$INDEX.json"
  : > "$EXISTING_NDJSON"
  while IFS=$'\t' read -r EX_LINE EX_SYM EX_TYPEREF; do
    [ -n "${EX_SYM:-}" ] || continue
    EX_TYPE="${EX_TYPEREF%@*}"
    EX_API="${EX_TYPEREF##*@}"
    [ "$EX_API" = "$EX_TYPEREF" ] && EX_API=""
    jq -nc \
      --arg symbolic_name "$EX_SYM" \
      --arg type "$EX_TYPE" \
      --arg api_version "$EX_API" \
      --argjson line "$EX_LINE" \
      '{
        symbolicName: $symbolic_name,
        type: $type,
        apiVersion: (if $api_version == "" then null else $api_version end),
        sourceLine: $line
      }' >> "$EXISTING_NDJSON"
  done < <(existing_declarations "$FILE")
  jq -s '.' "$EXISTING_NDJSON" > "$EXISTING_JSON"

  EXISTING_TYPES_JSON="$TMP_DIR/existing-types-$INDEX.json"
  jq '[.[].type] | unique' "$EXISTING_JSON" > "$EXISTING_TYPES_JSON"

  # Variables come from the compiled ARM, where they are fully resolved.
  # Reading them from source text truncates every multi-line object to "{".
  # ARM does inline single-use variables, so source-declared names that the
  # compiler optimised away are merged back in (flagged, value unavailable) --
  # they are usually naming expressions worth reproducing as Terraform locals.
  SOURCE_VARS_JSON="$TMP_DIR/source-vars-$INDEX.json"
  sed -nE 's/^[[:space:]]*var[[:space:]]+([A-Za-z_][A-Za-z0-9_]*)[[:space:]]*=.*$/\1/p' "$FILE" \
    | jq -R -s 'split("\n") | map(select(length > 0))' > "$SOURCE_VARS_JSON"

  VARIABLES_JSON="$TMP_DIR/variables-$INDEX.json"
  jq --slurpfile source_vars "$SOURCE_VARS_JSON" '
    ($source_vars[0] // []) as $declared
    | (
        (.variables // {})
        | to_entries
        | map({
            name: .key,
            generated: (.key | startswith("$fxv")),
            inlinedByArm: false,
            value: .value
          })
      ) as $arm
    | ($arm | map(.name)) as $arm_names
    | $arm + (
        $declared
        | map(select(. as $n | ($arm_names | index($n)) == null))
        | map({name: ., generated: false, inlinedByArm: true, value: null})
      )
  ' "$ARM_FILE" > "$VARIABLES_JSON"

  IS_ENTRYPOINT=false
  TF_MODULE_PATH=null
  if [ "$FILE" = "$ENTRY_ABS" ]; then
    IS_ENTRYPOINT=true
  else
    TF_MODULE_PATH="$(terraform_module_path "$SOURCE_PATH")"
  fi

  # Per-resource-type verdicts. The previous heuristic asked only "does the
  # api-version contain the word 'preview'", which is unrelated to whether
  # azurerm covers the type -- on a GA-dated tree it never fires, collapsing to
  # a single useless constant while missing the types that genuinely require
  # azapi (e.g. CognitiveServices .../projects, which is GA-dated 2025-12-01).
  PROVIDER_HINTS_JSON="$TMP_DIR/provider-hints-$INDEX.json"
  jq '
    [
      "Microsoft.CognitiveServices/accounts/projects",
      "Microsoft.CognitiveServices/accounts/projects/connections",
      "Microsoft.CognitiveServices/accounts/connections",
      "Microsoft.Resources/tags",
      "Microsoft.Web/sites/basicPublishingCredentialsPolicies"
    ] as $azapi_required
    | [ .[] | {type: .type, apiVersion: .apiVersion} ]
    | unique
    | map(
        .type as $type
        | .apiVersion as $api
        | . + (
          if ($azapi_required | index($type)) then
            {hint: "azapi_required",
             reason: "no stable azurerm resource for this ARM type"}
          elif (($api // "") | test("preview"; "i")) then
            {hint: "azapi_candidate_preview",
             reason: "preview api-version; confirm azurerm coverage before mapping"}
          else
            {hint: "azurerm_expected",
             reason: "expected to map to an azurerm resource"}
          end
        )
      )
  ' "$RESOURCES_JSON" > "$PROVIDER_HINTS_JSON"

  PARAMS_JSON="$TMP_DIR/parameters-$INDEX.json"
  OUTPUTS_JSON="$TMP_DIR/outputs-$INDEX.json"
  printf '%s' "$PARAMS" > "$PARAMS_JSON"
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
    --slurpfile existing_resources "$EXISTING_JSON" \
    --slurpfile existing_resource_types "$EXISTING_TYPES_JSON" \
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
        existingResources: ($existing_resources[0] | length),
        modules: ($modules[0] | length),
        outputs: ($outputs[0] | length)
      },
      parameters: $parameters[0],
      variables: $variables[0],
      resources: $resources[0],
      resourceTypes: $resource_types[0],
      existingResources: $existing_resources[0],
      existingResourceTypes: $existing_resource_types[0],
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

ENTRY_DIR="$(dirname "$ENTRY_ABS")"
for PARAMETER_FILE in "$ENTRY_DIR"/*.parameters.json "$ENTRY_DIR"/params/*.bicepparam; do
  [ -f "$PARAMETER_FILE" ] || continue
  PARAMETER_SOURCE="$(display_path "$PARAMETER_FILE")"

  case "$PARAMETER_FILE" in
    *.parameters.json)
      if ! jq -e '.parameters | type == "object"' "$PARAMETER_FILE" >/dev/null 2>&1; then
        echo "ERROR: ARM parameter file '$PARAMETER_SOURCE' has no parameters object" >&2
        exit 1
      fi
      jq -c \
        --arg source "$PARAMETER_SOURCE" \
        '{
          source: $source,
          format: "arm-parameters-json",
          parameters: [
            .parameters
            | to_entries[]
            | {
                name: .key,
                value: (if .value | has("value") then .value.value else null end),
                isEnvironmentExpression: (
                  (.value.value | type) == "string"
                  and (.value.value | test("^\\$\\{[A-Za-z_][A-Za-z0-9_]*(=[^}]*)?\\}$"))
                )
              }
          ]
        }' "$PARAMETER_FILE" >> "$PARAMETER_FILES_NDJSON"
      ;;
    *.bicepparam)
      jq -nc \
        --arg source "$PARAMETER_SOURCE" \
        '{source: $source, format: "bicepparam", parameters: []}' \
        >> "$PARAMETER_FILES_NDJSON"
      ;;
  esac
done

jq -s \
  --arg entrypoint "$(display_path "$ENTRY_ABS")" \
  --slurpfile edges "$EDGES_NDJSON" \
  --slurpfile parameter_files "$PARAMETER_FILES_NDJSON" \
  '{
    schemaVersion: 3,
    implementationEntrypoint: $entrypoint,
    scope: (map(select(.entrypoint))[0].scope),
    counts: {
      files: length,
      childModules: (map(select(.entrypoint | not)) | length),
      parameters: (map(.counts.parameters) | add // 0),
      variables: (map(.counts.variables) | add // 0),
      resources: (map(.counts.resources) | add // 0),
      existingResources: (map(.counts.existingResources) | add // 0),
      outputs: (map(.counts.outputs) | add // 0)
    },
    resourceTypes: ([.[].resourceTypes[]] | unique),
    existingResourceTypes: ([.[].existingResourceTypes[]] | unique),
    azapiRequiredTypes: (
      [.[].providerHints[] | select(.hint != "azurerm_expected")] | unique
    ),
    moduleEdges: $edges,
    parameterFiles: $parameter_files,
    files: .
  }' "$FILES_NDJSON"
