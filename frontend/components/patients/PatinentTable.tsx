'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Phone, History, Edit, Trash2 } from 'lucide-react';
import { initiateCall } from '@/lib/api';

import { toast } from 'sonner';
import AddPatientModal from './AddPatientModal';
import EditPatientModal from './EditPatientmodal';

interface Patient {
  id: number;
  name: string;
  phone: string;
  age: number;
  language: string;
  custom_questions: string;
  call_count?: number;
}

interface PatientTableProps {
  patients: Patient[];
  onRefresh: () => void;
}

export default function PatientTable({ patients, onRefresh }: PatientTableProps) {
  const router = useRouter();
  const [calling, setCalling] = useState<number | null>(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingPatient, setEditingPatient] = useState<Patient | null>(null);
  const [deletingPatient, setDeletingPatient] = useState<number | null>(null);

  const handleCall = async (patientId: number) => {
    setCalling(patientId);
    try {
      await initiateCall(patientId);
      toast.success('Call initiated successfully');
      onRefresh();
    } catch (error) {
      toast.error('Failed to initiate call');
    } finally {
      setCalling(null);
    }
  };

  const handleDelete = async (patient: Patient) => {
    if (!confirm(`Are you sure you want to delete ${patient.name}? This will delete all associated calls and transcripts.`)) {
      return;
    }

    setDeletingPatient(patient.id);
    try {
      const response = await fetch(`http://localhost:8000/api/calls/patients/${patient.id}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        toast.success('Patient deleted successfully');
        onRefresh();
      } else {
        toast.error('Failed to delete patient');
      }
    } catch (error) {
      toast.error('Error deleting patient');
    } finally {
      setDeletingPatient(null);
    }
  };

  return (
    <>
      <div className="p-6">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-semibold text-gray-900">
            Patients ({patients.length})
          </h2>
          <button
            onClick={() => setShowAddModal(true)}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            + Add Patient
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Name
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Phone
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Age
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Language
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Calls
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {patients.map((patient) => (
                <tr key={patient.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm font-medium text-gray-900">{patient.name}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-500">{patient.phone}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-500">{patient.age} years</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                      {patient.language}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-500">{patient.call_count || 0}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <div className="flex justify-end gap-2">
                      <button
                        onClick={() => handleCall(patient.id)}
                        disabled={calling === patient.id}
                        className="inline-flex items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400"
                      >
                        <Phone className="h-4 w-4 mr-1" />
                        {calling === patient.id ? 'Calling...' : 'Call'}
                      </button>
                      <button
                        onClick={() => router.push(`/patients/${patient.id}`)}
                        className="inline-flex items-center px-3 py-2 border border-gray-300 text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
                      >
                        <History className="h-4 w-4 mr-1" />
                        History
                      </button>
                      <button
                        onClick={() => setEditingPatient(patient)}
                        className="inline-flex items-center px-3 py-2 border border-gray-300 text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
                      >
                        <Edit className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => handleDelete(patient)}
                        disabled={deletingPatient === patient.id}
                        className="inline-flex items-center px-3 py-2 border border-red-300 text-sm leading-4 font-medium rounded-md text-red-700 bg-white hover:bg-red-50 disabled:bg-gray-100"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {patients.length === 0 && (
            <div className="text-center py-12 text-gray-500">
              No patients found
            </div>
          )}
        </div>
      </div>

      <AddPatientModal
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
        onSuccess={() => {
          onRefresh();
          setShowAddModal(false);
        }}
      />

      {editingPatient && (
        <EditPatientModal
          patient={editingPatient}
          isOpen={true}
          onClose={() => setEditingPatient(null)}
          onSuccess={() => {
            onRefresh();
            setEditingPatient(null);
          }}
        />
      )}
    </>
  );
}
