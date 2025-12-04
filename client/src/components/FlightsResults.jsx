const currencyFormatter = new Intl.NumberFormat('pt-BR', {
  style: 'currency',
  currency: 'BRL',
})

const milesFormatter = new Intl.NumberFormat('pt-BR')

function formatCash(value) {
  if (typeof value !== 'number' || Number.isNaN(value)) return '—'
  return currencyFormatter.format(value)
}

function formatMiles(value) {
  if (typeof value !== 'number' || Number.isNaN(value)) return '—'
  return `${milesFormatter.format(Math.round(value))} milhas`
}

function buildCards(data) {
  if (!data) return []

  const smiles = data.realtime?.smiles ?? null
  const azulMiles = data.realtime?.azul_miles ?? null
  const azulCash = data.realtime?.azul_cash ?? null
  const history = data.history ?? null

  return [
    {
      id: 'smiles',
      title: 'Smiles',
      miles: smiles?.total?.miles ?? null,
      money: smiles?.total?.money ?? null,
      outboundMiles: smiles?.outbound?.miles ?? null,
      inboundMiles: smiles?.inbound?.miles ?? null,
      outboundCash: smiles?.outbound?.money ?? null,
      inboundCash: smiles?.inbound?.money ?? null,
    },
    {
      id: 'azul',
      title: 'Azul',
      miles: azulMiles?.total?.miles ?? null,
      money: azulCash?.total?.money ?? null,
      outboundMiles: azulMiles?.outbound?.miles ?? null,
      inboundMiles: azulMiles?.inbound?.miles ?? null,
      outboundCash: azulCash?.outbound?.money ?? null,
      inboundCash: azulCash?.inbound?.money ?? null,
    },
    {
      id: 'history',
      title: 'Histórico',
      miles: history?.best_miles?.total?.miles ?? history?.best_money?.total?.miles ?? null,
      money: history?.best_money?.total?.money ?? null,
      outboundMiles: history?.best_miles?.outbound?.miles ?? null,
      inboundMiles: history?.best_miles?.inbound?.miles ?? null,
      outboundCash: history?.best_money?.outbound?.money ?? null,
      inboundCash: history?.best_money?.inbound?.money ?? null,
      departure: history?.best_miles?.departure ?? history?.best_money?.departure ?? null,
      returnDate: history?.best_miles?.return ?? history?.best_money?.return ?? null,
    },
  ]
}

