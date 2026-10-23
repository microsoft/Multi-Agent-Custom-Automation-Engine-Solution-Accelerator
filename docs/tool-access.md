# Acceso a herramientas: vías, identidad, estado medido y skills

Mapa de cómo un agente de MACAE llega a una herramienta, con qué identidad y qué
está comprobado. Cada fila lleva la fecha de la última medición real (no de un
test unitario). Sirve para decidir dónde va cada corrección y qué skill la
documenta.

## 1. Piezas

| Pieza | Qué es | Dónde |
|---|---|---|
| Compositor (carril directo) | `_RouterChatClient`: un agente en el Responses API de la **cuenta** con todas sus tools adjuntas | `src/backend/v4/api/router.py` |
| Especialistas (carril compuesto) | Agentes Foundry que `compose` arma por request; `use_mcp` les da MacaeMcpServer | `src/backend/v4/magentic_agents/` |
| MacaeMcpServer (ca-mcp) | FastMCP: tools de workspace, inspector (puente a servidores externos), skills | `src/mcp_server/` |
| Registro de conexiones | Catálogo en Cosmos `mcp_connections` + secretos en Key Vault | `POST/PUT/DELETE /api/v4/mcp/connections/servers`, `…/user/{name}/connect` |
| Toolbox de Foundry | Un endpoint MCP que agrega N miembros (GitHub, web_search, FoundryMCPServerpreview, KB, MacaeMcpServer, …) | `{project}/toolboxes/Toolbox/mcp?api-version=v1` |
| Inspector config | Servidores stdio/http para desarrollo local | `mcp-inspector-config.json` (raíz del repo) |

## 2. Vías de acceso

| Vía | Quién la usa | Qué ve el modelo | Identidad hacia el destino | Medido |
|---|---|---|---|---|
| **A. Tools nativas del Responses API** (`web_search`, `image_generation`, `code_interpreter`) | Compositor | Siempre, con o sin workspace | Bearer del compositor (OBO del usuario en prod, `az login` en dev) | 2026-10-16: `web_search` con cita; archivos del code interpreter con chip y blob |
| **B. Toolbox como tool `mcp` del Responses API** | Compositor | `mcp_list_tools`: `tool_search`, `call_tool` y las tools **fijadas** en la versión del Toolbox. No ve resources | Bearer del compositor | 2026-10-22: `call_tool` por nombre exacto funciona; `tool_search` devuelve vacío (índice muerto en Foundry) |
| **C. Tools de workspace de MacaeMcpServer** | Compositor con workspace montado | 45 tools (`workspace_*`, inspector) ejecutadas por el backend | Bearer del usuario en la sesión MCP (`http_client` con `Authorization`) | 2026-10-22: corregido en `_workspace_tools`; sin bearer, el salto ca-mcp→backend era anónimo y prod respondía 500 |
| **D. MacaeMcpServer en especialistas** (`use_mcp`) | Especialistas Foundry | Las mismas 45 tools; el framework pide aprobación a toda tool sin `readOnlyHint` | Bearer del usuario (`lifecycle.py`) | 2026-10-20: validación de INC completa con workspace montado; 3 tarjetas de aprobación por lecturas |
| **E. Registro → servidor externo** (`connect_from_registry`) | Compositor y especialistas vía ca-mcp | `discover_mcp_capabilities` (tools, resources, prompts), `call_external_tool`, `read_external_resource` | La que declare el registro: `static_secret` / `oauth_refresh` (Key Vault) o `managed_identity` (MI de ca-mcp). **`managed_identity` gana sobre cualquier token entrante** | 2026-10-22: `tool-boxv` conecta; GitHub, `web_search___search` y `FoundryMCPServerpreview___agent_get` responden por nombre exacto |
| **F. Conexión directa** (`connect_mcp_server(url, access_token)`) | Igual que E, sin registro | Igual que E | `access_token` pasado, si no el bearer entrante de la request MCP | 2026-10-21 (prod): conectó al Toolbox con `access_token=""` porque el registro forzaba MI |
| **G. Servidores stdio del inspector config** (`connect_stdio_server`) | Igual que E, sólo local | `filesystem`, `everything`, `github`, `playwright`, … | Proceso local | 2026-10-20: `filesystem` y `everything` probados. **No entran en la imagen**: el archivo vive en la raíz del repo y la imagen se construye con contexto `src/mcp_server` (prod: `inspector_config_servers: []`) |
| **H. Resources / skills** | Sólo vía E, F o G con `read_external_resource` | `skill://<nombre>/SKILL.md`, `_manifest`; en el Toolbox `skill://index.json` | La de la conexión | 2026-10-21: ca-mcp publica `using-the-toolbox` en local y prod; el índice del Toolbox lista `skills: []`. Ni la tool MCP del framework ni el tool `mcp` hosted exponen resources al modelo |

