"use client";

// Monaco served by this app (public/monaco/vs, copied by scripts/copy-monaco.mjs) instead of
// the default jsDelivr CDN: exams must not depend on a third-party CDN.
import Editor, { loader } from "@monaco-editor/react";

loader.config({ paths: { vs: "/monaco/vs" } });

export default Editor;
