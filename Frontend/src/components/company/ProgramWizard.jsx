import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { companyAPI } from '../../services/api';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const STEPS = [
    { n: 1, label: 'Basic Info' },
    { n: 2, label: 'Scope' },
    { n: 3, label: 'Rewards & Guidelines' },
    { n: 4, label: 'Review & Launch' },
];

const TARGET_TYPES = [
    { value: 'web_application',   label: 'Web Application' },
    { value: 'mobile_app',        label: 'Mobile App' },
    { value: 'api',               label: 'API / Web Service' },
    { value: 'iot',               label: 'IoT Device' },
    { value: 'network',           label: 'Network Infrastructure' },
    { value: 'hardware',          label: 'Hardware' },
    { value: 'source_code',       label: 'Source Code' },
    { value: 'social_engineering',label: 'Social Engineering' },
    { value: 'physical_security', label: 'Physical Security' },
    { value: 'other',             label: 'Other' },
];

const emptyScope = () => ({
    target: '',
    target_type: 'web_application',
    is_in_scope: true,
    description: '',
});

// ---------------------------------------------------------------------------
// Shared styles
// ---------------------------------------------------------------------------

const inputStyle = {
    width: '100%',
    padding: '0.75rem',
    border: '1px solid #ddd',
    borderRadius: '6px',
    fontSize: '1rem',
    boxSizing: 'border-box',
    fontFamily: 'inherit',
};

const labelStyle = {
    display: 'block',
    fontWeight: '500',
    marginBottom: '0.5rem',
    fontSize: '0.95rem',
};

const sectionStyle = {
    marginBottom: '1.75rem',
};

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

const FieldError = ({ error }) =>
    error ? (
        <span style={{ color: '#e74c3c', fontSize: '0.82rem', marginTop: '0.3rem', display: 'block' }}>
            {error}
        </span>
    ) : null;

const SectionLabel = ({ children, hint }) => (
    <label style={labelStyle}>
        {children}
        {hint && <span style={{ fontWeight: '400', color: '#888', marginLeft: '0.4rem', fontSize: '0.85rem' }}>{hint}</span>}
    </label>
);

const StepIndicator = ({ currentStep }) => (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', marginBottom: '2.5rem' }}>
        {STEPS.map((s, i) => {
            const done = currentStep > s.n;
            const active = currentStep === s.n;
            return (
                <React.Fragment key={s.n}>
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.4rem' }}>
                        <div style={{
                            width: '34px', height: '34px', borderRadius: '50%',
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                            fontWeight: '700', fontSize: '0.9rem',
                            background: done ? '#27ae60' : active ? '#3498db' : '#e9ecef',
                            color: done || active ? 'white' : '#aaa',
                            transition: 'all 0.2s',
                        }}>
                            {done ? '✓' : s.n}
                        </div>
                        <span style={{
                            fontSize: '0.78rem', whiteSpace: 'nowrap',
                            fontWeight: active ? '600' : '400',
                            color: active ? '#3498db' : done ? '#27ae60' : '#aaa',
                        }}>
                            {s.label}
                        </span>
                    </div>
                    {i < STEPS.length - 1 && (
                        <div style={{
                            width: '60px', height: '2px', marginBottom: '1.4rem',
                            background: currentStep > s.n ? '#27ae60' : '#e9ecef',
                            transition: 'background 0.2s',
                        }} />
                    )}
                </React.Fragment>
            );
        })}
    </div>
);

