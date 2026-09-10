import { useEffect, useState } from 'react'
import './App.css'
import AudioRecorder from './components/recorder'
import { fetchSongs } from './components/fetchSong'

function App() {
  const [status, setStatus] = useState('idle')
  const [results, setResults] = useState([])
  const [error, setError] = useState('')
  const [catalog, setCatalog] = useState({ total: 0, songs: [] })
  const [catalogOpen, setCatalogOpen] = useState(false)

  useEffect(() => {
    fetchSongs()
      .then(setCatalog)
      .catch(() => {})
  }, [])

  const handleResult = (response) => {
    const nextResults = Array.isArray(response) ? response : []
    setResults(nextResults)
    setStatus(nextResults.length ? 'found' : 'not-found')
  }

  const handleRecordingChange = (nextStatus) => {
    setStatus(nextStatus)
    if (nextStatus === 'recording') {
      setResults([])
      setError('')
    }
  }

  const handleError = (message) => {
    setError(message)
    setStatus('error')
  }

  const startNewSearch = () => {
    setResults([])
    setError('')
    setStatus('idle')
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="WaveTrace home">
          <span className="brand-mark" aria-hidden="true"><i /><i /><i /><i /></span>
          <span>WaveTrace</span>
        </a>
        <button className="catalog-button" onClick={() => setCatalogOpen((open) => !open)} aria-expanded={catalogOpen}>
          <span>{catalog.total}</span> songs
        </button>
      </header>

      {catalogOpen && <SongCatalog catalog={catalog} />}

      <section className="hero" aria-labelledby="page-title">
        <p className="eyebrow">Identify a sound</p>
        <h1 id="page-title">What’s that song?</h1>
        <p className="intro">Let WaveTrace listen for a moment and find the music around you.</p>

        <AudioRecorder onResult={handleResult} onStatusChange={handleRecordingChange} onError={handleError} />
        <p className="privacy-note"><span aria-hidden="true">⌁</span> Your recording is used only to identify the song</p>
      </section>

      {status === 'found' && <Results results={results} onSearchAgain={startNewSearch} />}
      {status === 'not-found' && <MessagePanel title="No match this time" message="Try moving closer to the sound or recording a clearer section." onRetry={startNewSearch} />}
      {status === 'error' && <MessagePanel title="Something went wrong" message={error} onRetry={startNewSearch} isError />}

      <footer className="footer">12 seconds of listening is all it takes.</footer>
    </main>
  )
}

function SongCatalog({ catalog }) {
  return (
    <aside className="catalog-panel" aria-label="Available songs">
      <div className="catalog-header">
        <div><p className="eyebrow">Fingerprint library</p><h2>Available songs</h2></div>
        <span className="catalog-count">{catalog.total}</span>
      </div>
      {catalog.songs.length > 0 ? <ol className="catalog-list">{catalog.songs.map((song) => <li key={song.song_id}><span>{String(song.song_id).padStart(2, '0')}</span><strong>{song.song_name}</strong></li>)}</ol> : <p className="catalog-empty">The song library is unavailable.</p>}
    </aside>
  )
}

function Results({ results, onSearchAgain }) {
  const [topResult, ...otherResults] = results

  return (
    <section className="results" aria-live="polite">
      <div className="results-heading">
        <div><p className="eyebrow">Best match</p><h2>We found something</h2></div>
        <button className="icon-button" onClick={onSearchAgain} aria-label="Search for another song" title="Search again">↗</button>
      </div>
      <article className="top-result">
        <div className="album-art" aria-hidden="true"><span>WT</span></div>
        <div className="song-details"><h3>{topResult.song_name || 'Unknown song'}</h3><p>{topResult.song_id ? `Track ${topResult.song_id}` : 'Recognized track'}</p></div>
        <div className="match-score"><strong>{((topResult.final_score || 0) * 100).toFixed(1)}%</strong><span>match</span></div>
      </article>
      {otherResults.length > 0 && <div className="other-results"><p className="list-label">Other possibilities</p>{otherResults.map((result, index) => <div className="result-row" key={`${result.song_id}-${index}`}><span className="row-number">0{index + 2}</span><span className="row-name">{result.song_name || 'Unknown song'}</span><span className="row-score">{((result.final_score || 0) * 100).toFixed(1)}%</span></div>)}</div>}
    </section>
  )
}

function MessagePanel({ title, message, onRetry, isError = false }) {
  return <section className={`message-panel ${isError ? 'error-panel' : ''}`} aria-live="assertive"><span className="message-icon" aria-hidden="true">{isError ? '!' : '⌁'}</span><h2>{title}</h2><p>{message}</p><button className="secondary-button" onClick={onRetry}>Try again</button></section>
}

export default App
