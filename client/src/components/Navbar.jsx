export default function Navbar({ links = [], active, onChange }) {
  const styles = {
    nav: {
      position: 'sticky',
      top: 0,
      background: '#0f172a',
      color: '#ffffff',
      borderBottom: '1px solid #1f2937',
      zIndex: 50
    },
    container: {
      maxWidth: 1200,
      margin: '0 auto',
      padding: '0.75rem 1rem',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      gap: '1rem'
    },
    brand: {
      fontWeight: 700,
      letterSpacing: '0.3px'
    },
    menu: {
      display: 'flex',
      gap: '0.5rem',
      alignItems: 'center'
    },
    link: isActive => ({
      padding: '0.5rem 0.75rem',
      borderRadius: 8,
      textDecoration: 'none',
      color: isActive ? '#0ea5e9' : '#e5e7eb',
      background: isActive ? 'rgba(14,165,233,0.12)' : 'transparent',
      transition: 'background 120ms, color 120ms'
    })
  }

  return (
    <nav style={styles.nav} aria-label="Navegação principal">
      <div style={styles.container}>
        <div style={styles.brand}>Portal Unificado</div>
        <div style={styles.menu}>
          {links.map(link => (
            <a
              key={link.key}
              href={link.href || '#'}
              onClick={e => {
                e.preventDefault()
                onChange && onChange(link.key)
              }}
              style={styles.link(active === link.key)}
              aria-current={active === link.key ? 'page' : undefined}
            >
              {link.label}
            </a>
          ))}
        </div>
      </div>
    </nav>
  )
}


