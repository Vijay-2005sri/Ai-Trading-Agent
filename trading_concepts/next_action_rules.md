# NEXT ACTION RULES — Decision Trees for Every Detectable Concept
# ICT / Smart Money Concepts Framework

> For each concept the agent can detect on a chart, this file answers:
> **"If the agent detects this, what should it investigate next?"**

---

## 1. EQUAL HIGHS (EQH) DETECTED

```
EQH detected on chart
│
├── Mark as potential Buy-Side Liquidity (BSL)
├── Determine: Is the EQH above current price? How far?
├── Check HTF bias:
│   ├── HTF Bearish → EQH is a likely sweep target (price may take it before dropping)
│   └── HTF Bullish → EQH is a potential continuation target (genuine breakout possible)
│
├── OBSERVE: Does price approach the EQH?
│   ├── YES → Watch closely
│   │   ├── Does price sweep the EQH (wick above, close back below)?
│   │   │   ├── YES → Liquidity swept → Check for displacement DOWN
│   │   │   │   ├── Displacement present → Check for CHoCH/MSS below
│   │   │   │   │   ├── MSS confirmed → Identify FVG/OB → Wait for retracement → Entry (SHORT)
│   │   │   │   │   └── No structural shift → Wait, may be just a wick
│   │   │   │   └── No displacement → Not a valid sweep setup → WAIT
│   │   │   └── NO (price breaks and CLOSES above with body) → Genuine breakout
│   │   │       └── Look for continuation setup (pullback to retest the broken level)
│   │   └── Price stalls near EQH without reaching → Still building liquidity → WAIT
│   └── NO → EQH is not yet relevant → Monitor
│
└── Do NOT automatically short just because EQH exists
```

---

## 2. EQUAL LOWS (EQL) DETECTED

```
EQL detected on chart
│
├── Mark as potential Sell-Side Liquidity (SSL)
├── Check HTF bias:
│   ├── HTF Bullish → EQL is a likely sweep target (price may take it before rallying)
│   └── HTF Bearish → EQL is a potential continuation target (genuine breakdown possible)
│
├── OBSERVE: Does price approach the EQL?
│   ├── YES → Watch closely
│   │   ├── Does price sweep the EQL (wick below, close back above)?
│   │   │   ├── YES → Liquidity swept → Check for displacement UP
│   │   │   │   ├── Displacement present → Check for CHoCH/MSS above
│   │   │   │   │   ├── MSS confirmed → Identify FVG/OB → Wait for retracement → Entry (LONG)
│   │   │   │   │   └── No structural shift → Wait
│   │   │   │   └── No displacement → WAIT
│   │   │   └── NO (genuine breakdown with body close below) → Continuation setup
│   │   └── Price stalls → Still building → WAIT
│   └── NO → Monitor
│
└── Do NOT automatically buy just because EQL exists
```

---

## 3. BULLISH FVG DETECTED

```
Bullish FVG detected (Low[3] > High[1])
│
├── WHY did it form?
│   ├── Check: Was there displacement? (body > 2× avg)
│   │   ├── YES → Proceed
│   │   └── NO → Weak FVG → Deprioritize (may still be valid but lower probability)
│   │
│   ├── Check: Was liquidity (SSL) swept before the FVG formed?
│   │   ├── YES → Strong context → High-probability FVG
│   │   └── NO → Less institutional backing → Moderate probability
│   │
│   └── Check: Did the displacement cause a BOS or MSS?
│       ├── BOS → Continuation FVG → Trade with trend
│       ├── MSS → Reversal FVG → Highest priority (new trend direction)
│       └── Neither → Isolated FVG → Lower priority
│
├── WHERE is it?
│   ├── Premium or Discount?
│   │   ├── Discount → STRONG (buying in cheap zone)
│   │   └── Premium → WEAK (buying in expensive zone) → Extra confirmation needed
│   │
│   ├── Does it overlap with an Order Block?
│   │   ├── YES → High confluence → Priority zone
│   │   └── NO → Still valid but less confluence
│   │
│   └── Does it align with an HTF zone?
│       ├── YES → Very strong
│       └── NO → Standalone LTF FVG → Good but less reliable
│
├── Is it FRESH?
│   ├── Untested → Best probability
│   ├── Partially filled → Weaker
│   └── Fully filled → INVALIDATED → Consider as IFVG (opposite role)
│
├── WAIT for price to retrace to the FVG
│   ├── Price enters FVG zone → Look for confirmation:
│   │   ├── Bullish engulfing at FVG zone → ENTER LONG
│   │   ├── LTF bullish CHoCH/MSS within the FVG zone → ENTER LONG
│   │   ├── Bullish pin bar with wick into FVG → ENTER LONG (with next candle confirmation)
│   │   ├── No confirmation → DO NOT ENTER → Wait or skip
│   │   │
│   │   ├── Entry: At FVG zone (CE / midpoint is optimal)
│   │   ├── SL: Below the FVG lower boundary (below High[1])
│   │   │   └── Or below the OB if FVG overlaps with OB
│   │   ├── TP: Next BSL / swing high / DOL
│   │   └── R:R ≥ 1.5 required
│   │
│   └── Price CLOSES below FVG → FVG INVALIDATED → No trade
│
└── Do NOT enter just because an FVG exists
```