## 3. Identidad por destino

Un contenedor, una conexión o un miembro sólo se ve con la identidad y desde el
endpoint que lo creó o lo autorizó. Medido:

| Destino | Identidad correcta | Por qué |
|---|---|---|
| Toolbox (`tool-boxv`) | **Bearer del usuario** | Cubre a todos los miembros. La MI cubre GitHub y `web_search` pero falla en los miembros OBO (`FoundryMCPServerpreview` → `obotoken` BadRequest, 2026-10-22) |
| MacaeMcpServer registrado como servidor | MI de ca-mcp | No tiene miembros OBO; el salto a su propio backend sí necesita el bearer del usuario |
| Grafana y recursos de plataforma | `managed_identity` con `audience` | Rol de la MI en el recurso |
| Servidores con secreto fijo o OAuth del usuario (Higgsfield, Linear, YouTube) | `static_secret` / `oauth_refresh` en Key Vault | La sesión re-resuelve por llamada con `(credential_source, audience, secret_ref)` |
| Contenedores del code interpreter | El endpoint que los creó: **cuenta** para el compositor, **proyecto** para agentes Foundry | 404 cruzado medido 2026-10-19; el ámbito viaja en `additional_properties` del archivo |

Regla práctica: el usuario nunca escribe un token. El bearer es su sesión de
EasyAuth, reenviada compositor → ca-mcp → destino.

## 4. Huecos abiertos (medidos)

1. **`tool_search` del Toolbox devuelve vacío** para cualquier consulta, incluido el nombre exacto, en todas las versiones (17, 20, 53, 54). Apagar y encender el selector y limpiar versiones no lo cambió. `call_tool` por nombre exacto funciona. Es del lado de Foundry.
2. **Skills del Toolbox vacías**: la capacidad cargada en el portal no está publicada en ninguna versión servida.
3. **`mcp-inspector-config.json` no viaja en la imagen** de ca-mcp: en prod no hay servidores stdio ni la entrada `macae-mcp-server`, así que ningún agente puede conectarse a ca-mcp mismo para leer sus skills.
4. **Las tools de ca-mcp no declaran `readOnlyHint`**: el carril compuesto pide aprobación humana por lecturas (`list_connected_servers`, `workspace_exec` de `pytest`).
5. **Cada reanudación tras una aprobación reconstruye el equipo** y deja una burbuja `assistant` vacía.
6. **`compose` no expone a los especialistas** `web_search` nativo ni el Toolbox; sólo `use_bing`, excluyente con `use_reasoning`.

## 5. Skills: qué documenta cada fase y dónde vive

Una skill es un `SKILL.md` con frontmatter `name` y `description` **en una sola
línea** (FastMCP parsea `clave: valor` plano; un `>-` queda literal).

| Skill | Dónde | Qué fija |
|---|---|---|
| `using-the-toolbox` | `src/mcp_server/skills/` (existe) y como capacidad del Toolbox (pendiente de publicar) | `tool_search` → `call_tool` con nombre exacto `Fuente___tool`; mientras el índice esté vacío, nombres conocidos por `discover_mcp_capabilities` |
| `registering-mcp-servers` | `src/mcp_server/skills/` | `POST /mcp/connections/servers` con `auth_type`; `credential_source` derivado; `PUT` para `managed_identity` + `audience`; qué identidad corresponde a cada destino (sección 3) |
| `workspace-sandbox` | `src/mcp_server/skills/` | Share = durable, sandbox = cómputo; escribir → `_catch_up` → `_publish`; `publish_detail` como evidencia |
| `incident-registry` | `src/mcp_server/skills/` | Leer `docs/incidents`, estado, firma, sonda, techo de autoridad; reporte por INC |

Las skills de ca-mcp las lee un agente con `connect_mcp_server` a ca-mcp (o la
entrada `macae-mcp-server` del inspector config cuando esté en la imagen) y
`read_external_resource("…", "skill://<nombre>/SKILL.md")`.
