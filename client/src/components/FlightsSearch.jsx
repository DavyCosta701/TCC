import { useMemo, useState } from 'react'
import { CITY_OPTIONS } from './cities.js'

const API_BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export default function FlightsSearch({ loading, onSearchStart, onSearchSuccess, onSearchError }) {
  const [origin, setOrigin] = useState('GRU')
  const [destination, setDestination] = useState('REC')
  const [departDate, setDepartDate] = useState(() => new Date().toISOString().slice(0, 10))
  const [returnDate, setReturnDate] = useState(() => new Date(Date.now() + 86400000 * 3).toISOString().slice(0, 10))
  const [adults, setAdults] = useState(1)

  const canSearch = useMemo(() => {
    if (!origin || !destination) return false
    if (!departDate || !returnDate) return false
    return returnDate >= departDate
  }, [origin, destination, departDate, returnDate])

  const swapDirections = () => {
    const currentOrigin = origin
    setOrigin(destination)
    setDestination(currentOrigin)
  }

  async function handleSubmit(event) {
    event?.preventDefault()
    if (!canSearch || loading) return

    onSearchStart?.()

    try {
      const params = new URLSearchParams({
        origin,
        destination,
        departure_date: departDate,
        return_date: returnDate,
        adults: String(adults),
      })

      const [searchResponse, historyResponse] = await Promise.all([
        fetch(`${API_BASE_URL}/search?${params.toString()}`),
        fetch(`${API_BASE_URL}/history?${new URLSearchParams({ origin, destination }).toString()}`),
      ])

      if (!searchResponse.ok) {
        const detail = await searchResponse.text()
        throw new Error(detail || 'Falha ao consultar a busca em tempo real.')
      }

      if (!historyResponse.ok) {
        const detail = await historyResponse.text()
        throw new Error(detail || 'Falha ao consultar o histórico.')
      }

      const realtimeData = await searchResponse.json()
      const historyData = await historyResponse.json()

      onSearchSuccess?.({
        criteria: {
          origin,
          destination,
          departure_date: departDate,
          return_date: returnDate,
          adults,
        },
        realtime: realtimeData,
        history: historyData,
      })
    } catch (err) {
      console.error(err)
      const error = err instanceof Error ? err : new Error('Erro inesperado durante a busca.')
      onSearchError?.(error)
    }
  }

  const styles = {
    card: {
      background: '#0b1220',
      border: '1px solid #1f2937',
      borderRadius: 12,
      padding: '1.25rem',
      display: 'grid',
      gap: '1rem',
    },
    label: { display: 'block', color: '#9ca3af', fontSize: 12, marginBottom: 6 },
    input: {
      width: '100%',
      padding: '0.7rem 0.75rem',
      borderRadius: 10,
      border: '1px solid #334155',
      background: '#0f172a',
      color: '#e5e7eb',
    },
    select: {
      width: '100%',
      padding: '0.7rem 0.75rem',
      borderRadius: 10,
      border: '1px solid #334155',
      background: '#0f172a',
      color: '#e5e7eb',
    },
    button: {
      padding: '0.75rem 1rem',
      borderRadius: 10,
      border: '1px solid #0ea5e9',
      background: '#0ea5e9',
      color: '#00131a',
      fontWeight: 600,
      cursor: loading || !canSearch ? 'not-allowed' : 'pointer',
      opacity: loading || !canSearch ? 0.6 : 1,
      transition: 'transform 120ms',
    },
    swap: {
      padding: '0.55rem 0.75rem',
      borderRadius: 10,
      border: '1px solid #334155',
      background: 'transparent',
      color: '#e5e7eb',
      cursor: 'pointer',
    },
  }

  return (
    <form onSubmit={handleSubmit} style={styles.card}>
      <div style={{ display: 'grid', gap: '0.75rem', gridTemplateColumns: '1fr auto 1fr', alignItems: 'end' }}>
        <div>
          <label style={styles.label}>Origem</label>
          <select
            style={styles.select}
            value={origin}
            onChange={(event) => setOrigin(event.target.value)}
          >
            {CITY_OPTIONS.map((city) => (
              <option key={city.code} value={city.code}>
                {city.name} ({city.code})
              </option>
            ))}
          </select>
        </div>

        <div style={{ display: 'flex', justifyContent: 'center' }}>
          <button type="button" onClick={swapDirections} style={styles.swap} title="Inverter origem/destino">
            ↔
          </button>
        </div>

        <div>
          <label style={styles.label}>Destino</label>
          <select
            style={styles.select}
            value={destination}
            onChange={(event) => setDestination(event.target.value)}
          >
            {CITY_OPTIONS.map((city) => (
              <option key={city.code} value={city.code}>
                {city.name} ({city.code})
              </option>
            ))}
          </select>
        </div>
      </div>

      <div style={{ display: 'grid', gap: '0.75rem', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))' }}>
        <div>
          <label style={styles.label}>Ida</label>
          <input
            style={styles.input}
            type="date"
            value={departDate}
            onChange={(event) => setDepartDate(event.target.value)}
          />
        </div>
        <div>
          <label style={styles.label}>Volta</label>
          <input
            style={styles.input}
            type="date"
            value={returnDate}
            min={departDate}
            onChange={(event) => setReturnDate(event.target.value)}
          />
        </div>
        <div>
          <label style={styles.label}>Adultos</label>
          <input
            style={styles.input}
            type="number"
            min={1}
            max={9}
            value={adults}
            onChange={(event) => setAdults(Number(event.target.value))}
          />
        </div>
      </div>

      <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', alignItems: 'center' }}>
        <button type="submit" style={styles.button} disabled={!canSearch || loading}>
          {loading ? 'Buscando ofertas…' : 'Buscar ofertas'}
        </button>
        <span style={{ color: '#64748b', fontSize: 12 }}>
          Consulta unificada: Azul, Smiles e histórico próprio.
        </span>
      </div>
    </form>
  )
}