---

## 4. BEARISH FVG DETECTED

```
Bearish FVG detected (High[3] < Low[1])
│
├── Same logic as Bullish FVG but mirrored:
│   ├── Check displacement, liquidity sweep (BSL), structural break
│   ├── Check location: Premium = STRONG, Discount = WEAK
│   ├── Check freshness
│   ├── Wait for price to retrace UP into the FVG
│   ├── Confirmation: Bearish engulfing, LTF bearish CHoCH/MSS, bearish pin bar
│   ├── Entry: At FVG zone | SL: Above FVG upper boundary | TP: Next SSL / DOL
│   └── R:R ≥ 1.5
│
└── Do NOT enter just because a bearish FVG exists
```

---

## 5. BULLISH ORDER BLOCK DETECTED

```
Bullish OB detected (last bearish candle before bullish displacement)
│
├── VALIDATE the OB:
│   ├── Was the displacement strong? (body > 2× avg, small wicks)
│   │   ├── YES → Valid OB
│   │   └── NO → Questionable OB → Deprioritize
│   │
│   ├── Did the displacement create an FVG?
│   │   ├── YES → Strong OB (FVG validates it)
│   │   └── NO → Weaker OB
│   │
│   ├── Did the displacement break structure (BOS/MSS)?
│   │   ├── YES → Significant OB
│   │   └── NO → Minor OB
│   │
│   └── Was liquidity (SSL) swept before the OB?
│       ├── YES → Highest-quality OB
│       └── NO → Standard quality
│
├── CHECK LOCATION:
│   ├── In Discount → STRONG
│   ├── In Premium → WEAK → Require additional confluence
│   ├── Overlaps with HTF zone → Very strong
│   └── Overlaps with FVG → High confluence
│
├── CHECK FRESHNESS:
│   ├── Fresh (never tested) → Best
│   ├── Tested once → Moderate
│   ├── Tested 2+ times → Significantly weakened → Avoid
│   └── Price CLOSED through it → INVALIDATED → Consider as Breaker Block (bearish)
│
├── WAIT for price to retrace to the OB zone:
│   ├── Price reaches OB zone → Look for confirmation:
│   │   ├── Bullish engulfing → ENTER LONG
│   │   ├── LTF bullish MSS → ENTER LONG
│   │   ├── Bullish rejection (pin bar) → ENTER LONG (with next candle)
│   │   ├── No confirmation → DO NOT ENTER
│   │   │
│   │   ├── Entry: At OB zone (50% / midpoint is optimal)
│   │   ├── SL: Below OB low (or below sweep extreme if liquidity was swept)
│   │   ├── TP: Next BSL / DOL / opposing OB
│   │   └── R:R ≥ 1.5
│   │
│   └── Price closes through the OB → INVALIDATED
│       └── Zone becomes Breaker Block → Potential SHORT zone
│
└── Do NOT enter just because an OB exists
```

---

## 6. BEARISH ORDER BLOCK DETECTED

```
Same logic as Bullish OB, mirrored:
├── Validate: displacement + FVG + structural break + BSL sweep
├── Location: Premium = STRONG, Discount = WEAK
├── Wait for retracement UP to the OB
├── Confirmation at zone → ENTER SHORT
├── SL: Above OB high | TP: Next SSL / DOL
└── Invalidated if price closes through → becomes Bullish Breaker Block
```

---

## 7. BOS (Break of Structure) DETECTED

