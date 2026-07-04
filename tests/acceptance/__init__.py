"""Acceptance test package.

================================================================
Phrase-pin classification convention
================================================================

When an acceptance test asserts on the *contents* of a markdown file
(agent prompt, skill, KB article, CHANGELOG, README, template), label
the assertion with one of three classification labels so future maintainers
can decide whether a copy-edit needs to update the test or not:

  # CONTRACT-PHRASE: <why this exact wording is the contract>
      The literal phrase IS the contract — change the file and you
      change what users see. Example: the commit-prompt sentence
      `Changes staged. Say 'commit' to proceed.` (canonical in
      CLAUDE.md, mirrored to README walkthrough and eval samples).
      A copy-edit that changes this phrase is a behaviour change.

  # STRUCTURE-MARKER: <why this presence-check matters>
      The test only requires that *something with this shape*
      exists — a heading, a section, a frontmatter key, a citation
      target. Wording inside is free to change.
      Example: `assert "## Sanitization" in skill` requires the
      heading to exist, not its body wording.

  # ACCIDENTAL-PIN: <how to loosen>
      The test happens to assert on a phrase that is not actually
      load-bearing. Loosen to a substring, regex, or structural
      check at the next opportunity. New ACCIDENTAL-PIN labels
      should not be introduced.

Assertions on `result.output` from Typer's CliRunner are CLI surface
contracts, not phrase pins on documents — they do not need this
labelling.

The classification is documented in CONTRIBUTING.md § Testing.
"""
