// Copies the Monaco editor from node_modules into public/monaco/vs so the app serves it itself.
// By default @monaco-editor/react loads Monaco from cdn.jsdelivr.net at runtime: an exam would
// then depend on a third-party CDN being reachable from the exam network, and the page could not
// use a strict Content-Security-Policy. Runs before `next dev` and `next build` (package.json).
import { cpSync, existsSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const source = join(root, "node_modules", "monaco-editor", "min", "vs");
const target = join(root, "public", "monaco", "vs");
const version = JSON.parse(readFileSync(join(root, "node_modules", "monaco-editor", "package.json"), "utf8")).version;
const stamp = join(target, ".version");

if (!existsSync(join(source, "loader.js"))) {
  console.error("monaco-editor is not installed (expected node_modules/monaco-editor/min/vs/loader.js)");
  process.exit(1);
}
if (existsSync(stamp) && readFileSync(stamp, "utf8") === version) {
  process.exit(0); // already copied
}
rmSync(target, { recursive: true, force: true });
cpSync(source, target, { recursive: true });
cpSync(join(root, "node_modules", "monaco-editor", "package.json"), join(target, "..", "package.json"));
writeFileSync(stamp, version);
console.log(`Monaco ${version} copied to public/monaco/vs`);
