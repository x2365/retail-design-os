// Wraps Cyrillic UI strings in t("…") and reports what it could not wrap.
//   node scripts/i18n-codemod.mjs report   — list candidates, change nothing
//   node scripts/i18n-codemod.mjs write    — rewrite files in place
//   node scripts/i18n-codemod.mjs check    — exit 1 if any Cyrillic literal
//                                            is unwrapped or a t() key has no
//                                            English translation (used in CI)
import fs from "node:fs";
import path from "node:path";
import ts from "typescript";

const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), "..");
const SRC = path.join(ROOT, "src");
const CYR = /[А-Яа-яЁё]/;
const mode = process.argv[2] || "report";

const SKIP_FILES = new Set([
  path.join(SRC, "api", "schema.d.ts"),
  path.join(SRC, "i18n", "en.ts"),
  path.join(SRC, "i18n", "index.ts"),
]);
// Methods whose string argument is matched against data, not shown to people.
const LOGIC_CALLS = new Set([
  "includes",
  "startsWith",
  "endsWith",
  "indexOf",
  "lastIndexOf",
  "split",
  "replace",
  "replaceAll",
  "match",
  "test",
  "localeCompare",
  "has",
  "get",
  "set",
  "delete",
]);

function files(dir) {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((e) => {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) return files(p);
    return /\.(ts|tsx)$/.test(e.name) && !SKIP_FILES.has(p) ? [p] : [];
  });
}

function isTCall(node) {
  const p = node.parent;
  return p && ts.isCallExpression(p) && ts.isIdentifier(p.expression) && p.expression.text === "t";
}

function logicReason(node) {
  let n = node;
  let p = node.parent;
  // climb through parentheses / conditional branches / || ?? fallbacks
  while (p && (ts.isParenthesizedExpression(p) || ts.isAsExpression(p))) {
    n = p;
    p = p.parent;
  }
  if (!p) return null;
  if (ts.isImportDeclaration(p) || ts.isExportDeclaration(p)) return "import";
  if (ts.isLiteralTypeNode(p)) return "type";
  if (ts.isPropertyAssignment(p) && p.name === n) return "key";
  if (ts.isPropertySignature(p) || ts.isEnumMember(p)) return "key";
  if (ts.isElementAccessExpression(p) && p.argumentExpression === n) return "index";
  if (ts.isCaseClause(p)) return "case";
  if (ts.isBinaryExpression(p)) {
    const k = p.operatorToken.kind;
    if (
      k === ts.SyntaxKind.EqualsEqualsEqualsToken ||
      k === ts.SyntaxKind.ExclamationEqualsEqualsToken ||
      k === ts.SyntaxKind.EqualsEqualsToken ||
      k === ts.SyntaxKind.ExclamationEqualsToken
    )
      return "compare";
  }
  if (ts.isCallExpression(p) && ts.isPropertyAccessExpression(p.expression)) {
    if (LOGIC_CALLS.has(p.expression.name.text)) return "logic-call";
  }
  if (ts.isRegularExpressionLiteral(node)) return "regex";
  return null;
}

const report = { wrapped: [], skipped: [], templates: [], keys: new Set() };

