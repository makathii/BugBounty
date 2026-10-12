import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import api from '../../services/api';
import ReportForm from './ReportForm';

// A report always belongs to a program. The program page links here with ?program=<id>;
// arriving without one (e.g. from the dashboard) means choosing one first.
const SubmitReport = () => {
    const navigate = useNavigate();
    const [params, setParams] = useSearchParams();
    const programId = params.get('program') || '';

    const [programs, setPrograms] = useState(null); // null = loading
    const [loadError, setLoadError] = useState('');

    useEffect(() => {
        let cancelled = false;
        api.get('/programs/researcher/')
            .then((res) => { if (!cancelled) setPrograms(res.data.results || res.data || []); })
            .catch(() => { if (!cancelled) { setPrograms([]); setLoadError('Could not load programs. Please try again.'); } });
        return () => { cancelled = true; };
    }, []);

    // Programs that can be seen (e.g. a private one to apply to) are not necessarily ones to report to.
    const submittable = (programs || []).filter((p) => p.user_has_access !== false);
    const chosen = submittable.find((p) => String(p.id) === String(programId));

    const handleSuccess = () => {
        alert('Report submitted successfully!');
        navigate('/reports');
    };

    return (
        <div style={{ padding: '2rem', maxWidth: '800px', margin: '0 auto' }}>
            <div className="report-form-card" style={{ marginBottom: '1.5rem' }}>
                <div className="form-group">
                    <label htmlFor="program-select">Program *</label>
                    <select
                        id="program-select"
                        value={chosen ? programId : ''}
                        onChange={(e) => setParams(e.target.value ? { program: e.target.value } : {})}
                        disabled={programs === null}
                    >
                        <option value="">{programs === null ? 'Loading programs...' : 'Choose a program'}</option>
                        {submittable.map((p) => (
                            <option key={p.id} value={p.id}>{p.name}</option>
                        ))}
                    </select>
                    {loadError && <span className="error-text">{loadError}</span>}
                    {programs !== null && programId && !chosen && !loadError && (
                        <span className="error-text">
                            That program is not available to you. Please choose another one.
                        </span>
                    )}
                </div>
            </div>

            {chosen ? (
                <ReportForm
                    key={chosen.id}
                    programId={chosen.id}
                    onSuccess={handleSuccess}
                    onCancel={() => navigate(`/programs/${chosen.id}`)}
                />
            ) : (
                programs !== null && !loadError && (
                    <p className="ui-muted" style={{ textAlign: 'center' }}>
                        Choose the program you are reporting to, then describe what you found.
                    </p>
                )
            )}
        </div>
    );
};

export default SubmitReport;
