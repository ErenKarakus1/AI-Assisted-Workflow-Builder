import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { listInstanceEvents, listWorkflowInstances, startWorkflowInstance } from "../../api/instances";
import {
  activateWorkflow,
  deactivateWorkflow,
  getWorkflow,
  updateWorkflow,
  validateWorkflow,
  validateWorkflowDraft,
} from "../../api/workflows";
import { errorMessage } from "../../lib/errors";
import type {
  InstanceEvent,
  WorkflowEdge,
  WorkflowInstance,
  WorkflowNode,
  WorkflowValidationResult,
} from "../../types/api";
import { WorkflowGraphEditor } from "./WorkflowGraphEditor";

export function WorkflowDetailPage() {
  const { organizationId = "", workflowId = "" } = useParams();
  const queryClient = useQueryClient();
  const [instanceInput, setInstanceInput] = useState("{}");
  const [selectedInstanceId, setSelectedInstanceId] = useState<string | null>(null);
  const [hasUnsavedGraphChanges, setHasUnsavedGraphChanges] = useState(false);
  const workflowQuery = useQuery({
    queryKey: ["workflow", organizationId, workflowId],
    queryFn: () => getWorkflow(organizationId, workflowId),
    enabled: Boolean(organizationId && workflowId),
  });
  const instancesQuery = useQuery({
    queryKey: ["workflow-instances", organizationId, workflowId],
    queryFn: () => listWorkflowInstances(organizationId, workflowId),
    enabled: Boolean(organizationId && workflowId),
  });
  const effectiveSelectedInstanceId = selectedInstanceId ?? instancesQuery.data?.[0]?.id ?? null;
  const eventsQuery = useQuery({
    queryKey: ["instance-events", organizationId, effectiveSelectedInstanceId],
    queryFn: () => listInstanceEvents(organizationId, effectiveSelectedInstanceId ?? ""),
    enabled: Boolean(organizationId && effectiveSelectedInstanceId),
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
  const startInstanceMutation = useMutation({
    mutationFn: () => startWorkflowInstance(organizationId, workflowId, parseJsonObject(instanceInput)),
    onSuccess: async (instance) => {
      setSelectedInstanceId(instance.id);
      await queryClient.invalidateQueries({ queryKey: ["workflow-instances", organizationId, workflowId] });
      await queryClient.invalidateQueries({ queryKey: ["tasks", organizationId] });
    },
  });
  useAutoResetMutation(activateMutation.isError, activateMutation.reset);
  useAutoResetMutation(deactivateMutation.isError, deactivateMutation.reset);
  useAutoResetMutation(validateDraftMutation.isError, validateDraftMutation.reset);
  useAutoResetMutation(saveMutation.isError || saveMutation.isSuccess, saveMutation.reset);
  useAutoResetMutation(startInstanceMutation.isError, startInstanceMutation.reset);
  useAutoResetMutation(Boolean(validateMutation.data?.is_valid), validateMutation.reset);
  useAutoResetMutation(Boolean(validateDraftMutation.data?.is_valid), validateDraftMutation.reset);

  const resetValidate = validateMutation.reset;
  const resetValidateDraft = validateDraftMutation.reset;
  const handleDirtyChange = useCallback((isDirty: boolean) => {
    setHasUnsavedGraphChanges(isDirty);
    if (isDirty) {
      resetValidate();
      resetValidateDraft();
    }
  }, [resetValidate, resetValidateDraft]);

  const workflow = workflowQuery.data;
  const selectedInstance =
    instancesQuery.data?.find((instance) => instance.id === effectiveSelectedInstanceId) ??
    startInstanceMutation.data ??
    null;

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
              disabled={workflow.status === "active" || activateMutation.isPending || hasUnsavedGraphChanges}
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

          {hasUnsavedGraphChanges ? (
            <p className="warning-panel">Save the graph before activating or starting an instance.</p>
          ) : null}

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
          {saveMutation.isSuccess ? (
            <p className="success-panel">
              <strong>Graph saved.</strong>
            </p>
          ) : null}

          <WorkflowGraphEditor
            workflow={workflow}
            isSaving={saveMutation.isPending}
            onSave={(nodes, edges) => saveMutation.mutate({ nodes, edges })}
            isValidatingDraft={validateDraftMutation.isPending}
            onValidateDraft={(nodes, edges) => validateDraftMutation.mutate({ nodes, edges })}
            onDirtyChange={handleDirtyChange}
            selectedInstance={selectedInstance}
            instanceEvents={eventsQuery.data ?? []}
          />

          <InstanceRunner
            workflowStatus={workflow.status}
            input={instanceInput}
            onInputChange={setInstanceInput}
            hasUnsavedGraphChanges={hasUnsavedGraphChanges}
            isStarting={startInstanceMutation.isPending}
            startError={startInstanceMutation.error}
            onStart={() => startInstanceMutation.mutate()}
            instances={instancesQuery.data ?? []}
            selectedInstance={selectedInstance}
            selectedInstanceId={selectedInstanceId}
            onSelectInstance={setSelectedInstanceId}
            events={eventsQuery.data ?? []}
            areEventsLoading={eventsQuery.isLoading}
          />

          <div className="split-panel">
            <GraphList
              title="Nodes"
              items={workflow.nodes.map((node) => `${nodeDisplayName(node.id, new Map(workflow.nodes.map((item) => [item.id, item])))} - ${humanize(node.type)}`)}
            />
            <ConnectionList nodes={workflow.nodes} edges={workflow.edges} />
          </div>
        </>
      ) : null}
    </section>
  );
}

