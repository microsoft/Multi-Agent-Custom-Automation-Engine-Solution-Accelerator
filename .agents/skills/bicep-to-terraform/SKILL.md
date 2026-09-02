# Bicep → Terraform converter (1:1 infrastructure port)

Produces a **faithful 1:1 Terraform port** of an existing Bicep infrastructure into a new
`infra_tf/` directory that **coexists** with the original `infra/` (Bicep). The port deploys the
same resources and — critically — emits the **same output contract** the solution's post-provision
scripts consume, so the post-deploy layer works unchanged regardless of which stack provisioned.

## Use when
The user wants to convert, port, or migrate existing Bicep infrastructure to Terraform, or to add
a Terraform flavor alongside Bicep. This skill authors HCL; it does **not** deploy it and does not
generate CI/CD (that is `cicd-terraform-workflows`).

## What this skill ships
- **`references/`** — `bicep-to-terraform-mapping.md` (resource/param/output mapping rules) and
  `naming-conventions.md` (the `infra_tf/` layout, `<env>.tfvars`, provider/backend conventions).
- **`scripts/`** — `inspect-bicep.sh` (read-only discovery of the Bicep entrypoint, its parameters,
  outputs, recursive local-module graph, and resource types → `bicep-facts.json`) and
  `validate-module-layout.sh` (checks source-module parity and the required generated files).
- **`templates/`** — root `providers.tf`, a mandatory four-file child-module scaffold
  (`main.tf`, `variables.tf`, `outputs.tf`, `versions.tf`), and `gitignore` (copied verbatim to
  `infra_tf/.gitignore`).

## Hard constraints
- **Faithful 1:1 port.** Reproduce the source's resources, properties, and dependencies — do not
  redesign, "improve", add, or drop resources. Deviate only where a Terraform provider genuinely
  requires it (document each such deviation).
- **Preserve the output contract.** Every output the source `main.bicep` emits **must** exist in
  `infra_tf/outputs.tf` with an equivalent value. Emit root output names by ASCII-lowercasing the
  exact contract key without inserting/removing separators: `RESOURCE_GROUP_NAME` becomes
  `resource_group_name`, while legacy `resourceGroupName` becomes `resourcegroupname`. The
  post-deploy bridge uppercases both back to their canonical environment-key forms. **Never rename,
  combine, or drop an output or compatibility alias.**
- **Never touch the source.** Do not edit the repo's Bicep files, application code, or
  post-provision scripts. Only author files under `infra_tf/`.
- **Coexist, never replace.** `infra/` (Bicep) stays intact. Everything you write goes under a new
  `infra_tf/` sibling directory.
- **One source module, one generated module.** Every reachable local Bicep module file maps to
  exactly one Terraform module directory. Repeated calls to the same Bicep file reuse that one
  generated module. Mirror the source path under `modules/`; never flatten or combine modules.
- **Four files in every child module.** Every generated module contains `main.tf`, `variables.tf`,
  `outputs.tf`, and `versions.tf`, even when one of those files has no blocks. Every Bicep module
  parameter and output must be represented in the corresponding file. `versions.tf` declares
  every provider used by that module, while provider authentication remains root-only.
- **Ask before any mutation.** Confirm with the user (via an interactive input tool when available)
  before writing any file under `infra_tf/`. Read-only discovery needs no approval.
- **Use the bundled script.** Run `scripts/inspect-bicep.sh` in place by absolute path; never copy
  it into the target repo. Extend it if a capability is missing.
- **Rely on active sessions.** Use the user's existing `az` session for any read-only lookup; never
  ask for credentials. Do not deploy anything.
- **Temp files under `.agent/tmp/`, always cleaned up.** Write scratch (e.g. `bicep-facts.json`)
  only under `.agent/tmp/` and remove it before finishing, even on failure.
- **No state, no backend deploy.** This skill authors the `backend "azurerm"` *block shape* only;
  it never creates the state storage account (that is a documented prerequisite handled by the
  CI/CD skill). You **may** run `terraform init -backend=false`, `terraform fmt`, and
  `terraform validate` for the static-check gate (step 8), but never run `terraform plan`/`apply`
  or `init` against a real remote backend.

