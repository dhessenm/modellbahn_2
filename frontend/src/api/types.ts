// Datentypen passend zur Backend-REST-API (siehe src/modellbahn/api/schemas.py).

export interface SystemStatus {
  connected: boolean
  track_power_on: boolean
  z21_host: string
  z21_port: number
}

export interface LocoState {
  address: number
  speed: number
  forward: boolean
  functions: Record<number, boolean>
}