export default function FlightsResults({ data, loading, error, onClear }) {
  if (error) {
    return (
      <section style={styles.section}>
        <div style={styles.errorCard}>
          <strong style={{ color: '#f87171' }}>Erro</strong>
          <span style={{ color: '#fca5a5' }}>{error}</span>
          <button type="button" style={styles.outlineButton} onClick={onClear}>
            Nova busca
          </button>
        </div>
      </section>
    )
  }

  if (!data && !loading) {
    return (
      <section style={styles.section}>
        <div style={styles.placeholder}>
          Realize uma busca para comparar ofertas de milhas, dinheiro e histórico.
        </div>
      </section>
    )
  }

  const criteria = data?.criteria ?? null
  const cards = buildCards(data)

  return (
    <section style={styles.section}>
      <header style={styles.header}>
        <div>
          <div style={{ color: '#94a3b8', fontSize: 12 }}>Rota analisada</div>
          {criteria ? (
            <strong style={{ color: '#e2e8f0' }}>
              {criteria.origin} → {criteria.destination} · {criteria.departure_date} → {criteria.return_date}
            </strong>
          ) : (
            <strong style={{ color: '#e2e8f0' }}>Buscando…</strong>
          )}
        </div>
        {criteria && (
          <div style={{ color: '#64748b', fontSize: 12 }}>
            Passageiros: {criteria.adults}
          </div>
        )}
      </header>

      {loading && (
        <div style={styles.loadingCard}>
          <div className="spinner" />
          <span style={{ color: '#94a3b8' }}>Consultando provedores…</span>
        </div>
      )}

      {!loading && cards.length === 0 && (
        <div style={styles.placeholder}>
          Nenhum resultado disponível para os critérios informados.
        </div>
      )}

      <div style={styles.cardsGrid}>
        {cards.map((card) => (
          <article key={card.id} style={styles.card}>
            <header style={styles.cardHeader}>
              <strong style={{ color: '#e2e8f0', fontSize: '1.1rem' }}>{card.title}</strong>
            </header>

            <div style={styles.valuesRow}>
              <div>
                <div style={styles.valueLabel}>Total em milhas</div>
                <div style={styles.mainValue}>{formatMiles(card.miles)}</div>
              </div>
              <div>
                <div style={styles.valueLabel}>Total em reais</div>
                <div style={styles.secondaryValue}>{formatCash(card.money)}</div>
              </div>
            </div>

            {(card.outboundMiles !== null || card.outboundCash !== null) && (
              <div style={styles.detailRow}>
                <span style={styles.detailLabel}>Ida</span>
                <span>{formatMiles(card.outboundMiles)}</span>
                <span>{formatCash(card.outboundCash)}</span>
              </div>
            )}

            {(card.inboundMiles !== null || card.inboundCash !== null) && (
              <div style={styles.detailRow}>
                <span style={styles.detailLabel}>Volta</span>
                <span>{formatMiles(card.inboundMiles)}</span>
                <span>{formatCash(card.inboundCash)}</span>
              </div>
            )}

            {card.departure && card.returnDate && (
              <div style={{ color: '#64748b', fontSize: 12 }}>
                Vigência: {card.departure} → {card.returnDate}
              </div>
            )}
          </article>
        ))}
      </div>

      {data && (
        <button type="button" style={styles.outlineButton} onClick={onClear}>
          Limpar resultados
        </button>
      )}
    </section>
  )
}

const styles = {
  section: {
    display: 'grid',
    gap: '1rem',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: '0.5rem',
    background: '#0b1220',
    border: '1px solid #1f2937',
    borderRadius: 12,
    padding: '1rem 1.25rem',
  },
  cardsGrid: {
    display: 'grid',
    gap: '1rem',
    gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
  },
  card: {
    background: '#0b1220',
    border: '1px solid #1f2937',
    borderRadius: 12,
    padding: '1rem 1.25rem',
    display: 'grid',
    gap: '0.75rem',
  },
  cardHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  valuesRow: {
    display: 'grid',
    gap: '0.75rem',
    gridTemplateColumns: 'repeat(2, minmax(0, 1fr))',
  },
  valueLabel: {
    color: '#94a3b8',
    fontSize: 12,
    marginBottom: 4,
  },
  mainValue: {
    color: '#22d3ee',
    fontSize: '1.4rem',
    fontWeight: 600,
  },
  secondaryValue: {
    color: '#e2e8f0',
    fontSize: '1.1rem',
    fontWeight: 500,
  },
  detailRow: {
    display: 'grid',
    gridTemplateColumns: '60px 1fr 1fr',
    gap: '0.5rem',
    color: '#cbd5f5',
    fontSize: 13,
  },
  detailLabel: {
    color: '#94a3b8',
  },
  loadingCard: {
    display: 'grid',
    gap: '0.75rem',
    justifyItems: 'center',
    padding: '2rem',
    background: '#0b1220',
    border: '1px solid #1f2937',
    borderRadius: 12,
  },
  placeholder: {
    background: '#0b1220',
    border: '1px solid #1f2937',
    borderRadius: 12,
    padding: '1.5rem',
    color: '#94a3b8',
    textAlign: 'center',
  },
  errorCard: {
    background: '#200b0b',
    border: '1px solid #7f1d1d',
    borderRadius: 12,
    padding: '1.5rem',
    display: 'grid',
    gap: '0.75rem',
    justifyItems: 'start',
  },
  outlineButton: {
    border: '1px solid #38bdf8',
    color: '#38bdf8',
    background: 'transparent',
    borderRadius: 10,
    padding: '0.6rem 1rem',
    cursor: 'pointer',
  },
}
