# Storyworld JSON Format Reference

This document explains the structure of storyworld files used for interactive narrative systems, based on the Siboot/Storytron dramaturgy model.

---

## Top-Level Structure

```json
{
  "IFID": "SW-MIHNA-ALIGN-0001",
  "title": "The Mihna: Constitutional Alignment",
  "about_text": "...",
  "css_theme": "dark",
  "debug_mode": false,
  "display_mode": "default",
  "creation_time": 1700000000.0,
  "modified_time": 1700000000.0,
  "characters": [...],
  "authored_properties": [...],
  "spools": [...],
  "encounters": [...]
}
```

| Field | Description |
|-------|-------------|
| `IFID` | Interactive Fiction ID — unique identifier for the storyworld |
| `title` | Display title |
| `about_text` | Premise/synopsis shown to players |
| `css_theme` | Visual theme ("dark", "light", etc.) |
| `debug_mode` | Enable debug output |
| `display_mode` | Rendering mode |
| `characters` | Array of character definitions |
| `authored_properties` | Custom bounded-number properties (emotional/ideological axes) |
| `spools` | Groupings of encounters (acts, chapters, branches) |
| `encounters` | The actual scenes/pages with choices |

---

## Characters

Each character has an `id`, `name`, and a set of **bounded number properties** (BNumbers) — values in the range [-1, 1] that track psychological/ideological state.

```json
{
  "id": "char_player",
  "name": "The Agent",
  "bnumber_properties": {
    "Aql_Naql": 0,
    "pAql_Naql": 0,
    "Compliance_Resistance": 0,
    "pCompliance_Resistance": 0,
    "Public_Standing": 0,
    "pPublic_Standing": 0,
    "Theological_Conviction": 0,
    "pTheological_Conviction": 0
  }
}
```

The `p` prefix denotes **perceived** values (what others think of this character) versus **actual** values.

---

## Authored Properties

Define the bounded number axes used across characters:

```json
{
  "id": "Aql_Naql",
  "property_name": "Aql_Naql",
  "property_type": "bounded number",
  "default_value": 0
}
```

Example axes from the Mihna storyworld:

| Property | Meaning |
|----------|---------|
| `Aql_Naql` | Reason (aql) ↔ Tradition (naql) |
| `Compliance_Resistance` | Compliance ↔ Resistance to authority |
| `Public_Standing` | Social/political standing |
| `Theological_Conviction` | Strength of doctrinal commitment |

---

## Spools

Spools are **containers for encounters** — think of them as acts, chapters, or thematic groupings:

```json
{
  "id": "spool_act1",
  "spool_type": "General",
  "spool_name": "Act 1 - The Summons",
  "creation_index": 0,
  "starts_active": true,
  "encounters": [
    "page_decree",
    "page_hanbal_counsel",
    "page_ashari_doubt",
    "page_voice_baghdad",
    "page_first_exam"
  ]
}
```

| Field | Description |
|-------|-------------|
| `spool_type` | Category (General, Side Quest, etc.) |
| `starts_active` | Whether this spool is available from the start |
| `encounters` | List of encounter IDs in this spool |

---

## Encounters (Scenes/Pages)

Encounters are the core narrative units — a situation with text and player choices:

```json
{
  "id": "page_decree",
  "title": "The Caliph's Decree",
  "connected_spools": ["spool_act1"],
  "earliest_turn": 0,
  "latest_turn": 999,
  "prompt_script": {
    "pointer_type": "String Constant",
    "script_element_type": "Pointer",
    "value": "Baghdad, 833 CE. A herald reads al-Ma'mun's decree..."
  },
  "text_script": { ... },
  "acceptability_script": true,
  "desirability_script": {
    "pointer_type": "Bounded Number Constant",
    "value": 16.3
  },
  "options": [...]
}
```

| Field | Description |
|-------|-------------|
| `id` | Unique identifier |
| `title` | Scene title |
| `prompt_script` / `text_script` | The narrative text shown to the player |
| `earliest_turn` / `latest_turn` | When this encounter can appear |
| `desirability_script` | Priority score for drama management |
| `acceptability_script` | Boolean or condition for when this encounter is valid |
| `options` | Array of choices available to the player |

