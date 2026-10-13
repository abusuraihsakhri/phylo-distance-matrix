// Dependency-free browser implementation of the aligned-DNA distance models.
// Keep the mathematical rules synchronized with distance_matrix.py.
const DNA = new Set(["A", "C", "G", "T"]);
const ALLOWED = new Set("ACGTRYSWKMBDHVN-.?");
const TRANSITIONS = new Set(["AG", "GA", "CT", "TC"]);

export function parseFasta(text) {
  if (typeof text !== "string") throw new Error("FASTA input must be text.");
  const records = [];
  let name = null;
  let chunks = [];
  const lines = text.replace(/^\uFEFF/, "").split(/\r?\n/);
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    if (!line) continue;
    if (line.startsWith(">")) {
      if (name !== null) records.push({ name, sequence: chunks.join("") });
      name = line.slice(1).trim();
      if (!name) throw new Error("Empty FASTA identifier on line " + (i + 1) + ".");
      chunks = [];
    } else {
      if (name === null) throw new Error("Sequence before first FASTA header on line " + (i + 1) + ".");
      const seq = line.toUpperCase();
      for (const ch of seq) {
        if (!ALLOWED.has(ch)) throw new Error("Invalid DNA symbol '" + ch + "' on line " + (i + 1) + ".");
      }
      chunks.push(seq);
    }
  }
  if (name !== null) records.push({ name, sequence: chunks.join("") });
  validate(records);
  return records;
}

function validate(records) {
  if (records.length < 2) throw new Error("At least two FASTA sequences are required.");
  const names = records.map((r) => r.name);
  if (new Set(names).size !== names.length) throw new Error("FASTA identifiers must be unique.");
  const lengths = new Set(records.map((r) => r.sequence.length));
  if (lengths.size !== 1 || lengths.has(0)) throw new Error("Sequences must be aligned, non-empty and equal in length.");
}

export function calculateMatrix(records, model = "p") {
  if (!["p", "jc69", "k2p"].includes(model)) throw new Error("Unknown distance model.");
  validate(records);
  const matrix = Array.from({ length: records.length }, () => Array(records.length).fill(0));
  for (let i = 0; i < records.length; i++) {
    for (let j = i + 1; j < records.length; j++) {
      let transitions = 0, transversions = 0, sites = 0;
      const a = records[i].sequence, b = records[j].sequence;
      for (let k = 0; k < a.length; k++) {
        if (!DNA.has(a[k]) || !DNA.has(b[k])) continue;
        sites++;
        if (a[k] !== b[k]) {
          if (TRANSITIONS.has(a[k] + b[k])) transitions++;
          else transversions++;
        }
      }
      const pair = records[i].name + " / " + records[j].name;
      if (!sites) throw new Error("No comparable A/C/G/T positions for " + pair + ".");
      const p = (transitions + transversions) / sites;
      let value;
      if (model === "p") value = p;
      else if (model === "jc69") {
        const term = 1 - 4 * p / 3;
        if (term <= 0) throw new Error("JC69 distance undefined (saturation) for " + pair + ".");
        value = -0.75 * Math.log(term);
      } else {
        const P = transitions / sites, Q = transversions / sites;
        const x = 1 - 2 * P - Q, y = 1 - 2 * Q;
        if (x <= 0 || y <= 0) throw new Error("K2P distance undefined (saturation) for " + pair + ".");
        value = -0.5 * Math.log(x) - 0.25 * Math.log(y);
      }
      matrix[i][j] = matrix[j][i] = value;
    }
  }
  return matrix;
}

