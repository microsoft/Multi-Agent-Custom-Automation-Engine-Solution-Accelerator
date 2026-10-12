/**
 * WorkspaceTree — lazy project explorer for the artifact panel's resting slot.
 *
 * Navigates the AUTHORIZED workspace filesystem as a real tree: one
 * `GET /workspace/{id}/entries?path=` request PER LEVEL, fetched on first
 * expand — never a recursive walk of the whole repo on load. Directories
 * carry an aggregate git marker (M/?) when anything beneath them changed;
 * files carry their own. Clicking a file hands its full path to the viewer
 * (Monaco); clicking a directory toggles and lazily loads its children.
 *
 * State (loaded levels + expansion) lives in `workspaceTreeStore`, NOT here:
 * this component is unmounted whenever a file is open in the panel, and
 * remounting must not mean re-reading the workspace. Coherence with the real
 * filesystem is obtained by explicit invalidation (see the store), never by
 * component lifecycle.
 */
import { Button, Input, Spinner, Tooltip } from '@fluentui/react-components';
import {
  ArrowClockwise20Regular,
  ChevronDown16Regular,
  ChevronRight16Regular,
  Document16Regular,
  Folder16Regular,
  Search16Regular,
} from '@fluentui/react-icons';
import { useEffect, useState } from 'react';
import { apiClient } from '../../api/apiClient';
import { useWorkspaceTree, workspaceTree } from './workspaceTreeStore';

interface WorkspaceTreeProps {
  workspaceId: string;
  onOpenFile: (path: string) => void;
}

const statusColor = (s?: string | null): string =>
  s === 'M' || s === '?'
    ? 'var(--colorStatusWarningForeground1)'
    : 'var(--colorStatusSuccessForeground1)';

export const WorkspaceTree: React.FC<WorkspaceTreeProps> = ({
  workspaceId,
  onOpenFile,
}) => {
  const { levels: childrenMap, expanded } = useWorkspaceTree(workspaceId);

  // Mount: only make sure the root is loaded. No reset, no refetch — the
  // store already holds what the user had open before this remount.
  useEffect(() => {
    workspaceTree.ensure(workspaceId, '');
  }, [workspaceId]);

  // External changes (other tab, SMB mount, agent runs outside a chat turn)
  // are reconciled on visibility by the STORE, not here: this component is
  // unmounted while a file is open, so a listener bound to it would miss the
  // exact moment the user comes back with a file open.

  const toggleDir = (path: string) => workspaceTree.toggle(workspaceId, path);

  // Explicit reconciliation against the real filesystem; keeps expansion.
  const refresh = () => workspaceTree.invalidateAll(workspaceId);

  // ── search: whole-workspace filename filter (git ls-files server-side) ──
  const [q, setQ] = useState('');
  const [results, setResults] = useState<string[] | null>(null);
  useEffect(() => {
    const query = q.trim();
    if (!query) {
      setResults(null);
      return;
    }

    let cancelled = false;
    const t = setTimeout(() => {
      apiClient
        .get(`/v4/workspace/${encodeURIComponent(workspaceId)}/search`, {
          params: { q: query },
        })
        .then((r: { matches?: string[] } | null) => {
          if (!cancelled) setResults(r?.matches ?? []);
        })
        .catch(() => {
          if (!cancelled) setResults([]);
        });
    }, 250);

    return () => {
      cancelled = true;
      clearTimeout(t);
    };
  }, [q, workspaceId]);

  const renderLevel = (parent: string, depth: number): React.ReactNode => {
    const children = childrenMap[parent];
    if (children === 'loading')
      return (
        <Spinner
          size="tiny"
          style={{ margin: `2px 0 2px ${12 + depth * 14}px` }}
        />
      );
    if (!children) return null;
    return children.map((e) => {
      const full = parent ? `${parent}/${e.name}` : e.name;
      const isOpen = expanded.has(full);
      return (
        <div key={full}>
          <Button
            appearance="subtle"
            size="small"
            style={{
              width: '100%',
              justifyContent: 'flex-start',
              paddingLeft: `${4 + depth * 14}px`,
              minHeight: '24px',
            }}
            icon={
              e.type === 'directory' ? (
                isOpen ? (
                  <ChevronDown16Regular />
                ) : (
                  <ChevronRight16Regular />
                )
              ) : (
                <Document16Regular />
              )
            }
            onClick={() =>
              e.type === 'directory' ? toggleDir(full) : onOpenFile(full)
            }
          >
            {e.type === 'directory' && (
              <Folder16Regular style={{ marginRight: 4, flexShrink: 0 }} />
            )}
            <span
              style={{
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
                flex: 1,
                textAlign: 'left',
              }}
            >
              {e.name}
            </span>
            {e.status && (
              <span
                style={{
                  color: statusColor(e.status),
                  fontWeight: 700,
                  fontSize: '11px',
                  flexShrink: 0,
                  marginLeft: 6,
                }}
              >
                {e.status}
              </span>
            )}
          </Button>
          {e.type === 'directory' && isOpen && renderLevel(full, depth + 1)}
        </div>
      );
    });
  };

  const root = childrenMap[''];
  // Empty workspace: yield the slot (same behavior as the old flat panel).
  if (Array.isArray(root) && root.length === 0) return null;

  // Ancho/alto los impone el contenedor redimensionable del slot derecho
  // (PreviewRightSlot): así el explorador y el editor miden lo mismo.
  return (
    <div
      style={{
        flex: 1,
        minHeight: 0,
        minWidth: 0,
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '4px',
          padding: '6px 8px',
          borderBottom: '1px solid var(--colorNeutralStroke1)',
        }}
      >
        <Input
          size="small"
          placeholder="Buscar archivo…"
          value={q}
          onChange={(_e, d) => setQ(d.value)}
          contentBefore={<Search16Regular />}
          style={{ flex: 1, minWidth: 0 }}
          aria-label="Buscar archivo en el workspace"
        />
        <Tooltip content="Refrescar" relationship="label">
          <Button
            appearance="subtle"
            size="small"
            icon={<ArrowClockwise20Regular />}
            aria-label="Refrescar archivos del workspace"
            onClick={refresh}
          />
        </Tooltip>
      </div>
      <div style={{ flex: 1, overflowY: 'auto', padding: '4px' }}>
        {results !== null ? (
          results.length === 0 ? (
            <div
              style={{
                padding: '8px',
                fontSize: '12px',
                color: 'var(--colorNeutralForeground3)',
              }}
            >
              Sin coincidencias.
            </div>
          ) : (
            results.map((p) => (
              <Button
                key={p}
                appearance="subtle"
                size="small"
                icon={<Document16Regular />}
                style={{
                  width: '100%',
                  justifyContent: 'flex-start',
                  minHeight: '24px',
                }}
                onClick={() => onOpenFile(p)}
              >
                <span
                  style={{
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {p}
                </span>
              </Button>
            ))
          )
        ) : (
          renderLevel('', 0)
        )}
      </div>
    </div>
  );
};

export default WorkspaceTree;
