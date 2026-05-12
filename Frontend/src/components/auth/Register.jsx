// src/components/Register.jsx
import React, { useState, useEffect, useRef } from 'react';
import api from '../../services/api';

const Register = ({ onRegister, switchToLogin }) => {
    const [formData, setFormData] = useState({
        username: '',
        email: '',
        password: '',
        password2: '',
        first_name: '',
        last_name: ''
    });
    const [errors, setErrors] = useState({});
    const [isLoading, setIsLoading] = useState(false);
    const captchaRef = useRef(null);
    const widgetIdRef = useRef(null);
    const siteKey = process.env.REACT_APP_RECAPTCHA_SITE_KEY;

    useEffect(() => {
        if (window.grecaptcha && captchaRef.current && widgetIdRef.current === null) {
            widgetIdRef.current = window.grecaptcha.render(captchaRef.current, {
                sitekey: siteKey,
            });
        }
    }, []);

    const handleChange = (e) => {
        setFormData({
            ...formData,
            [e.target.name]: e.target.value
        });
        // Clear errors when user starts typing
        if (errors[e.target.name]) {
            setErrors({
                ...errors,
                [e.target.name]: ''
            });
        }
    };

    const validateForm = () => {
        const newErrors = {};

        if (formData.username.length < 3) {
            newErrors.username = 'Username must be at least 3 characters';
        }

        if (!formData.email.includes('@')) {
            newErrors.email = 'Please enter a valid email address';
        }

        if (formData.password.length < 8) {
            newErrors.password = 'Password must be at least 8 characters';
        }

        if (formData.password !== formData.password2) {
            newErrors.password2 = 'Passwords do not match';
        }

        setErrors(newErrors);
        return Object.keys(newErrors).length === 0;
    };

    const handleSubmit = async (e) => {
        e.preventDefault();

        setErrors(prev => ({ ...prev, captcha: '' }));

        if (!validateForm()) {
            return;
        }

        const tokenInput = document.querySelector('textarea[name="g-recaptcha-response"]');
        const token = tokenInput ? tokenInput.value : '';

        setIsLoading(true);
        try {
            console.log('captcha token:', token);
            const response = await api.post('/users/register/', {
                ...formData,
                captcha: token,
            });
            console.log('Registration successful:', response.data);
            if (window.grecaptcha && window.grecaptcha.reset) {
                window.grecaptcha.reset();
            }

            // Auto-login after successful registration
            try {
                const loginResponse = await api.post('/token/', {
                    username: formData.username,
                    password: formData.password
                });

                localStorage.setItem('access_token', loginResponse.data.access);
                localStorage.setItem('refresh_token', loginResponse.data.refresh);

                onRegister(); // Notify parent component
            } catch (loginError) {
                console.error('Auto-login failed:', loginError);
                // Still consider registration successful, just redirect to login
                switchToLogin();
            }

        } catch (error) {
            console.error('Registration failed:', error);

            // Handle backend validation errors
            if (error.response?.data) {
                const backendErrors = error.response.data;
                const formattedErrors = {};

                Object.keys(backendErrors).forEach(key => {
                    formattedErrors[key] = Array.isArray(backendErrors[key])
                        ? backendErrors[key].join(', ')
                        : backendErrors[key];
                });

                setErrors(formattedErrors);
            } else {
                setErrors({ general: 'Registration failed. Please try again.' });
            }
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="register-container">
            <h2>Join Bug Bounty Platform</h2>

            {errors.general && (
                <div className="error-message">{errors.general}</div>
            )}

            <form onSubmit={handleSubmit}>
                <div className="form-group">
                    <input
                        type="text"
                        name="username"
                        placeholder="Username"
                        value={formData.username}
                        onChange={handleChange}
                        required
                        className={errors.username ? 'error' : ''}
                    />
                    {errors.username && <span className="error-text">{errors.username}</span>}
                </div>

                <div className="form-group">
                    <input
                        type="email"
                        name="email"
                        placeholder="Email"
                        value={formData.email}
                        onChange={handleChange}
                        required
                        className={errors.email ? 'error' : ''}
                    />
                    {errors.email && <span className="error-text">{errors.email}</span>}
                </div>

                <div className="name-fields">
                    <div className="form-group">
                        <input
                            type="text"
                            name="first_name"
                            placeholder="First Name"
                            value={formData.first_name}
                            onChange={handleChange}
                        />
                    </div>

                    <div className="form-group">
                        <input
                            type="text"
                            name="last_name"
                            placeholder="Last Name"
                            value={formData.last_name}
                            onChange={handleChange}
                        />
                    </div>
                </div>

                <div className="form-group">
                    <input
                        type="password"
                        name="password"
                        placeholder="Password"
                        value={formData.password}
                        onChange={handleChange}
                        required
                        className={errors.password ? 'error' : ''}
                    />
                    {errors.password && <span className="error-text">{errors.password}</span>}
                </div>

                <div className="form-group">
                    <input
                        type="password"
                        name="password2"
                        placeholder="Confirm Password"
                        value={formData.password2}
                        onChange={handleChange}
                        required
                        className={errors.password2 ? 'error' : ''}
                    />
                    {errors.password2 && <span className="error-text">{errors.password2}</span>}
                </div>

                <div className='form-group'>
                    <div
                        className="g-recaptcha"
                        ref={captchaRef}
                    />
                    {errors.captcha && (
                        <span className='error-text'>{errors.captcha}</span>
                    )}
                </div>

                <button
                    type="submit"
                    disabled={isLoading}
                    className="submit-btn"
                >
                    {isLoading ? 'Creating Account...' : 'Create Account'}
                </button>
            </form>

            <p className="switch-auth">
                Already have an account?{' '}
                <button type="button" onClick={switchToLogin} className="link-btn">
                    Login here
                </button>
            </p>
        </div>
    );
};

export default Register;