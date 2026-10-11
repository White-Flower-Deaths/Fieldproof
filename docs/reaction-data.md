# Reaction data - sources, likelihoods and coverage

This file is the human-readable companion to `backend/app/seed.py`. Every expected-reaction row the engine scores was researched against published forensic methods and carries the citation it derives from (enforced by `tests/test_auth.py::test_seed_rows_carry_source_citations`). Nothing here is a colour chart in itself - FieldProof is presumptive decision support only, and the full disclaimer applies to every result.

## Likelihood scheme

| Value | Meaning |
| --- | --- |
| 0.90 | 3 or more independent sources agree, no material conflict |
| 0.85 | 2 independent sources agree |
| 0.70 | one authoritative source (validation study / official method) |
| 0.60 | one source only (low-to-moderate evidence) |
| 0.55 / 0.30-0.35 | documented conflict: majority reading / documented dissent (both seeded, never averaged) |
| 0.15 | documented secondary reading (endpoint / variant nuance) |
| 0.02 (floor) | unlisted outcome for a pair that has rows - the engine's likelihood floor |
| *no rows* | pair with no published data found - readings stay non-discriminating |

## Policy

- **Citations**: kit, outcome and expected-reaction rows must be non-empty, not `DEMO_CITATION`, and contain a source-identity marker (BTNX, DanceSafe, Darsigny, District of Columbia, Halifax, JACS Au, Kosecki, Lockwood, NIJ, O'Neal, SIRCHIE, San Diego, UNODC, Wake County, e-PG Pathshala).
- **Substance metadata** (names, aliases, appearance notes) is generic field data, not reaction data, and still carries `DEMO_CITATION`.
- **Uniform readings**: if every candidate shares the same expected likelihood for an observation, the engine records it as non-discriminating - it can neither support nor contradict any candidate.
- **Coverage**: 33 sourced rows across 24 substance x kit pairs; 12 of the 36 possible pairs have no published data.

## Seeded rows

| Substance | Kit | Outcome | Likelihood | Source |
| --- | --- | --- | --- | --- |
| COCAINE | MARQUIS | NO_REACTION_ORANGE | 0.60 | Darsigny C, Couture ML, Desgagne-Penix I. Forensic Chemistry of Alkaloids: Presumptive ... |
| COCAINE | MARQUIS | ORANGE_RED | 0.35 | District of Columbia Dept. of Forensic Sciences, FCS10 Procedure for Chemical Spot Test... |
| HEROIN | MARQUIS | PURPLE_BLACK | 0.90 | O'Neal CL, Crouch DJ, Fatah AA. Validation of twelve chemical spot tests for the detect... |
| METHAMPHETAMINE | MARQUIS | ORANGE_RED | 0.80 | O'Neal CL, Crouch DJ, Fatah AA. Validation of twelve chemical spot tests for the detect... |
| METHAMPHETAMINE | MARQUIS | BROWN | 0.15 | SIRCHIE NARK Color Identification Chart, NARK20016_621ENG-REV12 (2020) (orange to brown... |
| MDMA | MARQUIS | PURPLE_BLACK | 0.90 | SIRCHIE NARK Color Identification Chart, NARK20016_621ENG-REV12 (2020); Wake County Bur... |
| FENTANYL | MARQUIS | ORANGE_RED | 0.60 | Wake County Bureau of Forensic Services, Drug Chemistry Unit Technical Procedures, Ch. ... |
| FENTANYL | MARQUIS | BROWN | 0.35 | Canoura J, Alkhamis O, Venzke M, Ly PT, Xiao Y. Developing Aptamer-Based Colorimetric O... |
| COCAINE | MECKE | NO_REACTION_ORANGE | 0.60 | Darsigny C, Couture ML, Desgagne-Penix I. Forensic Chemistry of Alkaloids: Presumptive ... |
| HEROIN | MECKE | GREEN | 0.85 | Darsigny C, Couture ML, Desgagne-Penix I. Forensic Chemistry of Alkaloids: Presumptive ... |
| METHAMPHETAMINE | MECKE | NO_REACTION_ORANGE | 0.60 | Darsigny C, Couture ML, Desgagne-Penix I. Forensic Chemistry of Alkaloids: Presumptive ... |
| MDMA | MECKE | PURPLE | 0.60 | Darsigny C, Couture ML, Desgagne-Penix I. Forensic Chemistry of Alkaloids: Presumptive ... |
| MDMA | MECKE | GREEN | 0.35 | City of San Diego Police Dept., Narcotics Method Manual, July 2017 Sec. 2.2.1 (green/bl... |
| COCAINE | MANDELIN | ORANGE_BROWN | 0.85 | O'Neal CL, Crouch DJ, Fatah AA. Validation of twelve chemical spot tests for the detect... |
| HEROIN | MANDELIN | ORANGE_BROWN | 0.70 | O'Neal CL, Crouch DJ, Fatah AA. Validation of twelve chemical spot tests for the detect... |
| METHAMPHETAMINE | MANDELIN | GREEN | 0.65 | O'Neal CL, Crouch DJ, Fatah AA. Validation of twelve chemical spot tests for the detect... |
| METHAMPHETAMINE | MANDELIN | NO_REACTION_YELLOW | 0.30 | Darsigny C, Couture ML, Desgagne-Penix I. Forensic Chemistry of Alkaloids: Presumptive ... |
| MDMA | MANDELIN | BLUE | 0.70 | Darsigny C, Couture ML, Desgagne-Penix I. Forensic Chemistry of Alkaloids: Presumptive ... |
| COCAINE | SCOTT | BLUE | 0.90 | UNODC, Recommended Methods for the Identification and Analysis of Cocaine in Seized Mat... |
| HEROIN | SCOTT | PALE_NO_REACTION | 0.55 | Darsigny C, Couture ML, Desgagne-Penix I. Forensic Chemistry of Alkaloids: Presumptive ... |
| HEROIN | SCOTT | BLUE | 0.30 | UGC e-PG Pathshala, Forensic Science Paper 9 Module 25, Colour Tests for Drug Identific... |
| METHAMPHETAMINE | SCOTT | PALE_NO_REACTION | 0.60 | Darsigny C, Couture ML, Desgagne-Penix I. Forensic Chemistry of Alkaloids: Presumptive ... |
| MDMA | SCOTT | PALE_NO_REACTION | 0.65 | Darsigny C, Couture ML, Desgagne-Penix I. Forensic Chemistry of Alkaloids: Presumptive ... |
| FENTANYL | SCOTT | BLUE | 0.60 | Kosecki TL, Brooke C, Canonico DL. Fentanyl as a potential false positive with color te... |
| CANNABIS | DUQUENOIS_LEVINE | PURPLE | 0.90 | UNODC, Recommended Methods for the Identification and Analysis of Cannabis in Seized Ma... |
| FENTANYL | FENT_STRIP | POSITIVE | 0.90 | BTNX Inc., Rapid Response Fentanyl Test Strip product insert 1110027361 REV 2.0 (effect... |
| FENTANYL | FENT_STRIP | NEGATIVE | 0.08 | BTNX Inc., Rapid Response Fentanyl Test Strip product insert 1110027361 REV 2.0 (effect... |
| COCAINE | FENT_STRIP | NEGATIVE | 0.90 | Lockwood TL, Vervoordt A, Lieberman M. High concentrations of illicit stimulants and cu... |
| HEROIN | FENT_STRIP | NEGATIVE | 0.90 | Halifax JC, Lim L, Ciccarone D, Lynch KL. Testing the test strips: laboratory performan... |
| METHAMPHETAMINE | FENT_STRIP | NEGATIVE | 0.70 | Lockwood TL, Vervoordt A, Lieberman M. High concentrations of illicit stimulants and cu... |
| METHAMPHETAMINE | FENT_STRIP | POSITIVE | 0.25 | Lockwood TL, Vervoordt A, Lieberman M. High concentrations of illicit stimulants and cu... |
| MDMA | FENT_STRIP | NEGATIVE | 0.70 | Lockwood TL, Vervoordt A, Lieberman M. High concentrations of illicit stimulants and cu... |
| MDMA | FENT_STRIP | POSITIVE | 0.25 | Lockwood TL, Vervoordt A, Lieberman M. High concentrations of illicit stimulants and cu... |

### Pairs with no published data (no rows seeded)

- COCAINE x DUQUENOIS_LEVINE
- HEROIN x DUQUENOIS_LEVINE
- METHAMPHETAMINE x DUQUENOIS_LEVINE
- MDMA x DUQUENOIS_LEVINE
- CANNABIS x MARQUIS
- CANNABIS x MECKE
- CANNABIS x MANDELIN
- CANNABIS x SCOTT
- CANNABIS x FENT_STRIP
- FENTANYL x MECKE
- FENTANYL x MANDELIN
- FENTANYL x DUQUENOIS_LEVINE

## Sources (full strings as seeded)

- Darsigny C, Couture ML, Desgagne-Penix I. Forensic Chemistry of Alkaloids: Presumptive Color Test. Austin J Forensic Sci Criminol 2018;5(1):1074, Tables 2-3; City of San Diego Police Dept., Narcotics Method Manual, July 2017; DanceSafe, Drug Checking Kits / Testing Instructions, V16 (Fall 2022); conflict: District of Columbia Dept. of Forensic Sciences, FCS10 Procedure for Chemical Spot Tests, Rev. 5 (2018-10-31) Sec. 7.1.4
- District of Columbia Dept. of Forensic Sciences, FCS10 Procedure for Chemical Spot Tests, Rev. 5 (2018-10-31) Sec. 7.1.4 (salmon); DanceSafe, Drug Checking Kits / Testing Instructions, V16 (Fall 2022) (light pink or no change)
- O'Neal CL, Crouch DJ, Fatah AA. Validation of twelve chemical spot tests for the detection of drugs of abuse. Forensic Science International 109 (2000) 189-201, Table 2; reproduced in NIJ Standard-0604.01 (July 2000, NCJ 183258), App. A Table 1; SIRCHIE NARK Color Identification Chart, NARK20016_621ENG-REV12 (2020); Wake County Bureau of Forensic Services, Drug Chemistry Unit Technical Procedures, Ch. 7 Color Tests, effective 2021-08-25; City of San Diego Police Dept., Narcotics Method Manual, July 2017
- SIRCHIE NARK Color Identification Chart, NARK20016_621ENG-REV12 (2020) (orange to brown); O'Neal CL, Crouch DJ, Fatah AA. Validation of twelve chemical spot tests for the detection of drugs of abuse. Forensic Science International 109 (2000) 189-201, Table 2; reproduced in NIJ Standard-0604.01 (July 2000, NCJ 183258), App. A Table 1 (final dark reddish brown)
- SIRCHIE NARK Color Identification Chart, NARK20016_621ENG-REV12 (2020); Wake County Bureau of Forensic Services, Drug Chemistry Unit Technical Procedures, Ch. 7 Color Tests, effective 2021-08-25; Darsigny C, Couture ML, Desgagne-Penix I. Forensic Chemistry of Alkaloids: Presumptive Color Test. Austin J Forensic Sci Criminol 2018;5(1):1074, Tables 2-3; UGC e-PG Pathshala, Forensic Science Paper 9 Module 25, Colour Tests for Drug Identification; outlier: City of San Diego Police Dept., Narcotics Method Manual, July 2017 Sec. 2.2.1 lists green and/or purple-black
- Wake County Bureau of Forensic Services, Drug Chemistry Unit Technical Procedures, Ch. 7 Color Tests, effective 2021-08-25; City of San Diego Police Dept., Narcotics Method Manual, July 2017
- Canoura J, Alkhamis O, Venzke M, Ly PT, Xiao Y. Developing Aptamer-Based Colorimetric Opioid Tests. JACS Au 2024;4(3):1059-1072, doi:10.1021/jacsau.3c00801
- Darsigny C, Couture ML, Desgagne-Penix I. Forensic Chemistry of Alkaloids: Presumptive Color Test. Austin J Forensic Sci Criminol 2018;5(1):1074, Tables 2-3
- Darsigny C, Couture ML, Desgagne-Penix I. Forensic Chemistry of Alkaloids: Presumptive Color Test. Austin J Forensic Sci Criminol 2018;5(1):1074, Tables 2-3 (deep bluish green); SIRCHIE NARK Color Identification Chart, NARK20016_621ENG-REV12 (2020); City of San Diego Police Dept., Narcotics Method Manual, July 2017
- Darsigny C, Couture ML, Desgagne-Penix I. Forensic Chemistry of Alkaloids: Presumptive Color Test. Austin J Forensic Sci Criminol 2018;5(1):1074, Tables 2-3; UGC e-PG Pathshala, Forensic Science Paper 9 Module 25, Colour Tests for Drug Identification
- City of San Diego Police Dept., Narcotics Method Manual, July 2017 Sec. 2.2.1 (green/blue - dissent)
- O'Neal CL, Crouch DJ, Fatah AA. Validation of twelve chemical spot tests for the detection of drugs of abuse. Forensic Science International 109 (2000) 189-201, Table 2; reproduced in NIJ Standard-0604.01 (July 2000, NCJ 183258), App. A Table 1 (deep orange yellow); Darsigny C, Couture ML, Desgagne-Penix I. Forensic Chemistry of Alkaloids: Presumptive Color Test. Austin J Forensic Sci Criminol 2018;5(1):1074, Tables 2-3 (+)
- O'Neal CL, Crouch DJ, Fatah AA. Validation of twelve chemical spot tests for the detection of drugs of abuse. Forensic Science International 109 (2000) 189-201, Table 2; reproduced in NIJ Standard-0604.01 (July 2000, NCJ 183258), App. A Table 1
- O'Neal CL, Crouch DJ, Fatah AA. Validation of twelve chemical spot tests for the detection of drugs of abuse. Forensic Science International 109 (2000) 189-201, Table 2; reproduced in NIJ Standard-0604.01 (July 2000, NCJ 183258), App. A Table 1 (dark yellowish green); SIRCHIE NARK Color Identification Chart, NARK20016_621ENG-REV12 (2020) (yellow-green); UNODC SCITEC, Screening Colour Test and Specific Colour Tests for MDA and Amphetamine-Type Stimulants, SCITEC/16
- Darsigny C, Couture ML, Desgagne-Penix I. Forensic Chemistry of Alkaloids: Presumptive Color Test. Austin J Forensic Sci Criminol 2018;5(1):1074, Tables 2-3 (no change - dissent)
- Darsigny C, Couture ML, Desgagne-Penix I. Forensic Chemistry of Alkaloids: Presumptive Color Test. Austin J Forensic Sci Criminol 2018;5(1):1074, Tables 2-3 (dark blue); UGC e-PG Pathshala, Forensic Science Paper 9 Module 25, Colour Tests for Drug Identification (blue/black)
- UNODC, Recommended Methods for the Identification and Analysis of Cocaine in Seized Materials, ST/NAR/7/Rev.1 (2012) Sec. 5.3.1.1; O'Neal CL, Crouch DJ, Fatah AA. Validation of twelve chemical spot tests for the detection of drugs of abuse. Forensic Science International 109 (2000) 189-201, Table 2; reproduced in NIJ Standard-0604.01 (July 2000, NCJ 183258), App. A Table 1; SIRCHIE NARK Color Identification Chart, NARK20016_621ENG-REV12 (2020); Wake County Bureau of Forensic Services, Drug Chemistry Unit Technical Procedures, Ch. 7 Color Tests, effective 2021-08-25
- Darsigny C, Couture ML, Desgagne-Penix I. Forensic Chemistry of Alkaloids: Presumptive Color Test. Austin J Forensic Sci Criminol 2018;5(1):1074, Tables 2-3 (Cobalt '-' for codeine and morphine; no heroin row in UNODC, Recommended Methods for the Identification and Analysis of Cocaine in Seized Materials, ST/NAR/7/Rev.1 (2012) or SIRCHIE NARK Color Identification Chart, NARK20016_621ENG-REV12 (2020) - unresolved, see docs/reaction-data.md)
- UGC e-PG Pathshala, Forensic Science Paper 9 Module 25, Colour Tests for Drug Identification Sec. 4.2 (single affirmative source - unresolved)
- Darsigny C, Couture ML, Desgagne-Penix I. Forensic Chemistry of Alkaloids: Presumptive Color Test. Austin J Forensic Sci Criminol 2018;5(1):1074, Tables 2-3 (Cobalt '-'; mechanistic rationale)
- Kosecki TL, Brooke C, Canonico DL. Fentanyl as a potential false positive with color tests commonly used for presumptive cocaine identification. J Forensic Sci 2022;67(5):2082-2088 (abstract), doi:10.1111/1556-4029.15090; City of San Diego Police Dept., Narcotics Method Manual, July 2017 (CoSCN blue on particles)
- UNODC, Recommended Methods for the Identification and Analysis of Cannabis in Seized Materials, ST/NAR/40 (2009) Sec. 5.4.3.1; District of Columbia Dept. of Forensic Sciences, FCS10 Procedure for Chemical Spot Tests, Rev. 5 (2018-10-31) Sec. 7.8.4; City of San Diego Police Dept., Narcotics Method Manual, July 2017 Sec. 8.1.3
- BTNX Inc., Rapid Response Fentanyl Test Strip product insert 1110027361 REV 2.0 (effective 2021-01-20); Halifax JC, Lim L, Ciccarone D, Lynch KL. Testing the test strips: laboratory performance of fentanyl test strips. Harm Reduct J 2024;21:14, doi:10.1186/s12954-023-00921-8
- BTNX Inc., Rapid Response Fentanyl Test Strip product insert 1110027361 REV 2.0 (effective 2021-01-20) (negative possible below the cut-off)
- Lockwood TL, Vervoordt A, Lieberman M. High concentrations of illicit stimulants and cutting agents cause false positives on fentanyl test strips. Harm Reduct J 2021;18:30, doi:10.1186/s12954-021-00478-4; Halifax JC, Lim L, Ciccarone D, Lynch KL. Testing the test strips: laboratory performance of fentanyl test strips. Harm Reduct J 2024;21:14, doi:10.1186/s12954-023-00921-8
- Halifax JC, Lim L, Ciccarone D, Lynch KL. Testing the test strips: laboratory performance of fentanyl test strips. Harm Reduct J 2024;21:14, doi:10.1186/s12954-023-00921-8
- Lockwood TL, Vervoordt A, Lieberman M. High concentrations of illicit stimulants and cutting agents cause false positives on fentanyl test strips. Harm Reduct J 2021;18:30, doi:10.1186/s12954-021-00478-4 (false positive at >= 1.5 mg/mL); Halifax JC, Lim L, Ciccarone D, Lynch KL. Testing the test strips: laboratory performance of fentanyl test strips. Harm Reduct J 2024;21:14, doi:10.1186/s12954-023-00921-8
- Lockwood TL, Vervoordt A, Lieberman M. High concentrations of illicit stimulants and cutting agents cause false positives on fentanyl test strips. Harm Reduct J 2021;18:30, doi:10.1186/s12954-021-00478-4 (false positive at >= 2 mg/mL); Halifax JC, Lim L, Ciccarone D, Lynch KL. Testing the test strips: laboratory performance of fentanyl test strips. Harm Reduct J 2024;21:14, doi:10.1186/s12954-023-00921-8

## Verbatim research report

<!-- Copied verbatim from the field research pass that produced this data set; keep in sync with backend/app/seed.py when reseeding. -->

# Presumptive Colour-Test Result Map
## 6 substances × 6 test systems — verbatim colour results, citation-intact

**Substances:** cocaine hydrochloride · heroin (diacetylmorphine HCl) · methamphetamine · MDMA · cannabis/THC · fentanyl
**Test systems:** MARQUIS · MECKE · MANDELIN · SCOTT (cobalt thiocyanate / modified Scott) · DUQUENOIS–LEVINE · fentanyl immunochromatographic test strip (FTS)

**Method.** Only sources actually downloaded and text-extracted locally are quoted. Scanned PDFs with no text layer are declared as such and not quoted (no OCR used). Absent = `NOT FOUND`. Non-trivial results were cross-checked against ≥2 independent sources where such sources exist; disagreements are shown, not reconciled.

**Convention.** Text extracts of PDFs preserve the source's own hyphenation/wording; `[sic]` is not used for obvious extraction artefacts (e.g. `–` rendered as `?`). ISCC-NBS colour names and Munsell notations come from the source's own table columns.

---

## 0. Master coverage grid

| | MARQUIS | MECKE | MANDELIN | SCOTT | DUQUENOIS–LEVINE | FENTANYL STRIP |
|---|---|---|---|---|---|---|
| **Cocaine HCl** | ⚠ conflict | 1 src | ✓ | ✓ | `NOT FOUND` | ✓ negative |
| **Heroin** | ✓ | ✓ | ✓ | 1 src ⚠ | `NOT FOUND` | ✓ negative |
| **Methamphetamine** | ✓ | 1 src | ⚠ conflict | 1 src | `NOT FOUND` | ✓ false-pos |
| **MDMA** | ✓ | ⚠ variance | 1 src ⚠ | 1 src | `NOT FOUND` | ✓ false-pos |
| **Cannabis/THC** | `NOT FOUND` | `NOT FOUND` | `NOT FOUND` | `NOT FOUND` | ✓ | `NOT FOUND` |
| **Fentanyl** | ⚠ conflict | `NOT FOUND` | `NOT FOUND` | ✓ ⚠ | `NOT FOUND` | ✓ positive |

Legend: ✓ = ≥2 independent sources agree or 1 authoritative SOP with no contradiction · 1 src = single source only · ⚠ = documented source disagreement · `NOT FOUND` = no source located.

---

## 1. MARQUIS REAGENT
*Reagent (NIJ/NIJ std): "Carefully add 100 mL of concentrated sulfuric acid to 5 mL of 40 percent formaldehyde (v:v, formaldehyde:water)."*

| Substance | Verbatim colour result | Exact citation | Confidence note |
|---|---|---|---|
| **Cocaine HCl** | **CONFLICT — two incompatible readings.**<br>(a) "Salmon may indicate presence of Cocaine"<br>(b) "Colorless" / "Marquis- No Reaction"<br>(c) "In the presence of cocaine, Marquis will either produce a light pink color or not change color at all." | (a) District of Columbia, Dept. of Forensic Sciences, *FCS10 Procedure for Chemical Spot Tests*, Rev. 5, issue date 10/31/2018, §7.1.4 "Interpretation (color test acceptance criteria)", p. 5. https://dfs.dc.gov/sites/default/files/dc/sites/dfs/publication/attachments/FCS10%20-%20Procedure%20for%20Chemical%20Spot%20Tests.pdf<br>(b) Darsigny C, Couture ML, Desgagné-Penix I. "Forensic Chemistry of Alkaloids: Presumptive Color Test." *Austin J Forensic Sci Criminol.* 2018;5(1):1074, Table 3 row "a. Cocaine / Marquis / Colorless" (p. 6); and p. 8: "with Marquis' test, cocaine is colorless". — *and* City of San Diego, *Narcotics Method Manual*, July 2017, §2.2.2 (p. 7): "Marquis- No Reaction".<br>(c) DanceSafe, *Drug Checking Kits / Testing Instructions*, V16 (Fall 2022), "HOW TO TEST COCAINE", step 2. https://dancesafe.org/wp-content/uploads/2023/01/DS_Testing-Instructions_V16_Fall22-1.pdf | **Moderate, genuinely conflicting.** Three independent sources say no/colourless; DC DFS says "salmon". Note also that neither O'Neal 2000 nor NIJ Standard-0604.01 Table 1 contains a cocaine row under A.5 Marquis — the standard simply does not list cocaine. |
| **Heroin (diacetylmorphine HCl)** | "Deep purplish red" (ISCC-NBS colour name **256**, Munsell **7.5RP 3/10**)<br>Orange → **Purple**<br>"Opiates, some opioids (morphine, codeine, heroin, buprenorphine) - purple"<br>"Marquis- Purple"<br>"dark purple color … matches the characteristic color heroin produces in the Marquis test"<br>QC reference: "Reference material: Heroin … Acceptable result: Purple color observed" | O'Neal CL, Crouch DJ, Fatah AA. "Validation of twelve chemical spot tests for the detection of drugs of abuse." *Forensic Science International* 109 (2000) 189–201, Table 2, row "A.5 Diacetylmorphine HCl". — same data reproduced in NIJ, *Color Test Reagents/Kits for Preliminary Identification of Drugs of Abuse*, NIJ Standard–0604.01, July 2000 (NCJ 183258), Appendix A Table 1, row "A.5 Diacetylmorphine HCl*". https://www.ojp.gov/pdffiles1/nij/183258.pdf<br>— SIRCHIE, *NARK® Color Identification Chart*, doc. NARK20016_621ENG-REV12 (© 2020), Test No. 1 "Marquis Reagent", row "Heroin/Morphine". https://www.sirchie.com/media/resourcecenter/item/n/a/nark20016_621eng-rev12.pdf<br>— Wake County Bureau of Forensic Services, *Drug Chemistry Unit Technical Procedures*, Ch. 7 "Color Tests", effective 8/25/2021, §5.1.2. https://public.powerdms.com/WakeBI/documents/1745769<br>— City of San Diego, *Narcotics Method Manual*, July 2017, §2.2.5 (p. 8): "Heroin … Marquis- Purple".<br>— Canoura J, Alkhamis O, Venzke M, Ly PT, Xiao Y. "Developing Aptamer-Based Colorimetric Opioid Tests." *JACS Au* 2024;4(3):1059–1072. doi:10.1021/jacsau.3c00801, Results text (PMC10976566).<br>— Wake County, Ch. 7, §5.1.3.4.1–.2 (quality-control paragraph). | **High.** Five independent sources, all "purple"; ISCC-NBS/Munsell values anchored to the peer-reviewed validation study and its NIJ restatement. |
| **Methamphetamine** | "Deep reddish orange" → "Dark reddish brown" (ISCC-NBS **36** "Deep reddish orange" 10R 4/12 → **44** "Dark reddish brown" 7.5R 2/4)<br>"Orange Brown (within 12 seconds)"<br>"(Meth)amphetamine - orange"<br>"Marquis- Orange or Orange Brown"<br>"methamphetamine yielded an orange color" | O'Neal 2000, Table 2, row "A.5 D-Methamphetamine HCl"; NIJ Std–0604.01, App. A Table 1, row "A.5 d-Methamphetamine HCl*".<br>SIRCHIE NARK20016_621ENG-REV12, Test No. 1, row "Amphetamines/Methamphetamine", columns "TEST → FINAL COLOR" = Orange → Brown (within 12 seconds).<br>Wake County Ch. 7, §5.1.2.<br>City of San Diego *Narcotics Method Manual*, July 2017, §2.2.1 (p. 7).<br>Darsigny 2018, p. 8: "MDA and MDMA produced a black-violet color while piperine and methamphetamine yielded an orange color." | **High.** Five sources; all agree on the orange/brown family. Only the *rate/endpoint* wording differs (12 s, "orange" vs "orange-brown"). |
| **MDMA** | "Orange" → **Black**<br>"MDA/MDMA - purple/black"<br>"Marquis- Green and/or Purple Black"<br>"MDA and MDMA produced a black-violet color"<br>"If a substance tests positive for an ecstasy-like substance by turning to purple/black with Marquis or Mecke …" | SIRCHIE NARK20016_621ENG-REV12, Test No. 1, row "MDMA (Ecstasy)".<br>Wake County Ch. 7, §5.1.2.<br>City of San Diego *Narcotics Method Manual*, §2.2.1 (p. 7).<br>Darsigny 2018, p. 8 (Marquis paragraph, quoted above).<br>University Grants Commission / e-PG Pathshala, *Forensic Science, Paper 9: Drugs of Abuse*, Module 25 "Colour Tests for Drug Identification", §4.14. https://epgp.inflibnet.ac.in/epgpdata/uploads/epgp_content/S000016FS/P000696/M011517/ET/1516251256FSC_P9_M25_e-text.pdf | **High** for "purple/black or black". Note: **San Diego's "Green and/or Purple Black" is an outlier** — reported, not smoothed over. Also note NIJ/O'Neal A.5 contains a row for **MDA** ("Black Black", ISCC 267) but **no MDMA row**; do not substitute MDA data for MDMA. |
| **Fentanyl** | **CONFLICT.**<br>(a) "Fentanyl - orange"<br>(b) "Marquis- Weak Orange (sometimes)"<br>(c) "Binary mixtures containing 8% fentanyl and 92% interferent turned dark brown (H), which is the signature color of fentanyl for this test" | (a) Wake County Ch. 7, §5.1.2 (p. 4).<br>(b) City of San Diego *Narcotics Method Manual*, §2.2.3 (p. 7).<br>(c) Canoura, Alkhamis, Venzke, Ly & Xiao, *JACS Au* 2024;4(3):1059–1072, Results, "…fentanyl and lidocaine yield similar colors, it is not possible…". | **Moderate, conflicting.** Two laboratory SOPs say orange/weak orange; the peer-reviewed paper says dark brown (which the same paper notes is confusable with lidocaine and with ibuprofen/diphenhydramine "orange-brown colors"). Neither O'Neal 2000 nor NIJ Std–0604.01 contains any fentanyl row — the 2000 NIJ data set predates illicit fentanyl prevalence. |
| **Cannabis / THC** | **NOT FOUND** | — | No source located giving a Marquis colour for cannabis or THC. O'Neal 2000 Table 2 and NIJ Std–0604.01 App. A Table 1 contain **no THC row under A.5**; DC FCS10 §7.1.4 lists no cannabis; Wake County §5.1.2 lists no cannabis; SIRCHIE Test No. 1 has no cannabis row; San Diego §2.2 has no cannabis entry under Amines/Opiates/Cocaine/Fentanyl. Explicitly searched (multiple queries) — none found. |

---

## 2. MECKE REAGENT
*Reagent (City of San Diego, §15): "Dissolve 0.25 grams of selenious acid in 25ml of concentrated sulfuric acid."*

| Substance | Verbatim colour result | Exact citation | Confidence note |
|---|---|---|---|
| **Cocaine HCl** | "Colorless" (Table 3, single-alkaloid column); Table 2 grid cell = "-" | Darsigny, Couture & Desgagné-Penix 2018, *Austin J Forensic Sci Criminol* 5(1):1074, Table 2 ("Cocaine … Mecke -") and Table 3 row "6) a. Cocaine / Mecke / Colorless". | **Low–moderate: single source.** No second independent source found. O'Neal 2000 / NIJ Std–0604.01 App. A Table 1 contain **no cocaine row under A.10**. |
| **Heroin (diacetylmorphine HCl)** | "Clear" → **Green**<br>"Mecke- Green"<br>"Deep bluish green" (ISCC-NBS **161**, Munsell **2.5BG 3/8**)<br>"…the opiates codeine and morphine gave a blue color" (structural context) | SIRCHIE NARK20016_621ENG-REV12, Test No. 11 "Mecke's Modified Reagent", row "Heroin (white, brown, black tar)", columns Clear → Green.<br>City of San Diego *Narcotics Method Manual*, §2.2.5 (p. 8).<br>O'Neal 2000, Table 2, row "A.10 Diacetylmorphine HCl"; NIJ Std–0604.01 App. A Table 1, row "A.10 Diacetylmorphine HCl*". | **High.** Three sources, all in the blue-green family; two give literally "Green". |
| **Methamphetamine** | "Colorless" (Table 3); Table 2 grid cell = "-" | Darsigny 2018, Table 2 ("Methamphetamine … Mecke -") and Table 3 row "4) a. Methamphetamine / Mecke / Colorless". | **Low: single source.** UGC e-PG Pathshala Module 25 §5 lists "Mecke test" as a useful test for amphetamines but gives **no colour**; San Diego §2.2.1 gives no Mecke entry for methamphetamine; O'Neal/NIJ A.10 has **no methamphetamine row**. |
| **MDMA** | **Variance.**<br>(a) "MDMA yielded purple-black" (Mecke)<br>(b) "Mecke- Green/Blue"<br>(c) "turning to purple/black with Marquis or Mecke" | (a) Darsigny 2018, p. 7: "In Mecke's test, berberine and piperine both produced a brown color, whereas MDA and MDMA yielded purple-black…".<br>(b) City of San Diego *Narcotics Method Manual*, §2.2.1 (p. 7).<br>(c) UGC e-PG Pathshala, Forensic Science Paper 9, Module 25, §4.14. | **Moderate, sources disagree on hue** (purple-black vs green/blue). All three agree Mecke **is** positive for MDMA. Note O'Neal/NIJ A.10 has **no MDMA row** (it does have MDA: "Very dark bluish green", ISCC 166). |
| **Fentanyl** | **NOT FOUND** | — | Searched repeatedly; no source located. |
| **Cannabis / THC** | **NOT FOUND** | — | O'Neal 2000 Table 2 / NIJ App. A Table 1 under A.10 contain only "Mace Crystals / Nutmeg … / Sugar Crystals" type interferences — **no THC row**. SIRCHIE Test No. 11 has no cannabis row. Searched — none found. |

---

## 3. MANDELIN REAGENT
*Reagent (NIJ Std–0604.01, App. A, A.4): ammonium vanadate in concentrated sulfuric acid.*

| Substance | Verbatim colour result | Exact citation | Confidence note |
|---|---|---|---|
| **Cocaine HCl** | "Deep orange yellow" (ISCC-NBS colour name **69**, Munsell **10YR 7/14**); Table 2 grid cell = "+" | O'Neal CL, Crouch DJ, Fatah AA, *Forensic Sci Int* 109 (2000) 189–201, Table 2, row "A.4 Cocaine HCl"; identical row in NIJ, *Color Test Reagents/Kits…*, NIJ Standard–0604.01 (July 2000, NCJ 183258), App. A Table 1, row "A.4 Cocaine HCl*". — Darsigny 2018, Table 2 ("Cocaine … Mandelin +"). | **High.** Two independent sources agree on positivity; the peer-reviewed validation study supplies the exact colour name. |
| **Heroin (diacetylmorphine HCl)** | "Moderate reddish brown" (ISCC-NBS **43**, Munsell **10R 3/6**) | O'Neal 2000, Table 2, row "A.4 Diacetylmorphine HCl"; NIJ Std–0604.01 App. A Table 1, same row. LOD from O'Neal Table 4: "A.4 Diacetylmorphine HCl 20" (µg). | **Moderate–high for the colour name** (peer-reviewed primary + NIJ restatement, identical wording). No *second independent* laboratory SOP with a Mandelin×heroin colour was found (San Diego, Wake County and FCS10 contain no Mandelin section). |
| **Methamphetamine** | **CONFLICT.**<br>(a) "Dark yellowish green" (ISCC-NBS **137**, Munsell **10GY 4/6**)<br>(b) "Methamphetamine … Yellow-Green"<br>(c) "3 Mandeline-reagent … yellow green"<br>(d) "No change" / Table 2 grid "-" | (a) O'Neal 2000, Table 2, row "A.4 D-Methamphetamine HCl"; NIJ Std–0604.01 App. A Table 1, same row. LOD (O'Neal Table 4): "A.4 D-Methamphetamine HCl 100" (µg).<br>(b) SIRCHIE NARK20016_621ENG-REV12, Test No. 22 "Mandelin Reagent", row "Methamphetamine".<br>(c) UNODC, *Screening Colour Test and Specific Colour Tests for the Detection of Methylendioxyamphetamine and Amphetamine Type Stimulants*, SCITEC/16, Table LIII "Cross-reactivity results (Amphetamine and Methamphetamine)", row 3. https://www.unodc.org/documents/scientific/Screening_Colour_Test_ATS.pdf<br>(d) Darsigny 2018, Table 2 ("Methamphetamine … Mandelin -") and Table 3 rows "7) a. Methamphetamine / Mandelin / No change" and "9) a. Methamphetamine / Mandelin / No change"; text p. 7: "methamphetamine did not react". | **Moderate — hard conflict, reported as found.** Three sources say yellow/green; one peer-reviewed paper says no reaction and offers a mechanism ("lack of the Methylenedioxy bridge in methamphetamine may have caused the lack of reaction with Mandelin's reagent"). |
| **MDMA** | "Dark blue"; grid cell "+"<br>"If a substance tests positive for an ecstasy-like substance by turning to … blue/black with Mandelin, then a color-change reaction with Simon's indicates the presence of MDMA or MDE." | Darsigny 2018, Table 2 ("MDMA … Mandelin +"), Table 3 row "8) a. MDMA / Mandelin / Dark blue", and p. 7: "Mandelin's reagent reacted with MDMA and yielded a dark blue color". — UGC e-PG Pathshala, Paper 9, Module 25, §4.14. | **Moderate: two sources, agree MDMA is positive.** ⚠ **Do not cite NIJ for this cell:** NIJ/O'Neal A.4 has a row for **MDA** ("bluish black", ISCC 193) but **no MDMA row**. (Wikipedia's Mandelin table attributes "MDMA — Bluish black" to NIJ; that attribution is not supported by the NIJ table.) |
| **Fentanyl** | **NOT FOUND** | — | Searched; none found. |
| **Cannabis / THC** | **NOT FOUND** | — | O'Neal 2000 / NIJ App. A Table 1 under A.4 contain no THC row; SIRCHIE Test No. 22 has no cannabis row; San Diego has no Mandelin section. Searched — none found. |

---

## 4. SCOTT TEST (cobalt thiocyanate / modified Scott)

| Substance | Verbatim colour result | Exact citation | Confidence note |
|---|---|---|---|
| **Cocaine HCl** | **Full 3-stage sequence:**<br>Stage 1 — "Cocaine – blue" (ppt) / "blue color results (positive, +, result)"; O'Neal A.1 = "Strong greenish blue" (ISCC **169**, **5B 5/10**)<br>Stage 2 — "pink"<br>Stage 3 — "intense blue" in lower chloroform layer; Sirchie "Blue → Pink → Pink over Blue"; San Diego "CoSCN- Blue Particles"<br>Rule: "A positive result at each stage is required…" | UNODC, *Recommended Methods for the Identification and Analysis of Cocaine in Seized Materials*, ST/NAR/7/Rev.1 (2012), §5.3.1.1 "Modified cobalt thiocyanate (Scott) test". https://www.unodc.org/pdf/publications/UNODC_Cocaine_Methods_rev_2012.pdf<br>O'Neal 2000 Table 2 row "A.1 Cocaine HCl"; NIJ Std–0604.01 App. A Table 1 row "A.1 Cocaine HCl" (LOD 60 µg, O'Neal Table 4).<br>SIRCHIE NARK20016_621ENG-REV12, Test No. 7 "Scott Reagent (modified)", row "Cocaine HCl (powder)".<br>City of San Diego *Narcotics Method Manual*, §2.2.2 (p. 7).<br>Wake County Ch. 7, §5.2.2: "Cocaine - blue".<br>DC DFS FCS10 Rev. 5, §7.2.4: "Upon mixing sample with reagent a blue color results (positive, +, result), indicating cocaine or a similar substance may be present." and "if the pink color turns blue, this indicates cocaine base may be present."<br>UGC e-PG Pathshala, Module 25, §4.20: "a blue colour develops at once which indicates the presence of cocaine. … The Chloroform layer becomes intense blue." | **High.** Six independent sources, consistent sequence. |
| **Heroin (diacetylmorphine HCl)** | "A strong but less green blue colour is produced by the hydrochloride salts of Cocaine, **Diacetylmorphine (Heroin)**, Ephedrine, Meperidine, Phencyclidine, Procaine, Propoxyphene and Pseudoephedrine." (cobalt thiocyanate test) | UGC e-PG Pathshala, *Forensic Science, Paper 9: Drugs of Abuse*, Module 25 "Colour Tests for Drug Identification", §4.2 "Cobalt Thiocyanate Test". | **Low–moderate: one source only.** ⚠ Counter-evidence must be shown: Darsigny 2018 Table 2 records **Cobalt "-"** for both codeine and morphine (i.e. no reaction for those two opiates), and neither SIRCHIE Test No. 7, Wake County §5.2.2, San Diego §2.2.5, nor UNODC ST/NAR/7 Rev.1 §5.3.1.1 contains a heroin row. Treat as unresolved. |
| **Methamphetamine** | Table 2 grid cell "Cobalt -" (no reaction) | Darsigny 2018, Table 2, row "Methamphetamine". | **Low: single source.** No other source located testing methamphetamine with cobalt thiocyanate/Scott. |
| **MDMA** | "MDMA reacts with all tests except Cobalt's test, since it does not possess a protonated tertiary amine."; Table 2 grid cell "Cobalt -" | Darsigny 2018, Introduction/Discussion (p. 3) and Table 2, row "MDMA". | **Moderate: one source, but with an explicit mechanistic rationale.** No second source found. |
| **Fentanyl** | (a) "The fentanyl standard and case material produced the colors that would be interpreted as cocaine using the aqueous cobalt thiocyanate and Young's tests." — and "The cocaine containing samples were distinguishable from the fentanyl containing samples with the Scott's and modified Scott's test when 1 mg of cocaine material was tested, whereas a 3-mg cocaine sample produced the same color sequence as fentanyl."<br>(b) "CoSCN- Blue on Particles"<br>(c) "In Scott's reagent, the color change most likely arises from coordination of tertiary amines to cobalt(II) thiocyanate, driving conversion of the pink octahedral Co(II) complex to a blue tetrahedral species." | (a) Kosecki TL, Brooke C, Canonico DL. "Fentanyl as a potential false positive with color tests commonly used for presumptive cocaine identification." *J Forensic Sci* 2022;67(5):2082–2088. doi:10.1111/1556-4029.15090; PMID 35766309 — **abstract obtained only** (full text paywalled).<br>(b) City of San Diego *Narcotics Method Manual*, July 2017, §2.2.3 (p. 7): "2.2.3 Fentanyl / Wagner- Brown Precipitate / CoSCN- Blue on Particles / Marquis- Weak Orange (sometimes)".<br>(c) "Modern Methods for Detection of Fentanyl and Its Analogues: A Review", *Pharmaceuticals* / PMC12430130, §2.7. | **Moderate.** Two independent sources agree fentanyl reads as a cobalt-thiocyanate "blue" indistinguishable from cocaine. ⚠ The Kosecki full text could not be read — only the published abstract is quoted. |
| **Cannabis / THC** | **NOT FOUND** | — | Searched; no source located. |

---

## 5. DUQUENOIS–LEVINE TEST

| Substance | Verbatim colour result | Exact citation | Confidence note |
|---|---|---|---|
| **Cannabis / THC** | (a) "A blue to violet color after the addition of HCl … is a positive reaction and indicates the possible presence of cannabinoids." + "After adding chloroform and mixing, a purple color in organic (lower) layer is a positive reaction…" + "NOTE: Known False Positives: Plants patchouli, cypress, and eucalyptus."<br>(b) "If the lower (chloroform) layer becomes violet coloured this indicates the presence of cannabis product."<br>(c) "A violet color should form. Add a few drops of chloroform (Levine modification) and the purple color should extract into the chloroform forming a purple or pink center for a positive identification of cannabinoids."<br>(d) "The violet colored lower (Chloroform) layer gives the positive indication of the presence of cannabis."<br>(e) "Marijuana, THC: Clear → Purplish-Blue → Light Blue-Purple over Dark Purple"<br>(f) "Only a few plants such as henna, nutmeg, mace and agrimony give false-positive results"<br>(g) "Gray purplish blue" (ISCC-NBS **204**, Munsell **7.5PB 4/4**), THC in ethanol, LOD **5 µg**<br>(h) "Colour tests for cannabis are among the most specific colour tests available" | (a) DC DFS, *FCS10 Procedure for Chemical Spot Tests*, Rev. 5 (10/31/2018), §7.8.4, p. 11.<br>(b) UNODC, *Recommended Methods for the Identification and Analysis of Cannabis in Seized Materials*, ST/NAR/40 (2009), §5.4.3.1.3 "Rapid Duquenois–Levine test".<br>(c) City of San Diego *Narcotics Method Manual*, July 2017, §8.1.3 (p. 26).<br>(d) UGC e-PG Pathshala, Module 25, §4.5.<br>(e) SIRCHIE NARK20016_621ENG-REV12, Test No. 5 "Duquenois-Levine Reagent", row "Marijuana, THC".<br>(f) UNODC ST/NAR/40 (2009), §5.4.3.1.<br>(g) O'Neal 2000, Table 2 row "A.3 THC EtOR" and Table 4 row "A.3 THC 5"; NIJ Std–0604.01 App. A Table 1 row "A.3 THC* EtOH".<br>(h) UNODC ST/NAR/40 (2009), §5.4.3.1. | **High.** Eight sources, all in the blue/violet/purple family; FCS10 adds the only explicit false-positive list among our sources. |
| **Cocaine HCl** | **NOT FOUND** | — | O'Neal 2000 Table 2 / NIJ App. A Table 1 under A.3 contain **only** "Mace Crystals / Nutmeg Extract / Tea Extract / THC" — no cocaine row. DC FCS10 §7.8.4 interprets the result **only** for cannabinoids. Searched specifically for explicit negatives — none located. |
| **Heroin** | **NOT FOUND** | — | Same as above: no A.3 row for diacetylmorphine in O'Neal/NIJ; FCS10 §7.8.4 is cannabinoid-only; SIRCHIE Test No. 5 has no heroin row; San Diego §8.1.3 is cannabis-only. Searched — none located. |
| **Methamphetamine** | **NOT FOUND** | — | Same evidence gap as above. |
| **MDMA** | **NOT FOUND** | — | Same evidence gap as above. |
| **Fentanyl** | **NOT FOUND** | — | Same evidence gap as above. |

> **Honest note on §5.** The Duquenois–Levine *positives* are among the best-sourced results in this report; the five *negatives* are not documented anywhere we could read. The nearest adjacent negative evidence found was City of San Diego §2.2.8: "GBL … Duquenois Reagent #1/Chens # 2- No Reaction" and "1, 4 Butanediol … Duquenois Reagent #1/Chens # 2- No Reaction" — i.e. the same laboratory does record Duquenois negatives, but **not** for any of our five target drugs. Reported rather than extrapolated.

---

## 6. FENTANYL IMMUNOCHROMATOGRAPHIC TEST STRIP (FTS)

Primary device: **BTNX Inc. Rapid Response™ Fentanyl Test Strip (Liquid & Powder)**, product insert no. 1110027361 REV 2.0, effective date 2021-01-20 (and companion insert H10110336601).

### 6.1 Result semantics (positive / negative / invalid)

| Reading | Verbatim text | Citation |
|---|---|---|
| **Positive** | "POSITIVE: Only one colored band appears, in the control region (C). No apparent colored band appears in the test region (T)." | BTNX Rapid Response™ Fentanyl Test Strip product insert, no. 1110027361 REV 2.0 (eff. 2021-01-20), "INTERPRETATION OF RESULTS". |
| **Negative** | "NEGATIVE: Two colored bands appear on the membrane. One band appears in the control region (C) and another band appears in the test region (T)." | as above |
| **Invalid** | "INVALID: Control band fails to appear. Results from any test which has not produced a control band at the specified read time must be discarded. Please review the procedure and repeat with a new test." | as above |
| **Faint line** | "NOTE: A very faint line in the test region indicates that the drug concentration is very close to the detection limit, in which case the test should be repeated or the sample should be additionally examined via a more specific method before a positive or negative result is determined." | as above |
| **Independent restatement** | "A positive result on this test strip gives one line, a negative result gives two lines, and an invalid test gives either no line or no control line." | Lockwood TL, Vervoordt A, Lieberman M. "High concentrations of illicit stimulants and cutting agents cause false positives on fentanyl test strips." *Harm Reduct J* 2021;18:30. doi:10.1186/s12954-021-00478-4; PMC7941948, Introduction. |
| **Community-harm-reduction restatement** | "One red line on top after waiting three minutes is a POSITIVE result … Two red lines is a NEGATIVE result. … No red lines (or one red line on the bottom) means the test is invalid." | DanceSafe, *Drug Checking Kits / Testing Instructions*, V16 (Fall 2022), "INTERPRETING THE RESULTS". |
| **Same convention for the companion amphetamine strip** | "(One red line is positive. Two red lines is negative.)" | DanceSafe V16, "USING OUR AMPHETAMINE TEST STRIPS". |
| **Procedural control** | "A colored band appearing in the control region (C) is considered an internal positive procedural control, confirming sufficient specimen volume and correct procedural technique." | BTNX insert 1110027361 REV 2.0, "QUALITY CONTROL". |

### 6.2 Read time and procedure

| Parameter | Verbatim text | Citation |
|---|---|---|
| **Dip duration** | "immerse it up to the MAX-mark into the liquid in the tube for 10 -15 sec" | BTNX insert 1110027361 REV 2.0, "EXAMINATION OF SOLID MATTER", step 7. |
| **Sample extraction** | "Dip the swab into the filled tube and leave it there for 1 to 2 minutes. Stir the swab in the buffer during this period…" | same, step 5 (graphic caption: "Stir for 1-2 min") |
| **Read window** | "Read the result after 5 minutes, but no later than 10 minutes after the strip has been dipped into the solution." (graphic caption: "Interpret result between 5-10 min") | same, step 9 and p. 2 graphic. |
| **Companion IFU wording** | "A result can be interpreted as positive when 60 seconds have passed since the control line has appeared and no line for that drug is present. Do not read results after 10 minutes." | BTNX Rapid Response Single Drug Test Strip IFU, H10110336601, "TEST PROCEDURE"/"RESULT INTERPRETATION". |
| **Independent confirmation of the window** | "The BTNX Inc. FTS product insert states to read the FTS between 5 and 10 min after sampling" | Lockwood et al. 2021, *Harm Reduct J* 18:30, Results (timing section), PMC7941948. |
| **Minimum wait (empirical)** | "From this data, a user should wait 2 min (120 s) at minimum when interpreting FTS." | Lockwood et al. 2021, Results. |
| **Community protocol** | "The results will appear after three minutes. Proceed to STEP 3. … Always wait three minutes before interpreting the results." | DanceSafe V16, fentanyl instructions. |

### 6.3 Sensitivity / cut-off

| Item | Verbatim | Citation |
|---|---|---|
| **Insert detection table** | "The following table lists compounds that are positively detected in fluid by the Rapid Response Fentanyl Test Strip (Liquid/ Powder) at 5 minutes. … **Fentanyl 200** ng/ml" (also: Carfentanil 5,000; Acetyl Fentanyl 150; Furanyl Fentanyl 500; p-Fluoro Fentanyl 200; 3-Methyl Fentanyl 500; Remifentanil 70,000; Sufentanil 100,000 ng/ml) | BTNX insert 1110027361 REV 2.0, "SPECIFICITY". |
| **Claimed urine cut-off** | "…lateral flow chromatographic immunoassay for the qualitative detection of fentanyl in urine at the cutoff concentration of 20 ng/mL." | Lockwood et al. 2021, Introduction. |
| **Visual LOD (independent)** | "The FTS limit of detection (LOD) was determined by eye to be 25 ng/mL due to the presence of a dark testing band … and is consistent with the FTS packaging stating a 20 ng/mL detection limit." | Lockwood et al. 2021, Results. |
| **Lot-to-lot drift** | "The two lots evaluated in 2017, 082, and 004, detected fentanyl at the manufacturer reported cutoff of 20 ng/mL. The three lots obtained in 2021, 018, 188, and 196, were only able to detect fentanyl down to a lower limit of 200 ng/mL, an order of magnitude above the reported cutoff." | Halifax JC, Lim L, Ciccarone D, Lynch KL. "Testing the test strips: laboratory performance of fentanyl test strips." *Harm Reduct J* 2024;21:14. doi:10.1186/s12954-023-00921-8; PMC10795297, "Fentanyl test strip sensitivity and cross-reactivity". |
| **Insert sensitivity table** | "0% Cut-off 50/50/0 · −50% Cut-off 50/50/0 · −25% Cut-off 50/50/0 · Cut-off 50 22 28 · +25% Cut-off 50 0 50 · +50% Cut-off 50 0 50 · +300% Cut-off 50 0 50" | BTNX insert 1110027361 REV 2.0, "SENSITIVITY". |
| **Temperature caveat** | "The FTS test band does not react properly at temperatures at or below 4 °C." | Lockwood et al. 2021, Results (temperature experiment). |
| **Disclaimer** | "Negative results can be obtained when drug is present but below the cut-off level of the test. The test does not distinguish between different fentanyl analogues and certain medications. Other compounds found in illicit drugs may display cross reactivity with the test device." | BTNX insert 1110027361 REV 2.0, "PERFORMANCE CHARACTERISTICS". |

### 6.4 Cross-reactivity vs. the five non-fentanyl target substances

| Substance | Result (verbatim) | Citation |
|---|---|---|
| **Fentanyl (target)** | "All five manufacturing lots cross-reacted with fentanyl and eleven fentanyl analogs." Detected analogs: "3-methylfentanyl, acetyl fentanyl, acrylfentanyl, β-hydroxy-thiofentanyl, butyrylfentanyl, carfentanil, cyclopropylfentanyl, fluorobutyrylfentanyl, furanyl fentanyl, p-fluorofentanyl, and tetrahydrofuran fentanyl." | Halifax et al. 2024, *Harm Reduct J* 21:14, Results, PMC10795297. |
| **Cocaine HCl → NEGATIVE** | "By eye, FTS with cocaine, alprazolam, gabapentin, and naloxone buprenorphine were negative even at the highest concentration, with the appearance of dark bands in both the control and test regions" — tested from 20 mg/mL down to 0.2 mg/mL.<br>"…heroin (10 µg/mL), 6-acetylcodeine (10 µg/mL), quinidine (10 µg/mL), **cocaine (25 mg/mL)**, and ketamine (25 mg/mL) showed no degree of cross-reactivity or interference." | Lockwood et al. 2021, *Harm Reduct J* 18:30, Results, PMC7941948.<br>Halifax et al. 2024, *Harm Reduct J* 21:14, "Strip sensitivity and cross-reactivity", PMC10795297. |
| **Heroin → NEGATIVE** | "…**heroin (10 µg/mL)**, 6-acetylcodeine (10 µg/mL), quinidine (10 µg/mL), cocaine (25 mg/mL), and ketamine (25 mg/mL) showed no degree of cross-reactivity or interference." | Halifax et al. 2024, *Harm Reduct J* 21:14, PMC10795297 (2017-sourced lots 082 and 004). |
| **Methamphetamine → FALSE POSITIVE** | "The critical concentration level for diphenhydramine capsules was 1 mg/mL, for diphenhydramine tablets 2.5 mg/mL, **methamphetamine was 1.5 mg/mL**, and MDMA was 2 mg/mL. At or above these concentrations, the FTS is likely to produce a false positive result."<br>"Cross-reactivity with methamphetamine was stereospecific, with l-methamphetamine at 25 mg/mL producing a negative result and d-methamphetamine producing a positive result when tested at 5 mg/mL."<br>2021 lots: "Lidocaine (2.5 mg/mL) and d-methamphetamine (10 mg/mL) produced false positives at the same cutoffs across all three lots." | Lockwood et al. 2021, Results, PMC7941948.<br>Halifax et al. 2024, *Harm Reduct J* 21:14, "Strip sensitivity and cross-reactivity" and "Follow-up interference testing", PMC10795297. |
| **MDMA → FALSE POSITIVE** | "**MDMA produced a positive result on the test strip at 50 mg/mL**." (2017 lots)<br>"MDMA produced false positives at 5 mg/mL for lots 018 and 188, but at 2.5 mg/mL for lot 196." (2021 lots)<br>Lockwood: "**MDMA was 2 mg/mL**" critical concentration. | Halifax et al. 2024, Results, PMC10795297.<br>Lockwood et al. 2021, Results, PMC7941948. |
| **Cannabis / THC → NOT FOUND** | — | Cannabis/THC was **not** among the 11 illicit drugs and adulterants evaluated. Halifax et al. 2024 explicitly states: "only 11 illicit drugs and adulterants were evaluated for potential cross-reactivity and other untested substances could produce a false-positive FTS result." The BTNX insert "no cross-reactivity at 100 µg/ml" list (acetaminophen, ephedrine, lidocaine, methadone, procaine, quinidine, pseudoephedrine, etc.) does **not** include cannabis or any cannabinoid — and equally does **not** include our other four target drugs. Searched — no source found. |
| **Caveat from the manufacturer** | "Other compounds found in illicit drugs may display cross reactivity with the test device." / "Cross reactivity with other emerging fentanyl analogs, such as U-47700, cyclopentyl fentanyl, is yet to be determined." | BTNX insert 1110027361 REV 2.0, "PERFORMANCE CHARACTERISTICS" and "*The test device is designed to screen for the presence of Fentanyl…" footnote. |
| **Strips are not a field colour test** | "High concentrations of illicit stimulants and cutting agents cause false positives on fentanyl test strips." (title) and "Samples for drug checking should be significantly diluted to avoid false positives from diphenhydramine, methamphetamine, and MDMA." | Lockwood et al. 2021, title and Conclusions. |

---

## 7. Documented conflicts (do not average these away)

| # | Pair | Source A | Source B | Status |
|---|---|---|---|---|
| 1 | **MARQUIS × cocaine** | DC DFS FCS10 Rev.5 §7.1.4: "**Salmon** may indicate presence of Cocaine" | Darsigny 2018 Table 3: "**Colorless**"; San Diego §2.2.2: "Marquis- **No Reaction**"; DanceSafe V16: "**light pink color or not change color at all**" | Unresolved — 3 vs 1, but the dissenting source is a working forensic SOP, not a blog. |
| 2 | **MANDELIN × methamphetamine** | NIJ/O'Neal: "**Dark yellowish green**" (10GY 4/6); SIRCHIE Test 22: "**Yellow-Green**"; UNODC SCITEC/16 Table LIII: "**yellow green**" | Darsigny 2018 Table 3: "**No change**"; Table 2: Mandelin "-" | Unresolved — 3 vs 1. Darsigny offers a structural explanation; the others are colour-chart entries. |
| 3 | **MARQUIS × fentanyl** | Wake County §5.1.2: "**Fentanyl - orange**"; San Diego §2.2.3: "**Weak Orange (sometimes)**" | Canoura et al., *JACS Au* 2024: "**dark brown** … the signature color of fentanyl for this test" | Unresolved — orange family vs brown. The JACS Au paper itself warns fentanyl/lidocaine colours are confusable. |
| 4 | **MECKE × MDMA** | Darsigny 2018: "**purple-black**"; UGC e-PG: "**purple/black**" | San Diego §2.2.1: "**Green/Blue**" | Hue disagreement; positivity not in dispute. |
| 5 | **MARQUIS × MDMA** | Wake/SIRCHIE/Darsigny: purple-black / black / black-violet | San Diego §2.2.1: "**Green and/or Purple Black**" | Outlier noted; majority is purple/black. |
| 6 | **SCOTT × heroin** | UGC e-PG §4.2: cobalt thiocyanate gives "a strong but less green blue colour" with diacetylmorphine HCl | Darsigny Table 2: Cobalt "-" for codeine **and** morphine; no heroin row in UNODC ST/NAR/7, SIRCHIE Test 7, Wake §5.2.2 or San Diego | Unresolved — single affirmative source. |
| 7 | **MDA vs MDMA attribution** | Wikipedia's Mandelin/Marquis tables list "**MDMA — Bluish black**" citing NIJ | NIJ Std–0604.01 App. A Table 1 contains a row for **MDA HCl**, **not MDMA** (under both A.4 and A.5) | The Wikipedia attribution is not supported by the cited table. Do not use. |

---

## 8. Full source list (URL + how it was read)

**Text-layer PDFs (extracted with pypdf 6.19.0 and read locally):**

1. **O'Neal CL, Crouch DJ, Fatah AA.** "Validation of twelve chemical spot tests for the detection of drugs of abuse." *Forensic Science International* 109 (2000) 189–201 (PII S0379-0738(99)00235-2). — file `oneal2000.pdf` → `.txt`, 21 pp, full text layer; pages 10–12 additionally re-extracted in layout mode for Tables 2–4.
2. **National Institute of Justice.** *Color Test Reagents/Kits for Preliminary Identification of Drugs of Abuse*, NIJ Standard–0604.01, Law Enforcement and Corrections Standards and Testing Program, U.S. Dept. of Justice, Office of Justice Programs, July 2000, NCJ 183258. https://www.ojp.gov/pdffiles1/nij/183258.pdf (mirror: https://www.ncjrs.gov/pdffiles1/nij/183258.pdf). — file `nij0605.pdf` → `.txt`, 26 pp, full text layer. **Confirms: no cocaine row under A.5, no MDMA row under A.4/A.5, no THC row under A.4/A.5/A.10, no fentanyl anywhere.**
3. **Darsigny C, Couture ML, Desgagné-Penix I.** "Forensic Chemistry of Alkaloids: Presumptive Color Test." *Austin J Forensic Sci Criminol.* 2018;5(1):1074. — file `darsigny2018.pdf` → `.txt`, full text layer; Tables 2 and 3 read directly.
4. **District of Columbia, Department of Forensic Sciences.** *FCS10 Procedure for Chemical Spot Tests*, Document Control Number 7474, Revision 5, issue date 10/31/2018. https://dfs.dc.gov/sites/default/files/dc/sites/dfs/publication/attachments/FCS10%20-%20Procedure%20for%20Chemical%20Spot%20Tests.pdf — file `fcs10.pdf` → `.txt`, 16 pp, full text layer. **Contains Marquis (§7.1), cobalt thiocyanate (§7.2), Duquenois–Levine (§7.8); no Mandelin, no Mecke, no fentanyl strip.**
5. **United Nations Office on Drugs and Crime.** *Recommended Methods for the Identification and Analysis of Cocaine in Seized Materials*, ST/NAR/7/Rev.1 (2012). — file `unodc_cocaine.pdf` → `.txt`, full text layer; §5.3.1.1 read directly.
6. **United Nations Office on Drugs and Crime.** *Recommended Methods for the Identification and Analysis of Cannabis in Seized Materials*, ST/NAR/40 (2009). — file `unodc_cannabis.pdf` → `.txt`, full text layer; §§5.4.3.1, 5.4.3.1.3 read directly.
7. **United Nations Office on Drugs and Crime, SCITEC.** *Screening Colour Test and Specific Colour Tests for the Detection of Methylendioxyamphetamine and Amphetamine Type Stimulants*, SCITEC/16. https://www.unodc.org/documents/scientific/Screening_Colour_Test_ATS.pdf — file `scitec16_ats.pdf` → `.txt`, 43 pp, full text layer (Table II reagent list, Table XXIX MDMA, Table LIII amphetamine/methamphetamine cross-reactivity).
8. **United Nations Office on Drugs and Crime, SCITEC.** *Colour Tests for Precursor Chemicals of Amphetamine-Type Substances*, SCITEC/21 (2007), https://www.unodc.org/documents/scientific/SCITEC21_07fin.pdf — read via search excerpts + `scitec6.pdf`/`scitec6.txt` companion (full text layer).
9. **BTNX Inc.** *Fentanyl Test Strips (Liquid & Powder) — Product Insert*, number 1110027361 REV 2.0, effective date 2021-01-20. — file `btnx_insert.pdf` → `.txt`, 2 pp, full text layer.
10. **BTNX Inc.** *Rapid Response™ Single Drug Test Strip* IFU, H10110336601. — file `btnx_ifu.pdf` → `.txt`, full text layer.
11. **Wake County Bureau of Forensic Services.** *Drug Chemistry Unit Technical Procedures*, Chapter 7: "Color Tests", Effective Date 8/25/2021, Issued By: Director. https://public.powerdms.com/WakeBI/documents/1745769 — file `wake_color.pdf` → `.txt`, 12 pp, full text layer. **Contains Marquis (§5.1) and cobalt thiocyanate (§5.2) only — no Mecke, no Mandelin, no Duquenois–Levine.**
12. **SIRCHIE.** *NARK® Color Identification Chart*, document NARK20016_621ENG-REV12 (3/20, © 2020). https://www.sirchie.com/media/resourcecenter/item/n/a/nark20016_621eng-rev12.pdf — file `sirchie_chart.pdf` → `.txt`, full text layer; all 34 test rows read directly.
13. **University Grants Commission / e-PG Pathshala (Inflibnet).** *Forensic Science, Paper No. 9: Drugs of Abuse, Module No. 25: Colour Tests for Drug Identification*. https://epgp.inflibnet.ac.in/epgpdata/uploads/epgp_content/S000016FS/P000696/M011517/ET/1516251256FSC_P9_M25_e-text.pdf — file `epgp_colortests.pdf` → `.txt`, 13 pp, full text layer; §§4.2, 4.5, 4.9, 4.14, 4.20 and §5 summary table read directly.
14. **City of San Diego, Police Department.** *Narcotics Method Manual*, July 2017 (Issuing Authority: Frank Healy, QM; marked ARCHIVED). https://www.sandiego.gov/sites/default/files/narcoticsmethodmanualjul2017-oct2017.pdf — file `sandiego_manual.pdf` → `.txt`, 36 pp, full text layer; §§2.2.1–2.2.8, 8.1.3, 9.1.1 and Appendix reagent-prep list read directly. **Contains Marquis, Mecke, cobaltous thiocyanate, Duquenois–Levine — no Mandelin.**
15. **DanceSafe.** *Drug Checking Kits / Testing Instructions*, Version V16 (Fall 2022). https://dancesafe.org/wp-content/uploads/2023/01/DS_Testing-Instructions_V16_Fall22-1.pdf — file `dancesafe_v16.pdf` → `.txt`, 8 pp, full text layer. (Manufacturer of consumer reagent kits — lower provenance tier than a laboratory SOP; used only where it states something the SOPs do not.)
16. **Canoura J, Alkhamis O, Venzke M, Ly PT, Xiao Y.** "Developing Aptamer-Based Colorimetric Opioid Tests." *JACS Au* 2024;4(3):1059–1072. doi:10.1021/jacsau.3c00801; PMC10976566. — retrieved as Europe PMC `fullTextXML` and converted to text (`aptamer_opioid.xml` → `aptamer_opioid.txt`); Marquis paragraphs read directly.
17. **Lockwood TL, Vervoordt A, Lieberman M.** "High concentrations of illicit stimulants and cutting agents cause false positives on fentanyl test strips." *Harm Reduct J* 2021;18:30. doi:10.1186/s12954-021-00478-4; PMC7941948. — Europe PMC `fullTextXML` → `lockwood2021.txt`.
18. **Halifax JC, Lim L, Ciccarone D, Lynch KL.** "Testing the test strips: laboratory performance of fentanyl test strips." *Harm Reduct J* 2024;21(1):14. doi:10.1186/s12954-023-00921-8; PMC10795297. — Europe PMC `fullTextXML` → `halifax2024.txt`.
19. **"Modern Methods for Detection of Fentanyl and Its Analogues: A Review."** PMC12430130. — Europe PMC `fullTextXML` → `fentanyl_review2025.txt`; §2.7 colourimetric methods read directly.
20. **UNODC SCITEC/6** *The Chemistry of Colour Tests and Reagent Preparations* (1989) — `scitec6.pdf` → `.txt`, full text layer (Marquis/Mecke/Froehde chemistry background).

**Sources used but NOT quoted (declared):**

- **UNODC, *Rapid Testing Methods of Drugs of Abuse*, ST/NAR/13/Rev.1** — `stnar13rev1.pdf`: **no text layer** (title-page metadata only). Google/OCR snippets containing apparent Duquenois-Levine and Scott wording were **deliberately not quoted** because they are OCR of a scan, not a text layer.
- **UNODC, *Rapid Testing Methods* (1994/1995)** — `unodc_rapid_testing.pdf`: **no text layer**, same handling.
- **Kosecki TL, Brooke C, Canonico DL.** *J Forensic Sci* 2022;67(5):2082–2088, doi:10.1111/1556-4029.15090 — **abstract only** (Wiley paywall). Quoted as abstract; full text not read.
- **RSC *Analytical Methods*** article D6AY00085A — OIDC login / redirect loop; **never read**.
- **Johns SH et al., "Spot Tests: A Color Chart Reference for Forensic Chemists," *J Forensic Sci* 24 (1979) 631–649** — download failed (0 bytes); **never read**.
- **Virginia Dept. of Forensic Science, Controlled Substances Procedures Manual (2013)** — Wayback download returned HTTP 429; **never read**. (The Virginia Regulatory Town Hall *approved field tests* notice **was** read: it lists Marquis approved for heroin/amphetamine/methamphetamine/MDMA, Duquenois–Levine for marijuana/THC/THC, and Scott (Modified) for cocaine HCl — an *approval* list, not a colour list, so it is not used as a colour source.)
- **Morris J., "Color Tests and Analytical Difficulties with Emerging Drugs of Abuse" (NIST/Ames, 2013)** — `morris_colortests.pdf` extracted only 10,065 chars from 36 pages (predominantly slide graphics). Usable fragment: "**No color with Duquenois-Levine**" — but that statement concerns **synthetic cannabinoids** (JWH-018, JWH-073, CP-47,497, HU-210), not classical cannabis/THC, and is therefore **not** used for the cannabis row.
- **Wikipedia** Marquis / Mecke / Mandelin colour tables — traced to NIJ Standard–0604.01 (NCJ 183258), which we hold directly; **not cited** (see conflict #7).

---

## 9. Open gaps (`NOT FOUND`)

Nine of the 36 cells could not be filled with a readable source:

| # | Cell | What was searched / why it failed |
|---|---|---|
| 1 | **MARQUIS × cannabis** | No SOP or chart found giving a Marquis colour for cannabis/THC. Absent from O'Neal 2000 Table 2, NIJ App. A Table 1, DC FCS10 §7.1.4, Wake §5.1.2, SIRCHIE Test 1, San Diego §2.2. Multiple targeted web searches returned only Duquenois/Fast Blue B references. |
| 2 | **MECKE × cannabis** | Absent from O'Neal/NIJ A.10 (only mace/nutmeg/tea/sugar rows) and from SIRCHIE Test 11. Not found elsewhere. |
| 3 | **MECKE × fentanyl** | Not found in any readable source. |
| 4 | **MANDELIN × cannabis** | Absent from O'Neal/NIJ A.4; SIRCHIE Test 22 has no cannabis row; San Diego and Wake contain no Mandelin section. |
| 5 | **MANDELIN × fentanyl** | Not found in any readable source. |
| 6 | **SCOTT × cannabis** | Not found in any readable source (UNODC ST/NAR/7 §5.3.1.1, SIRCHIE Test 7, Wake §5.2.2, San Diego §2.2.2, UGC §4.20 all lack a cannabis row). |
| 7 | **DUQUENOIS–LEVINE × cocaine** | No explicit negative located. O'Neal/NIJ A.3 contains only mace/nutmeg/tea/THC; FCS10 §7.8.4 interprets only cannabinoids. |
| 8 | **DUQUENOIS–LEVINE × heroin, × methamphetamine, × MDMA, × fentanyl** (4 cells) | Same evidence gap as #7. Searched for specificity studies (Pitt 1972 *J Forensic Sci* 17:693–700 is cited by FCS10 ref. 13.7 but was not obtained; Jacobs et al. 2014 PMID 24709027 obtained as PubMed record only). |
| 9 | **FENTANYL STRIP × cannabis** | Cannabis/THC was not among the 11 illicit drugs/adulterants tested by Halifax et al. 2024 (which states as much explicitly), was not tested by Lockwood et al. 2021 (which tested cocaine, methamphetamine, MDMA, alprazolam, gabapentin, naloxone/buprenorphine, diphenhydramine), and is absent from the BTNX insert's no-cross-reactivity list. |
| 10 | **MANDELIN × MDMA — second source** | Only Darsigny 2018 and UGC e-PG §4.14 were found; the NIJ/O'Neal A.4 table has **MDA, not MDMA**. |
| 11 | **SCOTT × methamphetamine — second source** | Only Darsigny 2018 Table 2 ("Cobalt -"). |
| 12 | **MECKE × cocaine / × methamphetamine — second sources** | Only Darsigny 2018. |
| 13 | **Kosecki 2022 full text** | Paywalled; the Scott × fentanyl result rests on the published abstract plus the San Diego SOP. |

**Also unresolved:** the seven source-to-source conflicts listed in §7.

---

*Every colour statement above is quoted from a source that was actually fetched and read in this session. Where a source was scanned, paywalled, or otherwise unreadable, it is listed in §8 as "declared" rather than paraphrased.*

