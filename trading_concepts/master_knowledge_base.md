# TRADING CONCEPTS — MASTER KNOWLEDGE BASE
# Primary Framework: ICT / Smart Money Concepts (SMC)

> **This document is NOT a glossary.**
> Every concept is documented as a component of a trading sequence.
> The most important field for every concept is: **"NEXT ACTION / WHAT TO CHECK NEXT"**
>
> The agent should be able to reason:
> "What do I see?" → "What does it mean?" → "What caused it?" → "What should I check next?"
> → "What would confirm it?" → "What would invalidate it?" → "Is there actually a trade here?"

---
---

# ═══════════════════════════════════════════════════════════════
# SECTION A: CANDLESTICK & PRICE ACTION
# ═══════════════════════════════════════════════════════════════

Candlesticks are the raw language of price. Every candle tells a story about the battle between buyers and sellers during a specific time period. But a candlestick pattern by itself is **NEVER** an automatic trade signal. It must always be interpreted in context — where it forms on the chart (relative to structure, liquidity, and key zones) matters far more than what it looks like in isolation.

---

## A.1 — UNDERSTANDING A SINGLE CANDLE

### What Is It?
A candlestick represents price movement over a fixed time interval. It has four data points:
- **Open**: The price at the start of the period
- **Close**: The price at the end of the period
- **High**: The highest price reached during the period
- **Low**: The lowest price reached during the period

The **body** is the filled area between Open and Close.
The **wicks** (also called shadows) are the thin lines extending above and below the body.

### Body-to-Wick Relationship — What It Reveals

| Candle Characteristic | What It Tells You |
|---|---|
| Large body, small wicks | Strong conviction in one direction. Buyers (bullish) or sellers (bearish) dominated with little opposition. |
| Small body, large wicks | Indecision. Both sides fought, but neither won decisively. |
| Large upper wick | Buyers pushed price up, but sellers rejected it and pushed it back down. Selling pressure present at higher prices. |
| Large lower wick | Sellers pushed price down, but buyers rejected it and pushed it back up. Buying pressure present at lower prices. |
| No wick on one side | Complete dominance. If a bullish candle has no upper wick, it closed at the absolute high — pure buying momentum. |

### Displacement Candles (Momentum/Impulsive Candles)

**What is it?**
A displacement candle is a candle with a significantly larger-than-average body and minimal wicks. It represents a strong, aggressive move by one side of the market (typically institutional/smart money).

**How to identify it:**
- Body size is noticeably larger than the previous 10-20 candles
- Wicks are very small relative to the body (ideally < 20% of total candle range)
- Often creates a Fair Value Gap (see Section G)
- Often breaks a structural level (see Section B)

**Why it matters:**
Displacement is evidence that aggressive orders entered the market. In the ICT/SMC framework, displacement is one of the primary confirmation signals — it validates that a liquidity event (sweep) was followed by genuine institutional interest.

**NEXT ACTION:** When you see a displacement candle:
→ Check if it followed a liquidity sweep (Section E)
→ Check if it broke market structure (BOS/MSS/CHoCH — Section B)
→ Look for an FVG created by the displacement (Section G)
→ Identify the Order Block at the origin of the displacement (Section F)

### Indecision Candles

**What is it?**
A candle with a very small body relative to its total range (body < 30% of total high-to-low range). The open and close are nearly equal.

**What it tells you:**
Neither buyers nor sellers won the period. This is meaningful ONLY at key levels. An indecision candle in the middle of nowhere is meaningless noise.

**When it matters:**
- At an Order Block / POI → potential reversal or continuation depending on context
- At a liquidity level → market is "deciding" whether to sweep or respect

**When to ignore it:**
- In the middle of a range with no structural significance
- During low-volume sessions (e.g., Asian session on forex pairs)

**NEXT ACTION:** When you see indecision at a key level:
→ Do NOT enter immediately
→ Wait for the next candle to show commitment (displacement)
→ Check the higher timeframe for bias direction

---

## A.2 — SINGLE-CANDLE PATTERNS

### Doji

**What is it?**
A candle where the open and close are virtually identical (body < 5-10% of total range). Wicks extend in both directions.

**How it forms:**
Both buyers and sellers were active during the period but ended at roughly the same price.

**What it does NOT mean:**
A Doji does NOT automatically mean reversal. It means indecision. The context determines whether that indecision leads to reversal or continuation.

**Where it matters (ICT/SMC context):**
- At an Order Block being retested → potential confirmation that price is respecting the zone
- After a liquidity sweep → possible sign that momentum is exhausting
- At equilibrium (50% of a dealing range) → market deciding direction

**Where it does NOT matter:**
- Random occurrence during consolidation
- Low-volume sessions

**NEXT ACTION:**
→ Identify WHERE the Doji formed (what zone/level)
→ Check HTF bias — is the Doji forming in premium or discount?
→ Wait for the next candle — a strong displacement candle after a Doji at a key level is significant
→ Do NOT trade the Doji itself

---

### Hammer

**What is it?**
A candle with a small body at the top of the range and a long lower wick (at least 2x the body length). Little to no upper wick.

**How it forms:**
Sellers pushed price down aggressively during the period, but buyers stepped in and pushed price back up near the open. The long lower wick is evidence of buying pressure at lower prices.

**Why it forms:**
Typically occurs when price reaches a level where institutional buy orders are resting (a demand zone, bullish Order Block, or area of buy-side interest).

**What market condition makes it meaningful:**
- Appears at the end of a downtrend or at a significant support/demand level
- Appears at a bullish Order Block or within a bullish FVG
- Appears after a sell-side liquidity sweep (price took out lows, then reversed)

**How to identify it:**
1. Small real body (top 25-33% of candle range)
2. Lower wick ≥ 2× body length
3. Upper wick is small or absent
4. Appears at or near a significant level

**What it does NOT mean:**
- A hammer in the middle of a range is meaningless
- A hammer in a strong downtrend without reaching a key level is just a pullback
- A hammer does NOT automatically mean "buy"

**How it can be used with market structure:**
- If price swept sell-side liquidity (SSL) and then formed a Hammer at a bullish OB → this is a potential reversal confirmation
- If the Hammer is followed by a displacement candle upward → stronger confirmation

**What confirmation should come next:**
- The next candle should be bullish and ideally have a body larger than the Hammer's body
- Best if displacement follows (a strong bullish candle that breaks a recent swing high)

**When it should be ignored:**
- Mid-range, no structural significance
- During low-volume/Asian session for instruments that are inactive then
- If HTF bias is strongly bearish and no significant level has been reached

**NEXT ACTION:**
→ Identify the level it formed at (OB? FVG? Liquidity sweep zone?)
→ Check if SSL was just swept before the Hammer formed
→ Wait for the next candle's confirmation (bullish close above Hammer high)
→ Check HTF bias alignment

---

### Inverted Hammer

**What is it?**
A candle with a small body at the bottom of the range and a long upper wick (≥ 2× body). Little to no lower wick. Appears in a downtrend.

**How it forms:**
Buyers attempted to push price up during the period but were met with resistance. However, the fact that buyers attempted a push during a downtrend suggests potential exhaustion of selling pressure.

**Meaningful when:**
- At a bullish OB or FVG zone during a pullback in an uptrend
- After SSL has been swept

**Not meaningful when:**
- Random occurrence in a strong downtrend with no key level nearby

**NEXT ACTION:**
→ Same as Hammer — check level, check liquidity, wait for confirmation candle
→ Requires a strong bullish candle to follow to validate the signal

---

### Shooting Star

**What is it?**
A candle with a small body at the bottom of the range and a long upper wick (≥ 2× body). Little to no lower wick. Appears in an uptrend — the bearish equivalent of a Hammer.

**How it forms:**
Buyers pushed price up but sellers aggressively rejected the higher prices, closing the candle near the open.

**Meaningful when:**
- At a bearish Order Block
- After buy-side liquidity (BSL) was swept (price took out highs, then reversed)
- At a premium level in the dealing range
- At a supply zone

**NEXT ACTION:**
→ Check if BSL was just swept
→ Identify if a bearish OB or supply zone is at this level
→ Wait for bearish displacement candle to follow
→ Check HTF bias — is the overall trend bearish?

---

### Hanging Man

**What is it?**
Visually identical to a Hammer, but appears at the top of an uptrend (or at a resistance/supply level).

**How it forms:**
During an uptrend, sellers briefly pushed price down (long lower wick) before buyers recovered. However, the fact that sellers were able to push that far suggests weakening buyer momentum.

**Meaningful when:**
- At a bearish OB / supply zone
- After BSL was swept
- At premium in the dealing range

