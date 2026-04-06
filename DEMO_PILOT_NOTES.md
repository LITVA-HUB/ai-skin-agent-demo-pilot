# Demo pilot notes

## What changed in this demo branch
- unified runtime initialization through `app.runtime.lifespan`
- added `/health` and `/ready` with version, storage and readiness signals
- switched session store to SQLite-backed persistence with in-memory fallback
- made cart server-authoritative by resolving products from catalog by `sku`
- tightened reply safety with deterministic grounding fallback
- aligned config and `.env.example` with `LOG_LEVEL` and `SQLITE_PATH`

## Recommended demo flow
1. Upload a prepared selfie and set a clear goal.
2. Show first recommendation bundle (4-5 items).
3. Ask follow-ups like `make it cheaper`, `more radiant`, `evening version`.
4. Add 2-3 products to cart and show total.

## Suggested talking points
- This is a decision layer in front of the existing catalog, not a replacement for checkout.
- The demo is optimized for skincare + complexion bundle selection.
- Session memory and cart handoff are persistent during the pilot thanks to SQLite-backed sessions.
