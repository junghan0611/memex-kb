// Phase 0 실측 러너 — 실제 org에 두 룰을 돌린다.
//   룰 A (마침표 뒤 공백): 순수 regex, 결정론적. 형태소 불요.
//   룰 B (인접 명사 띄어쓰기 후보): kime 형태소 — 조사/계사 오탐 0.
// 사용: node check.mjs <file.org>
import { KiwiBuilder, Match } from 'kiwi-nlp';
import { readFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const file = process.argv[2];
if (!file) { console.error('사용: node check.mjs <file.org>'); process.exit(1); }
const text = readFileSync(file, 'utf8');
const lines = text.split('\n');

// ── 룰 A: 문장부호(.?!) 뒤 한글이 공백 없이 붙음 ──────────────
//   수식/약물($...$, =...=)·소수점은 한글 인접이 아니므로 자연 제외.
const RULE_A = /([가-힣][.?!])([가-힣])/g;
const aHits = [];
lines.forEach((ln, i) => {
  for (const m of ln.matchAll(RULE_A)) aHits.push({ line: i + 1, at: `${m[1]}${m[2]}` });
});

// ── 룰 B: kime — 한 칸 띄운 인접 명사쌍(사이시옷/합성어 후보) ──
const MODEL_PATH = process.env.KIWI_MODEL_PATH
  || join(process.env.HOME || '', 'repos/3rd/Kiwi/models/cong/base');
const WASM = join(__dirname, 'node_modules/kiwi-nlp/dist/kiwi-wasm.wasm');
const MODEL_FILES = ['combiningRule.txt', 'default.dict', 'extract.mdl', 'multi.dict', 'sj.morph', 'cong.mdl', 'typo.dict', 'dialect.dict'];
const modelFiles = {};
for (const f of MODEL_FILES) modelFiles[f] = readFileSync(join(MODEL_PATH, f));
const builder = await KiwiBuilder.create(WASM);
const kiwi = await builder.build({ modelFiles, integrateAllomorph: true, loadDefaultDict: true, loadTypoDict: true, modelType: 'cong' });
const isNoun = (t) => t === 'NNG' || t === 'NNP';

// 관심 후보: 특정 사이시옷 쌍만(초기+값 류). 일반 명사쌍 전부는 정상 띄어쓰기라 제외.
const SAISIOT = new Set(['초기 값', '기대 값', '절대 값', '최대 값', '최소 값', '근사 값', '함수 값']);
const bHits = [];
lines.forEach((ln, i) => {
  for (const cand of SAISIOT) {
    if (!ln.includes(cand)) continue;
    // kime로 두 토큰이 실제 명사+명사인지 확인(오탐 차단)
    const toks = kiwi.analyze(cand, Match.allWithNormalizing).tokens;
    if (toks.length >= 2 && isNoun(toks[0].tag) && isNoun(toks[1].tag)) {
      bHits.push({ line: i + 1, at: cand, fix: cand.replace(' ', '').replace(/값$/, '값').replace('초기값', '초깃값') });
    }
  }
});

console.log(`파일: ${file}\n`);
console.log(`■ 룰 A (마침표 뒤 공백): ${aHits.length}곳`);
aHits.slice(0, 8).forEach((h) => console.log(`   L${h.line}  ${h.at}  →  ${h.at[0]}${h.at[1]} ${h.at[2]}`));
if (aHits.length > 8) console.log(`   …외 ${aHits.length - 8}곳`);
console.log(`\n■ 룰 B (kime 사이시옷 후보): ${bHits.length}곳`);
bHits.forEach((h) => console.log(`   L${h.line}  "${h.at}"  →  사이시옷 검토(초깃값 등)`));
