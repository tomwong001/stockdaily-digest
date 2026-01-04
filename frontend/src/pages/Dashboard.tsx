import { useState, useEffect } from 'react'
import api from '../api'
import CompanyCard from '../components/CompanyCard'

interface Company {
  id: string
  ticker: string
  name: string
  industry?: string
}

interface SearchResult {
  ticker: string
  name: string
  industry?: string
}

export default function Dashboard() {
  const [companies, setCompanies] = useState<Company[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<SearchResult[]>([])
  const [searching, setSearching] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  // 获取用户关注的公司列表
  useEffect(() => {
    fetchCompanies()
  }, [])

  const fetchCompanies = async () => {
    try {
      setLoading(true)
      setError('')
      const response = await api.get('/api/user/companies')
      setCompanies(response.data)
    } catch (err: unknown) {
      console.error('获取公司列表失败:', err)
      const error = err as { response?: { status?: number; data?: { detail?: string } } }
      if (error.response?.status === 401) {
        // 401 会被拦截器处理，这里不需要额外操作
        setError('请先登录')
      } else {
        setError(error.response?.data?.detail || '获取公司列表失败，请稍后重试')
      }
    } finally {
      setLoading(false)
    }
  }

  // 搜索公司
  const handleSearch = async () => {
    if (!searchQuery.trim()) return

    setSearching(true)
    setError('')

    try {
      const response = await api.get(`/api/companies/search?q=${encodeURIComponent(searchQuery)}`)
      setSearchResults(response.data)
    } catch (err) {
      console.error('搜索失败:', err)
      setError('搜索失败，请稍后重试')
    } finally {
      setSearching(false)
    }
  }

  // 添加公司到关注列表
  const handleAddCompany = async (company: SearchResult) => {
    try {
      const response = await api.post('/api/user/companies', {
        ticker: company.ticker,
        name: company.name,
        industry: company.industry,
      })
      setCompanies([...companies, response.data])
      setSearchResults([])
      setSearchQuery('')
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } }
      setError(error.response?.data?.detail || '添加失败')
    }
  }

  // 从关注列表中移除公司
  const handleRemoveCompany = async (companyId: string) => {
    try {
      await api.delete(`/api/user/companies/${companyId}`)
      setCompanies(companies.filter((c) => c.id !== companyId))
    } catch (err) {
      console.error('删除失败:', err)
      setError('删除失败，请稍后重试')
    }
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      {/* 页面标题 */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">我的关注列表</h1>
        <p className="text-gray-600 mt-1">添加您想要关注的美股公司，我们会每天为您发送相关新闻日报</p>
      </div>

      {/* 搜索添加公司 */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-8">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">添加公司</h2>
        <div className="flex gap-3">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="输入股票代码或公司名称，如 AAPL, Tesla"
            className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all outline-none"
          />
          <button
            onClick={handleSearch}
            disabled={searching || !searchQuery.trim()}
            className="px-6 py-3 bg-primary-600 hover:bg-primary-700 text-white font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {searching ? '搜索中...' : '搜索'}
          </button>
        </div>

        {/* 搜索结果 */}
        {searchResults.length > 0 && (
          <div className="mt-4 border border-gray-200 rounded-lg divide-y divide-gray-200">
            {searchResults.map((result) => (
              <div
                key={result.ticker}
                className="flex items-center justify-between p-4 hover:bg-gray-50"
              >
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-primary-600">{result.ticker}</span>
                    <span className="text-gray-900">{result.name}</span>
                  </div>
                  {result.industry && (
                    <span className="text-sm text-gray-500">{result.industry}</span>
                  )}
                </div>
                <button
                  onClick={() => handleAddCompany(result)}
                  disabled={companies.some((c) => c.ticker === result.ticker)}
                  className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {companies.some((c) => c.ticker === result.ticker) ? '已添加' : '添加'}
                </button>
              </div>
            ))}
          </div>
        )}

        {error && (
          <div className="mt-4 bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded-lg text-sm">
            {error}
          </div>
        )}
      </div>

      {/* 关注公司列表 */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">已关注的公司</h2>
          <span className="text-sm text-gray-500">{companies.length} 家公司</span>
        </div>

        {error && (
          <div className="mb-4 bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded-lg text-sm">
            {error}
          </div>
        )}

        {loading ? (
          <div className="text-center py-12 text-gray-500">加载中...</div>
        ) : companies.length === 0 ? (
          <div className="text-center py-12">
            <div className="text-gray-400 text-5xl mb-4">📭</div>
            <p className="text-gray-500">还没有关注任何公司</p>
            <p className="text-gray-400 text-sm mt-1">使用上方搜索框添加您感兴趣的美股公司</p>
          </div>
        ) : (
          <div className="space-y-3">
            {companies.map((company) => (
              <CompanyCard
                key={company.id}
                company={company}
                onRemove={handleRemoveCompany}
              />
            ))}
          </div>
        )}
      </div>

      {/* 示例日报预览 */}
      <div className="mt-8 bg-gradient-to-r from-primary-50 to-blue-50 rounded-xl border border-primary-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-3">📧 日报示例</h2>
        <p className="text-gray-600 text-sm mb-4">
          每天早上 8:00 (美东时间)，我们会将您关注公司的新闻摘要发送到您的邮箱：
        </p>
        <div className="bg-white rounded-lg shadow-sm p-4 border border-gray-200">
          <div className="border-b border-gray-100 pb-3 mb-3">
            <div className="text-sm text-gray-500">From: StockDaily Digest</div>
            <div className="text-sm text-gray-500">Subject: 📈 您的每日美股新闻摘要 - 2026/01/03</div>
          </div>
          <div className="space-y-3 text-sm">
            <div className="font-semibold text-gray-900">🍎 Apple (AAPL)</div>
            <div className="text-gray-600 pl-4 border-l-2 border-primary-200">
              • Apple 发布新款 Vision Pro 2，预计下季度出货量将增长 40%<br />
              • 分析师上调 Apple 目标价至 $250，看好 AI 业务潜力
            </div>
            <div className="font-semibold text-gray-900 mt-4">🚗 Tesla (TSLA)</div>
            <div className="text-gray-600 pl-4 border-l-2 border-primary-200">
              • Tesla 2025 年全年交付量创新高，达到 210 万辆<br />
              • FSD 功能在中国获批，预计将推动软件收入增长
            </div>
            <div className="font-semibold text-gray-900 mt-4">📊 行业新闻</div>
            <div className="text-gray-600 pl-4 border-l-2 border-green-200">
              • 科技股整体走强，NASDAQ 指数创历史新高<br />
              • 美联储暗示 2026 年可能降息，利好成长股
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
