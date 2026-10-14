Capturing the notes from auth install before deleting for docs...

### Auth section:
Requires an app registration as in azure_app_service_auth_setup.md so not deployed by default.

To setup basic auth with FastMCP - bearer token - you can integrate with Azure by using it as your token provider.

``` from fastmcp.server.auth import JWTVerifier```

```
auth = JWTVerifier(
    jwks_uri="https://login.microsoftonline.com/<your-tenant-id>/discovery/v2.0/keys",
    #issuer="https://login.microsoftonline.com/<your-tenant-id>/v2.0",
    # This issuer is not correct in the docs. Found by decoding the token.
    issuer="https://sts.windows.net/<your-tenant-id>/",
    algorithm="RS256",
    audience="api://<your-app-client-id>"
)
```

Requires env vars:
```
export MICROSOFT_CLIENT_ID="your-client-id"
export MICROSOFT_CLIENT_SECRET="your-client-secret"
export MICROSOFT_TENANT="common" # Or your tenant ID
```

```mcp = FastMCP("My MCP Server", auth=auth)```

For more complex and production - supports OAuth and PKCE

Enabled through MCP enabled base - see lifecycle.py


