"use client";

import { memo } from "react";
import { Handle, Position, NodeProps } from "@xyflow/react";

interface PasswordNodeData {
  id: number;
  value: string;
  redirectUrl: string | null;
  uses: number;
  maxUses: number | null;
  isActive: boolean;
  createdAt: string;
  expiresAt: string | null;
  parentId: number | null;
  isSelected: boolean;
}

function PasswordNode({ data }: NodeProps) {
  const nodeData = data as unknown as PasswordNodeData;
  const { id, value, uses, maxUses, isActive, createdAt, parentId, isSelected } = nodeData;

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString();
  };

  return (
    <div
      className={`
        w-44 p-2.5 font-mono border cursor-pointer relative
        ${isSelected 
          ? "ring-2 ring-foreground ring-offset-2 ring-offset-background" 
          : ""
        }
        ${isActive 
          ? "bg-background border-foreground/40 text-foreground" 
          : "bg-foreground/5 border-dashed border-foreground/20 text-foreground/30"
        }
      `}
    >
      {/* Disabled overlay */}
      {!isActive && (
        <div className="absolute inset-0 bg-background/50 pointer-events-none" />
      )}
      
      <Handle
        type="target"
        position={Position.Top}
        className="!w-1 !h-1 !bg-transparent !border-0 !min-w-0 !min-h-0"
      />

      {/* Header */}
      <div className="flex items-center justify-between mb-1.5 pb-1 border-b border-foreground/20 relative">
        <span className="text-[10px] uppercase tracking-wide text-foreground/60">Password</span>
        {!isActive ? (
          <span className="text-[10px] px-1 py-0.5 bg-foreground/10 text-foreground/50 uppercase tracking-wide">off</span>
        ) : (
          <span className="text-[10px] text-foreground/40">#{id}</span>
        )}
      </div>

      {/* Value */}
      <div className={`text-xs truncate mb-1 relative ${!isActive ? 'line-through decoration-foreground/30' : ''}`} title={value}>
        {value}
      </div>

      {/* Parent reference */}
      {parentId && (
        <div className="text-[10px] text-foreground/40 mb-1.5 relative">
          ↑ site #{parentId}
        </div>
      )}

      {/* Stats */}
      <div className="text-[10px] text-foreground/40 flex justify-between relative">
        <span>{uses}{maxUses ? `/${maxUses}` : ''} uses</span>
        <span>{formatDate(createdAt)}</span>
      </div>

      <Handle
        type="source"
        position={Position.Bottom}
        className="!w-1 !h-1 !bg-transparent !border-0 !min-w-0 !min-h-0"
      />
    </div>
  );
}

export default memo(PasswordNode);
