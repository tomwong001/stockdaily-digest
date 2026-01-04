interface Company {
  id: string
  ticker: string
  name: string
  industry?: string
}

interface CompanyCardProps {
  company: Company
  onRemove: (id: string) => void
}

export default function CompanyCard({ company, onRemove }: CompanyCardProps) {
  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 flex items-center justify-between hover:shadow-md transition-shadow">
      <div className="flex items-center gap-4">
        <div className="w-12 h-12 bg-primary-100 rounded-lg flex items-center justify-center">
          <span className="text-primary-700 font-bold text-sm">{company.ticker}</span>
        </div>
        <div>
          <h3 className="font-semibold text-gray-900">{company.name}</h3>
          <div className="flex items-center gap-2">
            <span className="text-sm text-primary-600 font-medium">{company.ticker}</span>
            {company.industry && (
              <>
                <span className="text-gray-300">•</span>
                <span className="text-sm text-gray-500">{company.industry}</span>
              </>
            )}
          </div>
        </div>
      </div>
      <button
        onClick={() => onRemove(company.id)}
        className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
        title="删除"
      >
        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
          <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
        </svg>
      </button>
    </div>
  )
}
