/** Shared constants - must stay byte-identical to backend/app/enums.py. */

export const DISCLAIMER =
  'PRESUMPTIVE FIELD RESULT ONLY. Not a substitute for laboratory ' +
  'confirmatory testing. Colour and immunoassay tests are presumptive; ' +
  'confirmatory methods (GC-MS, LC-MS, FTIR, etc.) are required before any ' +
  'substance is considered identified.'

export const CONCENTRATION_NOTE =
  'Concentration: not determinable from presumptive tests'

export const DEMO_CITATION =
  "DEMO DATA - verify against UNODC Recommended Methods and the kit " +
  "manufacturer's colour chart before real use"

export const RESULT_STATUSES = [
  'NO_MATCH',
  'WEAK_PRESUMPTIVE',
  'PRESUMPTIVE',
  'STRONG_PRESUMPTIVE',
  'INCONCLUSIVE',
  'CONFIRMED_BY_LAB',
] as const

export type ResultStatus = (typeof RESULT_STATUSES)[number]

export const AMBIGUOUS_STATUSES = ['INCONCLUSIVE'] as const satisfies readonly ResultStatus[]
