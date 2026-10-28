# Local development identity — used when APP_ENV=dev and no EasyAuth headers are present.
#
# Values are wired to the real MACAE tenant/app so that:
#   - get_authenticated_user_details() returns a stable, non-null user_principal_id
#   - get_tenantid() decodes the X-Ms-Client-Principal blob and returns the real tenant_id
#   - OBO flow in auth_utils._dev_acquire_user_token() targets the correct tenant/client
#
# X-Ms-Client-Principal is a base64-encoded JSON with at minimum {"tid": "<tenant_id>"}.
# Tenant / client IDs match _DEV_TENANT_ID / _DEV_CLIENT_ID in auth_utils.py.

sample_user = {
    "Accept": "*/*",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "en",
    "Content-Type": "application/json",
    "Host": "localhost:8000",
    "Origin": "http://localhost:3000",
    "Referer": "http://localhost:3000/",
    "User-Agent": "Mozilla/5.0 (dev)",
    # ── EasyAuth identity headers ──────────────────────────────────────────
    # A stable local dev user ID — used as Cosmos partition key / user_id everywhere.
    "X-Ms-Client-Principal-Id": "USER",
    "X-Ms-Client-Principal-Name": "dev@local",
    "X-Ms-Client-Principal-Idp": "aad",
    # get_tenantid() decodes this to extract tenant_id = 978d9cc6-...
    "X-Ms-Client-Principal": ("USER"),
    "X-Ms-Token-Aad-Access-Token": "",
    "X-Ms-Token-Aad-Id-Token": "",
}
