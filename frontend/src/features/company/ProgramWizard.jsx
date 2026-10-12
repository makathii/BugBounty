import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { companyAPI } from '../../services/api';
import './Wizard.css';

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
// Sub-components
// ---------------------------------------------------------------------------

const FieldError = ({ error }) =>
    error ? (
        <span className="field-error">
            {error}
        </span>
    ) : null;

const SectionLabel = ({ children, hint }) => (
    <label className="section-label">
        {children}
        {hint && <span className="section-label-hint">{hint}</span>}
    </label>
);

const StepIndicator = ({ currentStep }) => (
    <div className="wizard-steps">
        {STEPS.map((s, i) => {
            const done = currentStep > s.n;
            const active = currentStep === s.n;
            return (
                <React.Fragment key={s.n}>
                    <div className="wizard-step">
                        <div className={`wizard-step-circle ${done ? 'complete' : active ? 'active' : 'pending'}`}>
                            {done ? '✓' : s.n}
                        </div>
                        <span className={`wizard-step-label ${done ? 'complete' : active ? 'active' : ''}`}>
                            {s.label}
                        </span>
                    </div>
                    {i < STEPS.length - 1 && (
                        <div className={`wizard-step-line ${done ? 'complete' : ''}`} />
                    )}
                </React.Fragment>
            );
        })}
    </div>
);

