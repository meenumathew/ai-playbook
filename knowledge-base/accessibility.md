---
id: accessibility
size: small
tldr: For UI changes, check the accessible basics (semantic HTML, alt text, keyboard/focus, contrast, labels, ARIA) at review time; skip entirely for non-UI code.
load_when: accessibility, a11y, WCAG, screen reader, keyboard navigation, alt text, ARIA, color contrast, focus, form label, semantic HTML
audience: all
canonical_for: accessibility review checklist, when accessibility applies
cross_refs: CHEATSHEET.md
verified: 2026-07-17
---

# Accessibility

Accessibility (a11y) is a review dimension for **UI changes only**: HTML templates, components (React/Vue/Svelte), pages, or anything rendering to a browser DOM. `diff-reviewer` runs this check only when the diff touches a UI surface (§ When it applies). The goal is the checkable baseline that catches the common, high-impact failures, not a full WCAG audit (§ Deeper audit).

## Agent Use

- **Read first:** When it applies, Review checklist.
- **Load deeper only on trigger:** the audit note, only for a large new UI surface.

---

## When it applies

Run the checklist when the diff adds or changes rendered markup: templates, components, pages, or DOM-producing code. Skip it for API handlers, CLI, infra/CDK, data pipelines, tests, and docs. If unsure whether a change is user-facing UI, ask before flagging.

## Review checklist

Findings map to the standard severity: a barrier that blocks a user (no keyboard access, missing form label, image conveying meaning with no alt text) is **Must Fix**; a degraded-but-usable issue is **Should Fix**.

- **Semantic HTML.** Native elements for their purpose: `button` for actions, `a` for navigation, `label` bound to inputs, headings in order. A `div` with a click handler is a Must Fix when a `button` would do.
- **Text alternatives.** Meaningful images have `alt` describing the content; decorative images have empty `alt=""`. Icon-only buttons carry an accessible name (`aria-label` or visually-hidden text).
- **Keyboard and focus.** Every interactive element is reachable and operable by keyboard, focus order is logical, and focus is visible. No keyboard traps. Custom widgets manage focus deliberately.
- **Forms.** Every input has an associated `label`; error messages are programmatically linked (`aria-describedby`) and not conveyed by color alone.
- **Color and contrast.** Text meets the contrast baseline (WCAG AA: 4.5:1 body, 3:1 large); information is never conveyed by color alone (pair with text or icon).
- **ARIA as a last resort.** Prefer native semantics; add ARIA only when native HTML cannot express the pattern, and keep roles/states accurate. Wrong ARIA is worse than none.

## Deeper audit

For a large new UI surface, recommend (as a follow-up task, not a review blocker) an automated pass (axe-core / Lighthouse) plus manual keyboard and screen-reader testing. Note it in the review; do not attempt a full audit inside a diff review.
