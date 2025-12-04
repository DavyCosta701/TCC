import { useState } from 'react'
import FlightsSearch from './components/FlightsSearch.jsx'
import FlightsResults from './components/FlightsResults.jsx'

function App() {
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleSearchStart = () => {
    setLoading(true)
    setError(null)
  }

  const handleSearchSuccess = (data) => {
    setResults(data)
    setLoading(false)
  }

  const handleSearchError = (err) => {
    const message = err instanceof Error ? err.message : 'Não foi possível concluir a busca.'
    setError(message)
    setLoading(false)
  }

  return (
    <>
      <header style={{ padding: '1.5rem 1rem 1rem', textAlign: 'center' }}>
        <h1 style={{ margin: 0, color: '#e5e7eb', fontSize: '1.75rem' }}>
          Comparador de voos — TCC
        </h1>
        <p style={{ marginTop: 8, color: '#94a3b8' }}>
          Consulte Azul, Smiles e o histórico para decidir entre milhas e dinheiro.
        </p>
      </header>

      <main style={{ maxWidth: 1180, margin: '0 auto', padding: '0 1rem 2rem', display: 'grid', gap: '1.5rem' }}>
        <FlightsSearch
          loading={loading}
          onSearchStart={handleSearchStart}
          onSearchSuccess={handleSearchSuccess}
          onSearchError={handleSearchError}
        />

        <FlightsResults
          data={results}
          loading={loading}
          error={error}
          onClear={() => setResults(null)}
        />
      </main>
    </>
  )
}

export default App
