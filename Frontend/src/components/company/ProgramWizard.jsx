import React, { useState } from 'react';
import api from '../../services/api';

const ProgramWizard = ({ onSuccess, onCancel }) => {
    const [step, setStep] = useState(1);
    const [formData, setFormData] = useState({
        name: '',
        description: '',
        scope_type: 'public',
        bounty_policy: '',
        min_bounty: '',
        max_bounty: '',
        start_date: '',
        end_date: '',
        allow_anonymous: false,
        require_ndas: false,
        invitation_only: false,
        scopes: [{ target: '', target_type: 'web_application', is_in_scope: true, description: '' }]
    });
    const [loading, setLoading] = useState(false);
    const [errors, setErrors] = useState({});

    const handleChange = (e) => {
        const { name, value, type, checked } = e.target;
        setFormData({
            ...formData,
            [name]: type === 'checkbox' ? checked : value
        });
    };

    const addScope = () => {
        setFormData({
            ...formData,
            scopes: [...formData.scopes, { target: '', target_type: 'web_application', is_in_scope: true, description: '' }]
        });
    };

    const removeScope = (index) => {
        const newScopes = [...formData.scopes];
        newScopes.splice(index, 1);
        setFormData({ ...formData, scopes: newScopes });
    };

    const updateScope = (index, field, value) => {
        const newScopes = [...formData.scopes];
        newScopes[index][field] = value;
        setFormData({ ...formData, scopes: newScopes });
    };

    const toggleScopeInOut = (index) => {
        const newScopes = [...formData.scopes];
        newScopes[index].is_in_scope = !newScopes[index].is_in_scope;
        setFormData({ ...formData, scopes: newScopes });
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setErrors({});

        try {
            const response = await api.post('/programs/programs/', formData);
            if (onSuccess) onSuccess(response.data);
        } catch (error) {
            console.error('Program creation failed:', error);
            if (error.response?.data) {
                setErrors(error.response.data);
            } else {
                setErrors({ general: 'Failed to create program' });
            }
        } finally {
            setLoading(false);
        }
    };

    return (
        <div style={{ maxWidth: '800px', margin: '0 auto' }}>
            <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
                <h2>Create Bug Bounty Program</h2>
                <div style={{ display: 'flex', justifyContent: 'center', gap: '2rem', marginTop: '1rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <div style={{
                            width: '24px',
                            height: '24px',
                            borderRadius: '50%',
                            background: step === 1 ? '#3498db' : '#ecf0f1',
                            color: step === 1 ? 'white' : '#7f8c8d',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            fontWeight: 'bold'
                        }}>
                            1
                        </div>
                        <span style={{ color: step === 1 ? '#3498db' : '#7f8c8d', fontWeight: step === 1 ? '600' : '400' }}>
                            Basic Info
                        </span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <div style={{
                            width: '24px',
                            height: '24px',
                            borderRadius: '50%',
                            background: step === 2 ? '#3498db' : '#ecf0f1',
                            color: step === 2 ? 'white' : '#7f8c8d',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            fontWeight: 'bold'
                        }}>
                            2
                        </div>
                        <span style={{ color: step === 2 ? '#3498db' : '#7f8c8d', fontWeight: step === 2 ? '600' : '400' }}>
                            Scope
                        </span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <div style={{
                            width: '24px',
                            height: '24px',
                            borderRadius: '50%',
                            background: step === 3 ? '#3498db' : '#ecf0f1',
                            color: step === 3 ? 'white' : '#7f8c8d',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            fontWeight: 'bold'
                        }}>
                            3
                        </div>
                        <span style={{ color: step === 3 ? '#3498db' : '#7f8c8d', fontWeight: step === 3 ? '600' : '400' }}>
                            Settings & Rewards
                        </span>
                    </div>
                </div>
            </div>

            {errors.general && (
                <div style={{
                    background: '#f8d7da',
                    color: '#721c24',
                    padding: '1rem',
                    borderRadius: '8px',
                    marginBottom: '1.5rem',
                    border: '1px solid #f5c6cb'
                }}>
                    {errors.general}
                </div>
            )}

            <form onSubmit={handleSubmit}>
                {step === 1 && (
                    <div style={{
                        background: 'white',
                        padding: '2rem',
                        borderRadius: '8px',
                        boxShadow: '0 2px 10px rgba(0,0,0,0.1)'
                    }}>
                        <div style={{ marginBottom: '1.5rem' }}>
                            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500' }}>
                                Program Name *
                            </label>
                            <input
                                type="text"
                                name="name"
                                value={formData.name}
                                onChange={handleChange}
                                required
                                placeholder="e.g., Public Bug Bounty Program"
                                style={{
                                    width: '100%',
                                    padding: '0.75rem',
                                    border: '1px solid #ddd',
                                    borderRadius: '4px',
                                    fontSize: '1rem'
                                }}
                            />
                            {errors.name && (
                                <span style={{ color: '#e74c3c', fontSize: '0.9rem' }}>{errors.name}</span>
                            )}
                        </div>

                        <div style={{ marginBottom: '1.5rem' }}>
                            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500' }}>
                                Description *
                            </label>
                            <textarea
                                name="description"
                                value={formData.description}
                                onChange={handleChange}
                                required
                                rows="4"
                                placeholder="Describe what researchers should look for, program goals, etc."
                                style={{
                                    width: '100%',
                                    padding: '0.75rem',
                                    border: '1px solid #ddd',
                                    borderRadius: '4px',
                                    fontSize: '1rem',
                                    fontFamily: 'inherit'
                                }}
                            />
                            {errors.description && (
                                <span style={{ color: '#e74c3c', fontSize: '0.9rem' }}>{errors.description}</span>
                            )}
                        </div>

                        <div style={{ marginBottom: '1.5rem' }}>
                            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500' }}>
                                Scope Type
                            </label>
                            <select
                                name="scope_type"
                                value={formData.scope_type}
                                onChange={handleChange}
                                style={{
                                    width: '100%',
                                    padding: '0.75rem',
                                    border: '1px solid #ddd',
                                    borderRadius: '4px',
                                    fontSize: '1rem'
                                }}
                            >
                                <option value="public">Public (Visible to all researchers)</option>
                                <option value="private">Private (Invite only)</option>
                                <option value="vdp">VDP (Vulnerability Disclosure Program)</option>
                            </select>
                        </div>

                        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem' }}>
                            <button
                                type="button"
                                onClick={onCancel}
                                style={{
                                    padding: '0.75rem 1.5rem',
                                    background: '#95a5a6',
                                    color: 'white',
                                    border: 'none',
                                    borderRadius: '4px',
                                    cursor: 'pointer',
                                    fontSize: '1rem'
                                }}
                            >
                                Cancel
                            </button>
                            <button
                                type="button"
                                onClick={() => setStep(2)}
                                style={{
                                    padding: '0.75rem 1.5rem',
                                    background: '#3498db',
                                    color: 'white',
                                    border: 'none',
                                    borderRadius: '4px',
                                    cursor: 'pointer',
                                    fontSize: '1rem'
                                }}
                            >
                                Next: Define Scope
                            </button>
                        </div>
                    </div>
                )}

                {step === 2 && (
                    <div style={{
                        background: 'white',
                        padding: '2rem',
                        borderRadius: '8px',
                        boxShadow: '0 2px 10px rgba(0,0,0,0.1)'
                    }}>
                        <div style={{ marginBottom: '1.5rem' }}>
                            <h3 style={{ margin: '0 0 1rem 0' }}>Define Program Scope</h3>
                            <p style={{ color: '#666', marginBottom: '1.5rem' }}>
                                Specify which targets researchers can test and which are out of bounds.
                            </p>

                            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                                {formData.scopes.map((scope, index) => (
                                    <div key={index} style={{
                                        border: '1px solid #e9ecef',
                                        borderRadius: '8px',
                                        padding: '1.5rem',
                                        background: scope.is_in_scope ? '#f8fff8' : '#fff8f8'
                                    }}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                                                <button
                                                    type="button"
                                                    onClick={() => toggleScopeInOut(index)}
                                                    style={{
                                                        padding: '0.5rem 1rem',
                                                        background: scope.is_in_scope ? '#27ae60' : '#e74c3c',
                                                        color: 'white',
                                                        border: 'none',
                                                        borderRadius: '4px',
                                                        cursor: 'pointer',
                                                        fontSize: '0.9rem',
                                                        fontWeight: '500'
                                                    }}
                                                >
                                                    {scope.is_in_scope ? 'IN-SCOPE' : 'OUT-OF-SCOPE'}
                                                </button>
                                                {formData.scopes.length > 1 && (
                                                    <button
                                                        type="button"
                                                        onClick={() => removeScope(index)}
                                                        style={{
                                                            padding: '0.5rem',
                                                            background: '#e74c3c',
                                                            color: 'white',
                                                            border: 'none',
                                                            borderRadius: '4px',
                                                            cursor: 'pointer',
                                                            fontSize: '1rem'
                                                        }}
                                                    >
                                                        × Remove
                                                    </button>
                                                )}
                                            </div>
                                        </div>

                                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
                                            <div>
                                                <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem' }}>
                                                    Target (Domain/IP/CIDR)
                                                </label>
                                                <input
                                                    type="text"
                                                    placeholder="e.g., *.example.com or 192.168.1.0/24"
                                                    value={scope.target}
                                                    onChange={(e) => updateScope(index, 'target', e.target.value)}
                                                    style={{
                                                        width: '100%',
                                                        padding: '0.75rem',
                                                        border: '1px solid #ddd',
                                                        borderRadius: '4px',
                                                        fontSize: '1rem'
                                                    }}
                                                />
                                            </div>
                                            <div>
                                                <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem' }}>
                                                    Target Type
                                                </label>
                                                <select
                                                    value={scope.target_type}
                                                    onChange={(e) => updateScope(index, 'target_type', e.target.value)}
                                                    style={{
                                                        width: '100%',
                                                        padding: '0.75rem',
                                                        border: '1px solid #ddd',
                                                        borderRadius: '4px',
                                                        fontSize: '1rem'
                                                    }}
                                                >
                                                    <option value="web_application">Web Application</option>
                                                    <option value="mobile_app">Mobile App</option>
                                                    <option value="api">API</option>
                                                    <option value="iot">IoT Device</option>
                                                    <option value="network">Network</option>
                                                    <option value="hardware">Hardware</option>
                                                    <option value="other">Other</option>
                                                </select>
                                            </div>
                                        </div>

                                        <div>
                                            <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem' }}>
                                                Description (Optional)
                                            </label>
                                            <textarea
                                                placeholder="Additional details about this target..."
                                                value={scope.description}
                                                onChange={(e) => updateScope(index, 'description', e.target.value)}
                                                rows="2"
                                                style={{
                                                    width: '100%',
                                                    padding: '0.75rem',
                                                    border: '1px solid #ddd',
                                                    borderRadius: '4px',
                                                    fontSize: '1rem'
                                                }}
                                            />
                                        </div>
                                    </div>
                                ))}
                            </div>

                            <button
                                type="button"
                                onClick={addScope}
                                style={{
                                    marginTop: '1rem',
                                    padding: '0.75rem 1.5rem',
                                    background: '#f8f9fa',
                                    color: '#495057',
                                    border: '2px dashed #dee2e6',
                                    borderRadius: '4px',
                                    cursor: 'pointer',
                                    fontSize: '1rem',
                                    width: '100%'
                                }}
                            >
                                + Add Another Target
                            </button>
                        </div>

                        <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem' }}>
                            <button
                                type="button"
                                onClick={() => setStep(1)}
                                style={{
                                    padding: '0.75rem 1.5rem',
                                    background: '#95a5a6',
                                    color: 'white',
                                    border: 'none',
                                    borderRadius: '4px',
                                    cursor: 'pointer',
                                    fontSize: '1rem'
                                }}
                            >
                                Back
                            </button>
                            <button
                                type="button"
                                onClick={() => setStep(3)}
                                style={{
                                    padding: '0.75rem 1.5rem',
                                    background: '#3498db',
                                    color: 'white',
                                    border: 'none',
                                    borderRadius: '4px',
                                    cursor: 'pointer',
                                    fontSize: '1rem'
                                }}
                            >
                                Next: Settings & Rewards
                            </button>
                        </div>
                    </div>
                )}

                {step === 3 && (
                    <div style={{
                        background: 'white',
                        padding: '2rem',
                        borderRadius: '8px',
                        boxShadow: '0 2px 10px rgba(0,0,0,0.1)'
                    }}>
                        <div style={{ marginBottom: '2rem' }}>
                            <h3 style={{ margin: '0 0 1rem 0' }}>Program Settings & Rewards</h3>

                            <div style={{ marginBottom: '1.5rem' }}>
                                <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500' }}>
                                    Bounty Policy *
                                </label>
                                <textarea
                                    name="bounty_policy"
                                    value={formData.bounty_policy}
                                    onChange={handleChange}
                                    required
                                    rows="4"
                                    placeholder="Describe your reward structure, payment methods, timeline for payouts, etc."
                                    style={{
                                        width: '100%',
                                        padding: '0.75rem',
                                        border: '1px solid #ddd',
                                        borderRadius: '4px',
                                        fontSize: '1rem'
                                    }}
                                />
                                {errors.bounty_policy && (
                                    <span style={{ color: '#e74c3c', fontSize: '0.9rem' }}>{errors.bounty_policy}</span>
                                )}
                            </div>

                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', marginBottom: '1.5rem' }}>
                                <div>
                                    <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500' }}>
                                        Minimum Bounty (Optional)
                                    </label>
                                    <input
                                        type="number"
                                        name="min_bounty"
                                        value={formData.min_bounty}
                                        onChange={handleChange}
                                        placeholder="0.00"
                                        step="0.01"
                                        min="0"
                                        style={{
                                            width: '100%',
                                            padding: '0.75rem',
                                            border: '1px solid #ddd',
                                            borderRadius: '4px',
                                            fontSize: '1rem'
                                        }}
                                    />
                                </div>
                                <div>
                                    <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500' }}>
                                        Maximum Bounty (Optional)
                                    </label>
                                    <input
                                        type="number"
                                        name="max_bounty"
                                        value={formData.max_bounty}
                                        onChange={handleChange}
                                        placeholder="0.00"
                                        step="0.01"
                                        min="0"
                                        style={{
                                            width: '100%',
                                            padding: '0.75rem',
                                            border: '1px solid #ddd',
                                            borderRadius: '4px',
                                            fontSize: '1rem'
                                        }}
                                    />
                                </div>
                            </div>

                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', marginBottom: '1.5rem' }}>
                                <div>
                                    <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500' }}>
                                        Start Date (Optional)
                                    </label>
                                    <input
                                        type="date"
                                        name="start_date"
                                        value={formData.start_date}
                                        onChange={handleChange}
                                        style={{
                                            width: '100%',
                                            padding: '0.75rem',
                                            border: '1px solid #ddd',
                                            borderRadius: '4px',
                                            fontSize: '1rem'
                                        }}
                                    />
                                </div>
                                <div>
                                    <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500' }}>
                                        End Date (Optional)
                                    </label>
                                    <input
                                        type="date"
                                        name="end_date"
                                        value={formData.end_date}
                                        onChange={handleChange}
                                        style={{
                                            width: '100%',
                                            padding: '0.75rem',
                                            border: '1px solid #ddd',
                                            borderRadius: '4px',
                                            fontSize: '1rem'
                                        }}
                                    />
                                </div>
                            </div>

                            <div style={{ background: '#f8f9fa', padding: '1.5rem', borderRadius: '8px', marginBottom: '1.5rem' }}>
                                <h4 style={{ margin: '0 0 1rem 0' }}>Program Settings</h4>
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                                    <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                                        <input
                                            type="checkbox"
                                            name="allow_anonymous"
                                            checked={formData.allow_anonymous}
                                            onChange={handleChange}
                                        />
                                        <span>Allow anonymous submissions</span>
                                    </label>
                                    <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                                        <input
                                            type="checkbox"
                                            name="require_ndas"
                                            checked={formData.require_ndas}
                                            onChange={handleChange}
                                        />
                                        <span>Require NDA for participation</span>
                                    </label>
                                    {formData.scope_type === 'private' && (
                                        <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                                            <input
                                                type="checkbox"
                                                name="invitation_only"
                                                checked={formData.invitation_only}
                                                onChange={handleChange}
                                            />
                                            <span>Invitation only (researchers must be invited)</span>
                                        </label>
                                    )}
                                </div>
                            </div>
                        </div>

                        <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem' }}>
                            <button
                                type="button"
                                onClick={() => setStep(2)}
                                style={{
                                    padding: '0.75rem 1.5rem',
                                    background: '#95a5a6',
                                    color: 'white',
                                    border: 'none',
                                    borderRadius: '4px',
                                    cursor: 'pointer',
                                    fontSize: '1rem'
                                }}
                            >
                                Back
                            </button>
                            <button
                                type="submit"
                                disabled={loading}
                                style={{
                                    padding: '0.75rem 1.5rem',
                                    background: '#27ae60',
                                    color: 'white',
                                    border: 'none',
                                    borderRadius: '4px',
                                    cursor: 'pointer',
                                    fontSize: '1rem',
                                    opacity: loading ? 0.7 : 1
                                }}
                            >
                                {loading ? 'Creating Program...' : 'Create Program'}
                            </button>
                        </div>
                    </div>
                )}
            </form>
        </div>
    );
};

export default ProgramWizard;