## Process
1. **Pick the contract entrypoint, implementation entrypoint & flavor.** Default the contract
   entrypoint to `infra/main.bicep`. If it is a router with a `deploymentFlavor`-style switch
   (in this repository, `bicep` / `avm` / `avm-waf`), inspect its actual allowed values and **ask
   the user which single flavor to port first**. Preserve the router's public parameter/output
   contract, but follow only the selected implementation branch's resource/module tree. Port one
   flavor per run.
2. **Inspect recursively.** Run `bash <absolute-skill-path>/scripts/inspect-bicep.sh
   <implementation-entrypoint> > .agent/tmp/bicep-facts.json`. It compiles every reachable local Bicep module and reports the
   target scope; per-file parameters, source variables, resources, child-module edges, outputs,
   provider hints; sibling ARM `*.parameters.json` files and `params/*.bicepparam` files; and the
   complete local-module graph. When the contract entrypoint differs, run
   `bash <absolute-skill-path>/scripts/inspect-bicep.sh --no-recursive <contract-entrypoint> >
   .agent/tmp/bicep-contract-facts.json`. The script's source-variable extraction is an aid, not a
   parser: read every discovered source file before translating expressions.
3. **Confirm scope with the user.** Present the resource inventory, the parameter list, and the full
   output list that must be preserved. Confirm the exact source-file → Terraform-module mapping,
   the root plus one child module per reachable local Bicep module, the selected source parameter
   file, and its `terraform.tfvars` mapping. If `infra_tf/` already exists, explicitly classify the
   run as an in-place regeneration or a fresh conversion. For in-place regeneration, treat Bicep
   and the current mapping reference as authoritative, replace stale generated source rather than
   preserving old mistakes, remove only specifically identified stale generated files, and never
   delete `.terraform/`, state, or the lock file. **Get explicit approval before writing files.**
4. **Author `infra_tf/` — root.** Seed from `templates/`:
   - `providers.tf` — `terraform{}` `required_version` + `required_providers` (`azurerm`, and
     `azapi` when the source uses preview resource types via `Microsoft.*@<api-version>`, plus
     `random` if unique-suffix logic is present), the `provider "azurerm" { features {} }` block,
     and the **partial** `backend "azurerm" {}` block (init values supplied later by CI, never
     committed here).
   - `variables.tf` — one `variable` per Bicep `param`, carrying over type, `default`, and
     `validation` blocks from `@allowed`/`@minValue`/`@minLength` decorators.
   - `main.tf` — resources/`module` calls mirroring the source `main.bicep`, using the mapping
     rules in `references/bicep-to-terraform-mapping.md`. Preserve dependency order (implicit refs
     first; add `depends_on` only where Bicep had an explicit dependency).
   - `outputs.tf` — every source output, value-equivalent (see the output-contract constraint).
   - `.gitignore` — copy `templates/gitignore` verbatim to `infra_tf/.gitignore`. This is
     **required**: `terraform init` downloads multi-hundred-MB provider binaries into
     `.terraform/`, which exceed GitHub's 100 MB file limit and break `git push` if committed. The
     ignore also covers `*.tfstate`, saved `tfplan`s, and the CI-generated `backend.tf` /
     `backend.*.hcl`, while **keeping `.terraform.lock.hcl` tracked** (it pins provider versions).
5. **Author the complete mirrored module tree.** For every non-entrypoint file in
   `bicep-facts.json`, create its `terraform_module_path` and seed all four files from
   `templates/module/`:
   - `main.tf` — resources, locals, data sources, and nested module calls from that Bicep file.
   - `variables.tf` — every Bicep `param`, with equivalent type/default/validation semantics.
   - `outputs.tf` — every Bicep `output`, with a value-equivalent expression.
   - `versions.tf` — `required_version` plus every provider referenced in that module.

   A Bicep file called multiple times still has one generated directory and multiple Terraform
   module calls. Preserve nested calls as nested Terraform module calls. Child modules declare
   provider sources but never configure credentials/subscriptions; configuration belongs at root.
