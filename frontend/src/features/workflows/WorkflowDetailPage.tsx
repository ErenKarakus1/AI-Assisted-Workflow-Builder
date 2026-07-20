import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  activateWorkflow,
  deactivateWorkflow,
  getWorkflow,
  updateWorkflow,
  validateWorkflow,
  validateWorkflowDraft,
} from "../../api/workflows";
import { errorMessage } from "../../lib/errors";
import type { WorkflowEdge, WorkflowNode, WorkflowValidationResult } from "../../types/api";
import { WorkflowGraphEditor } from "./WorkflowGraphEditor";

export function WorkflowDetailPage() {
  const { organizationId = "", workflowId = "" } = useParams();
  const queryClient = useQueryClient();
  const workflowQuery = useQuery({
    queryKey: ["workflow", organizationId, workflowId],
    queryFn: () => getWorkflow(organizationId, workflowId),
    enabled: Boolean(organizationId && workflowId),
  });
  const validateMutation = useMutation({
    mutationFn: () => validateWorkflow(organizationId, workflowId),
  });
  const activateMutation = useMutation({
    mutationFn: () => activateWorkflow(organizationId, workflowId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["workflow", organizationId, workflowId] });
      await queryClient.invalidateQueries({ queryKey: ["workflows", organizationId] });
    },
  });
  const deactivateMutation = useMutation({
    mutationFn: () => deactivateWorkflow(organizationId, workflowId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["workflow", organizationId, workflowId] });
      await queryClient.invalidateQueries({ queryKey: ["workflows", organizationId] });
    },
  });
  const validateDraftMutation = useMutation({
    mutationFn: ({ nodes, edges }: { nodes: WorkflowNode[]; edges: WorkflowEdge[] }) => {
      if (!workflowQuery.data) {
        throw new Error("Workflow is not loaded");
      }

      return validateWorkflowDraft(organizationId, workflowId, { ...workflowQuery.data, nodes, edges });
    },
  });
  const saveMutation = useMutation({
    mutationFn: ({ nodes, edges }: { nodes: WorkflowNode[]; edges: WorkflowEdge[] }) => {
      if (!workflowQuery.data) {
        throw new Error("Workflow is not loaded");
      }

      return updateWorkflow({ ...workflowQuery.data, nodes, edges });
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["workflow", organizationId, workflowId] });
      await queryClient.invalidateQueries({ queryKey: ["workflows", organizationId] });
    },
  });

  const workflow = workflowQuery.data;

  return (
    <section className="page-stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Workflow</p>
          <h2>{workflow?.name ?? "Loading workflow"}</h2>
        </div>
        <Link className="text-link" to="/workflows">
          Back to workflows
        </Link>
      </div>

      {workflowQuery.isLoading ? <p className="muted">Loading...</p> : null}
      {workflowQuery.isError ? <p className="form-error">Could not load workflow.</p> : null}

      {workflow ? (
        <>
          <div className="detail-grid">
            <article className="metric-card">
              <span>Status</span>
              <strong>{workflow.status}</strong>
            </article>
            <article className="metric-card">
              <span>Revision</span>
              <strong>{workflow.revision}</strong>
            </article>
            <article className="metric-card">
              <span>Graph</span>
              <strong>
                {workflow.nodes.length} nodes / {workflow.edges.length} edges
              </strong>
            </article>
          </div>

          <div className="action-row">
            <button
              className="button"
              type="button"
              disabled={validateMutation.isPending}
              onClick={() => validateMutation.mutate()}
            >
              {validateMutation.isPending ? "Validating..." : "Validate"}
            </button>
            <button
              className="button button--secondary"
              type="button"
              disabled={workflow.status === "active" || activateMutation.isPending}
              onClick={() => activateMutation.mutate()}
            >
              {activateMutation.isPending ? "Activating..." : "Activate"}
            </button>
            <button
              className="button button--ghost"
              type="button"
              disabled={workflow.status !== "active" || deactivateMutation.isPending}
              onClick={() => deactivateMutation.mutate()}
            >
              {deactivateMutation.isPending ? "Inactivating..." : "Inactivate"}
            </button>
          </div>

          {validateMutation.data ? <ValidationPanel result={validateMutation.data} nodes={workflow.nodes} /> : null}
          {validateDraftMutation.data ? (
            <ValidationPanel
              result={validateDraftMutation.data}
              nodes={validateDraftMutation.variables?.nodes ?? workflow.nodes}
            />
          ) : null}
          {activateMutation.isError ? (
            <p className="form-error">
              {errorMessage(activateMutation.error, "Workflow could not be activated.")}
            </p>
          ) : null}
          {deactivateMutation.isError ? (
            <p className="form-error">
              {errorMessage(deactivateMutation.error, "Workflow could not be inactivated.")}
            </p>
          ) : null}
          {validateDraftMutation.isError ? (
            <p className="form-error">
              {errorMessage(validateDraftMutation.error, "Workflow draft could not be validated.")}
            </p>
          ) : null}
          {saveMutation.isError ? (
            <p className="form-error">{errorMessage(saveMutation.error, "Workflow graph could not be saved.")}</p>
          ) : null}
          {saveMutation.isSuccess ? <p className="success-panel">Graph saved.</p> : null}

          <WorkflowGraphEditor
            workflow={workflow}
            isSaving={saveMutation.isPending}
            onSave={(nodes, edges) => saveMutation.mutate({ nodes, edges })}
            isValidatingDraft={validateDraftMutation.isPending}
            onValidateDraft={(nodes, edges) => validateDraftMutation.mutate({ nodes, edges })}
          />

          <div className="split-panel">
            <GraphList title="Nodes" items={workflow.nodes.map((node) => `${node.id} - ${node.type}`)} />
            <GraphList
              title="Edges"
              items={workflow.edges.map(
                (edge) => `${edge.id}: ${edge.source} -> ${edge.target}${edge.label ? ` (${edge.label})` : ""}`,
              )}
            />
          </div>
        </>
      ) : null}
    </section>
  );
}

function ValidationPanel({
  result,
  nodes,
}: {
  result: WorkflowValidationResult;
  nodes: WorkflowNode[];
}) {
  const nodesById = new Map(nodes.map((node) => [node.id, node]));

  return (
    <div className={result.is_valid ? "success-panel" : "error-panel"}>
      <strong>{result.is_valid ? "Workflow is valid" : "Workflow needs changes"}</strong>
      {result.errors.length ? (
        <ul>
          {result.errors.map((error) => (
            <li key={`${error.code}-${error.node_id}-${error.edge_id}`}>
              {error.message}
              {error.node_id ? ` Node: ${nodeDisplayName(error.node_id, nodesById)}.` : ""}
              {error.edge_id ? ` Edge: ${error.edge_id}.` : ""}
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

function nodeDisplayName(nodeId: string, nodesById: Map<string, WorkflowNode>): string {
  const node = nodesById.get(nodeId);
  const label = node ? stringValue(node.data.label).trim() : "";
  return label ? `${label} (${nodeId})` : nodeId;
}

function stringValue(value: unknown): string {
  return typeof value === "string" || typeof value === "number" || typeof value === "boolean"
    ? String(value)
    : "";
}

function GraphList({ title, items }: { title: string; items: string[] }) {
  return (
    <article className="list-panel">
      <div className="panel-heading">{title}</div>
      {items.length ? (
        items.map((item) => (
          <div className="compact-row" key={item}>
            {item}
          </div>
        ))
      ) : (
        <p className="muted">None</p>
      )}
    </article>
  );
}
