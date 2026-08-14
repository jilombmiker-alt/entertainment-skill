# Card system

## Runtime model

Keep three layers separate:

1. immutable authored card content from `starter-deck.json`;
2. deterministic draw state: deck version, normalized seed, mode, cycle, history, last family;
3. presentation context: text, AI image, or user photo.

Never put photo contents, participant names, answers, time, location, or account data into the seed.

## Mode contract

| Mode | Draw | Interaction |
|---|---:|---|
| Solo | 1 card | Story first; optional one-question reflection |
| Friends | 1 shared card | Answer, riff, fictionalize, or pass; no scoring |
| Creative | 3-card arc | Opening from Notice/Trace, turn from Crossroads/Weave, afterimage from Voice/Ember |

## Deterministic ranking

Normalize a supplied seed with Unicode NFKC, trim, collapse whitespace, and case-fold. If absent, generate at least 80 random bits once and return a replay code.

Rank each eligible card with SHA-256 over:

```text
storycards/v1
<deck_version>
<normalized_seed>
<mode>
<cycle>
<draw_slot>
<card_id>
```

Sort by `(hash, card_id)`. Never repeat a card until the current eligible pool is exhausted. In a single-card stream, avoid repeating the previous family when another eligible family exists. Never relax a user topic exclusion.

Presentation type must not enter the hash. Switching visuals cannot change the card.

## Controls

- `pass`: consume and advance silently.
- `lighter`: consume and advance within Notice cards.
- `different topic`: add the current topic to exclusions before advancing.
- `another`: consume and advance.
- `show again`: do not consume or run the script.
- `stop`: stop with no pressure.

If exclusions empty the pool, ask whether the user wants to change exclusions or stop. Do not silently re-enable a topic.

## Accessibility

- Pair every glyph with a text label.
- Keep essential text outside generated raster images.
- Supply neutral alt text for every generated image.
- Do not rely on color alone to distinguish families.
- Accept spoken, typed, sketched, one-word, fictional, or no response.
