'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { getPatientCalls } from '@/lib/api';

interface Call {
  call_id: number;
  call_sid: string;
  status: string;
  duration: number;
  cost: number;
  started_at: string;
  ended_at: string | null;
}

export default function PatientCallHistoryPage() {
  const params = useParams();
  const router = useRouter();
  const patientId = params.id as string;
  const [calls, setCalls] = useState<Call[]>([]);
  const [patientName, setPatientName] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadCalls();
  }, [patientId]);

  const loadCalls = async () => {
    try {
      const data = await getPatientCalls(Number(patientId));
      setCalls(data.calls || []);
      setPatientName(data.patient_name || 'Patient');
    } catch (error) {
      console.error('Error loading calls:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="p-8">Loading call history...</div>;
  }

  return (
    <div className="min-h-screen p-8">
      <div className="max-w-7xl mx-auto">
        <button
          onClick={() => router.back()}
          className="text-blue-600 hover:text-blue-800 mb-4"
        >
          ← Back to Patients
        </button>

        <h1 className="text-3xl font-bold mb-2">{patientName}</h1>
        <p className="text-gray-600 mb-8">Call History ({calls.length} total calls)</p>

        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Date
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Duration
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Cost
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {calls.map((call) => (
                <tr key={call.call_id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    {new Date(call.started_at).toLocaleString()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    {call.duration ? `${Math.floor(call.duration / 60)}m ${call.duration % 60}s` : 'N/A'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`px-2 py-1 text-xs rounded-full ${
                      call.status === 'completed'
                        ? 'bg-green-100 text-green-800'
                        : call.status === 'answered'
                        ? 'bg-blue-100 text-blue-800'
                        : 'bg-gray-100 text-gray-800'
                    }`}>
                      {call.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    ${call.cost.toFixed(4)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <button
                      onClick={() => router.push(`/calls/${call.call_id}`)}
                      className="text-blue-600 hover:text-blue-800"
                    >
                      View Details
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {calls.length === 0 && (
            <div className="text-center py-12 text-gray-500">
              No calls found for this patient
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