const NavButtons = ({ step, totalSteps, onBack, onNext, onCancel, loading, nextLabel }) => (
    <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '2rem' }}>
        <button
            type="button"
            onClick={step === 1 ? onCancel : onBack}
            style={{
                padding: '0.75rem 1.5rem', background: '#f8f9fa',
                color: '#495057', border: '1px solid #dee2e6',
                borderRadius: '6px', cursor: 'pointer', fontSize: '1rem'
            }}
        >
            {step === 1 ? 'Cancel' : '← Back'}
        </button>
        <button
            type="button"
            onClick={onNext}
            disabled={loading}
            style={{
                padding: '0.75rem 2rem',
                background: step === totalSteps ? '#27ae60' : '#3498db',
                color: 'white', border: 'none', borderRadius: '6px',
                cursor: loading ? 'not-allowed' : 'pointer',
                fontSize: '1rem', fontWeight: '600',
                opacity: loading ? 0.7 : 1,
                transition: 'background 0.2s',
            }}
        >
            {loading ? 'Creating...' : (nextLabel || 'Next →')}
        </button>
    </div>
);

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

const ProgramWizard = ({ onSuccess, onCancel }) => {
    const navigate = useNavigate();

    const [step, setStep] = useState(1);
    const [loading, setLoading] = useState(false);
    const [errors, setErrors] = useState({});
    const [createdProgram, setCreatedProgram] = useState(null); // set after successful POST
    const [activating, setActivating] = useState(false);

    const [formData, setFormData] = useState({
        name: '',
        short_description: '',
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
        requires_application: false,
        testing_guidelines: '',
        report_guidelines: '',
        disclosure_policy: '',
    });

    const [scopes, setScopes] = useState([emptyScope()]);

    // ---------------------------------------------------------------------------
    // Helpers
    // ---------------------------------------------------------------------------

    const set = (field, value) => {
        setFormData(prev => {
            const next = { ...prev, [field]: value };
            // Clear private-only flags if scope type changes away from private
            if (field === 'scope_type' && value !== 'private') {
                next.invitation_only = false;
                next.requires_application = false;
            }
            return next;
        });
    };

    const handleChange = (e) => {
        const { name, value, type, checked } = e.target;
        set(name, type === 'checkbox' ? checked : value);
    };

    const updateScope = (index, field, value) => {
        setScopes(prev => prev.map((s, i) => i === index ? { ...s, [field]: value } : s));
    };

    const addScope = () => setScopes(prev => [...prev, emptyScope()]);

    const removeScope = (index) => {
        if (scopes.length === 1) return;
        setScopes(prev => prev.filter((_, i) => i !== index));
    };

    // ---------------------------------------------------------------------------
    // Validation
    // ---------------------------------------------------------------------------

    const validate = (s) => {
        const errs = {};

        if (s === 1) {
            if (!formData.name.trim())
                errs.name = 'Program name is required.';
            if (!formData.description.trim())
                errs.description = 'Description is required.';
        }

        if (s === 2) {
            const hasInScope = scopes.some(scope => scope.is_in_scope && scope.target.trim());
            if (!hasInScope)
                errs.scopes = 'At least one in-scope target is required.';
            scopes.forEach((scope, i) => {
                if (!scope.target.trim())
                    errs[`scope_${i}`] = 'Target is required.';
            });
        }

        if (s === 3) {
            if (formData.min_bounty && formData.max_bounty) {
                if (parseFloat(formData.min_bounty) > parseFloat(formData.max_bounty))
                    errs.max_bounty = 'Maximum must be greater than minimum bounty.';
            }
            if (formData.start_date && formData.end_date) {
                if (formData.start_date > formData.end_date)
                    errs.end_date = 'End date must be after start date.';
            }
            if (formData.invitation_only && formData.requires_application) {
                errs.requires_application =
                    'Choose one: invitation-only OR requires application — not both.';
            }
        }

        return errs;
    };

    // ---------------------------------------------------------------------------
    // Navigation
    // ---------------------------------------------------------------------------

    const goNext = async () => {
        const errs = validate(step);
        if (Object.keys(errs).length) {
            setErrors(errs);
            return;
        }
        setErrors({});

        if (step < STEPS.length) {
            setStep(s => s + 1);
        } else {
            await handleSubmit();
        }
    };

    const goBack = () => {
        setErrors({});
        setStep(s => s - 1);
    };

    // ---------------------------------------------------------------------------
    // Submit
    // ---------------------------------------------------------------------------

    const handleSubmit = async () => {
        setLoading(true);
        setErrors({});

        try {
            // 1. Create program
            const payload = {
                ...formData,
                min_bounty: formData.min_bounty || null,
                max_bounty: formData.max_bounty || null,
                start_date: formData.start_date || null,
                end_date: formData.end_date || null,
            };

            const programRes = await companyAPI.createProgram(payload);
            const program = programRes.data;

            // 2. Create scopes in parallel
            const validScopes = scopes.filter(s => s.target.trim());
            await Promise.all(
                validScopes.map(scope => companyAPI.createScope(program.id, scope))
            );

            setCreatedProgram(program);
            setStep(5); // Move to the "done" step
        } catch (err) {
            console.error('Program creation failed:', err);
            const serverErrors = err.response?.data || {};
            const flat = {};
            Object.entries(serverErrors).forEach(([k, v]) => {
                flat[k] = Array.isArray(v) ? v.join(' ') : String(v);
            });
            if (Object.keys(flat).length) {
                setErrors(flat);
                // Jump to the step containing the error fields
                if (flat.name || flat.description || flat.scope_type) setStep(1);
                else if (flat.scopes) setStep(2);
                else setStep(3);
            } else {
                setErrors({ general: 'Failed to create program. Please try again.' });
            }
        } finally {
            setLoading(false);
        }
    };

    const handleActivate = async () => {
        setActivating(true);
        try {
            await companyAPI.activateProgram(createdProgram.id);
            if (onSuccess) onSuccess({ ...createdProgram, status: 'active' });
            else navigate(`/programs/${createdProgram.id}`);
        } catch (err) {
            const msg = err.response?.data?.error || 'Failed to activate program.';
            setErrors({ general: msg });
        } finally {
            setActivating(false);
        }
    };

    const handleSaveAsDraft = () => {
        if (onSuccess) onSuccess(createdProgram);
        else navigate(`/programs/${createdProgram.id}`);
    };

    // ---------------------------------------------------------------------------
    // Render — success/launch screen (step 5)
    // ---------------------------------------------------------------------------

    if (step === 5 && createdProgram) {
        return (
            <div style={{ maxWidth: '600px', margin: '0 auto', textAlign: 'center', padding: '2rem' }}>
                <div style={{
                    background: 'white', padding: '3rem 2rem', borderRadius: '12px',
                    boxShadow: '0 4px 20px rgba(0,0,0,0.1)'
                }}>
                    <div style={{ fontSize: '3.5rem', marginBottom: '1rem' }}>🎉</div>
                    <h2 style={{ margin: '0 0 0.75rem 0', color: '#2c3e50' }}>
                        Program created!
                    </h2>
                    <p style={{ color: '#666', marginBottom: '0.5rem' }}>
                        <strong>{createdProgram.name}</strong> has been saved as a draft.
                    </p>
                    <p style={{ color: '#666', marginBottom: '2rem', fontSize: '0.95rem' }}>
                        Activate it now to make it visible to researchers, or save it as a
                        draft to review and activate later.
                    </p>

                    {errors.general && (
                        <div style={{
                            background: '#f8d7da', color: '#721c24', padding: '0.75rem 1rem',
                            borderRadius: '6px', marginBottom: '1.5rem', fontSize: '0.9rem',
                            border: '1px solid #f5c6cb'
                        }}>
                            {errors.general}
                        </div>
                    )}

                    {/* Summary */}
                    <div style={{
                        background: '#f8f9fa', borderRadius: '8px', padding: '1.25rem',
                        marginBottom: '2rem', textAlign: 'left'
                    }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                            <span style={{ color: '#666' }}>Type</span>
                            <span style={{ fontWeight: '500', textTransform: 'capitalize' }}>
                                {createdProgram.scope_type}
                            </span>
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                            <span style={{ color: '#666' }}>Status</span>
                            <span style={{
                                fontWeight: '600', color: '#e67e22',
                                background: '#fdf3e4', padding: '0.15rem 0.6rem',
                                borderRadius: '4px', fontSize: '0.85rem'
                            }}>
                                DRAFT
                            </span>
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                            <span style={{ color: '#666' }}>Bounty range</span>
                            <span style={{ fontWeight: '500', color: '#27ae60' }}>
                                {createdProgram.bounty_range || 'Not specified'}
                            </span>
                        </div>
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                        <button
                            onClick={handleActivate}
                            disabled={activating}
                            style={{
                                padding: '0.875rem', background: '#27ae60',
                                color: 'white', border: 'none', borderRadius: '6px',
                                cursor: activating ? 'not-allowed' : 'pointer',
                                fontSize: '1rem', fontWeight: '600',
                                opacity: activating ? 0.7 : 1,
                            }}
                        >
                            {activating ? 'Activating...' : '🚀 Activate Now — Make it Live'}
                        </button>
                        <button
                            onClick={handleSaveAsDraft}
                            style={{
                                padding: '0.875rem', background: 'white',
                                color: '#495057', border: '1px solid #dee2e6',
                                borderRadius: '6px', cursor: 'pointer', fontSize: '1rem'
                            }}
                        >
                            Save as Draft — Activate Later
                        </button>
                    </div>
                </div>
            </div>
        );
    }

    // ---------------------------------------------------------------------------
    // Render — review step (step 4)
    // ---------------------------------------------------------------------------

    const renderReview = () => (
        <div>
            <h3 style={{ marginTop: 0 }}>Review your program</h3>

            {[
                {
                    title: 'Basic Info',
                    step: 1,
                    rows: [
                        ['Name', formData.name],
                        ['Tagline', formData.short_description || '—'],
                        ['Type', formData.scope_type],
                        ['Description', formData.description.substring(0, 120) + (formData.description.length > 120 ? '...' : '')],
                    ]
                },
                {
                    title: 'Scope',
                    step: 2,
                    custom: (
                        <div>
                            <div style={{ marginBottom: '0.5rem', fontSize: '0.85rem', color: '#666' }}>
                                {scopes.filter(s => s.is_in_scope && s.target).length} in-scope ·{' '}
                                {scopes.filter(s => !s.is_in_scope && s.target).length} out-of-scope
                            </div>
                            {scopes.filter(s => s.target).map((s, i) => (
                                <div key={i} style={{ fontSize: '0.9rem', marginBottom: '0.25rem' }}>
                                    <span style={{
                                        display: 'inline-block', width: '24px', height: '16px',
                                        lineHeight: '16px', textAlign: 'center', borderRadius: '3px',
                                        fontSize: '0.7rem', fontWeight: '700', marginRight: '0.5rem',
                                        background: s.is_in_scope ? '#d4edda' : '#f8d7da',
                                        color: s.is_in_scope ? '#155724' : '#721c24',
                                    }}>
                                        {s.is_in_scope ? 'IN' : 'OUT'}
                                    </span>
                                    {s.target}
                                </div>
                            ))}
                        </div>
                    )
                },
                {
                    title: 'Rewards',
                    step: 3,
                    rows: [
                        ['Min bounty', formData.min_bounty ? `$${formData.min_bounty}` : 'Not set'],
                        ['Max bounty', formData.max_bounty ? `$${formData.max_bounty}` : 'Not set'],
                        ['Start date', formData.start_date || 'No start date'],
                        ['End date', formData.end_date || 'No end date'],
                        ['Anonymous submissions', formData.allow_anonymous ? 'Yes' : 'No'],
                        ['NDA required', formData.require_ndas ? 'Yes' : 'No'],
                        ...(formData.scope_type === 'private' ? [
                            ['Invitation only', formData.invitation_only ? 'Yes' : 'No'],
                            ['Requires application', formData.requires_application ? 'Yes' : 'No'],
                        ] : []),
                    ]
                }
            ].map(section => (
                <div key={section.title} style={{
                    background: '#f8f9fa', borderRadius: '8px',
                    padding: '1.25rem', marginBottom: '1rem'
                }}>
                    <div style={{
                        display: 'flex', justifyContent: 'space-between',
                        alignItems: 'center', marginBottom: '0.75rem'
                    }}>
                        <h4 style={{ margin: 0, fontSize: '0.95rem' }}>{section.title}</h4>
                        <button
                            type="button"
                            onClick={() => { setErrors({}); setStep(section.step); }}
                            style={{
                                background: 'none', border: 'none', color: '#3498db',
                                cursor: 'pointer', fontSize: '0.85rem', padding: 0
                            }}
                        >
                            Edit
                        </button>
                    </div>
                    {section.custom || (
                        <div>
                            {section.rows.map(([k, v]) => (
                                <div key={k} style={{
                                    display: 'flex', justifyContent: 'space-between',
                                    padding: '0.3rem 0',
                                    borderBottom: '1px solid #e9ecef',
                                    fontSize: '0.9rem'
                                }}>
                                    <span style={{ color: '#666' }}>{k}</span>
                                    <span style={{ fontWeight: '500', maxWidth: '60%', textAlign: 'right' }}>{v}</span>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            ))}
        </div>
    );

    // ---------------------------------------------------------------------------
    // Render — main wizard
    // ---------------------------------------------------------------------------

    return (
        <div style={{ maxWidth: '780px', margin: '0 auto' }}>
            <div style={{ textAlign: 'center', marginBottom: '0.5rem' }}>
                <h2 style={{ margin: '0 0 0.25rem 0' }}>Create Bug Bounty Program</h2>
                <p style={{ color: '#666', margin: '0 0 2rem 0', fontSize: '0.9rem' }}>
                    Set up your program in a few steps
                </p>
            </div>

            <StepIndicator currentStep={step} />

            {errors.general && (
                <div style={{
                    background: '#f8d7da', color: '#721c24', padding: '1rem',
                    borderRadius: '8px', marginBottom: '1.5rem', border: '1px solid #f5c6cb'
                }}>
                    {errors.general}
                </div>
            )}

            <div style={{
                background: 'white', padding: '2rem', borderRadius: '10px',
                boxShadow: '0 2px 12px rgba(0,0,0,0.08)'
            }}>
                {/* ── Step 1: Basic Info ─────────────────────────────────────── */}
                {step === 1 && (
                    <div>
                        <h3 style={{ marginTop: 0 }}>Basic Information</h3>

                        <div style={sectionStyle}>
                            <SectionLabel>Program Name *</SectionLabel>
                            <input
                                type="text" name="name" value={formData.name}
                                onChange={handleChange}
                                placeholder="e.g., Acme Corp Bug Bounty"
                                style={inputStyle}
                            />
                            <FieldError error={errors.name} />
                        </div>

                        <div style={sectionStyle}>
                            <SectionLabel hint="(shown in listing cards)">Short Description</SectionLabel>
                            <input
                                type="text" name="short_description" value={formData.short_description}
                                onChange={handleChange}
                                placeholder="One-line summary of the program"
                                maxLength={300}
                                style={inputStyle}
                            />
                        </div>

                        <div style={sectionStyle}>
                            <SectionLabel>Full Description *</SectionLabel>
                            <textarea
                                name="description" value={formData.description}
                                onChange={handleChange} rows={5}
                                placeholder="What should researchers look for? What are the program goals? Any important context?"
                                style={{ ...inputStyle, resize: 'vertical' }}
                            />
                            <FieldError error={errors.description} />
                        </div>

                        <div style={sectionStyle}>
                            <SectionLabel>Program Type</SectionLabel>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                                {[
                                    {
                                        value: 'public',
                                        label: 'Public',
                                        desc: 'Visible to all researchers. Anyone can submit reports.',
                                        color: '#3498db',
                                    },
                                    {
                                        value: 'private',
                                        label: 'Private',
                                        desc: 'Hidden from public listing. Researchers need an invitation or must apply.',
                                        color: '#9b59b6',
                                    },
                                    {
                                        value: 'vdp',
                                        label: 'VDP — Vulnerability Disclosure Program',
                                        desc: 'Public program focused on responsible disclosure. Typically no monetary bounties.',
                                        color: '#e67e22',
                                    },
                                ].map(opt => (
                                    <label
                                        key={opt.value}
                                        style={{
                                            display: 'flex', alignItems: 'flex-start', gap: '0.75rem',
                                            padding: '1rem', borderRadius: '8px', cursor: 'pointer',
                                            border: `2px solid ${formData.scope_type === opt.value ? opt.color : '#e9ecef'}`,
                                            background: formData.scope_type === opt.value ? opt.color + '08' : 'white',
                                            transition: 'all 0.15s',
                                        }}
                                    >
                                        <input
                                            type="radio" name="scope_type" value={opt.value}
                                            checked={formData.scope_type === opt.value}
                                            onChange={handleChange}
                                            style={{ marginTop: '0.2rem', accentColor: opt.color }}
                                        />
                                        <div>
                                            <div style={{ fontWeight: '600', color: opt.color }}>{opt.label}</div>
                                            <div style={{ fontSize: '0.85rem', color: '#666', marginTop: '0.2rem' }}>{opt.desc}</div>
                                        </div>
                                    </label>
                                ))}
                            </div>
                        </div>
                    </div>
                )}

                {/* ── Step 2: Scope ──────────────────────────────────────────── */}
                {step === 2 && (
                    <div>
                        <h3 style={{ marginTop: 0 }}>Define Scope</h3>
                        <p style={{ color: '#666', marginBottom: '1.5rem', fontSize: '0.9rem' }}>
                            Specify which targets are fair game and which are off-limits.
                            You need at least one in-scope target to activate the program.
                        </p>

                        {errors.scopes && (
                            <div style={{
                                background: '#f8d7da', color: '#721c24', padding: '0.75rem 1rem',
                                borderRadius: '6px', marginBottom: '1rem', fontSize: '0.9rem'
                            }}>
                                {errors.scopes}
                            </div>
                        )}

                        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                            {scopes.map((scope, index) => (
                                <div
                                    key={index}
                                    style={{
                                        border: `1px solid ${scope.is_in_scope ? '#c3e6cb' : '#f5c6cb'}`,
                                        borderRadius: '8px', padding: '1.25rem',
                                        background: scope.is_in_scope ? '#f8fff8' : '#fff8f8',
                                    }}
                                >
                                    {/* In/out toggle + remove */}
                                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem' }}>
                                        <div style={{ display: 'flex', gap: '0.5rem' }}>
                                            <button
                                                type="button"
                                                onClick={() => updateScope(index, 'is_in_scope', true)}
                                                style={{
                                                    padding: '0.35rem 0.85rem', borderRadius: '4px',
                                                    border: '2px solid',
                                                    borderColor: scope.is_in_scope ? '#27ae60' : '#dee2e6',
                                                    background: scope.is_in_scope ? '#27ae60' : 'white',
                                                    color: scope.is_in_scope ? 'white' : '#666',
                                                    cursor: 'pointer', fontSize: '0.82rem', fontWeight: '600'
                                                }}
                                            >
                                                ✓ In-Scope
                                            </button>
                                            <button
                                                type="button"
                                                onClick={() => updateScope(index, 'is_in_scope', false)}
                                                style={{
                                                    padding: '0.35rem 0.85rem', borderRadius: '4px',
                                                    border: '2px solid',
                                                    borderColor: !scope.is_in_scope ? '#e74c3c' : '#dee2e6',
                                                    background: !scope.is_in_scope ? '#e74c3c' : 'white',
                                                    color: !scope.is_in_scope ? 'white' : '#666',
                                                    cursor: 'pointer', fontSize: '0.82rem', fontWeight: '600'
                                                }}
                                            >
                                                ✕ Out-of-Scope
                                            </button>
                                        </div>
                                        {scopes.length > 1 && (
                                            <button
                                                type="button"
                                                onClick={() => removeScope(index)}
                                                style={{
                                                    background: 'none', border: 'none',
                                                    color: '#e74c3c', cursor: 'pointer',
                                                    fontSize: '0.85rem'
                                                }}
                                            >
                                                Remove
                                            </button>
                                        )}
                                    </div>

                                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '0.75rem' }}>
                                        <div>
                                            <label style={{ ...labelStyle, fontSize: '0.85rem' }}>Target *</label>
                                            <input
                                                type="text"
                                                value={scope.target}
                                                onChange={e => updateScope(index, 'target', e.target.value)}
                                                placeholder="*.example.com or 10.0.0.0/8"
                                                style={inputStyle}
                                            />
                                            <FieldError error={errors[`scope_${index}`]} />
                                        </div>
                                        <div>
                                            <label style={{ ...labelStyle, fontSize: '0.85rem' }}>Type</label>
                                            <select
                                                value={scope.target_type}
                                                onChange={e => updateScope(index, 'target_type', e.target.value)}
                                                style={inputStyle}
                                            >
                                                {TARGET_TYPES.map(t => (
                                                    <option key={t.value} value={t.value}>{t.label}</option>
                                                ))}
                                            </select>
                                        </div>
                                    </div>

                                    <div>
                                        <label style={{ ...labelStyle, fontSize: '0.85rem' }}>Notes (optional)</label>
                                        <textarea
                                            value={scope.description}
                                            onChange={e => updateScope(index, 'description', e.target.value)}
                                            rows={2}
                                            placeholder="Any additional details about this target..."
                                            style={{ ...inputStyle, resize: 'vertical' }}
                                        />
                                    </div>
                                </div>
                            ))}
                        </div>

                        <button
                            type="button"
                            onClick={addScope}
                            style={{
                                marginTop: '1rem', width: '100%', padding: '0.75rem',
                                background: 'transparent', color: '#3498db',
                                border: '2px dashed #3498db', borderRadius: '6px',
                                cursor: 'pointer', fontSize: '0.95rem', fontWeight: '500'
                            }}
                        >
                            + Add Another Target
                        </button>
                    </div>
                )}

                {/* ── Step 3: Rewards & Guidelines ───────────────────────────── */}
                {step === 3 && (
                    <div>
                        <h3 style={{ marginTop: 0 }}>Rewards & Guidelines</h3>

                        {/* Bounty */}
                        <div style={sectionStyle}>
                            <SectionLabel>Bounty Policy</SectionLabel>
                            <textarea
                                name="bounty_policy" value={formData.bounty_policy}
                                onChange={handleChange} rows={4}
                                placeholder="Describe your reward tiers, payment methods, timelines, etc."
                                style={{ ...inputStyle, resize: 'vertical' }}
                            />
                        </div>

                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', ...sectionStyle }}>
                            <div>
                                <SectionLabel>Min Bounty ($)</SectionLabel>
                                <input
                                    type="number" name="min_bounty" value={formData.min_bounty}
                                    onChange={handleChange} placeholder="0.00" step="0.01" min="0"
                                    style={inputStyle}
                                />
                            </div>
                            <div>
                                <SectionLabel>Max Bounty ($)</SectionLabel>
                                <input
                                    type="number" name="max_bounty" value={formData.max_bounty}
                                    onChange={handleChange} placeholder="0.00" step="0.01" min="0"
                                    style={inputStyle}
                                />
                                <FieldError error={errors.max_bounty} />
                            </div>
                        </div>

                        {/* Dates */}
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', ...sectionStyle }}>
                            <div>
                                <SectionLabel hint="(optional)">Start Date</SectionLabel>
                                <input
                                    type="date" name="start_date" value={formData.start_date}
                                    onChange={handleChange} style={inputStyle}
                                />
                            </div>
                            <div>
                                <SectionLabel hint="(optional)">End Date</SectionLabel>
                                <input
                                    type="date" name="end_date" value={formData.end_date}
                                    onChange={handleChange} style={inputStyle}
                                />
                                <FieldError error={errors.end_date} />
                            </div>
                        </div>

                        {/* Guidelines */}
                        <div style={sectionStyle}>
                            <SectionLabel hint="(optional)">Testing Guidelines</SectionLabel>
                            <textarea
                                name="testing_guidelines" value={formData.testing_guidelines}
                                onChange={handleChange} rows={3}
                                placeholder="What researchers should and should not do during testing..."
                                style={{ ...inputStyle, resize: 'vertical' }}
                            />
                        </div>

                        <div style={sectionStyle}>
                            <SectionLabel hint="(optional)">Report Guidelines</SectionLabel>
                            <textarea
                                name="report_guidelines" value={formData.report_guidelines}
                                onChange={handleChange} rows={3}
                                placeholder="What to include in a submission — PoC requirements, severity criteria, etc."
                                style={{ ...inputStyle, resize: 'vertical' }}
                            />
                        </div>

                        <div style={sectionStyle}>
                            <SectionLabel hint="(optional)">Disclosure Policy</SectionLabel>
                            <textarea
                                name="disclosure_policy" value={formData.disclosure_policy}
                                onChange={handleChange} rows={2}
                                placeholder="Coordinated disclosure timeline, e.g. 90 days before public disclosure..."
                                style={{ ...inputStyle, resize: 'vertical' }}
                            />
                        </div>

                        {/* Program flags */}
                        <div style={{
                            background: '#f8f9fa', padding: '1.25rem',
                            borderRadius: '8px'
                        }}>
                            <h4 style={{ margin: '0 0 1rem 0', fontSize: '0.95rem' }}>Program Settings</h4>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                                {[
                                    { name: 'allow_anonymous', label: 'Allow anonymous submissions' },
                                    { name: 'require_ndas', label: 'Require NDA for participation' },
                                    ...(formData.scope_type === 'private' ? [
                                        { name: 'invitation_only', label: 'Invitation only — researchers must be explicitly invited to join' },
                                        { name: 'requires_application', label: 'Requires application — researchers must apply and be approved' },
                                    ] : []),
                                ].map(({ name, label }) => (
                                    <label
                                        key={name}
                                        style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', cursor: 'pointer' }}
                                    >
                                        <input
                                            type="checkbox" name={name}
                                            checked={formData[name]}
                                            onChange={handleChange}
                                            style={{ width: '16px', height: '16px', accentColor: '#3498db' }}
                                        />
                                        <span style={{ fontSize: '0.95rem' }}>{label}</span>
                                    </label>
                                ))}
                            </div>
                            {errors.requires_application && (
                                <FieldError error={errors.requires_application} />
                            )}
                        </div>
                    </div>
                )}

                {/* ── Step 4: Review ─────────────────────────────────────────── */}
                {step === 4 && renderReview()}

                {/* ── Nav ────────────────────────────────────────────────────── */}
                <NavButtons
                    step={step}
                    totalSteps={STEPS.length}
                    onBack={goBack}
                    onNext={goNext}
                    onCancel={onCancel || (() => navigate(-1))}
                    loading={loading}
                    nextLabel={
                        step === STEPS.length - 1
                            ? 'Review →'
                            : step === STEPS.length
                            ? '✓ Create Program'
                            : 'Next →'
                    }
                />
            </div>
        </div>
    );
};

export default ProgramWizard;