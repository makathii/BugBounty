// src/components/company/CompanyRegistration.jsx
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import api from '../../services/api';
import '../auth/auth.css';

const CompanyRegistration = () => {
    const { setHasCompanyProfile } = useAuth();
    const navigate = useNavigate();
    const [loading, setLoading] = useState(false);
    const [errors, setErrors] = useState({});
    const [formData, setFormData] = useState({
        company_name: '',
        website: '',
        description: '',
        contact_email: '',
        industry: '',
        country: ''
    });

    const handleChange = (e) => {
        setFormData({
            ...formData,
            [e.target.name]: e.target.value
        });
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
        setErrors({});

        try {
            await api.post('/users/companies/', formData);

            setHasCompanyProfile(true);

            navigate('/company-dashboard');

        } catch (error) {
            if (error.response?.data) {
                setErrors(error.response.data);
            } else {
                setErrors({ general: 'Failed to register company profile' });
            }
        } finally {
            setLoading(false);
        }
    };

    const handleSkip = () => {
        navigate('/dashboard');
    };

    return (
        <div className="company-registration-container">
            <div className="company-registration-card">
                <div className="registration-header">
                    <h2>Complete Your Company Profile</h2>
                    <p className="subtitle">
                        Tell us more about your company to set up your first bug bounty program
                    </p>
                </div>

                {errors.general && (
                    <div className="alert alert-danger">{errors.general}</div>
                )}

                <form onSubmit={handleSubmit}>
                    <div className="form-section">
                        <h3>Company Details</h3>

                        <div className="form-group">
                            <label htmlFor="company_name">Company Name *</label>
                            <input
                                type="text"
                                id="company_name"
                                name="company_name"
                                value={formData.company_name}
                                onChange={handleChange}
                                required
                                className={errors.company_name ? 'error' : ''}
                                disabled={loading}
                                placeholder="Official company name"
                            />
                            {errors.company_name && <div className="error-text">{errors.company_name}</div>}
                        </div>

                        <div className="form-row">
                            <div className="form-group">
                                <label htmlFor="website">Website *</label>
                                <input
                                    type="url"
                                    id="website"
                                    name="website"
                                    value={formData.website}
                                    onChange={handleChange}
                                    required
                                    className={errors.website ? 'error' : ''}
                                    disabled={loading}
                                    placeholder="https://example.com"
                                />
                                {errors.website && <div className="error-text">{errors.website}</div>}
                            </div>

                            <div className="form-group">
                                <label htmlFor="industry">Industry</label>
                                <select
                                    id="industry"
                                    name="industry"
                                    value={formData.industry}
                                    onChange={handleChange}
                                    className={errors.industry ? 'error' : ''}
                                    disabled={loading}
                                >
                                    <option value="">Select Industry</option>
                                    <option value="Technology">Technology</option>
                                    <option value="Finance">Finance</option>
                                    <option value="Healthcare">Healthcare</option>
                                    <option value="E-commerce">E-commerce</option>
                                    <option value="Education">Education</option>
                                    <option value="Other">Other</option>
                                </select>
                                {errors.industry && <div className="error-text">{errors.industry}</div>}
                            </div>
                        </div>

                        <div className="form-row">
                            <div className="form-group">
                                <label htmlFor="contact_email">Contact Email *</label>
                                <input
                                    type="email"
                                    id="contact_email"
                                    name="contact_email"
                                    value={formData.contact_email}
                                    onChange={handleChange}
                                    required
                                    className={errors.contact_email ? 'error' : ''}
                                    disabled={loading}
                                    placeholder="security@example.com"
                                />
                                {errors.contact_email && <div className="error-text">{errors.contact_email}</div>}
                                <small>For vulnerability reports and communications</small>
                            </div>

                            <div className="form-group">
                                <label htmlFor="country">Country</label>
                                <input
                                    type="text"
                                    id="country"
                                    name="country"
                                    value={formData.country}
                                    onChange={handleChange}
                                    className={errors.country ? 'error' : ''}
                                    disabled={loading}
                                    placeholder="e.g., United States"
                                />
                                {errors.country && <div className="error-text">{errors.country}</div>}
                            </div>
                        </div>

                        <div className="form-group">
                            <label htmlFor="description">Company Description *</label>
                            <textarea
                                id="description"
                                name="description"
                                value={formData.description}
                                onChange={handleChange}
                                required
                                rows="4"
                                className={errors.description ? 'error' : ''}
                                disabled={loading}
                                placeholder="Describe your company, products, and what you'd like to secure..."
                            />
                            {errors.description && <div className="error-text">{errors.description}</div>}
                            <small>This description will be shown to security researchers</small>
                        </div>
                    </div>

                    <div className="form-actions">
                        <button
                            type="button"
                            onClick={handleSkip}
                            className="btn btn-secondary"
                            disabled={loading}
                        >
                            Skip for Now
                        </button>
                        <button
                            type="submit"
                            className="btn btn-primary"
                            disabled={loading}
                        >
                            {loading ? 'Saving...' : 'Complete Profile'}
                        </button>
                    </div>

                    <div className="registration-note">
                        <p>
                            <strong>Note:</strong> You can skip this step and complete your profile later,
                            but you'll need to complete it before creating your first bug bounty program.
                        </p>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default CompanyRegistration;