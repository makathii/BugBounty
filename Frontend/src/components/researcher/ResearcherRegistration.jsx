// src/components/researcher/ResearcherRegistration.jsx
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../../services/api';
import './ResearcherRegistration.css';

const ResearcherRegistration = () => {
    const navigate = useNavigate();
    const [loading, setLoading] = useState(false);
    const [errors, setErrors] = useState({});
    const [formData, setFormData] = useState({
        bio: '',
        skills: '',
        experience_years: '',
        preferred_technologies: '',
        github_profile: '',
        linkedin_profile: '',
        payment_method: ''
    });

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);

        try {
            await api.post('/researchers/profile/', formData);
            navigate('/dashboard');
        } catch (error) {
            setErrors(error.response?.data || { general: 'Failed to save profile' });
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="researcher-registration">
            <h2>Complete Your Researcher Profile</h2>
            <form onSubmit={handleSubmit}>
                {/* Form fields for researcher profile */}
                <button type="submit" disabled={loading}>
                    {loading ? 'Saving...' : 'Complete Profile'}
                </button>
            </form>
        </div>
    );
};

export default ResearcherRegistration;