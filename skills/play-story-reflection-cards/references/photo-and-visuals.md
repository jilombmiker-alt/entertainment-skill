# Photo and visual rules

## AI-original entry

1. Draw and lock the card before generating.
2. Convert only the authored `art_brief` into an image prompt.
3. Request an original editorial illustration or collage with no logo, watermark, embedded prompt text, or imitation of a named living artist.
4. Keep title and prompt as selectable text below the image.
5. Add neutral alt text describing composition, objects, and colors without psychological interpretation.
6. If the image tool fails or is unavailable, show the same text-and-symbol card.

## Text-and-symbol entry

Show, in order: family label, glyph and spoken label, title, prompt, optional follow-up, controls. Use `assets/card-frame.svg` only when a standalone visual file is requested.

## User-photo entry

Use the upload only after an explicit request such as “把这张照片做成故事卡.” Ask no extra consent if that request is already clear.

Ground the prompt in visible objects, color, light, shape, texture, framing, or composition. State the chosen anchor factually. Do not:

- identify or search for a person;
- guess a location, date, event, ownership, emotion, intention, relationship, occupation, health, disability, ethnicity, religion, sexuality, finances, or legal status;
- transcribe or repeat private messages, IDs, addresses, tickets, or screens;
- invent a factual backstory;
- store photo content in the seed or deck state;
- modify the photo or generate likeness variations unless separately requested.

When the user explicitly asks to make the upload itself the card face, place the original image inside the `assets/card-frame.svg` image area or show it immediately above the selectable card text. Preserve the image content; crop, recolor, retouch, or stylize only when the user separately requests that edit. Never place the only readable prompt inside the image.

If the visible content is too sensitive or identifying, offer a text-only card using a user-chosen neutral word instead.
