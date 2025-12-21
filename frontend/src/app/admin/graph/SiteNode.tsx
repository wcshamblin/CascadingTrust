"use client";

import { memo } from "react";
import { Handle, Position, NodeProps } from "@xyflow/react";

interface SiteNodeData {
  id: number;
  value: string;
  redirectUrl: string;
  uses: number;
  maxUses: number | null;
  isActive: boolean;
  createdAt: string;
  expiresAt: string | null;
  isSelected: boolean;
}

function SiteNode({ data }: NodeProps) {
  const nodeData = data as unknown as SiteNodeData;
  const { id, value, redirectUrl, uses, maxUses, isActive, createdAt, isSelected } = nodeData;

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString();
  };

  return (
    <div
      className={`
        w-44 p-2.5 font-mono cursor-pointer
        ${isSelected 
          ? "ring-2 ring-foreground ring-offset-2 ring-offset-background" 
          : ""
        }
        ${isActive 
          ? "bg-foreground text-background" 
          : "bg-background text-foreground/30 border border-foreground/20"
        }
      `}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-1.5 pb-1 border-b border-current opacity-30">
        <span className="text-[10px] uppercase tracking-wide">Site</span>
        <span className="text-[10px]">#{id}</span>
      </div>

      {/* Name */}
      <div className="text-xs font-medium truncate mb-1" title={value}>
        {value}
      </div>

      {/* URL */}
      <div className={`text-[10px] truncate mb-1.5 ${isActive ? 'opacity-60' : 'opacity-40'}`} title={redirectUrl}>
        → {redirectUrl}
      </div>

      {/* Stats */}
      <div className={`text-[10px] flex justify-between ${isActive ? 'opacity-60' : 'opacity-40'}`}>
        <span>{uses}{maxUses ? `/${maxUses}` : ''} uses</span>
        <span>{formatDate(createdAt)}</span>
      </div>

      {/* Status indicator */}
      {!isActive && (
        <div className="text-[10px] mt-1 text-foreground/40">inactive</div>
      )}

      <Handle
        type="source"
        position={Position.Bottom}
        className="!w-1 !h-1 !bg-transparent !border-0 !min-w-0 !min-h-0"
      />
    </div>
  );
}

export default memo(SiteNode);
