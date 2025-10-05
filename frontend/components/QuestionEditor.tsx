// components/patients/QuestionsEditor.tsx
'use client';

import { useState } from 'react';
import { X, Plus } from 'lucide-react';
import { toast } from 'sonner';

interface QuestionsEditorProps {
  patientId: number;
  patientName: string;
  currentQuestions: string[];
  onSave: (questions: string[]) => Promise<void>;
  onClose: () => void;
}

export default function QuestionsEditor({
  patientId,
  patientName,
  currentQuestions,
  onSave,
  onClose,
}: QuestionsEditorProps) {
  const [questions, setQuestions] = useState<string[]>(
    currentQuestions.length > 0 ? currentQuestions : ['']
  );
  const [isSaving, setIsSaving] = useState(false);

  const addQuestion = () => {
    if (questions.length < 10) {
      setQuestions([...questions, '']);
    }
  };

  const removeQuestion = (index: number) => {
    if (questions.length > 1) {
      setQuestions(questions.filter((_, i) => i !== index));
    }
  };

  const updateQuestion = (index: number, value: string) => {
    const updated = [...questions];
    updated[index] = value;
    setQuestions(updated);
  };

  const handleSave = async () => {
    const validQuestions = questions.filter((q) => q.trim() !== '');

    if (validQuestions.length === 0) {
      toast.error('Please add at least one question');
      return;
    }

    setIsSaving(true);
    try {
      await onSave(validQuestions);
      toast.success('Questions saved successfully');
      onClose();
    } catch (error) {
      toast.error('Failed to save questions');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-40 flex items-center justify-center z-50"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-xl shadow-2xl p-6 max-w-2xl w-full max-h-[85vh] overflow-y-auto transition-all"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-xl font-bold text-gray-900">
            Custom Questions for {patientName}
          </h3>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-gray-600 rounded-full hover:bg-gray-100 transition"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Instructions */}
        <p className="text-sm text-gray-600 mb-4">
          These questions will be asked during the AI call in order. Keep them
          short and clear.
        </p>

        {/* Questions list */}
        <div className="space-y-3 mb-4">
          {questions.map((question, index) => (
            <div
              key={index}
              className="flex items-start space-x-3 bg-gray-50 p-3 rounded-lg"
            >
              <span className="text-sm font-semibold text-gray-800 mt-2 min-w-[20px]">
                {index + 1}.
              </span>
              <textarea
                value={question}
                onChange={(e) => updateQuestion(index, e.target.value)}
                placeholder="Enter question..."
                className="flex-1 p-2 border border-gray-300 rounded-md resize-none
                           focus:ring-2 focus:ring-blue-500 focus:border-transparent
                           text-gray-900 bg-white"
                rows={2}
              />
              {questions.length > 1 && (
                <button
                  onClick={() => removeQuestion(index)}
                  className="p-2 text-white bg-red-500 hover:bg-red-600 rounded-md transition"
                >
                  <X className="h-4 w-4" />
                </button>
              )}
            </div>
          ))}
        </div>

        {/* Add question */}
        <button
          onClick={addQuestion}
          disabled={questions.length >= 10}
          className="flex items-center px-3 py-2 border border-blue-500 text-blue-600
                     rounded-md text-sm font-medium hover:bg-blue-50
                     disabled:border-gray-300 disabled:text-gray-400 disabled:cursor-not-allowed transition"
        >
          <Plus className="h-4 w-4 mr-1" />
          Add Question (max 10)
        </button>

        {/* Footer buttons */}
        <div className="flex justify-end space-x-3 mt-6 pt-4 border-t border-gray-200">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-700 border border-gray-300 rounded-md
                       hover:bg-gray-100 transition"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={isSaving}
            className="px-4 py-2 bg-blue-600 text-white rounded-md
                       hover:bg-blue-700 disabled:opacity-50 transition"
          >
            {isSaving ? 'Saving...' : 'Save Questions'}
          </button>
        </div>
      </div>
    </div>
  );
}
