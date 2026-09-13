# Urgency policy

Use the highest level directly supported by facts. Do not invent impact or immediacy.

- **U-P0-1 — P0_critical:** active or imminent severe harm needing immediate response,
  including active unauthorized disclosure, confirmed takeover in progress,
  widespread production outage, or irreversible data loss underway.
- **U-P1-1 — P1_high:** serious blocked work or high-impact degradation that does not
  meet P0, including an enterprise production workflow blocked without a workaround,
  repeated payment failure preventing service, or many users substantially affected.
- **U-P2-1 — P2_normal:** ordinary actionable support work, such as a single-user
  defect with a workaround, invoice correction, or routine access problem.
- **U-P3-1 — P3_low:** non-blocking improvements and informational requests, including
  feature requests, documentation suggestions, and cosmetic issues.

## Non-signals and tie-breaking

- **U-DEC-1:** words such as “urgent,” capitalization, anger, punctuation, and repeated
  requests do not raise urgency without impact facts.
- **U-DEC-2:** enterprise tier alone does not raise urgency. It matters only when an
  enterprise production workflow is actually blocked as described by U-P1-1.
- **U-TIE-1:** when facts support several levels, select the highest supported level.
  When key impact facts are absent, select the level supported by known facts rather
  than assuming the worst.
