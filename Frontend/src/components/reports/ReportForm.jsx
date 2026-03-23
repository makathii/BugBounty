import React, { useState } from 'react';
import { reportAPI } from '../../services/api';

const ReportForm = ({ onSuccess, onCancel, programId }) => {
    const [formData, setFormData] = useState({
        title: '',
        description: '',
        severity: 'medium',
        program: programId || ''
    });
    const [loading, setLoading] = useState(false);
    const [errors, setErrors] = useState({});

    const handleChange = (e) => {
        setFormData({
            ...formData,
            [e.target.name]: e.target.value
        });
        // Clear errors when user types
        if (errors[e.target.name]) {
            setErrors({
                ...errors,
                [e.target.name]: ''
            });
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);

        try {
            await reportAPI.createReport(formData);
            if (onSuccess) onSuccess();
            // Reset form
            setFormData({
                title: '',
                description: '',
                severity: 'medium',
                program: programId || ''
            });
        } catch (error) {
            if (error.response?.data) {
                setErrors(error.response.data);
            } else {
                setErrors({ general: 'Failed to submit report' });
            }
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="report-form">
            <h2>Submit New Bug Report</h2>

            {errors.general && (
                <div className="error-message">{errors.general}</div>
            )}

            <form onSubmit={handleSubmit}>
                {programId && (
                    <div className="form-group">
                        <label>Program ID</label>
                        <input type="text" value={programId} disabled className="form-control" />
                        <input type="hidden" name="program" value={formData.program} />
                    </div>
                )}
                <div className="form-group">
                    <label htmlFor="title">Title *</label>
                    <input
                        type="text"
                        id="title"
                        name="title"
                        value={formData.title}
                        onChange={handleChange}
                        required
                        minLength="10"
                        className={errors.title ? 'error' : ''}
                    />
                    {errors.title && <span className="error-text">{errors.title}</span>}
                    <small>Minimum 10 characters</small>
                </div>

                <div className="form-group">
                    <label htmlFor="description">Description *</label>
                    <textarea
                        id="description"
                        name="description"
                        value={formData.description}
                        onChange={handleChange}
                        required
                        minLength="50"
                        rows="6"
                        className={errors.description ? 'error' : ''}
                        placeholder="Provide detailed steps to reproduce the vulnerability..."
                    />
                    {errors.description && <span className="error-text">{errors.description}</span>}
                    <small>Minimum 50 characters</small>
                </div>

                <div className="form-group">
                    <label htmlFor="severity">Severity *</label>
                    <select
                        id="severity"
                        name="severity"
                        value={formData.severity}
                        onChange={handleChange}
                    >
                        <option value="low">Low</option>
                        <option value="medium">Medium</option>
                        <option value="high">High</option>
                        <option value="critical">Critical</option>
                    </select>
                </div>

                <div className="form-actions">
                    <button
                        type="button"
                        onClick={onCancel}
                        className="btn btn-secondary"
                    >
                        Cancel
                    </button>
                    <button
                        type="submit"
                        disabled={loading}
                        className="btn btn-primary"
                    >
                        {loading ? 'Submitting...' : 'Submit Report'}
                    </button>
                </div>
            </form>
        </div>
    );
};

export default ReportForm;