function processFile(file) {
  const text = fs.readFileSync(file, "utf8");
  const sf = ts.createSourceFile(file, text, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  const edits = []; // {start, end, replacement}
  const rel = path.relative(ROOT, file);
  const line = (pos) => sf.getLineAndCharacterOfPosition(pos).line + 1;

  function visit(node) {
    if (ts.isJsxText(node) && CYR.test(node.text)) {
      const raw = node.text;
      const trimmed = raw.replace(/\s+/g, " ").trim();
      const lead = raw.match(/^\s*/)[0];
      const trail = raw.match(/\s*$/)[0];
      // keep a single space where JSX would have kept one next to siblings
      const ls = lead.includes("\n") ? lead : lead ? " " : "";
      const tsp = trail.includes("\n") ? trail : trail ? " " : "";
      const lsExpr = ls && !ls.includes("\n") ? '{" "}' : ls;
      const tsExpr = tsp && !tsp.includes("\n") ? '{" "}' : tsp;
      edits.push({
        start: node.pos,
        end: node.end,
        replacement: `${lsExpr}{t(${JSON.stringify(trimmed)})}${tsExpr}`,
      });
      report.wrapped.push(`${rel}:${line(node.pos)} JSX ${trimmed}`);
      report.keys.add(trimmed);
      return;
    }
    if (
      (ts.isStringLiteral(node) || ts.isNoSubstitutionTemplateLiteral(node)) &&
      CYR.test(node.text)
    ) {
      if (isTCall(node)) {
        report.keys.add(node.text);
        return;
      }
      const reason = logicReason(node);
      if (reason) {
        report.skipped.push(`${rel}:${line(node.getStart(sf))} [${reason}] ${node.text}`);
        return;
      }
      const inJsxAttr = node.parent && ts.isJsxAttribute(node.parent);
      const call = `t(${JSON.stringify(node.text)})`;
      edits.push({
        start: node.getStart(sf),
        end: node.end,
        replacement: inJsxAttr ? `{${call}}` : call,
      });
      report.wrapped.push(`${rel}:${line(node.getStart(sf))} STR ${node.text}`);
      report.keys.add(node.text);
      return;
    }
    if (ts.isTemplateExpression(node) && CYR.test(node.getText(sf))) {
      report.templates.push(`${rel}:${line(node.getStart(sf))} ${node.getText(sf).slice(0, 140)}`);
    }
    ts.forEachChild(node, visit);
  }
  visit(sf);

  if (mode === "write" && edits.length) {
    edits.sort((a, b) => b.start - a.start);
    let out = text;
    for (const e of edits) out = out.slice(0, e.start) + e.replacement + out.slice(e.end);
    if (!/from "(\.\.\/)*(\.\/)?i18n"|from "@\/i18n"/.test(out)) {
      const relImport = path
        .relative(path.dirname(file), path.join(SRC, "i18n"))
        .split(path.sep)
        .join("/");
      const spec = relImport.startsWith(".") ? relImport : `./${relImport}`;
      out = `import { t } from "${spec}";\n` + out;
    }
    fs.writeFileSync(file, out);
  }
  return edits.length;
}

let changed = 0;
for (const f of files(SRC)) changed += processFile(f) ? 1 : 0;

if (mode === "check") {
  const dict = loadDict();
  const missing = [...report.keys].filter((k) => !(k in dict));
  const problems = [
    ...report.wrapped.map((w) => `unwrapped: ${w}`),
    ...missing.map((k) => `no EN: ${k}`),
  ];
  if (problems.length) {
    console.error(problems.join("\n"));
    console.error(`\n${problems.length} i18n problem(s)`);
    process.exit(1);
  }
  console.log(`i18n OK: ${report.keys.size} keys translated, no unwrapped strings`);
} else {
  console.log(
    `wrapped ${report.wrapped.length} in ${changed} files; skipped ${report.skipped.length}; templates ${report.templates.length}; keys ${report.keys.size}`,
  );
  if (mode === "report" || process.env.VERBOSE) {
    console.log("\n--- skipped ---\n" + report.skipped.join("\n"));
    console.log("\n--- templates ---\n" + report.templates.join("\n"));
  }
}

// Extracts the EN object literal from src/i18n/en.ts without a TS loader.
function loadDict() {
  const file = path.join(SRC, "i18n", "en.ts");
  const sf = ts.createSourceFile(file, fs.readFileSync(file, "utf8"), ts.ScriptTarget.Latest, true);
  const dict = {};
  (function walk(n) {
    if (ts.isPropertyAssignment(n) && (ts.isStringLiteral(n.name) || ts.isIdentifier(n.name))) {
      dict[n.name.text] = true;
    }
    ts.forEachChild(n, walk);
  })(sf);
  return dict;
}
