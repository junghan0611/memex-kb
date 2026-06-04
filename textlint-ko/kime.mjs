// kime — Kiwi(C++→WASM) 형태소 분석 싱글톤. textlint 룰들이 공유하는 백엔드.
// 외부 의존: kiwi-nlp(npm, prebuilt wasm) + cong 모델(~/repos/3rd/Kiwi/models/cong/base).
// JVM/emscripten 불요. 초기화 비용이 크므로 싱글톤으로 1회만.
import { KiwiBuilder, Match } from 'kiwi-nlp';
import { readFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

const __dirname = dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);

const MODEL_PATH = process.env.KIWI_MODEL_PATH
  || join(process.env.HOME || '', 'repos/3rd/Kiwi/models/cong/base');
const MODEL_FILES = [
  'combiningRule.txt', 'default.dict', 'extract.mdl', 'multi.dict',
  'sj.morph', 'cong.mdl', 'typo.dict', 'dialect.dict',
];

function wasmPath() {
  // kiwi-nlp dist/kiwi-wasm.wasm — require.resolve로 패키지 위치를 안전하게 찾는다.
  return join(dirname(require.resolve('kiwi-nlp')), 'kiwi-wasm.wasm');
}

let _kiwi = null;
let _initPromise = null;

async function init() {
  const modelFiles = {};
  for (const f of MODEL_FILES) modelFiles[f] = readFileSync(join(MODEL_PATH, f));
  const builder = await KiwiBuilder.create(wasmPath());
  return builder.build({
    modelFiles,
    integrateAllomorph: true,
    loadDefaultDict: true,
    loadTypoDict: true,
    modelType: 'cong',
  });
}

/** Kiwi 인스턴스(싱글톤). 첫 호출만 모델 로드. */
export async function getKiwi() {
  if (_kiwi) return _kiwi;
  if (!_initPromise) _initPromise = init().then((k) => (_kiwi = k));
  return _initPromise;
}

/** 문장 → 토큰 [{form, tag, start, length}]. form=Kiwi str, tag=세종 품사. */
export async function tokenize(text) {
  const kiwi = await getKiwi();
  return kiwi.analyze(text, Match.allWithNormalizing).tokens.map((t) => ({
    form: t.str,
    tag: t.tag,
    start: t.position,
    length: t.length,
  }));
}

export const isNoun = (tag) => tag === 'NNG' || tag === 'NNP';
