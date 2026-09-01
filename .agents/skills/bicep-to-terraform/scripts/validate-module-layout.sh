#!/usr/bin/env bash
# Validate generated Terraform module parity against inspect-bicep.sh schema v2.
# This is a structural check; run terraform validate afterward for HCL/provider
# validation.
#
# Usage:
#   validate-module-layout.sh <implementation-facts.json> [terraform-root] [contract-facts.json]
set -euo pipefail

FACTS="${1:-.agent/tmp/bicep-facts.json}"
TF_ROOT="${2:-infra_tf}"
CONTRACT_FACTS="${3:-$FACTS}"

command -v jq >/dev/null 2>&1 || { echo "ERROR: jq required" >&2; exit 1; }
[ -f "$FACTS" ] || { echo "ERROR: facts file '$FACTS' not found" >&2; exit 1; }
[ -f "$CONTRACT_FACTS" ] || { echo "ERROR: contract facts file '$CONTRACT_FACTS' not found" >&2; exit 1; }
[ -d "$TF_ROOT" ] || { echo "ERROR: Terraform root '$TF_ROOT' not found" >&2; exit 1; }

SCHEMA_VERSION="$(jq -r '.schemaVersion // 0' "$FACTS")"
[ "$SCHEMA_VERSION" = "2" ] || {
  echo "ERROR: '$FACTS' uses schemaVersion $SCHEMA_VERSION; rerun the current inspect-bicep.sh" >&2
  exit 1
}
CONTRACT_SCHEMA_VERSION="$(jq -r '.schemaVersion // 0' "$CONTRACT_FACTS")"
[ "$CONTRACT_SCHEMA_VERSION" = "2" ] || {
  echo "ERROR: '$CONTRACT_FACTS' uses schemaVersion $CONTRACT_SCHEMA_VERSION; rerun the current inspect-bicep.sh" >&2
  exit 1
}

to_snake_case() {
  printf '%s' "$1" \
    | sed -E 's/([A-Z]+)([A-Z][a-z])/\1_\2/g; s/([a-z0-9])([A-Z])/\1_\2/g' \
    | tr '[:upper:]' '[:lower:]'
}

to_contract_output_name() {
  printf '%s' "$1" | tr '[:upper:]' '[:lower:]'
}

