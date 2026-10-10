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
