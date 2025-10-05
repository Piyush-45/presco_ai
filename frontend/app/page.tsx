'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getPatients } from '@/lib/api';

import { Loader2 } from 'lucide-react';
import PatientTable from '@/components/patients/PatinentTable';

type TabType = 'all' | 'called' | 'never-called' | 'opd' | 'discharged';

export default function DashboardPage() {
  const [activeTab, setActiveTab] = useState<TabType>('all');

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['patients'],
    queryFn: getPatients,
  });

  const patients = data?.patients || [];

  const filteredPatients = patients.filter((patient: any) => {
    if (activeTab === 'all') return true;
    if (activeTab === 'called') return patient.call_count > 0;
    if (activeTab === 'never-called') return patient.call_count === 0;
    if (activeTab === 'discharged') return patient.patient_type === 'discharged';
    if (activeTab === 'opd') return patient.patient_type === 'opd';
    return true;
  });

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <h1 className="text-3xl font-bold text-gray-900">
            Hospital Voice Agent Dashboard
          </h1>
          <p className="mt-2 text-sm text-gray-600">
            AI-powered patient follow-up system
          </p>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Tabs */}
        <div className="mb-6">
          <div className="border-b border-gray-200">
            <nav className="-mb-px flex space-x-8 overflow-x-auto">
              {/* All Patients */}
              <button
                onClick={() => setActiveTab('all')}
                className={`${
                  activeTab === 'all'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm`}
              >
                All Patients ({patients.length})
              </button>
              <button
                onClick={() => setActiveTab('opd')}
                className={`${
                  activeTab === 'opd'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm`}
              >
                OPD Patients
              </button>

              {/* Discharged Patients */}
              <button
                onClick={() => setActiveTab('discharged')}
                className={`${
                  activeTab === 'discharged'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm`}
              >
                Discharged Patients
              </button>
              {/* Called */}
              <button
                onClick={() => setActiveTab('called')}
                className={`${
                  activeTab === 'called'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm`}
              >
                Called Patients
              </button>

              {/* Never Called */}
              <button
                onClick={() => setActiveTab('never-called')}
                className={`${
                  activeTab === 'never-called'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm`}
              >
                Never Called
              </button>

              {/* OPD Patients */}

            </nav>
          </div>
        </div>

        {/* Patient Table */}
        <div className="bg-white shadow rounded-lg">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
              <span className="ml-3 text-gray-600">Loading patients...</span>
            </div>
          ) : error ? (
            <div className="text-center py-12">
              <p className="text-red-600">Error loading patients</p>
              <button
                onClick={() => refetch()}
                className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
              >
                Retry
              </button>
            </div>
          ) : (
            <PatientTable patients={filteredPatients} onRefresh={() => refetch()} />
          )}
        </div>
      </main>
    </div>
  );
}
