import { createClient } from "@supabase/supabase-js"

const supabaseUrl = "https://ffasqfccgbgopxpfqrus.supabase.co"
const supabaseKey =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZmYXNxZmNjZ2Jnb3B4cGZxcnVzIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MTg2OTEwNCwiZXhwIjoyMDY3NDQ1MTA0fQ.8B6URog2lDENg5cuBlUdpn2CiVEJiKHiMINJfNgvqZc"

export const supabase = createClient(supabaseUrl, supabaseKey)

export interface TonnageRecord {
  id: number
  Date: string
  "Flight No.": string // Keeping database field name for compatibility, but will display as "Shipment ID"
  ACM: string // Will display as "Vehicle Type"
  KG: number
  Reg: string // Will display as "Vehicle ID"
  Month: string
  Year: number
  Day: string
  Sector: string
  Dep: string // Will display as "Origin"
  Arr: string // Will display as "Destination"
  "Out/In": string
  Station: string
  "Dom/Int": string
}
