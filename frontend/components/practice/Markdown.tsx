import React from "react";

/**
 * Minimal Markdown renderer for problem statements: paragraphs, bullet and
 * numbered lists, fenced code blocks, `inline code`, **bold** and *italic*.
 * Builds React elements directly (never dangerouslySetInnerHTML), so author
 * content cannot inject HTML.
 */
function renderInline(text: string, keyPrefix: string): React.ReactNode[] {
  const nodes: React.ReactNode[] = [];
  const pattern = /(`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*)/g;
  let last = 0;
  let match: RegExpExecArray | null;
  let i = 0;
  while ((match = pattern.exec(text)) !== null) {
    if (match.index > last) nodes.push(text.slice(last, match.index));
    const token = match[0];
    const key = `${keyPrefix}-${i++}`;
    if (token.startsWith("`")) {
      nodes.push(
        <code key={key} className="rounded bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 font-mono text-[0.85em] text-slate-800 dark:text-slate-200">
          {token.slice(1, -1)}
        </code>
      );
    } else if (token.startsWith("**")) {
      nodes.push(<strong key={key} className="font-semibold text-slate-900 dark:text-white">{token.slice(2, -2)}</strong>);
    } else {
      nodes.push(<em key={key}>{token.slice(1, -1)}</em>);
    }
    last = match.index + token.length;
  }
  if (last < text.length) nodes.push(text.slice(last));
  return nodes;
}

export default function Markdown({ source, className = "" }: { source: string; className?: string }) {
  const lines = source.replace(/\r\n/g, "\n").split("\n");
  const blocks: React.ReactNode[] = [];
  let i = 0;
  let k = 0;

  while (i < lines.length) {
    const line = lines[i];
    if (line.trim().startsWith("```")) {
      const code: string[] = [];
      i++;
      while (i < lines.length && !lines[i].trim().startsWith("```")) code.push(lines[i++]);
      i++;
      blocks.push(
        <pre key={k++} className="overflow-x-auto rounded-lg bg-slate-100 dark:bg-slate-800 p-3 font-mono text-sm text-slate-800 dark:text-slate-200">
          {code.join("\n")}
        </pre>
      );
      continue;
    }
    if (/^\s*[-*]\s+/.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^\s*[-*]\s+/.test(lines[i])) items.push(lines[i++].replace(/^\s*[-*]\s+/, ""));
      blocks.push(
        <ul key={k++} className="list-disc space-y-1 pl-6">
          {items.map((it, j) => <li key={j}>{renderInline(it, `ul${k}-${j}`)}</li>)}
        </ul>
      );
      continue;
    }
    if (/^\s*\d+\.\s+/.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^\s*\d+\.\s+/.test(lines[i])) items.push(lines[i++].replace(/^\s*\d+\.\s+/, ""));
      blocks.push(
        <ol key={k++} className="list-decimal space-y-1 pl-6">
          {items.map((it, j) => <li key={j}>{renderInline(it, `ol${k}-${j}`)}</li>)}
        </ol>
      );
      continue;
    }
    if (!line.trim()) {
      i++;
      continue;
    }
    const para: string[] = [];
    while (i < lines.length && lines[i].trim() && !/^\s*([-*]|\d+\.)\s+/.test(lines[i]) && !lines[i].trim().startsWith("```")) {
      para.push(lines[i++]);
    }
    blocks.push(<p key={k++}>{renderInline(para.join(" "), `p${k}`)}</p>);
  }

  return <div className={`space-y-3 leading-relaxed ${className}`}>{blocks}</div>;
}
