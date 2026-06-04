// Phase 0 프로브 — kiwi-nlp(WASM, cong 모델)가 memex-kb nix shell에서 도는지 +
// 형태소 분별이 "명사+조사 오탐 0"을 주는지 눈으로 확인.
//
// 모델: ~/repos/3rd/Kiwi/models/cong/base (KIWI_MODEL_PATH로 재정의 가능)
// wasm: node_modules/kiwi-nlp/dist/kiwi-wasm.wasm
import { KiwiBuilder, Match } from 'kiwi-nlp';
import { readFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const MODEL_PATH = process.env.KIWI_MODEL_PATH
  || join(process.env.HOME || '', 'repos/3rd/Kiwi/models/cong/base');
const WASM = join(__dirname, 'node_modules/kiwi-nlp/dist/kiwi-wasm.wasm');
const MODEL_FILES = [
  'combiningRule.txt', 'default.dict', 'extract.mdl', 'multi.dict',
  'sj.morph', 'cong.mdl', 'typo.dict', 'dialect.dict',
];

const modelFiles = {};
for (const f of MODEL_FILES) modelFiles[f] = readFileSync(join(MODEL_PATH, f));

const builder = await KiwiBuilder.create(WASM);
console.log(`[kime] kiwi-wasm ${builder.version()}, cong 모델 ${Object.keys(modelFiles).length}개 로드`);
const kiwi = await builder.build({
  modelFiles,
  integrateAllomorph: true,
  loadDefaultDict: true,
  loadTypoDict: true,
  modelType: 'cong',
});

const fmt = (s) => kiwi.analyze(s, Match.allWithNormalizing)
  .tokens.map((t) => `${t.str}/${t.tag}`).join(' ');

// 사이시옷 규칙 후보: 인접 두 명사(NNG/NNP)면 매칭. 형태소 없이 regex만이면
// "거리이다.속도"의 "거리" 다음을 명사로 오인하거나, "속도가"의 가를 못 거른다.
const isNoun = (t) => t === 'NNG' || t === 'NNP';
function adjacentNouns(s) {
  const toks = kiwi.analyze(s, Match.allWithNormalizing).tokens;
  const hits = [];
  for (let i = 0; i < toks.length - 1; i++) {
    if (isNoun(toks[i].tag) && isNoun(toks[i + 1].tag)) {
      hits.push(`${toks[i].str}+${toks[i + 1].str}`);
    }
  }
  return hits;
}

const cases = [
  ['초기 값', '명사+명사 → 사이시옷 후보(초깃값) 잡아야'],
  ['속도가 빨라진다', '속도/NNG + 가/JKS → 조사라 명사쌍 아님(오탐 0)'],
  ['거리이다.', '거리/NNG + 이다 계사 → 명사쌍 아님(오탐 0)'],
  ['최대 속도', '명사+명사 → 후보'],
  ['초기 조건', '명사+명사 → 후보(초깃값과 달리 조건은 받침이라 별개지만 POS는 동일)'],
];

console.log('\n=== 토큰화 ===');
for (const [s] of cases) console.log(`  ${s.padEnd(16)} → ${fmt(s)}`);

console.log('\n=== 인접 명사쌍(사이시옷 1차 후보) ===');
for (const [s, why] of cases) {
  const hits = adjacentNouns(s);
  console.log(`  ${s.padEnd(16)} ${hits.length ? '✔ ' + hits.join(', ') : '· 없음'}   (${why})`);
}
