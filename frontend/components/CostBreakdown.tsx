interface CostBreakdownProps {
  costs: {
    stt: number;
    llm: number;
    tts: number;
  };
  duration: number;
}

const TELEPHONY_COST_PER_MIN = 0.007;

export default function CostBreakdown({ costs, duration }: CostBreakdownProps) {
  const telephonyCost = (duration / 60) * TELEPHONY_COST_PER_MIN;
  const total = costs.stt + costs.llm + costs.tts + telephonyCost;

  const services = [
    {
      name: 'Speech-to-Text',
      provider: 'Deepgram',
      cost: costs.stt,
      color: 'bg-blue-500'
    },
    {
      name: 'AI Model',
      provider: 'OpenAI GPT-4o-mini',
      cost: costs.llm,
      color: 'bg-green-500'
    },
    {
      name: 'Text-to-Speech',
      provider: 'ElevenLabs Turbo v2.5',
      cost: costs.tts,
      color: 'bg-purple-500'
    },
    {
      name: 'Telephony',
      provider: 'Plivo',
      cost: telephonyCost,
      color: 'bg-orange-500'
    },
  ];

  return (
    <div className="bg-white p-6 rounded-lg shadow">
      <h3 className="text-lg font-semibold mb-4">Cost Analysis</h3>

      <div className="space-y-3 mb-4">
        {services.map((service) => (
          <div key={service.name} className="flex justify-between items-center">
            <div>
              <p className="font-medium text-sm">{service.name}</p>
              <p className="text-xs text-gray-500">{service.provider}</p>
            </div>
            <div className="text-right">
              <p className="font-semibold">${service.cost.toFixed(4)}</p>
              <div className="w-20 h-1 mt-1 rounded-full bg-gray-200">
                <div
                  className={`h-full rounded-full ${service.color}`}
                  style={{ width: `${(service.cost / total) * 100}%` }}
                />
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="pt-4 border-t border-gray-200">
        <div className="flex justify-between items-center">
          <p className="font-bold">Total Cost</p>
          <p className="font-bold text-xl">${total.toFixed(4)}</p>
        </div>
        <p className="text-xs text-gray-500 mt-1">
          Duration: {duration}s ({Math.floor(duration / 60)}m {duration % 60}s)
        </p>
      </div>
    </div>
  );
}
