const VARIABLE_PATTERN = /{{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*}}/g;

export function extractTemplateVariables(templateBody: string): string[] {
  const ordered: string[] = [];
  const seen = new Set<string>();

  for (const match of templateBody.matchAll(VARIABLE_PATTERN)) {
    const variable = match[1];
    if (!variable || seen.has(variable)) continue;
    seen.add(variable);
    ordered.push(variable);
  }

  return ordered;
}
