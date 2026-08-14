# Game engine

## Candidate-place score

Score each candidate from 0–2 on the six dimensions below. Require at least 9/12, with no zero in public access, current confidence, or safety.

| Dimension | 0 | 1 | 2 |
|---|---|---|---|
| Public access | private/restricted | conditional or unclear | clearly public |
| Current confidence | stale/one weak source | recent secondary source | current primary source |
| Safety | material unresolved risk | manageable caveat | ordinary public-space risk |
| Accessibility | unsuitable/unknown | partial with fallback | accessible or equivalent fallback |
| Observability | task needs touching/entry | detail may be unstable | stable exterior detail |
| Story fit | decorative only | supports one beat | changes the plot or choice |

Do not average away a zero in a critical dimension.

## State model

Track:

- `time_remaining`: 0 to initial minutes;
- `energy`: 0–100;
- `budget_remaining`: 0 to initial budget;
- `clues`: non-negative integer;
- `relationship`: -5 to 5;
- `reputation`: -5 to 5;
- `visited`: unique checkpoint IDs;
- `flags`: unique story facts created by choices.

Every choice should change no more than three metrics plus story flags. Avoid fake precision: use small deltas such as 1 clue, ±1 relationship, 5–15 minutes, or 5–15 energy.

## Checkpoint card

```markdown
### 第 N 站 · 地点名
现实锚点：<verified fact + source>
剧情：<80–150 words>
现场任务：<one safe observation>
选择：A / B / optional C
验证：观察题 / 照片 / 位置 / 自报 / 跳过
替代任务：<safe equivalent>
```

## Ending rules

Let the state script choose an ending key. Write an original ending scene around that key:

- `keeper-of-the-map`: at least 3 clues and positive reputation;
- `trusted-companion`: relationship at least 2;
- `last-minute-return`: time is 0 or energy is 10 or lower;
- `unfinished-thread`: all other valid states.

Never assign a “bad person” ending. Low metrics describe this playthrough, not the player.
