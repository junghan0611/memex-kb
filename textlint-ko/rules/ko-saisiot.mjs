// textlint-rule-ko-saisiot — 사이시옷 띄어쓰기 교정 (kime 형태소 검증).
// "초기 값" → "초깃값". 단순 regex가 아니라 kime로 두 토큰이 실제 명사+명사인지
// 확인하므로 "속도가"(조사)·"거리이다"(계사) 오탐이 0이다 — 이것이 연결고리의 요점.
//
// 연결: textlint kernel → 이 룰 → kime(kiwi tokenize) → report/fix.
import { tokenize, isNoun } from '../kime.mjs';

// 띄어쓴 형 → 붙인(사이시옷) 형. 양 채우기는 이후 — 지금은 연결 증명용 최소 집합.
const PAIRS = new Map([
  ['초기 값', '초깃값'],
  ['기대 값', '기댓값'],
  ['최대 값', '최댓값'],
  ['최소 값', '최솟값'],
  ['근사 값', '근삿값'],
  ['함수 값', '함숫값'],
]);

/** 띄어쓴 후보가 kime상 명사+명사인지 확인(오탐 차단). */
async function isNounPair(spaced) {
  const toks = await tokenize(spaced);
  return toks.length >= 2 && isNoun(toks[0].tag) && isNoun(toks[1].tag);
}

const report = function (context) {
  const { Syntax, RuleError, report, getSource, fixer } = context;
  return {
    async [Syntax.Str](node) {
      const text = getSource(node);
      for (const [spaced, fused] of PAIRS) {
        let from = 0;
        let idx;
        while ((idx = text.indexOf(spaced, from)) !== -1) {
          from = idx + spaced.length;
          if (!(await isNounPair(spaced))) continue; // kime 검증
          report(
            node,
            new RuleError(`'${spaced}'은 사이시옷을 붙여 '${fused}'으로 씁니다.`, {
              index: idx,
              fix: fixer.replaceTextRange([idx, idx + spaced.length], fused),
            })
          );
        }
      }
    },
  };
};

export default { linter: report, fixer: report };