function InstanceRunner({
  workflowStatus,
  input,
  onInputChange,
  hasUnsavedGraphChanges,
  isStarting,
  startError,
  onStart,
  instances,
  selectedInstance,
  selectedInstanceId,
  onSelectInstance,
  events,
  areEventsLoading,
}: {
  workflowStatus: string;
  input: string;
  onInputChange: (value: string) => void;
  hasUnsavedGraphChanges: boolean;
  isStarting: boolean;
  startError: unknown;
  onStart: () => void;
  instances: WorkflowInstance[];
  selectedInstance: WorkflowInstance | null;
  selectedInstanceId: string | null;
  onSelectInstance: (id: string) => void;
  events: InstanceEvent[];
  areEventsLoading: boolean;
}) {
  const inputError = parseJsonObjectError(input);
  const canStart = workflowStatus === "active" && !isStarting && !inputError && !hasUnsavedGraphChanges;

  return (
    <section className="runner-panel">
      <div className="editor-toolbar">
        <div>
          <strong>Run workflow</strong>
          <span>
            {hasUnsavedGraphChanges
              ? "Save graph changes before starting"
              : workflowStatus === "active"
                ? "Start a new instance"
                : "Activate workflow before running"}
          </span>
        </div>
        <button className="button" type="button" disabled={!canStart} onClick={onStart}>
          {isStarting ? "Starting..." : "Start instance"}
        </button>
      </div>

      <div className="runner-grid">
        <div className="config-stack">
          <label>
            Input JSON
            <textarea
              value={input}
              disabled={workflowStatus !== "active"}
              rows={8}
              onChange={(event) => onInputChange(event.target.value)}
            />
          </label>
          {inputError ? <p className="field-error">{inputError}</p> : null}
          {startError ? (
            <p className="form-error">{errorMessage(startError, "Workflow instance could not be started.")}</p>
          ) : null}
        </div>

        <div className="list-panel">
          <div className="panel-heading">Instances</div>
          {instances.length ? (
            instances.map((instance) => (
              <button
                className={
                  instance.id === (selectedInstanceId ?? selectedInstance?.id)
                    ? "compact-row compact-row--button active"
                    : "compact-row compact-row--button"
                }
                key={instance.id}
                type="button"
                onClick={() => onSelectInstance(instance.id)}
              >
                <strong>{instance.status}</strong>
                <span>
                  {instance.id} - rev {instance.workflow_revision}
                </span>
              </button>
            ))
          ) : (
            <p className="muted">No instances yet.</p>
          )}
        </div>
      </div>

      {selectedInstance ? (
        <div className="split-panel instance-panels">
          <article className="list-panel">
            <div className="panel-heading">Selected instance</div>
            <div className="compact-row instance-summary">
              <strong>{selectedInstance.status}</strong>
              <span>ID: {selectedInstance.id}</span>
              <span>Active node: {selectedInstance.active_node_id ?? "none"}</span>
              {selectedInstance.status === "waiting" ? (
                <Link className="text-link" to="/tasks">
                  Review approval tasks
                </Link>
              ) : null}
            </div>
            <JsonBlock title="Input" value={selectedInstance.input} />
            <JsonBlock title="Context" value={selectedInstance.context} />
          </article>

          <article className="list-panel">
            <div className="panel-heading">Event timeline</div>
            {areEventsLoading ? <p className="muted">Loading events...</p> : null}
            {events.length ? (
              events.map((event) => (
                <div className="compact-row event-row" key={event.id}>
                  <strong>{humanize(event.type)}</strong>
                  <span>{event.node_id ? `Node: ${event.node_id}` : "Workflow event"}</span>
                  {Object.keys(event.data).length ? <code>{humanizeEventData(event.data)}</code> : null}
                </div>
              ))
            ) : !areEventsLoading ? (
              <p className="muted">No events recorded yet.</p>
            ) : null}
          </article>
        </div>
      ) : null}
    </section>
  );
}

function JsonBlock({ title, value }: { title: string; value: Record<string, unknown> }) {
  return (
    <div className="compact-row">
      <strong>{title}</strong>
      <pre>{JSON.stringify(value, null, 2)}</pre>
    </div>
  );
}

function ConnectionList({ nodes, edges }: { nodes: WorkflowNode[]; edges: WorkflowEdge[] }) {
  const nodesById = new Map(nodes.map((node) => [node.id, node]));

  return (
    <article className="list-panel">
      <div className="panel-heading">Connections</div>
      {edges.length ? (
        edges.map((edge) => (
          <div className="compact-row connection-row" key={edge.id}>
            <strong>
              {nodeDisplayName(edge.source, nodesById)} → {nodeDisplayName(edge.target, nodesById)}
            </strong>
            <span>{edge.label ? humanize(edge.label) : "Default path"}</span>
          </div>
        ))
      ) : (
        <p className="muted">No connections yet.</p>
      )}
    </article>
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

function humanize(value: string): string {
  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function humanizeEventData(data: Record<string, unknown>): string {
  return Object.entries(data)
    .map(([key, value]) => `${humanize(key)}: ${String(value)}`)
    .join(", ");
}

function parseJsonObject(value: string): Record<string, unknown> {
  const parsed = JSON.parse(value) as unknown;
  if (!parsed || Array.isArray(parsed) || typeof parsed !== "object") {
    throw new Error("Input must be a JSON object");
  }
  return parsed as Record<string, unknown>;
}

function parseJsonObjectError(value: string): string | null {
  try {
    parseJsonObject(value);
    return null;
  } catch {
    return "Input must be valid JSON object, like { \"amount\": 1000 }";
  }
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

function useAutoResetMutation(shouldReset: boolean, reset: () => void) {
  useEffect(() => {
    if (!shouldReset) {
      return;
    }

    const timeoutId = window.setTimeout(reset, 5000);
    return () => window.clearTimeout(timeoutId);
  }, [reset, shouldReset]);
}
