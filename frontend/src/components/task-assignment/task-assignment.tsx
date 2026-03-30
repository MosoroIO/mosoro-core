/* ------------------------------------------------------------------ */
/* Task assignment form                                                */
/* ------------------------------------------------------------------ */

import { useState } from "react";
import { api } from "../../services/api";
import type {
  FleetStatusResponse,
  TaskAssignRequest,
  TaskAssignResponse,
} from "../../types/robot";
import { TASK_ACTIONS } from "../../types/robot";

interface TaskAssignmentProps {
  fleetData: FleetStatusResponse | null;
}

interface FormState {
  robot_id: string;
  action: string;
  posX: string;
  posY: string;
  posZ: string;
  parameters: string;
}

const INITIAL_FORM: FormState = {
  robot_id: "",
  action: "",
  posX: "",
  posY: "",
  posZ: "",
  parameters: "",
};

function TaskAssignment({ fleetData }: TaskAssignmentProps) {
  const [form, setForm] = useState<FormState>(INITIAL_FORM);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [result, setResult] = useState<TaskAssignResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const robots = fleetData?.robots.filter((r) => r.is_online) || [];

  function handleChange(
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>,
  ) {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  }

  function buildRequest(): TaskAssignRequest {
    const hasPosition = form.posX || form.posY || form.posZ;

    const request: TaskAssignRequest = {
      robot_id: form.robot_id,
      action: form.action,
    };

    if (hasPosition) {
      request.position = {
        x: parseFloat(form.posX) || 0,
        y: parseFloat(form.posY) || 0,
        z: parseFloat(form.posZ) || 0,
      };
    }

    if (form.parameters.trim()) {
      try {
        request.parameters = JSON.parse(form.parameters);
      } catch {
        throw new Error("Parameters must be valid JSON");
      }
    }

    return request;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setResult(null);

    if (!form.robot_id) {
      setError("Please select a robot.");
      return;
    }

    if (!form.action) {
      setError("Please select an action.");
      return;
    }

    try {
      setIsSubmitting(true);
      const request = buildRequest();
      const response = await api.assignTask(request);
      setResult(response);
      setForm(INITIAL_FORM);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to assign task",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  // Auto-clear feedback after 5 seconds
  if (result || error) {
    setTimeout(() => {
      setResult(null);
      setError(null);
    }, 5000);
  }

  return (
    <div className="mx-auto max-w-2xl animate-fade-in">
      <form onSubmit={handleSubmit} className="card space-y-5">
        <h2 className="text-lg font-semibold text-[var(--color-text-primary)]">
          Assign Task
        </h2>

        {/* Robot selection */}
        <div>
          <label htmlFor="robot_id" className="label">
            Robot
          </label>
          <select
            id="robot_id"
            name="robot_id"
            value={form.robot_id}
            onChange={handleChange}
            className="input"
            required
          >
            <option value="">Select a robot…</option>
            {robots.map((r) => (
              <option key={r.robot_id} value={r.robot_id}>
                {r.robot_id} ({r.vendor} · {r.status || "unknown"})
              </option>
            ))}
          </select>
          {robots.length === 0 && (
            <p className="mt-1 text-xs text-[var(--color-text-muted)]">
              No online robots available.
            </p>
          )}
        </div>

        {/* Action selection */}
        <div>
          <label htmlFor="action" className="label">
            Action
          </label>
          <select
            id="action"
            name="action"
            value={form.action}
            onChange={handleChange}
            className="input"
            required
          >
            <option value="">Select an action…</option>
            {TASK_ACTIONS.map((action) => (
              <option key={action} value={action}>
                {action.replace(/_/g, " ")}
              </option>
            ))}
          </select>
        </div>

        {/* Position (optional) */}
        <fieldset className="space-y-3">
          <legend className="label">
            Position{" "}
            <span className="font-normal text-[var(--color-text-muted)]">
              (optional)
            </span>
          </legend>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label htmlFor="posX" className="sr-only">
                X coordinate
              </label>
              <input
                id="posX"
                name="posX"
                type="number"
                step="any"
                placeholder="X"
                value={form.posX}
                onChange={handleChange}
                className="input"
              />
            </div>
            <div>
              <label htmlFor="posY" className="sr-only">
                Y coordinate
              </label>
              <input
                id="posY"
                name="posY"
                type="number"
                step="any"
                placeholder="Y"
                value={form.posY}
                onChange={handleChange}
                className="input"
              />
            </div>
            <div>
              <label htmlFor="posZ" className="sr-only">
                Z coordinate
              </label>
              <input
                id="posZ"
                name="posZ"
                type="number"
                step="any"
                placeholder="Z"
                value={form.posZ}
                onChange={handleChange}
                className="input"
              />
            </div>
          </div>
        </fieldset>

        {/* Parameters (optional JSON) */}
        <div>
          <label htmlFor="parameters" className="label">
            Parameters{" "}
            <span className="font-normal text-[var(--color-text-muted)]">
              (optional JSON)
            </span>
          </label>
          <textarea
            id="parameters"
            name="parameters"
            value={form.parameters}
            onChange={handleChange}
            className="input min-h-[80px] font-mono text-xs"
            placeholder='{"speed": 1.5, "priority": "high"}'
            rows={3}
          />
        </div>

        {/* Submit */}
        <button
          type="submit"
          disabled={isSubmitting}
          className="btn-primary w-full"
        >
          {isSubmitting ? "Assigning…" : "Assign Task"}
        </button>

        {/* Feedback */}
        {result && (
          <div
            className={`rounded-md p-3 text-sm ${
              result.success
                ? "bg-green-50 text-green-800 dark:bg-green-900/20 dark:text-green-400"
                : "bg-red-50 text-red-800 dark:bg-red-900/20 dark:text-red-400"
            }`}
            role="alert"
          >
            <p className="font-medium">
              {result.success ? "✅ Task assigned" : "❌ Task failed"}
            </p>
            <p className="mt-1">{result.message}</p>
            {result.task_id && (
              <p className="mt-1 font-mono text-xs">
                Task ID: {result.task_id}
              </p>
            )}
          </div>
        )}

        {error && (
          <div
            className="rounded-md bg-red-50 p-3 text-sm text-red-800 dark:bg-red-900/20 dark:text-red-400"
            role="alert"
          >
            ⚠️ {error}
          </div>
        )}
      </form>
    </div>
  );
}

export { TaskAssignment };
