import { Check, X, Clock, CheckCircle2, XCircle } from "lucide-react";
import type { PendingAction } from "../lib/types";

type Props = {
  action: PendingAction;
  status?: "pending" | "confirmed" | "cancelled";
  loading?: boolean;
  onConfirm: (action: PendingAction) => void;
  onCancel: (action: PendingAction) => void;
};

export function PendingActionCard({ action, status = "pending", loading, onConfirm, onCancel }: Props) {
  const isResolved = status !== "pending";
  const headerColor =
    status === "confirmed" ? "text-green-500"
    : status === "cancelled" ? "text-gray-500"
    : "text-yellow-500";
  const borderColor =
    status === "confirmed" ? "border-green-900/40"
    : status === "cancelled" ? "border-gray-800"
    : "border-yellow-800/50";
  const StatusIcon =
    status === "confirmed" ? CheckCircle2
    : status === "cancelled" ? XCircle
    : Clock;
  const statusLabel =
    status === "confirmed" ? "Confirmed"
    : status === "cancelled" ? "Cancelled"
    : (action.agent_name || "Awaiting Confirmation");

  return (
    <div className={`border ${borderColor} rounded-lg overflow-hidden bg-gray-900 max-w-md`}>
      <div className={`px-3 pt-2.5 pb-2 border-b ${borderColor} flex items-center gap-2`}>
        <StatusIcon size={12} className={headerColor} />
        <p className={`text-[10px] font-mono ${headerColor} uppercase tracking-widest`}>{statusLabel}</p>
      </div>
      {action.summary && (
        <div className="px-3 pt-2 pb-1">
          <p className="text-xs text-gray-300 leading-relaxed">{action.summary}</p>
        </div>
      )}
      {action.details && Object.keys(action.details).length > 0 && (
        <div className="px-3 py-2 space-y-1.5">
          {Object.entries(action.details).map(([k, v]) => (
            <div key={k} className="flex justify-between items-center gap-3">
              <span className="text-[10px] text-gray-500 font-mono capitalize">{k.replace(/_/g, " ")}</span>
              <span className="text-[11px] text-gray-200 font-mono text-right">{String(v)}</span>
            </div>
          ))}
        </div>
      )}
      {!isResolved && (
        <div className={`flex border-t ${borderColor}`}>
          <button
            className={`flex-1 px-2 py-1.5 text-xs text-gray-500 hover:text-gray-300 hover:bg-gray-800 transition-colors border-r ${borderColor} flex items-center justify-center gap-1.5`}
            onClick={() => onCancel(action)}
            disabled={loading}
          >
            <X size={12} /> Cancel
          </button>
          <button
            className="flex-1 px-2 py-1.5 text-xs text-green-400 hover:bg-green-900/30 transition-colors flex items-center justify-center gap-1.5"
            onClick={() => onConfirm(action)}
            disabled={loading}
          >
            <Check size={12} /> Confirm
          </button>
        </div>
      )}
    </div>
  );
}
