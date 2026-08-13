# TRADING CONCEPTS — CONDENSED CHEAT SHEET
# Quick-Reference for the AI Trading Agent (ICT/SMC Framework)

> This is a condensed representation of the same information in master_knowledge_base.md.
> Use this for fast lookups. Refer to the master file for full explanations.

---

## CANDLESTICK PATTERNS (Quick Reference)

| Pattern | What It Looks Like | Meaningful When | NEXT ACTION |
|---|---|---|---|
| **Hammer** | Small body top, long lower wick (≥2× body) | At bullish OB / after SSL sweep | Wait for bullish confirmation candle, check HTF bias |
| **Shooting Star** | Small body bottom, long upper wick (≥2× body) | At bearish OB / after BSL sweep | Wait for bearish confirmation candle |
| **Doji** | Tiny body, wicks both sides | At any key level (OB, FVG, liquidity) | Wait for next candle's direction, do NOT trade the Doji |
| **Bullish Engulfing** | Bullish candle fully engulfs prior bearish candle | At bullish OB/FVG in discount | THIS is the entry confirmation → define SL/TP |
| **Bearish Engulfing** | Bearish candle fully engulfs prior bullish candle | At bearish OB/FVG in premium | THIS is the entry confirmation → define SL/TP |
| **Inside Bar** | Entire range within prior candle | At OB/FVG zone = compression | Wait for breakout direction |
| **Pin Bar** | Small body, one very long wick (≥66% range) | Wick pierces liquidity level | Treat as sweep + rejection, wait for follow-through |
| **Displacement Candle** | Large body, minimal wicks, > 2× avg body | Anywhere | Check if it created FVG, broke structure, followed a sweep |

⚠️ **Rule:** A candlestick pattern alone is NEVER a trade signal. It requires context (where + what happened before).

---

## MARKET STRUCTURE

| Concept | Definition | Detection | NEXT ACTION |
|---|---|---|---|
| **Swing High** | High > highs of ≥2 candles on each side | Compare adjacent candle highs | Label as HH or LH |
| **Swing Low** | Low < lows of ≥2 candles on each side | Compare adjacent candle lows | Label as HL or LL |
| **HH/HL** | Higher High / Higher Low | New swing > previous swing of same type | Uptrend confirmed → look for buy pullbacks |
| **LH/LL** | Lower High / Lower Low | New swing < previous swing of same type | Downtrend confirmed → look for sell pullbacks |
| **BOS** | Break of Structure (WITH trend) | Close beyond prev swing in trend direction | Continuation → look for pullback to FVG/OB |
| **CHoCH** | Change of Character (AGAINST trend, 1st time) | Close beyond prev swing against trend | Warning → wait for displacement + confirmation |
| **MSS** | Market Structure Shift (confirmed reversal) | CHoCH + displacement + FVG + liquidity sweep | Bias changed → trade new direction on pullback |
| **Internal Structure** | Minor swings within a leg | Smaller swings between major swings | Breaking these ≠ trend change |
| **External Structure** | Major swings defining the trend | Obvious swings on current TF | Breaking these = potential trend change |

**BOS vs CHoCH vs MSS:**
- BOS = same direction = continuation
- CHoCH = opposite direction = warning  
- MSS = CHoCH + displacement + sweep = confirmed shift

---

## MULTI-TIMEFRAME ANALYSIS

| Timeframe Role | Timeframes | What to Extract |
|---|---|---|
| **HTF (Bias)** | Weekly, Daily | Trend, major liquidity, major OB/FVG, dealing range, premium/discount |
| **MTF (Context)** | H4, H1 | Intermediate structure, confluence zones, specific approach to zones |
| **LTF (Entry)** | M15, M5, M1 | Entry confirmation (LTF CHoCH/MSS), precise entry, tight SL |

**Rule:** LTF trades MUST align with HTF bias.

---

## LIQUIDITY

| Concept | Location | What It Contains | NEXT ACTION |
|---|---|---|---|
| **BSL** | Above swing highs, EQH, PDH, PWH | Buy stops (short SLs + breakout buys) | Mark as target; if swept → watch for bearish displacement |
| **SSL** | Below swing lows, EQL, PDL, PWL | Sell stops (long SLs + breakdown sells) | Mark as target; if swept → watch for bullish displacement |
| **EQH** | Multiple highs at same level | Dense stop cluster | High-probability sweep target |
| **EQL** | Multiple lows at same level | Dense stop cluster | High-probability sweep target |
| **IRL** | Inside the dealing range | Minor swing liquidity | Fuel — swept before targeting ERL |
| **ERL** | At/beyond range extremes | Major swing/range liquidity | Destination — the actual target |
| **DOL** | Next significant liquidity pool | Draw on Liquidity | Use as TP target |

**Key:** Price moves FROM one liquidity pool TO another. IRL is fuel; ERL is the destination.

---

## LIQUIDITY SWEEP → REACTION SEQUENCE

```
1. Liquidity exists (BSL/SSL/EQH/EQL)
2. Price approaches → sweeps the level
3. OBSERVE REACTION:
   → Displacement in opposite direction? → PROCEED
   → Continuation through? → Genuine breakout → NO reversal trade
4. Check for displacement (strong candle, >2× avg body)
5. Check for structure change (CHoCH/MSS)
6. Identify FVG/OB created by the displacement
7. Wait for retracement to FVG/OB
8. Seek entry confirmation (engulfing, LTF CHoCH)
9. Enter: at FVG/OB | SL: beyond sweep extreme | TP: DOL
10. If ANY step fails → NO TRADE
```

