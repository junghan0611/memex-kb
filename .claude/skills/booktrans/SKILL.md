---
name: booktrans
description: "PM/coordinator skill for translating a foreign-language book into Korean for GLG's personal reading and audiobook listening. Discuss the book and division of work with GLG, then sequentially assign exactly one bounded chunk to one fresh Sonnet at a time, review it, close the upstream glossary/meta barrier, and only then open the next worker. Uses ~/repos/3rd/translate-book unchanged; preserves voice and source surface forms; finishes the EPUB before ontology or platform work. Triggers: booktrans, 책 번역, 영어책 번역, 번역 EPUB, 오디오북 번역, translate-book, Why Machines Learn."
user_invocable: true
---

# booktrans — 책을 먼저 끝내는 번역 입구

Repo: `~/repos/gh/memex-kb`.
Implementation: `~/repos/3rd/translate-book` at the recorded upstream pin.
Current work and evidence: memex-kb issue #6.

This is a **PM/coordinator skill**, not a translation engine and not a bulk-agent launcher. The
agent reading it may be Opus, GPT, or another capable model. That agent owns the conversation with
GLG, the work plan, sequential dispatch, review, glossary/meta barriers, and final EPUB acceptance.
It delegates conversion, chunking, glossary/meta feedback, resume state, and EPUB build to upstream,
and delegates each bounded translation unit to a fresh Sonnet.

## Read order

Before translating:

1. `~/repos/gh/memex-kb/PHILOSOPHY.md`, section **두 번째 기둥 — 위대한 저작을 그 숨결로 읽기**.
2. This skill.
3. `~/repos/3rd/translate-book/SKILL.md` in full, then follow its commands.

If these disagree, this skill decides GLG's quality and scope policy; upstream remains the
runtime procedure. Do not patch upstream merely to make the prose agree.

## PM contract — discuss before dispatch

Before opening a translator, talk with GLG and establish:

- which book/source bytes and target language are in scope;
- what already exists and what is real translation versus passthrough output;
- how upstream chunks map to chapters and today's practical stopping point;
- the quality policy, terminology exceptions, and listening target;
- which exact chunk goes to the **first** fresh Sonnet.

Present the plan and current facts before execution. Do not turn “translate this book” into one giant
Sonnet assignment, and do not infer that existing `output_chunk*.md` files are translated without
checking their language/content. The PM remains the routing point throughout the book.

## Goal and stop rule

The immediate goal is a Korean EPUB that GLG can put on his phone and understand by listening.
It does not need to be a literary 99-point translation.

Ask before expanding the work:

> Is this required to finish and listen to the book, or can another owner receive it afterward?

If it is about dictcli tuples, andenken ontology, a general vocabulary platform, a new private
repository, or a universal document model, record/hand off the question and return to the book.
Do not let the long direction prevent today's readable EPUB.

## Hard boundaries

- Use `~/repos/3rd/translate-book` **unmodified**. Do not fork it for this work.
- Do not copy/vendor its scripts into memex-kb.
- Do not rebuild capture, inventory, run-state, merge-meta, or orchestration. The discarded
  `a2edcbc` experiment reached 10,312 added lines and proved that boundary wrong.
- Keep source books and translated bodies out of this PUBLIC repository.
- Never run `git clean -xdf` in upstream while ignored artifacts are the only copy.
- Keep source chunks beside translated chunks so the original is always reachable.

## Translation policy

Use upstream's `glossary.json` v2 and meta workflow as the translation-time interface. Do not
invent a second glossary system before the book is complete.

### Preserve source surface form

A glossary must not silently expand the form chosen by the author.

```text
Frank Rosenblatt       → 프랭크 로젠블랫
Rosenblatt             → 로젠블랫
artificial intelligence → 인공지능
AI                     → AI
```

When a short form or abbreviation needs a different target, remove that form from the canonical
term's `aliases` and represent it as an independent v2 term. A surface form must occur in only one
term, as required by upstream. Run upstream frequency/plan commands after edits; glossary edits
may correctly mark earlier chunks for selective retranslation.

Default rule:

> Preserve the length, abbreviation, and register of the source form. Do not expand a short form
> merely because the glossary knows its canonical entity.

A document-level first-mention expansion is optional and must not be invented by a chunk agent.

### Preserve the author's voice

Pass this intent through upstream's `custom_instructions` slot:

```text
저자의 리듬, 비유, 삽입구, 장난기와 필요한 문장 복잡도를 보존한다. 단지 더 명료하고 간결하게
만들기 위해 문체를 평탄화하지 않는다. 원문의 정식명·약식명·약어 선택을 그대로 보존하며,
약식명이나 약어를 정식명으로 임의 확장하지 않는다.
```

