// 연결고리 증명 드라이버 — textlint kernel에 ko-saisiot 룰을 직접 주입해 실행.
// 체인: kernel.lintText → ko-saisiot 룰 → kime(kiwi) → messages.
// 사용: node run-textlint.mjs <file.md> [--fix]
import { TextlintKernel } from '@textlint/kernel';
import markdownPlugin from '@textlint/textlint-plugin-markdown';
import { readFileSync } from 'node:fs';
import koSaisiot from './rules/ko-saisiot.mjs';

const interop = (m) => (m && m.default) || m;
const file = process.argv[2];
const fix = process.argv.includes('--fix');
if (!file) { console.error('사용: node run-textlint.mjs <file.md> [--fix]'); process.exit(1); }
const text = readFileSync(file, 'utf8');

const kernel = new TextlintKernel();
const options = {
  filePath: file,
  ext: '.md',
  plugins: [{ pluginId: 'markdown', plugin: interop(markdownPlugin) }],
  rules: [{ ruleId: 'ko-saisiot', rule: koSaisiot }],
};

if (fix) {
  const r = await kernel.fixText(text, options);
  process.stdout.write(r.output);
} else {
  const r = await kernel.lintText(text, options);
  if (!r.messages.length) { console.log('✓ 문제 없음'); process.exit(0); }
  for (const m of r.messages) {
    console.log(`  ${file}:${m.loc.start.line}:${m.loc.start.column}  [${m.ruleId}]  ${m.message}`);
  }
  console.log(`\n총 ${r.messages.length}건`);
}
