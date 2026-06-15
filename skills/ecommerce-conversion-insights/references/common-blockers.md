# Common Conversion Blockers by Funnel Stage

## Stage 1: Session Start → Product View

| Blocker | Typical Impact | Detection Signal | Recommended Test |
|---------|---------------|-----------------|-----------------|
| Slow page load (LCP > 3s) | -7% conversion per second | High bounce rate + low pages/session | A/B: Lazy-load images, defer JS |
| Poor landing page relevance | -15-25% engagement | High bounce + low scroll depth | A/B: Dynamic content matching search intent |
| Intrusive pop-ups/interstitials | -10-15% engagement | Immediate bounce spike on pages with pop-ups | A/B: Remove pop-up vs. delayed trigger |
| Navigation confusion | -8-12% product views | High menu interaction + low PDP visits | A/B: Simplified nav with prominent categories |
| Missing search functionality | -5-10% for intent-driven traffic | Search usage correlation with conversion | A/B: Prominent search bar + autocomplete |

## Stage 2: Product View → Add to Cart

| Blocker | Typical Impact | Detection Signal | Recommended Test |
|---------|---------------|-----------------|-----------------|
| Insufficient product images | -20-30% ATC rate | Low time on PDP + high exit rate | A/B: 360° images + lifestyle photography |
| Price not immediately visible | -15-20% ATC rate | High PDP views + low ATC | A/B: Above-fold pricing vs. current |
| Out-of-stock variants shown | -10-15% ATC rate | Size/color selection abandonment | A/B: Hide OOS variants vs. show with restock date |
| Missing reviews/social proof | -12-18% ATC rate | Low confidence signals in session | A/B: Add review summary above fold |
| Unclear shipping costs | -8-15% ATC rate | FAQ/shipping page visits before ATC | A/B: "Free shipping over $X" badge on PDP |
| Mobile CTA below fold | -25-35% ATC on mobile | Device segment shows mobile-specific drop | A/B: Sticky ATC button on mobile |

## Stage 3: Add to Cart → Begin Checkout

| Blocker | Typical Impact | Detection Signal | Recommended Test |
|---------|---------------|-----------------|-----------------|
| Surprise costs in cart | -25-40% checkout rate | Cart page exit spike | A/B: Show estimated total earlier (PDP or mini-cart) |
| Required account creation | -15-25% checkout rate | Account creation page high exit rate | A/B: Guest checkout option |
| Cart UX friction | -5-10% checkout rate | Cart editing errors/loops | A/B: Streamlined cart with inline editing |
| Missing urgency/scarcity | -5-8% checkout rate | Long cart dwell time + exit | A/B: "X left in stock" + timer for cart hold |
| No saved cart / email reminder | -10-15% for returning visitors | Cart reconstruction from returning sessions | Implement: Cart persistence + abandonment email |

## Stage 4: Begin Checkout → Payment Info

| Blocker | Typical Impact | Detection Signal | Recommended Test |
|---------|---------------|-----------------|-----------------|
| Too many form fields | -10-15% per extra field | Form completion time + field error rate | A/B: Reduce to essential fields only |
| Shipping cost revealed late | -20-30% payment entry | Checkout step 1 exit after shipping shown | A/B: Flat-rate shipping or earlier disclosure |
| Limited shipping options | -8-12% payment entry | Shipping selection page abandonment | A/B: Add express/same-day options |
| No progress indicator | -5-8% payment entry | Multi-step checkout confusion | A/B: Clear step indicator (Step 2 of 3) |
| Address validation friction | -5-10% payment entry | Address form error rates | A/B: Google Places autocomplete |

## Stage 5: Payment Info → Order Confirmation

| Blocker | Typical Impact | Detection Signal | Recommended Test |
|---------|---------------|-----------------|-----------------|
| Limited payment methods | -10-20% conversion | Payment page exit without attempt | A/B: Add Apple Pay, BNPL options |
| Security concerns | -8-15% conversion | Hesitation time on payment + exit | A/B: Add trust badges, SSL indicator |
| Payment form errors | -5-10% conversion | Payment validation error rate | Fix: Better error messaging + real-time validation |
| Price change at payment | -15-25% conversion | Price discrepancy between cart/payment | Fix: Ensure price consistency throughout |
| Unexpected tax/fees | -10-20% conversion | Payment page exit after total shown | A/B: Show all-inclusive price from PDP |
| Mobile input friction | -15-25% on mobile | Mobile payment form error rates | A/B: Digital wallet default on mobile |

## Cross-Stage Patterns

| Pattern | Stages Affected | Signal | Action |
|---------|----------------|--------|--------|
| Mobile-specific drops | All stages | Mobile conversion 40%+ below desktop | Mobile UX audit + responsive optimization |
| New vs. returning gap | Stage 3-5 | New user conversion << returning | Reduce friction for first-time buyers |
| Geographic concentration | All stages | Specific market underperforms | Localization review (currency, language, shipping) |
| Time-of-day pattern | Stage 4-5 | Evening/weekend drops | Server performance check + staff support hours |
| Category-specific | Stage 2-3 | One category drops more | Category-specific PDP/cart UX review |