Natural Korean is welcome, but smoothness must not erase the author. Never omit content to make a
sentence simpler.

## Sequential dispatch — one worker, one chunk, one closed barrier

Upstream's default parallel batches are **not** GLG's operating mode. Here, batch size is always 1.
Never launch ten translators because that appears faster. Parallel agents translate against stale
shared terminology, make review pile up, and move the integration burden onto the next context.

The PM repeats this loop:

```text
inspect plan and choose exactly one chunk
→ open one fresh visible Sonnet
→ give only that chunk, the current term table, neighbor context, and this book's policy
→ Sonnet writes exactly one output_chunkNNNN.md and one honest .meta.json
→ Sonnet reports completion to the PM
→ PM compares source/output and checks structure, meaning, terminology, voice, and boundary continuity
→ if PASS, record the output against the glossary actually used
→ prepare-merge → resolve evidence-backed findings → apply-merge
→ inspect the changed glossary and selective-retranslation plan
→ only now open a new fresh Sonnet for the next chunk
```

There is never more than one active translation worker. Do not dispatch the next chunk while the
current output is unreviewed, unrecorded, or has unmerged meta. A failed chunk is corrected or
reassigned before advancing. Human decisions may be shown compactly on one screen, but the
machine barrier still closes after every chunk.

Each Sonnet is a bounded translator, not a long-running book owner. Its assignment is **exactly one
upstream source chunk**. When another chunk is ready, open another fresh Sonnet rather than extending
the previous worker's job.

Keep worker prompts narrow. A translator does not need the whole issue history, the entire book, or
ontology plans. It needs the exact source/output paths, current generated term table, read-only
neighbor excerpt, custom instructions, meta schema, and the requirement to touch no other chunk.
Every dispatch must state:

```text
assignment: chunkNNNN only
read: chunkNNNN + supplied term table + supplied neighbor excerpt
write: output_chunkNNNN.md + output_chunkNNNN.meta.json only
policy: preserve meaning, structure, voice, and source surface form
forbidden: other chunks, glossary mutation, run_state/merge/build, repo code/docs, commit/push
return: paths written + concise uncertainties/conflicts; then stop and wait
```

The PM, never the chunk worker, mutates the glossary, records run state, resolves merge decisions,
and chooses the next assignment.

Use upstream state deliberately: when passthrough `output_chunk*.md` files exist without records,
plan with `--retranslate-untracked` so byte-identical English placeholders are not accepted as
completed translations. Keep meta honest: empty arrays are better than invented entities.

## Acceptance — enough to take home

### Mechanical gate

- Every source chunk has one non-empty translated output.
- Markdown structure, image paths, equations, blockquotes, links, and paragraph ordering survive.
- Empty text links may be removed; image empty-alt syntax such as `![](...)` must survive.
- Glossary/meta/run-state validation passes and no batch feedback is silently left unmerged.
- EPUB is produced and opens on the target phone/player.

### Reading gate

Block completion for:

- omitted content, hallucinated content, or reversed meaning;
- a term drift that changes understanding;
- broken cross-chunk reference or discourse;
- formatting damage that prevents reading/listening.

Do not block the book for isolated awkward tense, particles, or prose that is merely less elegant.
A source-form expansion is major when it damages discourse (for example, making an already
introduced person sound newly introduced); it is minor when it only changes register or rhythm.

The final pass/fail test is a real chapter listened to on the device. `epubcheck` and mechanical
checks are evidence, not the reading verdict.

## Vocabulary recovery — handoff, not ontology work

At a chapter or book barrier, preserve a small handoff from the existing upstream artifacts:

- glossary terms actually used or newly accepted;
- aliases/surface-form decisions;
- conflicts and human decisions with source/chunk evidence;
- book identity and upstream pin.

Deliver this material to the dictcli/andenken owners in a machine-readable form they can consume.
This lane does **not** decide their tuple schema, graph ontology, Denote policy, or ingestion
implementation. It only ensures that translation decisions do not disappear in an ignored temp
directory.

Do not delay an otherwise usable EPUB to design this downstream system. If no durable private
destination has been chosen yet, report the exact artifact paths and preserve them in place.

## Reporting

Report progress in book terms, not framework terms:

```text
translated / total chunks
failed or retried chunks
unresolved consequential decisions
EPUB path and size
phone/listening check status
small vocabulary handoff status
```

Success means: **the book is translated well enough to read or hear, and its vocabulary decisions
can be handed onward.**
