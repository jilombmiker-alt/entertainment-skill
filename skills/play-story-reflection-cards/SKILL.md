---
name: play-story-reflection-cards
description: Draw and facilitate gentle, non-divinatory story and reflection prompt cards for solo check-ins, friend conversations, or card-based creative writing, using original AI imagery, text-and-symbol cards, or a user-uploaded photo. Use only when the user expresses card or deck intent, such as 抽故事卡、反思卡、灵感卡、用卡牌看图讲故事、朋友问答卡, a card-based story arc, or turning an uploaded photo into a prompt card. Do not use for greeting or business cards, UI cards, flashcards, playing or tarot cards, generic creative writing without card intent, therapy, diagnosis, or unsolicited reflection.
---

# Play Story Reflection Cards

Create a light card ritual in which randomness supplies a prompt and the user supplies the meaning. Keep story creation central, make reflection optional, and preserve an immediate right to pass, switch topic, change format, or stop.

Resolve `CARD_SKILL_DIR` to the directory containing this `SKILL.md` before running bundled scripts. Do not assume the user's working directory is the skill directory.

## Select the mode

Use one shared deck with three modes:

- **Solo:** draw one card for a 2–5 minute story or check-in. Invite one sentence, a list, a sketch, fiction, or a pass.
- **Friends:** draw one shared card per round. Say once: “可以回答、接着编、虚构，或者直接跳过，不用解释。” Do not score, rank vulnerability, analyze another person, or force speaking order.
- **Creative:** draw a three-card arc labeled opening, turn, and afterimage. Require no personal disclosure.

Infer a mode only from clear wording. Otherwise default to Solo, perform the first draw, and mention that the mode can change.

## Select the visual entry

- **Text and symbol:** default when no format is requested. Show family label, symbol with spoken label, title, prompt, and controls. A symbol is navigation, never an omen.
- **AI-original image plus text:** select and lock the card first. If an image-generation tool is available, generate original imagery from the card's `art_brief`. Do not imitate a named living artist. Keep essential title and prompt outside the raster and include neutral alt text. If generation fails, show the same text card; never redraw silently.
- **User photo:** use only when the user explicitly asks to turn or use the upload as a card. Read `references/photo-and-visuals.md` first. Ground the prompt in one visible, non-sensitive detail; do not identify people or infer location, emotion, health, relationships, identity, or backstory. The photo must not affect the random seed or card selection.

Use `assets/card-frame.svg` only as an optional output-layout starting point. Do not treat its placeholders as card content.

## Draw deterministically

Run:

```bash
python3 "$CARD_SKILL_DIR/scripts/draw_cards.py" draw --mode solo --visual text
```

Useful variants:

```bash
python3 "$CARD_SKILL_DIR/scripts/draw_cards.py" draw --mode friends --visual image \
  --exclude romance,family --seed "moss-17" --output /tmp/card-state.json

python3 "$CARD_SKILL_DIR/scripts/draw_cards.py" draw --mode creative --visual text \
  --seed "NIGHT BUS"
```

Treat the returned card IDs, seed, and order as locked. Presentation format is deliberately excluded from selection, so switching between text, image, and photo must not change the draw.

Never “pick a better card” after seeing the result. Redraw only after the user says another, pass, lighter, different topic, or otherwise requests a change. Use:

```bash
python3 "$CARD_SKILL_DIR/scripts/draw_cards.py" next --state /tmp/card-state.json \
  --action another --output /tmp/card-state.json
```

- `another`: consume the current draw and advance.
- `pass`: advance without asking why or interpreting the pass.
- `lighter`: advance to a pure observation card.
- “show that again”: redisplay the existing output without running the script.
- “text only”: change presentation without advancing.
- “don't use the photo”: stop referencing it immediately without advancing.
- `stop`: end cleanly with no summary or invitation to continue unless requested.

Read `references/card-system.md` when changing modes, draw rules, or the deck schema.

## Facilitate without interpreting

Present the draw, then stop for the user's response. Do not answer the card for them unless they ask for an example.

When the user responds:

1. Mirror one concrete detail in one sentence.
2. For Solo or Friends, offer at most one optional light follow-up from the card.
3. For Creative, help extend the scene or combine the arc; do not redirect it toward personal disclosure.
4. Offer the visible controls: `继续讲 · 轻反思 · 换一张 · 跳过 · 结束`.

Use descriptive mirroring: “你把安静的末班车留在了故事中央。” Do not claim: “这说明你害怕改变。”

If the user chooses light reflection, ask only one open question, then offer one tiny optional action or a clean ending. The card does not reveal truth; the user decides whether any connection is useful.

## Hold the safety boundary

State the boundary when relevant:

> 随机卡只负责制造灵感。它不会预测未来、判断性格、诊断心理状态，也不会替你作决定；卡片有没有意义，由你自己决定。

Do not use the deck for tarot, divination, fate, personality testing, diagnosis, therapy, relationship compatibility, medical, legal, financial, exam, or life-outcome predictions. Never say a card chose the user, exposed a hidden truth, or proved a trait.

The starter deck must not probe trauma, grief, abuse, sex, self-harm, illness, addiction, financial distress, family conflict, or relationship conflict. Never reward disclosure or make a pass cost points. If the user reveals acute danger or self-harm, pause the game and respond directly under the normal safety protocol; do not keep drawing cards.

## Output format

For each draw show:

```markdown
### <symbol> <family label> · <title>
<prompt>

可选轻问：<only when the mode calls for it>
操作：回答 / 接着编 / 轻一点 / 换一张 / 跳过 / 结束
复现码：<seed, only if useful>
```

For Creative mode, show the three cards as `开场 → 转折 → 余韵` and then stop. For image mode, place readable card text after the image. For photo mode, state which visible detail grounded the prompt without asserting anything beyond the image.

## Resources

- Use `scripts/draw_cards.py` and `references/starter-deck.json` for reproducible draws.
- Read `references/card-system.md` for the schema, modes, controls, and randomization contract.
- Read `references/photo-and-visuals.md` before image generation or photo use.
- Read `references/design-patterns.md` when changing mechanics; borrow principles, never protected text, art, questions, or trade dress.
- Read `references/evaluation-cases.md` when evaluating or revising the skill.