function csvEscape(value, delimiter) {
  const s = String(value);
  return /["\r\n]/.test(s) || s.includes(delimiter) ? '"' + s.replace(/"/g, '""') + '"' : s;
}
function safeName(s) {
  return /^[\s]*[=+\-@]/.test(s) ? "'" + s : s;
}
export function formatMatrix(records, matrix, format = "csv") {
  const names = records.map((r) => r.name);
  if (!["csv", "tsv", "phylip"].includes(format)) throw new Error("Unknown output format.");
  if (matrix.length !== names.length || matrix.some((r) => r.length !== names.length)) throw new Error("Invalid matrix dimensions.");
  if (format === "phylip") {
    if (names.some((s) => s.length > 10 || /\s/.test(s))) {
      throw new Error("PHYLIP identifiers must have at most 10 characters and no spaces; use CSV for longer names.");
    }
    return names.length + "\n" + names.map((n, i) => n.padEnd(10) + " " + matrix[i].map((v) => v.toFixed(10)).join(" ")).join("\n") + "\n";
  }
  const sep = format === "csv" ? "," : "\t";
  const rows = [["taxon", ...names.map(safeName)]];
  matrix.forEach((row, i) => rows.push([safeName(names[i]), ...row.map((v) => v.toFixed(10))]));
  return rows.map((row) => row.map((x) => csvEscape(x, sep)).join(sep)).join("\n") + "\n";
}

if (typeof document !== "undefined") {
  const input = document.getElementById("alignment");
  const file = document.getElementById("file");
  const model = document.getElementById("model");
  const message = document.getElementById("message");
  const result = document.getElementById("result");
  const stats = document.getElementById("stats");
  const buttons = [document.getElementById("csv"), document.getElementById("phylip")];
  let current = null;
  const sample = ">Alpha\nACGTACGTACGT\n>Beta\nACGTACGTTCGT\n>Gamma\nACGTTCGTACGT\n>Delta\nACGTACGTACTT\n";

  function clear() {
    current = null;
    buttons.forEach((b) => { b.disabled = true; });
    result.replaceChildren();
    stats.textContent = "No matrix computed";
  }
  function notice(text, error = false) {
    message.textContent = text;
    message.className = error ? "message error" : "message";
  }
  document.getElementById("sample").addEventListener("click", () => {
    input.value = sample;
    file.value = "";
    clear();
    notice("Example alignment loaded. Select a model and calculate.");
  });
  input.addEventListener("input", () => { clear(); notice(""); });
  model.addEventListener("change", () => { clear(); notice(""); });
  file.addEventListener("change", async () => {
    clear();
    if (!file.files.length) return;
    const f = file.files[0];
    if (f.size > 2 * 1024 * 1024) { notice("File exceeds the 2 MB browser limit.", true); return; }
    try {
      input.value = await f.text();
      notice("Loaded " + f.name + ". Calculate to generate the matrix.");
    } catch (e) { notice("Unable to read file: " + e.message, true); }
  });

  document.getElementById("calculate").addEventListener("click", () => {
    clear();
    try {
      const records = parseFasta(input.value);
      if (records.length > 100) throw new Error("Browser limit: 100 taxa.");
      if (records[0].sequence.length > 100000) throw new Error("Browser limit: 100,000 aligned columns.");
      const matrix = calculateMatrix(records, model.value);
      const table = document.createElement("table");
      const caption = document.createElement("caption");
      caption.textContent = model.options[model.selectedIndex].text + " · pairwise deletion of gaps and ambiguous bases";
      table.append(caption);
      const thead = document.createElement("thead");
      const header = document.createElement("tr");
      ["Taxon", ...records.map((r) => r.name)].forEach((name) => {
        const th = document.createElement("th");
        th.textContent = name;
        th.scope = "col";
        header.append(th);
      });
      thead.append(header);
      table.append(thead);
      const tbody = document.createElement("tbody");
      matrix.forEach((row, i) => {
        const tr = document.createElement("tr");
        const th = document.createElement("th");
        th.scope = "row";
        th.textContent = records[i].name;
        tr.append(th);
        row.forEach((value) => {
          const td = document.createElement("td");
          td.textContent = value.toFixed(6);
          tr.append(td);
        });
        tbody.append(tr);
      });
      table.append(tbody);
      result.append(table);
      stats.textContent = records.length + " taxa · " + records[0].sequence.length + " sites · " + (records.length * (records.length - 1) / 2) + " comparisons";
      current = { records, matrix };
      buttons.forEach((b) => { b.disabled = false; });
      notice("Distance matrix calculated locally. No sequences were uploaded.");
    } catch (e) { notice(e.message, true); }
  });

  function download(format) {
    if (!current) return;
    try {
      const content = formatMatrix(current.records, current.matrix, format);
      const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "phylo-distances." + (format === "phylip" ? "phy" : format);
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      notice("Exported " + a.download + ".");
    } catch (e) { notice(e.message, true); }
  }
  document.getElementById("csv").addEventListener("click", () => download("csv"));
  document.getElementById("phylip").addEventListener("click", () => download("phylip"));
  clear();
  notice("Paste aligned DNA FASTA or load the example to begin.");
}
