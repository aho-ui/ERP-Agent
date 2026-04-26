export function renderInline(line: string) {
  const parts = line.split(/(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) return <strong key={i}>{part.slice(2, -2)}</strong>;
    if (part.startsWith("*") && part.endsWith("*")) return <em key={i}>{part.slice(1, -1)}</em>;
    if (part.startsWith("`") && part.endsWith("`")) return <code key={i} className="bg-gray-700 px-1 rounded text-xs font-mono">{part.slice(1, -1)}</code>;
    return <span key={i}>{part}</span>;
  });
}

export function renderMarkdown(text: string) {
  return text.split("\n").map((line, i) => (
    <span key={i}>{i > 0 && <br />}{renderInline(line)}</span>
  ));
}