module_directory() {
  local manifest_path="$1"
  local relative="$manifest_path"
  case "$relative" in
    infra_tf/*) relative="${relative#infra_tf/}" ;;
  esac
  printf '%s/%s\n' "${TF_ROOT%/}" "$relative"
}

ERRORS=0
MODULE_COUNT=0

fail() {
  echo "ERROR: $*" >&2
  ERRORS=$((ERRORS + 1))
}

require_block() {
  local file="$1"
  local block_type="$2"
  local block_name="$3"
  local context="$4"
  grep -Eq "^[[:space:]]*$block_type[[:space:]]+\"$block_name\"[[:space:]]*\\{" "$file" \
    || fail "$context is missing $block_type \"$block_name\" in $(basename "$file")"
}

require_sensitive_block() {
  local file="$1"
  local block_type="$2"
  local block_name="$3"
  local context="$4"
  awk -v type="$block_type" -v name="$block_name" '
    $0 ~ "^[[:space:]]*" type "[[:space:]]+\"" name "\"[[:space:]]*\\{" { in_block=1; next }
    in_block && $0 ~ "^[[:space:]]*(variable|output)[[:space:]]+\"" { exit }
    in_block && $0 ~ "sensitive[[:space:]]*=[[:space:]]*true" { found=1; exit }
    END { exit(found ? 0 : 1) }
  ' "$file" || fail "$context must set sensitive = true in $(basename "$file")"
}

PATH_COLLISIONS="$(jq '
  [
    [.files[] | select(.entrypoint | not)]
    | sort_by(.terraformModulePath)
    | group_by(.terraformModulePath)[]
    | select(length > 1)
    | {terraformModulePath: .[0].terraformModulePath, sources: map(.source)}
  ]
' "$FACTS")"
if [ "$(printf '%s' "$PATH_COLLISIONS" | jq 'length')" -ne 0 ]; then
  fail "implementation manifest contains colliding Terraform module paths: $(printf '%s' "$PATH_COLLISIONS" | jq -c .)"
fi

while IFS=$'\t' read -r SOURCE MANIFEST_PATH; do
  SOURCE="${SOURCE%$'\r'}"
  MANIFEST_PATH="${MANIFEST_PATH%$'\r'}"
  [ -n "${SOURCE:-}" ] || continue
  MODULE_COUNT=$((MODULE_COUNT + 1))
  MODULE_DIR="$(module_directory "$MANIFEST_PATH")"

  if [ ! -d "$MODULE_DIR" ]; then
    fail "$SOURCE has no generated module directory '$MODULE_DIR'"
    continue
  fi

  for required_file in main.tf variables.tf outputs.tf versions.tf; do
    [ -f "$MODULE_DIR/$required_file" ] \
      || fail "$SOURCE is missing '$MODULE_DIR/$required_file'"
  done

  if [ -f "$MODULE_DIR/variables.tf" ]; then
    while IFS= read -r BICEP_NAME; do
      BICEP_NAME="${BICEP_NAME%$'\r'}"
      [ -n "$BICEP_NAME" ] || continue
      TF_NAME="$(to_snake_case "$BICEP_NAME")"
      require_block "$MODULE_DIR/variables.tf" variable "$TF_NAME" "$SOURCE parameter '$BICEP_NAME'"
    done < <(jq -r --arg source "$SOURCE" '
      .files[] | select(.source == $source) | .parameters[].name
    ' "$FACTS")

    while IFS= read -r BICEP_NAME; do
      BICEP_NAME="${BICEP_NAME%$'\r'}"
      [ -n "$BICEP_NAME" ] || continue
      TF_NAME="$(to_snake_case "$BICEP_NAME")"
      require_sensitive_block "$MODULE_DIR/variables.tf" variable "$TF_NAME" \
        "$SOURCE secure parameter '$BICEP_NAME'"
    done < <(jq -r --arg source "$SOURCE" '
      .files[] | select(.source == $source) | .parameters[] | select(.secure) | .name
    ' "$FACTS")
  fi

  if [ -f "$MODULE_DIR/outputs.tf" ]; then
    while IFS= read -r BICEP_NAME; do
      BICEP_NAME="${BICEP_NAME%$'\r'}"
      [ -n "$BICEP_NAME" ] || continue
      TF_NAME="$(to_snake_case "$BICEP_NAME")"
      require_block "$MODULE_DIR/outputs.tf" output "$TF_NAME" "$SOURCE output '$BICEP_NAME'"
    done < <(jq -r --arg source "$SOURCE" '
      .files[] | select(.source == $source) | .outputs[].name
    ' "$FACTS")

    while IFS= read -r BICEP_NAME; do
      BICEP_NAME="${BICEP_NAME%$'\r'}"
      [ -n "$BICEP_NAME" ] || continue
      TF_NAME="$(to_snake_case "$BICEP_NAME")"
      require_sensitive_block "$MODULE_DIR/outputs.tf" output "$TF_NAME" \
        "$SOURCE secure output '$BICEP_NAME'"
    done < <(jq -r --arg source "$SOURCE" '
      .files[] | select(.source == $source) | .outputs[] | select(.secure) | .name
    ' "$FACTS")
  fi

  if [ -f "$MODULE_DIR/main.tf" ] && [ -f "$MODULE_DIR/versions.tf" ]; then
    for provider in azurerm azapi random; do
      if grep -Eq "(resource|data)[[:space:]]+\"${provider}_[^\"]+\"" "$MODULE_DIR"/*.tf; then
        grep -Eq "^[[:space:]]*$provider[[:space:]]*=" "$MODULE_DIR/versions.tf" \
          || fail "$SOURCE uses $provider but '$MODULE_DIR/versions.tf' does not declare it"
      fi
    done
  fi
done < <(jq -r '
  .files[]
  | select(.entrypoint | not)
  | [.source, .terraformModulePath]
  | @tsv
' "$FACTS")

EXPECTED_COUNT="$(jq '[.files[] | select(.entrypoint | not)] | length' "$FACTS")"
if [ "$MODULE_COUNT" -ne "$EXPECTED_COUNT" ]; then
  fail "validated $MODULE_COUNT modules but the manifest contains $EXPECTED_COUNT"
fi

for root_file in main.tf variables.tf outputs.tf providers.tf; do
  [ -f "$TF_ROOT/$root_file" ] || fail "Terraform root is missing '$TF_ROOT/$root_file'"
done

if [ -f "$TF_ROOT/variables.tf" ]; then
  while IFS= read -r BICEP_NAME; do
    BICEP_NAME="${BICEP_NAME%$'\r'}"
    [ -n "$BICEP_NAME" ] || continue
    TF_NAME="$(to_snake_case "$BICEP_NAME")"
    require_block "$TF_ROOT/variables.tf" variable "$TF_NAME" "contract parameter '$BICEP_NAME'"
  done < <(jq -r '.files[] | select(.entrypoint) | .parameters[].name' "$CONTRACT_FACTS")

  while IFS= read -r BICEP_NAME; do
    BICEP_NAME="${BICEP_NAME%$'\r'}"
    [ -n "$BICEP_NAME" ] || continue
    TF_NAME="$(to_snake_case "$BICEP_NAME")"
    require_sensitive_block "$TF_ROOT/variables.tf" variable "$TF_NAME" \
      "secure contract parameter '$BICEP_NAME'"
  done < <(jq -r '.files[] | select(.entrypoint) | .parameters[] | select(.secure) | .name' "$CONTRACT_FACTS")
fi

if [ -f "$TF_ROOT/outputs.tf" ]; then
  while IFS= read -r BICEP_NAME; do
    BICEP_NAME="${BICEP_NAME%$'\r'}"
    [ -n "$BICEP_NAME" ] || continue
    TF_NAME="$(to_contract_output_name "$BICEP_NAME")"
    require_block "$TF_ROOT/outputs.tf" output "$TF_NAME" "contract output '$BICEP_NAME'"
  done < <(jq -r '.files[] | select(.entrypoint) | .outputs[].name' "$CONTRACT_FACTS")

  while IFS= read -r BICEP_NAME; do
    BICEP_NAME="${BICEP_NAME%$'\r'}"
    [ -n "$BICEP_NAME" ] || continue
    TF_NAME="$(to_contract_output_name "$BICEP_NAME")"
    require_sensitive_block "$TF_ROOT/outputs.tf" output "$TF_NAME" \
      "secure contract output '$BICEP_NAME'"
  done < <(jq -r '.files[] | select(.entrypoint) | .outputs[] | select(.secure) | .name' "$CONTRACT_FACTS")
fi

if [ -f "$TF_ROOT/providers.tf" ]; then
  for provider in azurerm azapi random; do
    if grep -Eq "(resource|data)[[:space:]]+\"${provider}_[^\"]+\"" "$TF_ROOT"/*.tf; then
      grep -Eq "^[[:space:]]*$provider[[:space:]]*=" "$TF_ROOT/providers.tf" \
        || fail "Terraform root uses $provider but '$TF_ROOT/providers.tf' does not declare it"
    fi
  done
fi

if [ "$ERRORS" -ne 0 ]; then
  echo "Module layout validation failed with $ERRORS error(s)." >&2
  exit 1
fi

echo "Module layout validation passed: root contract plus $MODULE_COUNT source module(s), four required child files each, complete parameter/output blocks, sensitive markings, and declared providers."
