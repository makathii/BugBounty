import React, { useState, useEffect } from 'react';
import { reportAPI } from '../../services/api';

const VULNERABILITY_TYPES = [
    'SQL Injection', 'Cross-Site Scripting (XSS)', 'Cross-Site Request Forgery (CSRF)',
    'Insecure Direct Object Reference (IDOR)', 'Authentication Bypass', 'Privilege Escalation',
    'Remote Code Execution', 'Server-Side Request Forgery (SSRF)', 'XML External Entity (XXE)',
    'Broken Access Control', 'Sensitive Data Exposure', 'Security Misconfiguration',
    'Business Logic Vulnerability', 'Denial of Service', 'Other',
];

const ReportForm = ({ onSuccess, onCancel, programId, onError }) => {
    const [formData, setFormData] = useState({
        title: '',
        description: '',
        steps_to_reproduce: '',
        impact: '',
        vulnerability_type: '',
        affected_url: '',
        program: programId || '',
        is_human_generated: false, // New state field
    });
    const [loading, setLoading] = useState(false);
    const [errors, setErrors] = useState({});

    useEffect(() => {
        setFormData(prev => ({ ...prev, program: programId || '' }));
    }, [programId]);

    const handleChange = (e) => {
        const { name, value, type, checked } = e.target;
        setFormData(prev => ({
            ...prev,
            [name]: type === 'checkbox' ? checked : value
        }));
        if (errors[name]) setErrors(prev => ({ ...prev, [name]: '' }));
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
        if (!formData.is_human_generated)
            errs.is_human_generated = 'You must confirm this finding is your own work.';
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
            // Strip out or keep the checkbox data depending on what your backend expects
            const { is_human_generated, ...apiPayload } = formData;
            const payload = {
                ...apiPayload,
                program: programId ? parseInt(programId, 10) : undefined
            };

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

    const getCounterClass = (field, min) => {
        return formData[field].trim().length >= min ? 'counter-valid' : 'counter-invalid';
    };

    return (
        <div className="report-form-card">
            <div className="form-header-block">
                <h2>Submit Bug Report</h2>
                <p>Severity will be assessed by our triage team after submission.</p>
            </div>

            {errors.general && (
                <div className="error-message">{errors.general}</div>
            )}

            <form onSubmit={handleSubmit}>
                {/* Title */}
                <div className="form-group">
                    <label>Title *</label>
                    <input
                        type="text"
                        name="title"
                        value={formData.title}
                        onChange={handleChange}
                        placeholder="e.g., Reflected XSS on search parameter"
                        className={errors.title ? 'error' : ''}
                        disabled={loading}
                    />
                    <div className="field-meta">
                        {errors.title ? <span className="error-text">{errors.title}</span> : <span />}
                        <span className={`char-counter ${getCounterClass('title', 10)}`}>
                            {formData.title.trim().length}/10 min
                        </span>
                    </div>
                </div>

                {/* Vulnerability Type & Target Row */}
                <div className="form-row">
                    <div className="form-group">
                        <label>Vulnerability Type</label>
                        <select
                            name="vulnerability_type"
                            value={formData.vulnerability_type}
                            onChange={handleChange}
                            disabled={loading}
                        >
                            <option value="">— Select type —</option>
                            {VULNERABILITY_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                        </select>
                    </div>

                    <div className="form-group">
                        <label>Affected URL / Target</label>
                        <input
                            type="text"
                            name="affected_url"
                            value={formData.affected_url}
                            onChange={handleChange}
                            placeholder="https://example.com/vulnerable/endpoint"
                            disabled={loading}
                        />
                    </div>
                </div>

                {/* Description */}
                <div className="form-group">
                    <label>Description *</label>
                    <textarea
                        name="description"
                        value={formData.description}
                        onChange={handleChange}
                        rows={5}
                        placeholder="Describe the vulnerability in detail."
                        className={errors.description ? 'error' : ''}
                        disabled={loading}
                    />
                    <div className="field-meta">
                        {errors.description ? <span className="error-text">{errors.description}</span> : <span />}
                        <span className={`char-counter ${getCounterClass('description', 50)}`}>
                            {formData.description.trim().length}/50 min
                        </span>
                    </div>
                </div>

                {/* Steps */}
                <div className="form-group">
                    <label>Steps to Reproduce *</label>
                    <textarea
                        name="steps_to_reproduce"
                        value={formData.steps_to_reproduce}
                        onChange={handleChange}
                        rows={5}
                        placeholder={"1. Navigate to https://example.com/search\n2. Enter payload: <script>alert(1)</script>\n3. Observe alert executes"}
                        className={errors.steps_to_reproduce ? 'error' : ''}
                        disabled={loading}
                    />
                    {errors.steps_to_reproduce && <span className="error-text">{errors.steps_to_reproduce}</span>}
                </div>

                {/* Impact */}
                <div className="form-group">
                    <label>Impact *</label>
                    <textarea
                        name="impact"
                        value={formData.impact}
                        onChange={handleChange}
                        rows={3}
                        placeholder="What can an attacker achieve by exploiting this?"
                        className={errors.impact ? 'error' : ''}
                        disabled={loading}
                    />
                    {errors.impact && <span className="error-text">{errors.impact}</span>}
                </div>

                {/* AI / Human Verification Checkbox */}
                <div className="form-group checkbox-group">
                    <label className="checkbox-label">
                        <input
                            type="checkbox"
                            name="is_human_generated"
                            checked={formData.is_human_generated}
                            onChange={handleChange}
                            disabled={loading}
                            className={errors.is_human_generated ? 'error' : ''}
                        />
                        <span>I confirm that all steps to reproduce and impact assessments are my own work & not AI generated.</span>
                    </label>
                    {errors.is_human_generated && (
                        <span className="error-text">{errors.is_human_generated}</span>
                    )}
                </div>

                {/* Actions */}
                <div className="form-actions-row">
                    <button
                        type="button"
                        onClick={onCancel}
                        className="btn btn-secondary"
                        disabled={loading}
                    >
                        Cancel
                    </button>
                    <button
                        type="submit"
                        className="btn btn-primary"
                        disabled={loading || !formData.is_human_generated}
                    >
                        {loading ? 'Submitting...' : 'Submit Report'}
                    </button>
                </div>
            </form>
        </div>
    );
};

export default ReportForm;