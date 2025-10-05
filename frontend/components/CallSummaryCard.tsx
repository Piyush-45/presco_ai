interface Summary {
  sentiment: string;
  key_points: string[];
  health_concerns: string[];
  follow_up_needed: boolean;
  follow_up_reason?: string;
}

interface CallSummaryCardProps {
  summary: Summary;
}

export default function CallSummaryCard({ summary }: CallSummaryCardProps) {
  const getSentimentColor = (sentiment: string) => {
    switch (sentiment.toLowerCase()) {
      case 'positive': return 'bg-green-100 text-green-800';
      case 'negative': return 'bg-red-100 text-red-800';
      case 'concerned': return 'bg-orange-100 text-orange-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="bg-white p-6 rounded-lg shadow">
      <h3 className="text-lg font-semibold mb-4">Call Summary</h3>

      <div className="mb-4">
        <p className="text-sm text-gray-600 mb-2">Sentiment</p>
        <span className={`px-3 py-1 rounded-full text-sm font-medium ${getSentimentColor(summary.sentiment)}`}>
          {summary.sentiment}
        </span>
      </div>

      {summary.key_points && summary.key_points.length > 0 && (
        <div className="mb-4">
          <p className="text-sm font-medium text-gray-700 mb-2">Key Points</p>
          <ul className="list-disc list-inside space-y-1">
            {summary.key_points.map((point, i) => (
              <li key={i} className="text-sm text-gray-600">{point}</li>
            ))}
          </ul>
        </div>
      )}

      {summary.health_concerns && summary.health_concerns.length > 0 && (
        <div className="mb-4">
          <p className="text-sm font-medium text-gray-700 mb-2">Health Concerns</p>
          <ul className="list-disc list-inside space-y-1">
            {summary.health_concerns.map((concern, i) => (
              <li key={i} className="text-sm text-red-600">{concern}</li>
            ))}
          </ul>
        </div>
      )}

      <div className={`p-3 rounded ${summary.follow_up_needed ? 'bg-yellow-50 border border-yellow-200' : 'bg-green-50 border border-green-200'}`}>
        <p className="text-sm font-medium mb-1">
          Follow-up: {summary.follow_up_needed ? 'Required' : 'Not needed'}
        </p>
        {summary.follow_up_reason && (
          <p className="text-sm text-gray-600">{summary.follow_up_reason}</p>
        )}
      </div>
    </div>
  );
}
