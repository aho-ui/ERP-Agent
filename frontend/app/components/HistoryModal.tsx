import { X } from "lucide-react";
import type { Tab } from "../lib/types";

type Props = {
  open: boolean;
  closedTabs: Tab[];
  onClose: () => void;
  onRestore: (tab: Tab) => void;
  onDelete: (id: string) => void;
};

export function HistoryModal({ open, closedTabs, onClose, onRestore, onDelete }: Props) {
  if (!open) return null;
  return (
    <div
      className="fixed inset-0 bg-black/60 flex items-center justify-center z-50"
      onClick={onClose}
    >
      <div
        className="bg-gray-900 border border-gray-700 rounded-xl shadow-2xl w-96 max-h-[60vh] flex flex-col"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800">
          <span className="text-sm font-medium text-gray-300">Recently Closed</span>
          <button className="text-gray-500 hover:text-gray-300" onClick={onClose}><X size={16} /></button>
        </div>
        <div className="overflow-y-auto py-1">
          {closedTabs.map(tab => (
            <div key={tab.id} className="flex items-center gap-2 px-4 py-2.5 hover:bg-gray-800 group">
              <button
                className="flex-1 text-left text-sm text-gray-300 truncate"
                onClick={() => onRestore(tab)}
              >
                {tab.label}
              </button>
              <button
                className="text-gray-600 hover:text-red-400 opacity-0 group-hover:opacity-100 shrink-0 transition-colors"
                onClick={() => onDelete(tab.id)}
              >
                <X size={14} />
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