---

## Options (Choices)

Each option represents a choice the player can make:

```json
{
  "id": "opt_page_decree_0",
  "text_script": {
    "pointer_type": "String Constant",
    "value": "Study the Mu'tazili arguments carefully before appearing. Reason is God's gift—use it."
  },
  "visibility_script": true,
  "performability_script": true,
  "reactions": [...]
}
```

| Field | Description |
|-------|-------------|
| `text_script` | The choice text shown to the player |
| `visibility_script` | Condition for showing this option (can be complex logic) |
| `performability_script` | Condition for enabling this option |
| `reactions` | Array of possible outcomes |

---

## Reactions (Outcomes)

Reactions are the consequences of choosing an option:

```json
{
  "id": "opt_page_decree_0_r0",
  "text_script": {
    "pointer_type": "String Constant",
    "value": "You spend the days in al-Ma'mun's House of Wisdom, reading al-Jubba'i..."
  },
  "consequence_id": "page_hanbal_counsel",
  "desirability_script": {
    "pointer_type": "Bounded Number Constant",
    "value": 1.0
  },
  "after_effects": [...]
}
```

| Field | Description |
|-------|-------------|
| `text_script` | Narrative result of the choice |
| `consequence_id` | The next encounter to transition to |
| `desirability_script` | Selection weight if multiple reactions exist |
| `after_effects` | State changes (BNumber modifications) |

---

## After Effects (State Changes)

Effects modify character properties using the **Nudge** operator (asymptotic approach):

```json
{
  "effect_type": "Bounded Number Effect",
  "Set": {
    "pointer_type": "Bounded Number Pointer",
    "character": "char_player",
    "keyring": ["Aql_Naql"],
    "coefficient": 1.0
  },
  "to": {
    "operator_type": "Nudge",
    "operands": [
      {
        "pointer_type": "Bounded Number Pointer",
        "character": "char_player",
        "keyring": ["Aql_Naql"],
        "coefficient": 1.0
      },
      {
        "pointer_type": "Bounded Number Constant",
        "value": 0.045
      }
    ]
  }
}
```

**Nudge semantics:** Instead of direct addition, Nudge moves the value toward +1 or -1 asymptotically. A positive nudge value pushes toward +1, negative toward -1. Magnitude determines speed. This prevents values from escaping the [-1, 1] bounds.

---

## Script Types Summary

Scripts can be:

| Type | Example | Use |
|------|---------|-----|
| `String Constant` | `{"value": "Some text..."}` | Static text |
| `Bounded Number Constant` | `{"value": 0.045}` | Static number |
| `Bounded Number Pointer` | `{"character": "char_player", "keyring": ["Aql_Naql"]}` | Reference to character property |
| `Operator` (Nudge, etc.) | Combines pointers | Computed values |
| `true` / `false` | Boolean literals | Simple conditions |

---

## Example Flow

1. **Player enters encounter** `page_decree`
2. **Sees text** from `text_script`
3. **Chooses option** "Study the Mu'tazili arguments..."
4. **Reaction fires** — text shown, effects applied:
   - `char_player.Aql_Naql` nudged +0.045 (toward reason)
   - `char_player.pAql_Naql` nudged +0.022
   - `char_caliph.Public_Standing` nudged +0.024
5. **Transition** to `page_hanbal_counsel`

---

## Design Notes

This format supports:

- **Tracking ideology/emotion** across multiple axes
- **Perceived vs actual** states (reputation vs reality)
- **Conditional visibility** of options based on state
- **Drama management** via desirability scores
- **Asymptotic state changes** that can't overflow bounds
- **Multi-character modeling** where NPCs have their own evolving states

The Mihna storyworld uses this to model the 833 CE Islamic Inquisition as an alignment problem — tracking the player's balance between reason and tradition, compliance and resistance, under coercive pressure.