6. **Author `terraform.tfvars` and per-env `.tfvars`.** Always emit
   `infra_tf/terraform.tfvars` for the single flavor selected in step 1:
   - Use `infra/main.parameters.json` for `bicep` or `avm`, overriding its
     `deploymentFlavor` environment default with the selected flavor.
   - Use `infra/main.waf.parameters.json` for `avm-waf`, preserving its fixed WAF feature values.
   - Translate literal ARM parameter values and `.bicepparam` assignments to snake_case tfvars
     keys. Never copy `${AZURE_ENV_*}` expressions as literal Terraform values because tfvars does
     not expand them. Map non-secret runtime values to corresponding `TF_VAR_*` inputs, and leave
     required dynamic values out of the committed tfvars file.
   - Never write secure parameter values to a committed tfvars file. Supply them through the
     deployment environment or secret store.
   - Add `subscription_id` and `resource_group_name` to the runtime-input mapping because Bicep
     receives them from deployment context rather than ARM parameter files.

   When actual stage files exist under `infra/params/`, also translate each
   `<env>.bicepparam` into `infra_tf/<env>.tfvars`. Keep CI-identity values faithful to the source.
7. **Flag provider-forced deviations.** List any place where Terraform required a different shape
   than Bicep (e.g. `azapi_resource` for a preview type, `ignore_changes` for a known drift quirk,
   a `random_string` suffix where Bicep used `uniqueString()`), with a one-line reason each.
8. **Validate — mandatory semantic and static gates; iterate until clean.** Trace every `count` and
   `for_each` expression through root and child module arguments using the plan-time-known
   cardinality rules in `references/bicep-to-terraform-mapping.md`. Review type-overloaded function
   translations and provider deprecations. Then run this sequence and **do not consider the port
   complete until the semantic audit, structure validation, and `terraform validate` succeed**:
   ```bash
   bash <absolute-skill-path>/scripts/validate-module-layout.sh \
     .agent/tmp/bicep-facts.json infra_tf .agent/tmp/bicep-contract-facts.json
   cd infra_tf
   terraform fmt -recursive
   terraform init -backend=false   # installs providers without touching remote state
   terraform validate
   ```
   Pass the third contract-facts argument only when the contract and implementation entrypoints
   differ; otherwise the implementation facts are also the contract facts.
   The layout validator fails on missing module directories/files, missing parameter/output blocks,
   or undeclared providers. `-backend=false` lets `init` run without the (not-yet-provisioned)
   azurerm state backend. If any command reports errors, **fix the generated HCL and re-run the
   full sequence** — repeat until it passes. Common first-pass failures and their fixes are documented in
   `references/bicep-to-terraform-mapping.md` (azapi `identity` is a nested block not an argument;
   set `schema_validation_enabled = false` on preview `@api-version` azapi resources; every child
   module using `azapi_*`/`random_*` needs its own `versions.tf`). When you hit a NEW class of
   error not already covered there, fix the port **and** add a short note to that mapping reference
   so future conversions avoid it. Only if `terraform` is genuinely unavailable on the machine may
   you skip — say so explicitly; never report a port as done on an unvalidated tree when terraform
   is present. Static validation does not replace the cardinality provenance audit.
9. **Clean up** `bicep-facts.json`, `bicep-contract-facts.json`, and any other files this run
   created under `.agent/tmp/` (remove the directory only if this run created it and it is empty),
   even if an earlier step failed.

## Output
Report, in order:
1. **Source** — entrypoint, chosen flavor, target scope, stage(s) discovered.
2. **Inventory** — resource types ported, module count, parameter count, and the complete
   source-file → Terraform-module mapping.
3. **Output contract** — the full list of preserved outputs (source name → TF output name),
   confirming none were dropped or renamed.
4. **Generated files** — the `infra_tf/` tree written and each file's purpose.
5. **Deviations** — every provider-forced difference from the source, with its reason.
6. **Validation** — the module-layout / `fmt` / `init -backend=false` / `validate` gate results
   (layout and validate must both be clean), or an explicit note that `terraform` was unavailable.
7. **Cleanup** — confirm `.agent/tmp/` files were removed.
8. **Next step** — point to `cicd-terraform-workflows` to generate the pipeline, and note the
   state-backend bootstrap is a prerequisite there.
