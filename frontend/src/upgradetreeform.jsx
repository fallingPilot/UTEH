import { useState, useEffect } from 'react'
import { createInstance, getDatabase } from './api'

function CreateUpgradeTreeForm() {
    const [name, setName] = useState('')
    const [status, setStatus] = useState('idle') // 'idle' | 'submitting' | 'error' | 'success'
    const [errorMessage, setErrorMessage] = useState('')
    const [createdTree, setCreatedTree] = useState(null)

    // State for storing database snapshot
    const [dbData, setDbData] = useState(null)
    const [isDbLoading, setIsDbLoading] = useState(false)

    // Helper to fetch/refresh DB snapshot from FastAPI
    async function fetchDatabase() {
        setIsDbLoading(true)
        try {
            const res = await getDatabase()
            // Backend returns {"status": "ok", "data": serialize_database(...)}
            setDbData(res.data)
        } catch (err) {
            console.error('Failed to load database snapshot:', err)
        } finally {
            setIsDbLoading(false)
        }
    }

    // Load database state on initial render
    useEffect(() => {
        fetchDatabase()
    }, [])

    async function handleSubmit(event) {
        event.preventDefault()

        const trimmedName = name.trim()
        if (!trimmedName) {
            setStatus('error')
            setErrorMessage('Give the tree a name first.')
            return
        }

        setStatus('submitting')
        setErrorMessage('')

        try {
            const result = await createInstance('NodeTree', { name: trimmedName })
            setCreatedTree({ id: result.id, name: trimmedName })
            setStatus('success')
            setName('')

            // Refresh the displayed database snapshot instantly
            await fetchDatabase()
        } catch (err) {
            setStatus('error')
            setErrorMessage(err.message)
        }
    }

    function handleChange(event) {
        setName(event.target.value)
        if (status === 'error') {
            setStatus('idle')
            setErrorMessage('')
        }
    }

    return (
        <div className="create-tree-form">
            <h2>New Upgrade Tree</h2>

            <form onSubmit={handleSubmit}>
                <label htmlFor="tree-name">Tree name</label>
                <input
                    id="tree-name"
                    type="text"
                    value={name}
                    onChange={handleChange}
                    placeholder="e.g. Mage Class"
                    disabled={status === 'submitting'}
                    autoFocus
                />

                <button type="submit" disabled={status === 'submitting'}>
                    {status === 'submitting' ? 'Creating…' : 'Create Tree'}
                </button>
            </form>

            {status === 'error' && (
                <p className="form-message error" role="alert">
                    {errorMessage}
                </p>
            )}

            {status === 'success' && createdTree && (
                <p className="form-message success">
                    Created <strong>{createdTree.name}</strong> ({createdTree.id})
                </p>
            )}

            {/* Database Snapshot Display */}
            <div className="database-view" style={{ marginTop: '2rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                    <h3>Database Snapshot</h3>
                    <button type="button" onClick={fetchDatabase} disabled={isDbLoading}>
                        {isDbLoading ? 'Refreshing…' : 'Refresh'}
                    </button>
                </div>

                {!dbData ? (
                    <p>Loading database snapshot...</p>
                ) : Object.keys(dbData).length === 0 ? (
                    <p>Database is empty.</p>
                ) : (
                    Object.entries(dbData).map(([className, instances]) => (
                        <div key={className} className="entity-group">
                            <h4>{className}</h4>
                            {Object.keys(instances).length === 0 ? (
                                <p style={{ fontStyle: 'italic' }}>No entities</p>
                            ) : (
                                <ul>
                                    {Object.entries(instances).map(([id, attributes]) => (
                                        <li key={id}>
                                            <strong>{id}</strong>: {JSON.stringify(attributes)}
                                        </li>
                                    ))}
                                </ul>
                            )}
                        </div>
                    ))
                )}
            </div>
        </div>
    )
}

export default CreateUpgradeTreeForm