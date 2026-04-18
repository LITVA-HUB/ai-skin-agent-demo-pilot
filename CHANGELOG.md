# Changelog

## v0.6.0

### Added
- Demo auth flow with register / login / forgot-password / logout.
- Account-backed cabinet summaries and profile persistence.
- OpenRouter-backed live LLM path with Gemini 3.1 Flash-Lite Preview routing.
- Cart item decrement and remove controls.
- Cleaner onboarding and advisor copy for the current pilot demo.

### Changed
- Scan, advisor, recommendations, and cabinet were tightened into a more coherent demo flow.
- README now reflects the current run mode, architecture, and recommended demo path.
- Internal smoke checks were updated to match the current OpenRouter configuration.

### Fixed
- Removed stale onboarding artifacts and internal scratch files from the repo.
- Reworked the demo-auth plumbing so the account flow is consistent after refresh.
- Cleaned up a smoke script so it validates the current model/provider setup.

## v0.2.0

### Added
- Expanded beauty scope beyond skincare and complexion:
  - lips
  - eyes
  - cheeks
  - prep / finish products
- New beauty-aware planning modules:
  - intent parsing
  - profile service
  - plan service
  - response service
  - dialog service
- Look-aware recommendation logic:
  - look strategy
  - accent balance
  - focus features
  - look harmony
  - look transformations
- Merchandising and conversion layer:
  - hero-first ordering
  - bundle framing
  - choice simplification
  - cart-minded selling prompts
- New beauty catalog entries and richer metadata
- Expanded test coverage across planner, retrieval, response, conversion, harmony, transformations
- Architecture and product notes:
  - `ARCHITECTURE.md`
  - `BEAUTY_EXPANSION_PLAN.md`
  - `CONVERSION_NOTES.md`

### Changed
- UI simplified into a more consumer-facing flow:
  - upload photo
  - get first recommendation
  - chat naturally with the agent
- Response layer made shorter and more retail-oriented
- Recommendation stack split into more maintainable modules

### Current caveats
- Still a prototype
- Catalog is synthetic/mock
- LLM response discipline is improved but still not fully production-grade
- Some style transformations still need stricter category steering for best commercial behavior
