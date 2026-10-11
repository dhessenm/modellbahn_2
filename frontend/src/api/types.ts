// Datentypen passend zur Backend-REST-API (siehe src/modellbahn/api/schemas.py).

export interface SystemStatus {
  connected: boolean
  track_power_on: boolean
  short_circuit: boolean
  emergency_stop: boolean
  temperature_c: number
  supply_voltage_mv: number
  track_voltage_mv: number
  z21_host: string
  z21_port: number
}

export interface LocoState {
  address: number
  speed: number
  forward: boolean
  functions: Record<number, boolean>
}

export interface TurnoutState {
  address: number
  position: number | null // 0, 1 oder null (noch nicht geschaltet)
}

// CAN-Belegtmelder (Roco Z21 Detector 10808), passend zu schemas.py.
export interface DetectorLoco {
  address: number
  direction: 'forward' | 'backward' | 'unknown'
}

export interface DetectorInput {
  nid: number // unveraenderbare CAN-NetworkID (stabile Melder-Identitaet)
  addr: number // konfigurierbare Moduladresse (nur Anzeigeinfo, ggf. 0)
  port: number // Eingang 0..7 (intern 0-basiert; die UI zeigt Port+1 an)
  occupied: boolean
  with_power: boolean
  overload: boolean
  overload_level: number
  status_text: string
  locos: DetectorLoco[]
}