---

## ORDER BLOCKS

| Type | Formation | Zone | Entry |
|---|---|---|---|
| **Bullish OB** | Last bearish candle before bullish displacement | [Low, High] of that candle | Buy when price retraces to zone |
| **Bearish OB** | Last bullish candle before bearish displacement | [Low, High] of that candle | Sell when price retraces to zone |
| **Fresh OB** | Untested (price hasn't returned) | — | Highest probability |
| **Mitigated OB** | Price has returned and reacted | — | Weaker with each test |
| **Invalidated OB** | Price CLOSED through entire zone | — | No longer valid; consider as Breaker Block |
| **Breaker Block** | Invalidated OB acting on opposite side | Same zone, opposite role | Trade the opposite direction |

**OB requires:** Displacement + FVG creation + ideally structural break + liquidity context.
**Entry:** At OB zone (50% level ideal) | **SL:** Beyond OB | **TP:** DOL
**Invalidation:** Price closes through entire OB zone.

---

## FAIR VALUE GAP (FVG)

| Type | Detection Rule | Zone |
|---|---|---|
| **Bullish FVG** | Low[candle3] > High[candle1] | [High[1], Low[3]] |
| **Bearish FVG** | High[candle3] < Low[candle1] | [High[3], Low[1]] |
| **CE** | Midpoint of FVG = (boundary1 + boundary2) / 2 | 50% of FVG |
| **IFVG** | Fully filled FVG acting on opposite side | Same zone, opposite role |

**FVG is stronger when:** Strong displacement + structural break + liquidity sweep preceded it + in correct premium/discount zone + overlaps with OB.
**Invalidated when:** Price closes completely through the FVG zone.

---

## PREMIUM / DISCOUNT

```
Dealing Range:  [Swing Low ──────── Swing High]
                          50% = Equilibrium
                 DISCOUNT ↓          ↑ PREMIUM

Rule: BUY in discount. SELL in premium.
```

| Setup | In Discount | In Premium |
|---|---|---|
| Bullish OB/FVG | ✅ Strong | ⚠️ Weak |
| Bearish OB/FVG | ⚠️ Weak | ✅ Strong |

---

## MARKET PHASES (AMD / PO3)

```
ACCUMULATION → MANIPULATION → DISTRIBUTION/EXPANSION
(Range forms)    (Sweep one end)   (Move to other end + beyond)
```

| Phase | Action |
|---|---|
| Accumulation | WAIT. Mark range extremes. |
| Manipulation | ALERT. Sweep occurred → look for displacement. |
| Expansion | TRADE. Enter on pullback to FVG/OB. |

---

## SESSION TIMING

| Session | UTC | Key Behavior |
|---|---|---|
| Asian | 00:00–08:00 | Builds range (accumulation). Mark high/low. |
| London | 07:00–16:00 | Often sweeps Asian range (manipulation). High volatility. |
| NY | 12:00–21:00 | Directional move (distribution/expansion). |
| London-NY Overlap | 12:00–16:00 | Maximum volatility. Best setups. |

**Kill Zones (EST):** London 02:00–05:00 | NY AM 08:30–11:00 | NY PM 13:30–16:00

---

## RISK MANAGEMENT

| Rule | Value |
|---|---|
| Risk per trade (≤$2000) | 2% |
| Risk per trade (>$2000) | 1.5% |
| Minimum R:R | 1.5:1 |
| Max drawdown from peak | 5% → HALT |
| Daily DD reduce | 2.5% → half size |
| Daily DD halt | 4% → stop trading |

**Position Size Formula:**
```
Lots = (Account × Risk%) / (SL_pips × Pip_value_per_lot)
```

---

## MANIPULATION DETECTION

| Feature | Manipulation/Sweep | Genuine Breakout |
|---|---|---|
| After the break | Quick reversal + displacement opposite | Continuation + retest |
| Candle | Wick beyond, body closes inside | Body closes firmly beyond |
| Follow-through | Next candle reverses | Next candle continues |
| Structure | Break does NOT sustain | Creates new HH/LL |

**Rule:** When price breaks a level → WAIT. Watch what happens NEXT. Do not assume breakout OR manipulation immediately.

---

## MASTER REASONING SEQUENCE

```
RAW CHART
→ HTF: Determine trend/bias
→ HTF: Identify dealing range + premium/discount
→ HTF: Identify major liquidity (BSL/SSL/EQH/EQL)
→ HTF: Identify major OB/FVG/POI
→ MTF: Confirm structure, identify specific zone approach
→ OBSERVE: Did liquidity get swept?
→ OBSERVE: Is there displacement?
→ OBSERVE: Did structure shift (BOS/CHoCH/MSS)?
→ IDENTIFY: FVG/OB created by the move
→ CHECK: Confluence (OB+FVG+premium/discount+HTF alignment)
→ WAIT: For retracement to the zone
→ CONFIRM: Entry confirmation at the zone (candlestick, LTF shift)
→ CALCULATE: Entry, SL (beyond zone), TP (DOL), R:R, position size
→ EXECUTE: Only if R:R ≥ 1.5 and all conditions met
→ MANAGE: Move to BE after 1R; trail if strong trend
→ EXIT: At TP, SL, or trade invalidation
```
