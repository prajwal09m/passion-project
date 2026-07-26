"use client";

import { clsx } from "clsx";
import type { ReactNode } from "react";

export type Column<T> = {
  key: string;
  header: ReactNode;
  align?: "left" | "right" | "center";
  width?: string; // tailwind width class
  cell?: (row: T, index: number) => ReactNode;
  /** Numeric columns align text-right AND are monospaced automatically. */
  numeric?: boolean;
};

export function DataTable<T extends Record<string, unknown>>({
  rows,
  columns,
  empty,
  rowKey,
  zebra = false,
  maxHeight,
}: {
  rows: T[];
  columns: Column<T>[];
  empty?: ReactNode;
  rowKey?: (row: T, index: number) => string | number;
  zebra?: boolean;
  maxHeight?: string;
}) {
  // Narrowing helper: row-key resolution falls back to the literal `key` field
  // if present, then to row index.
  return (
    <div
      className={clsx("border border-line bg-ink-900", maxHeight && "overflow-auto")}
      style={maxHeight ? { maxHeight } : undefined}
    >
      <table className="data-table">
        <thead>
          <tr>
            {columns.map((c) => (
              <th
                key={c.key}
                className={clsx(
                  c.align === "right" && "text-right",
                  c.align === "center" && "text-center",
                  !c.align && "text-left",
                  c.width
                )}
              >
                {c.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="text-center text-fg-subtle py-6">
                {empty ?? "—"}
              </td>
            </tr>
          ) : (
            rows.map((row, i) => {
              const analyticKey =
                typeof row.key === "string" || typeof row.key === "number"
                  ? row.key
                  : undefined;
              const key = rowKey ? rowKey(row, i) : analyticKey ?? i;
              return (
                <tr
                  key={key}
                  className={clsx(zebra && i % 2 === 1 && "bg-ink-900/40")}
                >
                  {columns.map((c) => (
                    <td
                      key={c.key}
                      className={clsx(
                        c.align === "right" && "text-right num",
                        c.align === "center" && "text-center",
                        !c.align && "text-left",
                        c.numeric && !c.align && "num"
                      )}
                    >
                      {c.cell ? c.cell(row, i) : String(row[c.key] ?? "")}
                    </td>
                  ))}
                </tr>
              );
            })
          )}
        </tbody>
      </table>
    </div>
  );
}
