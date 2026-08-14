---
name: run-parallel-city-adventure
description: Create and run a safe, location-grounded real-city parallel-life adventure with verified public places, observation puzzles, optional photo or location checks, branching choices, persistent state, and a closing adventure dossier. Use only when real-world movement is part of 城市寻宝、实景剧情、互动 Citywalk、户外解谜、平行人生体验, or a request to design, play, resume, or adapt a real-city quest. Do not use for ordinary sightseeing itineraries, restaurant lists, pure fiction without real-world movement, or covert location tracking.
---

# Run Parallel City Adventure

Turn a real neighborhood into a bounded interactive story. Ground every route in current public-place evidence, give the player a fictional identity, release one checkpoint at a time, and let choices change the state and ending.

Resolve `CITY_SKILL_DIR` to the directory containing this `SKILL.md` before running bundled scripts. Do not assume the user's working directory is the skill directory.

## Collect the minimum brief

Confirm only information that materially changes the route:

- city or neighborhood and intended start time;
- 45–90 minute target duration, transport mode, and budget;
- solo or group play;
- mobility, accessibility, weather, daylight, and content limits;
- preferred theme, or default to light urban mystery with no horror;
- verification methods the player is comfortable using: observation answer, photo, location share, or self-report.

Offer concise choices when details are missing. Never require photo or location sharing. Let the player change verification method or stop at any checkpoint.

## Build a grounded route

1. Search current sources before proposing real places. Prefer official venue, municipal, transport, and weather sources. Use a second independent source for access details when practical.
2. Separate confirmed facts from story fiction. Cite the sources used for route facts. Never invent a place, entrance, opening time, ticket rule, accessibility feature, distance, or live condition.
3. Choose 4–6 compact checkpoints. Prefer public, observable, daylight-friendly outdoor places with a safe fallback. Avoid private property, restricted areas, construction zones, water edges without barriers, traffic exposure, and isolated late-night segments.
4. Score candidate places using `references/game-engine.md`. Reject a place if public access, current confidence, or safety is weak, even if the story fit is strong.
5. Read `references/location-safety.md` before using photos, location evidence, night routes, weather-sensitive routes, or accessibility claims.
6. For Beijing, read `references/beijing-sample.md` as a design sample, then re-check every location and current condition. The sample is not permission to reuse stale operating information.

## Create the adventure

Build a bounded plot with:

- one fictional identity and one immediate goal;
- three collectible clues or tokens;
- two choices with visible tradeoffs;
- four to six checkpoints connected by one coherent mystery;
- three or four possible endings based on the final state.

Keep the real place factual and the fictional layer clearly labeled. Do not attach invented crimes, scandals, deaths, supernatural claims, or personal allegations to real people or businesses.

Initialize state with:

```bash
python3 "$CITY_SKILL_DIR/scripts/adventure_state.py" new \
  --identity "城市时间修复员" --minutes 75 --budget 100 \
  --verification observation,photo,self-report
```

Preserve the returned JSON during the session. Treat the script as the source of truth for time, energy, budget, clues, relationship, reputation, visited checkpoints, and ending eligibility.

## Run one checkpoint at a time

Present only the current checkpoint:

1. **Destination** — verified public place, simple navigation anchor, and fact source.
2. **Story beat** — 80–150 words connecting the identity to the place.
3. **Field task** — one detail the player can safely observe without touching, entering, purchasing, or disturbing anyone.
4. **Choice** — two or three meaningfully different actions with no hidden “correct” moral answer.
5. **Verification menu** — every method supported here, including a no-upload option.
6. **Fallback** — an equivalent nearby or remote task if the place is closed, crowded, inaccessible, unsafe, or uncomfortable.

Do not reveal later checkpoints or solve the observation task before the player responds. Accept “skip,” “change verification,” “pause,” and “end” immediately.

After a player action, update state with `$CITY_SKILL_DIR/scripts/adventure_state.py update`. Apply only changes caused by the stated choice; do not secretly rewrite earlier values. Show a short state delta, not the full internal plot.

Adapt the next checkpoint to remaining time, energy, budget, weather, accessibility, and the player's last choice. Shorten safely rather than rushing the player.

## Verify evidence honestly

- **Observation answer:** compare only with a freshly verified, stable visual feature. Allow ambiguity caused by renovation or crowds.
- **Photo:** ask for consent each time. Recommend avoiding faces, children, license plates, house numbers, tickets, and other identifiers. Analyze only what is needed for the task.
- **Location:** use only a location the player voluntarily shares. Never claim GPS verification if no location-capable tool was actually used, and never retain or repeat precise coordinates unnecessarily.
- **Self-report:** accept it without shaming or reducing the quality of the story.

State exactly what was and was not verified. “The player reported arrival” is different from “the photo shows the target feature.”

## Finish with an adventure dossier

Run:

```bash
python3 "$CITY_SKILL_DIR/scripts/adventure_state.py" ending --state <state.json>
```

Return:

- ending title and a 150–250 word ending scene;
- the three most consequential choices and their state effects;
- collected clues and unresolved thread;
- a compact “parallel-life identity card”;
- one optional replay hook using a different identity or route branch;
- a source note for real-world facts, separated from fiction.

Do not turn the ending into a personality diagnosis or prediction about the player's real life.

## Stop and redirect

Stop or redesign the route when current safety, access, or location truth cannot be established. Never instruct trespass, confrontation, deception of staff, risky stunts, purchases, alcohol use, or interaction with strangers as a condition of success. For emergencies, tell the player to stop the game, move to a safe public place, and contact local emergency services or a trusted person.

## Resources

- Read `references/game-engine.md` for route scoring, checkpoint structure, and ending rules.
- Read `references/location-safety.md` for live verification, privacy, accessibility, and fallback rules.
- Read `references/beijing-sample.md` only for the Beijing golden-path example.
- Read `references/design-patterns.md` when changing the game mechanics; borrow principles, never text, art, puzzles, or proprietary content.
- Read `references/evaluation-cases.md` when evaluating or revising the skill.
- Use `scripts/adventure_state.py` for deterministic state changes and validation.
