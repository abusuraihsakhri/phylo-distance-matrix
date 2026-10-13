import test from "node:test";
import assert from "node:assert/strict";
import { parseFasta, calculateMatrix, formatMatrix } from "./app.mjs";

test("reads multiline FASTA and calculates a symmetric matrix", () => {
  const seqs = parseFasta(">A\nACG\nT\n>B\nATGT\n>C\nACGT\n");
  const m = calculateMatrix(seqs, "p");
  assert.equal(m[0][1], .25);
  assert.equal(m[0][2], 0);
  assert.deepEqual(m[0], [0, .25, 0]);
  assert.equal(m[1][0], m[0][1]);
});

test("correct analytic JC69 and K2P", () => {
  const r = parseFasta(">A\nAAAAAAAAAA\n>B\nGAAAAAACAA\n");
  assert.ok(Math.abs(calculateMatrix(r, "jc69")[0][1] + .75 * Math.log(1 - 4 * .2 / 3)) < 1e-12);
  assert.ok(Math.abs(calculateMatrix(r, "k2p")[0][1] + .5 * Math.log(.7) + .25 * Math.log(.8)) < 1e-12);
});

test("pairwise deletion excludes gaps and ambiguous bases", () => {
  const r = parseFasta(">A\nACGN-T\n>B\nATGATT\n");
  assert.equal(calculateMatrix(r)[0][1], .25);
});

test("invalid input and undefined corrected distance are rejected", () => {
  assert.throws(() => parseFasta(">A\nACG\n>B\nAC\n"), /equal in length/);
  assert.throws(() => parseFasta(">A\nAC@\n>B\nACC\n"), /Invalid DNA/);
  assert.throws(() => calculateMatrix(parseFasta(">A\nNN\n>B\nAA\n")), /No comparable/);
  const r = parseFasta(">A\nAAAA\n>B\nTTTT\n");
  assert.throws(() => calculateMatrix(r, "jc69"), /saturation/);
  assert.throws(() => calculateMatrix(r, "k2p"), /saturation/);
});

test("CSV export quotes fields and protects spreadsheet formula identifiers", () => {
  const r = parseFasta('>="danger",x\nAAAA\n>Safe\nAAAA\n');
  const csv = formatMatrix(r, calculateMatrix(r), "csv");
  assert.ok(csv.includes('"\u0027=""danger"",x"'));
  assert.throws(() => formatMatrix(r, calculateMatrix(r), "phylip"), /PHYLIP/);
});