**NEXT ACTION:**
→ Check if BSL was just swept
→ Wait for bearish confirmation candle (close below the Hanging Man's low)
→ Check for displacement to the downside

---

## A.3 — MULTI-CANDLE PATTERNS

### Engulfing Pattern (Bullish)

**What is it?**
A two-candle pattern where the second candle's body completely engulfs (covers) the first candle's body. Bullish engulfing: first candle is bearish, second candle is bullish with a body that opens below and closes above the first candle's body.

**How it forms:**
A bearish candle shows selling pressure. Then the next candle opens at or below the prior close and closes well above the prior open — buyers completely overwhelmed sellers.

**Why it matters in ICT/SMC:**
A bullish engulfing candle at an Order Block or FVG zone is one of the strongest entry confirmations. It represents displacement on a smaller scale — the aggressive buying that engulfs the prior selling is evidence of institutional order flow.

**Detection rules (OHLC):**
1. Candle[n-1] is bearish: Close[n-1] < Open[n-1]
2. Candle[n] is bullish: Close[n] > Open[n]
3. Open[n] ≤ Close[n-1] (opens at or below prior close)
4. Close[n] ≥ Open[n-1] (closes at or above prior open)
5. Body of candle[n] > Body of candle[n-1]

**Meaningful when:**
- At a bullish Order Block during a pullback
- Within a bullish FVG being filled
- After SSL sweep with price returning into the zone
- In discount of the dealing range

**Not meaningful when:**
- In the middle of nowhere
- Against the HTF trend without significant level confluence

**NEXT ACTION:**
→ If at an OB/FVG with HTF alignment → this IS the entry confirmation
→ Define entry: at the close of the engulfing candle or at a pullback to 50% of the engulfing candle
→ Define SL: below the low of the engulfing pattern
→ Define TP: next liquidity target (BSL, swing high, opposing OB)

---

### Engulfing Pattern (Bearish)

Mirror of bullish engulfing. A bearish candle that fully engulfs the prior bullish candle. Meaningful at bearish OBs, after BSL sweep, in premium of the dealing range.

**Detection rules (OHLC):**
1. Candle[n-1] is bullish: Close[n-1] > Open[n-1]
2. Candle[n] is bearish: Close[n] < Open[n]
3. Open[n] ≥ Close[n-1]
4. Close[n] ≤ Open[n-1]
5. Body of candle[n] > Body of candle[n-1]

**NEXT ACTION:** Same process as bullish but in reverse direction.

---

### Inside Bar

**What is it?**
A candle whose entire range (high to low) is contained within the range of the previous candle. The prior candle is called the "mother bar."

**How it forms:**
After a move, the market pauses. The inside bar represents compression — a period where price is coiling within the prior candle's range.

**Detection rules (OHLC):**
1. High[n] ≤ High[n-1]
2. Low[n] ≥ Low[n-1]

**Why it matters:**
- Inside bars at key levels (OB, FVG, liquidity zones) represent accumulation/compression before an expansion move
- The breakout direction of the inside bar tells you which side won

**Meaningful when:**
- At an OB or FVG zone → the market is coiling before expanding in the direction of the zone's bias
- After a liquidity sweep → price is building energy for a reversal move

**NEXT ACTION:**
→ Do NOT trade the inside bar itself
→ Wait for the breakout candle (which side of the mother bar does price break?)
→ If price breaks in the direction aligned with the OB/FVG bias AND the HTF trend → potential entry
→ If price breaks against the expected direction → the setup is invalidated

---

### Pin Bar

**What is it?**
A candle with a very small body and one very long wick (at least 2/3 of the total range). The long wick represents rejection of a price level.

**How it forms:**
Price was pushed aggressively in one direction, but was rejected and closed back near the open. The long wick is the "rejection" — evidence that orders on the opposite side were strong enough to reverse the move within the period.

**Detection rules (OHLC):**
- Bullish Pin Bar: Lower wick ≥ 66% of total range, body in upper 33%
- Bearish Pin Bar: Upper wick ≥ 66% of total range, body in lower 33%

**Meaningful when:**
- The long wick pierces through a liquidity level (swept liquidity) and then reversed → this is a liquidity sweep captured in a single candle
- At an OB or FVG zone

**NEXT ACTION:**
→ Check what the wick pierced — was it a liquidity level? Equal highs/lows? Previous day high/low?
→ If yes → treat this as a combined liquidity sweep + rejection signal
→ Wait for follow-through confirmation on the next candle
→ Check displacement and structure

---

## A.4 — CRITICAL RULE: CANDLESTICK PATTERNS ARE NOT TRADE SIGNALS

**A candlestick pattern is a piece of evidence, not a verdict.**

The agent must NEVER enter a trade solely because a candlestick pattern appeared. Every pattern must be evaluated against:

1. **WHERE** did it form? (What zone, what level?)
2. **WHAT** happened before it? (Was there a liquidity sweep? A structural break?)
3. **DOES** the HTF bias align?
4. **IS** there confluence with other concepts? (OB + FVG + premium/discount?)

Only when a candlestick pattern appears as **confirmation** at the end of a valid setup sequence should it contribute to an entry decision.

**Correct reasoning sequence:**
```
HTF bias determined → Liquidity identified → Sweep occurred → Displacement confirmed 
→ Structure shifted → FVG/OB identified → Price retraces to zone 
→ CANDLESTICK PATTERN appears at the zone → THIS is when it matters → Entry
```

**Incorrect reasoning:**
```
Hammer appeared → BUY  ← WRONG
```

---
---

# ═══════════════════════════════════════════════════════════════
# SECTION B: MARKET STRUCTURE
# ═══════════════════════════════════════════════════════════════

Market structure is the backbone of all price analysis in the ICT/SMC framework. It tells the agent: "What is the market currently doing? Is it trending up, trending down, or ranging?" Without correctly reading market structure, every other concept is useless.

---

## B.1 — SWING HIGHS AND SWING LOWS

### What Is It?
A **Swing High** is a price peak where the high of a candle is higher than the highs of the candles on both its left and right sides.
A **Swing Low** is a price trough where the low of a candle is lower than the lows of the candles on both its left and right sides.

### How to Identify (Detection Rules)

**Swing High (basic rule):**
A candle at index `i` forms a swing high if:
- `High[i] > High[i-1]` AND `High[i] > High[i-2]` (higher than at least 2 candles to the left)
- `High[i] > High[i+1]` AND `High[i] > High[i+2]` (higher than at least 2 candles to the right)

**Swing Low (basic rule):**
A candle at index `i` forms a swing low if:
- `Low[i] < Low[i-1]` AND `Low[i] < Low[i-2]`
- `Low[i] < Low[i+1]` AND `Low[i] < Low[i+2]`

**Note on lookback period:**
- Using 2 candles on each side gives "minor" swing points (more frequent, captures internal structure)
- Using 5-10 candles on each side gives "major" swing points (less frequent, captures external/significant structure)
- The timeframe determines what is "significant." A swing high on the Daily chart is far more important than a swing high on the 5-minute chart.

### Why It Matters
Swing points are the building blocks of market structure. Without identifying swing highs and swing lows, the agent cannot determine:
- Whether the market is making Higher Highs / Higher Lows (uptrend)
- Whether the market is making Lower Highs / Lower Lows (downtrend)
- Where structural breaks (BOS/CHoCH/MSS) occur

### Structural Significance
Not all swing points are equal. A swing point is **structurally significant** if:
1. It is visible on the timeframe being analyzed (not just minor noise)
2. It created a meaningful leg/move (price traveled a reasonable distance from the previous swing point)
3. It aligns with swing points on a higher timeframe
4. It caused or was caused by a liquidity event

**NEXT ACTION:**
→ After identifying swing highs and lows, label them as HH, HL, LH, or LL (see B.2)
→ Determine the trend direction
→ Identify which swing points hold liquidity (equal highs/lows, obvious levels)

---

## B.2 — HIGHER HIGHS, HIGHER LOWS, LOWER HIGHS, LOWER LOWS

### Definitions

| Label | Definition | What It Tells You |
|---|---|---|
| **HH** (Higher High) | A swing high that is HIGHER than the previous swing high | Buyers are pushing price to new highs → bullish momentum |
| **HL** (Higher Low) | A swing low that is HIGHER than the previous swing low | Buyers are defending higher levels → bullish structure intact |
| **LH** (Lower High) | A swing high that is LOWER than the previous swing high | Buyers are failing to reach previous highs → weakening bullish momentum or emerging bearish structure |
| **LL** (Lower Low) | A swing low that is LOWER than the previous swing low | Sellers are pushing price to new lows → bearish momentum |

### Trend Determination

| Structure Sequence | Trend |
|---|---|
| HH + HL → HH + HL | **Uptrend** (bullish) |
| LH + LL → LH + LL | **Downtrend** (bearish) |
| No consistent pattern (HH then LL, or HL then LH, etc.) | **Range / Consolidation** |

### Detection Rules (OHLC)

After identifying swing points (B.1):
1. Compare each new swing high with the previous swing high:
   - If higher → label HH
   - If lower → label LH
2. Compare each new swing low with the previous swing low:
   - If higher → label HL
   - If lower → label LL
3. A valid uptrend requires at least: HH followed by HL (or HL followed by HH)
4. A valid downtrend requires at least: LH followed by LL (or LL followed by LH)

### What Confirms It
- Consistent sequence: HH → HL → HH → HL = confirmed uptrend
- Each new HH should be accompanied by displacement (strong momentum)
- Volume/order flow should align with the trend direction

### What Invalidates It
- In an uptrend: if price makes a LL (breaks below the previous HL), the bullish structure is potentially broken
- In a downtrend: if price makes a HH (breaks above the previous LH), the bearish structure is potentially broken
- This is where BOS, CHoCH, and MSS come in (B.4)

**NEXT ACTION:**
→ Once trend is determined, establish directional bias
→ In an uptrend: look for buying opportunities at pullbacks (HLs)
→ In a downtrend: look for selling opportunities at pullbacks (LHs)
→ Watch for structural breaks that would change the bias

---

## B.3 — INTERNAL STRUCTURE vs EXTERNAL STRUCTURE

### What Is It?

**External Structure** = The major swing points that define the overall trend. These are the "big picture" swings visible on the current or higher timeframe.

**Internal Structure** = The smaller swing points that form WITHIN the legs between external structure points. These are the minor pullbacks/retracements within a larger move.

### Why the Distinction Matters

The agent must know which structural level it is looking at. Breaking internal structure is very different from breaking external structure:

| Break Type | Meaning |
|---|---|
| **Internal structure break** | A minor pullback within the larger trend. Does NOT necessarily change the overall trend direction. |
| **External structure break** | A significant break of the major swing points. This CAN indicate a trend change. |

### How to Identify

1. On the current timeframe, identify the major, obvious swing points → these are external structure
2. Within the legs between those major swings, look for smaller swing points → these are internal structure
3. Rule of thumb: if you need to zoom into a lower timeframe to see the swing point clearly, it is likely internal structure

### Example

In a bullish trend:
```
External: Swing Low A → Swing High B → Swing Low C (higher than A) → Swing High D (higher than B)

Internal structure between A and B:
  Price goes up from A, pulls back slightly (minor swing low), goes up again to B.
  That minor swing low is internal structure.
```

**NEXT ACTION:**
→ When analyzing BOS/CHoCH/MSS (B.4), always identify whether the break is internal or external
→ An internal BOS in a pullback does NOT invalidate the external trend
→ An external BOS is far more significant and may indicate a true trend change

---

## B.4 — BREAK OF STRUCTURE (BOS), CHANGE OF CHARACTER (CHoCH), MARKET STRUCTURE SHIFT (MSS)

This is one of the most critical sections. These three terms are sometimes used interchangeably in trading communities, but they have distinct meanings in the ICT/SMC framework.

### Break of Structure (BOS)

**What is it?**
A BOS occurs when price breaks beyond a previous swing point **in the direction of the existing trend**. It is a **continuation** signal.

**How it forms:**
- In an uptrend: Price makes a new HH by breaking above the previous swing high → Bullish BOS
- In a downtrend: Price makes a new LL by breaking below the previous swing low → Bearish BOS

**Detection rules (OHLC):**
- Bullish BOS: Close[n] > High of the previous swing high (price must CLOSE above, not just wick)
- Bearish BOS: Close[n] < Low of the previous swing low (price must CLOSE below)

**What it tells you:**
The existing trend is continuing. Momentum is intact. The market is making new structural moves in the same direction.

**What it does NOT mean:**
A BOS alone is NOT an entry signal. It confirms the trend is alive, which helps the agent determine directional bias. The entry comes later, at a pullback to an OB/FVG.

**NEXT ACTION after BOS:**
→ Trend is confirmed as continuing in this direction
→ Look for the FVG/OB created by the displacement that caused the BOS
→ Wait for price to retrace to that FVG/OB for an entry opportunity
→ Set targets at the next liquidity level in the trend direction

---

### Change of Character (CHoCH)

**What is it?**
A CHoCH occurs when price breaks beyond a previous swing point **against the current trend direction** for the FIRST TIME. It is an early warning that the trend may be shifting.

**How it forms:**
- In an uptrend: Price breaks below the most recent swing low (HL) → First bearish structural break → CHoCH
- In a downtrend: Price breaks above the most recent swing high (LH) → First bullish structural break → CHoCH

**Detection rules (OHLC):**
- Bearish CHoCH (in a previous uptrend): Close[n] < Low of the most recent Higher Low
- Bullish CHoCH (in a previous downtrend): Close[n] > High of the most recent Lower High

**Critical distinction from BOS:**
- BOS = break in the SAME direction as the trend (continuation)
- CHoCH = break AGAINST the trend direction (potential reversal)

**What it tells you:**
The character of price has changed. What was previously an uptrend (HH, HL) has now produced its first LL. This is a warning sign, not a confirmed reversal.

**What it does NOT mean:**
- CHoCH alone does NOT confirm a full reversal
- Price may CHoCH and then resume the original trend
- It requires additional confirmation (displacement, MSS, FVG formation) to validate

**NEXT ACTION after CHoCH:**
→ Be alert — the trend may be changing
→ Check if the CHoCH was accompanied by displacement (strong, aggressive move)
→ Check if significant liquidity was swept before the CHoCH occurred
→ Look for FVG/OB formation in the direction of the CHoCH
→ If all align → potential new trend forming
→ If CHoCH was weak (small candle, no displacement) → may be a false signal; wait for MSS

---

### Market Structure Shift (MSS)

**What is it?**
An MSS is a **confirmed** change of trend direction. It is stronger than a CHoCH. An MSS typically involves a CHoCH that is accompanied by:
1. A liquidity sweep preceding it
2. Significant displacement
3. Formation of FVG and/or OB

In some ICT teaching, MSS and CHoCH are used synonymously. However, the practical distinction is:
- **CHoCH** = first break against the trend (warning)
- **MSS** = confirmed structural shift with supporting evidence (actionable)

**How it forms (complete sequence):**
1. Trend is established (e.g., uptrend: HH, HL pattern)
2. Price sweeps liquidity at the extreme (e.g., takes out a swing high / BSL)
3. After the sweep, aggressive selling enters (displacement candle)
4. Price breaks below the most recent HL (CHoCH occurs)
5. The break is accompanied by displacement, FVG creation, and an OB forms at the point where selling began
6. This entire event = MSS

**Detection rules (OHLC):**
Same structural break as CHoCH, but additionally requires:
- Displacement candle(s) involved in the break (body > average body of last 20 candles)
- An FVG was created during the break
- The break has been sustained (price has not immediately reversed back above the broken level)

**What it tells you:**
The trend has shifted. The previous trend's structure has been invalidated with conviction. This is the most significant structural event and directly informs directional bias.

**NEXT ACTION after MSS:**
→ The directional bias has changed — trade in the direction of the MSS
→ Identify the FVG and OB created during the MSS move
→ Wait for price to retrace to the FVG/OB
→ Seek entry confirmation (candlestick pattern, LTF displacement, etc.)
→ Set SL beyond the swing point that was broken
→ Set TP at the next liquidity target in the new trend direction

---

### Summary: BOS vs CHoCH vs MSS

| Concept | Direction | Meaning | Strength | Action |
|---|---|---|---|---|
| **BOS** | With the trend | Continuation confirmed | Standard | Look for pullback entry to OB/FVG |
| **CHoCH** | Against the trend | First warning of potential reversal | Moderate | Be alert, wait for confirmation |
| **MSS** | Against the trend, with displacement | Confirmed trend reversal | Strong | Change directional bias, seek entry on pullback |

**They are NOT always identical.** The key difference:
- BOS = same direction = continuation
- CHoCH = opposite direction = warning
- MSS = CHoCH + displacement + liquidity sweep = confirmed shift

---

## B.5 — STRUCTURAL CONFIRMATION AND INVALIDATION

### What Confirms a Structural Move?
1. **Candle body close** beyond the level (not just a wick). In ICT/SMC, a level is only broken when a candle CLOSES beyond it.
2. **Displacement** during the break — strong, aggressive candles, not a slow grind.
3. **Follow-through** — the next candle continues in the break direction (not an immediate reversal).

### What Invalidates Structure?
- If price breaks below the most recent HL in an uptrend → bullish structure invalidated
- If price breaks above the most recent LH in a downtrend → bearish structure invalidated
- If a BOS fails (price breaks beyond a swing point but immediately reverses and closes back inside → this is a potential liquidity sweep / stop hunt, not a genuine break)

**NEXT ACTION:**
→ When structure is confirmed, use it to establish or maintain directional bias
→ When structure is invalidated, re-evaluate — look for CHoCH/MSS
→ When a break fails (wick beyond, close inside), look for a sweep setup (Section E)

---

## B.6 — CONTINUATION vs REVERSAL

### Continuation
When price maintains the existing trend structure:
- Uptrend: HH → HL → HH → HL → (continues)
- Each pullback (HL) is an opportunity to enter with the trend
- BOS confirms continuation

### Reversal
When price changes the existing trend structure:
- Uptrend ending: HH → HL → LH → LL (structure broken)
- The first LL is the CHoCH
- If confirmed with displacement → MSS
- MSS signals the start of a potential new downtrend

### How the Agent Should Think:

```
1. What is the current structure? (HH/HL = uptrend? LH/LL = downtrend?)
2. Is the latest swing point continuing the pattern or breaking it?
3. If continuing → look for pullback entry (trend continuation trade)
4. If breaking → is there displacement? Was liquidity swept? 
   → If yes → MSS → potential reversal trade
   → If no → possible false break → wait for more information
```

---
---

# ═══════════════════════════════════════════════════════════════
# SECTION C: TOP-DOWN / MULTI-TIMEFRAME ANALYSIS
# ═══════════════════════════════════════════════════════════════

Multi-timeframe analysis is how the agent gains **context**. Without it, the agent is staring at a single timeframe and making decisions in a vacuum. The ICT/SMC approach demands a top-down workflow: start from the highest relevant timeframe, determine the bias, then drill down to the execution timeframe.

---

## C.1 — THE TOP-DOWN WORKFLOW

### The Principle
Higher timeframes control the overall direction. Lower timeframes provide precision for entries. The agent should NEVER take a trade on a lower timeframe that contradicts the higher timeframe's bias without exceptional justification.

### Standard Timeframe Hierarchy (Forex/Commodities)

| Role | Timeframes | What to Extract |
|---|---|---|
| **HTF (Bias)** | Monthly, Weekly, Daily | Overall trend direction, major structure, major liquidity pools, key OBs/FVGs, premium/discount zones |
| **MTF (Context)** | H4, H1 | Current dealing range, intermediate structure, intermediate OBs/FVGs, confluence zones |
| **LTF (Entry)** | M15, M5, M1 | Entry confirmation, precise entry point, tight SL placement, LTF CHoCH/MSS/BOS |

### How Analysis Flows

```
WEEKLY / DAILY (HTF)
├── Determine overall trend (bullish / bearish / ranging)
├── Identify major swing highs and lows
├── Identify major liquidity pools (BSL/SSL)
├── Identify major OBs and FVGs
├── Determine dealing range
├── Determine premium vs discount
│
├── RESULT: "I am bullish on this pair. Price is currently in discount.
│            The next major target is BSL at [price]."
│
└──→ H4 / H1 (MTF)
     ├── Confirm HTF bias with intermediate structure
     ├── Identify intermediate OBs and FVGs within the HTF framework
     ├── Identify which specific zone price is approaching
     ├── Check if any liquidity has been swept
     │
     ├── RESULT: "HTF is bullish. Price just swept SSL on H4 and is now
     │            at a bullish OB. Looking for long entries."
     │
     └──→ M15 / M5 (LTF)
          ├── Wait for LTF CHoCH or MSS (structure shift confirming reversal)
          ├── Identify the LTF FVG/OB created by the shift
          ├── Wait for price to retrace to the LTF FVG/OB
          ├── Enter with a tight SL below the LTF swing low
          │
          └── RESULT: "Long entry at [price]. SL at [price]. TP at [price]."
```

---

## C.2 — WHAT INFORMATION COMES FROM EACH TIMEFRAME

### Higher Timeframe (Weekly / Daily)
- **Trend direction**: Is the market making HH/HL (bullish) or LH/LL (bearish)?
- **Major liquidity**: Where are the major BSL and SSL pools? Equal highs/lows?
- **Major zones**: HTF Order Blocks and FVGs that price is likely to react to
- **Dealing range**: The current range between the most recent significant swing high and swing low
- **Premium/Discount**: Is price above or below the 50% of the dealing range?
- **Bias**: The directional bias that all lower-timeframe analysis must align with

### Mid Timeframe (H4 / H1)
- **Intermediate structure**: More granular view of swing points within the HTF framework
- **Confluence zones**: Where HTF and MTF OBs/FVGs overlap → strongest zones
- **Liquidity sweeps**: Has any H4/H1 liquidity been taken?
- **Current position**: Where exactly is price relative to the identified zones?

### Lower Timeframe (M15 / M5 / M1)
- **Entry timing**: The precise candle/moment to enter
- **Entry confirmation**: LTF CHoCH/MSS that confirms the HTF bias is playing out
- **Tight SL placement**: Using the LTF swing point for a minimal SL distance
- **FVG/OB refinement**: The LTF OB/FVG created by the LTF structural shift → the exact entry zone

---

## C.3 — TIMEFRAME ALIGNMENT

### What is it?
Timeframe alignment means the bias on the higher timeframe and the action on the lower timeframe are pointing in the SAME direction.

### Why it matters
Trades that align across multiple timeframes have a significantly higher probability of success. If HTF is bullish but LTF is showing bearish signals, there is a conflict — the LTF bearish move is likely just a pullback in the larger bullish trend.

### When HTF overrides LTF
**Always**, unless the LTF is showing evidence of a major MSS with heavy displacement that could indicate the HTF is itself beginning to shift. This is rare.

General rule:
- If HTF is bullish → only look for buy setups on LTF
- If HTF is bearish → only look for sell setups on LTF
- If HTF is ranging → use the range boundaries (buy at range bottom, sell at range top)

### When to be cautious
- HTF showing signs of exhaustion (long wicks, indecision at key levels)
- Major economic news events that could cause HTF structural shifts
- Price at a major HTF OB/FVG that could cause a significant reaction

**NEXT ACTION:**
→ Always start analysis from the HTF
→ Determine bias BEFORE looking at LTF
→ On LTF, only look for setups that align with the HTF bias
→ If LTF and HTF conflict → wait, do not trade

---

## C.4 — DEALING RANGE

### What is it?
The dealing range is the price range between the most recent significant swing high and swing low on the current timeframe. It represents the "field of play" within which price is currently operating.

### How to determine it
1. Identify the most recent significant swing high on the timeframe
2. Identify the most recent significant swing low on the timeframe
3. The range between them = the dealing range
4. The 50% level of this range = equilibrium

### Why it matters
The dealing range determines premium and discount (see Section O). All zones, OBs, FVGs, and liquidity within the dealing range are evaluated relative to whether they are in premium or discount.

**NEXT ACTION:**
→ After identifying the dealing range, calculate the 50% level
→ Determine whether current price is in premium (above 50%) or discount (below 50%)
→ In an uptrend: look for buys in discount, targets in premium
→ In a downtrend: look for sells in premium, targets in discount

---
---

# ═══════════════════════════════════════════════════════════════
# SECTION D: LIQUIDITY
# ═══════════════════════════════════════════════════════════════

Liquidity is arguably the most fundamental concept in ICT/SMC. It is the reason price moves. Understanding where liquidity rests, why it forms, and how price interacts with it is essential for every single trade the agent evaluates.

---

## D.1 — WHAT IS LIQUIDITY?

### Definition
In the ICT/SMC framework, **liquidity** refers to clusters of pending orders (primarily stop-loss orders and stop orders) resting at specific price levels. These orders are "fuel" for price movement — when price reaches them, the orders are triggered, creating a burst of volume that facilitates institutional order execution.

### Why Does Liquidity Form?
Retail traders place stop-loss orders at predictable locations:
- Below swing lows (for long positions)
- Above swing highs (for short positions)
- Below/above obvious support and resistance levels
- At round numbers
- At equal highs and equal lows

Institutional/smart money participants know where these stops are clustered. They use this knowledge to move price toward those clusters, trigger the stops, absorb the resulting liquidity, and then move price in their intended direction.

### The Key Insight
**Price is drawn to liquidity.** It does not move randomly. Price moves FROM one pool of liquidity TO another. Understanding this allows the agent to predict where price is likely to go next (the "Draw on Liquidity").

---

## D.2 — BUY-SIDE LIQUIDITY (BSL) AND SELL-SIDE LIQUIDITY (SSL)

### Buy-Side Liquidity (BSL)

**What is it?**
Buy-side liquidity is the cluster of buy stop orders resting ABOVE swing highs, equal highs, and resistance levels. These are:
- Stop-loss orders from short sellers (placed above highs)
- Buy-stop orders from breakout traders (waiting to buy a breakout above resistance)

**Where it forms:**
- Above swing highs
- Above equal highs (EQH)
- Above previous day/week/month highs
- Above obvious resistance levels
- Above old highs that have not been taken

**How to identify it:**
Look for areas above the chart where price has made swing highs, especially:
- Multiple highs at similar prices (equal highs → heavy BSL)
- Obvious swing highs that are clearly visible (retail traders will have stops above them)
- Previous session highs (PDH, PWH)

### Sell-Side Liquidity (SSL)

**What is it?**
Sell-side liquidity is the cluster of sell stop orders resting BELOW swing lows, equal lows, and support levels. These are:
- Stop-loss orders from long buyers (placed below lows)
- Sell-stop orders from breakdown traders

**Where it forms:**
- Below swing lows
- Below equal lows (EQL)
- Below previous day/week/month lows
- Below obvious support levels
- Below old lows that have not been taken

### How BSL and SSL Differ

| BSL | SSL |
|---|---|
| Rests ABOVE price | Rests BELOW price |
| Triggered when price moves UP to take highs | Triggered when price moves DOWN to take lows |
| Contains buy stops (from short sellers' SL + breakout buyers) | Contains sell stops (from long buyers' SL + breakdown sellers) |
| When swept in a bearish context → provides fuel for a reversal down | When swept in a bullish context → provides fuel for a reversal up |

**NEXT ACTION after identifying BSL/SSL:**
→ Mark the liquidity levels on the chart
→ Determine which pool is most likely to be targeted next (Draw on Liquidity)
→ If price is moving toward BSL → be cautious about taking longs near that level (price may sweep and reverse)
→ If price is moving toward SSL → be cautious about taking shorts near that level
→ Wait for price to reach the liquidity → observe how it reacts (see Section E)

---

## D.3 — EQUAL HIGHS (EQH) AND EQUAL LOWS (EQL)

### What is it?
Equal highs are two or more swing highs at approximately the same price level. Equal lows are two or more swing lows at approximately the same price level.

### Why they represent liquidity
Equal highs/lows are extremely obvious on a chart. Every retail trader sees them and thinks "strong resistance/support." They place stop-loss orders just above/below. This creates a dense pool of liquidity.

In the ICT/SMC view, equal highs/lows are NOT strong support/resistance — they are **liquidity targets**. The more equal the highs/lows, the more liquidity sits there, and the more likely price will eventually reach and sweep them.

### Detection rules (OHLC)
- EQH: Two or more swing highs where the difference between their prices is less than a threshold (e.g., < 0.1% of price or < a few pips)
- EQL: Two or more swing lows where the difference between their prices is less than the same threshold

### What confirms it
- The more times price has tested a level without breaking it, the more liquidity accumulates
- Clean, flat levels visible to naked eye = heavy liquidity

### What invalidates it
- If price sweeps the equal highs/lows (breaks through them) → the liquidity has been taken and the level is no longer relevant as a target

**NEXT ACTION after identifying EQH/EQL:**
→ Mark them as potential liquidity targets
→ Determine if price is likely to target them (based on HTF bias and structure)
→ If price approaches EQH from below → do NOT blindly buy the "breakout" — it may be a liquidity sweep
→ If price sweeps EQH and immediately reverses with displacement → potential short setup (see Section E)
→ If price sweeps EQL and immediately reverses with displacement → potential long setup

---

## D.4 — INTERNAL RANGE LIQUIDITY (IRL) vs EXTERNAL RANGE LIQUIDITY (ERL)

### Internal Range Liquidity (IRL)

**What is it?**
Liquidity that rests WITHIN the current dealing range. This includes:
- Minor swing highs and lows inside the range
- FVGs inside the range
- Equal highs/lows within the range
- Order Blocks within the range

**Think of it as:** The liquidity between the range's high and low.

### External Range Liquidity (ERL)

**What is it?**
Liquidity that rests OUTSIDE the current dealing range. This includes:
- The range high itself (BSL above)
- The range low itself (SSL below)
- Previous day/week highs and lows beyond the range
- Liquidity pools beyond the current structure

**Think of it as:** The liquidity at or beyond the extremes of the range.

### How They Differ

| IRL | ERL |
|---|---|
| Inside the range | Outside/at the edges of the range |
| Price moves from IRL to ERL (uses internal liquidity as fuel to reach external targets) | ERL is the destination |
| Minor swing points, FVGs within range | Major swing points, range highs/lows |

### The IRL → ERL Concept
Price typically sweeps IRL (internal liquidity) to gather fuel, then targets ERL (external liquidity). This is a key concept for determining where price is heading:

```
Price is in a range
→ Price sweeps internal liquidity (takes out a minor swing low inside the range)
→ This provides fuel
→ Price then moves toward external range liquidity (the range high or low)
→ This is the primary target
```

**NEXT ACTION after identifying IRL/ERL:**
→ If price swept IRL → look for it to target ERL next
→ If price is at ERL → watch for a sweep and reaction (potential reversal)
→ Use IRL/ERL to determine realistic targets for trades

---

## D.5 — KEY LIQUIDITY LEVELS

### Previous Day High / Low (PDH / PDL)

Significant liquidity levels because many day-traders set their stops relative to the previous day's range.

### Previous Week High / Low (PWH / PWL)

Even more significant than PDH/PDL. Swing traders and institutional players reference weekly levels.

### Previous Month High / Low (PMH / PML)

Major institutional levels. Monthly candle highs and lows are watched by large players.

### Session High / Low

The high and low of the current trading session (Asian, London, New York). Intra-session traders' stops accumulate at these levels.

### Old Highs / Old Lows

Swing points from earlier in the chart's history that have not been revisited. These represent "unswept" liquidity — price may eventually return to take them.

### Relative Equal Highs / Lows

Not perfectly equal, but close enough that a cluster of stops sits at that zone.

---

## D.6 — DRAW ON LIQUIDITY (DOL)

### What is it?
The Draw on Liquidity is the concept that price is always being "pulled" toward the nearest significant liquidity pool. It is the likely destination for the current price move.

### How to determine the DOL
1. Identify all significant BSL and SSL on the chart
2. Determine the HTF bias direction
3. In a bullish context: the DOL is the next BSL above (price is drawn upward to take highs)
4. In a bearish context: the DOL is the next SSL below (price is drawn downward to take lows)

### Why it matters
The DOL helps the agent set realistic take-profit targets. Instead of arbitrary pip targets, the agent targets the next liquidity pool — because that is where price is naturally heading.

**NEXT ACTION:**
→ After determining HTF bias and identifying liquidity, determine the DOL
→ Use the DOL as the primary take-profit target
→ If the DOL is too far away for the risk/reward to work → the trade may not be viable

---
---

# ═══════════════════════════════════════════════════════════════
# SECTION E: LIQUIDITY SWEEP → REACTION
# ═══════════════════════════════════════════════════════════════

This section is CRITICAL. A liquidity sweep is the event that often initiates the trade sequence. But a sweep by itself does NOT automatically mean reversal.

---

## E.1 — WHAT IS A LIQUIDITY SWEEP?

### Definition
A liquidity sweep (also called liquidity grab, stop hunt, or liquidity raid) occurs when price moves beyond a known liquidity level (swing high/low, equal highs/lows, PDH/PDL, etc.), triggers the resting orders, and then reverses away from that level.

### How it forms
1. Liquidity accumulates at a known level (e.g., below a swing low → SSL)
2. Price is driven toward that level (often during a kill zone or volatile session)
3. Price breaks beyond the level — this triggers all the resting stop-loss and stop orders
4. The triggered orders provide liquidity (volume) for institutional players to fill their positions on the other side
5. Once the institutional orders are filled, price reverses away from the level

### Detection rules (OHLC)
- Price's wick (not necessarily the body) breaks beyond a previously identified liquidity level
- The candle that breaks beyond the level closes BACK inside or near the level (the body does not sustain beyond)
- Alternatively: price breaks the level, moves slightly beyond, then the NEXT candle reverses aggressively (displacement)

### How to distinguish a GENUINE LIQUIDITY SWEEP from an ORDINARY BREAKOUT

| Liquidity Sweep | Genuine Breakout |
|---|---|
| Price breaks the level but quickly reverses | Price breaks the level and continues in the break direction |
| Wick beyond, body closes back inside | Body closes firmly beyond the level |
| Followed by displacement in the opposite direction | Followed by continuation and retest of the broken level as new support/resistance |
| Often occurs during kill zones or news events | Can occur at any time with sustained volume |
| The break "looks" forced and is quickly rejected | The break is accompanied by volume and follow-through |

### Critical Rule
**A liquidity sweep alone does NOT mean reversal.** The sweep is just step 1. The agent must observe what happens AFTER the sweep to determine whether a trade opportunity exists.

---

## E.2 — THE COMPLETE SWEEP → ENTRY SEQUENCE

This is the most important sequence in the entire knowledge base.

```
STEP 1: Liquidity exists
  └── BSL above a swing high / EQH / PDH
  └── SSL below a swing low / EQL / PDL

STEP 2: Price approaches the liquidity
  └── Price moves toward the identified liquidity level
  └── This is expected — price is drawn to liquidity

STEP 3: Liquidity is swept (taken)
  └── Price breaks beyond the level
  └── Stop orders are triggered
  └── Check: did price CLOSE beyond, or just wick beyond?

STEP 4: Observe the reaction
  └── THIS IS THE KEY STEP
  └── After the sweep, what happens?
  
  IF: Price reverses aggressively (displacement) after the sweep
  → PROCEED to Step 5
  
  IF: Price continues beyond the level with strength
  → This was a genuine breakout, NOT a sweep → NO reversal trade

STEP 5: Check for displacement
  └── Is there a strong, aggressive candle moving away from the sweep level?
  └── Is the candle body significantly larger than average?
  └── Does the displacement candle create an FVG? (see Section G)
  
  IF YES → PROCEED to Step 6
  IF NO → Weak reaction → Not a high-probability setup → WAIT

STEP 6: Check for structural change
  └── Did the displacement cause a CHoCH or MSS? (see Section B.4)
  └── Did a swing point from the previous trend get broken?
  
  IF YES → PROCEED to Step 7
  IF NO → The reaction is not strong enough to confirm a reversal → WAIT or SKIP

STEP 7: Identify FVG / OB / POI
  └── The displacement move should have created:
      └── An FVG (gap between candles — see Section G)
      └── An OB at the origin of the displacement (see Section F)
  └── Mark these zones as potential entry areas

STEP 8: Wait for retracement
  └── After the displacement, price often retraces to "fill" the FVG or retest the OB
  └── This retracement is the entry opportunity
  └── DO NOT chase the displacement move — wait for the pullback

STEP 9: Entry confirmation
  └── When price reaches the FVG/OB zone, look for:
      └── Candlestick confirmation (engulfing, pin bar, rejection candle at the zone)
      └── LTF CHoCH/MSS confirming the direction
      └── Rejection of the zone (price touches the zone and immediately moves away)

STEP 10: Execute the trade
  └── Entry: at the FVG/OB zone with confirmation
  └── Stop Loss: beyond the sweep extreme (the furthest point price reached during the sweep)
  └── Take Profit: at the next liquidity target in the opposite direction (DOL)
  └── Risk/Reward: must meet minimum R:R requirement (at least 1.5:1, ideally 2:1+)
  └── Position Size: calculated based on account risk and SL distance (see Section K)
```

### What can go wrong at each step

| Step | What can go wrong |
|---|---|
| Step 3 | Price might not sweep. It might reverse before reaching the liquidity level. |
| Step 4 | Price might continue through the level (genuine breakout, not a sweep). |
| Step 5 | Displacement might be weak or absent → low-probability setup. |
| Step 6 | No structural change → the trend continues, sweep was just a brief spike. |
| Step 8 | Price might not retrace to the FVG/OB → missed entry. This is OK. Better to miss than force. |
| Step 9 | No confirmation at the zone → DO NOT ENTER. Walk away. |

**NEXT ACTION after observing a sweep:**
→ Follow Steps 4-10 above
→ If ANY step fails → do not trade
→ The agent must have discipline to walk away when the sequence is incomplete

---
---

# ═══════════════════════════════════════════════════════════════
# SECTION F: ORDER BLOCKS
# ═══════════════════════════════════════════════════════════════

---

## F.1 — WHAT IS AN ORDER BLOCK?

### Definition
An Order Block (OB) is the last candle (or cluster of candles) of the opposite color before a significant displacement move. It represents the area where institutional/smart money participants placed their orders before driving price aggressively in one direction.

### Why it matters
When institutions initiate a large position, they cannot fill it all at once without moving the market against themselves. They accumulate orders in a zone (the OB), then trigger a displacement move. If price returns to that zone later, the remaining unfilled institutional orders may still be resting there — making it a high-probability zone for price to react again.

### Critical clarification
An OB is NOT simply "the last red candle before a green move" or "where institutions placed orders." That is an oversimplification. The agent must verify that the candle/zone in question satisfies ALL of the following conditions.

---

## F.2 — BULLISH ORDER BLOCK

### What is it?
A bullish OB is the last bearish (red/down) candle before a significant bullish displacement move.

### Formation conditions (ALL must be met)
1. There is a bearish candle (or a cluster of bearish candles)
2. The very next candle (or sequence) is a strong bullish displacement move
3. The displacement must be meaningful — a large body candle that moves aggressively upward
4. The displacement should ideally break a structural level (BOS or MSS) or follow a liquidity sweep (SSL)
5. The displacement should create an FVG (see Section G)

### How to identify the relevant candle
1. Find a strong bullish displacement move on the chart
2. Look at the candle immediately BEFORE the displacement
3. If that candle is bearish → its entire range (high to low) is the bullish OB zone
4. If there are multiple consecutive bearish candles before the displacement, the OB can be the last one, or the entire cluster (different practitioners use different rules — primary ICT approach uses the last opposing candle)

### The OB zone
- **Upper boundary**: The HIGH of the last bearish candle before displacement
- **Lower boundary**: The LOW of the last bearish candle before displacement
- **Optimal entry within the OB**: The 50% level of the OB (midpoint) — sometimes called the "mean threshold"

### Detection rules (OHLC)
```
For candle at index i:
1. Candle[i] is bearish: Close[i] < Open[i]
2. Candle[i+1] is bullish with displacement: 
   - Close[i+1] > Open[i+1]
   - Body of Candle[i+1] > 2× average body of last 20 candles (displacement)
3. Candle[i+1] closes above Candle[i]'s high (or at least at its high)
4. Ideally: the move breaks a structural level (previous swing high)

If all conditions met:
  Bullish OB Zone = [Low[i], High[i]]
  OB Midpoint = (Low[i] + High[i]) / 2
```

---

## F.3 — BEARISH ORDER BLOCK

### What is it?
A bearish OB is the last bullish (green/up) candle before a significant bearish displacement move.

### Formation conditions (ALL must be met)
1. There is a bullish candle (or cluster)
2. The next candle/sequence is a strong bearish displacement move
3. Displacement breaks a structural level or follows a BSL sweep
4. Creates an FVG

### The OB zone
- **Upper boundary**: The HIGH of the last bullish candle before displacement
- **Lower boundary**: The LOW of the last bullish candle before displacement

### Detection rules (OHLC)
```
For candle at index i:
1. Candle[i] is bullish: Close[i] > Open[i]
2. Candle[i+1] is bearish with displacement:
   - Close[i+1] < Open[i+1]
   - Body of Candle[i+1] > 2× average body of last 20 candles
3. Candle[i+1] closes below Candle[i]'s low (or at its low)
4. Ideally: breaks a structural level (previous swing low)

If all conditions met:
  Bearish OB Zone = [Low[i], High[i]]
  OB Midpoint = (Low[i] + High[i]) / 2
```

---

## F.4 — VALID vs INVALID vs MITIGATED ORDER BLOCKS

### Valid (Fresh) Order Block
- Has NOT been revisited by price since its formation
- The displacement that created it was strong (with FVG and structural break)
- It has not been "touched" — price has not returned to the zone yet
- Fresh OBs have the highest probability of producing a reaction

### Mitigated Order Block
- Price HAS returned to the OB zone and reacted from it
- The institutional orders that were resting there have been partially or fully filled ("mitigated")
- A mitigated OB is weaker — it may still produce a reaction, but each subsequent visit weakens it
- Rule of thumb: an OB that has been tested 2+ times is considered significantly weakened

### Invalid Order Block
An OB is invalidated when:
- Price CLOSES through the OB zone entirely (not just wicks through)
- The displacement that created it was weak (no FVG, no structural break)
- The OB was in the wrong context (e.g., a bearish OB in a strongly bullish HTF without confluence)

---

## F.5 — BREAKER BLOCK (BB)

### What is it?
A Breaker Block is a former Order Block that was invalidated (price closed through it) and now acts as a zone on the OPPOSITE side. It "breaks" the original OB's role.

### How it forms
1. A bullish OB forms (last bearish candle before a bullish displacement)
2. Price eventually returns and closes BELOW the bullish OB → the OB is invalidated
3. The zone that was a bullish OB now becomes a bearish Breaker Block → it may act as resistance

### Why it matters
When an OB is invalidated, the traders who entered at that OB are now trapped. Their stop-losses are still in the market. When price returns to the zone from the other side, those stops provide liquidity, and the zone can now act as a reaction point in the opposite direction.

### Detection rules
1. Identify a previously valid OB
2. Check if price subsequently closed through the entire OB zone
3. If yes → the OB is now a Breaker Block
4. When price returns to the Breaker Block zone from the opposite side → potential reaction

**NEXT ACTION after identifying a Breaker Block:**
→ Use it as a potential entry zone in the direction opposite to the original OB
→ Require confirmation (candlestick pattern, LTF structure shift) at the zone
→ SL beyond the Breaker Block zone
→ TP at the next liquidity target

---

## F.6 — MITIGATION BLOCK (MB)

### What is it?
A Mitigation Block is an area where previous institutional orders that were "on the wrong side" (a losing institutional position) are mitigated (closed out). When price returns to this zone, the institutions close their losing positions, creating a reaction.

### How it forms
1. A bullish move occurs, creating a swing high
2. Price reverses and creates a bearish structure
3. During the reversal, the area near the original bullish entry point becomes a mitigation block
4. When price returns to this zone, institutions close their remaining long positions (mitigate their loss), providing selling pressure

### Practical use
Mitigation blocks function similarly to OBs but have a different origin story. The agent can treat them as secondary POIs (Points of Interest) after OBs and FVGs.

---

## F.7 — REJECTION BLOCK (RB)

### What is it?
A Rejection Block is formed by a candle with a long wick that represents rejection at a level. The wick area (the price zone covered by the wick but not the body) becomes a potential reaction zone.

### How to identify
1. Find a candle with an unusually long wick
2. The wick zone = the area between the body extreme and the wick tip
3. If the wick represents rejection from a key level (OB, liquidity, FVG) → Rejection Block

### Use
The rejection block zone can act as a secondary entry area when price returns to it. It is less reliable than a standard OB but can provide confluence with other concepts.

---

## F.8 — ORDER BLOCK RELATIONSHIPS

### OB ↔ Displacement
An OB REQUIRES displacement to be valid. Without a strong, aggressive move following the OB candle, it is just a random candle — not an OB.

### OB ↔ BOS/MSS
The displacement from an OB should ideally break a structural level. An OB whose displacement breaks structure is significantly stronger than one that does not.

### OB ↔ Liquidity
An OB often forms after a liquidity sweep. The sequence: liquidity swept → OB formed → displacement → BOS/MSS. The liquidity sweep provides the "fuel" (volume) for the institutional order placement at the OB.

### OB ↔ FVG
The displacement from an OB typically creates an FVG. The FVG and OB zones may overlap or be adjacent. Both are valid entry zones, but the OB is generally considered the stronger zone.

### OB ↔ Premium/Discount
- A bullish OB in DISCOUNT is stronger than one in premium
- A bearish OB in PREMIUM is stronger than one in discount

### Entry at an OB
1. Price returns to the OB zone
2. Look for entry confirmation: LTF CHoCH/MSS, engulfing pattern, rejection candle
3. Entry at: the OB zone (ideally at the 50% level or at the FVG within the OB)
4. SL: beyond the OB zone (below the OB low for bullish, above the OB high for bearish)
5. TP: at the next liquidity target (DOL)

### Invalidation
- If price CLOSES beyond the OB zone → it is invalidated
- The remaining institutional orders have been overwhelmed
- Consider the zone as a potential Breaker Block instead

**NEXT ACTION when OB is identified:**
→ Check if it is fresh (untested) or mitigated (already tested)
→ Check the displacement that created it (was it strong? Did it create an FVG?)
→ Check if a liquidity sweep preceded it
→ Check if it broke structure (BOS/MSS)
→ Determine if it is in premium or discount
→ Wait for price to return to the OB zone
→ Seek entry confirmation at the zone
→ If confirmed → enter with SL beyond OB and TP at DOL
→ If price closes through the OB → it is invalidated → look for Breaker Block

---
---

# ═══════════════════════════════════════════════════════════════
# SECTION G: FAIR VALUE GAP (FVG) / IMBALANCE
# ═══════════════════════════════════════════════════════════════

---

## G.1 — WHAT IS A FAIR VALUE GAP?

### Definition
A Fair Value Gap (FVG) is a three-candle pattern where the middle candle's body is so large (displacement) that it creates a gap in price between the first and third candle. This gap represents an area where only one side of the market was active — price moved so fast that trading was one-sided, creating an "imbalance" that price may return to fill.

### Why it matters
FVGs represent inefficient price delivery. In the ICT/SMC framework, price tends to return to FVGs to "rebalance" — to fill the gap where fair value was not established. This makes FVGs excellent potential entry zones.

---

## G.2 — BULLISH FVG

### What is it?
A bullish FVG forms during a strong upward displacement move. It is the gap between:
- The HIGH of candle 1 (the candle before the displacement)
- The LOW of candle 3 (the candle after the displacement)

Where the LOW of candle 3 is HIGHER than the HIGH of candle 1, creating a gap.

### Detection rules (OHLC)
```
Three consecutive candles: [1], [2], [3]

Bullish FVG exists if:
  Low[3] > High[1]

FVG Zone:
  Upper boundary = Low[3]
  Lower boundary = High[1]
  
Consequent Encroachment (CE) = midpoint of the FVG = (Low[3] + High[1]) / 2
```

### Visual
```
         ┌────┐
    [3]  │    │  Low[3] ─── FVG Upper Boundary
         └────┘
    ══════════════  ← FVG ZONE (the gap)
         ┌────┐
    [2]  │████│  ← DISPLACEMENT candle (large body)
         │████│
         └────┘
    ══════════════  
         ┌────┐
    [1]  │    │  High[1] ─── FVG Lower Boundary
         └────┘
```

---

## G.3 — BEARISH FVG

### What is it?
A bearish FVG forms during a strong downward displacement move. It is the gap between:
- The LOW of candle 1
- The HIGH of candle 3

Where the HIGH of candle 3 is LOWER than the LOW of candle 1.

### Detection rules (OHLC)
```
Three consecutive candles: [1], [2], [3]

Bearish FVG exists if:
  High[3] < Low[1]

FVG Zone:
  Upper boundary = Low[1]
  Lower boundary = High[3]
  
Consequent Encroachment (CE) = midpoint = (Low[1] + High[3]) / 2
```

---

## G.4 — FVG FILL / MITIGATION

### What is it?
When price returns to the FVG zone and trades through part or all of it, the FVG is being "filled" or "mitigated."

### Levels of fill
- **Partial fill**: Price enters the FVG zone but reverses before reaching the opposite boundary → the FVG is partially mitigated
- **CE fill**: Price reaches the Consequent Encroachment (50% of the FVG) → a common target/reaction point
- **Full fill**: Price passes through the entire FVG zone → the imbalance is fully rebalanced

### What it means
- If price enters the FVG and immediately reverses → the FVG is acting as support/resistance → potential entry confirmation
- If price fills the FVG completely and continues → the FVG has been invalidated → the setup is gone

---

## G.5 — INVERSE FVG (IFVG)

### What is it?
An Inverse FVG occurs when a regular FVG is filled/invalidated, and the zone that was previously a gap now acts as a zone on the OPPOSITE side.

### How it works
1. A bullish FVG forms (gap between candle 1 high and candle 3 low)
2. Price returns and fills the FVG completely (passes through the entire zone)
3. Now, the zone acts as a potential resistance area (inverse role)

### Practical use
Similar to how an invalidated OB becomes a Breaker Block, an invalidated FVG can become an Inverse FVG. It is a secondary concept — the agent should prioritize fresh FVGs and OBs over IFVGs.

---

## G.6 — WHAT MAKES AN FVG MORE MEANINGFUL?

Not all FVGs are worth trading. An FVG is more meaningful when:

1. **The displacement was strong**: A tiny FVG from a weak candle is less reliable
2. **It was created by a structural break**: An FVG formed during a BOS or MSS is significant
3. **It followed a liquidity sweep**: An FVG that formed after BSL/SSL was swept has institutional backing
4. **It aligns with an OB**: When the FVG overlaps with or is adjacent to an OB → high-confluence zone
5. **It is in the correct premium/discount zone**: A bullish FVG in discount is stronger; a bearish FVG in premium is stronger
6. **HTF alignment**: A LTF FVG within an HTF OB/FVG = powerful confluence

### What makes an FVG less meaningful
1. Formed during low-volume conditions (Asian session for forex)
2. No displacement — the "gap" is tiny
3. No structural break associated with it
4. Against the HTF bias
5. Already partially filled multiple times

---

## G.7 — FVG DECISION TREE: "WHAT SHOULD THE AGENT CHECK NEXT?"

```
FVG Detected
│
├── WHY did it form?
│   ├── Was there displacement? → YES: proceed / NO: weak FVG, deprioritize
│   ├── Was liquidity swept before it? → YES: strong context / NO: less significant
│   └── Did it cause a BOS/MSS? → YES: high significance / NO: moderate
│
├── WHERE is it?
│   ├── Premium or Discount? → Bullish FVG in discount = strong / Bullish FVG in premium = weak
│   ├── Does it overlap with an OB? → YES: high confluence
│   └── Does it align with an HTF zone? → YES: very strong
│
├── Is it FRESH?
│   ├── Has price returned to it? → NO: fresh (best) / YES: partially mitigated (weaker)
│   └── Has it been fully filled? → YES: invalidated
│
├── WAIT for price to retrace to the FVG zone
│   ├── Price enters the FVG → look for confirmation
│   ├── Confirmation present → ENTER
│   │   ├── Entry: at the FVG zone (ideally near CE or OB overlap)
│   │   ├── SL: beyond the FVG (and beyond the OB if they overlap)
│   │   └── TP: next liquidity target (DOL)
│   │
│   └── Confirmation absent → DO NOT ENTER
│
└── If price closes through the entire FVG → INVALIDATED → consider IFVG
```

---
---

# ═══════════════════════════════════════════════════════════════
# SECTION H: SUPPLY & DEMAND
# ═══════════════════════════════════════════════════════════════

---

## H.1 — WHAT IS SUPPLY AND DEMAND?

### Definition
Supply and Demand is a traditional technical analysis concept that identifies zones where buying (demand) or selling (supply) pressure was historically strong enough to cause a significant price reversal.

- **Demand Zone**: An area where price previously reversed upward with strength. Buyers overwhelmed sellers here.
- **Supply Zone**: An area where price previously reversed downward with strength. Sellers overwhelmed buyers here.

### How They Form

Supply and Demand zones are classified by the price pattern that created them:

| Pattern | Type | Description |
|---|---|---|
| **Rally-Base-Rally (RBR)** | Demand (continuation) | Price rallies up, pauses/consolidates (base), then rallies again. The base is a demand zone. |
| **Drop-Base-Drop (DBD)** | Supply (continuation) | Price drops, pauses/consolidates, then drops again. The base is a supply zone. |
| **Rally-Base-Drop (RBD)** | Supply (reversal) | Price rallies up, pauses, then drops. The base is a supply zone where sellers took control. |
| **Drop-Base-Rally (DBR)** | Demand (reversal) | Price drops, pauses, then rallies. The base is a demand zone where buyers took control. |

### Zone Identification
1. The zone is the "base" area — the consolidation between the two moves
2. The zone extends from the low of the base to the high of the base
3. The stronger the move away from the base, the stronger the zone

---

## H.2 — FRESH vs TESTED ZONES

### Fresh Zone
A zone that price has not yet revisited since it formed. The institutional orders that were placed there may still be partially unfilled. Fresh zones have the highest probability of producing a reaction.

### Tested Zone
A zone that price has already revisited. Each time price returns to a zone and reacts, some of the resting orders are filled. With each test, the zone weakens.

### Multiple Tests
- 1st retest: Zone is still strong, good probability of reaction
- 2nd retest: Zone is weakening
- 3rd+ retest: Zone is significantly depleted — avoid trading it

---

## H.3 — SUPPLY/DEMAND vs ORDER BLOCKS — SIMILARITIES AND DIFFERENCES

| Aspect | Supply/Demand (Traditional) | Order Block (ICT/SMC) |
|---|---|---|
| **Origin** | Classical technical analysis | ICT / Smart Money Concepts |
| **Definition** | Zones of historical buying/selling pressure | The last opposing candle before displacement |
| **Formation** | Based on base patterns (RBR, DBD, etc.) | Based on specific candle + displacement + structural break |
| **Validation requires** | Strong departure from the zone | Displacement + FVG + structural break + liquidity context |
| **Granularity** | Zone can be larger (entire base area) | Zone is typically a single candle or small cluster |
| **Context dependency** | Less emphasis on liquidity and structure | Heavily dependent on liquidity, structure, and premium/discount |
| **Overlap** | S/D zones often contain OBs within them | OBs are a more refined version of the same underlying concept |

### Practical Guidance for the Agent
- Use OBs as the PRIMARY zone identification method (ICT/SMC framework)
- Use S/D zone analysis as SUPPLEMENTARY confirmation
- If a S/D zone and an OB overlap → high-confluence area → stronger zone
- Do not let S/D analysis contradict the ICT/SMC structural framework

**NEXT ACTION:**
→ Identify S/D zones using base patterns
→ Cross-reference with OB identification
→ Use overlapping zones as high-probability entry areas
→ Apply the same confirmation, invalidation, and entry rules as OBs

---
---

# ═══════════════════════════════════════════════════════════════
# SECTION I: ORDER FLOW
# ═══════════════════════════════════════════════════════════════

---

## I.1 — WHAT IS ORDER FLOW?

### Definition
Order flow refers to the actual buying and selling activity occurring in the market — who is buying, who is selling, and with what aggression. In a broader sense, order flow analysis attempts to understand the imbalance between buying and selling pressure.

### Components

| Concept | What It Means |
|---|---|
| **Buying pressure** | More aggressive buyers than sellers. Market buy orders are hitting the ask. Price tends to move up. |
| **Selling pressure** | More aggressive sellers than buyers. Market sell orders are hitting the bid. Price tends to move down. |
| **Aggression** | The use of market orders (immediate execution) rather than limit orders (passive). Aggression = conviction. |
| **Absorption** | One side is placing large limit orders that "absorb" the other side's aggression. Price does not move despite heavy buying/selling. This often precedes a reversal. |
| **Displacement** | In ICT/SMC terms, displacement is visible order flow — a strong, aggressive candle shows that one side overwhelmed the other. It is order flow made visible on the chart without needing order-flow tools. |

### How Order Flow Supports or Contradicts a Setup

| Scenario | Order Flow Signal | Meaning |
|---|---|---|
| Price at a bullish OB, buying pressure increases | **Supporting** | Confirms the OB is being defended by buyers |
| Price at a bullish OB, selling pressure continues | **Contradicting** | The OB may not hold; sellers are still dominant |
| Strong displacement candle | **Confirming aggression** | One side has taken control — order flow aligns with the move |
| Price breaks a level but with very weak candles | **Weak order flow** | The breakout may fail; insufficient conviction |

### Momentum as Visible Order Flow
For the agent, the primary way to assess order flow is through **candle structure**:
- Large bodies with small wicks = strong order flow in the body's direction
- Small bodies with large wicks = contested order flow / indecision
- Multiple consecutive candles in one direction = sustained order flow
- A sudden displacement candle after slow movement = institutional order flow entering

### Market Orders vs Limit Orders

| Order Type | Role in Order Flow |
|---|---|
| **Market Orders** | Aggressive. They execute immediately at the current price. They move price. |
| **Limit Orders** | Passive. They wait at a specific price. They provide liquidity but do not move price on their own. |

In the context of OBs and FVGs:
- The OB zone likely contains resting limit orders (institutional orders waiting to be filled)
- When price returns to the OB, market orders (from new participants) interact with those limit orders
- If the limit orders (institutional) are larger than the market orders → price reacts from the OB
- If the market orders overwhelm the limit orders → the OB is invalidated

**NEXT ACTION:**
→ Use displacement candles as the primary order flow indicator
→ Verify that displacement aligns with the expected direction at key zones
→ If a key zone (OB/FVG) does not produce displacement in the expected direction → the zone may be failing
→ Do NOT require specialized order flow tools — candle structure is sufficient for this framework

---
---

# ═══════════════════════════════════════════════════════════════
# SECTION J: ORDER TYPES
# ═══════════════════════════════════════════════════════════════

---

## J.1 — ALL ORDER TYPES

### Market Order
**What it does:** Executes immediately at the current best available price.
**Where it is used:** When the agent needs immediate execution (e.g., confirming a setup and entering right now).
**Advantages:** Guaranteed execution.
**Disadvantages:** May experience slippage (execution at a slightly different price than expected, especially in volatile conditions).

### Limit Order
**What it does:** Places an order to execute at a specific price or better. It will only fill when price reaches that level.
**Where it is used:** When the agent wants to enter at a specific zone (OB, FVG) and is willing to wait for price to reach it.

#### Buy Limit
**What it does:** An order to BUY at a price BELOW the current market price.
**Where it is used:** Placing an entry at a bullish OB or FVG below the current price. The agent expects price to pull back to the zone and then bounce.
**Example:** Current price is 1.1000, bullish OB is at 1.0950. Place a Buy Limit at 1.0950.

#### Sell Limit
**What it does:** An order to SELL at a price ABOVE the current market price.
**Where it is used:** Placing an entry at a bearish OB or FVG above the current price. The agent expects price to rally to the zone and then drop.
**Example:** Current price is 1.1000, bearish OB is at 1.1050. Place a Sell Limit at 1.1050.

### Stop Order
**What it does:** An order that becomes a market order when price reaches a specified level.

#### Buy Stop
**What it does:** An order to BUY at a price ABOVE the current market price.
**Where it is used:** Breakout entries — the agent wants to buy if price breaks above a certain level.
**Note:** In ICT/SMC, Buy Stops above highs are often swept by smart money (they are BSL). The agent should be aware that breakout-style Buy Stop entries carry sweep risk.

#### Sell Stop
**What it does:** An order to SELL at a price BELOW the current market price.
**Where it is used:** Breakdown entries — entering a short if price breaks below a level.
**Note:** Sell Stops below lows = SSL. Same sweep risk applies.

### Stop-Limit Order
**What it does:** A combination — when price reaches the stop level, a limit order is placed. Provides more control than a stop order but risks non-execution if price moves too fast.

---

## J.2 — STOP LOSS (SL), TAKE PROFIT (TP), BREAK EVEN (BE)

### Stop Loss (SL)
**What it does:** An order that automatically closes a position at a predetermined loss level to limit risk.
**Rule:** EVERY trade MUST have a Stop Loss. NO EXCEPTIONS.

**Placement logic in ICT/SMC:**
- For a long trade: SL below the OB zone, or below the sweep extreme (the lowest point of the liquidity sweep)
- For a short trade: SL above the OB zone, or above the sweep extreme
- SL should be at a level where, if reached, the trade thesis is invalidated

### Take Profit (TP)
**What it does:** An order that automatically closes a position at a predetermined profit level.
**Rule:** EVERY trade MUST have a Take Profit.

**Placement logic in ICT/SMC:**
- Target the next liquidity pool (DOL — Draw on Liquidity)
- Or target the next OB/FVG on the opposing side
- Or target a structural level (previous swing high/low)

### Break Even (BE)
**What it does:** Moving the SL to the entry price after the trade has moved in your favor, ensuring at minimum a zero-loss outcome.

**When to move to BE:**
- After price has moved at least 1R in your favor (covered the distance of the initial risk)
- After a structural confirmation in your direction (LTF BOS)
- NOT prematurely — moving to BE too early risks being stopped out on a normal pullback

### Trailing Stop
**What it does:** A stop-loss that moves in your favor as price moves. It "trails" the price by a fixed distance or based on structural levels.
**When to use:** In a strongly trending market where you want to capture extended moves (relevant for the "high conviction hold" scenario).

---
---

# ═══════════════════════════════════════════════════════════════
# SECTION K: RISK MANAGEMENT
# ═══════════════════════════════════════════════════════════════

---

## K.1 — RISK PER TRADE

### Rule
Never risk more than a fixed percentage of your account on a single trade. This is the most fundamental rule of trading.

| Account Size | Risk Per Trade |
|---|---|
| ≤ $2,000 | 2% (max $40 risk per trade) |
| > $2,000 | 1.5% |

### Why
Even the best setup can fail. If the agent risks too much on one trade and it fails, the damage to the account can be devastating. By limiting risk per trade, the agent ensures it can survive losing streaks without significant equity destruction.

---

## K.2 — POSITION SIZE CALCULATION

This is the formula the agent MUST use for every trade:

```
Step 1: Determine risk amount
  Risk Amount = Account Balance × Risk Percentage
  Example: $1,000 × 2% = $20

Step 2: Determine stop-loss distance
  SL Distance (in pips) = |Entry Price - Stop Loss Price| / Pip Size
  Example: Entry at 1.1000, SL at 1.0950 → 50 pips (for forex)

Step 3: Calculate position size
  Position Size (lots) = Risk Amount / (SL Distance × Pip Value per lot)
  Example: $20 / (50 pips × $10/pip) = 0.04 lots

Step 4: Round down to available lot increment
  Example: 0.04 lots → 0.04 (if micro lots available)
```

### Critical Rule
A technically valid setup does NOT mean the trade is financially acceptable. If the SL distance is so wide that the required position size is below the minimum lot size, the trade cannot be taken. If the R:R is below 1.5:1, the trade should not be taken regardless of how good the setup looks.

---

## K.3 — RISK:REWARD RATIO (R:R)

### Calculation
```
R:R = (TP Distance) / (SL Distance)

Example:
  Entry: 1.1000
  SL: 1.0950 (50 pips risk)
  TP: 1.1100 (100 pips reward)
  R:R = 100/50 = 2:1
```

### Minimum Requirement
- Minimum R:R = 1.5:1
- Ideal R:R = 2:1 or higher
- If R:R < 1.5 → DO NOT take the trade, regardless of setup quality

---

## K.4 — MAXIMUM DRAWDOWN AND DAILY LIMITS

| Rule | Threshold | Action |
|---|---|---|
| Max drawdown from peak equity | 5% | HALT ALL TRADING |
| Daily drawdown | 2.5% | Reduce position sizes by 50% |
| Daily drawdown | 4% | HALT trading for the rest of the day |

---

## K.5 — LEVERAGE AND MARGIN

### Leverage
Leverage allows trading a larger position than the account balance would normally allow. While it amplifies profits, it equally amplifies losses.

**Rule:** The agent should calculate position size based on RISK, not on leverage. Leverage is a tool, not a strategy. The position size formula (K.2) inherently controls risk regardless of leverage.

### Margin
The amount of equity required to maintain an open position. If equity falls below the required margin → margin call → positions may be force-closed.

---

## K.6 — TRADE INVALIDATION vs FINANCIAL INVALIDATION

| Type | Meaning |
|---|---|
| **Trade Invalidation** | The setup conditions are no longer met (e.g., price closes through the OB, FVG is fully filled, structure invalidated). The trade idea is wrong. Exit or do not enter. |
| **Financial Invalidation** | The SL is hit. The maximum acceptable loss for this trade has been reached. Exit automatically. |

Both are reasons to exit. The agent must respect both.

**NEXT ACTION:**
→ Before every trade: calculate position size using the formula in K.2
→ Verify R:R ≥ 1.5:1
→ If position size < minimum lot → trade is not financially viable → SKIP
→ If daily drawdown thresholds are approached → reduce or halt

---
---

# ═══════════════════════════════════════════════════════════════
# SECTION L: ACCUMULATION / DISTRIBUTION
# ═══════════════════════════════════════════════════════════════

---

## L.1 — ACCUMULATION

### What is it?
Accumulation is a phase where institutional/smart money participants are quietly building (accumulating) a large position before a significant move upward. Price appears to be moving sideways in a range, but beneath the surface, large buy orders are being filled.

### How it forms
1. Price enters a range (consolidation) after a downtrend or at a significant support level
2. Within the range, price tests the lower boundary multiple times
3. Each test of the lower boundary may include wicks below support (sweeping SSL / stop hunting) to trigger retail stop-losses and create liquidity for institutional buying
4. Volume may decrease during the range (lack of retail interest) while institutional orders quietly fill

### How to identify
- Price is in a clear range (support and resistance visible)
- Multiple tests of the lower boundary, often with wicks below
- Decreasing volatility over time (compression)
- False breakdowns below the range (springs/sweep)
- The range follows a prior downtrend

### What confirms accumulation
- A "Spring" (Wyckoff term): price briefly breaks below the range, sweeps SSL, then reverses back into the range → this is a liquidity sweep within accumulation
- After the Spring, price shows a "Sign of Strength" (SOS): a strong displacement move upward, often breaking the range's resistance

### What happens next
After accumulation is complete:
→ **Markup** phase begins
→ Price breaks above the range with displacement
→ This creates BOS, FVG, and OBs above the range
→ The breakout move is the expansion that follows the compression

---

## L.2 — DISTRIBUTION

### What is it?
Distribution is the opposite of accumulation. Institutional/smart money participants are quietly selling (distributing) their positions before a significant move downward. Price appears sideways, but large sell orders are being filled.

### How it forms
1. Price enters a range after an uptrend or at significant resistance
2. Multiple tests of the upper boundary
3. Wicks above resistance (sweeping BSL) to trigger retail stops and create sell liquidity
4. False breakouts above the range (upthrust)

### What happens next
After distribution is complete:
→ **Markdown** phase begins
→ Price breaks below the range with displacement
→ Creates BOS, FVG, OBs below the range

---

## L.3 — RE-ACCUMULATION AND RE-DISTRIBUTION

### Re-Accumulation
A period of consolidation within an existing uptrend. Price pauses, accumulates more, then continues upward. It looks like accumulation but occurs mid-trend rather than at the bottom.

### Re-Distribution
A period of consolidation within an existing downtrend. Price pauses, distributes more, then continues downward.

### How to distinguish from reversal patterns
- Re-accumulation occurs within a confirmed uptrend (HTF bullish) → expect continuation up
- Distribution occurs at the top of a trend → expect reversal down
- Check HTF structure: if HTF is still making HH/HL → likely re-accumulation, not distribution

### How liquidity behaves around ranges
Within any range (accumulation, distribution, or re-accumulation/distribution):
- BSL forms above the range high (stops from shorts + breakout buy stops)
- SSL forms below the range low (stops from longs + breakdown sell stops)
- Both sides build liquidity the longer the range persists
- Eventually, one side is swept (manipulation) before the expansion in the opposite direction

**NEXT ACTION when range is detected:**
→ Determine if it is accumulation (bottom of trend), distribution (top of trend), or re-accumulation/distribution (mid-trend)
→ Identify the liquidity building at both extremes
→ Wait for a sweep of one extreme (false breakout / spring / upthrust)
→ After the sweep, look for displacement in the opposite direction
→ The displacement confirms which type of range it was
→ Enter on a pullback to the FVG/OB created by the displacement move

---
---

# ═══════════════════════════════════════════════════════════════
# SECTION M: MANIPULATION
# ═══════════════════════════════════════════════════════════════

---

## M.1 — WHAT IS MANIPULATION?

### Definition
In the ICT/SMC framework, manipulation refers to intentional price moves designed to trigger retail traders' stop-losses, create liquidity, and induce retail traders into the wrong position. These moves are orchestrated by institutional/smart money participants to accumulate or distribute positions at favorable prices.

### Critical Rule
**NOT every wick, false breakout, or unexpected move is manipulation.** The agent must distinguish between:
1. Genuine volatility / normal market noise
2. A legitimate breakout
3. A liquidity sweep / manipulation event

---

## M.2 — TYPES OF MANIPULATION

### Liquidity Manipulation (Stop Hunt / Liquidity Raid)
- Price is driven to a known liquidity level (EQH, EQL, PDH, PDL, swing H/L)
- Stops are triggered
- Price reverses

### False Breakout / Fakeout
- Price appears to break a key level (support/resistance, range boundary)
- Retail traders enter in the breakout direction
- Price reverses, stopping out the breakout traders
- The "breakout" was a liquidity grab

### Inducement
- A minor structure or pattern forms that looks tradeable on a lower timeframe
- Retail traders enter based on this pattern, placing stops at predictable locations
- Price hits those stops (sweeps the inducement liquidity) before moving to the actual target
- Inducement is essentially "bait" to lure traders into placing stops where institutions want them

### Judas Swing
- Specifically refers to a fake directional move at the start of a session (typically during Kill Zones)
- Price moves in one direction at the session open (the "Judas" move — deception)
- This move sweeps liquidity from the prior session's range
- Price then reverses aggressively in the opposite direction for the rest of the session

---

## M.3 — HOW TO DISTINGUISH MANIPULATION FROM GENUINE MOVES

| Feature | Manipulation / Liquidity Sweep | Genuine Breakout |
|---|---|---|
| **Price action after the break** | Quick reversal with displacement | Continuation and retest |
| **Candle behavior** | Wick beyond, body closes back inside | Body closes firmly beyond |
| **Follow-through** | Next candle reverses aggressively | Next candle continues in break direction |
| **Volume/displacement** | Displacement occurs in the OPPOSITE direction of the break | Displacement occurs in the SAME direction as the break |
| **Context** | Often occurs during kill zones, at obvious liquidity levels | Can occur at any time with fundamental backing |
| **Structure** | The break does NOT sustain — price returns inside the structure | The break creates new structural HH/LL |

### The Agent's Rule
1. When price breaks a level → do NOT immediately assume breakout OR manipulation
2. WAIT for the reaction after the break
3. If displacement follows in the OPPOSITE direction → likely manipulation / sweep → look for reversal setup
4. If displacement follows in the SAME direction with follow-through → likely genuine breakout → look for continuation setup

**NEXT ACTION when suspicious move detected:**
→ Was the move into a known liquidity level? → Check Section D
→ Did the move fail (wick beyond, close back inside)? → Likely sweep
→ After the sweep, is there displacement? → Check Section E
→ Did structure shift (CHoCH/MSS)? → Check Section B
→ If all align → potential trade setup in the opposite direction of the manipulation

---
---

# ═══════════════════════════════════════════════════════════════
# SECTION N: TRADING SESSIONS & TIMING
# ═══════════════════════════════════════════════════════════════

---

## N.1 — MAJOR TRADING SESSIONS

### Session Times (approximate, in UTC)

| Session | Approximate UTC Hours | Key Characteristics |
|---|---|---|
| **Asian Session (Tokyo)** | 00:00 – 08:00 UTC | Low volatility for forex. Establishes a range. Liquidity builds at the session high and low. |
| **London Session** | 07:00 – 16:00 UTC | High volatility, especially the first 2-3 hours. Often sweeps the Asian range. |
| **New York Session** | 12:00 – 21:00 UTC | High volatility, especially the first 2-3 hours. Often creates the day's directional move. |
| **London-NY Overlap** | 12:00 – 16:00 UTC | Highest volatility period. Maximum liquidity. Most significant moves often occur here. |

**Note:** Exact times depend on DST (Daylight Saving Time) in the relevant regions, the instrument being traded, and the broker's server time. The agent should adjust based on the specific instrument.

---

## N.2 — KILL ZONES (ICT)

Kill Zones are specific time windows within sessions where the highest probability ICT setups occur.

| Kill Zone | Time (EST / New York) | Time (approx. UTC) | Purpose |
|---|---|---|---|
| **London Kill Zone** | 02:00 – 05:00 EST | 07:00 – 10:00 UTC | Often sweeps the Asian session range. Look for manipulation + reversal setups. |
| **NY AM Kill Zone** | 08:30 – 11:00 EST | 13:30 – 16:00 UTC | Often completes the daily directional move. News releases often fall within this window. |
| **NY PM Kill Zone** | 13:30 – 16:00 EST | 18:30 – 21:00 UTC | Often retraces or continues the NY AM move. Good for re-entries. |

### Why Kill Zones Matter
- Most significant liquidity events (sweeps) happen during Kill Zones
- The Judas Swing often occurs at the start of the London or NY Kill Zone
- Setups taken outside Kill Zones have lower probability
- The Asian session typically BUILDS the range → London/NY sessions EXPLOIT that range

---

## N.3 — THE ASIAN RANGE

### What is it?
The price range established during the Asian session (from Asian session open to London open). This range represents consolidation.

### Why it matters
- BSL forms above the Asian Range high
- SSL forms below the Asian Range low
- London and NY sessions frequently sweep one end of the Asian Range before moving to the other

### Common pattern
```
Asian Session: Range forms [high, low]
London Open: Price sweeps one end (e.g., breaks below Asian low → takes SSL)
Then: Reverses with displacement → moves toward the other end (Asian high) and beyond
```

This pattern is the essence of the Judas Swing.

**NEXT ACTION:**
→ Mark the Asian range (high and low) before London open
→ At London/NY open, watch for a sweep of one end
→ If sweep occurs with displacement → potential trade in the opposite direction
→ Target: the opposite end of the Asian range, or beyond (to the next liquidity level)

---
---

# ═══════════════════════════════════════════════════════════════
# SECTION O: PREMIUM / DISCOUNT
# ═══════════════════════════════════════════════════════════════

---

## O.1 — DEALING RANGE, EQUILIBRIUM, PREMIUM, AND DISCOUNT

### Dealing Range
The range between the most recent significant swing high and swing low. This is the "field of play."

### Equilibrium
The 50% level of the dealing range. Calculated as:
```
Equilibrium = (Swing High + Swing Low) / 2
```

### Premium
The area ABOVE the equilibrium (above the 50% level). This is "expensive" territory.
- In an uptrend: price may briefly enter premium during a pullback → look for sells (or avoid buys)
- In a downtrend: price entering premium is a potential selling opportunity

### Discount
The area BELOW the equilibrium (below the 50% level). This is "cheap" territory.
- In an uptrend: price in discount is a buying opportunity
- In a downtrend: price may briefly enter discount during a pullback → look for buys (or avoid sells)

### The Rule
- **Buy in discount, sell in premium.**
- A bullish OB in discount is stronger than one in premium
- A bearish OB in premium is stronger than one in discount
- FVGs in the "right" zone (bullish FVG in discount, bearish FVG in premium) have higher probability

---

## O.2 — PREMIUM AND DISCOUNT ARRAYS

### Premium Arrays (zones/concepts found in premium — potential selling opportunities)
- Bearish Order Blocks
- Bearish FVGs
- BSL (liquidity above — may be swept before a drop)
- Supply zones

### Discount Arrays (zones/concepts found in discount — potential buying opportunities)
- Bullish Order Blocks
- Bullish FVGs
- SSL (liquidity below — may be swept before a rally)
- Demand zones

### How the Agent Should Use This
1. Determine the dealing range
2. Calculate the 50% level
3. Determine if current price is in premium or discount
4. Align trade direction with the zone:
   - In discount → look for long setups
   - In premium → look for short setups
5. Cross-reference with HTF bias:
   - HTF bullish + price in discount = ideal buy zone
   - HTF bearish + price in premium = ideal sell zone
   - HTF bullish + price in premium = wait for price to pull back to discount, or skip

**NEXT ACTION:**
→ Calculate premium/discount for the current dealing range
→ Only look for setups that align: longs in discount, shorts in premium
→ If a bullish setup appears in premium → it is less reliable → require extra confirmation or skip

---
---

# ═══════════════════════════════════════════════════════════════
# SECTION P: INDUCEMENT
# ═══════════════════════════════════════════════════════════════

---

## P.1 — WHAT IS INDUCEMENT?

### Definition
Inducement is the creation of minor structural patterns on a lower timeframe that "trick" retail traders into entering positions. The purpose is to generate liquidity (stops) at known levels before price moves to the actual target.

### How it works
1. Within a larger pullback (e.g., price pulling back in an uptrend), a minor swing low forms on the LTF
2. Retail traders see this minor low as "support" and place buy orders with stops below
3. This creates minor SSL (inducement liquidity) below that minor low
4. Price sweeps that minor low (takes the inducement) → triggers the retail stops → creates liquidity
5. After taking the inducement, price moves to the actual OB/FVG below → THIS is the real entry zone

### The Key Insight
Inducement is a "trap within a trap." The agent must recognize that the first obvious entry zone is often the inducement, and the real entry is deeper (at the actual OB/FVG/liquidity level beyond the inducement).

### Detection
1. Within a pullback, identify minor swing points on the LTF
2. These minor swings hold minor liquidity (inducement)
3. Expect price to sweep the inducement BEFORE reaching the actual HTF OB/FVG

### Internal Liquidity as Inducement
The minor swing points within a leg are internal structure. The liquidity at these minor swings = internal liquidity = inducement. Price sweeps the internal liquidity on its way to the external target.

**NEXT ACTION when inducement is identified:**
→ Do NOT place an entry at the inducement level (it will be swept)
→ Wait for price to sweep the inducement
→ Look for the ACTUAL OB/FVG below/above the inducement
→ Place the entry at the actual zone, with SL beyond the inducement sweep extreme

---
---

# ═══════════════════════════════════════════════════════════════
# SECTION Q: MARKET PHASES
# ═══════════════════════════════════════════════════════════════

---

## Q.1 — THE FOUR PHASES

### Accumulation
- Price consolidates in a range (usually after a downtrend)
- Institutional buyers accumulate positions
- Liquidity builds at both extremes of the range

### Manipulation
- Price breaks one extreme of the range (usually the one that creates the most liquidity for institutional purposes)
- This is the "Spring" (for accumulation) or "Upthrust" (for distribution)
- A fake breakout / liquidity sweep

### Distribution / Expansion
- After manipulation, price expands in the true direction
- This is the markup (after accumulation → up) or markdown (after distribution → down)
- The largest, most profitable moves occur during expansion

### AMD: Accumulation → Manipulation → Distribution (Power of Three / PO3)

This is the fundamental ICT cycle:

```
[ACCUMULATION]          [MANIPULATION]          [DISTRIBUTION/EXPANSION]
Price builds a range → Price sweeps one end → Price moves aggressively the other way

Example (Bullish):
Range forms at support → Price breaks below range (takes SSL) → Price reverses and rallies

Example (Bearish):
Range forms at resistance → Price breaks above range (takes BSL) → Price reverses and drops
```

### How the Agent Should Use Market Phases

1. **Identify the current phase:**
   - Is price in a range? → Accumulation or Distribution
   - Was liquidity just swept at the range extreme? → Manipulation phase
   - Is price moving aggressively away from the range? → Expansion phase

2. **Act accordingly:**
   - During accumulation → WAIT. Do not enter the range chop.
   - During manipulation → This IS the setup trigger. Look for displacement.
   - During expansion → This is where the trade runs. Enter on pullbacks to FVG/OB if not already in.
   - After expansion → Look for the next accumulation/distribution range.

### Phase Transitions

```
Accumulation → Manipulation (sweep of range low) → Markup (bullish expansion)
   ↓
Re-accumulation → Manipulation (minor sweep) → Continued Markup
   ↓
Distribution → Manipulation (sweep of range high) → Markdown (bearish expansion)
   ↓
Re-distribution → Manipulation (minor sweep) → Continued Markdown
   ↓
Accumulation (new cycle begins)
```

**NEXT ACTION when market phase is identified:**
→ If in Accumulation → identify the range, mark BSL/SSL at extremes, WAIT for manipulation
→ If Manipulation just occurred → look for displacement and MSS
→ If in Expansion → look for pullbacks to FVG/OB for entries; set TP at DOL
→ If Expansion is exhausting (slowing momentum, indecision candles at key levels) → prepare for the next accumulation/distribution phase

---
---

# ═══════════════════════════════════════════════════════════════
# SECTION R: ADVANCED SMC CONCEPTS
# ═══════════════════════════════════════════════════════════════

---

## R.1 — DISPLACEMENT

### Definition
Displacement is a rapid, aggressive price move characterized by one or more large-bodied candles with small or no wicks. It represents institutional/smart money entering the market with conviction.

### How to identify
- Candle body > 2× the average body of the last 20 candles
- Minimal wicks (< 20% of total candle range)
- Often creates an FVG
- Often breaks a structural level (BOS or MSS)

### Why it matters
Displacement is the primary confirmation signal in ICT/SMC. Without displacement, there is no institutional conviction. A setup without displacement is a weak setup.

### What it tells you
- Smart money has entered
- The direction of the displacement is the intended direction
- The FVG created by displacement is a re-entry zone
- The OB at the origin of displacement is a re-entry zone

**NEXT ACTION after displacement:**
→ Identify the FVG and OB created
→ Determine if it broke structure (BOS/MSS)
→ Wait for price to retrace to the FVG/OB
→ Enter with confirmation

---

## R.2 — MITIGATION

### What is it?
Mitigation refers to the process of institutional orders being filled (mitigated). When price returns to an OB or FVG, the orders resting there are filled — the zone is being "mitigated."

### Why it matters
Once a zone is fully mitigated, it has no more resting orders and will no longer produce a reaction. This is why fresh OBs/FVGs are prioritized over mitigated ones.

---

## R.3 — BALANCED PRICE RANGE (BPR)

### What is it?
A Balanced Price Range occurs when a bullish FVG and a bearish FVG overlap in the same price area. The overlapping zone represents a price area that has been balanced — both buyers and sellers have established fair value there.

### Why it matters
A BPR can act as a strong support/resistance zone because both sides of the market have acknowledged that price as fair.

### Detection
1. Identify a bullish FVG
2. Identify a bearish FVG
3. If they overlap → the overlapping zone is the BPR

---

## R.4 — VOLUME IMBALANCE

### What is it?
A gap between the close of one candle and the open of the next candle. Unlike an FVG (which involves 3 candles), a volume imbalance is a 2-candle event.

### Detection
- Bullish Volume Imbalance: Open[n] > Close[n-1] (gap up between consecutive candles)
- Bearish Volume Imbalance: Open[n] < Close[n-1] (gap down)

### Use
Volume imbalances act like minor FVGs — price may return to fill them. They are less significant than FVGs but can provide additional confluence.

---

## R.5 — LIQUIDITY VOID

### What is it?
An area on the chart where price moved so rapidly (extreme displacement) that there was virtually no trading activity. It is similar to an FVG but even more extreme — an "empty" zone.

### Why it matters
Liquidity voids are magnets — price may return aggressively to fill these voids because the market needs to establish fair value in that zone. They represent the most extreme imbalances.

---

## R.6 — OPENING RANGE

### What is it?
The price range established in the first 30-60 minutes of a trading session. In ICT methodology, the opening range of each Kill Zone is particularly important.

### Why it matters
The opening range establishes the initial boundary for the session. Price often sweeps one end of the opening range (manipulation) before moving to the other end (expansion).

---

## R.7 — DAILY AND WEEKLY BIAS

### What is it?
The expected directional movement for the current day or week, determined by HTF analysis.

### How to determine daily bias
1. Check Weekly/Daily structure (HH/HL = bullish, LH/LL = bearish)
2. Check where price is relative to the HTF dealing range (premium/discount)
3. Check the previous day's candle:
   - If previous day closed bullish in a bullish trend → bias remains bullish
   - If previous day closed with a long upper wick at resistance → possible bearish bias for today
4. Check the Asian range → which end is likely to be swept?

### How to determine weekly bias
1. Check Monthly/Weekly structure
2. Where is price relative to the monthly dealing range?
3. Was last week's high or low swept?
4. Is there a HTF OB/FVG being approached?

---

## R.8 — POWER OF THREE (PO3) / AMD

### What is it?
The Power of Three describes the three phases of every trading session or every candle:
1. **Accumulation**: The initial range/consolidation (often the Asian session for daily, or the opening range for a session)
2. **Manipulation**: The false move that sweeps liquidity (the Judas Swing, the stop hunt)
3. **Distribution**: The real move in the intended direction (the expansion, the trend move)

### Applied to a Daily Candle
- Open → Accumulation zone (where the candle begins)
- Manipulation → the wick that sweeps one direction (takes liquidity)
- Distribution → the body of the candle in the opposite direction (the real move)

### Applied to a Session
- Asian session → Accumulation (range forms)
- London open → Manipulation (sweeps one end of Asian range)
- NY session → Distribution (expansion in the true direction)

### How the Agent Should Use PO3
- At the start of a session: expect accumulation. DO NOT trade during this phase.
- Watch for the manipulation move (Judas Swing). This is the trigger.
- After manipulation: look for displacement and enter during the distribution phase.

---
---

# ═══════════════════════════════════════════════════════════════
# END OF MASTER KNOWLEDGE BASE
# ═══════════════════════════════════════════════════════════════

# This document should be used in conjunction with:
# - cheat_sheet.md (condensed quick-reference)
# - concept_relationships.md (how concepts connect)
# - next_action_rules.md (decision trees for each concept)
