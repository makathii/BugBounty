import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import ReportForm from '../../components/reports/ReportForm';
import { researcherAPI } from '../../services/api';

const SubmitReport = () => {
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const programId = searchParams.get('program');

    const [program, setProgram] = useState(null);
    const [accessState, setAccessState] = useState('loading'); // loading | granted | denied | not_found
    const [formError, setFormError] = useState(null);

    useEffect(() => {
        if (!programId) {
            setAccessState('granted'); //TODO: No program specified, allow submission to general triage 
            return;
        }
        checkAccess();
    }, [programId]);

    const checkAccess = async () => {
        try {
            const response = await researcherAPI.getProgram(programId);
            const prog = response.data;
            setProgram(prog);

            if (!prog.can_accept_submissions || prog.user_has_access === false) {
                setAccessState('denied');
                return;
            }

            setAccessState('granted');
        } catch (err) {
            if (err.response?.status === 404 || err.response?.status === 403) {
                setAccessState('not_found');
            } else {
                setAccessState('denied');
            }
        }
    };

    const handleSuccess = (report) => {
        navigate(`/reports/${report.id}`, { state: { successMessage: 'Report submitted successfully!' } });
    };

    const handleCancel = () => {
        if (programId) navigate(`/programs/${programId}`);
        else navigate('/dashboard');
    };

    if (accessState === 'loading') {
        return (
            <div style={{ padding: '3rem', textAlign: 'center' }}>
                <div style={{
                    border: '4px solid #f3f3f3', borderTop: '4px solid #3498db',
                    borderRadius: '50%', width: '40px', height: '40px',
                    animation: 'spin 1s linear infinite', margin: '0 auto 1rem'
                }} />
                <p style={{ color: '#666' }}>Checking program access...</p>
                <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
            </div>
        );
    }

    if (accessState === 'not_found') {
        return (
            <div style={{ padding: '3rem', maxWidth: '600px', margin: '0 auto', textAlign: 'center' }}>
                <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>🔍</div>
                <h2>Program not found</h2>
                <p style={{ color: '#666', marginBottom: '1.5rem' }}>
                    This program doesn't exist or you don't have permission to view it.
                </p>
                <Link to="/programs" style={{
                    padding: '0.75rem 1.5rem', background: '#3498db',
                    color: 'white', textDecoration: 'none', borderRadius: '4px'
                }}>Browse Programs</Link>
            </div>
        );
    }

    if (accessState === 'denied') {
        const isPaused = program?.status === 'paused';
        const isClosed = program?.status === 'closed';
        const isExpired = program?.end_date && new Date(program.end_date) < new Date();
        const noAccess = program && !program.user_has_access;

        let reason = 'You cannot submit a report to this program right now.';
        let action = null;

        if (isPaused) reason = `${program.name} is currently paused and not accepting reports.`;
        else if (isClosed) reason = `${program.name} is closed and no longer accepting reports.`;
        else if (isExpired) reason = `${program.name} has ended.`;
        else if (noAccess) {
            reason = `You need to join ${program.name} before submitting a report.`;
            action = <Link to={`/programs/${programId}`} style={{
                padding: '0.75rem 1.5rem', background: '#9b59b6',
                color: 'white', textDecoration: 'none', borderRadius: '4px', marginRight: '1rem'
            }}>Join Program</Link>;
        }

        return (
            <div style={{ padding: '3rem', maxWidth: '600px', margin: '0 auto', textAlign: 'center' }}>
                <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>🚫</div>
                <h2>Access denied</h2>
                <p style={{ color: '#666', marginBottom: '1.5rem' }}>{reason}</p>
                <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center', flexWrap: 'wrap' }}>
                    {action}
                    <Link to="/programs" style={{
                        padding: '0.75rem 1.5rem', background: '#3498db',
                        color: 'white', textDecoration: 'none', borderRadius: '4px'
                    }}>Browse Programs</Link>
                </div>
            </div>
        );
    }

    // Access granted
    return (
        <div style={{ padding: '2rem', maxWidth: '800px', margin: '0 auto' }}>
            {/* Breadcrumb */}
            <div style={{ marginBottom: '1.5rem', fontSize: '0.9rem', color: '#666' }}>
                <Link to="/programs" style={{ color: '#3498db', textDecoration: 'none' }}>Programs</Link>
                {program && (
                    <>
                        {' / '}
                        <Link to={`/programs/${programId}`} style={{ color: '#3498db', textDecoration: 'none' }}>
                            {program.name}
                        </Link>
                    </>
                )}
                {' / Submit Report'}
            </div>

            {/* Program banner */}
            {program && (
                <div style={{
                    background: 'white', padding: '1.25rem 1.5rem', borderRadius: '8px',
                    boxShadow: '0 2px 10px rgba(0,0,0,0.08)', marginBottom: '1.5rem',
                    borderLeft: '4px solid #3498db',
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                    flexWrap: 'wrap', gap: '0.5rem'
                }}>
                    <div>
                        <div style={{ fontWeight: '600', marginBottom: '0.2rem' }}>Submitting to: {program.name}</div>
                        <div style={{ fontSize: '0.85rem', color: '#666' }}>
                            {program.company?.username} · {program.scope_type_display || program.scope_type}
                            {program.bounty_range && program.bounty_range !== 'Not specified' && (
                                <> · <span style={{ color: '#27ae60', fontWeight: '500' }}>{program.bounty_range}</span></>
                            )}
                        </div>
                    </div>
                    <Link to={`/programs/${programId}`} style={{ fontSize: '0.85rem', color: '#3498db', textDecoration: 'none' }}>
                        View program details →
                    </Link>
                </div>
            )}

            {/* Display backend/form errors */}
            {formError && (
                <div style={{
                    background: '#f8d7da', color: '#721c24', padding: '1rem',
                    borderRadius: '6px', marginBottom: '1.5rem', border: '1px solid #f5c6cb'
                }}>
                    {formError}
                </div>
            )}

            <ReportForm
                onSuccess={handleSuccess}
                onCancel={handleCancel}
                programId={programId}
                onError={(err) => setFormError(err)}
            />
        </div>
    );
};

export default SubmitReport;