```
BOS detected (structural break WITH the existing trend)
│
├── Trend is CONFIRMED as continuing
├── Identify the displacement that caused the BOS
├── Identify the FVG created during the BOS move
├── Identify the OB at the origin of the move
│
├── WAIT for price to retrace:
│   ├── Price pulls back to FVG/OB → Entry in trend direction
│   ├── Confirmation at zone → ENTER (with trend)
│   ├── SL: Beyond the FVG/OB
│   ├── TP: Next liquidity in trend direction (DOL)
│   └── This is a CONTINUATION trade
│
└── Do NOT enter AT the BOS level — enter on the PULLBACK
```

---

## 8. CHoCH (Change of Character) DETECTED

```
CHoCH detected (first structural break AGAINST the trend)
│
├── ⚠️ WARNING: Trend may be shifting
├── DO NOT immediately change bias or enter
│
├── Check: Was the CHoCH accompanied by displacement?
│   ├── YES → This is becoming an MSS → High probability
│   │   ├── Check for FVG/OB created by the move
│   │   ├── Check if liquidity was swept before (at the trend extreme)
│   │   ├── If both → MSS CONFIRMED → Change directional bias
│   │   └── Enter on pullback to FVG/OB in new direction
│   │
│   └── NO → Weak CHoCH → May be false
│       ├── Wait for more evidence
│       ├── If price returns above the broken level → CHoCH failed → Original trend intact
│       └── If another break occurs with displacement → NOW it's an MSS
│
└── A single CHoCH without displacement is NOT enough to change bias
```

---

## 9. MSS (Market Structure Shift) DETECTED

```
MSS detected (CHoCH + displacement + liquidity sweep)
│
├── DIRECTIONAL BIAS HAS CHANGED
├── The previous trend is over (until proven otherwise)
│
├── Identify:
│   ├── The FVG created during the MSS displacement
│   ├── The OB at the origin of the MSS move
│   ├── The liquidity that was swept before the MSS
│
├── TRADE THE NEW DIRECTION:
│   ├── Wait for price to retrace to the FVG/OB
│   ├── Confirmation at zone → ENTER in new trend direction
│   ├── SL: Beyond the MSS extreme (the sweep point)
│   ├── TP: Next liquidity target in the new direction
│   └── R:R ≥ 1.5
│
└── This is the HIGHEST PRIORITY reversal setup
```

---

## 10. LIQUIDITY SWEEP DETECTED

```
Liquidity sweep detected (price broke beyond a known level and reversed)
│
├── Identify WHAT was swept:
│   ├── BSL (highs) → Bearish implication (fuel for selling)
│   ├── SSL (lows) → Bullish implication (fuel for buying)
│   ├── EQH → Heavy BSL taken → Strong bearish potential
│   ├── EQL → Heavy SSL taken → Strong bullish potential
│   ├── PDH/PDL → Session liquidity taken → Direction depends on context
│   └── Asian range high/low → Session sweep → Check Kill Zone timing
│
├── Check for DISPLACEMENT after the sweep:
│   ├── Strong displacement in opposite direction → PROCEED
│   └── No displacement → Not a valid sweep setup → WAIT
│
├── Check for STRUCTURAL CHANGE (CHoCH/MSS):
│   ├── MSS confirmed → Full reversal setup → Enter on pullback
│   ├── CHoCH only → Partial confirmation → Wait for more evidence
│   └── No structural change → The sweep may not lead to reversal → SKIP
│
├── Identify FVG/OB created by the post-sweep displacement
├── Wait for retracement
├── Confirm entry at zone
├── Execute with SL beyond sweep extreme, TP at DOL
│
└── REMINDER: Sweep alone ≠ reversal. All subsequent steps must be satisfied.
```

---

## 11. DISPLACEMENT CANDLE DETECTED

```
Displacement candle detected (body > 2× avg, small wicks)
│
├── Check: What CAUSED the displacement?
│   ├── Did it follow a liquidity sweep? → Strong institutional backing
│   ├── Did it follow a news event? → Fundamentally driven
│   └── No clear cause → Less reliable
│
├── Check: What did the displacement CREATE?
│   ├── FVG? → Mark it as an entry zone
│   ├── OB? → The candle before the displacement is the OB → Mark it
│   ├── Structural break (BOS/MSS)? → Defines trend continuation or reversal
│   └── None of the above → Isolated displacement → Less actionable
│
├── DETERMINE DIRECTION:
│   ├── Bullish displacement → Look for long entries on pullback
│   └── Bearish displacement → Look for short entries on pullback
│
├── WAIT for retracement to FVG/OB
├── Confirm and enter
│
└── Displacement without a pullback = MISSED entry → Do NOT chase
```

