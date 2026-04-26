import type { RefObject } from "react";
import type { LogEntry } from "../lib/types";

type Props = {
  logs: LogEntry[];
  logEndRef: RefObject<HTMLDivElement | null>;
};

export function ActivitySidebar({ logs, logEndRef }: Props) {
  return (
    <div className="flex flex-col w-80 shrink-0">
      <div className="px-4 py-3 border-b border-gray-800 text-sm font-medium text-gray-400">Agent Activity</div>
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3 font-mono">
        {logs.length === 0 && (
          <p className="text-xs text-gray-600">No activity yet.</p>
        )}
        {logs.map((log, i) => (
          <div key={i} className="text-xs text-gray-400">
            <span className="text-gray-600 mr-2">{log.timestamp}</span>
            {log.content}
          </div>
        ))}
        <div ref={logEndRef} />
      </div>
    </div>
  );
}
