// Laengen-Einheiten fuer die Anzeige im Anlagenmodell.
//
// Semantik (verbindlich):
//   - Transport/Backend ist IMMER ganze Millimeter (int). Jeder gesendete und
//     jeder empfangene Laengenwert ist eine ganze mm-Zahl.
//   - Die Anzeige-Einheit ('mm' | 'cm' | 'zoll') ist reine UI-Darstellung und
//     wird zentral im anlage-Store gehalten. Umrechnung ausschliesslich an der
//     UI-Kante ueber fromMm()/toMm().
//   - 1 Zoll = 25,4 mm.

export type LengthUnit = 'mm' | 'cm' | 'zoll'

export const LENGTH_UNITS: LengthUnit[] = ['mm', 'cm', 'zoll']

const MM_PER_UNIT: Record<LengthUnit, number> = {
  mm: 1,
  cm: 10,
  zoll: 25.4,
}

// Kurzlabel fuer die UI-Anzeige der Einheit.
export const UNIT_LABEL: Record<LengthUnit, string> = {
  mm: 'mm',
  cm: 'cm',
  zoll: '″',
}

// mm -> Anzeige-Einheit. Fuer Anzeige/Eingabe gedacht; KEINE Rundung auf ganze
// mm (die passiert erst beim Zuruecksenden in toMm). mm: identisch; cm: /10;
// zoll: /25,4.
export function fromMm(valueMm: number, unit: LengthUnit): number {
  return valueMm / MM_PER_UNIT[unit]
}

// Anzeige-Einheit -> GANZE mm (fuer Transport/Backend). Immer auf ganze mm
// gerundet: mm: Math.round(input); cm: Math.round(input*10); zoll:
// Math.round(input*25,4).
export function toMm(input: number, unit: LengthUnit): number {
  return Math.round(input * MM_PER_UNIT[unit])
}

// Formatiert einen mm-Wert fuer die Anzeige in der gewaehlten Einheit.
// Liefert zusaetzlich, ob die Rundung sichtbar gemacht werden sollte: Bei
// nicht-metrischer Einheit (zoll) bzw. wenn die Rueckrechnung einer Eingabe auf
// ganze mm einen abweichenden Wert ergibt, kann die UI den tatsaechlich
// gesendeten mm-Wert anzeigen ("gespeichert als 1016 mm").
export function formatLength(
  valueMm: number | null,
  unit: LengthUnit,
): { text: string; mm: number | null } {
  if (valueMm === null) {
    return { text: '—', mm: null }
  }
  const converted = fromMm(valueMm, unit)
  // Kompakte Darstellung ohne ueberfluessige Nachkommastellen.
  const text = `${Number(converted.toFixed(3))} ${UNIT_LABEL[unit]}`
  return { text, mm: valueMm }
}
