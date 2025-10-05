'use client';

import { useEffect, useState } from 'react';
import { getPatients, initiateCall, getPatientCalls } from '@/lib/api';

interface Patient {
  id: number;
  name: string;
  phone: string;
  age: number;
  language: string;
  custom_questions: string;
}

export default function PatientsPage() {
  const [patients, setPatients] = useState<Patient[]>([]);
  const [loading, setLoading] = useState(true);
  const [calling, setCalling] = useState<number | null>(null);

  useEffect(() => {
    loadPatients();
  }, []);

  const loadPatients = async () => {
    try {
      const data = await getPatients();
      setPatients(data.patients || []);
    } catch (error) {
      console.error('Error loading patients:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCall = async (patientId: number) => {
    setCalling(patientId);
    try {
      const result = await initiateCall(patientId);
      alert(`Call initiated! Status: ${result.status}`);
    } catch (error) {
      alert('Failed to initiate call');
    } finally {
      setCalling(null);
    }
  };

  if (loading) {
    return <div className="p-8">Loading patients...</div>;
  }

  return (
    <div className="min-h-screen p-8">

      <div className="max-w-7xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold">Patients</h1>
          <button className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
            + Add Patient
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {patients.map((patient) => (
            <div key={patient.id} className="bg-white p-6 rounded-lg shadow">
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h2 className="text-xl font-semibold">{patient.name}</h2>
                  <p className="text-gray-600 text-sm">{patient.phone}</p>
                </div>
                <span className="px-2 py-1 bg-green-100 text-green-800 text-xs rounded">
                  {patient.language}
                </span>
              </div>

              <div className="mb-4">
                <p className="text-sm text-gray-600">
                  Age: {patient.age} years
                </p>
                {patient.custom_questions && (
                  <p className="text-sm text-gray-500 mt-2 line-clamp-2">
                    Questions: {patient.custom_questions}
                  </p>
                )}
              </div>

              <div className="flex gap-2">
                <button
                  onClick={() => handleCall(patient.id)}
                  disabled={calling === patient.id}
                  className="flex-1 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-400"
                >
                  {calling === patient.id ? 'Calling...' : 'Call Now'}
                </button>
                <button
                  onClick={() => window.location.href = `/patients/${patient.id}`}
                  className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-50"
                >
                  History
                </button>
              </div>
            </div>
          ))}
        </div>

        {patients.length === 0 && (
          <div className="text-center py-12 text-gray-500">
            No patients found. Add a patient to get started.
          </div>
        )}
      </div>
    </div>
  );
}
