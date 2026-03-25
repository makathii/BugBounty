import React, { useState, useEffect } from 'react';
import { reportAPI, researcherAPI } from '../../services/api';

const VULNERABILITY_TYPES = [
    'SQL Injection', 'Cross-Site Scripting (XSS)', 'Cross-Site Request Forgery (CSRF)',
    'Insecure Direct Object Reference (IDOR)', 'Authentication Bypass', 'Privilege Escalation',
    'Remote Code Execution', 'Server-Side Request Forgery (SSRF)', 'XML External Entity (XXE)',
    'Broken Access Control', 'Sensitive Data Exposure', 'Security Misconfiguration',
    'Business Logic Vulnerability', 'Denial of Service', 'Other',
];

const inputStyle = {
    width: '100%',
    padding: '0.75rem',
    border: '1px solid #ddd',
    borderRadius: '6px',
    fontSize: '1rem',
    boxSizing: 'border-box',
    fontFamily: 'inherit',
};

const ReportForm = ({ onSuccess, onCancel, programId, onError }) => {
    const [formData, setFormData] = useState({
        title: '',
        description: '',
        steps_to_reproduce: '',
        impact: '',
        vulnerability_type: '',
        affected_url: '',
        program: programId || '',
    });
    const [loading, setLoading] = useState(false);
    const [errors, setErrors] = useState({}); // now handles both client & API errors

    useEffect(() => {
        setFormData(prev => ({ ...prev, program: programId || '' }));
    }, [programId]);

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, [name]: value }));
        if (errors[name]) setErrors(prev => ({ ...prev, [name]: '' })); // clear field error on change
    };

    const validate = () => {
        const errs = {};
        if (!formData.title.trim() || formData.title.trim().length < 10)
            errs.title = 'Title must be at least 10 characters.';
        if (!formData.description.trim() || formData.description.trim().length < 50)
            errs.description = 'Description must be at least 50 characters.';
        if (!formData.steps_to_reproduce.trim())
            errs.steps_to_reproduce = 'Steps to reproduce are required.';
        if (!formData.impact.trim())
            errs.impact = 'Impact description is required.';
        return errs;
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        const clientErrors = validate();
        if (Object.keys(clientErrors).length) {
            setErrors(clientErrors);
            if (onError) onError('Please fix the highlighted fields.');
            return;
        }

        setLoading(true);
        setErrors({});
        if (onError) onError(null);

        try {
            const payload = { ...formData, program: programId ? parseInt(programId, 10) : undefined };
            const response = await reportAPI.createReport(payload);
            if (onSuccess) onSuccess(response.data);
        } catch (error) {
            if (error.response?.data) {
                const apiErrs = {};
                Object.entries(error.response.data).forEach(([k, v]) => {
                    apiErrs[k] = Array.isArray(v) ? v.join(' ') : String(v);
                });
                setErrors(apiErrs);
                if (onError) onError(apiErrs.general || 'Please fix the highlighted fields.');
            } else {
                setErrors({ general: 'Failed to submit report. Please try again.' });
                if (onError) onError('Failed to submit report. Please try again.');
            }
        } finally {
            setLoading(false);
        }
    };

    const charCount = (field, min) => {
        const len = formData[field].trim().length;
        const color = len >= min ? '#27ae60' : '#e74c3c';
        return <span style={{ fontSize: '0.8rem', color }}>{len}/{min} min characters</span>;
    };

    return (
        <div style={{
            background: 'white', borderRadius: '10px',
            boxShadow: '0 2px 12px rgba(0,0,0,0.08)', padding: '2rem'
        }}>
            <h2 style={{ margin: '0 0 0.25rem 0' }}>Submit Bug Report</h2>
            <p style={{ color: '#666', margin: '0 0 2rem 0', fontSize: '0.9rem' }}>
                Severity will be assessed by our triage team after submission.
            </p>

            {errors.general && (
                <div style={{
                    background: '#f8d7da', color: '#721c24', padding: '1rem',
                    borderRadius: '6px', marginBottom: '1.5rem', border: '1px solid #f5c6cb'
                }}>
                    {errors.general}
                </div>
            )}

            <form onSubmit={handleSubmit}>
                {/* Title */}
                <div style={{ marginBottom: '1.5rem' }}>
                    <label style={{ display: 'block', fontWeight: '500', marginBottom: '0.5rem' }}>Title *</label>
                    <input
                        type="text" name="title" value={formData.title} onChange={handleChange}
                        placeholder="e.g., Reflected XSS on search parameter"
                        style={{ ...inputStyle, borderColor: errors.title ? '#e74c3c' : '#ddd' }}
                    />
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '0.25rem' }}>
                        {errors.title && <span style={{ color: '#e74c3c', fontSize: '0.82rem' }}>{errors.title}</span>}
                        {charCount('title', 10)}
                    </div>
                </div>

                {/* Vulnerability Type */}
                <div style={{ marginBottom: '1.5rem' }}>
                    <label style={{ display: 'block', fontWeight: '500', marginBottom: '0.5rem' }}>Vulnerability Type</label>
                    <select
                        name="vulnerability_type" value={formData.vulnerability_type}
                        onChange={handleChange} style={inputStyle}
                    >
                        <option value="">— Select type (optional) —</option>
                        {VULNERABILITY_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                    </select>
                </div>

                {/* Affected URL */}
                <div style={{ marginBottom: '1.5rem' }}>
                    <label style={{ display: 'block', fontWeight: '500', marginBottom: '0.5rem' }}>Affected URL / Target</label>
                    <input
                        type="text" name="affected_url" value={formData.affected_url}
                        onChange={handleChange} placeholder="https://example.com/vulnerable/endpoint"
                        style={inputStyle}
                    />
                </div>

                {/* Description */}
                <div style={{ marginBottom: '1.5rem' }}>
                    <label style={{ display: 'block', fontWeight: '500', marginBottom: '0.5rem' }}>Description *</label>
                    <textarea
                        name="description" value={formData.description} onChange={handleChange} rows={5}
                        placeholder="Describe the vulnerability in detail."
                        style={{ ...inputStyle, resize: 'vertical', borderColor: errors.description ? '#e74c3c' : '#ddd' }}
                    />
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '0.25rem' }}>
                        {errors.description && <span style={{ color: '#e74c3c', fontSize: '0.82rem' }}>{errors.description}</span>}
                        {charCount('description', 50)}
                    </div>
                </div>

                {/* Steps */}
                <div style={{ marginBottom: '1.5rem' }}>
                    <label style={{ display: 'block', fontWeight: '500', marginBottom: '0.5rem' }}>Steps to Reproduce *</label>
                    <textarea
                        name="steps_to_reproduce" value={formData.steps_to_reproduce} onChange={handleChange} rows={5}
                        placeholder={`1. Navigate to https://example.com/search\n2. Enter payload: <script>alert(1)</script>\n3. Observe alert executes`}
                        style={{ ...inputStyle, resize: 'vertical', borderColor: errors.steps_to_reproduce ? '#e74c3c' : '#ddd' }}
                    />
                    {errors.steps_to_reproduce && <span style={{ color: '#e74c3c', fontSize: '0.82rem' }}>{errors.steps_to_reproduce}</span>}
                </div>

                {/* Impact */}
                <div style={{ marginBottom: '1.5rem' }}>
                    <label style={{ display: 'block', fontWeight: '500', marginBottom: '0.5rem' }}>Impact *</label>
                    <textarea
                        name="impact" value={formData.impact} onChange={handleChange} rows={3}
                        placeholder="What can an attacker achieve by exploiting this?"
                        style={{ ...inputStyle, resize: 'vertical', borderColor: errors.impact ? '#e74c3c' : '#ddd' }}
                    />
                    {errors.impact && <span style={{ color: '#e74c3c', fontSize: '0.82rem' }}>{errors.impact}</span>}
                </div>

                {/* Actions */}
                <div style={{ display: 'flex', gap: '1rem', justifyContent: 'flex-end' }}>
                    <button type="button" onClick={onCancel}
                        style={{
                            padding: '0.75rem 1.5rem', background: '#f8f9fa',
                            color: '#495057', border: '1px solid #dee2e6',
                            borderRadius: '6px', cursor: 'pointer', fontSize: '1rem'
                        }}>Cancel</button>
                    <button type="submit" disabled={loading}
                        style={{
                            padding: '0.75rem 2rem', background: '#3498db',
                            color: 'white', border: 'none', borderRadius: '6px',
                            cursor: loading ? 'not-allowed' : 'pointer',
                            fontSize: '1rem', fontWeight: '600',
                            opacity: loading ? 0.7 : 1
                        }}>
                        {loading ? 'Submitting...' : 'Submit Report'}
                    </button>
                </div>
            </form>
        </div>
    );
};

export default ReportForm;