const NavButtons = ({ step, totalSteps, onBack, onNext, onCancel, loading, nextLabel }) => (
    <div className="wizard-nav">
        <button
            type="button"
            className="btn btn-ghost"
            onClick={step === 1 ? onCancel : onBack}
        >
            {step === 1 ? 'Cancel' : '← Back'}
        </button>
        <button
            type="button"
            className="btn btn-primary"
            onClick={onNext}
            disabled={loading}
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
    const [createdProgram, setCreatedProgram] = useState(null);
    const [activating, setActivating] = useState(false);

    const [formData, setFormData] = useState({
        name: '',
        short_description: '',
        description: '',
        scope_type: 'public',
        reward_notes: '',
        min_points: '',
        max_points: '',
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
            if (formData.min_points && formData.max_points) {
                if (parseInt(formData.min_points, 10) > parseInt(formData.max_points, 10))
                    errs.max_points = 'Maximum must be greater than minimum points.';
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
            const payload = {
                ...formData,
                min_points: formData.min_points || null,
                max_points: formData.max_points || null,
                start_date: formData.start_date || null,
                end_date: formData.end_date || null,
            };

            const programRes = await companyAPI.createProgram(payload);
            const program = programRes.data;

            const validScopes = scopes.filter(s => s.target.trim());
            await Promise.all(
                validScopes.map(scope => companyAPI.createScope(program.id, scope))
            );

            setCreatedProgram(program);
            setStep(5);
        } catch (err) {
            console.error('Program creation failed:', err);
            const serverErrors = err.response?.data || {};
            const flat = {};
            Object.entries(serverErrors).forEach(([k, v]) => {
                flat[k] = Array.isArray(v) ? v.join(' ') : String(v);
            });
            if (Object.keys(flat).length) {
                setErrors(flat);
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
            <div className="program-success">
                <div className="program-success-card">
                    <div className="program-success-icon">🎉</div>
                    <h2>Program created!</h2>
                    <p>
                        <strong>{createdProgram.name}</strong> has been saved as a draft.
                    </p>
                    <p>
                        Activate it now to make it visible to researchers, or save it as a
                        draft to review and activate later.
                    </p>

                    {errors.general && (
                        <div className="alert-error">
                            {errors.general}
                        </div>
                    )}

                    <div className="program-summary">
                        <div className="review-row">
                            <span className="review-key">Type</span>
                            <span className="review-value">{createdProgram.scope_type}</span>
                        </div>
                        <div className="review-row">
                            <span className="review-key">Status</span>
                            <span className="status-pill draft">DRAFT</span>
                        </div>
                        <div className="review-row">
                            <span className="review-key">Points range</span>
                            <span className="review-value">
                                {createdProgram.points_range || 'Not specified'}
                            </span>
                        </div>
                    </div>

                    <div className="wizard-nav">
                        <button
                            className="btn btn-primary"
                            onClick={handleActivate}
                            disabled={activating}
                        >
                            {activating ? 'Activating...' : '🚀 Activate Now — Make it Live'}
                        </button>
                        <button
                            className="btn btn-ghost"
                            onClick={handleSaveAsDraft}
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
            <h3>Review your program</h3>

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
                            <div className="review-row">
                                <span className="review-key">
                                    {scopes.filter(s => s.is_in_scope && s.target).length} in-scope ·{' '}
                                    {scopes.filter(s => !s.is_in_scope && s.target).length} out-of-scope
                                </span>
                            </div>
                            {scopes.filter(s => s.target).map((s, i) => (
                                <div key={i} className="review-row">
                                    <span className={`status-pill ${s.is_in_scope ? 'active' : 'draft'}`}>
                                        {s.is_in_scope ? 'IN' : 'OUT'}
                                    </span>
                                    <span className="review-value">{s.target}</span>
                                </div>
                            ))}
                        </div>
                    )
                },
                {
                    title: 'Rewards',
                    step: 3,
                    rows: [
                        ['Min points', formData.min_points ? `${formData.min_points} pts` : 'Not set'],
                        ['Max points', formData.max_points ? `${formData.max_points} pts` : 'Not set'],
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
                <div key={section.title} className="review-card">
                    <div className="review-row">
                        <h4>{section.title}</h4>
                        <button
                            type="button"
                            className="btn btn-ghost"
                            onClick={() => { setErrors({}); setStep(section.step); }}
                        >
                            Edit
                        </button>
                    </div>
                    {section.custom || (
                        <div>
                            {section.rows.map(([k, v]) => (
                                <div key={k} className="review-row">
                                    <span className="review-key">{k}</span>
                                    <span className="review-value">{v}</span>
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
        <div className="program-wizard">
            <div className="program-wizard-header">
                <h2>Create Bug Bounty Program</h2>
                <p>Set up your program in a few steps</p>
            </div>

            <StepIndicator currentStep={step} />

            {errors.general && (
                <div className="alert-error">
                    {errors.general}
                </div>
            )}

            <div className="program-wizard-card">
                {/* ── Step 1: Basic Info ─────────────────────────────────────── */}
                {step === 1 && (
                    <div>
                        <h3>Basic Information</h3>

                        <div className="form-group">
                            <SectionLabel>Program Name *</SectionLabel>
                            <input
                                className="form-input"
                                type="text" name="name" value={formData.name}
                                onChange={handleChange}
                                placeholder="e.g., Acme Corp Bug Bounty"
                            />
                            <FieldError error={errors.name} />
                        </div>

                        <div className="form-group">
                            <SectionLabel hint="(shown in listing cards)">Short Description</SectionLabel>
                            <input
                                className="form-input"
                                type="text" name="short_description" value={formData.short_description}
                                onChange={handleChange}
                                placeholder="One-line summary of the program"
                                maxLength={300}
                            />
                        </div>

                        <div className="form-group">
                            <SectionLabel>Full Description *</SectionLabel>
                            <textarea
                                className="form-input"
                                name="description" value={formData.description}
                                onChange={handleChange} rows={5}
                                placeholder="What should researchers look for? What are the program goals? Any important context?"
                            />
                            <FieldError error={errors.description} />
                        </div>

                        <div className="form-group">
                            <SectionLabel>Program Type</SectionLabel>
                            <div className="radio-group">
                                {[
                                    {
                                        value: 'public',
                                        label: 'Public',
                                        badge: 'Open',
                                        desc: 'Visible to all researchers. Anyone can submit reports.',
                                    },
                                    {
                                        value: 'private',
                                        label: 'Private',
                                        badge: 'Invite',
                                        desc: 'Hidden from public listing. Researchers need an invitation or must apply.',
                                    },
                                    {
                                        value: 'vdp',
                                        label: 'VDP',
                                        badge: 'Disclosure',
                                        desc: 'Public program focused on responsible disclosure. Typically awards no points.',
                                    },
                                ].map(opt => (
                                    <label
                                        key={opt.value}
                                        className={`radio-card ${formData.scope_type === opt.value ? 'selected' : ''}`}
                                        data-type={opt.value}
                                    >
                                        <input
                                            type="radio" name="scope_type" value={opt.value}
                                            checked={formData.scope_type === opt.value}
                                            onChange={handleChange}
                                        />
                                        <div>
                                            <div className="radio-card-label">
                                                {opt.label}
                                                <span className={`radio-card-badge ${opt.value}`}>{opt.badge}</span>
                                            </div>
                                            <div className="radio-card-desc">{opt.desc}</div>
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
                        <h3>Define Scope</h3>
                        <p>
                            Specify which targets are fair game and which are off-limits.
                            You need at least one in-scope target to activate the program.
                        </p>

                        {errors.scopes && (
                            <div className="alert-error">
                                {errors.scopes}
                            </div>
                        )}

                        <div className="scope-list">
                            {scopes.map((scope, index) => (
                                <div
                                    key={index}
                                    className={`scope-card ${scope.is_in_scope ? 'in-scope' : 'out-scope'}`}
                                >
                                    <div className="scope-card-header">
                                        <div className="scope-toggles">
                                            <button
                                                type="button"
                                                className={`scope-toggle ${scope.is_in_scope ? 'active in' : ''}`}
                                                onClick={() => updateScope(index, 'is_in_scope', true)}
                                            >
                                                ✓ In-Scope
                                            </button>
                                            <button
                                                type="button"
                                                className={`scope-toggle ${!scope.is_in_scope ? 'active out' : ''}`}
                                                onClick={() => updateScope(index, 'is_in_scope', false)}
                                            >
                                                ✕ Out-of-Scope
                                            </button>
                                        </div>
                                        {scopes.length > 1 && (
                                            <button
                                                type="button"
                                                className="btn btn-ghost btn-sm"
                                                onClick={() => removeScope(index)}
                                            >
                                                Remove
                                            </button>
                                        )}
                                    </div>

                                    <div className="scope-grid">
                                        <div className="form-group">
                                            <label className="form-label">Target *</label>
                                            <input
                                                className="form-input"
                                                type="text"
                                                value={scope.target}
                                                onChange={e => updateScope(index, 'target', e.target.value)}
                                                placeholder="*.example.com or 10.0.0.0/8"
                                            />
                                            <FieldError error={errors[`scope_${index}`]} />
                                        </div>
                                        <div className="form-group">
                                            <label className="form-label">Type</label>
                                            <select
                                                className="form-input"
                                                value={scope.target_type}
                                                onChange={e => updateScope(index, 'target_type', e.target.value)}
                                            >
                                                {TARGET_TYPES.map(t => (
                                                    <option key={t.value} value={t.value}>{t.label}</option>
                                                ))}
                                            </select>
                                        </div>
                                    </div>

                                    <div className="form-group">
                                        <label className="form-label">Notes (optional)</label>
                                        <textarea
                                            className="form-input"
                                            value={scope.description}
                                            onChange={e => updateScope(index, 'description', e.target.value)}
                                            rows={2}
                                            placeholder="Any additional details about this target..."
                                        />
                                    </div>
                                </div>
                            ))}
                        </div>

                        <button
                            type="button"
                            className="btn btn-ghost"
                            onClick={addScope}
                        >
                            + Add Another Target
                        </button>
                    </div>
                )}

                {/* ── Step 3: Rewards & Guidelines ───────────────────────────── */}
                {step === 3 && (
                    <div>
                        <h3>Rewards & Guidelines</h3>

                        <div className="form-group">
                            <SectionLabel>Reward Notes</SectionLabel>
                            <textarea
                                className="form-input"
                                name="reward_notes" value={formData.reward_notes}
                                onChange={handleChange} rows={4}
                                placeholder="Points are awarded by severity (10 / 30 / 70 / 150). Say what earns bonus points here."
                            />
                        </div>

                        <div className="scope-grid">
                            <div className="form-group">
                                <SectionLabel>Min Points</SectionLabel>
                                <input
                                    className="form-input"
                                    type="number" name="min_points" value={formData.min_points}
                                    onChange={handleChange} placeholder="10" step="1" min="0"
                                />
                            </div>
                            <div className="form-group">
                                <SectionLabel>Max Points</SectionLabel>
                                <input
                                    className="form-input"
                                    type="number" name="max_points" value={formData.max_points}
                                    onChange={handleChange} placeholder="150" step="1" min="0"
                                />
                                <FieldError error={errors.max_points} />
                            </div>
                        </div>

                        <div className="scope-grid">
                            <div className="form-group">
                                <SectionLabel hint="(optional)">Start Date</SectionLabel>
                                <input
                                    className="form-input"
                                    type="date" name="start_date" value={formData.start_date}
                                    onChange={handleChange}
                                />
                            </div>
                            <div className="form-group">
                                <SectionLabel hint="(optional)">End Date</SectionLabel>
                                <input
                                    className="form-input"
                                    type="date" name="end_date" value={formData.end_date}
                                    onChange={handleChange}
                                />
                                <FieldError error={errors.end_date} />
                            </div>
                        </div>

                        <div className="form-group">
                            <SectionLabel hint="(optional)">Testing Guidelines</SectionLabel>
                            <textarea
                                className="form-input"
                                name="testing_guidelines" value={formData.testing_guidelines}
                                onChange={handleChange} rows={3}
                                placeholder="What researchers should and should not do during testing..."
                            />
                        </div>

                        <div className="form-group">
                            <SectionLabel hint="(optional)">Report Guidelines</SectionLabel>
                            <textarea
                                className="form-input"
                                name="report_guidelines" value={formData.report_guidelines}
                                onChange={handleChange} rows={3}
                                placeholder="What to include in a submission — PoC requirements, severity criteria, etc."
                            />
                        </div>

                        <div className="form-group">
                            <SectionLabel hint="(optional)">Disclosure Policy</SectionLabel>
                            <textarea
                                className="form-input"
                                name="disclosure_policy" value={formData.disclosure_policy}
                                onChange={handleChange} rows={2}
                                placeholder="Coordinated disclosure timeline, e.g. 90 days before public disclosure..."
                            />
                        </div>

                        <div className="settings-panel">
                            <h4>Program Settings</h4>
                            <div className="checkbox-group">
                                {[
                                    { name: 'allow_anonymous', label: 'Allow anonymous submissions' },
                                    { name: 'require_ndas', label: 'Require NDA for participation' },
                                    ...(formData.scope_type === 'private' ? [
                                        { name: 'invitation_only', label: 'Invitation only — researchers must be explicitly invited to join' },
                                        { name: 'requires_application', label: 'Requires application — researchers must apply and be approved' },
                                    ] : []),
                                ].map(({ name, label }) => (
                                    <label key={name} className="checkbox-label">
                                        <input
                                            type="checkbox" name={name}
                                            checked={formData[name]}
                                            onChange={handleChange}
                                        />
                                        <span>{label}</span>
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