---

## 12. RANGE / CONSOLIDATION DETECTED

```
Range detected (price moving sideways between support and resistance)
│
├── Identify the range boundaries (high and low)
├── Mark BSL above range high and SSL below range low
│
├── Determine the TYPE of range:
│   ├── After a downtrend at support → Likely ACCUMULATION
│   │   └── Expect: SSL sweep (spring) → then bullish expansion
│   ├── After an uptrend at resistance → Likely DISTRIBUTION
│   │   └── Expect: BSL sweep (upthrust) → then bearish expansion
│   ├── Mid-uptrend → Likely RE-ACCUMULATION
│   │   └── Expect: minor sweep → then continued uptrend
│   └── Mid-downtrend → Likely RE-DISTRIBUTION
│       └── Expect: minor sweep → then continued downtrend
│
├── WAIT for manipulation (sweep of one extreme):
│   ├── Price sweeps the LOW of the range → Check for bullish displacement
│   │   ├── Bullish displacement + MSS → LONG setup
│   │   └── No displacement → May be genuine breakdown → WAIT
│   │
│   ├── Price sweeps the HIGH of the range → Check for bearish displacement
│   │   ├── Bearish displacement + MSS → SHORT setup
│   │   └── No displacement → May be genuine breakout → WAIT
│   │
│   └── No sweep yet → CONTINUE WAITING (do NOT trade inside the range chop)
│
└── Do NOT trade inside the range. Wait for the manipulation + expansion.
```

---

## 13. ASIAN RANGE IDENTIFIED (SESSION TIMING)

```
Asian session range identified [Asian High, Asian Low]
│
├── Mark Asian High → BSL above
├── Mark Asian Low → SSL below
│
├── At LONDON OPEN (Kill Zone 07:00-10:00 UTC):
│   ├── Watch for Judas Swing (fake move to one end)
│   ├── Price sweeps Asian Low?
│   │   ├── YES + bullish displacement → LONG setup
│   │   │   ├── Target: Asian High and beyond
│   │   │   ├── SL: Below the sweep extreme
│   │   │   └── Enter on pullback to FVG/OB
│   │   └── NO → Continue watching
│   │
│   ├── Price sweeps Asian High?
│   │   ├── YES + bearish displacement → SHORT setup
│   │   │   ├── Target: Asian Low and beyond
│   │   │   └── Enter on pullback to FVG/OB
│   │   └── NO → Continue watching
│   │
│   └── Neither swept → Range may extend → Wait for NY session
│
├── At NY OPEN (Kill Zone 13:30-16:00 UTC):
│   ├── Same logic — check if remaining liquidity is targeted
│   └── If London already established direction → NY may continue or reverse
│
└── Outside Kill Zones → Lower probability setups → Be more selective
```

---

## 14. PREMIUM/DISCOUNT DETERMINED

```
Current price position determined relative to dealing range
│
├── Price is in DISCOUNT (below 50% of dealing range):
│   ├── Look for LONG setups only
│   ├── Prioritize: Bullish OBs, Bullish FVGs, SSL sweeps
│   ├── Avoid: Short setups (selling in cheap territory = poor R:R)
│   └── If HTF is also bullish → IDEAL buying zone
│
├── Price is in PREMIUM (above 50% of dealing range):
│   ├── Look for SHORT setups only
│   ├── Prioritize: Bearish OBs, Bearish FVGs, BSL sweeps
│   ├── Avoid: Long setups (buying in expensive territory = poor R:R)
│   └── If HTF is also bearish → IDEAL selling zone
│
├── Price is at EQUILIBRIUM (near 50%):
│   ├── Neutral zone → direction depends on structure and liquidity
│   ├── Not ideal for entries → wait for price to move into premium or discount
│   └── Use structural signals (BOS/CHoCH) to determine direction
│
└── Always cross-reference with HTF bias before acting
```

---

## 15. INDUCEMENT DETECTED

```
Minor swing point detected within a larger pullback (potential inducement)
│
├── Mark the minor swing as inducement liquidity
├── Expect: Price will sweep this minor swing BEFORE reaching the actual OB/FVG
│
├── DO NOT place entry at the inducement level
│   └── It WILL be swept → your entry would be stopped out
│
├── Wait for:
│   1. Price to sweep the inducement (take minor liquidity)
│   2. Price to continue to the ACTUAL OB/FVG zone (deeper level)
│   3. Confirmation at the actual zone
│
├── ENTER at the actual OB/FVG (beyond the inducement)
│   ├── SL: Beyond the actual zone (not the inducement)
│   ├── TP: DOL
│   └── R:R ≥ 1.5
│
└── Inducement recognition prevents premature entries
```

