import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { companyAPI } from '../../services/api';
import { statusTone, scopeTone } from '../../utils/tones';

const CompanyPrograms = () => {
    const navigate = useNavigate();
    const [programs, setPrograms] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [actioning, setActioning] = useState(null);

    useEffect(() => { loadPrograms(); }, []);

    const loadPrograms = async () => {
        setLoading(true);
        setError(null);
        try {
            const res = await companyAPI.getPrograms();
            setPrograms(res.data.results ?? res.data);
        } catch {
            setError('Failed to load programs.');
        } finally {
            setLoading(false);
        }
    };

    const handleAction = async (id, action) => {
        setActioning(id);
        try {
            if (action === 'activate') await companyAPI.activateProgram(id);
            if (action === 'pause') await companyAPI.pauseProgram(id);
            if (action === 'close') await companyAPI.closeProgram(id);
            await loadPrograms();
        } catch (err) {
            alert(err.response?.data?.error || `Failed to ${action} program.`);
        } finally {
            setActioning(null);
        }
    };

    if (loading) return (
        <div className="ui-loading">
            <div className="ui-spinner" />
            <p>Loading programs...</p>
        </div>
    );

    return (
        <div className="ui-page">
            <header className="ui-page-header ui-page-header--row">
                <div>
                    <h1 className="ui-title">Your Programs</h1>
                    <p className="ui-subtitle">Manage your bug bounty programs</p>
                </div>
                <button className="ui-btn" onClick={() => navigate('/company/programs/create')}>
                    + Create Program
                </button>
            </header>

            {error && <div className="ui-alert tone-red">{error}</div>}

            {programs.length === 0 ? (
                <div className="ui-card ui-empty">
                    <div className="ui-empty-icon">🎯</div>
                    <h3>No programs yet</h3>
                    <p>Create your first bug bounty program to start receiving security reports.</p>
                    <button className="ui-btn" onClick={() => navigate('/company/programs/create')}>
                        Create Your First Program
                    </button>
                </div>
            ) : (
                <div className="ui-stack" style={{ gap: '1rem' }}>
                    {programs.map(program => {
                        const isActioning = actioning === program.id;
                        return (
                            <div key={program.id} className={`ui-card ui-card--hover ${statusTone(program.status)}`}>
                                <div className="ui-row ui-row--between ui-row--start" style={{ gap: '1rem' }}>
                                    <div className="ui-grow">
                                        <div className="ui-row" style={{ marginBottom: '0.5rem' }}>
                                            <h3 className="ui-section-title" style={{ margin: 0 }}>{program.name}</h3>
                                            <span className={`ui-badge ${statusTone(program.status)}`}>{program.status}</span>
                                            <span className={`ui-badge ${scopeTone(program.scope_type)}`}>{program.scope_type}</span>
                                        </div>
                                        <p className="ui-muted ui-small" style={{ margin: '0 0 0.75rem' }}>
                                            {program.short_description || program.description?.substring(0, 100) + '...'}
                                        </p>
                                        <div className="ui-row ui-muted ui-small" style={{ gap: '1.5rem' }}>
                                            <span>📋 {program.total_reports} reports</span>
                                            <span>💰 ${parseFloat(program.total_bounties || 0).toLocaleString()} paid</span>
                                            {program.bounty_range && program.bounty_range !== 'Not specified' && (
                                                <span>🎯 {program.bounty_range}</span>
                                            )}
                                        </div>
                                    </div>

                                    <div className="ui-row">
                                        <Link to={`/programs/${program.id}`} className="ui-btn ui-btn--ghost ui-btn--sm">View</Link>

                                        {program.status === 'draft' && (
                                            <button className="ui-btn ui-btn--green ui-btn--sm" disabled={isActioning}
                                                    onClick={() => handleAction(program.id, 'activate')}>
                                                {isActioning ? '...' : 'Activate'}
                                            </button>
                                        )}
                                        {program.status === 'active' && (
                                            <button className="ui-btn ui-btn--warn ui-btn--sm" disabled={isActioning}
                                                    onClick={() => handleAction(program.id, 'pause')}>
                                                {isActioning ? '...' : 'Pause'}
                                            </button>
                                        )}
                                        {program.status === 'paused' && (
                                            <button className="ui-btn ui-btn--green ui-btn--sm" disabled={isActioning}
                                                    onClick={() => handleAction(program.id, 'activate')}>
                                                {isActioning ? '...' : 'Resume'}
                                            </button>
                                        )}
                                        {program.status !== 'closed' && (
                                            <button
                                                className="ui-btn ui-btn--danger ui-btn--sm"
                                                disabled={isActioning}
                                                onClick={() => {
                                                    if (window.confirm('Close this program? Researchers will no longer be able to submit reports.')) {
                                                        handleAction(program.id, 'close');
                                                    }
                                                }}
                                            >
                                                Close
                                            </button>
                                        )}
                                    </div>
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
};

export default CompanyPrograms;
