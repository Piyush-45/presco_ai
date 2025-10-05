'use client';

import { useState } from 'react';

import { toast } from 'sonner';
import QuestionsEditor from '../QuestionEditor';

interface Patient {
  id: number;
  name: string;
  phone: string;
  age: number;
  language: string;
  custom_questions: string;
}

interface EditPatientModalProps {
  patient: Patient;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export default function EditPatientModal({ patient, isOpen, onClose, onSuccess }: EditPatientModalProps) {
  const [formData, setFormData] = useState({
    name: patient.name,
    phone: patient.phone,
    age: patient.age.toString(),
    language: patient.language,
    patient_type: 'opd',
  });

  const parseQuestions = (questionsStr: string): string[] => {
    if (!questionsStr) return [''];
    return questionsStr
      .split('\n')
      .map(q => q.replace(/^\d+\.\s*/, '').trim())
      .filter(q => q);
  };

  const [questions, setQuestions] = useState<string[]>(
    parseQuestions(patient.custom_questions)
  );
  const [showQuestionEditor, setShowQuestionEditor] = useState(false);
  const [loading, setLoading] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    const validQuestions = questions.filter(q => q.trim() !== '');
    const custom_questions = validQuestions.length > 0
      ? validQuestions.map((q, i) => `${i + 1}. ${q}`).join('\n')
      : '';

    try {
      const response = await fetch(`http://localhost:8000/api/calls/patients/${patient.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: formData.name,
          phone: formData.phone,
          age: parseInt(formData.age),
          language: formData.language,
          custom_questions
        })
      });

      if (response.ok) {
        toast.success('Patient updated successfully!');
        onSuccess();
        onClose();
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to update patient');
      }
    } catch (error) {
      toast.error('Error updating patient');
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg p-8 max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-2xl font-bold">Edit Patient</h2>
            <button
              onClick={onClose}
              className="text-gray-500 hover:text-gray-700 text-2xl"
            >
              ×
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Patient Name *
              </label>
              <input
                type="text"
                required
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Phone Number *
              </label>
              <input
                type="tel"
                required
                value={formData.phone}
                onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
  <label className="block text-sm font-medium text-gray-700 mb-1">
    Patient Type *
  </label>
  <select
    value={formData.patient_type}
    onChange={(e) => setFormData({ ...formData, patient_type: e.target.value })}
    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
  >
    <option value="opd">OPD</option>
    <option value="discharged">Discharged</option>
  </select>
</div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Age *
              </label>
              <input
                type="number"
                required
                min="1"
                max="120"
                value={formData.age}
                onChange={(e) => setFormData({ ...formData, age: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Preferred Language *
              </label>
              <select
                value={formData.language}
                onChange={(e) => setFormData({ ...formData, language: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="English">English</option>
                <option value="Hindi">Hindi</option>
                <option value="Spanish">Spanish</option>
                <option value="Marathi">Marathi</option>
                <option value="Tamil">Tamil</option>
                <option value="Telugu">Telugu</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Custom Questions
              </label>
              <button
                type="button"
                onClick={() => setShowQuestionEditor(true)}
                className="w-full px-4 py-2 border-2 border-dashed border-gray-300 rounded-lg text-gray-600 hover:border-blue-500 hover:text-blue-600 transition"
              >
                {questions.filter(q => q.trim()).length > 0
                  ? `${questions.filter(q => q.trim()).length} questions configured`
                  : 'Click to add custom questions'}
              </button>
            </div>

            <div className="flex gap-3 pt-4">
              <button
                type="button"
                onClick={onClose}
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={loading}
                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400"
              >
                {loading ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          </form>
        </div>
      </div>

      {showQuestionEditor && (
        <QuestionsEditor
          patientId={patient.id}
          patientName={formData.name}
          currentQuestions={questions}
          onSave={async (newQuestions) => {
            setQuestions(newQuestions);
            setShowQuestionEditor(false);
          }}
          onClose={() => setShowQuestionEditor(false)}
        />
      )}
    </>
  );
}