---

## 16. CANDLESTICK PATTERN AT KEY LEVEL

```
Candlestick pattern detected (engulfing, pin bar, hammer, etc.)
│
├── WHERE is it?
│   ├── At an identified OB/FVG/POI → MEANINGFUL
│   ├── At a liquidity level (EQH/EQL/PDH/PDL) → MEANINGFUL
│   ├── In the middle of nowhere → NOT MEANINGFUL → IGNORE
│   └── At equilibrium with no other confluence → WEAK → Wait for more
│
├── Does it align with the setup sequence?
│   ├── Was liquidity swept before this pattern? → YES → Stronger
│   ├── Was there displacement before this pattern? → YES → Stronger
│   ├── Did structure shift (BOS/MSS)? → YES → Strongest
│   └── None of the above → The pattern is isolated → IGNORE
│
├── Does it align with HTF bias?
│   ├── YES → Proceed with entry
│   └── NO → Counter-trend pattern → Higher risk → Require extra confirmation
│
├── IF all conditions met:
│   ├── The candlestick pattern IS the entry confirmation
│   ├── Enter at the candle's close (or 50% of the pattern for tighter entry)
│   ├── SL: Beyond the pattern extreme + beyond the zone
│   ├── TP: DOL
│   └── R:R ≥ 1.5
│
└── A candlestick pattern WITHOUT context is NEVER a trade signal
```

---

## 17. BREAKER BLOCK DETECTED

```
Previously valid OB has been invalidated (price closed through it)
│
├── The zone is now a BREAKER BLOCK
├── It may act as a zone on the OPPOSITE side
│
├── Wait for price to return to the zone FROM the other direction
│   ├── Former Bullish OB → Now Bearish Breaker → Wait for price to rally back to it
│   │   ├── Bearish confirmation at the zone → SHORT entry
│   │   └── No confirmation → Skip
│   │
│   └── Former Bearish OB → Now Bullish Breaker → Wait for price to drop back to it
│       ├── Bullish confirmation at the zone → LONG entry
│       └── No confirmation → Skip
│
├── Breaker Blocks are SECONDARY zones → prioritize fresh OBs and FVGs
│
└── SL: Beyond the Breaker Block zone | TP: DOL
```

---

## 18. ASSET-SPECIFIC HOLD TIMES (SWING TRADING)

```
Trade entry conditions met
│
├── What is the Asset?
│   ├── Forex, Gold (XAUUSD), Silver (XAGUSD), Crypto:
│   │   └── Execute as standard Day Trade (Close within session/day)
│   │
│   └── Crude Oil (USOIL / WTI):
│       ├── Check Confidence Score:
│       │   ├── Confidence ≥ 90% → SWING TRADE AUTHORIZED
│       │   │   ├── You may set wider SL/TP targets.
│       │   │   ├── You are authorized to hold this trade for 24-48 hours.
│       │   │   └── Do not panic close on minor pullbacks.
│       │   │
│       │   └── Confidence < 90% → Standard Day Trade
│       │       └── Tighter SL/TP, close within the day.
│
└── Ensure Risk:Reward is still ≥ 1.5 regardless of holding time.
```

---

## SUMMARY: THE UNIVERSAL "WHAT NEXT?" FRAMEWORK

For ANY concept detected on the chart:

```
1. WHAT do I see?
   └── Identify the concept clearly

2. WHERE is it?
   └── Key level? Premium/Discount? HTF zone?

3. WHAT caused it?
   └── Liquidity sweep? Displacement? Structural break?

4. WHAT does it mean?
   └── Continuation? Potential reversal? Indecision?

5. WHAT should I check next?
   └── Follow the specific decision tree above

6. Is there CONFIRMATION?
   └── Displacement? Structural shift? Candlestick pattern at zone?

7. Is there INVALIDATION?
   └── Price closed through the zone? Setup conditions broken?

8. Is there a TRADE?
   └── Entry, SL, TP defined? R:R ≥ 1.5? Position size calculated?

9. If ALL conditions met → EXECUTE
   If ANY condition fails → NO TRADE → WAIT for next setup
```
