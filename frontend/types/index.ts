// types/index.ts
export type PatientType = 'discharged' | 'opd';

export type CallStatus = 'pending' | 'in_progress' | 'completed' | 'failed';

export interface Patient {
  [x: string]: never[];
  id: number;
  mrn: string;
  name: string;
  age: number | null;
  phone_number: string;
  city: string | null;
  patient_type: PatientType;
  discharge_date: string | null;
  appointment_date: string | null;
  created_at: string;
  updated_at: string;
}

export interface Call {
  id: number;
  call_uuid: string;
  patient_id: number;
  status: CallStatus;
  duration: number;
  started_at: string | null;
  ended_at: string | null;
  created_at: string;
}

export interface CallResponse {
  status: string;
  message: string;
  call_id: number;
  call_uuid: string;
  patient_name: string;
  phone_number: string;
}
