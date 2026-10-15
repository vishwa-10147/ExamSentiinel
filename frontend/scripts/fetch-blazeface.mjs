// Downloads the BlazeFace face-detection model into public/models/blazeface so exam pages load
// it from this app instead of tfhub.dev during an exam. The files are committed; re-run only to
// update the model:  node scripts/fetch-blazeface.mjs
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const BASE = "https://tfhub.dev/tensorflow/tfjs-model/blazeface/1/default/1";
const target = join(dirname(fileURLToPath(import.meta.url)), "..", "public", "models", "blazeface");

async function fetchFile(url) {
  const response = await fetch(url, { redirect: "follow" });
  if (!response.ok) throw new Error(`${url}: HTTP ${response.status}`);
  return Buffer.from(await response.arrayBuffer());
}

mkdirSync(target, { recursive: true });
const modelJson = await fetchFile(`${BASE}/model.json?tfjs-format=file`);
const model = JSON.parse(modelJson.toString("utf8"));
writeFileSync(join(target, "model.json"), modelJson);
let total = modelJson.length;
for (const group of model.weightsManifest) {
  for (const path of group.paths) {
    const shard = await fetchFile(`${BASE}/${path}?tfjs-format=file`);
    writeFileSync(join(target, path), shard);
    total += shard.length;
  }
}
console.log(`BlazeFace model saved to public/models/blazeface (${(total / 1024).toFixed(0)} KB)`);
