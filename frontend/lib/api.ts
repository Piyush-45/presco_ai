const API_BASE = 'http://localhost:8000/api/calls';

export async function getPatients() {
  const res = await fetch(`${API_BASE}/patients`);
  return res.json();
}

export async function initiateCall(patientId: number) {
  const res = await fetch(`${API_BASE}/initiate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ patient_id: patientId }),
  });
  return res.json();
}

export async function getPatientCalls(patientId: number) {
  const res = await fetch(`${API_BASE}/patients/${patientId}/calls`);
  return res.json();
}

export async function getCallTranscript(callId: number) {
  const res = await fetch(`${API_BASE}/calls/${callId}/transcript`);
  return res.json();
}
