'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { getCallTranscript } from '@/lib/api';
import CostBreakdown from '@/components/CostBreakdown';
import CallSummaryCard from '@/components/CallSummaryCard';

interface Message {
  role: string;
  content: string;
}

interface CallData {
  call_id: number;
  transcript: {
    conversation: Message[];
    call_ended_at: string;
  };
  summary: any;
  costs: {
    stt: number;
    llm: number;
    tts: number;
  };
  created_at: string;
}

export default function CallDetailsPage() {
  const params = useParams();
  const callId = params.id as string;
  const [callData, setCallData] = useState<CallData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadCallDetails();
  }, [callId]);

  const loadCallDetails = async () => {
    try {
      const data = await getCallTranscript(Number(callId));
      setCallData(data);
    } catch (error) {
      console.error('Error loading call:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen p-8 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading call details...</p>
        </div>
      </div>
    );
  }

  if (!callData) {
    return (
      <div className="min-h-screen p-8">
        <div className="max-w-7xl mx-auto">
          <p className="text-red-600">Call not found</p>
        </div>
      </div>
    );
  }

  const duration = callData.transcript.conversation.length * 15; // Approximate

  return (
    <div className="min-h-screen p-8 bg-gray-50">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <button
            onClick={() => window.history.back()}
            className="text-blue-600 hover:text-blue-800 mb-4"
          >
            ← Back
          </button>
          <h1 className="text-3xl font-bold">Call Details</h1>
          <p className="text-gray-600">Call ID: {callData.call_id}</p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Transcript - Left Column (2/3 width) */}
          <div className="lg:col-span-2">
            <div className="bg-white p-6 rounded-lg shadow">
              <h2 className="text-xl font-semibold mb-4">Conversation Transcript</h2>

              <div className="space-y-4">
                {callData.transcript.conversation.map((message, index) => (
                  <div
                    key={index}
                    className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-[80%] p-4 rounded-lg ${
                        message.role === 'user'
                          ? 'bg-blue-100 text-blue-900'
                          : 'bg-gray-100 text-gray-900'
                      }`}
                    >
                      <p className="text-xs font-semibold mb-1 uppercase">
                        {message.role === 'user' ? 'Patient' : 'AI Assistant'}
                      </p>
                      <p className="text-sm">{message.content}</p>
                    </div>
                  </div>
                ))}
              </div>

              {callData.transcript.conversation.length === 0 && (
                <p className="text-gray-500 text-center py-8">No conversation recorded</p>
              )}
            </div>
          </div>

          {/* Right Column - Summary & Costs */}
          <div className="space-y-6">
            {/* Call Summary */}
            {callData.summary && (
              <CallSummaryCard summary={callData.summary} />
            )}

            {/* Cost Breakdown */}
            <CostBreakdown costs={callData.costs} duration={duration} />

            {/* Call Info */}
            <div className="bg-white p-6 rounded-lg shadow">
              <h3 className="text-lg font-semibold mb-4">Call Information</h3>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600">Date:</span>
                  <span className="font-medium">
                    {new Date(callData.created_at).toLocaleDateString()}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Time:</span>
                  <span className="font-medium">
                    {new Date(callData.created_at).toLocaleTimeString()}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Status:</span>
                  <span className="px-2 py-1 bg-green-100 text-green-800 text-xs rounded">
                    Completed
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
